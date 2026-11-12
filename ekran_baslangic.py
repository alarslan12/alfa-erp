"""ALFA ERP - branded launch screen with actual startup diagnostics.

Never runs network or mutates order data. The main window owns the checks,
and cloud verification continues in an independent thread after launch.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor


class StartupSplash(QWidget):
    STEPS = (
        ('storage', 'Yerel veri alanı'),
        ('orders', 'Siparişler ve işlem kuyruğu'),
        ('catalog', 'Katalog ve uygulama bileşenleri'),
        ('device', 'Cihaz yetkilendirmesi'),
        ('cloud', 'Bulut eşitlemesi'),
    )

    def __init__(self, owner=False, version=''):
        super().__init__(
            None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 456)
        self._states = {}
        self._labels = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)

        panel = QFrame()
        panel.setObjectName('BootPanel')
        panel.setStyleSheet("""
            QFrame#BootPanel {
                background: #111d30;
                border: 1px solid #31445e;
                border-radius: 20px;
            }
            QLabel { background: transparent; border: none; color: #e8f0fa; }
            QProgressBar { border: 0; border-radius: 4px; background: #26394d; height: 7px; }
            QProgressBar::chunk { border-radius: 4px; background: #43c5b6; }
        """)
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 105))
        panel.setGraphicsEffect(shadow)
        root.addWidget(panel)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(35, 27, 35, 24)
        outer.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(14)
        badge = QLabel('A')
        badge.setFixedSize(57, 57)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            QLabel {
                background: #43c5b6; color: #102132; border-radius: 14px;
                font-family: 'Segoe UI'; font-size: 33px; font-weight: 800;
            }
        """)
        top.addWidget(badge)
        brand = QVBoxLayout()
        brand.setSpacing(2)
        title = QLabel('ALFA ERP')
        title.setStyleSheet("font: 700 27px 'Segoe UI'; color:#f7f9ff;")
        subtitle = QLabel('YÖNETİCİ' if owner else 'PERSONEL')
        subtitle.setStyleSheet(
            "font: 600 10px 'Segoe UI'; color: #d6ba85;" if owner else
            "font: 600 10px 'Segoe UI'; color: #91c4d7;"
        )
        brand.addWidget(title)
        brand.addWidget(subtitle)
        top.addLayout(brand, 1)
        ver = QLabel('v' + str(version))
        ver.setStyleSheet("font: 11px 'Segoe UI'; color:#8298b1;")
        top.addWidget(ver, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(top)

        caption = QLabel('Çalışma ortamı hazırlanıyor')
        caption.setStyleSheet("font: 600 15px 'Segoe UI'; color:#dfeaf8;")
        outer.addWidget(caption)

        self.detail = QLabel('Yerel veriler doğrulanıyor…')
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("font: 11px 'Segoe UI'; color:#9fb1c8;")
        outer.addWidget(self.detail)

        for key, name in self.STEPS:
            line = QHBoxLayout()
            line.setSpacing(12)
            label = QLabel('○')
            label.setFixedWidth(19)
            label.setStyleSheet("color:#647a91; font: 16px 'Segoe UI';")
            message = QLabel(name)
            message.setStyleSheet("color:#c4d2e3; font: 12px 'Segoe UI';")
            line.addWidget(label)
            line.addWidget(message, 1)
            outer.addLayout(line)
            self._labels[key] = (label, message)

        outer.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.STEPS))
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)
        footer = QLabel('ALFA COPY CENTER  •  GÜVENLİ ÇALIŞMA ORTAMI')
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font: 600 9px 'Segoe UI'; color:#6f889d; letter-spacing: 1px;")
        outer.addWidget(footer)

    def update_step(self, key, detail=None, warning=False, error=False):
        if key not in self._labels:
            return
        symbol, label = self._labels[key]
        if error:
            symbol.setText('×')
            color = '#f08f8f'
        elif warning:
            symbol.setText('!')
            color = '#eac080'
        else:
            symbol.setText('✓')
            color = '#43c5b6'
        symbol.setStyleSheet("color:%s; font: 700 15px 'Segoe UI';" % color)
        label.setStyleSheet("color:#f0f6fe; font: 12px 'Segoe UI';")
        self._states[key] = True
        self.progress.setValue(len(self._states))
        if detail:
            self.detail.setText(str(detail))

    def center_on_screen(self, screen):
        if screen:
            center = screen.availableGeometry().center()
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)


def launch_with_splash(app,create_main,version='',owner=False,on_error=None):
    """Check local state and do an asynchronous Firebase startup check."""
    import tempfile
    from pathlib import Path
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    splash=StartupSplash(owner=owner,version=version)
    splash.center_on_screen(app.primaryScreen())
    app.setQuitOnLastWindowClosed(False)
    splash.show()
    state={'main':None,'finished':False,'failed':False}

    def finish():
        if state['finished'] or state['main'] is None:
            return
        state['finished']=True
        main=state['main']
        screen=app.primaryScreen()
        if screen:
            area=screen.availableGeometry()
            width=min(1600,max(780,area.width()-32))
            height=min(960,max(580,area.height()-32))
            main.setMinimumSize(min(860,width),min(620,height))
            main.resize(width,height)
            frame=main.frameGeometry()
            frame.moveCenter(area.center())
            main.move(frame.topLeft())
        main.show()
        splash.close()
        app.setQuitOnLastWindowClosed(True)
        QTimer.singleShot(2000,main._show_whats_new_once)
        QTimer.singleShot(3500,main.check_background_updates)

    def cloud_status(online,message):
        if state['finished']:
            return
        if online:
            splash.update_step('cloud','Firebase eşitlemesi doğrulandı.')
            QTimer.singleShot(120,finish)
        elif any(x in str(message).lower() for x in
                 ('beklemede','hata','ulaşılamadı','geçici','iptal','reddedildi')):
            splash.update_step('cloud','Firebase çevrimdışı; yerel işlemler korunuyor.',
                               warning=True)
            QTimer.singleShot(120,finish)

    def cloud_timeout():
        if not state['finished']:
            splash.update_step('cloud','Firebase denetimi arka planda devam ediyor.',
                               warning=True)
            finish()

    def load():
        try:
            app.processEvents()
            main=create_main()
            state['main']=main
            folder=Path(main.db.siparis_dosyasi).parent
            with tempfile.NamedTemporaryFile(prefix='.alfa_boot_',dir=folder) as test:
                test.write(b'ok')
                test.flush()
            splash.update_step('storage','Yerel çalışma dizini kullanılabilir.')
            splash.update_step('orders',
                ('%d işlem güvenle kuyrukta.'%main.db.pending_count)
                if main.db.pending_count else 'Yerel siparişler ve kuyruk doğrulandı.')
            if not main.db.katalog or main.stack.count()!=5:
                raise RuntimeError('Katalog veya ERP sayfaları hazırlanamadı.')
            splash.update_step('catalog',
                               '%d kitap ve ERP ekranları hazır.'%len(main.db.katalog))
            if main.device.paired:
                splash.update_step('device','Şifreli Firebase cihaz kimliği yüklendi.')
                main.live.status.connect(cloud_status)
                QTimer.singleShot(6000,cloud_timeout)
            else:
                splash.update_step('device','Cihaz henüz yetkilendirilmedi.',warning=True)
                splash.update_step('cloud','İlk Firebase yetkilendirmesi gerekli.',
                                   warning=True)
                QTimer.singleShot(120,finish)
        except Exception as exc:
            state['failed']=True
            splash.update_step('storage','Başlangıç hatası.',error=True)
            splash.close()
            if on_error:
                try:
                    on_error(type(exc),exc,exc.__traceback__,source='startup')
                except Exception:
                    pass
            QMessageBox.critical(None,'ALFA ERP başlangıç hatası',str(exc))
            app.exit(1)

    QTimer.singleShot(60,load)
    code=app.exec()
    return 1 if state['failed'] else code
