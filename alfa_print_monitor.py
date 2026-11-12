"""ALFA ERP print surveillance: native Windows spooler, local durable history.

Read-only baseline: no spooler resets, implicit deletes or driver patching.
PagesPrinted is a spooler counter, NEVER proof of physical output.
All printer document names remain in the local SQLite file, not Firebase.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from PySide6.QtCore import QThread, Signal
from alfa_print_events import WinPrintChangeFeed, RECONCILE_MS, FALLBACK_MS
from alfa_print_plan import PrintPlanRepository
from alfa_print_ipp import IppSettings, IppReader, IppTelemetryError
from alfa_print_snmp import SnmpSettings, SnmpReader, SnmpTelemetryError
from alfa_print_vendor import WinPrinterVendorInventory, installed_vendor_tools
from alfa_print_runtime import PrintCollectorLease

ACTIVE = {"bekliyor", "aktarılıyor", "yazdırılıyor", "duraklatıldı",
          "çevrimdışı", "kağıt_yok", "müdahale", "bloklandı", "hata"}
WARNING = {"çevrimdışı", "kağıt_yok", "müdahale", "bloklandı", "hata"}
MIB = 1024 * 1024
MAX_QUEUE_JOBS = 500
MAX_BUFFER = 16 * MIB


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PrintAccessError(RuntimeError):
    pass


class _SystemTime(ctypes.Structure):
    _fields_ = [(name, wintypes.WORD) for name in (
        "year", "month", "weekday", "day", "hour", "minute", "second", "millisecond")]


class _PrinterInfo4(ctypes.Structure):
    _fields_ = [("name", wintypes.LPWSTR), ("server", wintypes.LPWSTR),
                ("attributes", wintypes.DWORD)]


class _DevModePrefix(ctypes.Structure):
    # Standard DEVMODEW fields up to dmColor. Only valid when DM_COLOR is set.
    _fields_ = [("device", ctypes.c_wchar * 32),
                ("spec_version", wintypes.WORD), ("driver_version", wintypes.WORD),
                ("size", wintypes.WORD), ("extra", wintypes.WORD),
                ("fields", wintypes.DWORD),
                ("paper", ctypes.c_short * 8),
                ("color", ctypes.c_short)]


class _JobInfo2(ctypes.Structure):
    _fields_ = [
        ("id", wintypes.DWORD), ("printer", wintypes.LPWSTR),
        ("machine", wintypes.LPWSTR), ("user", wintypes.LPWSTR),
        ("document", wintypes.LPWSTR), ("notify_name", wintypes.LPWSTR),
        ("data_type", wintypes.LPWSTR), ("processor", wintypes.LPWSTR),
        ("parameters", wintypes.LPWSTR), ("driver", wintypes.LPWSTR),
        ("devmode", ctypes.c_void_p), ("status_text", wintypes.LPWSTR),
        ("security_descriptor", ctypes.c_void_p), ("status", wintypes.DWORD),
        ("priority", wintypes.DWORD), ("position", wintypes.DWORD),
        ("start_time", wintypes.DWORD), ("until_time", wintypes.DWORD),
        ("total_pages", wintypes.DWORD), ("size_bytes", wintypes.DWORD),
        ("submitted", _SystemTime), ("elapsed", wintypes.DWORD),
        ("pages_printed", wintypes.DWORD),
    ]


def _state(bits):
    # Windows job statuses are flags. Check errors before Printing.
    for flag,state in ((0x20,"çevrimdışı"),(0x40,"kağıt_yok"),
                       (0x400,"müdahale"),(0x200,"bloklandı"),
                       (0x2,"hata")):
        if bits & flag:
            return state
    if bits & 0x1:
        return "duraklatıldı"
    if bits & 0x8:
        return "aktarılıyor"
    if bits & 0x10:
        return "yazdırılıyor"
    # COMPLETE can mean only "sent to printer", not physical output.
    if bits & (0x80 | 0x1000):
        return "spool_tamam"
    if bits & 0x4:
        return "siliniyor"
    if bits & 0x100:
        return "silindi"
    return "bekliyor"


def _submitted(st):
    if st.year < 2000 or not st.month or not st.day:
        return ""
    try:
        # Microsoft defines the submitted SYSTEMTIME as UTC.
        return datetime(st.year, st.month, st.day, st.hour, st.minute,
                        st.second, tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def _job_color(ptr):
    if not ptr:
        return "Bilinmiyor"
    try:
        dm=ctypes.cast(ptr, ctypes.POINTER(_DevModePrefix)).contents
        if int(dm.size) < ctypes.sizeof(_DevModePrefix) or not (dm.fields & 0x800):
            return "Bilinmiyor"
        return {1:"Siyah-beyaz (sürücü)", 2:"Renkli (sürücü)"}.get(
            int(dm.color), "Bilinmiyor")
    except (ValueError, OSError, ctypes.ArgumentError):
        return "Bilinmiyor"


class WinSpoolProbe:
    """Read Windows spool queues via official WinSpoolW API, no admin bypass."""

    def __init__(self):
        if os.name != "nt":
            raise PrintAccessError("Windows yazdırma altyapısı yalnız Windows'ta kullanılabilir.")
        self.api=ctypes.WinDLL("winspool.drv", use_last_error=True)
        self.api.EnumPrintersW.argtypes=[
            wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD)]
        self.api.EnumPrintersW.restype=wintypes.BOOL
        self.api.OpenPrinterW.argtypes=[
            wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
        self.api.OpenPrinterW.restype=wintypes.BOOL
        self.api.ClosePrinter.argtypes=[wintypes.HANDLE]
        self.api.ClosePrinter.restype=wintypes.BOOL
        self.api.EnumJobsW.argtypes=[
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
        self.api.EnumJobsW.restype=wintypes.BOOL

    @staticmethod
    def _buffer(size):
        if size > MAX_BUFFER:
            raise PrintAccessError("Windows yazdırma kuyruğu güvenli okuma sınırını aştı.")
        return ctypes.create_string_buffer(max(1, size))

    def printers(self):
        needed=wintypes.DWORD()
        count=wintypes.DWORD()
        ctypes.set_last_error(0)
        initial=self.api.EnumPrintersW(0x2 | 0x4, None, 4, None, 0,
                                       ctypes.byref(needed), ctypes.byref(count))
        if needed.value == 0:
            if not initial and ctypes.get_last_error() not in (0,122):
                raise PrintAccessError("Yazıcı listesi okunamadı (Win32 %d)." %
                                       ctypes.get_last_error())
            return []
        buf=self._buffer(needed.value)
        if not self.api.EnumPrintersW(0x2 | 0x4, None, 4, buf, len(buf),
                                      ctypes.byref(needed), ctypes.byref(count)):
            raise PrintAccessError("Yüklü Windows yazıcıları okunamadı (Win32 %d)." %
                                   ctypes.get_last_error())
        array=ctypes.cast(buf, ctypes.POINTER(_PrinterInfo4))
        return sorted(set(str(array[i].name) for i in range(count.value)
                          if array[i].name))

    def queue(self, printer):
        handle=wintypes.HANDLE()
        if not self.api.OpenPrinterW(printer, ctypes.byref(handle), None):
            raise PrintAccessError("Yazıcı kuyruğuna erişilemiyor (Win32 %d)." %
                                   ctypes.get_last_error())
        try:
            needed=wintypes.DWORD()
            count=wintypes.DWORD()
            ctypes.set_last_error(0)
            ok=self.api.EnumJobsW(handle, 0, MAX_QUEUE_JOBS, 2, None, 0,
                                  ctypes.byref(needed), ctypes.byref(count))
            if ok and count.value==0:
                return []
            if not ok and needed.value==0:
                if ctypes.get_last_error() not in (0,122):
                    raise PrintAccessError("Kuyruğa erişim reddedildi (Win32 %d)." %
                                           ctypes.get_last_error())
                return []
            buf=self._buffer(needed.value)
            if not self.api.EnumJobsW(handle,0,MAX_QUEUE_JOBS,2,buf,len(buf),
                                      ctypes.byref(needed),ctypes.byref(count)):
                raise PrintAccessError("Kuyruk okunamadı (Win32 %d)." %
                                       ctypes.get_last_error())
            data=ctypes.cast(buf,ctypes.POINTER(_JobInfo2))
            jobs=[]
            for i in range(count.value):
                j=data[i]
                doc=str(j.document or "Belge adı bilinmiyor")[:260]
                when=_submitted(j.submitted)
                key=hashlib.sha256(
                    (printer+"\0"+str(j.id)+"\0"+when+"\0"+doc).encode(
                        "utf-8","replace")).hexdigest()[:32]
                jobs.append(dict(
                    key=key, printer=printer, native_id=int(j.id),
                    document=doc, submitted=when,
                    owner=str(j.user or "")[:100],
                    position=int(j.position), pages=max(0,int(j.pages_printed)),
                    total=max(0,int(j.total_pages)), bytes=int(j.size_bytes),
                    state=_state(int(j.status)),
                    detail=str(j.status_text or "")[:180],
                    color=_job_color(j.devmode),
                ))
            return jobs
        finally:
            self.api.ClosePrinter(handle)

    def snapshot(self):
        result=[]
        for printer in self.printers():
            try:
                result.append({"name":printer, "jobs":self.queue(printer),
                               "error":""})
            except (PrintAccessError, OSError) as exc:
                # A remote printer might be unreachable; do not mislabel
                # its last known jobs as finished or removed.
                result.append({"name":printer, "jobs":[], "error":str(exc)[:180]})
        return result


class PrintJournal:
    """Private local SQLite history; no spool or PDF bytes stored here."""

    def __init__(self, data_dir):
        folder=Path(data_dir)/"print_monitor"
        folder.mkdir(parents=True,exist_ok=True)
        self.path=folder/"print_history.sqlite3"
        self.db=sqlite3.connect(str(self.path),timeout=12)
        self.db.row_factory=sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=12000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs(
                key TEXT PRIMARY KEY,
                printer TEXT NOT NULL, native_id INTEGER,
                document TEXT, submitted TEXT, owner TEXT, position INTEGER,
                pages INTEGER, total INTEGER, bytes INTEGER, state TEXT,
                detail TEXT, color TEXT, first_seen TEXT, last_seen TEXT,
                disappeared TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_print_jobs_printer
                ON jobs(printer, last_seen DESC);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_key TEXT,
                at TEXT, printer TEXT, kind TEXT, detail TEXT
            );
            CREATE TABLE IF NOT EXISTS labels(
                job_key TEXT PRIMARY KEY, book TEXT, mode TEXT
            );
            CREATE TABLE IF NOT EXISTS monitor_sessions(
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pid INTEGER, started_at TEXT NOT NULL, closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS collector_snapshot(
                id INTEGER PRIMARY KEY CHECK(id=1),
                payload TEXT NOT NULL, captured_at TEXT NOT NULL
            );
        """)
        self.db.commit()
        previous=self.db.execute("""
            SELECT session_id, closed_at FROM monitor_sessions
            ORDER BY session_id DESC LIMIT 1
        """).fetchone()
        if previous and previous["closed_at"] is None:
            with self.db:
                self._event("",_utc(),"","oturum_kurtarma",
                            "Önceki izleme oturumu düzgün kapanmamış veya hâlâ açık; "
                            "eski baskılar fiziksel olarak tamamlandı sayılmadı")
        with self.db:
            cur=self.db.execute("""
                INSERT INTO monitor_sessions(pid,started_at) VALUES(?,?)
            """,(os.getpid(),_utc()))
            self.session_id=cur.lastrowid

    def change(self, printers, size_warning_mb=250):
        """Apply only changes: don't write to SSD on every unchanged poll."""
        now=_utc()
        alarms=[]
        with self.db:
            for printer in printers:
                name=printer["name"]
                if printer["error"]:
                    # Never mark jobs as finished if a printer isn't reachable.
                    continue
                seen={j["key"] for j in printer["jobs"]}
                for j in printer["jobs"]:
                    old=self.db.execute(
                        "SELECT * FROM jobs WHERE key=?", (j["key"],)).fetchone()
                    fields=("native_id","document","submitted","owner",
                            "position","pages","total","bytes","state",
                            "detail","color")
                    new=tuple(j[field] for field in fields)
                    if old is None:
                        columns=("key","printer")+fields+("first_seen","last_seen","disappeared")
                        self.db.execute(
                            "INSERT INTO jobs ("+",".join(columns)+") VALUES ("+
                            ",".join("?" for _ in columns)+")",
                            (j["key"],name,*new,now,now,None))
                        self._event(j["key"],now,name,"görüldü",j["state"])
                        if j["state"] in WARNING:
                            alarms.append((name,j["document"],j["state"]))
                    elif any(old[f] != j[f] for f in fields) or old["disappeared"]:
                        self.db.execute("""
                            UPDATE jobs SET native_id=?,document=?,submitted=?,
                            owner=?,position=?,pages=?,total=?,bytes=?,
                            state=?,detail=?,color=?,last_seen=?,
                            disappeared=NULL WHERE key=?
                        """,(*new,now,j["key"]))
                        if old["state"]!=j["state"]:
                            self._event(j["key"],now,name,"durum",
                                        old["state"]+" → "+j["state"])
                            if j["state"] in WARNING:
                                alarms.append((name,j["document"],j["state"]))
                        if int(old["pages"] or 0)!=j["pages"]:
                            self._event(j["key"],now,name,"ilerleme",
                                        "Windows sayacı: "+str(j["pages"]))
                    if j["bytes"] >= int(size_warning_mb)*MIB and (
                            old is None or int(old["bytes"] or 0)<int(size_warning_mb)*MIB):
                        self._event(j["key"],now,name,"büyük_spool",
                                    str(round(j["bytes"]/MIB,1))+" MiB")
                        alarms.append((name,j["document"],"Büyük spool dosyası"))
                # A print job disappearing from a successful queue query
                # isn't proof that a physical sheet was ever delivered.
                old_jobs=self.db.execute(
                    "SELECT key FROM jobs WHERE printer=? AND disappeared IS NULL",
                    (name,)).fetchall()
                for prior in old_jobs:
                    if prior["key"] not in seen:
                        self.db.execute(
                            "UPDATE jobs SET disappeared=?,state=? WHERE key=?",
                            (now,"kuyrukta_yok",prior["key"]))
                        self._event(prior["key"],now,name,"kayboldu",
                                    "Kuyrukta yok; fiziksel bitiş doğrulanamadı")
        return alarms

    def publish_snapshot(self,snapshot):
        """Update one local snapshot only on state change or every minute."""
        meaningful={key:value for key,value in snapshot.items()
                    if key!="captured_at"}
        digest=hashlib.sha256(json.dumps(
            meaningful,ensure_ascii=False,sort_keys=True
        ).encode("utf-8")).hexdigest()
        now_mono=time.monotonic()
        if (digest==getattr(self,"_snapshot_digest",None) and
                now_mono-getattr(self,"_snapshot_written",0)<60):
            return
        payload=json.dumps(snapshot,ensure_ascii=False,separators=(",",":"))
        with self.db:
            self.db.execute("""
                INSERT INTO collector_snapshot(id,payload,captured_at)
                VALUES(1,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    captured_at=excluded.captured_at
            """,(payload,snapshot["captured_at"]))
        self._snapshot_digest=digest
        self._snapshot_written=now_mono

    def _event(self,key,now,printer,kind,detail):
        self.db.execute(
            "INSERT INTO events(job_key,at,printer,kind,detail) VALUES(?,?,?,?,?)",
            (key,now,printer,kind,str(detail)[:240]))

    def recent(self,limit=90):
        rows=self.db.execute("""
            SELECT j.*, l.book AS book_label, l.mode AS mode_label
            FROM jobs j LEFT JOIN labels l ON l.job_key=j.key
            ORDER BY j.first_seen DESC LIMIT ?
        """,(limit,)).fetchall()
        return [dict(row) for row in rows]

    def events(self,limit=25):
        rows=self.db.execute("""
            SELECT * FROM events ORDER BY id DESC LIMIT ?
        """,(limit,)).fetchall()
        return [dict(row) for row in rows]

    def set_label(self,key,book,mode):
        book=str(book or "").strip()[:100]
        if mode not in ("SB","RENK","BELIRSIZ"):
            raise ValueError("Baskı türü geçersiz")
        with self.db:
            self.db.execute("""
                INSERT INTO labels(job_key,book,mode) VALUES(?,?,?)
                ON CONFLICT(job_key) DO UPDATE SET book=excluded.book,mode=excluded.mode
            """,(str(key),book,mode))

    def close(self):
        try:
            with self.db:
                self.db.execute("""
                    UPDATE monitor_sessions SET closed_at=?
                    WHERE session_id=? AND closed_at IS NULL
                """,(_utc(),self.session_id))
        finally:
            self.db.close()


def read_collector_snapshot(data_dir):
    """Read-only data source for an ERP window when agent owns the mutex."""
    path=Path(data_dir)/"print_monitor"/"print_history.sqlite3"
    if not path.is_file():
        return None
    try:
        connection=sqlite3.connect(str(path),timeout=2)
    except sqlite3.Error:
        # Another process may be creating the first WAL database.
        return None
    try:
        connection.execute("PRAGMA query_only=ON")
        row=connection.execute("""
            SELECT payload FROM collector_snapshot WHERE id=1
        """).fetchone()
        if not row:
            return None
        value=json.loads(row[0])
        if not isinstance(value,dict) or "printers" not in value:
            return None
        return value
    except (sqlite3.Error,ValueError,TypeError):
        return None
    finally:
        connection.close()


class PrintMonitor(QThread):
    """Read native printer queues outside the Qt GUI thread."""
    updated=Signal(object)
    warning=Signal(str)
    failed=Signal(str)

    def __init__(self,data_dir,parent=None):
        super().__init__(parent)
        self.data_dir=Path(data_dir)
        self.delay_ms=RECONCILE_MS  # full reconciliation; native events wake early
        self.size_warning_mb=250
        self._job_progress={}  # key -> (page count, spool size, monotonic time)
        self._stale_warned=set()

    def _check_progress(self,printers):
        """Warn on absent Windows counter movement, not 'printer stopped'.

        Some drivers never report pages. The alert deliberately says
        counter unchanged and never claims real pages are stuck.
        """
        observed=set()
        alerts=[]
        moment=time.monotonic()
        for printer in printers:
            if printer["error"]:
                continue
            for job in printer["jobs"]:
                key=job["key"]
                observed.add(key)
                if job["state"] not in ("yazdırılıyor","aktarılıyor"):
                    self._job_progress.pop(key,None)
                    self._stale_warned.discard(key)
                    continue
                progress=(int(job["pages"]),int(job["bytes"]))
                prior=self._job_progress.get(key)
                if prior is None or progress!=prior[:2]:
                    self._job_progress[key]=(progress[0],progress[1],moment)
                    self._stale_warned.discard(key)
                elif moment-prior[2]>240 and key not in self._stale_warned:
                    self._stale_warned.add(key)
                    alerts.append(printer["name"]+": "+job["document"][:75]+
                        " · 4 dk Windows sayacı değişmedi (gerçek baskı kontrol edilmeli)")
        for key in list(self._job_progress):
            if key not in observed:
                self._job_progress.pop(key,None)
                self._stale_warned.discard(key)
        return alerts[:3]

    def run(self):
        journal=None
        planner=None
        feed=None
        lease=None
        try:
            if os.name!="nt":
                self.failed.emit("Windows spooler yalnız Windows cihazlarında çalışır.")
                return
            # The optional login agent or another ERP window may already
            # collect this user's print history. It must be single-writer.
            last_observed=None
            while not self.isInterruptionRequested():
                lease=PrintCollectorLease(self.data_dir)
                if lease.acquired:
                    break
                data=read_collector_snapshot(self.data_dir)
                if data is not None:
                    # A spool status can change more than once per second.
                    # Compare actual snapshot data, not only timestamps.
                    if data!=last_observed:
                        last_observed=data
                        self.updated.emit(data)
                for _ in range(6):
                    if self.isInterruptionRequested():return
                    self.msleep(500)
            if self.isInterruptionRequested():return
            probe=WinSpoolProbe()
            journal=PrintJournal(self.data_dir)
            planner=PrintPlanRepository(self.data_dir)
            # IPP is OPT-IN and has its own bounded rate limiter.
            # Never infer a device IPP job-id from Windows JobId.
            ipp_settings=IppSettings(self.data_dir)
            ipp_reader=IppReader(timeout=2.0)
            ipp_devices={}
            ipp_warnings=[]
            ipp_last_probe=0.0
            ipp_cursor=0
            # Optional SNMPv2c is read-only and explicitly configured per
            # Windows printer; encrypted community never enters snapshots.
            snmp_settings=SnmpSettings(self.data_dir)
            snmp_reader=SnmpReader(timeout=1.0)
            snmp_devices={}
            snmp_cursor=0
            snmp_last=0.0
            snmp_warnings=[]
            # Windows driver and installed Epson/Canon utilities are read
            # only every five minutes, not on each queue event.
            vendor_reader=WinPrinterVendorInventory(probe.api)
            vendor_devices={}
            vendor_tools=[]
            vendor_last=0.0
            try:
                feed=WinPrintChangeFeed(probe)
            except (OSError,AttributeError) as exc:
                # Unsupported spoolers may lack notifications. Periodic
                # read-only reconciliation remains functional.
                self.failed.emit(
                    "Yazıcı olay bildirimleri yok; aralıklı izleme etkin: "+
                    str(exc)[:150])
            first=True
            while not self.isInterruptionRequested():
                try:
                    printers=probe.snapshot()
                    if time.monotonic()-vendor_last>=300:
                        vendor_last=time.monotonic()
                        vendor_devices=vendor_reader.snapshot(
                            [p["name"] for p in printers])
                        vendor_tools=installed_vendor_tools()
                    if feed is not None:
                        feed.sync([item["name"] for item in printers])
                    alarms=journal.change(printers,self.size_warning_mb)
                    # A queue entry vanishing is a review state, not proof
                    # of successful printing or permission to resend.
                    interruptions=planner.reconcile()
                    stale_alerts=self._check_progress(printers)
                    if time.monotonic()-ipp_last_probe>=20:
                        ipp_last_probe=time.monotonic()
                        config=ipp_settings.read()
                        ipp_devices={key:value for key,value in ipp_devices.items()
                                     if key in config}
                        names=list(sorted(config))
                        if names:
                            batch=min(3,len(names))
                            selected=[names[(ipp_cursor+i)%len(names)]
                                      for i in range(batch)]
                            ipp_cursor=(ipp_cursor+batch)%len(names)
                            current_tasks=planner.list(350)
                            for printer_name in selected:
                                uri=config[printer_name]
                                previous=ipp_devices.get(printer_name) or {}
                                try:
                                    info=ipp_reader.printer(uri)
                                    info["error"]=""
                                    ipp_devices[printer_name]=info
                                    if (info["state_code"]==5 and
                                            previous.get("state_code")!=5):
                                        ipp_warnings.append(
                                            printer_name+": IPP cihaz durdu · "+
                                            ", ".join(info["reasons"][:2])[:100])
                                except (IppTelemetryError,OSError) as exc:
                                    # A network outage never rewrites or
                                    # completes old print tasks.
                                    ipp_devices[printer_name]={
                                        "source":"IPP doğrudan cihaz",
                                        "error":str(exc)[:180],
                                        "state":"ulaşılamıyor",
                                        "seen_at":previous.get("seen_at") or "",
                                    }
                                    continue
                                # Reading an IPP job is allowed ONLY after
                                # the operator links its actual device id.
                                linked=[t for t in current_tasks
                                        if t["printer"]==printer_name
                                        and t.get("ipp_job_id") is not None
                                        and t["state"] in ("queued","verify")]
                                for task in linked[:2]:
                                    try:
                                        data=ipp_reader.job(uri,task["ipp_job_id"])
                                        planner.record_ipp_report(
                                            task["task_id"],task["ipp_job_id"],data)
                                    except (IppTelemetryError,OSError):
                                        # Some printers immediately erase
                                        # completed jobs; keep last reading.
                                        continue
                    # Only explicit, private-IP SNMP devices are queried.
                    # At most one device per 30s cycle; timeout is bounded.
                    if time.monotonic()-snmp_last>=30:
                        snmp_last=time.monotonic()
                        devices=snmp_settings.read()
                        snmp_devices={
                            name:data for name,data in snmp_devices.items()
                            if name in devices}
                        names=sorted(devices)
                        if names:
                            name=names[snmp_cursor%len(names)]
                            snmp_cursor+=1
                            item=devices[name]
                            prior=snmp_devices.get(name) or {}
                            try:
                                info=snmp_reader.snapshot(
                                    item["ip"],item["community"])
                                info["error"]=""
                                snmp_devices[name]=info
                                if (prior.get("alerts") is not None
                                    and info.get("alerts")!=prior.get("alerts")
                                    and info.get("alerts")):
                                    snmp_warnings.append(
                                        name+": "+", ".join(info["alerts"][:2])[:120])
                            except (SnmpTelemetryError,OSError) as exc:
                                snmp_devices[name]={
                                    "source":"SNMPv2c · Printer-MIB (yalnız okuma)",
                                    "error":str(exc)[:180],
                                    "status":"erişilemiyor",
                                    "seen_at":prior.get("seen_at") or ""
                                }
                    rows=journal.recent(160)
                    tagged={j["key"]:j for j in rows}
                    for p in printers:
                        for job in p["jobs"]:
                            if job["key"] in tagged:
                                job["book_label"]=tagged[job["key"]].get("book_label") or ""
                                job["mode_label"]=tagged[job["key"]].get("mode_label") or ""
                    snapshot={
                        "printers":printers, "recent":rows,
                        "events":journal.events(25),
                        "tasks":planner.list(300),
                        "ipp":ipp_devices,
                        "snmp":snmp_devices,
                        "vendor":vendor_devices,
                        "vendor_software":vendor_tools,
                        "captured_at":_utc()
                    }
                    journal.publish_snapshot(snapshot)
                    self.updated.emit(snapshot)
                    # Interrupted book tasks are important even on startup:
                    # the PC may have rebooted while a PDF was printing.
                    for notice in ipp_warnings[:3]:
                        self.warning.emit("IPP cihaz uyarısı · "+notice)
                    ipp_warnings.clear()
                    for notice in snmp_warnings[:3]:
                        self.warning.emit("SNMP yazıcı uyarısı · "+notice)
                    snmp_warnings.clear()
                    for item in interruptions[:3]:
                        self.warning.emit(
                            "BASKI KESINTİSİ · "+str(item["book"])[:75]+
                            " · Windows'un son sayacı: "+
                            str(item["windows_counter"])+
                            " · fiziksel PDF sayfasını doğrula / baskı planından devam et")
                    if not first:
                        for printer,document,state in alarms[:3]:
                            self.warning.emit(printer+": "+document[:80]+" · "+state)
                        for alert in stale_alerts:
                            self.warning.emit(alert)
                    first=False
                except (OSError,sqlite3.Error,PrintAccessError) as exc:
                    self.failed.emit(str(exc)[:230])
                if self.isInterruptionRequested():
                    break
                if feed is not None:
                    # Poll fallback protects against missed signals from
                    # offline/shared/driver-specific Windows print queues.
                    budget=(FALLBACK_MS if feed.has_fallback
                            else RECONCILE_MS)
                    try:
                        awakened=feed.wait(self.isInterruptionRequested,budget)
                    except (OSError,RuntimeError,ctypes.ArgumentError) as exc:
                        self.failed.emit(
                            "Windows olay bildirimi kesildi; aralıklı izleme sürecek: "+
                            str(exc)[:160])
                        feed.close()
                        feed=None
                    else:
                        if awakened and not self.isInterruptionRequested():
                            # Combine bursts of SET_JOB/WRITE_JOB notifications
                            # before fetching potentially expensive remote data.
                            self.msleep(450)
                else:
                    for _ in range(FALLBACK_MS//250):
                        if self.isInterruptionRequested():
                            break
                        self.msleep(250)
        finally:
            if feed is not None:
                feed.close()
            if planner is not None:
                planner.close()
            if journal is not None:
                journal.close()
            if lease is not None:
                lease.close()
