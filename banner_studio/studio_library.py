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


def save_design(settings, books, image, cover_index, resolve_cover, name='', image_format='PNG', reason='manual'):
    """Persist render, preview and editable project; do not change user's sources."""
    if not books:
        raise ValueError('Arşive kaydetmek için en az bir kitap seç.')
    image_format = str(image_format).upper()
    if image_format not in ('PNG', 'JPEG'):
        raise ValueError('Yalnız PNG ve JPG arşivlenebilir.')
    with LOCK:
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        ASSET_POOL.mkdir(parents=True, exist_ok=True)
        record_id = uuid.uuid4().hex
        dest = _record_dir(record_id)
        dest.mkdir()
        try:
            title = _safe_text(name) or _safe_text(' / '.join((settings.title_series, settings.title_set))) or 'İsimsiz afiş'
            now = datetime.now(timezone.utc).isoformat(timespec='seconds')
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
            artwork = dest / ('afis.' + ext)
            image.convert('RGB').save(artwork, image_format,
                **({'quality':97,'subsampling':0,'optimize':True} if ext == 'jpg' else {'optimize':True}))
            preview = image.copy()
            preview.thumbnail((340, 455), Image.Resampling.LANCZOS)
            preview.convert('RGB').save(dest / 'onizleme.jpg', 'JPEG', quality=84)
            manifest = {
                'id': record_id, 'title': title, 'created_at': now,
                'series': _safe_text(settings.title_series),
                'set': _safe_text(settings.title_set),
                'books_count': len(books), 'format': ext,
                'reason': _safe_text(reason, 32),
                'theme': _safe_text(settings.theme),
                'account': _safe_text(settings.account_name),
            }
            project = {'schema': 4, 'settings': settings_copy, 'books': rows}
            _write_json(dest / 'proje.json', project)
            _write_json(dest / 'kayit.json', manifest)
            return manifest
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise


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
    # Excel-like natural A-Z order: Kitap 2 before Kitap 10.
    def order_key(item):
        s = unicodedata.normalize('NFKD', str(item.get('title') or '').casefold())
        s = s.replace('ı', 'i')
        parts = re.split(r'(\d+)', s)
        return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)
    out.sort(key=lambda x: (order_key(x), x.get('created_at','')))
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


def save_working_draft(settings, books):
    """Durable autosave, independent of browser port and extracted ZIP folder."""
    if not isinstance(books,list) or len(books)>30:
        raise ValueError('Son çalışma en fazla 30 kitap içerebilir.')
    with LOCK:
        DRAFT.parent.mkdir(parents=True,exist_ok=True)
        _write_json(DRAFT,{
            'schema':5,'saved_at':datetime.now(timezone.utc).isoformat(),
            'settings':asdict(settings),'books':books
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


def bulk_archive(ids):
    """Prepare ZIP with full-resolution originals and editable project JSON.

    Temporary disk-backed ZIP avoids keeping hundreds of large artworks in RAM.
    Only existing, valid archive IDs are read. Caller removes the temporary ZIP.
    """
    if not isinstance(ids,list) or not 1<=len(ids)<=1000:
        raise ValueError('Toplu indirmede 1–1000 tasarım seçilebilir.')
    wanted=set(str(x) for x in ids)
    available=[x for x in list_designs(limit=5000) if x['id'] in wanted]
    if len(available)!=len(wanted):
        raise ValueError('Seçilen arşiv kayıtlarından biri bulunamadı.')
    ROOT.mkdir(parents=True,exist_ok=True)
    handle=tempfile.NamedTemporaryFile(prefix='alfa_toplu_',suffix='.zip',
                                       dir=ROOT,delete=False)
    output=Path(handle.name)
    handle.close()
    try:
        total=0
        with LOCK,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED,
                                  allowZip64=True) as z:
            for i,entry in enumerate(available,1):
                picture=image_path(entry['id'],'original')
                total+=picture.stat().st_size
                if total>650*1024*1024:
                    raise ValueError('ZIP 650 MB sınırını aştı; daha az tasarım seç.')
                name=re.sub(r'[^\w\- .]+','_',entry.get('title') or 'Tasarim',
                            flags=re.UNICODE).strip(' .')[:75] or 'Tasarim'
                prefix=f'{i:03d}_{name}'
                z.write(picture,f'{prefix}.{entry.get("format") or picture.suffix.lstrip(".")}')
                project=_record_dir(entry['id'])/'proje.json'
                if project.is_file() and entry.get('reason')!='import':
                    z.write(project,f'{prefix}.proje.json')
        return output
    except Exception:
        output.unlink(missing_ok=True)
        raise
