"""Local outsourced printing bundle; no Firebase traffic and no original PDF copies.

Every source page is rasterized into a new image-only PDF. This deliberately
drops source Info/XMP, embedded files, scripts, hidden text/layers, form fields,
bookmarks and annotations not visible in the rendered page. Printed/visible
watermarks and personally identifying content in page pixels CANNOT be removed.
Raster output is no longer searchable; visual review is still recommended.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from pdf_kitap import PdfKutuphane


class DerlemeHatasi(ValueError):
    """Do not publish an incomplete outsourced printing package."""


def _check_cancel(cancel):
    if cancel is not None and cancel():
        raise InterruptedError('Sipariş derlemesi iptal edildi; eksik ZIP kaydedilmedi.')


def _zip_entry(name):
    """No source path, creation time, local permissions or username in ZIP headers."""
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_DEFLATED
    entry.create_system = 0
    entry.external_attr = 0
    entry.comment = b''
    entry.extra = b''
    return entry


def _add_file(archive, source, name, cancel):
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


def _rasterize_pdf(source, destination, kind, progress=None, cancel=None):
    """Page pixels only: never copy a source PDF object, metadata or attachment.

    Uses QtPdf and QPdfWriter already shipped with Personel/Yönetici. 300 DPI
    keeps ordinary type readable in print; huge pages are rejected instead of
    exhausting RAM. Color copies retain RGB; SB output is grayscale.
    """
    from PySide6.QtCore import QByteArray, QMarginsF, QRectF, QSize, Qt
    from PySide6.QtGui import QImage, QPageSize, QPdfWriter, QPainter
    from PySide6.QtPdf import QPdfDocument

    pdf = QPdfDocument()
    writer = None
    painter = QPainter()
    try:
        _check_cancel(cancel)
        pdf.load(str(source))
        if pdf.status() != QPdfDocument.Status.Ready or pdf.pageCount() <= 0:
            raise DerlemeHatasi('PDF okunamıyor, hasarlı veya parola korumalı.')
        if pdf.pageCount() > 10000:
            raise DerlemeHatasi('PDF güvenli sayfa sınırını aşıyor (10.000).')

        writer = QPdfWriter(str(destination))
        writer.setResolution(300)
        writer.setAuthor('')
        writer.setCreator('')
        writer.setTitle('')
        writer.setDocumentXmpMetadata(QByteArray())
        if kind == 'SB':
            writer.setColorModel(QPdfWriter.ColorModel.Grayscale)

        for page in range(pdf.pageCount()):
            _check_cancel(cancel)
            pts = pdf.pagePointSize(page)
            width, height = pts.width(), pts.height()
            if not (math.isfinite(width) and math.isfinite(height)
                    and 30 <= width <= 4000 and 30 <= height <= 4000):
                raise DerlemeHatasi('PDF geçersiz veya aşırı büyük sayfa boyutu içeriyor.')
            pixels = QSize(max(1, round(width * 300 / 72)),
                           max(1, round(height * 300 / 72)))
            if pixels.width() * pixels.height() > 24_000_000:
                raise DerlemeHatasi('Sayfa 300 DPI güvenli bellek sınırını aşıyor.')
            if not writer.setPageSize(QPageSize(pts, QPageSize.Unit.Point)):
                raise DerlemeHatasi('PDF sayfa boyutu ayarlanamadı.')
            if not writer.setPageMargins(QMarginsF(0, 0, 0, 0)):
                raise DerlemeHatasi('PDF sayfa kenarları ayarlanamadı.')
            if page == 0:
                if not painter.begin(writer):
                    raise DerlemeHatasi('Anonim PDF oluşturulamadı.')
            elif not writer.newPage():
                raise DerlemeHatasi('PDF sayfası oluşturulamadı.')

            image = pdf.render(page, pixels)
            if image.isNull():
                raise DerlemeHatasi('PDF sayfası görüntülenemedi.')
            # Transparent backgrounds are composited onto white paper.
            frame = QImage(pixels, QImage.Format.Format_RGB32)
            frame.fill(Qt.GlobalColor.white)
            layer = QPainter(frame)
            layer.drawImage(0, 0, image)
            layer.end()
            del image
            if kind == 'SB':
                frame = frame.convertToFormat(QImage.Format.Format_Grayscale8)
            painter.drawImage(QRectF(0, 0, writer.width(), writer.height()), frame)
            del frame
            if progress is not None and (page == 0 or (page + 1) % 10 == 0 or page + 1 == pdf.pageCount()):
                progress(page + 1, pdf.pageCount())
        if not painter.end():
            raise DerlemeHatasi('PDF çıktısı tamamlanamadı.')
        del writer
        writer = None
        if not destination.is_file() or destination.stat().st_size < 128:
            raise DerlemeHatasi('Anonim PDF boş veya geçersiz üretildi.')
        # Validate PDF can be opened and retains every page.
        check = QPdfDocument()
        try:
            check.load(str(destination))
            if check.status() != QPdfDocument.Status.Ready or check.pageCount() != pdf.pageCount():
                raise DerlemeHatasi('Anonim PDF doğrulaması başarısız.')
        finally:
            check.close()
    except Exception:
        if painter.isActive():
            painter.end()
        if writer is not None:
            del writer
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    finally:
        pdf.close()


def derle_siparis(order, catalog, pdf_folder, desktop, *, codes=None,
                  progress=None, cancel=None, sanitize=None):
    """Return the final local ZIP path, or leave no ZIP on any failure.

    codes=None exports every item. A sequence exports only selected book codes,
    with both SB and RNK variants and all their quantities. No source path or
    real book title is included in the archive.
    """
    sid = str(order.get('id', '')).strip()
    if not re.fullmatch(r'[0-9]{1,10}', sid):
        raise DerlemeHatasi('Geçerli bir sayısal sipariş numarası bulunamadı.')
    root = Path(pdf_folder).expanduser().resolve()
    desktop = Path(desktop).expanduser()
    if not root.is_dir():
        raise DerlemeHatasi('Yerel kitap PDF klasörü bulunamadı.')
    if not desktop.is_dir():
        raise DerlemeHatasi('Windows Masaüstü klasörü bulunamadı.')

    selected = None if codes is None else {str(code) for code in codes}
    if selected is not None and not selected:
        raise DerlemeHatasi('Derlemek için en az bir kitap seçin.')
    amounts = {}
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
        if not source.is_file() or not source.is_relative_to(root):
            raise DerlemeHatasi('PDF kaynağı belirlenen yerel klasörün dışında.')
        resolved.append((source, code, kind, qty))

    _check_cancel(cancel)
    base = 'Sipariş ' + sid
    with tempfile.TemporaryDirectory(prefix='alfa_siparis_derleme_') as workspace:
        workspace = Path(workspace)
        clean_cache = {}
        aliases = set()
        entries = []
        total = len(resolved)
        for index, (source, code, kind, qty) in enumerate(resolved, 1):
            _check_cancel(cancel)
            # Sanitize each print mode independently: SB grayscale, RNK color.
            cache_key = (source, kind)
            if cache_key not in clean_cache:
                clean = workspace / (secrets.token_hex(12) + '.pdf')
                method = sanitize or _rasterize_pdf
                try:
                    method(source, clean, kind,
                           progress=(lambda page, pages, idx=index:
                                     progress(idx, total, page, pages) if progress else None),
                           cancel=cancel)
                except Exception as exc:
                    raise DerlemeHatasi('Kitap kodu ' + code + ' anonimleştirilemedi: ' + str(exc)) from exc
                if not clean.is_file() or clean.stat().st_size == 0:
                    raise DerlemeHatasi('Kitap kodu ' + code + ' anonim PDF oluşturamadı.')
                clean_cache[cache_key] = clean

            alias = _random_alias(aliases)
            filename = 'DOSYA_' + alias + ('__' + str(qty) + '_ADET_BASILACAK' if qty > 1 else '') + '.pdf'
            folder = 'Siyah' if kind == 'SB' else 'Renkli'
            entries.append((clean_cache[cache_key], folder + '/' + filename, qty, folder))

        order_code = str(order.get('kod') or '').replace('\r', ' ').replace('\n', ' ').strip()
        note = [
            'ALFA ERP - FASON BASKI TALIMATI',
            'Siparis No: ' + sid,
            'Siparis Kodu: ' + order_code if order_code else 'Siparis Kodu: Belirtilmedi',
            '',
            'Her dosya tek PDF kopyasidir; yanindaki adet kadar basiniz.',
            'Siyah klasoru siyah-beyaz; Renkli klasoru renkli basilacaktir.',
            '',
        ]
        for _clean, name, qty, folder in entries:
            note.append(name + ' -> ' + str(qty) + ' ADET BASILACAK')
        note.extend(('', 'TOPLAM DOSYA CESIDI: ' + str(len(entries)),
                     'TOPLAM BASILACAK KITAP: ' + str(sum(x[2] for x in entries)), ''))
        temp_zip = workspace / 'derleme.zip'
        with ZipFile(temp_zip, 'w', compression=ZIP_DEFLATED, compresslevel=6,
                     allowZip64=True) as archive:
            for folder in ('Siyah/', 'Renkli/'):
                archive.writestr(_zip_entry(folder), b'')
            for clean, name, _qty, _folder in entries:
                _add_file(archive, clean, name, cancel)
            archive.writestr(_zip_entry('BASKI_TALIMATI.txt'),
                             '\r\n'.join(note).encode('utf-8-sig'))
        _check_cancel(cancel)

        # Reserve a unique destination without clobbering an earlier order ZIP.
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
