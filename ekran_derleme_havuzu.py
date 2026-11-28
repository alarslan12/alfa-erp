"""Yöneticiye özel, çevrimdışı fason sipariş takibi."""
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QStandardPaths
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QVBoxLayout, QWidget, QPlainTextEdit,
    QButtonGroup, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox,
    QAbstractSpinBox, QFormLayout)

from pdf_kitap import PdfKutuphane
from siparis_derleme_havuzu import compile_snapshot, local_label, order_totals
from widgets import button, confirm, error, text, cover_label, scrollable
from utils import metin_eslesiyor_mu


def _money(cents):
    return f'{cents / 100:,.2f}'.translate(str.maketrans(',.', '.,')) + ' TL'


def _number(value):
    return f'{value:,}'.replace(',', '.')


def _date(value):
    return value[:16].replace('T', ' ') if value else '—'


def _item(value):
    item = QTableWidgetItem(str(value))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class _BatchDerleme(QThread):
    progress = Signal(str)
    result = Signal(object)

    def __init__(self, store, orders, folder, desktop, parent=None):
        super().__init__(parent)
        self.store, self.orders = store, orders
        self.folder, self.desktop = folder, desktop

    def run(self):
        succeeded, failed = [], []
        try:
            from siparis_derle import derle_siparis
        except ImportError:
            self.result.emit(([], ['Derleme modülü kullanılamıyor.'], False))
            return
        for index, order in enumerate(self.orders, 1):
            if self.isInterruptionRequested():
                break
            sid = order['id']
            label = local_label(sid)
            snapshot, catalog = compile_snapshot(order)
            try:
                path = derle_siparis(
                    snapshot, catalog, self.folder, self.desktop,
                    cancel=self.isInterruptionRequested,
                    progress=lambda n, total, _p, _pages:
                        self.progress.emit(f'{index}/{len(self.orders)} · {label} · Kitap {n}/{total}'))
            except InterruptedError:
                break
            except Exception as exc:
                failed.append(f'{label}: {exc}')
                continue
            succeeded.append(str(path))
            try:
                self.store.record_zip(sid, path, expected=order)
            except Exception:
                failed.append(f'{label}: ZIP kaydedildi fakat yerel derleme tarihi kaydedilemedi.')
        self.result.emit((succeeded, failed, self.isInterruptionRequested()))


def _plain(value, role='Muted', wrap=False):
    label = text(value, role, wrap)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


class LocalDerlemeDialog(QDialog):
    """Cover strips and quantities, without shared ERP production controls."""
    def __init__(self, order, catalog, covers, parent=None, *, editing=False):
        super().__init__(parent)
        self.order, self.catalog, self.covers = order, catalog, covers
        self.editing = editing
        self.rows = {}
        self.setWindowTitle(local_label(order['id']) + (' · Düzenle' if editing else ' · Sipariş ayrıntısı'))
        self.resize(900, 650)
        layout = QVBoxLayout(self)
        layout.setSpacing(9)
        self.summary = _plain('', 'PageTitle')
        layout.addWidget(self.summary)
        layout.addWidget(_plain(f"Oluşturuldu: {_date(order['created_at'])} · Bitiş: {_date(order['completed_at'])} · Son ZIP: {_date(order['last_zip_at'])}"))
        if editing:
            form = QFormLayout()
            self.reference = QLineEdit(order['kod'])
            self.reference.setMaxLength(500)
            self.price = QDoubleSpinBox()
            self.price.setDecimals(2)
            self.price.setRange(0, 999999999.99)
            self.price.setValue(order['ciro_kurus'] / 100)
            self.price.valueChanged.connect(self.update_summary)
            self.price.setSuffix(' TL')
            self.note = QPlainTextEdit(order['order_note'])
            self.note.setObjectName('OrderNoteInput')
            self.note.setFixedHeight(68)
            form.addRow('Referans', self.reference)
            form.addRow('Ciro', self.price)
            form.addRow('Sipariş notu', self.note)
            layout.addLayout(form)
            if order['completed_at']:
                layout.addWidget(_plain('Bitmiş sipariş düzenleniyor. Durumu değişmez; kitap veya not değişirse yeni ZIP derleyin.', wrap=True))
            search_row = QHBoxLayout()
            self.search = QLineEdit()
            self.search.setObjectName('OrderBookSearch')
            self.search.setPlaceholderText('Kitap adı veya tam kod ile ara')
            self.matches = QComboBox()
            self.matches.setMinimumWidth(240)
            self.add_btn = button('Kitap ekle', 'Accent')
            self.add_btn.clicked.connect(self.add_book)
            self.search.textChanged.connect(self.filter_books)
            self.search.returnPressed.connect(self.add_book)
            search_row.addWidget(self.search, 1)
            search_row.addWidget(self.matches, 1)
            search_row.addWidget(self.add_btn)
            layout.addLayout(search_row)
            self.filter_books('')
        else:
            layout.addWidget(_plain('Referans: ' + (order['kod'] or '—'), 'Title', True))
            if order['order_note']:
                note = QPlainTextEdit(order['order_note'])
                note.setObjectName('OrderNoteInput')
                note.setReadOnly(True)
                note.setFixedHeight(76)
                layout.addWidget(note)
        content = QWidget()
        self.book_layout = QVBoxLayout(content)
        self.book_layout.setContentsMargins(3, 3, 6, 3)
        self.book_layout.setSpacing(6)
        self.book_layout.addStretch()
        area = scrollable(content)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(area, 1)
        grouped = {}
        for item in order['kitaplar']:
            grouped.setdefault(str(item['kod']), {})[item['tur']] = item
        for code, variants in grouped.items():
            self.add_row(code, variants)
        actions = QHBoxLayout()
        actions.addStretch()
        close = button('İptal' if editing else 'Kapat')
        close.clicked.connect(self.reject)
        actions.addWidget(close)
        if editing:
            self.save_btn = button('Değişiklikleri kaydet', 'Success')
            actions.addWidget(self.save_btn)
        layout.addLayout(actions)
        self.update_summary()

    def filter_books(self, query):
        query = query.strip()
        self.matches.clear()
        exact = query.lstrip('#').strip()
        if exact in self.catalog:
            book = self.catalog[exact]
            self.matches.addItem(f"#{exact} · {book.get('isim', exact)}", exact)
        elif len(query) >= 6:
            for code, book in self.catalog.items():
                if metin_eslesiyor_mu(query, dict(book, kod=str(code))):
                    self.matches.addItem(f"#{code} · {book.get('isim', code)}", str(code))
                    if self.matches.count() >= 60:
                        break
        self.add_btn.setEnabled(self.matches.count() > 0)

    def add_book(self):
        code = self.matches.currentData()
        if code is None:
            return
        if code in self.rows:
            row = self.rows[code]
            spin = row['spins']['SB']
            if spin.isEnabled():
                spin.setValue(max(1, spin.value()))
                spin.setFocus()
        else:
            self.add_row(code, {})
        self.search.clear()
        self.update_summary()

    def add_row(self, code, variants):
        saved = next(iter(variants.values()), {})
        book = dict(self.catalog.get(code, {}))
        book.update(kod=code, isim=saved.get('isim', book.get('isim', code)))
        page = int(saved.get('sayfa_birim', book.get('sayfa', 0)) or 0)
        card = QFrame()
        card.setObjectName('PoolOverviewBook')
        card.setMinimumHeight(84)
        line = QHBoxLayout(card)
        line.setContentsMargins(8, 5, 10, 5)
        line.setSpacing(10)
        line.addWidget(cover_label(book, self.covers, 52, 74))
        info = QVBoxLayout()
        info.setSpacing(3)
        info.addWidget(_plain(book['isim'], 'TrackBookName', True))
        info.addWidget(_plain(f'#{code} · {_number(page)} sayfa/adet', 'TrackBookInfo'))
        line.addLayout(info, 1)
        row = dict(card=card, variants=variants, page=page, book=book, spins={})
        self.rows[code] = row
        for kind in ('SB', 'RNK'):
            qty = variants.get(kind, {}).get('adet', 0)
            if self.editing:
                allowed = kind in variants or (code in self.catalog and
                          (kind == 'SB' or bool(book.get('renkli_opsiyon'))))
                controls = QHBoxLayout()
                controls.setSpacing(3)
                controls.addWidget(_plain(kind, 'Title'))
                spin = QSpinBox()
                spin.setObjectName('OrderEditQty')
                spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                spin.lineEdit().setObjectName('OrderEditQtyText')
                spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                spin.setFixedSize(72, 36)
                spin.setRange(0, 100000)
                spin.setValue(qty if variants else (1 if kind == 'SB' else 0))
                minus = button('−', 'OrderEditQtyStep')
                plus = button('+', 'OrderEditQtyStep')
                for control in (minus, plus):
                    control.setFixedSize(30, 36)
                    control.setEnabled(allowed)
                spin.setEnabled(allowed)
                minus.clicked.connect(spin.stepDown)
                plus.clicked.connect(spin.stepUp)
                spin.valueChanged.connect(self.update_summary)
                controls.addWidget(minus)
                controls.addWidget(spin)
                controls.addWidget(plus)
                row['spins'][kind] = spin
                line.addLayout(controls)
            elif qty:
                line.addWidget(_plain(f'{kind}  × {qty}', 'PoolOverviewCounts'))
        if self.editing:
            remove = button('Kaldır', 'PoolDeleteAction')
            remove.clicked.connect(lambda _=False, c=code: self.remove_row(c))
            line.addWidget(remove)
        else:
            total = sum(i['adet'] for i in variants.values())
            pages = sum(i['adet'] * i['sayfa_birim'] for i in variants.values())
            line.addWidget(_plain(f'{total} kitap · {_number(pages)} sayfa', 'Muted'))
        self.book_layout.insertWidget(self.book_layout.count()-1, card)

    def remove_row(self, code):
        row = self.rows.pop(code)
        self.book_layout.removeWidget(row['card'])
        row['card'].deleteLater()
        self.update_summary()

    def values(self):
        items = []
        for code, row in self.rows.items():
            for kind, spin in row['spins'].items():
                if spin.value():
                    items.append(dict(kod=code, tur=kind, adet=spin.value()))
        return dict(kod=self.reference.text(), ciro=self.price.value(),
                    order_note=self.note.toPlainText()), items

    def update_summary(self, *_):
        if not self.editing:
            total = order_totals([self.order])
        else:
            total = dict(kitap=0, sayfa=0, ciro_kurus=round(self.price.value()*100))
            for row in self.rows.values():
                for kind, spin in row['spins'].items():
                    page = row['variants'].get(kind, {}).get('sayfa_birim', row['book'].get('sayfa', row['page']))
                    total['kitap'] += spin.value()
                    total['sayfa'] += spin.value() * int(page or 0)
        self.summary.setText(f"{local_label(self.order['id'])} · {_money(total['ciro_kurus'])} · "
                             f"{_number(total['kitap'])} kitap · {_number(total['sayfa'])} sayfa")


class DerlemeHavuzuView(QWidget):
    def __init__(self, store, pdf_data_dir, parent=None, *, catalog=None, covers=None):
        super().__init__(parent)
        self.store = store
        self.pdf_data_dir = pdf_data_dir
        self.catalog = catalog or (lambda: {})
        self.covers = covers
        self.completed = False
        self._worker = None
        self._progress = None
        self._result = None
        self._rows = []
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(9)
        header = QHBoxLayout()
        self.heading = text('Yerel Derlemeler', 'PageTitle')
        header.addWidget(self.heading)
        header.addWidget(text('Yalnız bu bilgisayar · Firebase ve genel analitik dışında', 'Muted'))
        header.addStretch()
        root.addLayout(header)
        tabs = QHBoxLayout()
        self.group_tabs = QButtonGroup(self)
        self.group_tabs.setExclusive(True)
        self.open_tab = button('Derleme Havuzu', 'OrdersSubnav')
        self.done_tab = button('Bitmiş Derleme Siparişleri', 'OrdersSubnav')
        for completed, tab in ((False, self.open_tab), (True, self.done_tab)):
            tab.setCheckable(True)
            self.group_tabs.addButton(tab)
            tab.clicked.connect(lambda _=False, c=completed: self.set_completed(c))
            tabs.addWidget(tab)
        self.open_tab.setChecked(True)
        tabs.addStretch()
        root.addLayout(tabs)

        metrics = QGridLayout()
        self.metrics = {}
        for col, (key, name) in enumerate((
            ('siparis', 'TOPLAM SİPARİŞ'), ('kitap', 'TOPLAM KİTAP'),
            ('sayfa', 'TOPLAM SAYFA'), ('ciro_kurus', 'TOPLAM CİRO'))):
            card = QFrame()
            card.setObjectName('AnalyticsMetric')
            layout = QVBoxLayout(card)
            layout.setContentsMargins(13, 8, 13, 8)
            layout.addWidget(text(name, 'Muted'))
            value = text('0', 'Kpi')
            layout.addWidget(value)
            self.metrics[key] = value
            metrics.addWidget(card, 0, col)
            metrics.setColumnStretch(col, 1)
        root.addLayout(metrics)

        tools = QHBoxLayout()
        self.detail_btn = button('Sipariş ayrıntısı')
        self.detail_btn.clicked.connect(self.show_detail)
        self.edit_btn = button('Düzenle')
        self.edit_btn.clicked.connect(self.edit_selected)
        self.delete_btn = button('Sil', 'PoolDeleteAction')
        self.delete_btn.clicked.connect(self.delete_selected)
        self.compile_btn = button('Seçili siparişleri ZIP derle', 'Accent')
        self.compile_btn.clicked.connect(self.compile_selected)
        self.complete_btn = button('Fason baskı bitti · Onayla', 'Success')
        self.complete_btn.clicked.connect(self.change_completion)
        for widget in (self.detail_btn, self.edit_btn, self.delete_btn, self.compile_btn, self.complete_btn):
            tools.addWidget(widget)
        tools.addStretch()
        self.refresh_btn = button('Yenile')
        self.refresh_btn.clicked.connect(self.refresh)
        tools.addWidget(self.refresh_btn)
        root.addLayout(tools)

        self.table = QTableWidget(0, 8)
        self.table.setObjectName('LocalDerlemeTable')
        self.table.setHorizontalHeaderLabels([
            'Yerel No', 'Referans', 'Oluşturuldu', 'Kitap', 'Sayfa', 'Ciro',
            'Son ZIP', 'Bitiş onayı'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.cellDoubleClicked.connect(lambda *_: self.show_detail())
        root.addWidget(self.table, 1)
        self.empty = text('', 'Muted')
        root.addWidget(self.empty)
        root.addWidget(text('ZIP oluşturmak siparişi bitirmez. Fason baskı tamamlandığında onaylayın.', 'Muted'))
        self.refresh()

    def set_completed(self, completed):
        self.completed = bool(completed)
        self.open_tab.setChecked(not self.completed)
        self.done_tab.setChecked(self.completed)
        self.complete_btn.setText('Havuza geri al' if completed else 'Fason baskı bitti · Onayla')
        self.refresh()

    def selected(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return [self._rows[i] for i in rows if i < len(self._rows)]

    def _update_actions(self):
        selected = self.selected()
        busy = self._worker is not None
        self.detail_btn.setEnabled(len(selected) == 1 and not busy)
        self.edit_btn.setEnabled(len(selected) == 1 and not busy)
        self.delete_btn.setEnabled(bool(selected) and not busy)
        self.open_tab.setEnabled(not busy)
        self.done_tab.setEnabled(not busy)
        self.compile_btn.setEnabled(bool(selected) and not busy)
        self.complete_btn.setEnabled(bool(selected) and not busy)
        self.refresh_btn.setEnabled(not busy)

    def refresh(self):
        try:
            rows = self.store.list(self.completed)
        except Exception as exc:
            error(self, f'Yerel derleme havuzu okunamadı: {exc}')
            return
        self._rows = rows
        totals = order_totals(rows)
        for key, label in self.metrics.items():
            label.setText(_money(totals[key]) if key == 'ciro_kurus' else _number(totals[key]))
        self.table.clearSelection()
        self.table.setRowCount(len(rows))
        for i, order in enumerate(rows):
            total = order_totals([order])
            values = (local_label(order['id']), order['kod'] or '—', _date(order['created_at']),
                      _number(total['kitap']), _number(total['sayfa']), _money(total['ciro_kurus']),
                      _date(order['last_zip_at']), _date(order['completed_at']))
            for col, value in enumerate(values):
                item = _item(value)
                if col == 6 and order['last_zip_path']:
                    item.setToolTip(order['last_zip_path'])
                self.table.setItem(i, col, item)
        self.empty.setText('Bu grupta henüz sipariş yok.' if not rows else
                           f'{len(rows)} sipariş · Ctrl veya Shift ile çoklu seçim')
        self._update_actions()

    def show_detail(self):
        selected = self.selected()
        if len(selected) != 1 or self._worker is not None:
            return
        dialog = LocalDerlemeDialog(selected[0], self.catalog(), self.covers, self)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def edit_selected(self):
        selected = self.selected()
        if len(selected) != 1 or self._worker is not None:
            return
        order = selected[0]
        catalog = self.catalog()
        dialog = LocalDerlemeDialog(order, catalog, self.covers, self, editing=True)
        def save():
            try:
                info, items = dialog.values()
                self.store.update(order['id'], info, items, catalog, expected=order)
            except Exception as exc:
                error(dialog, exc)
                return
            dialog.accept()
        dialog.save_btn.clicked.connect(save)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
        finally:
            dialog.deleteLater()

    def delete_selected(self):
        selected = self.selected()
        if not selected or self._worker is not None:
            return
        if not confirm(self, f'{len(selected)} yerel sipariş listeden silinsin mi? '
                       'Mevcut ZIP ve PDF dosyaları silinmez.'):
            return
        try:
            self.store.delete_many([order['id'] for order in selected])
        except Exception as exc:
            error(self, exc)
        self.refresh()

    def change_completion(self):
        selected = self.selected()
        if not selected or self._worker is not None:
            return
        target = not self.completed
        action = 'bitmiş olarak onaylansın mı?' if target else 'derleme havuzuna geri alınsın mı?'
        if not confirm(self, f'{len(selected)} seçili fason siparişi {action}'):
            return
        try:
            self.store.set_completed_many([o['id'] for o in selected], target)
        except Exception as exc:
            error(self, exc)
        self.refresh()

    def compile_selected(self):
        orders = self.selected()
        if not orders or self._worker is not None:
            return
        pdfs = PdfKutuphane(Path(self.pdf_data_dir))
        if pdfs.folder is None or not pdfs.folder.is_dir():
            chosen = QFileDialog.getExistingDirectory(self, 'Kitap PDF klasörünü seç', str(Path.home()))
            if not chosen:
                return
            try:
                pdfs.set_folder(chosen)
            except Exception as exc:
                return error(self, exc)
        desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        if not desktop or not Path(desktop).is_dir():
            return error(self, 'Windows Masaüstü klasörüne erişilemiyor.')
        app = QApplication.instance()
        worker = _BatchDerleme(self.store, orders, str(pdfs.folder), desktop, app)
        dialog = QProgressDialog('Yerel ZIP hazırlanıyor...', 'İptal', 0, 0, self)
        dialog.setWindowTitle('Derleme Havuzu')
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        self._worker, self._progress = worker, dialog
        self._result = None
        dialog.canceled.connect(worker.requestInterruption)
        worker.progress.connect(dialog.setLabelText)
        worker.result.connect(self._store_result)
        worker.finished.connect(self._compile_finished)
        app.aboutToQuit.connect(self.stop_worker)
        self._update_actions()
        dialog.show()
        worker.start()

    def stop_worker(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait()

    def _compile_finished(self):
        worker, dialog = self._worker, self._progress
        self._worker = self._progress = None
        QApplication.instance().aboutToQuit.disconnect(self.stop_worker)
        dialog.close()
        dialog.deleteLater()
        worker.deleteLater()
        self.refresh()
        result, self._result = self._result, None
        if result is not None:
            self._compile_result(result)

    def _store_result(self, result):
        self._result = result

    def _compile_result(self, result):
        paths, failed, cancelled = result
        message = f'{len(paths)} ZIP Masaüstüne kaydedildi.'
        if cancelled:
            message += '\nİşlem iptal edildi; tamamlanan ZIP dosyaları korundu.'
        if failed:
            message += '\n\n' + '\n'.join(failed[:12])
            if len(failed) > 12:
                message += f'\n+ {len(failed)-12} hata'
            QMessageBox.warning(self, 'Derleme sonucu', message)
        else:
            QMessageBox.information(self, 'Derleme sonucu', message)
