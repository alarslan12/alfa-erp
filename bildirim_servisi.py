"""Windows sign-in tray notification agent, independent from the main ERP window."""
import sys,json,os
from pathlib import Path
from PySide6.QtCore import QTimer,QThread,Signal,Qt,QLockFile
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QLabel,QPushButton
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor,QFont,QAction
from alfa_cihaz import DATA
from alfa_rtdb import Workstation
from bildirim_sesleri import configured_sound,play_order_sound
from alfa_hatalar import install_reporter,record_error,connect_device
from bulut_canli import RtdbWatch
from ayar_yonetimi import UserSettings
STATE=DATA/'alfa_bildirim_durumu.json'
class Reader(QThread):
    done=Signal(dict);error=Signal(str)
    def __init__(self,client,last_revision=None,last_number=0):
        super().__init__()
        self.client=client;self.last_revision=last_revision;self.last_number=last_number
    def run(self):
        try:
            data=self.client.sync(known=self.last_revision,
                notification=True,last_order_number=self.last_number)
            pulse={k:data[k] for k in
                   ('epoch','orders_revision','catalog_revision','inventory_revision')}
            self.done.emit({'pulse':pulse,'orders':data.get('orders_brief')})
        except Exception as exc:self.error.emit(str(exc)[:200])
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
        layout=QVBoxLayout(self);layout.setContentsMargins(17,16,17,14)
        title=QLabel('Yeni sipariş geldi!');title.setObjectName('OrderArrivedTitle')
        layout.addWidget(title)
        content=QLabel(numbers);content.setObjectName('OrderArrivedBody')
        content.setWordWrap(True);layout.addWidget(content)
        close=QPushButton('Kapat');close.clicked.connect(self.close);layout.addWidget(close)
        QTimer.singleShot(14000,self.close)
def icon():
    pix=QPixmap(64,64);pix.fill(QColor('#23345b'))
    p=QPainter(pix);p.setPen(QColor('white'));font=QFont('Segoe UI',34);font.setBold(True);p.setFont(font)
    p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,'A');p.end();return QIcon(pix)
class Service:
    def __init__(self,app):
        self.client=Workstation()
        connect_device(lambda:self.client)
        self.tray=QSystemTrayIcon(icon(),app)
        self.tray.setToolTip('ALFA ERP · Sipariş bildirimleri')
        menu=QMenu();quit_item=QAction('Bildiriciyi kapat',menu);quit_item.triggered.connect(app.quit)
        menu.addAction(quit_item);self.tray.setContextMenu(menu);self.tray.show()
        try:
            state=json.loads(STATE.read_text(encoding='utf-8'))
            self.seen=set(state['seen']) if 'seen' in state else None
            self.last_order_number=max(0,int(state.get('last_order_number') or 0))
            self.last_epoch=str(state.get('epoch') or '')
        except (OSError,ValueError,KeyError,TypeError):
            self.seen=None;self.last_order_number=0;self.last_epoch=''
        self.worker=None;self.popup=None;self.last_revision=None
        self._consecutive_failures=0
        self._normal_poll_ms=45000+(id(self)%10000)
        # Notifications need new order numbers, not full books/inventory snapshots.
        self.timer=QTimer();self.timer.setInterval(self._normal_poll_ms);self.timer.timeout.connect(self.poll)
        self._watchers=[]
        self.timer.start();QTimer.singleShot(500,self.poll)
        if self.client.paired:self._start_watchers()

    def _start_watchers(self):
        if self._watchers or not self.client.paired:return
        for location in ("meta/revisions","checkout"):
            watcher=RtdbWatch(self.client,location)
            watcher.changed.connect(lambda:QTimer.singleShot(100,self.poll))
            watcher.start()
            self._watchers.append(watcher)
        app=QApplication.instance()
        if app:app.aboutToQuit.connect(self._stop_watchers)

    def _stop_watchers(self):
        for watcher in self._watchers:watcher.stop()

    def poll(self):
        if not self.client.paired:self.client=Workstation()
        if self.client.paired:self._start_watchers()
        if not self.client.paired or self.worker:return
        work=Reader(self.client,self.last_revision,self.last_order_number);self.worker=work
        def success(result):
            self.worker=None
            self._consecutive_failures=0
            if self.timer.interval()!=self._normal_poll_ms:
                self.timer.setInterval(self._normal_poll_ms)
            try:
                self.last_revision=result['pulse']
                rows=result.get('orders')
                if rows is None:return
                epoch=str(self.last_revision.get('epoch') or '')
                reset=bool(self.last_epoch and epoch!=self.last_epoch)
                if reset:
                    # A cloud reset reuses order numbers: do not announce old data.
                    self.last_order_number=0
                    self.seen=None
                if self.last_order_number:
                    fresh=[o for o in rows if int(o.get('order_number') or 0)>self.last_order_number]
                elif self.seen is not None and not reset:
                    fresh=[o for o in rows if str(o.get('id')) not in self.seen]
                else:
                    fresh=[]  # Initial pairing does not notify historical orders.
                self.last_order_number=max([self.last_order_number]+
                    [int(o.get('order_number') or 0) for o in rows])
                self.last_epoch=epoch
                self.seen=None  # Compact the legacy seen-UUID file on migration.
                DATA.mkdir(parents=True,exist_ok=True)
                staged=STATE.with_suffix('.tmp')
                staged.write_text(json.dumps({'last_order_number':self.last_order_number,
                    'epoch':epoch}),encoding='utf-8')
                os.replace(staged,STATE)
                if fresh:
                    numbers=[str(x.get('order_number')) for x in fresh]
                    self.notify(', '.join('#'+n for n in numbers[:5]),len(fresh))
            except (OSError,ValueError,TypeError,KeyError):pass
        def fail(message):
            self.worker=None
            self._consecutive_failures+=1
            self.timer.setInterval(min(600000,60000*(2**min(self._consecutive_failures-1,4))))
            self.tray.setToolTip('ALFA ERP · '+message[:60])
        work.done.connect(success);work.error.connect(fail);work.finished.connect(work.deleteLater);work.start()
    def notify(self,numbers,count):
        caption=f'{count} yeni sipariş · {numbers}'
        self.tray.showMessage('ALFA ERP · Yeni Sipariş',caption,QSystemTrayIcon.MessageIcon.Information,12000)
        # Reread the saved preference on every genuine new order so changing
        # the tone in either desktop app takes effect without restarting tray.
        play_order_sound(configured_sound(DATA),DATA)
        if self.popup:self.popup.close()
        self.popup=Popup(caption);self.popup.show()
def main():
    DATA.mkdir(parents=True,exist_ok=True)
    install_reporter("1.1.0","staff",data_dir=DATA)
    def _error_hook(error_type,error,tb):
        record_error(error_type,error,tb,source="tray")
    sys.excepthook=_error_hook
    lock=QLockFile(str(DATA/'alfa_bildirim.lock'));lock.setStaleLockTime(30000)
    if not lock.tryLock(100):return 0
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    service=Service(app);app._service=service
    return app.exec()
if __name__=='__main__':sys.exit(main())
