"""Local PDF first-page cover cache; never uploads PDFs or JPEGs to Firebase.

Reuse the already-supported PdfKutuphane code matcher. A fingerprint of each
source PDF (path/size/mtime) skips unchanged pages, retaining manually imported
JPEG covers as higher-priority overrides. Runs in a QThread from Settings.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from pdf_kitap import PdfKutuphane

CACHE_VERSION=1
MAX_PDFS=4000
MAX_SOURCE_BYTES=850*1024*1024


def _atomic_json(destination,content):
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".alfa_cover_",suffix=".tmp",dir=destination.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(content,out,ensure_ascii=False,indent=2)
        os.replace(temp,destination)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def render_first_page(source,target):
    """Render using the official QtPdf module; original source is read-only."""
    pdf=QPdfDocument()
    try:
        pdf.load(str(source))
        if pdf.pageCount()<1:
            raise ValueError("PDF ilk sayfası okunamıyor (şifreli/bozuk olabilir)")
        points=pdf.pagePointSize(0)
        width=max(1,float(points.width()))
        height=max(1,float(points.height()))
        # Preserve page aspect ratio, and bound memory/thumbnail size.
        factor=min(480/width,690/height)
        size=QSize(max(1,int(width*factor)),max(1,int(height*factor)))
        picture=pdf.render(0,size)
        if picture.isNull():
            raise ValueError("PDF kapağı oluşturulamadı")
        # PDFium page backgrounds can be transparent; JPEG lacks alpha.
        # Paint on white before encoding or text-only covers become black.
        opaque=QImage(size,QImage.Format.Format_RGB32)
        opaque.fill(Qt.GlobalColor.white)
        painter=QPainter(opaque)
        try:painter.drawImage(0,0,picture)
        finally:painter.end()
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix=".alfa_pdf_",suffix=".tmp",dir=target.parent)
        os.close(fd)
        try:
            if not opaque.save(temp,"JPEG",83):
                raise OSError("JPEG kapağı diske kaydedilemedi")
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    finally:
        pdf.close()


def refresh_pdf_covers(data_dir,book_codes,progress=None):
    """Incrementally build one JPEG per numeric book code, with metadata cache.

    progress(done,total) is optional and must remain pure; when called from
    QThread do not mutate Qt GUI widgets directly.
    """
    data_dir=Path(data_dir)
    pdf=PdfKutuphane(data_dir)
    if not pdf.folder:
        return {"matched":0,"created":0,"unchanged":0,"manual":0,
                "missing":len(book_codes),"errors":0,"message":"PDF klasörü seçilmedi"}
    pdf.scan()
    folder=data_dir/"kapaklar"/"pdf_otomatik"
    folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/"alfa_pdf_kapak_onbellek.json"
    try:
        saved=json.loads(manifest.read_text(encoding="utf-8"))
        recorded=saved.get("entries",{}) if saved.get("version")==CACHE_VERSION else {}
    except (OSError,ValueError,TypeError,AttributeError):
        recorded={}
    if not isinstance(recorded,dict):
        recorded={}
    current={}
    codes=sorted({str(int(x)) for x in book_codes if str(x).isdigit()},key=int)
    if len(codes)>MAX_PDFS:
        raise ValueError("PDF kapak taraması güvenlik sınırını aşıyor")
    stats={"matched":0,"created":0,"unchanged":0,
           "manual":0,"missing":0,"errors":0}
    manual=data_dir/"kapaklar"
    pdf_folder=pdf.folder
    for index,code in enumerate(codes,1):
        src=pdf.find(code)
        if not src:
            stats["missing"]+=1
            if progress:progress(index,len(codes))
            continue
        stats["matched"]+=1
        try:
            stat=src.stat()
            # Canonical relative location differentiates same code/name in
            # nested directories; never match by substring alone.
            signature=[str(pdf_folder.resolve()),str(src.relative_to(pdf_folder)),
                       stat.st_size,stat.st_mtime_ns]
            target=folder/(code+".jpg")
            manual_exists=any((manual/(code+ext)).exists()
                for ext in (".jpg",".jpeg",".png",".webp",".bmp"))
            if manual_exists:
                # A user-supplied cover has higher priority, so do not render
                # its PDF at all; avoid waste when hundreds were hand-curated.
                stats["manual"]+=1
                if recorded.get(code)==signature and target.exists():
                    current[code]=signature
                if progress:progress(index,len(codes))
                continue
            if (recorded.get(code)==signature and target.exists() and
                    target.stat().st_size>0):
                stats["unchanged"]+=1
                current[code]=signature
            elif stat.st_size>MAX_SOURCE_BYTES:
                stats["errors"]+=1
            else:
                render_first_page(src,target)
                current[code]=signature
                stats["created"]+=1
        except (OSError,ValueError,RuntimeError,PermissionError):
            stats["errors"]+=1
            if recorded.get(code) and (folder/(code+".jpg")).exists():
                current[code]=recorded[code]
        if progress:progress(index,len(codes))
    _atomic_json(manifest,{"version":CACHE_VERSION,"entries":current,
                           "source_folder":str(pdf_folder)})
    # Don't delete old generated JPEGs automatically. Some PDFs may have
    # been moved temporarily, and manual overrides remain untouched.
    return stats
