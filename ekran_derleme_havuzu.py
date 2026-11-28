"""Yöneticiye özel, çevrimdışı fason sipariş takibi."""
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QStandardPaths
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QVBoxLayout, QWidget, QPlainTextEdit)

from pdf_kitap import PdfKutuphane
from siparis_derleme_havuzu import compile_snapshot, local_label, order_totals
from widgets import button, confirm, error, text


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
                self.store.record_zip(sid, path)
            except Exception:
                failed.append(f'{label}: ZIP kaydedildi fakat yerel derleme tarihi kaydedilemedi.')
        self.result.emit((succeeded, failed, self.isInterruptionRequested()))


class DerlemeHavuzuView(QWidget):
    def __init__(self, store, pdf_data_dir, parent=None):
        super().__init__(parent)
        self.store = store
        self.pdf_data_dir = pdf_data_dir
        self.completed = False
        self._worker = None
        self._progress = None
        self._result = None
        self._rows = []
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(9)
        header = QHBoxLayout()
        self.heading = text('Derleme Havuzu', 'PageTitle')
        header.addWidget(self.heading)
        header.addWidget(text('Yalnız bu bilgisayar · Firebase ve genel analitik dışında', 'Muted'))
        header.addStretch()
        root.addLayout(header)

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
        self.compile_btn = button('Seçili siparişleri ZIP derle', 'Accent')
        self.compile_btn.clicked.connect(self.compile_selected)
        self.complete_btn = button('Fason baskı bitti · Onayla', 'Success')
        self.complete_btn.clicked.connect(self.change_completion)
        for widget in (self.detail_btn, self.compile_btn, self.complete_btn):
            tools.addWidget(widget)
        tools.addStretch()
        self.refresh_btn = button('Yenile')
        self.refresh_btn.clicked.connect(self.refresh)
        tools.addWidget(self.refresh_btn)
        root.addLayout(tools)

        self.table = QTableWidget(0, 8)
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
        self.heading.setText('Bitmiş Derleme Siparişleri' if completed else 'Derleme Havuzu')
        self.complete_btn.setText('Havuza geri al' if completed else 'Fason baskı bitti · Onayla')
        self.refresh()

    def selected(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return [self._rows[i] for i in rows if i < len(self._rows)]

    def _update_actions(self):
        selected = self.selected()
        busy = self._worker is not None
        self.detail_btn.setEnabled(len(selected) == 1)
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
        if len(selected) != 1:
            return
        order = selected[0]
        dialog = QDialog(self)
        dialog.setWindowTitle(local_label(order['id']) + ' · Yerel sipariş')
        dialog.resize(700, 460)
        layout = QVBoxLayout(dialog)
        total = order_totals([order])
        layout.addWidget(text(f"{local_label(order['id'])} · {_money(total['ciro_kurus'])} · "
                              f"{_number(total['kitap'])} kitap · {_number(total['sayfa'])} sayfa", 'PageTitle'))
        lines = [f"Referans: {order['kod'] or '—'}", f"Oluşturuldu: {_date(order['created_at'])}",
                 f"Bitiş onayı: {_date(order['completed_at'])}", '',
                 'KİTAPLAR']
        for item in order['kitaplar']:
            lines.append(f"#{item['kod']} · {item['isim']} · {item['tur']} × {item['adet']} · "
                         f"{item['sayfa_birim']} sayfa/adet")
        if order['order_note']:
            lines.extend(['', 'SİPARİŞ NOTU', order['order_note']])
        if order['last_zip_path']:
            lines.extend(['', 'SON ZIP', order['last_zip_path']])
        body = QPlainTextEdit('\n'.join(lines))
        body.setReadOnly(True)
        layout.addWidget(body, 1)
        close = button('Kapat')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

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
