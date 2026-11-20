"""Local, persistent design library for ALFA Banner Studio Pro.

This archive lives OUTSIDE an extracted ZIP/app directory so upgrades won't erase
saved projects or generated JPG/PNG images. Original cover/logo assets used by
saved designs are content-addressed and retained for faithful reopening.
"""
from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import threading
import tempfile
import unicodedata
import uuid
import zipfile

from PIL import Image

ROOT = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.local' / 'share')) / 'ALFA_Banner_Studio_Pro' / 'Tasarim_Arsivi'
ARCHIVE = ROOT / 'Kayitlar'
ASSET_POOL = ROOT / 'Gorseller'
LOCK = threading.RLock()
EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
DRAFT = ROOT.parent / 'Son_Calisma.json'


def _record_dir(record_id):
    record_id = str(record_id)
    if not re.fullmatch(r'[a-f0-9]{32}', record_id):
        raise ValueError('Arşiv kayıt kimliği geçersiz.')
    return ARCHIVE / record_id


def _safe_text(text, maximum=120):
    return str(text or '').strip()[:maximum]


def _write_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def _freeze_asset(source):
    source = Path(str(source or ''))
    if not source.is_file() or source.suffix.lower() not in EXTS:
        return ''
    if source.stat().st_size > 30 * 1024 * 1024:
        return ''
    with source.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    target = ASSET_POOL / (digest + source.suffix.lower())
    if not target.exists():
        tmp = ASSET_POOL / (digest + '.' + uuid.uuid4().hex + '.tmp')
        shutil.copyfile(source, tmp)
        os.replace(tmp, target)
    return str(target)


def _title_key(value):
    """Compare archive titles without accidental duplicates from spacing/case."""
    value = unicodedata.normalize('NFKC', _safe_text(value)).casefold()
    return re.sub(r'\s+', ' ', value).strip()


def save_design(settings, books, image, cover_index, resolve_cover, name='',
                image_format='PNG', reason='manual', record_id=None):
    """Create a design, or replace the editable contents of an existing ID."""
    if not books:
        raise ValueError('Arşive kaydetmek için en az bir kitap seç.')
    image_format = str(image_format).upper()
    if image_format not in ('PNG', 'JPEG'):
        raise ValueError('Yalnız PNG ve JPG arşivlenebilir.')
    with LOCK:
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        ASSET_POOL.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        title = _safe_text(name) or _safe_text(' / '.join(
            (settings.title_series, settings.title_set))) or 'İsimsiz afiş'
        previous = None
        if record_id:
            dest = _record_dir(record_id)
            try:
                previous = json.loads((dest / 'kayit.json').read_text(encoding='utf-8'))
                old_project = json.loads((dest / 'proje.json').read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise ValueError('Güncellenecek arşiv kaydı bulunamadı.') from exc
            if (previous.get('id') != str(record_id) or
                    not isinstance(old_project, dict) or
                    old_project.get('editable') is False):
                raise ValueError('Bu arşiv kaydı düzenlenebilir bir proje değil.')
            title = previous.get('title') or title
        else:
            if reason == 'manual' and any(
                _title_key(item.get('title')) == _title_key(title)
                for item in list_designs(limit=5000)
            ):
                raise ValueError('Bu isim arşivde var. Üzerine yazmak için mevcut kaydı seçin.')
            record_id = uuid.uuid4().hex
            dest = _record_dir(record_id)

        staging = Path(tempfile.mkdtemp(prefix='.kaydediliyor-', dir=ARCHIVE))
        try:
            settings_copy = asdict(settings)
            if settings_copy.get('logo_path'):
                settings_copy['logo_path'] = _freeze_asset(settings_copy['logo_path'])
            rows = []
            for book in books:
                copy = dict(book)
                path = resolve_cover(book, cover_index)
                copy['cover_override'] = _freeze_asset(path) if path else ''
                rows.append(copy)
            ext = 'jpg' if image_format == 'JPEG' else 'png'
            artwork = staging / ('afis.' + ext)
            image.convert('RGB').save(artwork, image_format,
                **({'quality':97,'subsampling':0,'optimize':True} if ext == 'jpg' else {'optimize':True}))
            preview = image.copy()
            preview.thumbnail((340, 455), Image.Resampling.LANCZOS)
            preview.convert('RGB').save(staging / 'onizleme.jpg', 'JPEG', quality=84)
            manifest = {
                'id': record_id, 'title': title,
                'created_at': previous.get('created_at', now) if previous else now,
                'updated_at': now,
                'series': _safe_text(settings.title_series),
                'set': _safe_text(settings.title_set),
                'subtitle': _safe_text(settings.subtitle) if settings.show_subtitle else '',
                'books_count': len(books), 'format': ext,
                'reason': previous.get('reason', reason) if previous else _safe_text(reason, 32),
                'theme': _safe_text(settings.theme),
                'account': _safe_text(settings.account_name),
            }
            project = {'schema': 4, 'settings': settings_copy, 'books': rows}
            _write_json(staging / 'proje.json', project)
            _write_json(staging / 'kayit.json', manifest)
            if previous:
                # Stage every file first; never delete the original directory on failure.
                for filename in (artwork.name, 'onizleme.jpg', 'proje.json', 'kayit.json'):
                    os.replace(staging / filename, dest / filename)
                old_ext = previous.get('format')
                if old_ext in ('jpg', 'png') and old_ext != ext:
                    (dest / ('afis.' + old_ext)).unlink(missing_ok=True)
            else:
                os.replace(staging, dest)
            return manifest
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)


def _archive_order_key(item):
    s = unicodedata.normalize('NFKD', str(item.get('title') or '').casefold())
    s = s.replace('ı', 'i')
    parts = re.split(r'(\d+)', s)
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)


def list_designs(limit=500):
    out = []
    if not ARCHIVE.is_dir():
        return out
    for folder in ARCHIVE.iterdir():
        if not folder.is_dir():
            continue
        path = folder / 'kayit.json'
        try:
            item = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(item, dict) and item.get('id') == folder.name:
                out.append(item)
        except (OSError, ValueError):
            continue
    out.sort(key=lambda x: (_archive_order_key(x), x.get('created_at','')))
    return out[:max(1, min(5000, int(limit)))]


def get_design(record_id):
    folder = _record_dir(record_id)
    data = json.loads((folder / 'proje.json').read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('books'), list):
        raise ValueError('Kayıt dosyası bozulmuş.')
    return data


def image_path(record_id, kind='preview'):
    folder = _record_dir(record_id)
    if kind == 'preview':
        path = folder / 'onizleme.jpg'
    elif kind == 'original':
        info = json.loads((folder / 'kayit.json').read_text(encoding='utf-8'))
        path = folder / ('afis.' + ('jpg' if info.get('format') == 'jpg' else 'png'))
    else:
        raise ValueError('Görsel türü geçersiz.')
    if not path.is_file():
        raise FileNotFoundError('Görsel bulunamadı.')
    return path


def rename_design(record_id, title):
    title = _safe_text(title)
    if not title:
        raise ValueError('Tasarım adı boş olamaz.')
    path = _record_dir(record_id) / 'kayit.json'
    with LOCK:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['title'] = title
        _write_json(path, manifest)
    return manifest


def delete_design(record_id):
    folder = _record_dir(record_id)
    with LOCK:
        if not (folder / 'kayit.json').is_file():
            raise FileNotFoundError('Kayıt bulunamadı.')
        shutil.rmtree(folder)
    return True


def import_image(raw, filename='Eski Afiş', title=''):
    """Archive an existing downloaded JPG/PNG as a viewable, noneditable image."""
    if not raw or len(raw)>24*1024*1024:
        raise ValueError('Görsel 24 MB sınırını aşamaz.')
    with Image.open(BytesIO(raw)) as check:
        check.verify()
    with Image.open(BytesIO(raw)) as source:
        if source.format not in ('JPEG','PNG'):
            raise ValueError('Yalnız JPG ve PNG desteklenir.')
        if source.width*source.height>35_000_000:
            raise ValueError('Görsel çözünürlüğü çok büyük.')
        rgb=source.convert('RGB')
        kind='jpg' if source.format=='JPEG' else 'png'
        with LOCK:
            ARCHIVE.mkdir(parents=True, exist_ok=True)
            ident=uuid.uuid4().hex
            folder=_record_dir(ident);folder.mkdir()
            try:
                # Preserve imported JPG/PNG bytes exactly: no quality loss.
                (folder/('afis.'+kind)).write_bytes(raw)
                thumb=rgb.copy();thumb.thumbnail((340,455),Image.Resampling.LANCZOS)
                thumb.save(folder/'onizleme.jpg','JPEG',quality=85)
                item={'id':ident,'title':_safe_text(title) or _safe_text(Path(filename).stem),
                      'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                      'series':'','set':'Harici görsel','books_count':0,'format':kind,
                      'reason':'import','theme':'','account':''}
                _write_json(folder/'proje.json',{'schema':4,'editable':False,'books':[],
                                                'settings':{}})
                _write_json(folder/'kayit.json',item)
                return item
            except Exception:
                shutil.rmtree(folder,ignore_errors=True)
                raise


def save_working_draft(settings, books, archive_id=None):
    """Durable autosave that also remembers the edited archive record."""
    if not isinstance(books,list) or len(books)>30:
        raise ValueError('Son çalışma en fazla 30 kitap içerebilir.')
    if archive_id:
        folder = _record_dir(archive_id)
        if not (folder / 'kayit.json').is_file():
            archive_id = None
    with LOCK:
        DRAFT.parent.mkdir(parents=True,exist_ok=True)
        _write_json(DRAFT,{
            'schema':5,'saved_at':datetime.now(timezone.utc).isoformat(),
            'settings':asdict(settings),'books':books,'archive_id':archive_id
        })
    return True


def read_working_draft():
    try:
        item=json.loads(DRAFT.read_text(encoding='utf-8'))
        if (item.get('schema')!=5 or not isinstance(item.get('books'),list)
            or len(item['books'])>30 or not isinstance(item.get('settings'),dict)):
            return None
        return item
    except (OSError,ValueError,TypeError,AttributeError):
        return None


def artwork_png(record_id):
    """Get one archived artwork as PNG, including legacy JPG entries.

    No JSON or editable-project files are exposed by this export API.
    """
    picture=image_path(record_id,'original')
    with Image.open(picture) as source:
        output=BytesIO()
        source.convert('RGB').save(output,format='PNG',optimize=True)
    return output.getvalue()


def export_label(entry,index=None):
    """User-facing safe file name: series, set/advert, subtitle, with fallback."""
    record_id=entry['id']
    try:
        project=get_design(record_id)
        settings=project.get('settings') or {}
        parts=[str(settings.get(k) or '').strip() for k in
               ('title_series','title_set','subtitle')]
        if not settings.get('show_subtitle') or not parts[2]:
            parts[2]=str(entry.get('books_count') or len(project.get('books') or []))+' Kitap'
        # Imported artwork does not have design settings.
        if not any(parts):
            parts=[entry.get('title') or 'Tasarim']
    except (OSError,ValueError,KeyError,TypeError):
        parts=[entry.get('title') or 'Tasarim']
    name=' - '.join(x for x in parts if x).strip() or 'Tasarim'
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]+','_',name)
    name=re.sub(r'\s+',' ',name).strip(' .')[:125] or 'Tasarim'
    if index is not None:
        return f'{index:03d}_{name}'
    return name


def suggested_export_name(title, ext='png', record_id=None, entries=None):
    """Global natural A–Z archive rank, independent of selected/filtered rows."""
    ext = str(ext or '').lower().lstrip('.')
    if ext not in ('png', 'jpg', 'pdf'):
        raise ValueError('Dosya türü geçersiz.')
    items = list(entries) if entries is not None else list_designs(limit=5000)
    if record_id:
        target = next((entry for entry in items if entry['id'] == record_id), None)
        if target is None:
            raise ValueError('Tasarım arşivinde kayıt bulunamadı.')
    else:
        target = {'id': '', 'title': _safe_text(title) or 'İsimsiz afiş',
                  'created_at': '9999'}
        items.append(target)
        items.sort(key=lambda x: (_archive_order_key(x), x.get('created_at', '')))
    index = next((i for i, entry in enumerate(items, 1) if entry is target), None)
    if index is None:
        raise ValueError('Arşiv sırası bulunamadı.')
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '_', str(target['title']))
    safe = re.sub(r'\s+', ' ', safe).strip(' .')[:110] or 'Tasarim'
    return f'{index:04d}_{safe}.{ext}'


def bulk_archive(ids):
    """ZIP with PNG pictures exclusively; never attach archive project JSON."""
    if not isinstance(ids,list) or not 1<=len(ids)<=1000:
        raise ValueError('Toplu indirmede 1–1000 tasarım seçilebilir.')
    wanted=set(str(x) for x in ids)
    ordered=list_designs(limit=5000)
    available=[x for x in ordered if x['id'] in wanted]
    if len(available)!=len(wanted):
        raise ValueError('Seçilen arşiv kayıtlarından biri bulunamadı.')
    ROOT.mkdir(parents=True,exist_ok=True)
    handle=tempfile.NamedTemporaryFile(prefix='alfa_png_toplu_',suffix='.zip',
                                       dir=ROOT,delete=False)
    output=Path(handle.name)
    handle.close()
    try:
        total=0
        with LOCK,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED,
                                  allowZip64=True) as package:
            for entry in available:
                png=artwork_png(entry['id'])
                total+=len(png)
                if total>650*1024*1024:
                    raise ValueError('Toplu PNG boyutu 650 MB sınırını aştı; daha az seç.')
                package.writestr(suggested_export_name(entry['title'],'png',entry['id'],ordered),png)
        return output
    except Exception:
        output.unlink(missing_ok=True)
        raise
