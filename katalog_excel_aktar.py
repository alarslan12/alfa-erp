"""Preview a book Excel in an isolated temporary ERP data directory."""
from pathlib import Path
import tempfile

def preview_excel_catalog(path):
    from database import ERPDatabase
    source=Path(path)
    if not source.is_file() or source.suffix.lower()!=".xlsx":
        raise ValueError("Yalnızca .xlsx katalog dosyası seçebilirsiniz.")
    if source.stat().st_size>35*1024*1024:
        raise ValueError("Excel dosyası 35 MB sınırını aşıyor.")
    with tempfile.TemporaryDirectory(prefix="alfa_excel_preview_") as safe_dir:
        parsed=ERPDatabase(str(source),data_dir=safe_dir)
        rows=[{
            "code":str(book["kod"]),
            "name":str(book["isim"]),
            "group_name":str(book["grup"]),
            "page_count":int(book["sayfa"] or 0),
            "supports_color":bool(book["renkli_opsiyon"]),
        } for book in parsed.kitaplar]
    if not 1<=len(rows)<=2000:
        raise ValueError("Excel 1–2000 geçerli kitap içermeli.")
    keys=[row["code"] for row in rows]
    if len(keys)!=len(set(keys)):
        raise ValueError("Excel'de tekrarlanan kitap kodu var.")
    return rows
