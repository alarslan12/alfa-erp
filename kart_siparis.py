"""Havuz / Aktif / Tamamlanan için kompakt, hizalı sipariş kartları."""
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import math
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QColor, QPainter, QAction, QFont, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QProgressBar,
    QCheckBox, QApplication, QToolButton, QMenu, QGridLayout, QSizePolicy
)
from widgets import text, cover_label, button, fallback_cover_pixmap
from siparis_uyari import pending_notice


def readable_date(value):
    try:
        return datetime.fromisoformat(value).strftime('%d.%m.%Y  %H:%M')
    except (TypeError, ValueError):
        return str(value or '')[:16]


@lru_cache(maxsize=950)
def _scaled_cover(path, stamp, w, h):
    pix = QPixmap(path)
    if pix.isNull():
        return QPixmap()
    return pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)


class ProgressCover(QLabel):
    """İlerlemeyi doğrudan kapağın görünen alanı üstünde gösterir."""
    def __init__(self, book, covers, group, w=80, h=110, active=False):
        super().__init__()
        self.book = book
        self.covers_ref = covers
        self._target_w = w
        self._target_h = h
        self._fallback = None
        self._path = covers.path(book) if covers else None
        self.setObjectName('OrderPreviewCover')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet('QLabel#OrderPreviewCover { background:transparent; border:0; padding:0; }')
        self.ready = 0
        self.boxed = 0
        self.set_thumb_size(w, h)
        self.set_progress(group, active)

    def set_thumb_size(self, w, h, force=False):
        w = max(18, int(w))
        h = max(26, int(h))
        # Qt 6 may return a non-None *null* QPixmap for an empty QLabel.
        # Checking only "is not None" made all first-render tracking covers blank.
        old_pix = self.pixmap()
        if not force and (w, h) == (self._target_w, self._target_h) and old_pix is not None and not old_pix.isNull():
            self.setFixedSize(w, h)
            return
        self._target_w, self._target_h = w, h
        self.setFixedSize(w, h)
        pix = QPixmap()
        if self._path:
            path = Path(self._path)
            try:
                pix = _scaled_cover(str(path), path.stat().st_mtime_ns, w, h)
            except OSError:
                pass
        self._showing_placeholder = pix.isNull()
        if self._showing_placeholder:
            pix = fallback_cover_pixmap(self.book, w, h)
        self.setPixmap(pix)
        self.update()

    def refresh_cover_theme(self):
        # Gerçek kapakları önbellekten kullan; yalnızca çizilmiş placeholder
        # tema değişikliğinde yeniden üretilsin.
        if getattr(self, '_showing_placeholder', False):
            self.set_thumb_size(self._target_w, self._target_h, force=True)

    def content_rect(self):
        pix = self.pixmap()
        if pix is None or pix.isNull():
            return self.rect().adjusted(0, 0, -1, -1)
        rect = pix.rect()
        rect.moveCenter(self.rect().center())
        return rect

    def set_progress(self, group, active=True):
        count = max(1, int(group.get('adet', 0)))
        self.ready = min(1, max(0, int(group.get('hazir', 0)) / count)) if active else 0
        self.boxed = min(1, max(0, int(group.get('koli', 0)) / count)) if active else 0
        self.setToolTip(
            f"Hazır: {group.get('hazir',0)}/{group.get('adet',0)}\n"
            f"Kolilendi: {group.get('koli',0)}/{group.get('adet',0)}"
        )
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.ready and not self.boxed:
            return
        painter = QPainter(self)
        rect = self.content_rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if self.ready:
            ready_h = round(h * self.ready)
            painter.fillRect(QRect(x, y + h - ready_h, w, ready_h), QColor(47, 137, 230, 32))
            painter.fillRect(x, y + h - 3, round(w * self.ready), 3, QColor(78, 156, 233, 150))
        if self.boxed:
            boxed_h = round(h * self.boxed)
            painter.fillRect(QRect(x, y + h - boxed_h, w, boxed_h), QColor(56, 210, 143, 46))
            painter.fillRect(x, y + h - 3, round(w * self.boxed), 3, QColor(95, 209, 160, 175))
        if self.boxed >= 1 and w >= 34 and h >= 44:
            tick = QRect(rect.center().x() - 13, rect.center().y() - 13, 26, 26)
            painter.setPen(QPen(QColor('#b8f5d7'), 1.4))
            painter.setBrush(QColor(19, 94, 65, 205))
            painter.drawRoundedRect(tick, 13, 13)
            painter.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
            painter.setPen(QColor('#ffffff'))
            painter.drawText(tick, Qt.AlignmentFlag.AlignCenter, '✓')
        painter.end()


def order_cover_badges(group):
    """Show only nonzero print-variant quantities."""
    badges = []
    for kind, key in (('SB', 'sb'), ('RNK', 'rnk')):
        qty = int(group.get(key, 0))
        if qty > 0:
            badges.append((key, f'{kind} {qty}'))
    return badges


class OrderMiniCover(ProgressCover):
    """Kitap kapağında yalnızca SB/RNK miktarları."""
    def __init__(self, book, covers, group, w, h, active=False):
        self.book_name = book.get('isim', '')
        self.book_code = book.get('kod', '')
        self.group = group
        super().__init__(book, covers, group, w, h, active)

    def set_progress(self, group, active=True):
        self.group = group
        super().set_progress(group, active)
        self.setToolTip(
            f"#{self.book_code} · {self.book_name}\n"
            f"Toplam {group.get('adet',0)} kitap · SB {group.get('sb',0)} / RNK {group.get('rnk',0)}\n"
            f"Hazır {group.get('hazir',0)} · Kolilendi {group.get('koli',0)}"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        # Use the entire thumbnail's bounds; a narrow portrait image in a
        # wider label must not cause quantity badges to disappear.
        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return
        badges = order_cover_badges(self.group)
        if not badges:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = {
            'sb': (QColor(68, 52, 118, 240), QColor('#f1e9ff')),
            'rnk': (QColor(153, 80, 53, 240), QColor('#fff2e9')),
        }
        font = QFont('Segoe UI')
        font.setWeight(QFont.Weight.Bold)
        gap = 1
        # Fit only existing print variants, stacked at the top right.
        font_px = min(12, max(5, (rect.height() - gap) // len(badges) - 2))
        while True:
            font.setPixelSize(font_px)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            padding = 4 if font_px >= 9 else 2
            widths = [metrics.horizontalAdvance(label) + padding
                      for _, label in badges]
            height = metrics.height() + 2
            if (max(widths) <= rect.width() and
                    len(badges) * height + (len(badges) - 1) * gap <= rect.height()) or font_px <= 3:
                break
            font_px -= 1

        for index, ((key, label), width) in enumerate(zip(badges, widths)):
            width = min(width, rect.width())
            x = rect.right() - width + 1
            y = rect.y() + index * (height + gap)
            area = QRect(x, y, width, height)
            bg, fg = colors[key]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(area, 3, 3)
            painter.setPen(fg)
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()


class OrderCoversArea(QWidget):
    """Geometry-driven cover layout: no child grid's minimum width can overflow the row.

    Children are repositioned only when the available width actually changes.
    One row is filled before beginning the next; no horizontal scrollbar.
    """
    def __init__(self, db, order, covers, status, parent=None):
        super().__init__(parent)
        self.setObjectName('OrderCovers')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(90)
        self._active = status in ('aktif', 'tamamlandi')
        self._cards = []
        self.thumbs = {}
        self._layout_key = None
        self._pending_reflow = QTimer(self)
        self._pending_reflow.setSingleShot(True)
        self._pending_reflow.setInterval(35)
        self._pending_reflow.timeout.connect(self.reflow)
        for group in db.siparis_gruplari(order):
            code = str(group['kod'])
            book = db.katalog.get(code, {'kod':code,'isim':group['isim']})
            thumb = OrderMiniCover(book,covers,group,64,91,active=self._active)
            thumb.setParent(self)
            thumb.show()
            self._cards.append(thumb)
            self.thumbs[code] = thumb
        self._pending_reflow.start(0)

    def showEvent(self, event):
        super().showEvent(event)
        self._pending_reflow.start(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self._pending_reflow.start()

    def reflow(self):
        n = len(self._cards)
        if not n:
            return
        available = max(1, self.contentsRect().width() - 4)
        gap = 5
        # Choose the largest readable thumbnails that fit both actual width
        # and height. Grid children have no minimum-width constraint on the card.
        best = None
        for columns in range(1, n+1):
            rows = math.ceil(n/columns)
            if rows > 7:
                continue
            width_fit = (available-(columns-1)*gap)//columns
            height_fit = (max(50,self.height()-6)-(rows-1)*gap)//rows
            thumb_w = min(125, width_fit, int(height_fit/1.42))
            if thumb_w < 18:
                continue
            score = (thumb_w + (8 if rows == 1 else 3 if rows == 2 else 0), -rows, -columns)
            if best is None or score > best[0]:
                best = (score, columns, rows, thumb_w)
        if best is None:
            columns, rows, thumb_w = max(1,math.ceil(n/7)),7,18
        else:
            _,columns,rows,thumb_w = best
        thumb_h = max(25, int(thumb_w*1.42))
        key = (available,self.height(),columns,rows,thumb_w,thumb_h)
        if key == self._layout_key:
            return
        self._layout_key = key
        # Always anchor covers to the left edge so the strip starts flush
        # beside the order information regardless of resolution.
        offset_x = 0
        offset_y = max(0,(self.height()-(rows*thumb_h+(rows-1)*gap))//2)
        for index, thumb in enumerate(self._cards):
            col, row = index % columns, index//columns
            thumb.set_thumb_size(thumb_w, thumb_h)
            thumb.setGeometry(2+offset_x+col*(thumb_w+gap),offset_y+row*(thumb_h+gap),thumb_w,thumb_h)
            thumb.show()

    def update_groups(self, db, order):
        groups = {str(g['kod']):g for g in db.siparis_gruplari(order)}
        active = db.siparis_durumu(order) in ('aktif','tamamlandi')
        for code, thumb in self.thumbs.items():
            if code in groups:
                thumb.set_progress(groups[code], active=active)
        # This path doesn't rebuild geometry, so counters cannot jump around.

class SiparisKarti(QFrame):
    def __init__(self, db, siparis, covers, on_open, on_status, on_check=None,
                 selected=False, on_delete=None, allow_edit=True):
        super().__init__()
        self.setObjectName('OrderRow')
        self.setMinimumHeight(174)
        status = db.siparis_durumu(siparis)
        self._status = status
        self._notice_pending = status!='tamamlandi' and pending_notice(siparis)
        self._pulse_on = True
        self.setFixedHeight((202 if status == 'tamamlandi' else 186)+(43 if self._notice_pending else 0))
        self.setProperty('orderStatus', status)
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(10)
        summary = db.siparis_ozeti(siparis)
        self._selected_checkbox = None
        self._selected_tag = None
        self._progress = {}

        left = QVBoxLayout(); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(5)
        head = QHBoxLayout(); head.setContentsMargins(0, 0, 0, 0); head.setSpacing(6)
        if status == 'aktif' and on_check:
            cb = QCheckBox()
            cb.setAccessibleName(f"Sipariş {siparis['id']} seçimi")
            cb.setToolTip('Kargo fişi için bu siparişi seç')
            cb.setChecked(selected)
            cb.stateChanged.connect(lambda state: on_check(str(siparis['id']), bool(state)))
            self._selected_checkbox = cb
            head.addWidget(cb)
        head.addWidget(text('#' + str(siparis['id']), 'OrderID'))
        role = 'OrderPlatformDone' if status == 'tamamlandi' else 'OrderPlatform'
        head.addWidget(text(str(siparis.get('platform') or 'Manuel'), role))
        selected_tag = text('✓ Seçili', 'OrderSelectedTag')
        selected_tag.setVisible(selected)
        self._selected_tag = selected_tag
        head.addWidget(selected_tag)
        head.addStretch()
        left.addLayout(head)
        ship = button(str(siparis.get('kod') or 'Kargo kodu yok') + '   ⧉', 'CopyCode')
        ship.setToolTip('Kargo kodunu veya adresi panoya kopyala')
        ship.setFixedHeight(32)
        ship.setMinimumWidth(0)
        ship.setToolTip(f"{siparis.get('kod') or 'Kargo kodu yok'}\nKopyalamak için tıklayın.")
        ship.clicked.connect(lambda: QApplication.clipboard().setText(str(siparis.get('kod', ''))))
        left.addWidget(ship)
        left.addWidget(text(readable_date(siparis.get('tarih', '')), 'OrderMeta'))
        if status == 'tamamlandi' and siparis.get('tamamlanma_tarihi'):
            left.addWidget(text('Tamamlandı · ' + readable_date(siparis['tamamlanma_tarihi']), 'OrderDoneDate'))
        if status == 'tamamlandi' and siparis.get('kargo_turu') in ('telafi', 'acik_adres'):
            label = 'Telafi kargosu' if siparis.get('kargo_turu') == 'telafi' else 'Açık adres kargosu'
            cost = text(f"{label}: {float(siparis.get('kargo_ucreti',0) or 0):,.2f} TL", 'OrderShippingCost')
            cost.setToolTip('Tamamlanan siparişin kaydedilen kargo gideri')
            left.addWidget(cost)
        highlight = QHBoxLayout()
        highlight.setSpacing(6)
        qty_role = 'OrderPoolQty' if status == 'havuz' else 'OrderActiveQty'
        pages_role = 'OrderPoolPages' if status == 'havuz' else 'OrderActivePages'
        highlight.addWidget(text(f"{summary['adet']} kitap", qty_role))
        highlight.addWidget(text(f"{summary['sayfa']:,} sayfa", pages_role))
        highlight.addStretch()
        left.addLayout(highlight)
        finance = QHBoxLayout(); finance.setContentsMargins(0, 0, 0, 0); finance.setSpacing(5)
        ciro = float(siparis.get('ciro', 0) or 0)
        # Very large sales values get a compact badge; exact amount remains on hover.
        short_ciro = f'{ciro/1_000_000:,.2f} Mn ₺' if ciro >= 1_000_000 else f'{ciro:,.2f} ₺'
        revenue = text(short_ciro, 'OrderRevenuePill')
        revenue.setToolTip(f'Kesin ciro: {ciro:,.2f} ₺')
        revenue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        revenue.setMinimumWidth(88)
        revenue.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        finance.addWidget(revenue, 1)
        sb_badge = text(f"SB {summary['sb']}", 'BadgeSB')
        rnk_badge = text(f"RNK {summary['rnk']}", 'BadgeRNK')
        for badge in (sb_badge, rnk_badge):
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        finance.addWidget(sb_badge)
        finance.addWidget(rnk_badge)
        left.addLayout(finance)
        left.addStretch()
        left_box = QWidget(); left_box.setLayout(left); left_box.setFixedWidth(278 if status == 'tamamlandi' else 264)
        root.addWidget(left_box)
        self._left_box = left_box

        self.covers_area = OrderCoversArea(db, siparis, covers, status)
        root.addWidget(self.covers_area, 1)

        right = QVBoxLayout()
        right.setContentsMargins(5, 5, 5, 5)
        right.setSpacing(8)
        if status in ('aktif', 'tamamlandi'):
            progress_group = QFrame()
            progress_group.setObjectName('OrderProgressGroup')
            progress_lay = QVBoxLayout(progress_group)
            progress_lay.setContentsMargins(6, 3, 6, 5)
            progress_lay.setSpacing(3)
            for name, key, kind in (('Hazır', 'hazir', 'ReadyProgress'), ('Koli', 'koli', 'BoxProgress')):
                line = QHBoxLayout()
                line.setContentsMargins(0, 0, 0, 0)
                line.setSpacing(6)
                line.addWidget(text(name, 'OrderProgressCaption'))
                line.addStretch(1)
                number = text(f"{summary[key]}/{summary['adet']}", 'OrderProgressNumber')
                number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                line.addWidget(number)
                progress_lay.addLayout(line)
                progress = QProgressBar()
                progress.setObjectName(kind)
                progress.setTextVisible(False)
                progress.setFixedHeight(7)
                progress.setRange(0, max(1, summary['adet']))
                progress.setValue(summary[key])
                progress.setToolTip('Hazırlanan kitapların oranı' if key == 'hazir'
                                    else 'Kolilenen kitapların oranı')
                progress_lay.addWidget(progress)
                self._progress[key] = (number, progress)
            right.addWidget(progress_group)
        else:
            pool_info = text('SİPARİŞ HAVUZU', 'OrderPoolInfo')
            pool_info.setToolTip('Sipariş henüz aktife alınmadı')
            right.addWidget(pool_info)
        if self._notice_pending:
            self._notice_btn=button('⚠ Siparişle ilgili\ngüncelleme var')
            self._notice_btn.setFixedHeight(38)
            self._notice_btn.setToolTip('Değişiklikleri okumak ve onaylamak için tıklayın')
            self._notice_btn.clicked.connect(lambda:on_open(siparis['id'],'track'))
            right.addWidget(self._notice_btn)
            self._notice_timer=QTimer(self)
            self._notice_timer.setInterval(700)
            self._notice_timer.timeout.connect(self._pulse_notice)
            self._pulse_notice()
        detail = button('Sipariş detayı', 'DetailAction')
        detail.setToolTip('Hazırlama, kolileme ve kitap PDF ekranını aç')
        detail.clicked.connect(lambda: on_open(siparis['id'], 'track'))
        detail.setFixedHeight(40 if status == 'havuz' else 36)
        right.addWidget(detail)
        row = QHBoxLayout(); row.setSpacing(7)
        if status == 'havuz':
            primary = button('Aktife al', 'Success')
            primary.clicked.connect(lambda: on_status(siparis, 'aktif'))
            primary.setFixedHeight(40)
            primary.setEnabled(not self._notice_pending)
            if self._notice_pending:primary.setToolTip('Önce sipariş güncellemesini okuyun')
            primary.setMinimumWidth(0)
            row.addWidget(primary, 1)
            if on_delete:
                delete_direct=button('Sil', 'PoolDeleteAction')
                delete_direct.setFixedHeight(40)
                delete_direct.setMinimumWidth(70)
                delete_direct.setToolTip('Siparişi onay alarak kalıcı sil')
                delete_direct.clicked.connect(lambda: on_delete(siparis))
                row.addWidget(delete_direct, 0)
        elif status == 'aktif':
            self._complete_btn = button('Tamamla', 'Success')
            self._complete_btn.setEnabled(db.kolileme_tamam(siparis) and not self._notice_pending)
            self._complete_btn.setToolTip('Bütün kitaplar kolilendiğinde kullanılabilir')
            self._complete_btn.clicked.connect(lambda: on_status(siparis, 'tamamlandi'))
            self._complete_btn.setFixedHeight(36)
            self._complete_btn.setMinimumWidth(0)
            row.addWidget(self._complete_btn, 1)
        else:
            done = text('✓ Tamamlandı', 'OrderDoneTag')
            done.setAlignment(Qt.AlignmentFlag.AlignCenter)
            done.setFixedHeight(36)
            row.addWidget(done, 1)
        more = QToolButton(); more.setObjectName('MoreActions'); more.setText('▾')
        more.setFixedSize(38, 36)
        more.setToolTip('Diğer sipariş işlemleri')
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(more); menu.setObjectName('OrderActionsMenu')
        if status != 'tamamlandi' and allow_edit:
            edit = QAction('Siparişi düzenle', menu)
            edit.triggered.connect(lambda: on_open(siparis['id'], 'edit'))
            menu.addAction(edit)
        if status == 'aktif':
            pool = QAction('Havuza geri al', menu)
            pool.triggered.connect(lambda: on_status(siparis, 'havuz'))
            menu.addAction(pool)
            if on_delete:
                delete = QAction('Siparişi kalıcı olarak sil', menu)
                delete.triggered.connect(lambda: on_delete(siparis))
                menu.addSeparator()
                menu.addAction(delete)
        elif status == 'havuz' and on_delete:
            delete = QAction('Siparişi sil', menu)
            delete.triggered.connect(lambda: on_delete(siparis))
            menu.addSeparator(); menu.addAction(delete)
        elif status == 'tamamlandi':
            reopen = QAction('Aktife geri al', menu)
            reopen.triggered.connect(lambda: on_status(siparis, 'aktif'))
            menu.addAction(reopen)
            if on_delete:
                delete = QAction('Siparişi sil', menu)
                delete.triggered.connect(lambda: on_delete(siparis))
                menu.addSeparator(); menu.addAction(delete)
        more.setMenu(menu)
        if status != 'havuz' or allow_edit:
            row.addWidget(more)
        right.addLayout(row)
        if status == 'havuz':
            right.addStretch(1)
        box = QFrame()
        box.setObjectName('OrderRightPanel')
        box.setLayout(right)
        box.setFixedWidth(216 if status == 'havuz' else 205)
        root.addWidget(box)
        self._right_box = box
        self.set_selected(selected)

    def showEvent(self,event):
        super().showEvent(event)
        if self._notice_pending:
            self._notice_timer.start()

    def hideEvent(self,event):
        if self._notice_pending:
            self._notice_timer.stop()
        super().hideEvent(event)

    def _pulse_notice(self):
        if not self._notice_pending:
            return
        self._pulse_on=not self._pulse_on
        bg,fg=('#ffcb40','#362000') if self._pulse_on else ('#a74a00','#ffffff')
        self._notice_btn.setStyleSheet(f'QPushButton {{background:{bg};color:{fg};font-size:11px;font-weight:900;border:2px solid #ffaa17;border-radius:6px;padding:1px;}}')
        if self.isVisible():
            self.update()

    def paintEvent(self,event):
        super().paintEvent(event)
        if not self._notice_pending:
            return
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color=QColor('#ffc328' if self._pulse_on else '#ff8b21')
        for width,alpha,inset in ((7,65,4),(4,140,3),(2,255,2)):
            color.setAlpha(alpha)
            pen=QPen(color,width)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(inset,inset,-inset,-inset),11,11)
        painter.end()

    def set_compact_mode(self, compact):
        compact = bool(compact)
        if getattr(self, '_compact', None) == compact:
            return
        self._compact = compact
        self._left_box.setFixedWidth((248 if compact else 278) if self._status=='tamamlandi' else (232 if compact else 264))
        self._right_box.setFixedWidth((194 if compact else 216) if self._status=='havuz' else (170 if compact else 205))
        # Dense orders need a third row on smaller screens; only the affected
        # row grows, not the whole application's font/theme.
        total = len(self.covers_area._cards)
        self.setFixedHeight((226 if compact and total >= 18 else (202 if self._status=='tamamlandi' else 186))+(43 if self._notice_pending else 0))
        self.covers_area._pending_reflow.start(0)

    def set_selected(self, selected):
        selected = bool(selected)
        if self._selected_checkbox is not None:
            self._selected_checkbox.blockSignals(True)
            self._selected_checkbox.setChecked(selected)
            self._selected_checkbox.blockSignals(False)
        if self._selected_tag is not None:
            self._selected_tag.setVisible(selected)
        if self.property('orderSelected') != selected:
            self.setProperty('orderSelected', selected)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def refresh_progress(self, db, order):
        summary = db.siparis_ozeti(order)
        for key, (value, bar) in self._progress.items():
            value.setText(f"{summary[key]}/{summary['adet']}")
            bar.setRange(0, max(1, summary['adet']))
            bar.setValue(summary[key])
        self.covers_area.update_groups(db, order)
        if hasattr(self, '_complete_btn'):
            self._complete_btn.setEnabled(db.kolileme_tamam(order) and not pending_notice(order))
