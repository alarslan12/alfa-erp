"""Alfa ERP mobile-to-local inbox: ordinary Sipariş Havuzu, no separate cloud menu."""
from PySide6.QtCore import QObject, QThread, QTimer, Signal


class _DownloadInbox(QThread):
    completed = Signal(list, list)
    failed = Signal(str)

    def __init__(self, client, workspace_id, known, parent=None):
        super().__init__(parent)
        self.client = client
        self.workspace_id = str(workspace_id)
        self.known = set(known)

    def run(self):
        try:
            rows = self.client.list_mobile_inbox_orders(self.workspace_id)
            result = []
            warnings = []
            for order in rows:
                uid = str(order.get('id', '')).strip()
                if not uid or uid in self.known:
                    continue
                try:
                    items = self.client.list_cloud_items(self.workspace_id, uid)
                except Exception as exc:
                    # One remote order must not prevent the others from arriving.
                    warnings.append('Sipariş ' + uid[:12] + ': ' + str(exc)[:160])
                    continue
                result.append((order, items))
            self.completed.emit(result, warnings)
        except Exception as exc:
            self.failed.emit(str(exc)[:320])


class CloudInboxSynchronizer(QObject):
    new_orders = Signal(list)
    sync_error = Signal(str)

    def __init__(self, client, db, parent=None):
        super().__init__(parent)
        self.client = client
        self.db = db
        self._workspace = None
        self._task = None
        self._timer = QTimer(self)
        self._timer.setInterval(20000)
        self._timer.timeout.connect(self.sync_now)

    def configure(self, status):
        if not isinstance(status, dict):
            status = {}
        workspace = str(status.get('workspace_id')) if status.get('access') else None
        if not self.client.logged_in or not workspace:
            self._workspace = None
            self._timer.stop()
            return
        self._workspace = workspace
        self._timer.start()
        self.sync_now()

    def sync_now(self):
        if not self._workspace or not self.client.logged_in:
            return
        if self._task is not None:
            return
        try:
            known = self.db.bulut_bilinen_kayitlar()
        except Exception as exc:
            self.sync_error.emit('Gelen kayıt kontrolü başarısız: ' + str(exc)[:200])
            return
        task = _DownloadInbox(self.client, self._workspace, known, self)
        self._task = task
        def ok(rows, warnings):
            self._task = None
            if not self.client.logged_in or self._workspace != task.workspace_id:
                return
            try:
                ids = self.db.bulut_siparislerini_havuza_al(rows, errors=warnings)
            except Exception as exc:
                self.sync_error.emit(str(exc)[:320])
            else:
                if ids:
                    self.new_orders.emit(ids)
                if warnings:
                    self.sync_error.emit(
                        str(len(warnings)) + ' sipariş aktarılamadı. ' + warnings[0][:250])
        def fail(message):
            self._task = None
            self.sync_error.emit(message)
        task.completed.connect(ok)
        task.failed.connect(fail)
        task.finished.connect(task.deleteLater)
        task.start()
