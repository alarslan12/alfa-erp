"""Fast cloud change detection and durable background delivery.

Never blocks a Qt button handler with network I/O. All responses are applied
only on the GUI thread; failed writes stay in the encrypted-device's local outbox.
"""
import time
from PySide6.QtCore import QObject, QThread, QTimer, Signal


class Pull(QThread):
    done = Signal(dict)
    failed = Signal(str, int)

    def __init__(self, client, last=None, force=False, parent=None):
        super().__init__(parent)
        self.client, self.last, self.force = client, last, force

    def run(self):
        try:
            # One round trip: validated pulse + only the changed sections.
            payload = self.client.sync(known=None if self.force else self.last)
            pulse = {key:payload[key] for key in
                     ('epoch','orders_revision','catalog_revision','inventory_revision')}
            has_data = any(key in payload for key in
                           ('orders','items','books','inventory_products','accounting_days'))
            self.done.emit({'pulse':pulse,'snapshot':payload if has_data else None})
        except Exception as exc:
            self.failed.emit(str(exc)[:280],int(getattr(exc,'status',0) or 0))


class Push(QThread):
    done = Signal(object)
    failed = Signal(str, int)

    def __init__(self, client, batch, parent=None):
        super().__init__(parent)
        self.client, self.batch = client, batch

    def run(self):
        try:
            if self.batch['kind'] == 'status':
                result = self.client.transition(self.batch['events'])
            elif self.batch['kind'] == 'progress':
                result = self.client.progress(self.batch['events'])
            else:
                result = self.client.commit(self.batch['edits'])
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc)[:280],int(getattr(exc,'status',0) or 0))


class Sync(QObject):
    changed = Signal(list)
    status = Signal(bool, str)

    def __init__(self, client, db, parent=None):
        super().__init__(parent)
        self.client, self.db = client, db
        self.pull_task = None
        self.push_task = None
        self.last_pulse = None
        self.force_pull = True
        self.retry_after = 0
        self._pull_retry_after = 0
        self._consecutive_pull_failures = 0
        self._last_orders_verified = 0
        self._last_pending_count = db.pending_count
        self.current_batch = None
        self.isolate_batch=False
        self._last_status = None
        self.timer = QTimer(self)
        self._recent_until = time.monotonic() + 16
        self._active_poll_ms = 2100 + (id(self) % 350)
        self._idle_poll_ms = 5500 + (id(self) % 950)
        self.timer.setInterval(self._active_poll_ms)
        self.timer.timeout.connect(self.pull)
        self.sender = QTimer(self)
        self.sender.setInterval(350)
        self.sender.timeout.connect(self.push)
        if client.paired:
            db.cloud_api = client
            self.timer.start()
            self.sender.start()
            QTimer.singleShot(100, self.pull)

    def _retune_poll(self):
        # Frequent changes receive fast checks; an idle window is inexpensive.
        interval = (self._active_poll_ms if self.db.pending_count or
                    time.monotonic() < self._recent_until else self._idle_poll_ms)
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)

    def _status(self, online, message):
        state=(online,message)
        if state != self._last_status:
            self._last_status=state
            self.status.emit(online, message)

    def _revision_request(self, now=None):
        """Periodic authoritative order refresh, without re-downloading books.

        Prevents a deleted or edited order being hidden indefinitely when an
        older optimistic outbox action temporarily blocked its application.
        """
        now = time.monotonic() if now is None else now
        if self.last_pulse is None:
            return None, True
        known = dict(self.last_pulse)
        if self.force_pull or now-self._last_orders_verified >= 45:
            known['orders_revision'] = -1
        return known, False

    def pull(self):
        if (not self.client.paired or self.pull_task is not None or
                time.monotonic() < self._pull_retry_after):
            return
        # Outbox work was acknowledged/quarantined: previously skipped cloud
        # tombstones must be re-checked even if the revision did not change.
        if self.db.pending_count < self._last_pending_count:
            self.force_pull = True
        self._last_pending_count = self.db.pending_count
        known,initial=self._revision_request()
        worker=Pull(self.client,known,initial,parent=self)
        self.pull_task=worker

        def finish(payload):
            self.pull_task=None
            try:
                snapshot=payload.get('snapshot')
                if snapshot is not None:
                    changes=self.db.apply_cloud_snapshot(snapshot)
                    if 'orders' in snapshot and 'items' in snapshot:
                        self._last_orders_verified=time.monotonic()
                    if changes:
                        self._recent_until = time.monotonic()+18
                        self.changed.emit(changes)
                    self.force_pull=False
                self.last_pulse=payload['pulse']
                self._consecutive_pull_failures=0
                self._pull_retry_after=0
                self._retune_poll()
                pending=self.db.pending_count
                self._status(True, f'Bulut bağlı · {pending} işlem sırada' if pending else 'Bulut bağlı')
            except Exception as exc:
                self.force_pull=True
                self._consecutive_pull_failures+=1
                self._pull_retry_after=time.monotonic()+min(
                    30,3*self._consecutive_pull_failures)
                self._status(False,'Eşitleme uygulanamadı: '+str(exc)[:170])

        def fail(message,status=0):
            self.pull_task=None
            self.force_pull=True
            self._consecutive_pull_failures+=1
            self._pull_retry_after=time.monotonic()+min(
                30,3*self._consecutive_pull_failures)
            self._retune_poll()
            self._status(False, 'Bulut eşitlemesi beklemede: '+message[:160])
        worker.done.connect(finish)
        worker.failed.connect(fail)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def push(self):
        if not self.client.paired or self.push_task is not None or not self.db.cloud_epoch:
            return
        if not self.db.pending_count or time.monotonic()<self.retry_after:
            return
        if time.monotonic()-self.db._pending_started<0.85:
            return
        batch=self.db.next_outbox_batch(max_events=1 if self.isolate_batch else 30)
        if not batch:return
        worker=Push(self.client,batch,parent=self)
        self.push_task=worker
        self.current_batch=batch

        def finish(results):
            self.push_task=None
            try:
                self.db.confirm_outbox(batch,results)
                self.isolate_batch=False
                self.retry_after=0
                # Server revision changes after each accepted business write.
                # The next delta sync will fetch it without cold-reading books.
                # An order changed on the server. Re-read it regardless of
                # what revision the last concurrent pull might have observed.
                self.force_pull=True
                self._recent_until = time.monotonic()+18
                self._retune_poll()
                self._status(True, f'Bulut bağlı · {self.db.pending_count} işlem sırada'
                    if self.db.pending_count else 'Bulut bağlı')
                QTimer.singleShot(100,self.pull)
            except Exception as exc:
                self.retry_after=time.monotonic()+5
                self._status(False,'Bulut onayı işlenemedi: '+str(exc)[:120])

        def fail(message,status=0):
            self.push_task=None
            self.force_pull=True
            if status in (400,409,413,422):
                # One failing event must not roll back an entire group's work.
                size=len(batch.get('events',batch.get('edits',[])))
                if size>1:
                    self.isolate_batch=True
                    self.retry_after=time.monotonic()+0.2
                    self._status(True,'Bir işlem çakıştı; hareketler tek tek doğrulanıyor')
                    return
                # A stale version/invalid operation is not a network outage.
                # Quarantine a SINGLE poison entry; keep all other work flowing.
                self.db.quarantine_batch(batch,message)
                self.retry_after=time.monotonic()+0.25
                self._status(True,
                    f'{len(self.db._conflicts)} çakışma kayıt altına alındı · '
                    f'{self.db.pending_count} işlem bekliyor')
                QTimer.singleShot(150,self.pull)
                return
            # Network/timeouts/503 and revoked keys are NOT permanent poison
            # actions. Preserve the exact op_id so retries stay idempotent.
            self.retry_after=time.monotonic()+min(45,6+len(self.db._conflicts))
            self._status(False,'Bulut işlemi geçici beklemede: '+
                message[:150]+' · kuyruk korunuyor')
        worker.done.connect(finish)
        worker.failed.connect(fail)
        worker.finished.connect(worker.deleteLater)
        worker.start()
