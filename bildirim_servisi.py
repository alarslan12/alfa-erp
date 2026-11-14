"""Persistent Firebase order tray agent, independent of the ERP main window.

Windows Task Scheduler starts this EXE in the currently signed-in user's
interactive desktop session. Single-instance QLockFile prevents duplicates.
No cloud write, API token or service-account key is embedded in the setup.
"""
import sys,json,os
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QThread,Signal,Slot,Qt,QLockFile
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QLabel,QPushButton
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor,QFont,QAction
from cihaz_sifreleme import DATA
from alfa_rtdb import Workstation
from bildirim_sesleri import configured_sound,play_order_sound
from alfa_hatalar import install_reporter,record_error,connect_device
from bulut_canli import RtdbWatch
from ayar_yonetimi import UserSettings
from bildirim_durumu import classify_new_orders

STATE=DATA/'alfa_bildirim_durumu.json'


class Reader(QThread):
    done=Signal(dict)
    error=Signal(str)
    def __init__(self,client,last_revision=None,last_number=0):
        super().__init__()
        self.client=client
        self.last_revision=last_revision
        self.last_number=last_number

    def run(self):
        try:
            data=self.client.sync(
                known=self.last_revision,notification=True,
                last_order_number=self.last_number)
            pulse={k:data[k] for k in
                   ('epoch','orders_revision','catalog_revision','inventory_revision')}
            self.done.emit({'pulse':pulse,'orders':data.get('orders_brief')})
        except Exception as exc:
            self.error.emit(str(exc)[:200])


class Popup(QDialog):
    def __init__(self,numbers):
        super().__init__()
        self.setObjectName('OrderArrivedPopup')
        self.setWindowTitle('ALFA ERP · Yeni Sipariş')
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.resize(370,175)
        theme=UserSettings(DATA).get('tema','koyu')
        if theme=='acik':
            bg,fg,muted,button_bg,edge='#fffaf2','#253d55','#556b80','#dce9f2','#bfaf98'
        elif theme=='kontrast':
            bg,fg,muted,button_bg,edge='#080d13','#ffffff','#e6f5ff','#21486b','#91adcb'
        else:
            bg,fg,muted,button_bg,edge='#14263b','#f5f9ff','#c8dded','#244b6d','#567e9d'
        self.setStyleSheet(f"""
            QDialog#OrderArrivedPopup {{background:{bg};color:{fg};
                border:1px solid {edge};}}
            QLabel#OrderArrivedTitle {{color:{fg};font-size:18px;
                font-weight:850;background:transparent;}}
            QLabel#OrderArrivedBody {{color:{muted};font-size:13px;
                background:transparent;}}
            QPushButton {{background:{button_bg};color:{fg};
                border:1px solid {edge};border-radius:7px;padding:8px;}}
        """)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(17,16,17,14)
        title=QLabel('Yeni sipariş geldi!')
        title.setObjectName('OrderArrivedTitle')
        layout.addWidget(title)
        content=QLabel(numbers)
        content.setObjectName('OrderArrivedBody')
        content.setWordWrap(True)
        layout.addWidget(content)
        close=QPushButton('Kapat')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        QTimer.singleShot(14000,self.close)


def icon():
    pix=QPixmap(64,64)
    pix.fill(QColor('#23345b'))
    p=QPainter(pix)
    p.setPen(QColor('white'))
    font=QFont('Segoe UI',34)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,'A')
    p.end()
    return QIcon(pix)


class Service(QObject):
    def __init__(self,app):
        super().__init__(app)
        self.client=Workstation()
        connect_device(lambda:self.client)
        self.tray=QSystemTrayIcon(icon(),app)
        self.tray.setToolTip('ALFA ERP · Sipariş bildirimleri')
        menu=QMenu()
        self.quit_item=QAction('Bildiriciyi kapat',menu)
        self.quit_item.triggered.connect(app.quit)
        menu.addAction(self.quit_item)
        menu.addAction('Yeni siparişleri kontrol et',self.poll)
        self.tray.setContextMenu(menu)
        self.tray.show()
        try:
            state=json.loads(STATE.read_text(encoding='utf-8'))
            if not isinstance(state,dict):raise ValueError("invalid state")
        except (OSError,ValueError,TypeError):
            state={}
        self.state={
            'initialized':bool(state.get('initialized') or
                               state.get('last_order_number') or
                               state.get('epoch')),
            'last_order_number':max(0,int(state.get('last_order_number') or 0)),
            'epoch':str(state.get('epoch') or '')
        }
        self.seen=set(state['seen']) if isinstance(state.get('seen'),list) else None
        self.worker=None
        self.popup=None
        self.last_revision=None
        self._refresh_pending=False
        self._consecutive_failures=0
        self._normal_poll_ms=20000+(id(self)%4000)
        self.timer=QTimer(self)
        self.timer.setInterval(self._normal_poll_ms)
        self.timer.timeout.connect(self.poll)
        self._watchers=[]
        app.aboutToQuit.connect(self._stop_watchers)
        self.timer.start()
        QTimer.singleShot(650,self.poll)
        if self.client.paired:
            self._start_watchers()
        else:
            self.tray.setToolTip('ALFA ERP · Firebase cihaz onayı bekleniyor')

    def _start_watchers(self):
        if self._watchers or not self.client.paired:
            return
        for location in ("meta/revisions","checkout"):
            watcher=RtdbWatch(self.client,location)
            watcher.changed.connect(self._watch_changed)
            watcher.start()
            self._watchers.append(watcher)

    @Slot()
    def _watch_changed(self):
        # Queued to the tray agent's GUI thread; never mutate timers in SSE
        # worker threads (previously a thread-unsafe lambda did this).
        if self.worker is not None:
            self._refresh_pending=True
            return
        QTimer.singleShot(120,self.poll)

    @Slot()
    def _stop_watchers(self):
        self.timer.stop()
        for watcher in self._watchers:
            watcher.stop()
        self._watchers.clear()

    @Slot()
    def poll(self):
        if not self.client.paired:
            self.client=Workstation()
            if self.client.paired:
                self._start_watchers()
        if not self.client.paired:
            return
        if self.worker is not None:
            self._refresh_pending=True
            return
        work=Reader(self.client,self.last_revision,self.state['last_order_number'])
        self.worker=work
        work.done.connect(self._read_done)
        work.error.connect(self._read_failed)
        work.finished.connect(self._reader_finished)
        work.finished.connect(work.deleteLater)
        work.start()

    @Slot(dict)
    def _read_done(self,result):
        self._consecutive_failures=0
        if self.timer.interval()!=self._normal_poll_ms:
            self.timer.setInterval(self._normal_poll_ms)
        try:
            self.last_revision=result["pulse"]
            rows=result.get("orders")
            if rows is None:
                return
            fresh,new_state=classify_new_orders(
                self.state,rows,str(self.last_revision.get("epoch") or ""),
                legacy_seen=self.seen)
            # Preserve the legacy migration and repair missing state, but
            # avoid rewriting an unchanged watermark on routine refreshes.
            if new_state!=self.state or self.seen is not None or not STATE.is_file():
                DATA.mkdir(parents=True,exist_ok=True)
                staged=STATE.with_suffix(".tmp")
                staged.write_text(json.dumps(new_state),encoding="utf-8")
                os.replace(staged,STATE)
            self.state=new_state
            self.seen=None
            self.tray.setToolTip('ALFA ERP · Firebase bildirimleri aktif')
            if fresh:
                numbers=[str(x.get("order_number")) for x in fresh]
                self.notify(', '.join('#'+n for n in numbers[:5]),len(fresh))
        except (OSError,TypeError,ValueError,KeyError):
            self.tray.setToolTip('ALFA ERP · Bildirim durumu kaydedilemedi')

    @Slot(str)
    def _read_failed(self,message):
        self._consecutive_failures+=1
        self.timer.setInterval(min(180000,10000*(2**min(self._consecutive_failures-1,4))))
        self.tray.setToolTip('ALFA ERP · Firebase: '+str(message)[:65])

    @Slot()
    def _reader_finished(self):
        self.worker=None
        if self._refresh_pending:
            self._refresh_pending=False
            QTimer.singleShot(200,self.poll)

    def notify(self,numbers,count):
        caption=f'{count} yeni sipariş · {numbers}'
        self.tray.showMessage('ALFA ERP · Yeni Sipariş',caption,
                              QSystemTrayIcon.MessageIcon.Information,12000)
        play_order_sound(configured_sound(DATA),DATA)
        if self.popup:
            self.popup.close()
        self.popup=Popup(caption)
        self.popup.show()


def main():
    DATA.mkdir(parents=True,exist_ok=True)
    install_reporter("2.0.32","staff",data_dir=DATA)
    def _error_hook(error_type,error,tb):
        record_error(error_type,error,tb,source="tray")
    sys.excepthook=_error_hook
    lock=QLockFile(str(DATA/'alfa_bildirim.lock'))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        return 0
    app=QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    service=Service(app)
    app._service=service
    return app.exec()


if __name__=="__main__":
    sys.exit(main())
