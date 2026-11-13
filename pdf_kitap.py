"""Kod ve güvenli *tam kitap adı* eşleştirmeli yerel PDF kütüphanesi.

Örnek: 402 -> TUSDATA PRETUS 3.pdf.
Sayısal seri/cilt numarası (3) başka kitap kodu sanılmaz.
"""
from pathlib import Path
import json
import os
import re
import tempfile
import unicodedata

PDF_PREFIXES = ('kitap', 'kod', 'book', 'pdf', 'alfa')
_ALLOWED_SUFFIXES = ('kapak', 'cover', 'pdf', 'baski', 'kitap')


def normalize_title(value):
    value = str(value or '').replace('İ', 'i').replace('ı', 'i')
    decomp = unicodedata.normalize('NFKD', value)
    return ''.join(ch for ch in decomp.casefold()
                   if ch.isalnum() and not unicodedata.combining(ch))


def match_score(stem, code):
    """0 is exact code, 1-2 explicitly coded, 3 is weak/ambiguous."""
    key = str(code).strip()
    if not key.isdigit():
        return None
    pattern = rf'0*{int(key)}'
    if re.fullmatch(pattern, stem, re.I):
        return 0
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
        self._title_index = {}
        self._files = []
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
        self._title_index = {}
        self._files = []
        if self.folder is None or not self.folder.is_dir():
            return
        # Nested folders are supported, but exact duplicate titles are
        # ambiguous: never pick the first PDF arbitrarily.
        for file in sorted(self.folder.rglob('*')):
            if not file.is_file() or file.suffix.lower() != '.pdf':
                continue
            self._files.append(file)
            norm = normalize_title(file.stem)
            if norm:
                self._title_index.setdefault(norm, []).append(file)
            for part in re.findall(r'\d+', file.stem):
                code = str(int(part))
                score = match_score(file.stem, code)
                if score is None:
                    continue
                prev = self._index.get(code)
                if prev is None or (score, str(file)) < (prev[0], str(prev[1])):
                    self._index[code] = (score, file)

    def _find_named(self, title):
        key=normalize_title(title)
        if not key:return None
        matches = set(self._title_index.get(key, ()))
        for suffix in _ALLOWED_SUFFIXES:
            matches.update(self._title_index.get(key + suffix, ()))
            matches.update(self._title_index.get(suffix + key, ()))
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches)>1:
            raise ValueError('Aynı kitap adıyla birden fazla PDF var: '+str(title))
        return None

    def find(self, code, title=None):
        if self.folder is None or not self.folder.is_dir():
            return None
        key = str(int(code)) if str(code).isdigit() else str(code)
        if not self._files or self._index is None:
            self.scan()
        if title:
            named = self._find_named(title)
            if named:
                # Full book title beats an unrelated volume number.
                return named
        found = self._index.get(key)
        if found is None or not found[1].is_file():
            self.scan()
            if title:
                named = self._find_named(title)
                if named:return named
            found = self._index.get(key)
        if found is None:
            return None
        score, candidate=found
        if title and score >= 3:
            # Legacy heuristic "DUS Set 3.pdf" would claim code 3 even
            # when that book belongs to another publisher. Fail closed.
            return None
        return candidate

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
