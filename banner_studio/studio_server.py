"""ALFA Banner Studio Pro — local browser editor + Pillow poster renderer.

Runs on 127.0.0.1 only. Inputs/exports remain on this computer; no cloud.
Dependencies: Pillow and openpyxl, already used by the original MVP.
"""
from __future__ import annotations
import base64
from dataclasses import asdict
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import zipfile
import tempfile
import threading
import secrets
import socket
import sys
import time
from urllib.parse import urlsplit, parse_qs, unquote
import webbrowser
from alfa_guncelleme import check_for_update,download_update,launch_update,UpdateError

from PIL import Image
from banner_engine import (Renderer, Settings, read_excel, cover_files,
                           get_cover, upright_cover, PALETTES, LAYOUTS, STYLES, square_preview)
import studio_library as library

SUITE_VERSION='2.0.32'
UPDATE_NONCE=secrets.token_urlsafe(32)
UPDATE_LOCK=threading.RLock()
UPDATE_STATE={'release':None,'verified':None,'busy':False}
SUITE_STORAGE=Path(os.environ.get('LOCALAPPDATA') or Path.home())/'ALFA_Banner_Studio_Pro'
BASE=Path(__file__).resolve().parent
# User data survives replacing/upgrading the extracted application folder.
DATA=library.ROOT.parent/'Calisma'
LEGACY_DATA=BASE/'data'
DATA.mkdir(parents=True,exist_ok=True)
for filename in ('Kitaplar.xlsx','Magaza_Logo.png'):
    dest=DATA/filename
    if not dest.exists() and (LEGACY_DATA/filename).is_file():
        shutil.copy2(LEGACY_DATA/filename,dest)
if (LEGACY_DATA/'Kapaklar').is_dir():
    (DATA/'Kapaklar').mkdir(parents=True,exist_ok=True)
    for old in (LEGACY_DATA/'Kapaklar').iterdir():
        if old.is_file() and old.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):
            dest=DATA/'Kapaklar'/old.name
            if not dest.exists():shutil.copy2(old,dest)
ASSETS=DATA/'Kapaklar'
ASSETS.mkdir(parents=True,exist_ok=True)
WEB=BASE/'static'
CATALOG_FILE=DATA/'Kitaplar.xlsx'
if not CATALOG_FILE.is_file():
    example=BASE/'ornek'/'KİTAPS.xlsx'
    if example.is_file():CATALOG_FILE=example


CATALOG_ERROR=''
def _catalog():
    global CATALOG_ERROR
    if not CATALOG_FILE.is_file():
        CATALOG_ERROR='Kitap kataloğu dosyası bulunamadı. Excel kataloğunu yeniden seç.'
        return []
    try:
        books=read_excel(str(CATALOG_FILE))
        CATALOG_ERROR=''
        return books
    except (OSError,ValueError,KeyError,TypeError) as exc:
        CATALOG_ERROR='Kayıtlı Excel açılamadı: '+str(exc)[:300]
        return []

CATALOG=_catalog()
def _combined_covers():
    # Uploaded covers win. The bundled sample remains available, including
    # when a different Excel catalog has been uploaded.
    uploaded=cover_files(str(ASSETS))
    # Do not discard bundled artwork just because Excel was reimported.
    # get_cover validates demo title + code before using those candidates.
    demo=cover_files(str(BASE/'ornek'/'Kapaklar'))
    codes={key:list(uploaded[0].get(key,[]))+list(demo[0].get(key,[]))
           for key in set(uploaded[0])|set(demo[0])}
    titles={key:list(uploaded[1].get(key,[]))+list(demo[1].get(key,[]))
            for key in set(uploaded[1])|set(demo[1])}
    return codes,titles

COVER_IDX=_combined_covers()

def _cover_status():
    matched=sum(bool(get_cover(book,COVER_IDX)) for book in CATALOG)
    missing=[b['code']+' · '+b['name'] for b in CATALOG
             if not get_cover(b,COVER_IDX)]
    return {'covers':len(COVER_IDX[0]),'matched':matched,
            'total':len(CATALOG),'missing':missing[:16]}


def _safe_filename(name):
    name=Path(str(name).replace('\\','/')).name
    name=re.sub(r'[^\w.\-() +]+','_',name,flags=re.UNICODE)
    return name[:135] or 'resim.jpg'


def _json_bytes(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')


def _settings(raw):
    valid=Settings.__dataclass_fields__
    d={k:v for k,v in raw.items() if k in valid}
    if str(d.get('theme','')) not in PALETTES:d['theme']='Zümrüt / Krem'
    if str(d.get('style','')) not in STYLES:d['style']='Vintage Koleksiyon'
    if str(d.get('layout','')) not in LAYOUTS:d['layout']='Akıllı'
    cfg=Settings(**d)
    try:cfg.cover_zoom=max(72,min(116,int(cfg.cover_zoom)))
    except (ValueError,TypeError):cfg.cover_zoom=100
    try:cfg.cover_spacing=max(0,min(65,int(cfg.cover_spacing)))
    except (ValueError,TypeError):cfg.cover_spacing=12
    for key,minimum,maximum in [('edition_font_size',16,60),
                                ('cover_edition_font_size',10,86),
                                ('cover_badge_font_size',10,86),
                                ('export_scale',1,3)]:
        try:setattr(cfg,key,max(minimum,min(maximum,int(getattr(cfg,key)))))
        except (ValueError,TypeError):setattr(cfg,key,getattr(Settings(),key))
    # Prevent the browser from passing arbitrary absolute server paths.
    if cfg.logo_path:
        candidate=Path(cfg.logo_path).resolve()
        if DATA.resolve() not in candidate.parents and library.ROOT.resolve() not in candidate.parents:cfg.logo_path=''
    return cfg


def _rows(raw):
    if not isinstance(raw,list) or len(raw)>30:
        raise ValueError('Bir afişte en fazla 30 kitap olabilir.')
    out=[]
    for x in raw:
        if not isinstance(x,dict):continue
        o={k:x.get(k,'') for k in ('id','code','name','group','pages','color','cover_override','badge_override','edition_override')}
        o['name']=str(o['name'])[:150]
        o['code']=str(o['code'])[:50]
        override=str(o['cover_override']) if o['cover_override'] else ''
        if override:
            path=Path(override).resolve()
            if (DATA.resolve() not in path.parents
                and (BASE/'ornek').resolve() not in path.parents
                and library.ROOT.resolve() not in path.parents):
                o['cover_override']=''
        out.append(o)
    return out


def _read_body(h, max_bytes=8*1024*1024):
    try:size=int(h.headers.get('Content-Length','0'))
    except ValueError:size=-1
    if not 0<=size<=max_bytes:raise ValueError('Dosya veya istek çok büyük.')
    return h.rfile.read(size)


class Handler(SimpleHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(WEB),**kwargs)
    def log_message(self,fmt,*args):
        if '/api/' not in str(args):
            pass
    def _headers(self,code=200,mime='application/json; charset=utf-8',length=0):
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(length))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
    def _response(self,obj,code=200):
        data=_json_bytes(obj)
        self._headers(code,length=len(data))
        self.wfile.write(data)
    def _binary(self,data,ctype='image/jpeg',filename=None):
        self.send_response(200)
        self.send_header('Content-Type',ctype)
        if filename:self.send_header('Content-Disposition',
            'attachment; filename="'+str(filename).encode('ascii','ignore').decode('ascii')+'"')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        global CATALOG,COVER_IDX
        req=urlsplit(self.path);q=parse_qs(req.query)
        if req.path=='/api/library/asset':
            filename=(q.get('name') or [''])[0]
            if not re.fullmatch(r'[a-f0-9]{64}\.(jpg|jpeg|png|webp)',filename):
                return self._response({'error':'Görsel kimliği geçersiz'},404)
            path=library.ASSET_POOL/filename
            if not path.is_file():
                return self._response({'error':'Arşiv kapağı bulunamadı'},404)
            return self._binary(path.read_bytes(),
                'image/png' if path.suffix=='.png' else 'image/webp' if path.suffix=='.webp' else 'image/jpeg')
        if req.path=='/api/update/check':
            try:
                release=check_for_update(SUITE_VERSION,'banner')
                with UPDATE_LOCK:
                    UPDATE_STATE['release']=release
                    UPDATE_STATE['verified']=None
                return self._response({'release':release,'current':SUITE_VERSION})
            except (UpdateError,OSError,ValueError) as exc:
                return self._response({'error':str(exc)[:280]},503)
        if req.path=='/api/library/list':
            return self._response({'items':library.list_designs(limit=5000),'folder':str(library.ROOT)})
        if req.path=='/api/library/png':
            ident=(q.get('id') or [''])[0]
            try:
                data=library.artwork_png(ident)
                return self._binary(data,'image/png',filename='ALFA_Tasarim.png')
            except (ValueError,OSError,KeyError,TypeError) as exc:
                return self._response({'error':str(exc)[:200]},404)
        if req.path in ('/api/library/open','/api/library/preview','/api/library/download'):
            ident=(q.get('id') or [''])[0]
            try:
                if req.path=='/api/library/open':
                    return self._response(library.get_design(ident))
                stored=library.image_path(ident, 'preview' if req.path.endswith('preview') else 'original')
                kind='image/png' if stored.suffix.lower()=='.png' else 'image/jpeg'
                return self._binary(stored.read_bytes(),kind,
                    filename=stored.name if req.path.endswith('download') else None)
            except (ValueError,OSError,KeyError) as exc:
                return self._response({'error':str(exc)[:200]},404)
        if req.path=='/api/draft':
            return self._response({'draft':library.read_working_draft()})
        if req.path=='/api/cover-status':
            return self._response(_cover_status())
        if req.path=='/api/bootstrap':
            config=asdict(Settings(title_series='TTS',title_set='KLİNİK SET',
                     theme='Zümrüt / Krem',offer='SB + RENKLİ',
                     sb_price='2.800 TL',color_price='3.000 TL',
                     sb_single_price='600 TL',color_single_price='750 TL',
                     note1='İlan fiyatı yalnız tek kitap içindir; set için mesaj atınız.',
                     note2='Lütfen bu ilanı doğrudan satın almayınız.',
                     note3='Kitap kodu, set ve baskı türünü mesajla belirtiniz.'))
            selected=[dict(book) for book in CATALOG if book['code'] in
                      ('443','444','445','446','447')][:5]
            return self._response({'catalog':CATALOG,'settings':config,'books':selected,
                   'palettes':PALETTES,'styles':STYLES,'layouts':LAYOUTS,
                   'covers':len(COVER_IDX[0]),'cover_status':_cover_status(),
                   'version':'3.13 - Fiyat etiketi punto düzeltmesi',
                   'suite_version':SUITE_VERSION,
                   'update_nonce':UPDATE_NONCE,
                   'catalog_error':CATALOG_ERROR,
                   'library_total':len(library.list_designs())})
        if req.path=='/api/custom-cover':
            filename=_safe_filename((q.get('name') or [''])[0])
            target=ASSETS/filename
            if target.is_file() and target.suffix.lower() in ('.jpg','.jpeg','.png','.webp'):
                try:
                    with Image.open(target) as source:
                        im=upright_cover(source).convert('RGB');im.thumbnail((90,130))
                        out=BytesIO();im.save(out,'JPEG',quality=78)
                    return self._binary(out.getvalue())
                except OSError:pass
            return self._headers(404,length=0)
        if req.path=='/api/cover':
            code=(q.get('code') or [''])[0]
            o=next((b for b in CATALOG if b['code']==code),None)
            p=get_cover(o or {'code':code,'name':''},COVER_IDX)
            if p and Path(p).is_file():
                try:
                    with Image.open(p) as source:
                        im=upright_cover(source).convert('RGB');im.thumbnail((90,130))
                        f=BytesIO();im.save(f,'JPEG',quality=78)
                    return self._binary(f.getvalue())
                except OSError:pass
            return self._headers(404,length=0)
        return super().do_GET()

    def do_POST(self):
        global CATALOG,COVER_IDX,CATALOG_FILE,CATALOG_ERROR
        path=urlsplit(self.path).path
        try:
            if path in ('/api/update/download','/api/update/install'):
                # A local page can update itself; a website in another tab cannot.
                origin=self.headers.get('Origin','')
                expected=f'http://127.0.0.1:{self.server.server_port}'
                if (origin and origin!=expected) or self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                    return self._response({'error':'Güvenilmeyen güncelleme isteği'},403)
                body=json.loads(_read_body(self,4_096))
                if body.get('nonce')!=UPDATE_NONCE:
                    return self._response({'error':'Güncelleme oturumu doğrulanamadı'},403)
                if path=='/api/update/download':
                    with UPDATE_LOCK:
                        if UPDATE_STATE['busy']:
                            return self._response({'error':'Güncelleme işlemi zaten sürüyor'},409)
                        release=UPDATE_STATE['release']
                        if not isinstance(release,dict) or not release.get('available'):
                            return self._response({'error':'Önce yeni sürümü kontrol et'},409)
                        UPDATE_STATE['busy']=True
                    try:
                        verified=download_update(release,SUITE_STORAGE)
                        with UPDATE_LOCK:UPDATE_STATE['verified']=verified
                        return self._response({'success':True,'version':verified['version']})
                    finally:
                        with UPDATE_LOCK:UPDATE_STATE['busy']=False
                with UPDATE_LOCK:
                    if UPDATE_STATE['busy']:
                        return self._response({'error':'Güncelleme işlemi sürüyor'},409)
                    verified=UPDATE_STATE['verified']
                    if not verified:
                        return self._response({'error':'Kurulum henüz indirilip doğrulanmadı'},409)
                    UPDATE_STATE['busy']=True
                try:
                    launch_update(verified,SUITE_STORAGE,sys.executable)
                    self._response({'success':True,'message':'Kurulum hazırlanıyor; Banner Studio kapanacak.'})
                    # A detached helper waits for this process to exit and
                    # installs the suite after rechecking SHA-256.
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                except Exception:
                    with UPDATE_LOCK:UPDATE_STATE['busy']=False
                    raise
            if path in ('/api/render','/api/export','/api/library/save'):
                body=json.loads(_read_body(self,1_500_000))
                cfg=_settings(body.get('settings') or {})
                books=_rows(body.get('books') or [])
                if path=='/api/library/save':
                    if not books:raise ValueError('Önce afişe kitap ekle.')
                    out=Renderer(cfg,books,COVER_IDX,scale=cfg.export_scale).render()
                    record=library.save_design(
                        cfg,books,out,COVER_IDX,get_cover,
                        name=str(body.get('name') or ''),
                        image_format=str(body.get('format') or 'PNG'),reason='manual')
                    return self._response({'saved':record})
                if path=='/api/render':
                    renderer=Renderer(cfg,books,COVER_IDX)
                    image=renderer.render()
                    if body.get('square'):
                        image=square_preview(image)
                    image.thumbnail((900,1200),Image.Resampling.LANCZOS)
                    buf=BytesIO();image.save(buf,'JPEG',quality=92,subsampling=0)
                    # positions are from the original 1200x1600 image.
                    self._response({'image':'data:image/jpeg;base64,'+
                        base64.b64encode(buf.getvalue()).decode('ascii'),
                        'positions':renderer.positions,
                        'crop':bool(body.get('square'))})
                    return
                if not books:raise ValueError('Dışa aktarmadan önce kitap ekle.')
                renderer=Renderer(cfg,books,COVER_IDX,scale=cfg.export_scale)
                out=renderer.render()
                if body.get('square'):out=square_preview(out)
                fmt=str(body.get('format') or 'PNG').upper()
                if fmt not in ('PNG','JPEG'):raise ValueError('Yalnız JPG/PNG dışa aktarılır.')
                record=library.save_design(
                    cfg,books,out,COVER_IDX,get_cover,
                    name=str(body.get('name') or ''), image_format=fmt,reason='export')
                stream=BytesIO()
                if fmt=='JPEG':out.convert('RGB').save(stream,'JPEG',quality=97,subsampling=0,optimize=True)
                else:out.save(stream,'PNG',optimize=True)
                label='Kare' if body.get('square') else 'Afiş'
                suffix='jpg' if fmt=='JPEG' else 'png'
                name=f'{cfg.title_series}_{cfg.title_set}_{label}.{suffix}'
                return self._binary(stream.getvalue(),
                    'image/jpeg' if fmt=='JPEG' else 'image/png',filename=name)
            if path=='/api/library/import':
                name=(parse_qs(urlsplit(self.path).query).get('name') or ['Afiş'])[0]
                record=library.import_image(_read_body(self,24*1024*1024),name)
                return self._response({'saved':record})
            if path=='/api/library/rename':
                request=json.loads(_read_body(self,32_000))
                record=library.rename_design(request.get('id'),request.get('title'))
                return self._response({'saved':record})
            if path=='/api/library/delete':
                request=json.loads(_read_body(self,32_000))
                library.delete_design(request.get('id'))
                return self._response({'success':True})
            if path=='/api/draft/save':
                request=json.loads(_read_body(self,1_500_000))
                cfg=_settings(request.get('settings') or {})
                books=_rows(request.get('books') or [])
                library.save_working_draft(cfg,books)
                return self._response({'success':True})
            if path=='/api/library/export-names':
                request=json.loads(_read_body(self,90_000))
                ids=request.get('ids')
                if not isinstance(ids,list) or not 1<=len(ids)<=1000:
                    raise ValueError('En fazla 1000 arşiv kaydı seçilebilir.')
                available={x['id']:x for x in library.list_designs(limit=5000)}
                if any(i not in available for i in ids) or len(set(ids))!=len(ids):
                    raise ValueError('Arşiv seçimi geçersiz.')
                return self._response({'files':[{
                    'id':i,'name':library.export_label(available[i],n)+'.png'
                } for n,i in enumerate(ids,1)]})
            if path=='/api/library/bulk-download':
                request=json.loads(_read_body(self,90_000))
                package=library.bulk_archive(request.get('ids'))
                try:
                    self.send_response(200)
                    self.send_header('Content-Type','application/zip')
                    self.send_header('Content-Disposition',
                        'attachment; filename="ALFA_Tasarim_Arsivi.zip"')
                    self.send_header('Content-Length',str(package.stat().st_size))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    with package.open('rb') as fd:
                        while True:
                            block=fd.read(1024*512)
                            if not block:break
                            self.wfile.write(block)
                finally:package.unlink(missing_ok=True)
                return
            if path=='/api/upload/excel':
                raw=_read_body(self,30*1024*1024)
                if not raw:
                    raise ValueError('Boş Excel dosyası yüklenemez.')
                # The original workbook is replaced ONLY after full parsing,
                # duplicate-code checks and file validation succeed.
                # Parse in-memory: Windows/openpyxl/antivirus can keep a
                # read-only .xlsx ZIP handle open after close(), causing
                # WinError 32 when that same temporary file is renamed.
                # Never open our eventual rename source with openpyxl.
                items=read_excel(BytesIO(raw))
                with tempfile.NamedTemporaryFile(
                    dir=DATA,prefix='excel_kontrol_',suffix='.xlsx',delete=False
                ) as out:
                    temp=Path(out.name)
                    out.write(raw)
                try:
                    final=DATA/'Kitaplar.xlsx'
                    # Windows Defender/indexing or an external Excel
                    # process can briefly lock the destination.
                    for attempt in range(6):
                        try:
                            os.replace(temp,final)
                            break
                        except PermissionError:
                            if attempt==5:
                                raise ValueError(
                                    'Kitaplar.xlsx başka bir program tarafından kullanılıyor. '
                                    'Excel dosyasını kapatıp tekrar dene.'
                                )
                            time.sleep(0.2*(attempt+1))
                finally:
                    temp.unlink(missing_ok=True)
                CATALOG_FILE=final
                CATALOG=items
                CATALOG_ERROR=''
                COVER_IDX=_combined_covers()
                return self._response({'catalog':items,'total':len(items),
                                       'cover_status':_cover_status()})
            if path=='/api/upload/cover-zip':
                # Upload an existing ZIP directly; zip slips and zip bombs
                # are rejected before any extraction to the user profile.
                try:total=int(self.headers.get('Content-Length','0'))
                except ValueError:total=-1
                if not 0<total<=440*1024*1024:
                    raise ValueError('Kapak ZIP boyutu en fazla 440 MB olabilir.')
                temp_file=None
                try:
                    with tempfile.NamedTemporaryFile(dir=DATA,suffix='.zip',
                                                    prefix='kapak_',delete=False) as out:
                        temp_file=Path(out.name)
                        remaining=total
                        while remaining:
                            raw=self.rfile.read(min(1024*1024,remaining))
                            if not raw:raise ValueError('Kapak ZIP aktarımı eksik.')
                            out.write(raw)
                            remaining-=len(raw)
                    saved=0;skipped=0
                    with zipfile.ZipFile(temp_file) as archive:
                        members=[m for m in archive.infolist() if not m.is_dir()]
                        if len(members)>2000:
                            raise ValueError('ZIP içinde çok fazla dosya var.')
                        total_expanded=sum(m.file_size for m in members)
                        if total_expanded>650*1024*1024:
                            raise ValueError('ZIP açılmış boyutu güvenlik sınırını aşıyor.')
                        for member in members:
                            if member.flag_bits&0x1:
                                skipped+=1;continue
                            name=_safe_filename(Path(member.filename.replace('\\','/')).name)
                            if Path(name).suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                                skipped+=1;continue
                            if not 0<member.file_size<=30*1024*1024:
                                skipped+=1;continue
                            # Preserve only the safe basename in local assets.
                            # Never extract an archive member path itself.
                            with archive.open(member) as source:
                                with tempfile.NamedTemporaryFile(dir=ASSETS,
                                        suffix='.img',prefix='kapak_tmp_',delete=False) as dest:
                                    staged=Path(dest.name)
                                    shutil.copyfileobj(source,dest,1024*1024)
                            try:
                                with Image.open(staged) as check:check.verify()
                                staged.replace(ASSETS/name)
                                saved+=1
                            except (OSError,ValueError):
                                skipped+=1
                            finally:
                                staged.unlink(missing_ok=True)
                    COVER_IDX=_combined_covers()
                    return self._response({**_cover_status(),
                        'uploaded':saved,'skipped':skipped})
                finally:
                    if temp_file is not None:temp_file.unlink(missing_ok=True)
            if path=='/api/upload/cover':
                q=parse_qs(urlsplit(self.path).query)
                filename=_safe_filename((q.get('name') or ['kapak.jpg'])[0])
                if Path(filename).suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                    raise ValueError('Yalnız JPG/PNG/WebP kapak yüklenebilir.')
                raw=_read_body(self,25*1024*1024)
                # Image.open verifies the image is genuine before indexing.
                with Image.open(BytesIO(raw)) as im:im.verify()
                (ASSETS/filename).write_bytes(raw)
                return self._response({'name':filename})
            if path=='/api/upload/commit':
                COVER_IDX=_combined_covers()
                return self._response(_cover_status())
            if path=='/api/upload/logo':
                raw=_read_body(self,8*1024*1024)
                with Image.open(BytesIO(raw)) as i:
                    im=i.convert('RGBA');im.thumbnail((900,900))
                    file=DATA/'Magaza_Logo.png'
                    im.save(file)
                return self._response({'logo_path':str(file)})
            if path=='/api/upload/custom':
                q=parse_qs(urlsplit(self.path).query)
                filename=_safe_filename((q.get('name') or ['custom.jpg'])[0])
                if Path(filename).suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                    raise ValueError('Yalnız görsel kapak dosyası yüklenebilir.')
                raw=_read_body(self,25*1024*1024)
                with Image.open(BytesIO(raw)) as im:im.verify()
                name='Ozel_'+secrets.token_hex(5)+'_'+filename
                dest=ASSETS/name
                dest.write_bytes(raw)
                COVER_IDX=_combined_covers()
                return self._response({'cover_path':str(dest)})
            return self._response({'error':'Bilinmeyen işlem'},404)
        except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
            try:return self._response({'error':str(exc)[:300]},400)
            except (BrokenPipeError,ConnectionResetError):return
        except Exception as exc:
            try:return self._response({'error':'Beklenmeyen hata: '+str(exc)[:200]},500)
            except (BrokenPipeError,ConnectionResetError):return


def main():
    if '--self-check' in sys.argv:
        # Offline packaging check. No browser or HTTP listener is created.
        assert (WEB/'index.html').is_file(), 'Missing bundled HTML'
        assert (WEB/'app.js').is_file(), 'Missing bundled JavaScript'
        assert CATALOG, 'Bundled or persisted book catalog is missing'
        assert DATA.is_dir(), 'Persistent user-data folder is unavailable'
        print('ALFA Banner Studio self-check OK; catalog:',len(CATALOG))
        return
    DATA.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print('ALFA Banner Studio Pro · Yerel web arayüzü')
    print('Adres:',url)
    print('Bilgisayar dışına veri gönderilmez. Kapatmak için Ctrl+C.')
    webbrowser.open(url)
    try:server.serve_forever(poll_interval=.4)
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
