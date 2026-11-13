"""Tekrarlanan masaüstü bileşenleri, kapak eşleme ve düzen yardımcıları."""
from pathlib import Path
import shutil, re, unicodedata
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QPushButton, QMessageBox, QApplication
from tema import MUTED, AMBER

IMAGE_SUFFIXES = ('.jpg','.jpeg','.png','.webp','.bmp')

def normal(text):
    t=str(text).replace('İ','i').replace('I','i').replace('ı','i')
    return ''.join(c for c in unicodedata.normalize('NFKD',t.lower()) if c.isalnum() and not unicodedata.combining(c))

class Covers:
    def __init__(self, db, root):
        self.db=db; self.root=Path(root); self.user=Path(db.sepet_dosyasi).parent/'kapaklar'
        self.user.mkdir(exist_ok=True,parents=True)
        self.refresh()
    def refresh(self):
        self.manual_index={}
        self.auto_index={}
        manual_dirs=(self.root/'assets'/'kapaklar',self.root/'kapaklar',self.user)
        for directory in manual_dirs:
            if not directory.exists():continue
            for file in directory.iterdir():
                if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES:
                    self.manual_index[normal(file.stem)]=file
        automated=self.user/'pdf_otomatik'
        if automated.is_dir():
            for file in automated.iterdir():
                if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES:
                    self.auto_index[normal(file.stem)]=file
        # Backward-compatible index for non-cover callers.
        self.index={**self.auto_index,**self.manual_index}

    def path(self,book):
        code=str(book['kod'])
        title=normal(book['isim'])
        # Manual overrides have priority EVEN if named after the book
        # rather than its numeric code. Auto renders are a fallback only.
        for index in (self.manual_index,self.auto_index):
            for key in (normal(code),title):
                if key in index:return index[key]
            for key,file in index.items():
                if re.fullmatch(
                    r'(?:kitap|kod|book)?0*'+re.escape(code)+
                    r'(?:kapak|cover)?',key):
                    return file
        return None

    def import_file(self, book, source):
        src=Path(source)
        if src.suffix.lower() not in IMAGE_SUFFIXES:raise ValueError('JPG, PNG, WEBP veya BMP seçin.')
        dst=self.user/(str(book['kod'])+src.suffix.lower())
        if src.resolve()!=dst.resolve():shutil.copy2(src,dst)
        self.refresh();return dst
    def import_folder(self, source):
        src=Path(source); count=0
        for file in src.rglob('*'):
            if file.suffix.lower() not in IMAGE_SUFFIXES or not file.is_file():continue
            # Yalnızca katalogda doğru bir kitapla eşleşen resimleri içeri al.
            key=normal(file.stem)
            found=None
            books=list(self.db.katalog.values())
            for book in books:
                if key in (normal(book['kod']),normal(book['isim'])):
                    found=book;break
            if not found:
                # 'kitap_29', '29-kapak', 'BOOK-29' ve benzeri eski adları da karşıla.
                matches=re.findall(r'(?<!\d)\d{1,5}(?!\d)', file.stem)
                for n in matches:
                    code=str(int(n))
                    if code in self.db.katalog:
                        found=self.db.katalog[code];break
            if found:self.import_file(found,file);count+=1
        self.refresh();return count

def _cover_theme_is_light():
    app = QApplication.instance()
    return bool(app and app.property('alfa_theme') == 'acik')


def fallback_cover_pixmap(book, w, h):
    """Gerçek kapak olmayan kitaplar için aktif temada oluşturulan geçici kapak.

    Görsel dosyası yoktur; bu pixmap kullanıcının tema tercihi değiştiğinde
    yeniden çizilebilir. Böylece krem/koyu renkler birbirine karışmaz.
    """
    light = _cover_theme_is_light()
    base_fill = '#f2e6d5' if light else '#233348'
    g1 = '#efe0c8' if light else '#38516a'
    g2 = '#dbc7ad' if light else '#242938'
    accent = '#b58950' if light else '#d5b88b'
    text_color = '#35506a' if light else '#f1e4d5'
    pix = QPixmap(w, h)
    pix.fill(QColor(base_fill))
    painter = QPainter(pix)
    gradient = QLinearGradient(0, 0, w, h)
    gradient.setColorAt(0, QColor(g1))
    gradient.setColorAt(1, QColor(g2))
    painter.fillRect(0, 0, w, h, gradient)
    painter.setPen(QColor(accent))
    font = QFont('Segoe UI', 17)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(8, 26, 'A')
    font = QFont('Segoe UI', max(6, min(9, w // 10)))
    font.setBold(True)
    painter.setFont(font)
    title = str(book.get('isim', 'KİTAP')) if book else 'KİTAP'
    painter.setPen(QColor(text_color))
    painter.drawText(6, h // 2 - 5, w - 12, h // 2,
                     Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop, title[:64])
    painter.setPen(QColor(accent))
    painter.drawText(6, h - 8, '#' + str(book.get('kod', '')) if book else '')
    painter.end()
    return pix


class ThemedCoverLabel(QLabel):
    """Katalog/arayüz kapak placeholder'ını tema değiştiğinde günceller."""
    def __init__(self, book, covers, w, h):
        super().__init__()
        self.book = book
        self.covers_ref = covers
        self.cover_w = w
        self.cover_h = h
        self._is_placeholder = True
        self.setFixedSize(w, h)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Transparan zemin, kapak resminin gerçek boyutu dışında koyu blok bırakmaz.
        self.setStyleSheet('background:transparent; border:0; padding:0;')
        self.refresh_cover_theme()

    def reload_cover_from_disk(self):
        """Refresh a live book card when PDF thumbnails were regenerated."""
        self._is_placeholder=True
        self.refresh_cover_theme()

    def refresh_cover_theme(self):
        # Gerçek kitap kapağı değişmeyeceğinden büyük dosyaları yeniden yükleme.
        if not self._is_placeholder:
            return
        file = self.covers_ref.path(self.book) if self.book and self.covers_ref else None
        if file:
            image = QPixmap(str(file))
            if not image.isNull():
                self._is_placeholder = False
                self.setPixmap(image.scaled(self.cover_w - 2, self.cover_h - 2,
                                           Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
                return
        self.setPixmap(fallback_cover_pixmap(self.book, self.cover_w, self.cover_h))


def cover_label(book, covers, w=66, h=94):
    return ThemedCoverLabel(book, covers, w, h)


def refresh_cover_placeholders():
    """Ayarlar ekranından tema değişince zaten açık kartların kapaklarını da güncelle."""
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.allWidgets():
        refresh = getattr(widget, 'refresh_cover_theme', None)
        if refresh is not None and callable(refresh):
            refresh()


def refresh_all_cover_labels():
    """Reload automatically extracted covers without rebuilding order cards."""
    app=QApplication.instance()
    if app is None:return
    for widget in app.allWidgets():
        reload=getattr(widget,'reload_cover_from_disk',None)
        if callable(reload):
            try:reload()
            except RuntimeError:pass


def vbox(*children, gap=8, margin=0):
    lay=QVBoxLayout();lay.setContentsMargins(margin,margin,margin,margin);lay.setSpacing(gap)
    for child in children:lay.addWidget(child)
    return lay

def hbox(*children,gap=8,margin=0):
    lay=QHBoxLayout();lay.setContentsMargins(margin,margin,margin,margin);lay.setSpacing(gap)
    for child in children:lay.addWidget(child)
    return lay

def text(value, role='Muted',wrap=False):
    lbl=QLabel(str(value));lbl.setObjectName(role);lbl.setWordWrap(wrap);return lbl

def button(value,kind=None):
    b=QPushButton(value);b.setCursor(Qt.CursorShape.PointingHandCursor)
    if kind:b.setObjectName(kind)
    return b

def panel():
    frame=QFrame();frame.setObjectName('Panel');return frame

def scrollable(widget):
    area=QScrollArea();area.setWidgetResizable(True);area.setWidget(widget);area.setFrameShape(QFrame.Shape.NoFrame)
    return area

def clear_layout(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget():item.widget().deleteLater()
        if item.layout():clear_layout(item.layout())

def error(parent, reason):QMessageBox.warning(parent,'ALFA ERP',str(reason))
def confirm(parent,question):return QMessageBox.question(parent,'ALFA ERP',question,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
