"""Windows sign-in tray notification agent, independent from the main ERP window."""
import sys,json,os
from pathlib import Path
from PySide6.QtCore import QTimer,QThread,Signal,Qt,QLockFile
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QLabel,QPushButton
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor,QFont,QAction
from alfa_cihaz import DATA,Workstation
STATE=DATA/'alfa_bildirim_durumu.json'
class Reader(QThread):
    done=Signal(dict);error=Signal(str)
    def __init__(self,client,last_revision=None):
        super().__init__();self.client=client;self.last_revision=last_revision
    def run(self):
        try:
            pulse=self.client.pulse()
            revision=(pulse.get('epoch'),pulse.get('orders_revision'))
            data=self.client.snapshot() if revision!=self.last_revision else None
            self.done.emit({'pulse':revision,'snapshot':data})
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
        try:self.seen=set(json.loads(STATE.read_text(encoding='utf-8'))['seen'])
        except (OSError,ValueError,KeyError,TypeError):self.seen=None
        self.worker=None;self.popup=None;self.last_revision=None
        self.timer=QTimer();self.timer.setInterval(2100);self.timer.timeout.connect(self.poll)
        self.timer.start();QTimer.singleShot(500,self.poll)
    def poll(self):
        if not self.client.paired:self.client=Workstation()
        if not self.client.paired or self.worker:return
        work=Reader(self.client,self.last_revision);self.worker=work
        def success(result):
            self.worker=None
            try:
                self.last_revision=result['pulse']
                data=result.get('snapshot')
                if data is None:return
                rows=[o for o in data['orders'] if o.get('id') and not o.get('deleted_at')]
                current={str(o['id']) for o in rows}
                fresh=current-self.seen if self.seen is not None else set()
                self.seen=(self.seen or set())|current
                DATA.mkdir(parents=True,exist_ok=True)
                staged=STATE.with_suffix('.tmp')
                staged.write_text(json.dumps({'seen':sorted(self.seen)}),encoding='utf-8');os.replace(staged,STATE)
                if fresh:
                    numbers=[str(x.get('order_number')) for x in rows if str(x.get('id')) in fresh]
                    self.notify(', '.join('#'+n for n in numbers[:5]),len(fresh))
            except (OSError,ValueError,TypeError,KeyError):pass
        def fail(message):self.worker=None;self.tray.setToolTip('ALFA ERP · '+message[:60])
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
