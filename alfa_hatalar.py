"""Event-only ALFA ERP crash reports; no telemetry timer, no customer content.

Only sanitized exception TYPE and Python module/function/line locations are
transmitted. No exception messages, arbitrary stack locals, customer data,
Windows paths, tokens, SQL or order payloads are uploaded. Files queue
locally until an approved Firebase device can send them. Workers block on
an in-memory Queue (not a network polling loop).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import socket
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from uuid import uuid4

MAX_PENDING=30
MAX_FRAMES=12
MAX_FRAME_LEN=112
MIN_REPEAT_SECONDS=300
SEND_TIMEOUT_SECONDS=15

REPORTER=None


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _folder():
    local=os.environ.get("ALFA_ERP_DATA_DIR") or (
        Path(os.environ.get("LOCALAPPDATA") or
             Path.home()/".local"/"share")/"AlfaERP")
    return Path(local)/"logs"/"pending_reports"


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".alfa_error_",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(value,out,ensure_ascii=False,sort_keys=True)
        os.replace(name,path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _name(value):
    return re.sub(r"[^a-zA-Z0-9_.-]","_",str(value or ""))[:76]


def _frames(tb):
    out=[]
    for item in traceback.extract_tb(tb)[-MAX_FRAMES:] if tb else []:
        # Filename BASENAME only, no arguments, no source-code snippet.
        out.append({"file":_name(Path(item.filename).name),
                    "function":_name(item.name),
                    "line":max(0,min(999999,int(item.lineno)))})
    return out


class ErrorReporter:
    """One daemon sender for on-error uploads, backed by a small local queue."""

    def __init__(self,version,edition,device_provider=None,data_dir=None):
        self.version=str(version)[:20]
        self.edition="owner" if edition=="owner" else "staff"
        self.device_provider=device_provider or (lambda:None)
        self.directory=Path(data_dir)/"logs"/"pending_reports" if data_dir else _folder()
        self.queue=queue.Queue()
        self._last={}
        self._lock=threading.RLock()
        self._started=False
        self._worker=None
        self._shutting_down=False

    def set_device_provider(self,provider):
        self.device_provider=provider
        self.flush_pending_once()

    def start(self):
        with self._lock:
            if self._started:return
            self._started=True
            self._worker=threading.Thread(target=self._sender,daemon=True,
                         name="alfa-error-event-sender")
            self._worker.start()

    def _add(self,event):
        self.directory.mkdir(parents=True,exist_ok=True)
        files=sorted(self.directory.glob("error_*.json"))
        # Never overwrite unsubmitted reports; bound retained disk usage.
        if len(files)>=MAX_PENDING:
            return False
        target=self.directory/("error_"+event["id"]+".json")
        _atomic_json(target,event)
        self.start()
        # A real error event wakes the oldest pending report. Successful
        # uploads drain the queue one-by-one; no timer or network polling.
        pending=next(iter(sorted(self.directory.glob("error_*.json"))),None)
        if pending is not None:
            self.queue.put(str(pending))
        return True

    def report(self,error_type,error,tb,source="application"):
        """Called only by Python/Qt exception hooks, never on a timer."""
        try:
            frames=_frames(tb)
            kind=_name(getattr(error_type,"__name__","Exception"))
            # Fingerprint intentionally excludes the exception message.
            signature=json.dumps([kind,frames[-4:]],sort_keys=True)
            fingerprint=hashlib.sha256(signature.encode()).hexdigest()[:20]
            now=time.monotonic()
            with self._lock:
                if now-self._last.get(fingerprint,-1e15)<MIN_REPEAT_SECONDS:
                    return False
                self._last[fingerprint]=now
            event={
                "id":datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+
                     "_"+str(uuid4()),
                "created_at":_utc_now(),"device_id":"",
                "device_name":_name(socket.gethostname())[:80],
                "edition":self.edition,"version":self.version,
                "type":kind,"source":_name(source)[:30],
                "fingerprint":fingerprint,"frames":frames,
            }
            return self._add(event)
        except Exception:
            # Reporting must never throw or obscure the original error.
            return False

    def report_recovered_native_crash(self):
        """Detect appended faulthandler output after last application launch.

        Uploads only the fact that a native crash was recorded, not its text.
        """
        try:
            logs=self.directory.parent
            raw=logs/"fatal_error.log"
            marker=logs/"fatal_error_reported.json"
            size=raw.stat().st_size if raw.is_file() else 0
            if marker.exists():
                recorded=json.loads(marker.read_text(encoding="utf-8"))
                old=int(recorded.get("size",0))
            else:
                old=size  # Initial install: do not send old historical logs.
            if size>old:
                self.report(type("NativeCrash",(Exception,),{}),None,None,
                            source="previous_native_crash")
            _atomic_json(marker,{"size":size})
        except (OSError,ValueError,TypeError):
            pass

    def flush_pending_once(self):
        """Triggered at application startup/device pairing, never periodically."""
        self.start()
        try:
            # Probe once on startup/pairing. If offline, do not issue another
            # network request for every saved report in the same outage.
            item=next(iter(sorted(self.directory.glob("error_*.json"))),None)
            if item is not None:
                self.queue.put(str(item))
        except OSError:
            pass

    def _sender(self):
        while not self._shutting_down:
            path_text=self.queue.get()  # no repeated requests while idle
            if path_text is None:break
            try:
                path=Path(path_text)
                if not path.is_file():continue
                data=json.loads(path.read_text(encoding="utf-8"))
                client=self.device_provider()
                if client is None or not getattr(client,"paired",False):
                    continue  # stays on disk until next real event/pairing
                data["device_id"]=str(client.uid)
                client.send_error_report(data,timeout=SEND_TIMEOUT_SECONDS)
                path.unlink(missing_ok=True)
                # After an acknowledged upload, continue with the next saved
                # report. A failure leaves the rest on disk until a real event.
                pending=next(iter(sorted(self.directory.glob("error_*.json"))),None)
                if pending is not None:
                    self.queue.put(str(pending))
            except Exception:
                # A rejected rule or offline device never drops the report.
                # No timed retry: next error/start/pairing triggers a new try.
                pass

    def stop(self):
        self._shutting_down=True
        self.queue.put(None)


def install_reporter(version,edition,data_dir=None):
    global REPORTER
    if REPORTER is None:
        REPORTER=ErrorReporter(version,edition,data_dir=data_dir)
        REPORTER.start()
        REPORTER.report_recovered_native_crash()
        REPORTER.flush_pending_once()
    return REPORTER


def record_error(error_type,error,tb,source="application"):
    if REPORTER:
        return bool(REPORTER.report(error_type,error,tb,source))
    return False


def report_manual_error(category):
    """User-initiated report, with only a vetted category and no free text.

    This preserves RTDB's existing strict 10-field report schema and never
    uploads customer details, order identifiers or local exception messages.
    """
    kinds={
        'orders':'ManualOrderReport',
        'inventory':'ManualInventoryReport',
        'sync':'ManualSyncReport',
        'theme':'ManualThemeReport',
        'other':'ManualOtherReport',
    }
    kind=kinds.get(str(category))
    if not kind:return False
    return record_error(type(kind,(RuntimeError,),{}),None,None,source='manual')


def connect_device(provider):
    if REPORTER:
        REPORTER.set_device_provider(provider)

def record_operational_error(category,status=0):
    """Report a significant business sync failure without its message/payload."""
    category=_name(category)
    try:code=max(0,min(999,int(status)))
    except (ValueError,TypeError):code=0
    name="Cloud"+category+"Error"+str(code)
    cls=type(name,(RuntimeError,),{})
    record_error(cls,None,None,source="sync")
