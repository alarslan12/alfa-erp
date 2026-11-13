"""Kod bazlı yerel PDF kütüphanesi; Qt bağımlılığı yoktur.

Örnekler: 31.pdf, 031.pdf, kitap_31.pdf, kod-31.pdf, 31-endodonti.pdf.
31 kodu asla 131 / 310 numaralı dosyayla eşleşmez.
"""
from pathlib import Path
import json
import os
import re
import tempfile
import unicodedata

PDF_PREFIXES = ('kitap', 'kod', 'book', 'pdf', 'alfa')
_COVER_SUFFIXES = ('kapak', 'cover', 'baski', 'pdf')


def _title_words(value):
    raw = unicodedata.normalize(
        'NFKD', str(value or '').replace('İ', 'I').replace('ı', 'i'))
    folded = ''.join(ch for ch in raw.casefold()
                     if not unicodedata.combining(ch))
    return re.findall(r'[a-z0-9]+', folded)


def _title_keys(value):
    """Only exact book-name variants; never guess from volume alone."""
    words = _title_words(value)
    while words and words[-1] in _COVER_SUFFIXES:
        words.pop()
    if not words:
        return set()
    variants = [words]
    # Excel: DUSDATA DENTTEST 12; a PDF may say only DENTTEST 12.
    if len(words) >= 3 and words[:2] == ['dusdata', 'denttest']:
        variants.append(words[1:])
    keys = set()
    for parts in variants:
        keys.add(''.join(parts))
        # "ADÇ Cerrahi" can be printed as just "Cerrahi" on the cover.
        if len(parts) >= 4 and 'adc' in parts:
            keys.add(''.join(word for word in parts if word != 'adc'))
    return keys


def match_score(stem, code):
    """Only explicitly placed numeric catalog codes, not series/volume IDs."""
    key = str(code).strip()
    if not key.isdecimal():
        return None
    number = int(key)
    if re.fullmatch(rf'0*{number}', stem, re.I):
        return 0
    # 31-endodonti.pdf, 031 Endodonti.pdf are explicit book codes.
    if re.match(rf'^\s*0*{number}(?=$|[^0-9])', stem, re.I):
        return 1
    # kitap_31.pdf, kod-31-endodonti.pdf are explicit book codes.
    if re.match(
            rf'^\s*(?:kitap|kod|book|pdf|alfa)[\s._-]*0*{number}(?=$|[^0-9])',
            stem, re.I):
        return 1
    return None


class PdfKutuphane:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.settings_file = self.data_dir / 'alfa_pdf_ayarlari.json'
        self.folder = None
        self._index = {}
        self._name_index = {}
        self._scanned = False
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
        self._name_index = {}
        self._scanned = True
        if self.folder is None or not self.folder.is_dir():
            return
        # Klasör içinde alt klasörler de desteklenir.
        for file in sorted(self.folder.rglob('*')):
            if file.is_file() and file.suffix.lower() == '.pdf':
                for name_key in _title_keys(file.stem):
                    self._name_index.setdefault(name_key, set()).add(file)
                for part in re.findall(r'\d+', file.stem):
                    code = str(int(part))
                    score = match_score(file.stem, code)
                    if score is None:
                        continue
                    prev = self._index.get(code)
                    if prev is None or (score, str(file)) < (prev[0], str(prev[1])):
                        self._index[code] = score, file

    def find(self, code, title=None):
        if self.folder is None or not self.folder.is_dir():
            return None
        key = str(int(code)) if str(code).isdigit() else str(code)
        if not self._scanned:
            self.scan()
        # Prefer one unambiguous *full title*, not arbitrary fuzzy matches.
        if title:
            names = _title_keys(title)
            exact_key = ''.join(_title_words(title))
            direct = self._name_index.get(exact_key, set())
            if len(direct) == 1:
                return next(iter(direct))
            if len(direct) > 1:
                return None
            matches = set().union(*(self._name_index.get(k, set()) for k in names))
            if len(matches) == 1:
                return next(iter(matches))
            if len(matches) > 1:
                return None
        found = self._index.get(key)
        if found is not None and not found[1].is_file():
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
