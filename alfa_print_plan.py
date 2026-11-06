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
TASK_STATES = ("planned", "queued", "verify", "verified", "cancelled")
STATE_NAMES = {
    "planned": "Baskı planında",
    "queued": "Windows kuyruğuyla eşleşti",
    "verify": "Kuyruk kayboldu · fiziksel teyit gerekli",
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
                note TEXT
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
                  WHEN 'verified' THEN 3 ELSE 4 END,
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

    def reconcile(self):
        """After journal.change(), identify missing jobs without auto-reprinting.

        Only a successful Windows queue snapshot marks a job disappeared
        in jobs.disappeared. Unreachable printers remain uncertain.
        """
        changed = 0
        with self.db:
            rows = self.db.execute("""
                SELECT t.task_id, t.linked_job_key, j.disappeared
                FROM print_tasks t
                LEFT JOIN jobs j ON j.key=t.linked_job_key
                WHERE t.state='queued'
            """).fetchall()
            for row in rows:
                if row["disappeared"] is None:
                    continue
                changed += self.db.execute("""
                    UPDATE print_tasks SET state='verify',updated_at=?
                    WHERE task_id=? AND state='queued'
                """, (_now(), row["task_id"])).rowcount
                self._record(row["task_id"], "verify",
                             "Windows işi kuyruktan çıktı; fiziksel baskı belirsiz")
        return changed

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
