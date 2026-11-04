"""ALFA ERP: taşmayan, platformdan bağımsız seçim açılır listesi.

QComboBox'un Windows Qt6 style popup'ı az seçenekli tarihlerde beyaz,
boş alt panel üretiyordu. QFrame(Qt.Popup) içinde boyu tam satıra göre
ayarlanan bir QListWidget kullanılır; seçim QComboBox API'sini korur.
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QComboBox, QFrame, QListWidget,
    QListWidgetItem, QVBoxLayout,
)


class AlfaTemaliCombo(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alfa_popup = None
        self.setMaxVisibleItems(10)

    def showPopup(self):
        if self.count() <= 0:
            return
        if self._alfa_popup is not None:
            self._alfa_popup.close()
            self._alfa_popup = None

        light = QApplication.instance().property('alfa_theme') == 'acik'
        surface = '#fffaf2' if light else '#1c2c3f'
        item_bg = '#fffaf2' if light else '#1c2c3f'
        text_color = '#294158' if light else '#e9f3ff'
        line = '#d1bea3' if light else '#456381'
        hover = '#e8d8c2' if light else '#304a66'
        chosen = '#d6c0a0' if light else '#456c95'

        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setObjectName('AlfaDropdownPopup')
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        popup.setStyleSheet(f"""
            QFrame#AlfaDropdownPopup {{ background:{surface}; border:1px solid {line}; border-radius:6px; }}
            QListWidget#AlfaDropdownList {{ background:{surface}; color:{text_color}; border:0; padding:0; outline:0; }}
            QListWidget#AlfaDropdownList::item {{ background:{item_bg}; color:{text_color};
                min-height:30px; padding:2px 11px; border:0; border-bottom:1px solid {line}; }}
            QListWidget#AlfaDropdownList::item:hover {{ background:{hover}; color:{text_color}; }}
            QListWidget#AlfaDropdownList::item:selected {{ background:{chosen}; color:{text_color}; }}
            QScrollBar:vertical {{ width:8px; background:{surface}; }}
            QScrollBar::handle:vertical {{ background:{line}; border-radius:4px; min-height:18px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        content = QVBoxLayout(popup)
        content.setContentsMargins(1, 1, 1, 1)
        content.setSpacing(0)
        items = QListWidget(popup)
        items.setObjectName('AlfaDropdownList')
        items.setFrameShape(QFrame.Shape.NoFrame)
        items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        items.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        items.setUniformItemSizes(True)
        pal = items.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(surface))
        pal.setColor(QPalette.ColorRole.Window, QColor(surface))
        pal.setColor(QPalette.ColorRole.Text, QColor(text_color))
        items.setPalette(pal)
        items.viewport().setAutoFillBackground(True)
        items.viewport().setPalette(pal)
        for index in range(self.count()):
            entry = QListWidgetItem(self.itemText(index))
            entry.setData(Qt.ItemDataRole.UserRole, index)
            if not self.model().index(index, 0).flags() & Qt.ItemFlag.ItemIsEnabled:
                entry.setFlags(entry.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            items.addItem(entry)
        items.setCurrentRow(self.currentIndex())
        content.addWidget(items)
        popup.setFixedWidth(max(self.width(), 190))
        count = self.count()
        visible = min(count, self.maxVisibleItems(), 10)
        row_height = 35  # includes the 1 px separator
        outer_height = visible * row_height + 3
        screen = self.screen() or QApplication.primaryScreen()
        region = screen.availableGeometry() if screen else None
        if region:
            outer_height = min(outer_height, max(38, region.height()-28))
        popup.setFixedHeight(outer_height)

        def choose(entry):
            if entry is None or not entry.flags() & Qt.ItemFlag.ItemIsEnabled:
                return
            index = entry.data(Qt.ItemDataRole.UserRole)
            self.setCurrentIndex(index)
            popup.close()
            self.setFocus(Qt.FocusReason.MouseFocusReason)

        items.itemClicked.connect(choose)
        items.itemActivated.connect(choose)
        self._alfa_popup = popup
        popup.destroyed.connect(lambda *_: setattr(self, '_alfa_popup', None))
        point = self.mapToGlobal(QPoint(0, self.height()+2))
        if region:
            if point.x()+popup.width() > region.right():
                point.setX(max(region.left(), region.right()-popup.width()+1))
            if point.y()+popup.height() > region.bottom():
                above = self.mapToGlobal(QPoint(0, 0)).y()-popup.height()-2
                point.setY(above if above >= region.top() else max(region.top(), region.bottom()-popup.height()+1))
        popup.move(point)
        popup.show()
        items.setFocus(Qt.FocusReason.PopupFocusReason)

    def hidePopup(self):
        if self._alfa_popup is not None:
            self._alfa_popup.close()
            self._alfa_popup = None
