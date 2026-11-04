"""Minimal staff settings; administrative functions moved to separate app."""
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFrame,QFileDialog,QMessageBox,QApplication,QStackedWidget
from ayar_yonetimi import theme_styles
from tema import QSS
from pdf_kitap import PdfKutuphane
from widgets import button,text,refresh_cover_placeholders
class SettingsPage(QWidget):
    def __init__(self,db,config):
        super().__init__();self.db=db;self.config=config
        self.pdf=PdfKutuphane(Path(db.siparis_dosyasi).parent)
        root=QVBoxLayout(self);root.addWidget(text('ÇALIŞMA AYARLARI','SettingsTitle'))
        self.nav=[];nav=QHBoxLayout()
        for i,label in enumerate(('Görünüm','Kitap PDF klasörü')):
            b=button(label,'SettingsNav');b.setCheckable(True)
            b.clicked.connect(lambda checked=False,x=i:self.show_tab(x));nav.addWidget(b);self.nav.append(b)
        nav.addStretch();root.addLayout(nav)
        self.stack=QStackedWidget();root.addWidget(self.stack)
        page=QWidget();col=QVBoxLayout(page);card=QFrame();card.setObjectName('SettingsCard');controls=QVBoxLayout(card)
        controls.addWidget(text('Görünüm','SettingsHeading'));row=QHBoxLayout();self.themes=[]
        for key,label in [('koyu','Koyu'),('acik','Açık'),('kontrast','Yüksek kontrast')]:
            b=button(label,'SettingsThemeOption');b.setCheckable(True)
            b.clicked.connect(lambda checked=False,k=key:self.set_theme(k));row.addWidget(b);self.themes.append((key,b))
        controls.addLayout(row);col.addWidget(card);col.addStretch();self.stack.addWidget(page)
        page=QWidget();col=QVBoxLayout(page);card=QFrame();card.setObjectName('SettingsCard');controls=QVBoxLayout(card)
        controls.addWidget(text('PDF kütüphanesi','SettingsHeading'));self.path=text('','SettingsHint',wrap=True);controls.addWidget(self.path)
        row=QHBoxLayout();pick=button('PDF klasörü seç','Accent');pick.clicked.connect(self.select_pdf)
        reload=button('Yenile','SmallAction');reload.clicked.connect(self.rescan_pdf)
        row.addWidget(pick);row.addWidget(reload);controls.addLayout(row);col.addWidget(card);col.addStretch();self.stack.addWidget(page)
        self.show_tab(0)
    def show_tab(self,index):
        self.current_tab=index;self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav):b.setChecked(i==index)
        for key,b in self.themes:b.setChecked(self.config.get('tema','koyu')==key)
        self.path.setText('PDF: '+str(self.pdf.folder or 'Klasör seçilmedi'))
    def set_theme(self,key):
        self.config.set('tema',key);QApplication.instance().setProperty('alfa_theme',key)
        QApplication.instance().setStyleSheet(QSS+theme_styles(key));refresh_cover_placeholders();self.show_tab(0)
    def select_pdf(self):
        path=QFileDialog.getExistingDirectory(self,'PDF klasörünü seç',str(self.pdf.folder or Path.home()))
        if path:
            try:self.pdf.set_folder(path);self.show_tab(1)
            except Exception as exc:QMessageBox.warning(self,'PDF',str(exc))
    def rescan_pdf(self):
        self.pdf.scan();self.show_tab(1)
