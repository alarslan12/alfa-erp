"""Fast local outsourcing bundle: source PDFs are stored WITHOUT modification.

Only archive entry names are randomized. The original PDF bytes, including any
metadata, watermarks, attachments, annotations and other PDF content, remain
unchanged. No PDF is opened, rendered, re-encoded or uploaded to Firebase.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from pdf_kitap import PdfKutuphane


class DerlemeHatasi(ValueError):
    """Do not publish an incomplete outsourced printing package."""


def _check_cancel(cancel):
    if cancel is not None and cancel():
        raise InterruptedError('Sipariş derlemesi iptal edildi; eksik ZIP kaydedilmedi.')


def _zip_entry(name):
    """No source filename, timestamp or local permissions in the ZIP entry."""
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_STORED
    entry.create_system = 0
    entry.external_attr = 0
    entry.comment = b''
    entry.extra = b''
    return entry


def _add_file(archive, source, name, cancel):
    """Stream raw bytes directly to ZIP, no rasterization or compression overhead."""
    _check_cancel(cancel)
    with open(source, 'rb') as input_file, archive.open(_zip_entry(name), 'w', force_zip64=True) as output:
        while True:
            _check_cancel(cancel)
            data = input_file.read(1024 * 1024)
            if not data:
                break
            output.write(data)


def _random_alias(seen):
    while True:
        alias = secrets.token_hex(6).upper()
        if alias not in seen:
            seen.add(alias)
            return alias


def _book_pages(item, catalog):
    """Match Database._book_page_count: prefer historical per-book snapshot."""
    code = str(item.get('kod') or '').strip()
    raw = item.get('sayfa_birim') if item.get('sayfa_birim') is not None else item.get('sayfa')
    try:
        saved = max(0, int(raw or 0))
    except (TypeError, ValueError):
        saved = 0
    if saved:
        return saved
    try:
        return max(0, int((catalog.get(code) or {}).get('sayfa') or 0))
    except (TypeError, ValueError):
        return 0


def derle_siparis(order, catalog, pdf_folder, desktop, *, codes=None,
                  progress=None, cancel=None):
    """Export one ZIP with the original PDF bytes. No incomplete ZIP on failure.

    codes=None exports every book. Specifying codes exports those selected
    books including all of their SB/RNK variants and quantities.
    """
    sid = str(order.get('id', '')).strip()
    if not re.fullmatch(r'[0-9]{1,10}', sid):
        raise DerlemeHatasi('Geçerli bir sayısal sipariş numarası bulunamadı.')
    root = Path(pdf_folder).expanduser().resolve()
    desktop = Path(desktop).expanduser().resolve()
    if not root.is_dir():
        raise DerlemeHatasi('Yerel kitap PDF klasörü bulunamadı.')
    if not desktop.is_dir():
        raise DerlemeHatasi('Windows Masaüstü klasörü bulunamadı.')

    selected = None if codes is None else {str(code) for code in codes}
    if selected is not None and not selected:
        raise DerlemeHatasi('Derlemek için en az bir kitap seçin.')
    amounts = {}
    total_pages = 0
    for item in order.get('kitaplar', []):
        code = str(item.get('kod', ''))
        if selected is not None and code not in selected:
            continue
        kind = str(item.get('tur', 'SB')).upper()
        if kind not in ('SB', 'RNK'):
            raise DerlemeHatasi('Kitap baskı türü geçersiz.')
        try:
            qty = int(item.get('adet', 0))
        except (ValueError, TypeError):
            raise DerlemeHatasi('Kitap baskı adedi geçersiz.') from None
        if qty < 0:
            raise DerlemeHatasi('Kitap baskı adedi negatif olamaz.')
        if qty:
            key = (code, kind)
            amounts[key] = amounts.get(key, 0) + qty
            total_pages += qty * _book_pages(item, catalog)
    items = [(code, kind, qty) for (code, kind), qty in amounts.items()]
    if not items:
        raise DerlemeHatasi('Seçilen kitaplarda derlenecek baskı bulunamadı.')
    if selected is not None and selected - {code for code, _, _ in items}:
        raise DerlemeHatasi('Seçilen kitaplardan biri bu siparişte bulunamadı.')

    library = PdfKutuphane(root)
    library.folder = root
    library.scan()
    resolved = []
    for code, kind, qty in items:
        title = str((catalog.get(code) or {}).get('isim') or '')
        source = library.find(code, title=title)
        if source is None:
            raise DerlemeHatasi('Sipariş #' + sid + ' · PDF bulunamadı: kitap kodu ' + code)
        source = Path(source).resolve()
        if not source.is_file() or not source.is_relative_to(root) or source.stat().st_size == 0:
            raise DerlemeHatasi('PDF kaynağı geçersiz, boş veya yerel kitap klasörünün dışında.')
        resolved.append((source, kind, qty))

    _check_cancel(cancel)
    aliases = set()
    entries = []
    for source, kind, qty in resolved:
        alias = _random_alias(aliases)
        filename = str(qty) + ' ADET - DOSYA_' + alias + '.pdf'
        folder = 'Siyah' if kind == 'SB' else 'Renkli'
        entries.append((source, folder + '/' + filename, qty))

    order_code = str(order.get('kod') or '').replace('\r', ' ').replace('\n', ' ').strip()
    note = [
        'Sipariş Kodu: ' + (order_code if order_code else 'Belirtilmedi'),
        'Toplam Sayfa Sayısı: ' + str(total_pages),
        'Toplam Kitap Sayısı: ' + str(sum(x[2] for x in entries)),
    ]
    order_note = str(order.get('order_note') or '').strip()
    if order_note:
        note.extend(['', 'Sipariş Notu:', order_note])

    base = 'Sipariş ' + sid
    # Keep the temporary archive on the same drive as the Desktop, so the
    # final rename is fast and never uses a slow cross-volume copy.
    with tempfile.TemporaryDirectory(prefix='.alfa_siparis_derleme_', dir=desktop.parent) as workspace:
        temp_zip = Path(workspace) / 'derleme.zip'
        with ZipFile(temp_zip, 'w', compression=ZIP_STORED, allowZip64=True) as archive:
            for folder in ('Siyah/', 'Renkli/'):
                archive.writestr(_zip_entry(folder), b'')
            total = len(entries)
            for index, (source, name, _qty) in enumerate(entries, 1):
                _add_file(archive, source, name, cancel)
                if progress is not None:
                    progress(index, total, 1, 1)
            archive.writestr(_zip_entry('BASKI_TALIMATI.txt'),
                             '\r\n'.join(note).encode('utf-8-sig'))
        _check_cancel(cancel)

        # Never overwrite a previous bundle.
        for i in range(1, 10000):
            destination = desktop / (base + ('' if i == 1 else ' (' + str(i) + ')') + '.zip')
            try:
                fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
                break
            except FileExistsError:
                continue
        else:
            raise DerlemeHatasi('Masaüstünde yeni dosya adı oluşturulamadı.')
        try:
            os.replace(temp_zip, destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return destination
