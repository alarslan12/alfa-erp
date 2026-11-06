"""ALFA ERP: a persistent, local-first book/PDF production plan.

A planned print task is NOT a Windows spool job. Linking the two requires
explicit operator confirmation; disappearance from WinSpool never proves
paper was printed. This module never submits/cancels a printer job or
uploads PDF paths, print names or order data to Firebase.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import uuid


MODES = ("SB", "RENK")
TASK_STATES = ("planned", "queued", "verify", "resumed", "verified", "cancelled")
STATE_NAMES = {
    "planned": "Baskı planında",
    "queued": "Windows kuyruğuyla eşleşti",
    "verify": "Kuyruk kayboldu · fiziksel teyit gerekli",
    "resumed": "Kesilen baskıdan yeni devam planı oluşturuldu",
    "verified": "Operatör fiziksel baskıyı teyit etti",
    "cancelled": "Plan iptal edildi · geçmiş korundu",
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PrintPlanError(ValueError):
    pass


class PrintPlanRepository:
    """One SQLite writer connection per calling thread; WAL for concurrent UI."""

    def __init__(self, data_dir):
        folder = Path(data_dir) / "print_monitor"
        folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(folder / "print_history.sqlite3"), timeout=12)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=12000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS print_tasks (
                task_id TEXT PRIMARY KEY,
                printer TEXT NOT NULL,
                book TEXT NOT NULL,
                book_code TEXT,
                pdf_path TEXT,
                pdf_bytes INTEGER NOT NULL DEFAULT 0,
                pdf_mtime_ns INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL CHECK(mode IN ('SB','RENK')),
                copies INTEGER NOT NULL DEFAULT 1 CHECK(copies BETWEEN 1 AND 100),
                page_start INTEGER NOT NULL DEFAULT 1,
                page_end INTEGER NOT NULL DEFAULT 0,
                sort_index INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'planned',
                linked_job_key TEXT UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                verified_at TEXT,
                note TEXT,
                parent_task_id TEXT,
                confirmed_last_page INTEGER,
                last_reported_pages INTEGER NOT NULL DEFAULT 0,
                last_reported_at TEXT,
                last_job_total INTEGER NOT NULL DEFAULT 0,
                ipp_job_id INTEGER,
                ipp_impressions INTEGER,
                ipp_sheets INTEGER,
                ipp_document_pages INTEGER,
                ipp_state TEXT,
                ipp_job_name TEXT,
                ipp_seen_at TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_print_tasks_queue
                ON print_tasks(printer, state, sort_index);
            CREATE TABLE IF NOT EXISTS print_task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                at TEXT NOT NULL,
                kind TEXT NOT NULL,
                detail TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_print_task_events_task
                ON print_task_events(task_id, id);
        """)
        # Existing v2 draft databases may have been created before the
        # interruption/resume feature. Migrate in place; never drop history.
        names={row["name"] for row in self.db.execute(
            "PRAGMA table_info(print_tasks)").fetchall()}
        migration={
            "parent_task_id":"TEXT",
            "confirmed_last_page":"INTEGER",
            "last_reported_pages":"INTEGER NOT NULL DEFAULT 0",
            "last_reported_at":"TEXT",
            "last_job_total":"INTEGER NOT NULL DEFAULT 0",
            "ipp_job_id":"INTEGER",
            "ipp_impressions":"INTEGER",
            "ipp_sheets":"INTEGER",
            "ipp_document_pages":"INTEGER",
            "ipp_state":"TEXT",
            "ipp_job_name":"TEXT",
            "ipp_seen_at":"TEXT"
        }
        with self.db:
            for column,definition in migration.items():
                if column not in names:
                    self.db.execute(
                        f"ALTER TABLE print_tasks ADD COLUMN {column} {definition}")
            self.db.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_print_resume_once
                ON print_tasks(parent_task_id)
                WHERE parent_task_id IS NOT NULL
            """)
        self.db.commit()

    def _record(self, task_id, kind, detail=""):
        self.db.execute("""
            INSERT INTO print_task_events(task_id, at, kind, detail)
            VALUES(?, ?, ?, ?)
        """, (task_id, _now(), str(kind)[:48], str(detail)[:240]))

    def list(self, limit=200):
        rows = self.db.execute("""
            SELECT * FROM print_tasks
            ORDER BY
                CASE state
                  WHEN 'planned' THEN 0
                  WHEN 'queued' THEN 1
                  WHEN 'verify' THEN 2
                  WHEN 'resumed' THEN 3
                  WHEN 'verified' THEN 4 ELSE 5 END,
                sort_index ASC, created_at DESC
            LIMIT ?
        """, (max(1, min(int(limit), 1000)),)).fetchall()
        return [dict(row) for row in rows]

    def create(self, *, printer, book, mode, copies=1, pdf_path="",
               book_code="", page_start=1, page_end=0):
        printer = str(printer or "").strip()[:250]
        book = str(book or "").strip()[:160]
        book_code = str(book_code or "").strip()[:80]
        if not printer or not book:
            raise PrintPlanError("Yazıcı ve kitap/belge adı zorunludur.")
        if mode not in MODES:
            raise PrintPlanError("Siyah-beyaz veya renkli baskı seçilmeli.")
        copies = int(copies)
        page_start = int(page_start)
        page_end = int(page_end)
        if not 1 <= copies <= 100:
            raise PrintPlanError("Kopya sayısı 1–100 arasında olmalı.")
        if page_start < 1 or (page_end and page_end < page_start):
            raise PrintPlanError("Geçerli bir PDF sayfa aralığı belirtin.")
        if page_start > 100000 or page_end > 100000:
            raise PrintPlanError("PDF sayfa aralığı çok büyük.")
        path = ""
        size = mtime = 0
        if pdf_path:
            source = Path(pdf_path).expanduser()
            if not source.is_file() or source.suffix.lower() != ".pdf":
                raise PrintPlanError("Seçilen yerel PDF dosyası bulunamadı.")
            stat = source.stat()
            path = str(source.resolve())
            size = int(stat.st_size)
            mtime = int(stat.st_mtime_ns)
        task_id = str(uuid.uuid4())
        at = _now()
        with self.db:
            index = self.db.execute(
                "SELECT COALESCE(MAX(sort_index), 0) + 1000 FROM print_tasks"
            ).fetchone()[0]
            self.db.execute("""
                INSERT INTO print_tasks (
                    task_id, printer, book, book_code, pdf_path, pdf_bytes,
                    pdf_mtime_ns, mode, copies, page_start, page_end,
                    sort_index, state, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (task_id, printer, book, book_code, path, size, mtime,
                  mode, copies, page_start, page_end, int(index),
                  "planned", at, at))
            self._record(task_id, "planned",
                         "Yerel baskı planına eklendi; henüz yazıcıya gönderilmedi")
        return task_id

    def _task(self, task_id):
        row = self.db.execute(
            "SELECT * FROM print_tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise PrintPlanError("Baskı planı kaydı bulunamadı.")
        return dict(row)

    def move(self, task_id, direction):
        if direction not in (-1, 1):
            raise PrintPlanError("Sıralama yönü geçersiz.")
        task = self._task(task_id)
        if task["state"] != "planned":
            raise PrintPlanError("Yalnız Windows'a henüz gönderilmeyen işler sıralanabilir.")
        rows = self.db.execute("""
            SELECT task_id,sort_index FROM print_tasks
            WHERE printer=? AND state='planned'
            ORDER BY sort_index,created_at
        """, (task["printer"],)).fetchall()
        index = next((i for i, row in enumerate(rows)
                      if row["task_id"] == task_id), None)
        if index is None or not 0 <= index + direction < len(rows):
            return False
        other = rows[index + direction]
        with self.db:
            self.db.execute(
                "UPDATE print_tasks SET sort_index=?,updated_at=? WHERE task_id=?",
                (other["sort_index"], _now(), task_id))
            self.db.execute(
                "UPDATE print_tasks SET sort_index=?,updated_at=? WHERE task_id=?",
                (task["sort_index"], _now(), other["task_id"]))
            self._record(task_id, "reordered", "Yazıcı baskı planı sırası değişti")
        return True

    def link_job(self, task_id, job_key):
        task = self._task(task_id)
        if task["state"] != "planned":
            raise PrintPlanError("Yalnız planlanan bir iş Windows kuyruğuna bağlanabilir.")
        job = self.db.execute(
            "SELECT key, printer, document, disappeared FROM jobs WHERE key=?",
            (job_key,)
        ).fetchone()
        if job is None or job["disappeared"] is not None:
            raise PrintPlanError("Bu Windows işi canlı kuyrukta bulunamadı.")
        if job["printer"] != task["printer"]:
            raise PrintPlanError("Planlanan yazıcıyla gerçek yazdırma kuyruğu farklı.")
        if self.db.execute(
            "SELECT 1 FROM print_tasks WHERE linked_job_key=?", (job_key,)
        ).fetchone():
            raise PrintPlanError("Windows işi zaten başka bir baskı planına bağlı.")
        with self.db:
            self.db.execute("""
                UPDATE print_tasks SET linked_job_key=?,state='queued',
                    updated_at=? WHERE task_id=? AND state='planned'
            """, (job_key, _now(), task_id))
            self._record(task_id, "linked",
                         "Operatör Windows iş kimliğiyle eşledi: " + job_key)
            # Preserve manual labels that may already have been supplied.
            self.db.execute("""
                INSERT OR IGNORE INTO labels(job_key,book,mode)
                VALUES(?,?,?)
            """, (job_key, task["book"], task["mode"]))
        return True

    def link_ipp_job(self,task_id,ipp_job_id):
        """Operator links a REAL device IPP id (never Windows JobId).

        No inference from a job name or Windows id is permitted.
        """
        try:job_id=int(ipp_job_id)
        except (TypeError,ValueError) as exc:
            raise PrintPlanError("IPP iş numarası sayısal olmalı.") from exc
        if not 1<=job_id<2**31:
            raise PrintPlanError("IPP iş numarası geçersiz.")
        with self.db:
            task=self._task(task_id)
            if task["state"] not in ("queued","verify"):
                raise PrintPlanError(
                    "Önce baskı planını gerçek Windows kuyruğu işiyle eşleştir.")
            existing=self.db.execute("""
                SELECT task_id FROM print_tasks
                WHERE printer=? AND ipp_job_id=? AND task_id!=?
                AND state IN ('queued','verify')
            """,(task["printer"],job_id,task_id)).fetchone()
            if existing:
                raise PrintPlanError(
                    "Bu IPP iş numarası aynı yazıcıda başka aktif baskıya bağlı.")
            if task["ipp_job_id"] is not None:
                if int(task["ipp_job_id"])==job_id:return False
                raise PrintPlanError(
                    "İşin IPP numarası zaten kaydedilmiş; geçmişi "
                    "yanlış eşleşmeden korumak için değiştirilemez.")
            update=self.db.execute("""
                UPDATE print_tasks SET ipp_job_id=?,updated_at=?
                WHERE task_id=? AND ipp_job_id IS NULL
            """,(job_id,_now(),task_id))
            if update.rowcount!=1:
                raise PrintPlanError("IPP bağlantısı başka işlemde değişti.")
            self._record(task_id,"ipp_link",
                         "Operatör IPP cihaz iş numarasını doğruladı: "+
                         str(job_id)+" (Windows JobId değil)")
        return True

    def record_ipp_report(self,task_id,ipp_job_id,report):
        """Persist read-only device readings; never infer a PDF page.

        IPP job-impressions-completed is an impression count, while
        job-media-sheets-completed counts media sheets where supported.
        Neither maps reliably to the last intact physical PDF page.
        """
        with self.db:
            task=self._task(task_id)
            if task["ipp_job_id"] is None or int(task["ipp_job_id"])!=int(ipp_job_id):
                return False
            values={}
            for attr,field in (("impressions","ipp_impressions"),
                               ("sheets","ipp_sheets"),
                               ("document_pages","ipp_document_pages")):
                raw=report.get(attr)
                if isinstance(raw,int) and 0<=raw<2**31:
                    # Some devices reset counters; retain the maximum as
                    # historical observation, not proof of physical pages.
                    previous=task.get(field)
                    values[field]=max(int(previous or 0),raw)
            state=str(report.get("state") or "")[:80]
            name=str(report.get("name") or "")[:120]
            if (all(task.get(k)==v for k,v in values.items()) and
                    task.get("ipp_state")==state and
                    task.get("ipp_job_name")==name):
                return False
            self.db.execute("""
                UPDATE print_tasks SET ipp_impressions=COALESCE(?,ipp_impressions),
                    ipp_sheets=COALESCE(?,ipp_sheets),
                    ipp_document_pages=COALESCE(?,ipp_document_pages),
                    ipp_state=?,ipp_job_name=?,ipp_seen_at=?,updated_at=?
                WHERE task_id=? AND ipp_job_id=?
            """,(values.get("ipp_impressions"),values.get("ipp_sheets"),
                 values.get("ipp_document_pages"),state,name,
                 str(report.get("seen_at") or _now()),
                 _now(),task_id,int(ipp_job_id)))
            self._record(task_id,"ipp_progress",
                "Cihaz bildirimi: "+state+
                "; impressions="+str(values.get("ipp_impressions",
                                               task.get("ipp_impressions")))+
                "; sheets="+str(values.get("ipp_sheets",task.get("ipp_sheets")))+
                "; document pages="+str(values.get("ipp_document_pages",
                                                   task.get("ipp_document_pages")))+
                " (fiziksel son sayfa değil)")
        return True

    def reconcile(self):
        """Persist the last Windows page COUNTER for every linked job.

        The counter may lag, jump, reset or mean sheets rather than PDF
        pages. It is evidence only; never mark the last physical PDF
        page as confirmed from this value.
        """
        interruptions=[]
        with self.db:
            rows=self.db.execute("""
                SELECT t.task_id,t.book,t.linked_job_key,t.last_reported_pages,
                       t.last_reported_at,t.last_job_total,
                       j.key AS observed_key,j.pages,j.total,
                       j.last_seen,j.disappeared
                FROM print_tasks t
                LEFT JOIN jobs j ON j.key=t.linked_job_key
                WHERE t.state='queued'
            """).fetchall()
            for row in rows:
                if row["observed_key"] is None:
                    # No trusted observation; never assume printed.
                    continue
                pages=max(0,int(row["pages"] or 0))
                total=max(0,int(row["total"] or 0))
                # A driver can reset PagesPrinted: retain highest observed
                # as a clue, but it still is NOT guaranteed printed pages.
                highest=max(int(row["last_reported_pages"] or 0),pages)
                stored_total=max(int(row["last_job_total"] or 0),total)
                if (highest!=int(row["last_reported_pages"] or 0)
                    or stored_total!=int(row["last_job_total"] or 0)
                    or not row["last_reported_at"]):
                    self.db.execute("""
                        UPDATE print_tasks SET last_reported_pages=?,
                            last_job_total=?,last_reported_at=?,updated_at=?
                        WHERE task_id=? AND state='queued'
                    """,(highest,stored_total,row["last_seen"],_now(),
                          row["task_id"]))
                    if highest!=int(row["last_reported_pages"] or 0):
                        self._record(row["task_id"],"windows_pages",
                            "Windows son gözlenen sayfa sayacı: "+str(highest)+
                            " (fiziksel çıktı değil)")
                if row["disappeared"] is None:
                    continue
                updated=self.db.execute("""
                    UPDATE print_tasks SET state='verify',updated_at=?
                    WHERE task_id=? AND state='queued'
                """,(_now(),row["task_id"]))
                if updated.rowcount:
                    interruptions.append({
                        "task_id":row["task_id"],
                        "book":row["book"],
                        "windows_counter":highest
                    })
                    self._record(row["task_id"],"verify",
                        "Windows işi kuyruktan çıktı. Son sayaç: "+
                        str(highest)+"; son fiziksel PDF sayfası bilinmiyor")
        return interruptions

    def create_resume(self, task_id, last_confirmed_pdf_page, note):
        """Create ONE safe new continuation plan after manual paper inspection.

        The original queued job must already have disappeared. This method
        never prints a PDF or issues a Windows spooler command.
        """
        note=str(note or "").strip()[:200]
        if not note:
            raise PrintPlanError(
                "Kâğıt çıktısını inceleyip son sağlam PDF sayfasını not etmelisin.")
        confirmed=int(last_confirmed_pdf_page)
        with self.db:
            source=self._task(task_id)
            if source["state"]!="verify":
                raise PrintPlanError(
                    "Devam planı yalnız kuyruktan kaybolmuş ve sonucu "
                    "belirsiz işler için oluşturulur. Önce aktif baskının "
                    "yazıcıda tamamen durduğunu kontrol et.")
            if int(source["copies"])!=1:
                raise PrintPlanError(
                    "Birden çok kopyada son sağlam PDF sayfası her kopya için "
                    "farklı olabilir. Otomatik aralık oluşturulmaz; ayrı "
                    "kopyaların fiziksel sayfalarını kontrol ederek planla.")
            original=source.get("pdf_path")
            if original:
                current=Path(original)
                if not current.is_file():
                    raise PrintPlanError(
                        "Orijinal PDF bulunamadı; aynı kaynak doğrulanmadan "
                        "devam sayfası güvenli değil.")
                stat=current.stat()
                if (int(stat.st_size)!=int(source["pdf_bytes"]) or
                        int(stat.st_mtime_ns)!=int(source["pdf_mtime_ns"])):
                    raise PrintPlanError(
                        "Kaynak PDF değişmiş. Eski PDF ile karşılaştırmadan "
                        "kesilen yerden baskıya devam edilmemeli.")
            if self.db.execute(
                "SELECT 1 FROM print_tasks WHERE parent_task_id=?",
                (task_id,)).fetchone():
                raise PrintPlanError(
                    "Bu kesintiden zaten bir devam planı oluşturulmuş.")
            lower=int(source["page_start"])-1
            upper=int(source["page_end"] or 0)
            if confirmed<lower or (upper and confirmed>upper):
                raise PrintPlanError(
                    "Son sağlam PDF sayfası planlanan sayfa aralığı dışında.")
            if upper and confirmed==upper:
                raise PrintPlanError(
                    "Bütün planlanan sayfalar çıktıysa baskıyı fiziksel "
                    "olarak teyit et; yeni devam planı gerekmiyor.")
            new_start=confirmed+1
            new_id=str(uuid.uuid4())
            now=_now()
            order=int(self.db.execute(
                "SELECT COALESCE(MAX(sort_index),0)+1000 FROM print_tasks"
            ).fetchone()[0])
            # All information is copied as metadata, not PDF contents.
            self.db.execute("""
                INSERT INTO print_tasks(
                    task_id,printer,book,book_code,pdf_path,pdf_bytes,
                    pdf_mtime_ns,mode,copies,page_start,page_end,
                    sort_index,state,created_at,updated_at,parent_task_id,
                    confirmed_last_page,note
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(new_id,source["printer"],source["book"],source["book_code"],
                 source["pdf_path"],source["pdf_bytes"],
                 source["pdf_mtime_ns"],source["mode"],source["copies"],
                 new_start,source["page_end"],order,"planned",now,now,
                 task_id,confirmed,note))
            updated=self.db.execute("""
                UPDATE print_tasks SET state='resumed',
                    confirmed_last_page=?,note=?,updated_at=?
                WHERE task_id=? AND state='verify'
            """,(confirmed,note,now,task_id))
            if updated.rowcount!=1:
                raise PrintPlanError("Kesilen baskı başka cihazda değiştirildi.")
            self._record(task_id,"resume_verified",
                "Son sağlam PDF sayfası: "+str(confirmed)+
                "; operatör teyidi: "+note)
            self._record(new_id,"resume_created",
                "Önceki iş: "+task_id+"; PDF başlangıç sayfası: "+str(new_start)+
                "; otomatik yazdırma YOK")
        return {"task_id":new_id,"resume_from":new_start}


    def verify(self, task_id, note):
        task = self._task(task_id)
        if task["state"] not in ("queued", "verify"):
            raise PrintPlanError(
                "Fiziksel baskı yalnız yazıcıya bağlanmış bir işte doğrulanabilir.")
        note = str(note or "").strip()[:200]
        if not note:
            raise PrintPlanError("Fiziksel baskı kontrol notu gerekli.")
        with self.db:
            result = self.db.execute("""
                UPDATE print_tasks SET state='verified',verified_at=?,
                    updated_at=?,note=? WHERE task_id=? AND
                    state IN ('queued','verify')
            """, (_now(), _now(), note, task_id))
            if result.rowcount != 1:
                raise PrintPlanError("Baskı işi başka bir işlemde değişti.")
            self._record(task_id, "verified",
                         "Operatör fiziksel baskıyı teyit etti: " + note)
        return True

    def cancel_plan(self, task_id, reason):
        task = self._task(task_id)
        if task["state"] != "planned":
            raise PrintPlanError(
                "Yalnız Windows'a henüz bağlanmamış planlar iptal edilebilir. "
                "Spool'daki işi ayrıca Windows kuyruğundan kontrol edin.")
        reason = str(reason or "").strip()[:200]
        if not reason:
            raise PrintPlanError("Plan iptal nedeni gerekli.")
        with self.db:
            result = self.db.execute("""
                UPDATE print_tasks SET state='cancelled',note=?,updated_at=?
                WHERE task_id=? AND state='planned'
            """, (reason, _now(), task_id))
            if result.rowcount != 1:
                raise PrintPlanError("Plan başka bir işlemde değişti.")
            self._record(task_id, "cancelled",
                         "Yalnız plan iptal edildi; Windows spooler değiştirilmedi: "+reason)
        return True

    def task_events(self, task_id, limit=60):
        rows = self.db.execute("""
            SELECT at,kind,detail FROM print_task_events
            WHERE task_id=? ORDER BY id DESC LIMIT ?
        """, (task_id, max(1,min(200,int(limit))))).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self.db.close()
