"""Kod bazlı yerel PDF kütüphanesi; Qt bağımlılığı yoktur.

Örnekler: 31.pdf, 031.pdf, kitap_31.pdf, kod-31.pdf, 31-endodonti.pdf.
31 kodu asla 131 / 310 numaralı dosyayla eşleşmez.
"""
from pathlib import Path
import json
import os
import re
import tempfile

PDF_PREFIXES = ('kitap', 'kod', 'book', 'pdf', 'alfa')


def match_score(stem, code):
    """Dosya adını kodla eşleştir; 0 yanlış, düşük skor daha kesin."""
    key = str(code).strip()
    if not key.isdigit():
        return None
    pattern = rf'0*{int(key)}'
    if re.fullmatch(pattern, stem, re.I):
        return 0
    # Dosyada kod tek bir belirgin sayısal parça olarak bulunmalı.
    parts = re.findall(r'\d+', stem)
    if len(parts) != 1 or int(parts[0]) != int(key):
        return None
    name = re.sub(r'[\s._()\[\]−\-]+', ' ', stem.lower()).strip()
    words = name.split()
    if words and words[0] in PDF_PREFIXES:
        return 1
    if words and words[-1] in ('kitap', 'pdf', 'baski'):
        return 2
    return 3


class PdfKutuphane:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.settings_file = self.data_dir / 'alfa_pdf_ayarlari.json'
        self.folder = None
        self._index = {}
        self._read_settings()

    def _read_settings(self):
        try:
            stored = json.loads(self.settings_file.read_text(encoding='utf-8'))
            folder = Path(stored.get('pdf_klasoru', ''))
            if folder.is_dir():
                self.folder = folder.resolve()
        except (OSError, ValueError, TypeError):
            pass

    def set_folder(self, path):
        folder = Path(path).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError('PDF klasörü bulunamadı.')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.alfa_pdf_', suffix='.tmp', dir=self.data_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'pdf_klasoru': str(folder)}, handle, ensure_ascii=False)
            os.replace(name, self.settings_file)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.folder = folder
        self.scan()

    def scan(self):
        self._index = {}
        if self.folder is None or not self.folder.is_dir():
            return
        # Klasör içinde alt klasörler de desteklenir.
        for file in sorted(self.folder.rglob('*')):
            if file.is_file() and file.suffix.lower() == '.pdf':
                for part in re.findall(r'\d+', file.stem):
                    code = str(int(part))
                    score = match_score(file.stem, code)
                    if score is None:
                        continue
                    prev = self._index.get(code)
                    if prev is None or (score, str(file)) < (prev[0], str(prev[1])):
                        self._index[code] = score, file

    def find(self, code):
        if self.folder is None or not self.folder.is_dir():
            return None
        key = str(int(code)) if str(code).isdigit() else str(code)
        found = self._index.get(key)
        if found is None or not found[1].is_file():
            self.scan()
            found = self._index.get(key)
        return found[1] if found else None

    def resolve_many(self, codes):
        found, missing = [], []
        seen = set()
        for code in codes:
            key = str(code)
            if key in seen:
                continue
            seen.add(key)
            file = self.find(key)
            if file:
                found.append(file)
            else:
                missing.append(key)
        return found, missing
