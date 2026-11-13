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
from difflib import SequenceMatcher

PDF_PREFIXES = ('kitap', 'kod', 'book', 'pdf', 'alfa')
_ALLOWED_SUFFIXES = ('kapak', 'cover', 'pdf', 'baski', 'kitap')


def normalize_title(value):
    value = str(value or '').replace('İ', 'i').replace('ı', 'i')
    decomp = unicodedata.normalize('NFKD', value)
    return ''.join(ch for ch in decomp.casefold()
                   if ch.isalnum() and not unicodedata.combining(ch))


def match_score(stem, code):
    """Match an explicitly placed catalog code, never an incidental volume number."""
    key = str(code).strip()
    if not key.isdecimal():
        return None
    num = int(key)
    parts = [p for p in re.split(r'[\\s._()\\[\\]−–—-]+', stem.casefold()) if p]
    if not parts:
        return None
    def is_code(token):
        return token.isdecimal() and int(token) == num
    if len(parts) == 1 and is_code(parts[0]):
        return 0
    # Leading numeric ID is authoritative, e.g. 31-endodonti.pdf.
    if is_code(parts[0]):
        return 1
    # Explicit "kitap_31", "kod 31 - endodonti".
    if len(parts) > 1 and parts[0] in PDF_PREFIXES and is_code(parts[1]):
        return 1
    # Numeric ID with explicit suffix, e.g. endodonti-31-kapak.
    if len(parts) >= 2 and parts[-1] in _ALLOWED_SUFFIXES and is_code(parts[-2]):
        return 2
    return None


def _title_similarity(stem, title):
    """Conservative typo tolerance, with safeguards against unrelated series."""
    def words(value):
        norm = unicodedata.normalize(
            'NFKD', str(value).replace('İ', 'i').replace('ı', 'i')).casefold()
        return [x for x in re.findall(r'[a-z0-9]+', norm)
                if (len(x) > 1 or x.isdecimal()) and x not in _ALLOWED_SUFFIXES]
    source, wanted = words(stem), words(title)
    if len(source) < 2 or len(wanted) < 2:
        return 0.0
    # Numbers (volumes, set numbers, edition years) must never disagree.
    source_nums = {x for x in source if x.isdecimal()}
    wanted_nums = {x for x in wanted if x.isdecimal()}
    if source_nums != wanted_nums:
        return 0.0
    a, b = ''.join(source), ''.join(wanted)
    if min(len(a), len(b)) < 12:
        return 0.0
    overlap = len(set(source) & set(wanted)) / max(len(set(source)), len(set(wanted)))
    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio >= .92 and overlap >= .5:
        return ratio
    if ratio >= .85 and overlap >= .75:
        return ratio
    return 0.0

class PdfKutuphane:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.settings_file = self.data_dir / 'alfa_pdf_ayarlari.json'
        self.folder = None
        self._index = {}
        self._title_index = {}
        self._files = []
        self._conflicted = set()
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
        self._title_index = {}
        self._files = []
        self._conflicted = set()
        self._scanned = True
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
                if prev is None or score < prev[0]:
                    self._index[code] = (score, file)
                    self._conflicted.discard(code)
                elif score == prev[0] and file != prev[1]:
                    self._conflicted.add(code)

    def _find_named(self, title):
        key = normalize_title(title)
        if not key:
            return None
        matches = set(self._title_index.get(key, ()))
        for suffix in _ALLOWED_SUFFIXES:
            matches.update(self._title_index.get(key + suffix, ()))
            matches.update(self._title_index.get(suffix + key, ()))
        # Many scanner exports add a harmless explicit "kapak / baski /
        # cover" suffix to the book title.  Keep this match strict:
        # never infer a match from just a volume number or shared series.
        for file in self._files:
            raw = file.stem
            stem = normalize_title(raw)
            if stem in (key,):
                matches.add(file)
                continue
            remainder = None
            if stem.startswith(key):
                remainder = stem[len(key):]
            elif stem.endswith(key):
                remainder = stem[:-len(key)]
            if remainder and remainder in _ALLOWED_SUFFIXES:
                matches.add(file)
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches) > 1:
            raise ValueError('Aynı kitap adıyla birden fazla PDF var: ' + str(title))
        ranked = sorted(
            ((score, file) for file in self._files
             if (score := _title_similarity(file.stem, title)) > 0),
            key=lambda item: item[0], reverse=True)
        if ranked:
            if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < .06:
                raise ValueError('Birden fazla benzer PDF adı var: ' + str(title))
            return ranked[0][1]
        return None

    def find(self, code, title=None):
        if self.folder is None or not self.folder.is_dir():
            return None
        key = str(int(code)) if str(code).isdigit() else str(code)
        if not self._scanned:
            self.scan()
        # Restore code-first matching from the working Suite for explicit
        # filenames such as 31-endodonti.pdf and kitap_31.pdf.
        found = self._index.get(key)
        if found is not None and found[0] <= 2 and found[1].is_file():
            if key in self._conflicted:
                raise ValueError('Aynı kitap koduyla birden fazla PDF var: ' + key)
            return found[1]
        if title:
            named = self._find_named(title)
            if named:
                return named
        if found is None or not found[1].is_file():
            if found is not None:
                self.scan()
            if title:
                named = self._find_named(title)
                if named:return named
            found = self._index.get(key)
        if found is None:
            return None
        score, candidate = found
        if key in self._conflicted:
            raise ValueError('Aynı kitap koduyla birden fazla PDF var: ' + key)
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
