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
from PySide6.QtGui import QImage, QPainter, QTransform
from PySide6.QtPdf import QPdfDocument

from pdf_kitap import PdfKutuphane

CACHE_VERSION=6
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
        landscape=width>height
        # Size for the FINAL upright picture (rotated dimensions swapped).
        fit_w,fit_h=(height,width) if landscape else (width,height)
        factor=min(480/fit_w,690/fit_h)
        size=QSize(max(1,int(width*factor)),max(1,int(height*factor)))
        picture=pdf.render(0,size)
        if picture.isNull():
            raise ValueError("PDF kapağı oluşturulamadı")
        if landscape:
            # A landscape first page is physically a rotated portrait cover.
            # Correct orientation for these landscape-source covers is -90 degrees.
            # Never crop or stretch the content.
            picture=picture.transformed(
                QTransform().rotate(-90),
                Qt.TransformationMode.SmoothTransformation)
            size=picture.size()
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
    """Safely refresh matching PDF covers using explicit code AND full title.

    Accepts legacy list[str] or catalog list[{'kod': ..., 'isim': ...}].
    Nonmatching generated thumbnails remain on disk for recovery, but are
    not published in the active manifest (no stale/wrong cover display).
    """
    data_dir=Path(data_dir)
    books={}
    for book in book_codes:
        if isinstance(book,dict):
            code=str(book.get("kod") or book.get("code") or "").strip()
            title=str(book.get("isim") or book.get("name") or "").strip()
        else:
            code=str(book).strip()
            title=""
        if code.isdecimal():
            books[str(int(code))]=title
    if len(books)>MAX_PDFS:
        raise ValueError("PDF kapak taraması güvenlik sınırını aşıyor")
    pdf=PdfKutuphane(data_dir)
    if not pdf.folder:
        return {"matched":0,"created":0,"unchanged":0,"manual":0,
                "missing":len(books),"errors":0,"message":"PDF klasörü seçilmedi"}
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
    codes=sorted(books,key=int)
    stats={"matched":0,"created":0,"unchanged":0,"manual":0,
           "missing":0,"errors":0,"missing_examples":[],"error_examples":[],
           "pdf_found":len(pdf._files),"unmatched_pdf":0,
           "unmatched_pdf_examples":[],"catalog_without_pdf":0}
    used_sources={}
    manual=data_dir/"kapaklar"
    # One directory scan, not one scan per book (thousands of images can exist).
    manual_codes={
        str(int(path.stem)) for path in manual.iterdir()
        if path.is_file() and path.stem.isdecimal()
        and path.suffix.lower() in (".jpg",".jpeg",".png",".webp",".bmp")
    }
    pdf_folder=pdf.folder
    for index,code in enumerate(codes,1):
        title=books[code]
        try:
            src=pdf.find(code,title=title)
            if not src:
                stats["missing"]+=1
                if len(stats["missing_examples"])<25:
                    stats["missing_examples"].append(f"#{code} {title}"[:135])
                continue
            # A source cannot silently become two unrelated catalog covers.
            source_key=str(src.resolve()).casefold()
            previous=used_sources.get(source_key)
            if previous is not None and previous!=code:
                raise ValueError(
                    "PDF başka kitap koduyla da eşleşti: #"+previous+
                    " (dosya: "+src.name+")")
            used_sources[source_key]=code
            stats["matched"]+=1
            stat=src.stat()
            signature=[str(pdf_folder.resolve()),str(src.relative_to(pdf_folder)),
                       stat.st_size,stat.st_mtime_ns]
            target=folder/(code+".jpg")
            manual_exists=code in manual_codes
            if manual_exists:
                stats["manual"]+=1
                # The manual cover takes precedence, regardless of the auto
                # cache state. No need to render a redundant image.
                continue
            if (recorded.get(code)==signature and target.exists()
                and target.stat().st_size>0):
                stats["unchanged"]+=1
                current[code]=signature
            elif stat.st_size>MAX_SOURCE_BYTES:
                raise ValueError("PDF boyutu güvenlik sınırını aşıyor")
            else:
                render_first_page(src,target)
                current[code]=signature
                stats["created"]+=1
        except (OSError,ValueError,RuntimeError,PermissionError) as exc:
            stats["errors"]+=1
            if len(stats["error_examples"])<25:
                stats["error_examples"].append(f"#{code} {title}: {str(exc)[:160]}")
            # If thumbnail creation fails, a stale old auto-cover is NOT
            # included in the current manifest (it is retained for recovery).
        finally:
            if progress:
                progress(index,len(codes))
    matched_sources=set(used_sources)
    unmatched_sources=[
        str(path.relative_to(pdf_folder)) for path in pdf._files
        if str(path.resolve()).casefold() not in matched_sources
    ]
    stats["unmatched_pdf"]=len(unmatched_sources)
    stats["unmatched_pdf_examples"]=unmatched_sources[:25]
    stats["catalog_without_pdf"]=stats["missing"]
    # 'missing' is a catalog coverage statistic, not a PDF import error.
    # Real errors are in 'errors'; PDF names needing attention in 'unmatched_pdf'.
    # One atomic write: Covers may continue showing old manifest until this
    # validated new manifest is fully available.
    _atomic_json(manifest,{"version":CACHE_VERSION,"entries":current,
                           "source_folder":str(pdf_folder)})
    _atomic_json(data_dir/"alfa_pdf_kapak_tarama_raporu.json",{
        "summary":stats,"source_folder":str(pdf_folder),
        "hint":"Eşleşmeyen PDF örneklerini inceleyin; katalogda PDF bulunmaması hata değildir. 31-endodonti.pdf, kitap_31.pdf ve tam kitap adları desteklenir."
    })
    return stats
