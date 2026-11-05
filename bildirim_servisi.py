"""Windows sign-in tray notification agent, independent from the main ERP window."""
import sys,json,os
from pathlib import Path
from PySide6.QtCore import QTimer,QThread,Signal,Qt,QLockFile
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QLabel,QPushButton
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor,QFont,QAction
from alfa_cihaz import DATA
from alfa_rtdb import Workstation
from bulut_canli import RtdbWatch
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
        super().__init__();self.setWindowTitle('ALFA ERP · Yeni Sipariş')
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.resize(350,150);layout=QVBoxLayout(self)
        title=QLabel('Yeni sipariş geldi!');title.setStyleSheet('font-size:18px;font-weight:bold')
        layout.addWidget(title);content=QLabel(numbers);content.setWordWrap(True);layout.addWidget(content)
        button=QPushButton('Kapat');button.clicked.connect(self.close);layout.addWidget(button)
        QTimer.singleShot(14000,self.close)
def icon():
    pix=QPixmap(64,64);pix.fill(QColor('#23345b'))
    p=QPainter(pix);p.setPen(QColor('white'));font=QFont('Segoe UI',34);font.setBold(True);p.setFont(font)
    p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,'A');p.end();return QIcon(pix)
class Service:
    def __init__(self,app):
        self.client=Workstation();self.tray=QSystemTrayIcon(icon(),app)
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
        try:
            import winsound
            winsound.PlaySound('SystemExclamation',winsound.SND_ALIAS|winsound.SND_ASYNC)
        except (ImportError,OSError,RuntimeError):pass
        if self.popup:self.popup.close()
        self.popup=Popup(caption);self.popup.show()
def main():
    DATA.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(DATA/'alfa_bildirim.lock'));lock.setStaleLockTime(30000)
    if not lock.tryLock(100):return 0
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    service=Service(app);app._service=service
    return app.exec()
if __name__=='__main__':sys.exit(main())
