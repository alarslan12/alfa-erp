# database.py - ALFA ERP Yetki Korumalı Sepet Hafızalı ve Merged Hücre Çözümleyicili Veri Motoru
import os
import json
import tempfile
import shutil
import uuid
import copy
import time
from pathlib import Path
from datetime import datetime
import openpyxl
from utils import tr_kucult
from islem_gunlugu import AuditLog
from decimal import Decimal, InvalidOperation

class ERPDatabase:
    def __init__(self, excel_dosyasi=None, data_dir=None):
        self.excel_dosyasi = str(excel_dosyasi or (Path(__file__).resolve().parent / "KİTAPS.xlsx"))
        self.katalog = {}
        self.gruplar = {}
        self.kitaplar = []
        self.secili_siparisler = {}
        self.siparisler = []
        self.son_incelenen_sid = None
        
        # Sepet Hafıza (Session Precaution) Yapılandırması (Permission Denied önlemi için güvenli dizin)
        local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
        hedef_klasor = str(data_dir or os.environ.get("ALFA_ERP_DATA_DIR") or Path(local_app_data) / "AlfaERP")
        try:
            os.makedirs(hedef_klasor, exist_ok=True)
            self.sepet_dosyasi = os.path.join(hedef_klasor, "alfa_sepet_hafiza.json")
        except Exception:
            self.sepet_dosyasi = "alfa_sepet_hafiza.json"

        self.siparis_dosyasi = os.path.join(os.path.dirname(self.sepet_dosyasi), "alfa_siparisler.json")
        self.audit = AuditLog(os.path.dirname(self.sepet_dosyasi))
        self.bulut_gorulenler_dosyasi = os.path.join(
            os.path.dirname(self.sepet_dosyasi), 'alfa_bulut_gorulenler.json')
        self.cloud_api=None
        self.cloud_accounting_rows=[]
        self.cloud_accounting_loaded=False
        self.cloud_required=False
        self.cloud_epoch=None
        self.cloud_catalog_revision=None
        self._cloud_applying=False
        # Durable optimistic outbox: all network writes happen in a QThread.
        self._pending_file=Path(self.siparis_dosyasi).parent/'alfa_outbox.json'
        self._pending={};self._progress_events=[];self._status_events=[];self._conflicts=[];self._next_revision=0
        self._pending_started=0.0
        # Protect locally deleted orders against a late, pre-delete Firebase
        # snapshot arriving while the optimistic outbox is still in flight.
        self._deleted_cloud_ids=set()
        if self._pending_file.exists():
            try:
                stored=json.loads(self._pending_file.read_text(encoding='utf-8'))
                self._pending=stored.get('edits',{})
                self._deleted_cloud_ids.update(str(p.get('uuid')) for p in
                    self._pending.values() if p.get('delete') and p.get('uuid'))
                self._progress_events=stored.get('progress',[])
                self._status_events=stored.get('status_events',[])
                # Existing V6 queue retained; sequence new actions monotonically.
                for event in self._progress_events+self._status_events:
                    self._next_revision=max(self._next_revision,int(event.get('sequence',0)))
                self._conflicts=stored.get('conflicts',[])
                self._next_revision=max(self._next_revision,int(stored.get('revision',0)))
                if self._pending or self._progress_events or self._status_events:self._pending_started=time.monotonic()-3
            except (OSError,ValueError,TypeError):
                raise RuntimeError('Bekleyen bulut işlemleri okunamadı; veri kaybını önlemek için işlem durduruldu.')
        self.inventory_products=[]
        self.inventory_sales=[]
        self.inventory_revision=None
        self.siparisleri_yukle()
        self.sayac_dosyasi = os.path.join(os.path.dirname(self.sepet_dosyasi), "alfa_siparis_sayac.json")
        self._son_id = max((int(x["id"]) for x in self.siparisler if str(x.get("id", "")).isdigit()), default=0)
        if os.path.exists(self.sayac_dosyasi):
            with open(self.sayac_dosyasi, "r", encoding="utf-8") as f:
                self._son_id = max(self._son_id, int(json.load(f).get("son_id", 0)))
        self.sepet_kurtarilabilir = False
        self.hafiza_sepet = {}
        
        self.katalog_yukle()
        self.sepet_hafiza_kontrol()

    @staticmethod
    def _atomik_json_yaz(hedef, veri):
        klasor = os.path.dirname(os.path.abspath(hedef))
        os.makedirs(klasor, exist_ok=True)
        fd, gecici = tempfile.mkstemp(prefix=".alfa_", suffix=".tmp", dir=klasor)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(gecici, hedef)
        finally:
            if os.path.exists(gecici):
                os.remove(gecici)

    def siparisleri_yukle(self):
        if not os.path.exists(self.siparis_dosyasi):
            return
        try:
            with open(self.siparis_dosyasi, "r", encoding="utf-8") as f:
                veri = json.load(f)
            if not isinstance(veri, list) or not all(isinstance(x, dict) for x in veri):
                raise ValueError("Sipariş verisi liste biçiminde olmalı")
            self.siparisler = veri
        except (OSError, ValueError, TypeError) as e:
            print(f"❌ Siparişler okunamadı; dosya korunuyor: {e}")
            raise RuntimeError("Sipariş verileri yüklenemedi; veri kaybını önlemek için uygulama durduruldu") from e

    def siparisleri_kaydet(self):
        # İşlem günlüğü, bellek içindeki değişmiş objeden değil diskteki SON
        # başarılı kayıttan fark alır. Veri yazımı başarısızsa log oluşmaz.
        before = []
        if os.path.exists(self.siparis_dosyasi):
            with open(self.siparis_dosyasi, 'r', encoding='utf-8') as handle:
                before = json.load(handle)
            if not isinstance(before, list):
                raise ValueError('Sipariş veri dosyası bozuk; üzerine yazılamaz.')
            # Avoid a full second disk copy on every button click.
            backup=os.path.join(os.path.dirname(self.siparis_dosyasi), "alfa_siparisler_onceki.json")
            if not os.path.exists(backup) or time.time()-os.path.getmtime(backup)>60:
                shutil.copy2(self.siparis_dosyasi, backup)
        if self.cloud_required and not self.cloud_api and not self._cloud_applying:
            raise ValueError('Cihaz yönetici tarafından eşleştirilmeden sipariş değiştirilemez.')
        if self.cloud_required and self.cloud_api and not self.cloud_epoch and not self._cloud_applying:
            raise ValueError('Bulut ilk eşitlemesi henüz tamamlanmadı. Bağlantı kurulduğunda tekrar deneyin.')
        if self.cloud_api and not self._cloud_applying:
            self._queue_changes(before)
        self._atomik_json_yaz(self.siparis_dosyasi, self.siparisler)
        # Cloud audit is authoritative; no expensive duplicate local per-click diff.

    @staticmethod
    def _business(row):
        return {k:v for k,v in row.items() if k not in ('bulut_id','bulut_version','bulut_siparis_no','bulut_istem_id')}

    def _write_outbox(self):
        self._atomik_json_yaz(str(self._pending_file),{
            'edits':self._pending,'progress':self._progress_events,
            'status_events':self._status_events,'conflicts':self._conflicts,
            'revision':self._next_revision})

    @property
    def unreviewed_cloud_conflicts(self):
        return [x for x in self._conflicts if not x.get('reviewed_at')]

    def mark_cloud_conflicts_reviewed(self):
        """Acknowledge archived errors only; never discard failed work evidence."""
        stamp=datetime.now().astimezone().isoformat(timespec='seconds')
        count=0
        for entry in self._conflicts:
            if not entry.get('reviewed_at'):
                entry['reviewed_at']=stamp
                count+=1
        if count:self._write_outbox()
        return count

    @property
    def pending_count(self):
        return len(self._pending)+len(self._progress_events)+len(self._status_events)

    @staticmethod
    def _order_content_signature(order):
        """Only business fields and book quantities; status/counters are separate RPCs."""
        items=tuple(sorted((str(x.get('kod') or ''),
                           str(x.get('tur','SB')).upper(),
                           int(x.get('adet') or 0))
                          for x in order.get('kitaplar',[]) if isinstance(x,dict)))
        return (str(order.get('platform') or ''),
                str(order.get('kod') or ''),
                str(order.get('siparis_turu') or ''),
                round(float(order.get('ciro') or 0),2),
                str(order.get('tarih') or ''), items)

    def _queue_changes(self,before):
        """No HTTP here: record current local state and a durable outbox only."""
        old={str(x['id']):x for x in before}
        current={str(x['id']):x for x in self.siparisler}
        for sid,prior in old.items():
            if sid not in current:
                if not prior.get('bulut_id') and sid in self._pending:
                    # The creation never reached Supabase: cancel it locally.
                    self._pending.pop(sid,None)
                    continue
                if not prior.get('bulut_id'):
                    raise ValueError('Eski yerel sipariş buluta eşitlenmeden silinemez.')
                self._next_revision+=1
                self._pending[sid]={'revision':self._next_revision,'delete':True,
                    'uuid':prior['bulut_id'],'version':int(prior['bulut_version'])}
        for sid,row in current.items():
            prior=old.get(sid)
            if prior and self._business(prior)==self._business(row):continue
            if prior and not prior.get('bulut_id') and sid not in self._pending:
                raise ValueError('Eski yerel siparişler önce yönetici aracından buluta aktarılmalı.')
            # Semantic change detection: cloud-origin orders can contain
            # immutable snapshots and metadata that differ from local models.
            # A button click changing only status/counts must NEVER become a
            # heavy full-order edit (stale version => 409 / apparent rollback).
            if prior and row.get('bulut_id') and sid not in self._pending:
                same_content=self._order_content_signature(prior)==self._order_content_signature(row)
                previous_status=self.siparis_durumu(prior)
                next_status=self.siparis_durumu(row)
                status_changed=previous_status!=next_status
                fee_changed=(prior.get('kargo_ucreti')!=row.get('kargo_ucreti') or
                             prior.get('kargo_turu')!=row.get('kargo_turu'))
                if same_content and (not fee_changed or
                                     (status_changed and next_status=='tamamlandi')):
                    previous_items={(str(i.get('kod')),str(i.get('tur','SB')).upper()):i
                                    for i in prior.get('kitaplar',[])}
                    updates=[]
                    for item in row.get('kitaplar',[]):
                        key=(str(item.get('kod')),str(item.get('tur','SB')).upper())
                        old_item=previous_items.get(key)
                        if old_item is None:continue
                        old_ready=int(old_item.get('hazir') or 0)
                        old_boxed=int(old_item.get('koli') or 0)
                        target_ready=int(item.get('hazir') or 0)
                        target_boxed=int(item.get('koli') or 0)
                        dr=target_ready-old_ready
                        dk=target_boxed-old_boxed
                        if dr or dk:
                            self._next_revision+=1
                            updates.append({'kind':'progress',
                                'sequence':self._next_revision,'op_id':str(uuid.uuid4()),
                                'local_id':sid,'order_id':row['bulut_id'],
                                'book_code':key[0],'print_type':key[1],
                                'delta_ready':dr,'delta_boxed':dk,
                                'base_ready':old_ready,'base_boxed':old_boxed,
                                'target_ready':target_ready,'target_boxed':target_boxed})
                    def enqueue_status(a,b):
                        self._next_revision+=1
                        self._status_events.append({'kind':'status',
                            'sequence':self._next_revision,'op_id':str(uuid.uuid4()),
                            'local_id':sid,'order_id':row['bulut_id'],
                            'from_status':a,'to_status':b,
                            'shipping_fee':row.get('kargo_ucreti') if b=='tamamlandi' else None})
                    if status_changed and next_status=='aktif':
                        enqueue_status(previous_status,next_status)
                        # Status must come before queued progress events.
                        for event in updates:
                            self._next_revision+=1
                            event['sequence']=self._next_revision
                    self._progress_events.extend(updates)
                    if status_changed and next_status!='aktif':
                        enqueue_status(previous_status,next_status)
                    if status_changed or updates:
                        continue
                    if not fee_changed:
                        # Other local-only metadata is not a business edit.
                        continue
            request_id=row.get('bulut_istem_id') or str(uuid.uuid4())
            row['bulut_istem_id']=request_id
            self._next_revision+=1
            self._pending[sid]={'revision':self._next_revision,'delete':False}
        if self.pending_count and not self._pending_started:
            self._pending_started=time.monotonic()
        if self.pending_count:self._write_outbox()

    @staticmethod
    def _without_counts(row):
        result=copy.deepcopy(ERPDatabase._business(row))
        for item in result.get('kitaplar',[]):
            item.pop('hazir',None);item.pop('koli',None)
        return result

    @staticmethod
    def _without_status(row):
        result=copy.deepcopy(ERPDatabase._without_counts(row))
        for key in ('durum','isleme_alinma_tarihi','tamamlanma_tarihi',
                    'kargo_ucreti','kargo_turu'):
            result.pop(key,None)
        return result

    def next_outbox_batch(self,max_events=30):
        """One dependency-ordered batch. Never send progress before a pending start.

        Edits without cloud IDs are creations and must be sent before their events.
        Events retain the order of the user's actions across fast successive clicks.
        """
        current={str(x['id']):x for x in self.siparisler}
        for sid, entry in self._pending.items():
            row=current.get(sid)
            if row is not None and not row.get('bulut_id'):
                return self._commit_batch({sid:entry},current)
        # Status and progress are sequenced through their monotonic local sequence.
        combined=sorted(self._progress_events+self._status_events,
                        key=lambda e:int(e.get('sequence',0)))
        if combined:
            first=combined[0];kind=first.get('kind','progress')
            selected=[]
            for event in combined:
                if event.get('kind','progress')!=kind:break
                if kind=='progress':
                    # Normal path: all books for one order are one atomic PUT.
                    # Error recovery sets max_events=1 to isolate bad events;
                    # that mode MUST still return exactly one event.
                    if selected and (max_events==1 or
                       str(event.get('order_id'))!=str(first.get('order_id'))):
                        break
                elif len(selected)>=max_events:
                    break
                selected.append(copy.deepcopy(event))
            return {'kind':kind,'events':selected}
        if self._pending:
            return self._commit_batch(dict(list(self._pending.items())[:max_events]),current)
        return None

    def _commit_batch(self, entries, current):
        edits=[];revisions={}
        for sid,p in entries.items():
            revisions[sid]=p['revision']
            if p.get('delete'):
                edits.append({'local_id':sid,'uuid':p['uuid'],
                              'version':p['version'],'delete':True})
                continue
            row=current.get(sid)
            if row is None:continue
            edits.append({'local_id':sid,'uuid':row.get('bulut_id'),
                'version':int(row.get('bulut_version') or 0),
                'request_id':row.get('bulut_istem_id'),'order':copy.deepcopy(row)})
        return {'kind':'commit','edits':edits,'revisions':revisions} if edits else None

    def confirm_outbox(self,batch,results):
        by_id={str(x.get('id')):x for x in self.siparisler}
        if batch['kind'] in ('status','progress'):
            acknowledged={str(r['op_id']) for r in results}
            target=self._status_events if batch['kind']=='status' else self._progress_events
            target[:]=[e for e in target if str(e['op_id']) not in acknowledged]
            for r in results:
                for row in self.siparisler:
                    if str(row.get('bulut_id'))==str(r.get('order_id')):
                        row['bulut_version']=max(int(row.get('bulut_version') or 0),int(r['version']))
                        break
        else:
            for result in results:
                sid=str(result['local_id']);row=by_id.get(sid)
                if row is not None:
                    row.update(bulut_id=result['uuid'],bulut_version=int(result['version']),
                        bulut_siparis_no=int(result['order_number']))
                state=self._pending.get(sid)
                if state is not None:
                    if state['revision']==batch['revisions'].get(sid):
                        self._pending.pop(sid,None)
                    elif state.get('delete'):
                        state['version']=int(result['version'])
        if not self.pending_count:self._pending_started=0
        self._write_outbox()
        self._cloud_applying=True
        try:self.siparisleri_kaydet()
        finally:self._cloud_applying=False

    def quarantine_batch(self,batch,message):
        """Never re-post a permanent 409 forever. Preserve evidence for recovery."""
        self._conflicts.append({'at':datetime.now().astimezone().isoformat(),
            'reason':str(message)[:240],'batch':copy.deepcopy(batch)})
        if batch['kind'] in ('status','progress'):
            target=self._status_events if batch['kind']=='status' else self._progress_events
            ids={str(x['op_id']) for x in batch['events']}
            target[:]=[e for e in target if str(e['op_id']) not in ids]
        else:
            for sid,rev in batch['revisions'].items():
                if self._pending.get(sid,{}).get('revision')==rev:
                    self._pending.pop(sid,None)
        if not self.pending_count:self._pending_started=0
        # Force a later pull to reconcile any optimistic state that the server
        # explicitly rejected. Do not leave it looking synchronized forever.
        ids={str(e.get('local_id')) for e in batch.get('events',batch.get('edits',[]))}
        for row in self.siparisler:
            if str(row.get('id')) in ids and row.get('bulut_id'):
                row['bulut_version']=0
        self._write_outbox()
        self._cloud_applying=True
        try:self.siparisleri_kaydet()
        finally:self._cloud_applying=False

    def recover_old_outbox(self,payload):
        """Conservatively convert V6 old full-order edits into ordered actions.

        Only plain status/progress changes are migrated. Structural changes are
        retained for manual review, not silently overwritten. Never synthesize
        negative count deltas from a potentially stale cross-device snapshot.
        """
        if not self._pending:return
        cloud={str(o.get('id')):o for o in payload.get('orders',[])}
        lines={}
        for item in payload.get('items',[]):
            lines.setdefault(str(item.get('order_id')),{})[(str(item.get('book_code')),
                str(item.get('print_type')).upper())]=item
        changed=False
        for sid,pending in list(self._pending.items()):
            row=next((o for o in self.siparisler if str(o.get('id'))==sid),None)
            if not row or not row.get('bulut_id') or pending.get('delete'):continue
            if any(str(e.get('local_id'))==sid for e in self._progress_events+self._status_events):
                continue
            remote=cloud.get(str(row['bulut_id']))
            if not remote or remote.get('deleted_at'):continue
            if (str(row.get('kod',''))!=str(remote.get('shipping_reference') or '') or
                str(row.get('platform',''))!=str(remote.get('platform') or '') or
                str(row.get('siparis_turu',''))!=str(remote.get('order_type') or '') or
                abs(float(row.get('ciro') or 0)-float(remote.get('gross_amount') or 0))>0.009):
                continue
            remote_lines=lines.get(str(row['bulut_id']),{})
            local_lines={(str(i.get('kod')),str(i.get('tur','SB')).upper()):i for i in row.get('kitaplar',[])}
            if local_lines.keys()!=remote_lines.keys() or any(
                int(local_lines[k].get('adet',0))!=int(remote_lines[k].get('quantity',0))
                for k in local_lines):continue
            # Historic counters may be old; reconcile only safe, nonnegative deltas.
            deltas=[]
            for key,item in local_lines.items():
                earlier=remote_lines[key]
                dr=int(item.get('hazir',0))-int(earlier.get('prepared_count') or 0)
                dk=int(item.get('koli',0))-int(earlier.get('boxed_count') or 0)
                if dr<0 or dk<0:
                    deltas=None;break
                if dr or dk:deltas.append((key,dr,dk))
            if deltas is None:continue
            source=str(remote.get('status') or 'havuz');target=self.siparis_durumu(row)
            prefix=[];suffix=[]
            if source!=target:
                if source=='havuz' and target in ('aktif','tamamlandi'):
                    prefix=[('havuz','aktif')]
                    if target=='tamamlandi':suffix=[('aktif','tamamlandi')]
                elif source=='aktif' and target in ('havuz','tamamlandi'):
                    if target=='tamamlandi':suffix=[('aktif','tamamlandi')]
                    elif deltas:continue
                    else:prefix=[('aktif','havuz')]
                elif source=='tamamlandi' and target=='aktif' and not deltas:
                    prefix=[('tamamlandi','aktif')]
                else:continue
            elif deltas and source!='aktif':continue
            self._pending.pop(sid,None)
            for from_status,to_status in prefix:
                self._next_revision+=1
                self._status_events.append({'kind':'status','sequence':self._next_revision,
                     'op_id':str(uuid.uuid4()),'local_id':sid,'order_id':row['bulut_id'],
                     'from_status':from_status,'to_status':to_status,'shipping_fee':None})
            for key,dr,dk in deltas:
                self._next_revision+=1
                self._progress_events.append({'kind':'progress','sequence':self._next_revision,
                     'op_id':str(uuid.uuid4()),'local_id':sid,'order_id':row['bulut_id'],
                     'book_code':key[0],'print_type':key[1],
                     'delta_ready':dr,'delta_boxed':dk})
            for from_status,to_status in suffix:
                self._next_revision+=1
                self._status_events.append({'kind':'status','sequence':self._next_revision,
                     'op_id':str(uuid.uuid4()),'local_id':sid,'order_id':row['bulut_id'],
                     'from_status':from_status,'to_status':to_status,
                     'shipping_fee':row.get('kargo_ucreti')})
            changed=True
        if changed:self._write_outbox()

    def apply_cloud_snapshot(self,payload):
        from mobil_siparis_donusum import convert_mobile_order
        if not isinstance(payload,dict):
            raise ValueError('Bulut yanıtı geçersiz.')
        reset_changes=[]
        full_order_snapshot=('orders' in payload and 'items' in payload)
        # Revision-aware snapshots omit unchanged order rows entirely.
        # Keep the existing local orders; only process books/inventory/accounting.
        if 'orders' not in payload and 'items' not in payload:
            if str(payload.get('epoch') or '') != str(self.cloud_epoch or ''):
                raise ValueError('Bulut sıfırlaması tam sipariş verisi gerektiriyor.')
            payload = {**payload, 'orders':[], 'items':[]}
        if not isinstance(payload.get('orders'),list) or not isinstance(payload.get('items'),list):
            raise ValueError('Bulut sipariş verisi geçersiz.')
        # Bulut çalışma alanı nesil kimliği değişince eski yerel test verilerini
        # yeniden içe aktarma veya güncelleme. Önce geri alınabilir yedekle.
        new_epoch=str(payload.get('epoch') or '')
        if new_epoch and new_epoch!=self.cloud_epoch:
            marker=Path(self.siparis_dosyasi).parent/'alfa_cloud_epoch.json'
            old_epoch=None
            if marker.exists():
                try:old_epoch=json.loads(marker.read_text(encoding='utf-8')).get('epoch')
                except (OSError,ValueError):old_epoch=None
            if old_epoch!=new_epoch:
                # Preserve any unsent edits instead of resetting the local outbox.
                if self.pending_count:
                    raise ValueError('Yeni Firebase nesli algılandı ancak bekleyen yerel işlemler var. İşlemler korunuyor; önce kuyruğu inceleyin.')
                reset_changes=['__siparisler__'] if self.siparisler else []
                data_root=Path(self.siparis_dosyasi).parent
                backup=data_root/'arsiv_eski_test_kayitlari'
                backup.mkdir(parents=True,exist_ok=True)
                for name in ('alfa_siparisler.json','alfa_siparisler_onceki.json',
                             'alfa_siparis_sayac.json','alfa_bulut_gorulenler.json',
                             'alfa_muhasebe_gunleri.json','alfa_islem_gunlugu.jsonl',
                             'alfa_sepet_hafiza.json','alfa_bildirim_durumu.json',
                             'alfa_outbox.json'):
                    old_file=data_root/name
                    if old_file.exists():
                        dest=backup/(new_epoch+'_'+name)
                        counter=1
                        while dest.exists():
                            dest=backup/(new_epoch+'_'+str(counter)+'_'+name)
                            counter+=1
                        shutil.move(str(old_file),str(dest))
                self.siparisler.clear();self._son_id=0
                self.cloud_accounting_rows=[];self.cloud_accounting_loaded=False
                self.secili_siparisler={};self.hafiza_sepet={}
                self._pending.clear();self._progress_events.clear();self._status_events.clear();self._conflicts.clear()
                self._pending_started=0
                self._write_outbox()
                self._atomik_json_yaz(self.siparis_dosyasi,[])
                self._atomik_json_yaz(self.sayac_dosyasi,{'son_id':0})
                self._atomik_json_yaz(marker,{'epoch':new_epoch})
            self.cloud_epoch=new_epoch
        self.recover_old_outbox(payload)
        catalog_changed=self.apply_cloud_catalog(payload)
        before_accounting=json.dumps(self.cloud_accounting_rows,sort_keys=True,default=str)
        if isinstance(payload.get('accounting_days'),list):
            self.cloud_accounting_rows=payload['accounting_days']
            self.cloud_accounting_loaded=True
        accounting_changed=before_accounting!=json.dumps(self.cloud_accounting_rows,sort_keys=True,default=str)
        inventory_changed=False
        if isinstance(payload.get('inventory_products'),list):
            new_rev=payload.get('inventory_revision')
            if new_rev!=self.inventory_revision:
                self.inventory_products=payload['inventory_products']
                self.inventory_sales=payload.get('inventory_sales') or []
                self.inventory_revision=new_rev
                inventory_changed=True
        items={}
        for item in payload['items']:items.setdefault(str(item['order_id']),[]).append(item)
        existing={str(o['bulut_id']):o for o in self.siparisler if o.get('bulut_id')}
        pending_requests={str(o.get('bulut_istem_id')) for o in self.siparisler
            if str(o.get('id')) in self._pending and o.get('bulut_istem_id')}
        staged=[]
        deleted_inflight=self._deleted_cloud_ids | {
            str(p.get('uuid')) for p in self._pending.values()
            if p.get('delete') and p.get('uuid')}
        for row in payload['orders']:
            uid=str(row.get('id') or '')
            if not uid:continue
            # A concurrent GET can return the order as it looked just before
            # our successful soft-delete; never re-add that ghost into the pool.
            if uid in deleted_inflight:continue
            local=existing.get(uid)
            if local is None and str(row.get('client_request_id') or '') in pending_requests:
                continue  # Creation reached server; preserve local optimistic row until ack.
            if row.get('deleted_at'):
                if local is not None and str(local['id']) not in self._pending:
                    staged.append((uid,None))
            elif local is not None and (str(local['id']) in self._pending or
                    any(str(e.get('local_id'))==str(local['id']) for e in self._progress_events+self._status_events)):
                continue  # Keep optimistic state until its pending work is acknowledged.
            elif local is None or int(local.get('bulut_version',0))!=int(row.get('version') or 0):
                staged.append((uid,convert_mobile_order(row,items.get(uid,[]),{**self.katalog,**getattr(self,'archived_catalog',{})})))
        if full_order_snapshot:
            # A complete RTDB response is authoritative, including zero rows.
            # Old local cloud orders omitted after production cutover are ghosts;
            # retain work explicitly in the durable outbox and never prune it.
            remote_ids={str(r.get('id')) for r in payload['orders']
                        if isinstance(r,dict) and r.get('id') and not r.get('deleted_at')}
            staged_ids={uid for uid,_ in staged}
            protected=set(self._pending)
            protected.update(str(e.get('local_id'))
                for e in self._progress_events+self._status_events)
            for local in list(self.siparisler):
                uid=str(local.get('bulut_id') or '')
                if uid and uid not in remote_ids and uid not in staged_ids and str(local.get('id')) not in protected:
                    staged.append((uid,None))
                    staged_ids.add(uid)
        if not staged:return reset_changes+(['__muhasebe__'] if accounting_changed else [])+(['__katalog__'] if catalog_changed else [])+(['__envanter__'] if inventory_changed else [])
        previous=[dict(x) for x in self.siparisler]
        ids={int(x['id']) for x in self.siparisler if str(x.get('id','')).isdigit()}
        latest=max(ids or {0});changed=[]
        try:
            for uid,converted in staged:
                current=existing.get(uid)
                if converted is None:
                    changed.append(current['id']);self.siparisler.remove(current)
                elif current is not None:
                    sid=current['id'];current.clear();current.update(converted);current['id']=sid;changed.append(sid)
                else:
                    intended=int(converted.get('bulut_siparis_no') or 0)
                    sid=intended if intended>=1 and intended not in ids else latest+1
                    while sid in ids:sid+=1
                    latest=max(latest,sid);ids.add(sid)
                    converted['id']=sid;self.siparisler.append(converted);changed.append(sid)
            self._cloud_applying=True
            self.siparisleri_kaydet()
            self._son_id=latest
            self._atomik_json_yaz(self.sayac_dosyasi,{'son_id':latest})
        except Exception:
            self.siparisler=previous;raise
        finally:self._cloud_applying=False
        if accounting_changed:changed.append('__muhasebe__')
        if catalog_changed:changed.append('__katalog__')
        if inventory_changed:changed.append('__envanter__')
        return reset_changes+changed

    def apply_cloud_catalog(self,payload):
        revision=payload.get('catalog_revision')
        rows=payload.get('books')
        if not isinstance(rows,list) or not revision:return False
        if revision==self.cloud_catalog_revision:return False
        mapping={};books=[];groups={}
        archived={}
        for row in rows:
            if not isinstance(row,dict):continue
            code=str(row.get('code') or '').strip()
            if not code:continue
            book={'kod':code,'isim':str(row.get('name') or code),
                 'sayfa':max(0,int(row.get('page_count') or 0)),
                 'renkli_opsiyon':bool(row.get('supports_color')),
                 'grup':str(row.get('group_name') or 'Tekil Kitaplar')}
            book['grup_temiz']=tr_kucult(book['grup'])
            if not row.get('is_active'):
                archived[code]=book
                continue
            mapping[code]=book;books.append(book)
            groups.setdefault(book['grup'],[]).append(code)
        if not mapping:
            raise ValueError('Bulut katalog boş, yerel katalog korunuyor.')
        # The RTDB UUID-key iteration order is NOT the book code order.
        def sort_code(book):
            code=str(book.get('kod') or '').strip()
            return (0,int(code),code) if code.isdecimal() else (1,code.casefold(),code)
        books.sort(key=sort_code)
        self.katalog.clear();self.katalog.update(mapping)
        self.kitaplar.clear();self.kitaplar.extend(books)
        self.gruplar.clear();self.gruplar.update(groups)
        self.archived_catalog=archived
        self.cloud_catalog_revision=revision
        return True

    def bulut_bilinen_kayitlar(self):
        """Imported IDs and deletion tombstones. Prevents re-import after local deletion."""
        known = {str(o['bulut_id']) for o in self.siparisler if o.get('bulut_id')}
        if os.path.exists(self.bulut_gorulenler_dosyasi):
            with open(self.bulut_gorulenler_dosyasi, encoding='utf-8') as f:
                stored = json.load(f)
            if not isinstance(stored, list) or not all(isinstance(x,str) for x in stored):
                raise ValueError('Bulut aktarılan kayıtlar dosyası geçersiz.')
            known.update(stored)
        return known

    def bulut_siparislerini_havuza_al(self, batches, errors=None):
        """Import fresh mobile orders once, preserving every existing desktop order."""
        from mobil_siparis_donusum import convert_mobile_order
        known = self.bulut_bilinen_kayitlar()
        next_id = max([0, self._son_id] +
                      [int(o['id']) for o in self.siparisler if str(o.get('id', '')).isdigit()])
        imported = []
        for row, items in batches:
            cloud_id = str(row.get('id', '')).strip()
            if not cloud_id or cloud_id in known:
                continue
            try:
                order = convert_mobile_order(row, items, self.katalog)
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                if errors is None:
                    # Preserve the original strict behavior for existing callers.
                    raise
                errors.append('Sipariş ' + cloud_id[:12] + ': ' + str(exc)[:160])
                continue
            next_id += 1
            order['id'] = next_id
            imported.append(order)
            known.add(cloud_id)
        if not imported:
            return []
        self.siparisler.extend(imported)
        try:
            self.siparisleri_kaydet()
        except Exception:
            del self.siparisler[-len(imported):]
            raise
        self._son_id = next_id
        try:
            self._atomik_json_yaz(self.sayac_dosyasi, {'son_id': next_id})
        except OSError:
            pass  # Orders file remains the authoritative counter.
        return [row['id'] for row in imported]

    def yeni_siparis_id(self):
        yeni = self._son_id + 1
        self._atomik_json_yaz(self.sayac_dosyasi, {"son_id": yeni})
        self._son_id = yeni
        return yeni

    # Durumlar tek kayıtta tutulur; eski kayıtlar aktif sipariş kabul edilir.
    DURUMLAR = ("havuz", "aktif", "tamamlandi")

    @staticmethod
    def siparis_durumu(siparis):
        durum = siparis.get("durum", "aktif")
        return durum if durum in ERPDatabase.DURUMLAR else "aktif"

    @staticmethod
    def kolileme_tamam(siparis):
        kitaplar = siparis.get("kitaplar", [])
        if not isinstance(kitaplar, list) or not kitaplar:
            return False
        try:
            return all(int(k["adet"]) > 0 and
                       int(k.get("koli", 0)) >= int(k["adet"]) for k in kitaplar)
        except (KeyError, TypeError, ValueError):
            return False

    def durumdaki_siparisler(self, durum):
        if durum not in self.DURUMLAR:
            raise ValueError("Geçersiz sipariş durumu")
        return [s for s in self.siparisler if self.siparis_durumu(s) == durum]

    @staticmethod
    def kargo_kategorisi(siparis):
        """Telafi öncelikli; normal açık adres siparişini ayrı tut."""
        kind = tr_kucult(siparis.get('siparis_turu', ''))
        platform = tr_kucult(siparis.get('platform', ''))
        if 'telafi' in kind:
            return 'telafi'
        if 'acik adres' in platform or 'acik adres' in kind:
            return 'acik_adres'
        return None

    def siparis_durumunu_degistir(self, siparis, yeni_durum, kargo_ucreti=None):
        from datetime import datetime
        eski = self.siparis_durumu(siparis)
        if (eski, yeni_durum) not in (("havuz", "aktif"), ("aktif", "tamamlandi"), ("aktif", "havuz"), ("tamamlandi", "aktif")):
            raise ValueError("İzin verilmeyen sipariş geçişi")
        if yeni_durum == "tamamlandi" and not self.kolileme_tamam(siparis):
            raise ValueError("Bütün kitaplar kolilenmeden sipariş tamamlanamaz")
        if siparis not in self.siparisler:
            raise ValueError("Sipariş bulunamadı")
        category = self.kargo_kategorisi(siparis) if yeni_durum == 'tamamlandi' else None
        if category is not None:
            if kargo_ucreti is None:
                raise ValueError('Telafi veya açık adres siparişinde kargo ücreti girilmelidir.')
            try:
                fee = Decimal(str(kargo_ucreti).strip().replace(',', '.'))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError('Kargo ücreti sayı olmalıdır.') from exc
            if not fee.is_finite() or not Decimal('0') <= fee <= Decimal('10000000'):
                raise ValueError('Kargo ücreti 0 ile 10.000.000 TL arasında olmalıdır.')
            fee = float(round(fee, 2))
        onceki = dict(siparis)
        if category is not None:
            siparis['kargo_ucreti'] = fee
            siparis['kargo_turu'] = category
        siparis["durum"] = yeni_durum
        if yeni_durum == "aktif":
            siparis["isleme_alinma_tarihi"] = datetime.now().astimezone().isoformat(timespec="seconds")
            siparis.pop("tamamlanma_tarihi", None)
        elif yeni_durum == "tamamlandi":
            siparis["tamamlanma_tarihi"] = datetime.now().astimezone().isoformat(timespec="seconds")
        else:
            siparis.pop("isleme_alinma_tarihi", None)
            siparis.pop("tamamlanma_tarihi", None)
        try:
            self.siparisleri_kaydet()
        except Exception:
            siparis.clear()
            siparis.update(onceki)
            raise

    def siparis_sil(self, siparis):
        """Her durumdaki siparişi onay sonrasında atomik yedekli kayıtla sil."""
        if self.siparis_durumu(siparis) not in ('havuz', 'aktif', 'tamamlandi'):
            raise ValueError('Geçersiz sipariş durumu.')
        if siparis not in self.siparisler:
            raise ValueError('Sipariş bulunamadı.')
        position = self.siparisler.index(siparis)
        if siparis.get('bulut_id'):
            previous_seen = self.bulut_bilinen_kayitlar()
            previous_seen.add(str(siparis['bulut_id']))
            self._atomik_json_yaz(self.bulut_gorulenler_dosyasi, sorted(previous_seen))
        cloud_id=str(siparis.get('bulut_id') or '')
        if cloud_id:self._deleted_cloud_ids.add(cloud_id)
        self.siparisler.pop(position)
        try:
            self.siparisleri_kaydet()
        except Exception:
            self.siparisler.insert(position, siparis)
            if cloud_id:self._deleted_cloud_ids.discard(cloud_id)
            raise

    def siparis_ozeti(self, siparis):
        """Kitap adedi, SB/RNK adedi ve toplam basılacak sayfa."""
        sb = rnk = sayfa = hazir = koli = 0
        for item in siparis.get("kitaplar", []):
            try:
                adet = max(0, int(item.get("adet", 0)))
                kitap_sayfa = max(0, int(item.get("sayfa_birim") if item.get("sayfa_birim") is not None else self.katalog.get(str(item.get("kod", "")), {}).get("sayfa", 0)))
                hazir += min(adet, max(0, int(item.get("hazir", 0))))
                koli += min(adet, max(0, int(item.get("koli", 0))))
            except (ValueError, TypeError):
                continue
            if str(item.get("tur", "SB")).upper() in ("RNK", "RENKLİ", "RENKLI"):
                rnk += adet
            else:
                sb += adet
            sayfa += adet * kitap_sayfa
        return {"adet": sb + rnk, "sb": sb, "rnk": rnk, "sayfa": sayfa, "hazir": hazir, "koli": koli}

    def siparis_duzenle(self, siparis, alanlar, yeni_kitaplar):
        """Havuz/aktif siparişlerde tüm alanları tek atomik işlemle kaydeder."""
        if self.siparis_durumu(siparis) not in ("havuz", "aktif"):
            raise ValueError("Tamamlanan sipariş önce aktife geri alınmalıdır")
        if siparis not in self.siparisler:
            raise ValueError("Sipariş bulunamadı")
        if not yeni_kitaplar:
            raise ValueError("Sipariş en az bir kitap içermelidir")
        if not all(str(x.get("kod", "")) in self.katalog for x in yeni_kitaplar):
            raise ValueError("Katalogda bulunmayan kitap kodu var")
        if not str(alanlar.get("kod", "")).strip():
            raise ValueError("Kargo kodu / adres boş olamaz")
        try:
            ciro = float(str(alanlar.get("ciro", 0)).replace(",", "."))
        except (ValueError, TypeError) as exc:
            raise ValueError("Ciro sayısal olmalıdır") from exc
        if not 0 <= ciro < 1_000_000_000:
            raise ValueError("Ciro geçerli aralıkta değil")
        temiz = []
        birlesmis = {}
        for item in yeni_kitaplar:
            kod = str(item.get("kod", "")).strip()
            tur = str(item.get("tur", "SB")).upper()
            if tur not in ("SB", "RNK"):
                raise ValueError("Kitap türü SB veya RNK olmalıdır")
            try:
                adet = int(item.get("adet", 0))
                hazir = int(item.get("hazir", 0))
                koli = int(item.get("koli", 0))
            except (ValueError, TypeError) as exc:
                raise ValueError("Kitap miktarları tam sayı olmalıdır") from exc
            if adet <= 0 or not (0 <= koli <= hazir <= adet):
                raise ValueError("Geçersiz kitap / hazırlık / koli adedi")
            key = (kod, tur)
            if key not in birlesmis:
                birlesmis[key] = {"kod": kod, "tur": tur, "adet": 0, "hazir": 0, "koli": 0}
            for fld, val in (("adet", adet), ("hazir", hazir), ("koli", koli)):
                birlesmis[key][fld] += val
        temiz = list(birlesmis.values())
        onceki = dict(siparis)
        siparis.update({
            "platform": str(alanlar.get("platform", "")).strip(),
            "kod": str(alanlar["kod"]).strip(),
            "ciro": ciro,
            "siparis_turu": str(alanlar.get("siparis_turu", "")).strip(),
            "kitaplar": temiz,
        })
        try:
            self.siparisleri_kaydet()
        except Exception:
            siparis.clear()
            siparis.update(onceki)
            raise

    def siparis_ilerleme_degistir(self, siparis, kod, tur, hazir, koli):
        """Tek kitap varyantı için basıldı/kolilendi sayısını güvenle kaydeder."""
        if self.siparis_durumu(siparis) not in ("havuz", "aktif"):
            raise ValueError("Bu siparişin ilerlemesi değiştirilemez")
        if siparis not in self.siparisler:
            raise ValueError("Sipariş bulunamadı")
        item = next((x for x in siparis.get("kitaplar", [])
                     if str(x.get("kod")) == str(kod) and str(x.get("tur", "SB")).upper() == str(tur).upper()), None)
        if item is None:
            raise ValueError("Kitap siparişte bulunamadı")
        adet = int(item.get("adet", 0))
        if not (0 <= koli <= hazir <= adet):
            raise ValueError("Önce hazırlanma, sonra kolileme işaretlenmelidir")
        onceki = (item.get("hazir", 0), item.get("koli", 0))
        item["hazir"], item["koli"] = hazir, koli
        try:
            self.siparisleri_kaydet()
        except Exception:
            item["hazir"], item["koli"] = onceki
            raise

    def siparis_toplu_ilerlet(self, siparis, kitap_kodlari, hedef):
        """Seçili kitap kodlarının SB/RNK varyantlarını tek kayıtla ilerletir.

        Kolilemede daha önce hazırlanmış olmayan kopya otomatik hazırlanmaz;
        işlem reddedilir ve sipariş olduğu gibi kalır.
        """
        if self.siparis_durumu(siparis) != 'aktif':
            raise ValueError('İlerleme yalnızca aktif siparişte yapılabilir.')
        if siparis not in self.siparisler:
            raise ValueError('Sipariş bulunamadı.')
        if hedef not in ('hazir', 'koli'):
            raise ValueError('Bilinmeyen ilerleme işlemi.')
        kodlar = {str(k) for k in kitap_kodlari}
        if not kodlar:
            raise ValueError('En az bir kitap seçilmelidir.')
        hedefler = [x for x in siparis.get('kitaplar', [])
                    if str(x.get('kod')) in kodlar]
        if not hedefler:
            raise ValueError('Seçilen kitaplar siparişte bulunamadı.')
        if hedef == 'koli' and any(int(x.get('hazir', 0)) != int(x.get('adet', 0))
                                   for x in hedefler):
            raise ValueError('Toplu kolilemeden önce seçili kitapların tamamı hazırlanmalıdır.')
        onceki = [(x, x.get('hazir', 0), x.get('koli', 0)) for x in hedefler]
        for x in hedefler:
            x[hedef] = int(x['adet'])
        try:
            self.siparisleri_kaydet()
        except Exception:
            for x, hazir, koli in onceki:
                x['hazir'], x['koli'] = hazir, koli
            raise
        return len(hedefler)

    def siparis_kitaplarini_degistir(self, siparis, yeni_kitaplar):
        self.siparis_duzenle(siparis, {
            "platform": siparis.get("platform", ""),
            "kod": siparis.get("kod", ""),
            "ciro": siparis.get("ciro", 0),
            "siparis_turu": siparis.get("siparis_turu", ""),
        }, yeni_kitaplar)

    def siparis_gruplari(self, siparis):
        """Aynı kitap kodunu SB ve RNK varyantlarıyla tek başlık altında toplar."""
        gruplar = {}
        for item in siparis.get("kitaplar", []):
            kod = str(item.get("kod", "")).strip()
            if not kod:
                continue
            tur = str(item.get("tur", "SB")).upper()
            try:
                adet = max(0, int(item.get("adet", 0)))
                hazir = min(adet, max(0, int(item.get("hazir", 0))))
                koli = min(hazir, max(0, int(item.get("koli", 0))))
            except (ValueError, TypeError):
                continue
            bilgi = self.katalog.get(kod, {})
            grup = gruplar.setdefault(kod, {
                "kod": kod, "isim": bilgi.get("isim", kod), "kitap_grubu": bilgi.get("grup", ""),
                "sayfa_birim": max(0, int(item.get("sayfa_birim") if item.get("sayfa_birim") is not None else bilgi.get("sayfa", 0) or 0)),
                "adet": 0, "hazir": 0, "koli": 0,
                "sb": 0, "sb_hazir": 0, "sb_koli": 0,
                "rnk": 0, "rnk_hazir": 0, "rnk_koli": 0,
            })
            grup["adet"] += adet
            grup["hazir"] += hazir
            grup["koli"] += koli
            if tur == "RNK":
                grup["rnk"] += adet
                grup["rnk_hazir"] += hazir
                grup["rnk_koli"] += koli
            else:
                grup["sb"] += adet
                grup["sb_hazir"] += hazir
                grup["sb_koli"] += koli
        liste = list(gruplar.values())
        for g in liste:
            g["sayfa_toplam"] = g["sayfa_birim"] * g["adet"]
            g["hazir_sayfa"] = g["sayfa_birim"] * max(0, g["adet"] - g["hazir"])
        return liste

    def siparis_ara_metin(self, siparis):
        alanlar = [str(siparis.get("id", "")), str(siparis.get("platform", "")), str(siparis.get("kod", "")), str(siparis.get("siparis_turu", ""))]
        for grup in self.siparis_gruplari(siparis):
            alanlar.extend([grup.get("kod", ""), grup.get("isim", ""), grup.get("kitap_grubu", "")])
        return " ".join(str(x) for x in alanlar if x)

    def durum_istatistikleri(self, durum):
        toplam = {"siparis": 0, "ciro": 0.0, "adet": 0, "sayfa": 0, "sb": 0, "rnk": 0, "hazir": 0, "koli": 0, "hazir_sayfa": 0}
        for siparis in self.durumdaki_siparisler(durum):
            ozet = self.siparis_ozeti(siparis)
            toplam["siparis"] += 1
            toplam["ciro"] += float(siparis.get("ciro", 0) or 0)
            for anahtar in ("adet", "sayfa", "sb", "rnk", "hazir", "koli"):
                toplam[anahtar] += ozet.get(anahtar, 0)
            toplam["hazir_sayfa"] += sum(g["sayfa_birim"] * max(0, g["adet"] - g["hazir"]) for g in self.siparis_gruplari(siparis))
        return toplam

    def _bul_excel(self):
        adaylar = [
            self.excel_dosyasi,
            "KİTAPS.xlsx",
            "KITAPS.xlsx",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "KİTAPS.xlsx"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "KITAPS.xlsx"),
        ]
        for aday in adaylar:
            if aday and os.path.exists(aday):
                return aday
        return None

    def sepet_hafiza_kontrol(self):
        """Uygulama açılışında yarım kalmış sepet var mı kontrol eder."""
        if os.path.exists(self.sepet_dosyasi):
            try:
                with open(self.sepet_dosyasi, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and any(isinstance(t, dict) and any(isinstance(v, int) and v > 0 for v in t.values()) for t in data.values()):
                        self.hafiza_sepet = data
                        self.sepet_kurtarilabilir = True
            except Exception as e:
                print(f"⚠️ Sepet hafızası okunamadı: {e}")

    def sepeti_hafizaya_kaydet(self):
        """Sepetteki her değişiklikte verileri güvenli JSON deposuna yazar."""
        try:
            self._atomik_json_yaz(self.sepet_dosyasi, self.secili_siparisler)
        except Exception as e:
            print(f"❌ Sepet hafızaya kaydedilemedi: {e}")

    def sepeti_hafizadan_sil(self):
        """Sipariş tamamlandığında veya reddedildiğinde hafızayı temizler."""
        if os.path.exists(self.sepet_dosyasi):
            try:
                os.remove(self.sepet_dosyasi)
            except Exception:
                pass

    def katalog_yukle(self):
        dosya = self._bul_excel()
        if not dosya:
            print(f"❌ HATA: '{self.excel_dosyasi}' konumunda Excel dosyası bulunamadı!")
            return

        try:
            wb = openpyxl.load_workbook(dosya, data_only=True)
            ws = wb.active

            # 1. Adım: Tüm Birleştirilmiş Hücreleri (Merged Cells) Doğru Koordinatlarla Haritalandır
            merged_lookup = {}
            for m_range in ws.merged_cells.ranges:
                min_c, min_r, max_c, max_r = m_range.min_col, m_range.min_row, m_range.max_col, m_range.max_row
                parent_val = ws.cell(row=min_r, column=min_c).value
                if parent_val is None or str(parent_val).strip() == "":
                    for rr in range(min_r, max_r + 1):
                        for cc in range(min_c, max_c + 1):
                            v = ws.cell(row=rr, column=cc).value
                            if v is not None and str(v).strip() != "":
                                parent_val = v
                                break
                        if parent_val is not None and str(parent_val).strip() != "":
                            break

                if parent_val is not None and str(parent_val).strip() != "":
                    temiz_parent = " - ".join([p.strip() for p in str(parent_val).splitlines() if p.strip()])
                    for r in range(min_r, max_r + 1):
                        for c in range(min_c, max_c + 1):
                            merged_lookup[(r, c)] = temiz_parent

            def hucre_oku(r, c):
                if (r, c) in merged_lookup:
                    return merged_lookup[(r, c)]
                val = ws.cell(row=r, column=c).value
                if val is None:
                    return ""
                return " - ".join([p.strip() for p in str(val).splitlines() if p.strip()])

            # 2. Adım: Başlık satırını ve sütun indekslerini tespit et
            baslik_satiri = 1
            for r in range(1, min(10, ws.max_row + 1)):
                satir_metni = " ".join([tr_kucult(ws.cell(row=r, column=c).value or "") for c in range(1, ws.max_column + 1)])
                if "kod" in satir_metni and ("ad" in satir_metni or "sayfa" in satir_metni):
                    baslik_satiri = r
                    break

            kod_col = None
            isim_col = None
            sayfa_col = None
            renkli_col = None
            grup_cols = []
            haric_kelimeler = ("fiyat", "stok", "maliyet", "tutar", "barkod", "adet", "koli")

            for c in range(1, ws.max_column + 1):
                baslik = tr_kucult(hucre_oku(baslik_satiri, c))
                if "kod" in baslik and kod_col is None:
                    kod_col = c
                elif ("kitap ad" in baslik or baslik in ("ad", "adi", "isim", "kitap")) and isim_col is None:
                    isim_col = c
                elif "sayfa" in baslik and sayfa_col is None:
                    sayfa_col = c
                elif "renk" in baslik and renkli_col is None:
                    renkli_col = c
                elif any(k in baslik for k in ("grub", "grup", "kategor", "seri", "set", "bolum", "klinik", "brans", "tur")):
                    grup_cols.append(c)

            # Başlığı olmasa bile yan sütunlara yazılmış (ÇTS Klinik, TTS Klinik vb.) merged/metin kategori sütunlarını yakala
            ana_sutunlar = {kod_col, isim_col, sayfa_col, renkli_col}
            for c in range(1, ws.max_column + 1):
                if c in ana_sutunlar or c in grup_cols:
                    continue
                baslik = tr_kucult(hucre_oku(baslik_satiri, c))
                if any(hk in baslik for hk in haric_kelimeler):
                    continue
                for r in range(baslik_satiri + 1, ws.max_row + 1):
                    v = hucre_oku(r, c)
                    v_low = tr_kucult(v)
                    if v_low and v_low not in ("nan", "none", "nat", "x", "evet", "hayir", "var", "yok") and not v_low.replace(".", "", 1).isdigit():
                        grup_cols.append(c)
                        break

            self.katalog.clear()
            self.kitaplar.clear()
            self.gruplar.clear()

            basarili = 0
            for r in range(baslik_satiri + 1, ws.max_row + 1):
                kod_ham = ws.cell(row=r, column=kod_col).value if kod_col else None
                sayfa_ham = ws.cell(row=r, column=sayfa_col).value if sayfa_col else None
                if kod_ham is None or sayfa_ham is None:
                    continue

                try:
                    sayfa = int(float(sayfa_ham))
                    if sayfa <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

                try:
                    kod_str = str(int(float(kod_ham))) if str(kod_ham).strip().replace(".", "", 1).isdigit() else str(kod_ham).strip()
                except Exception:
                    kod_str = str(kod_ham).strip()

                isim = hucre_oku(r, isim_col) if isim_col else f"Kitap #{kod_str}"
                renkli_val = tr_kucult(hucre_oku(r, renkli_col)) if renkli_col else ""
                renkli_opsiyon = (renkli_val == "x") or ("partial" in renkli_val) or (renkli_val == "evet")

                satir_kategorileri = []
                for gc in grup_cols:
                    g_val = hucre_oku(r, gc).strip()
                    if g_val and tr_kucult(g_val) not in ("nan", "none", "nat", ""):
                        if g_val not in satir_kategorileri:
                            satir_kategorileri.append(g_val)

                grup_ham = " - ".join(satir_kategorileri) if satir_kategorileri else "Tekil Kitaplar"
                grup_temiz = tr_kucult(grup_ham)

                veri = {
                    "kod": kod_str,
                    "isim": isim,
                    "sayfa": sayfa,
                    "renkli_opsiyon": renkli_opsiyon,
                    "grup": grup_ham,
                    "grup_temiz": grup_temiz,
                }
                self.katalog[kod_str] = veri
                self.kitaplar.append(veri)

                if grup_ham not in self.gruplar:
                    self.gruplar[grup_ham] = []
                self.gruplar[grup_ham].append(kod_str)
                basarili += 1

            wb.close()
            print(f"Katalog yuklendi: {basarili} kitap, {len(self.gruplar)} kategori.")

        except Exception as e:
            print(f"Excel katalog okuma hatasi: {e!a}")
    @staticmethod
    def _kargo_kodu_esleme_anahtari(value):
        """Normalize a shipping code without fuzzy matching other addresses."""
        value=str(value or '').strip()
        if not value:
            return None
        compact=''.join(value.split())
        if compact.isdecimal():
            return ('numeric',compact)
        return ('text',' '.join(value.casefold().split()))

    def ayni_kargo_kodlu_siparisler(self,code):
        """Existing orders with the same code; no new Firebase request."""
        key=self._kargo_kodu_esleme_anahtari(code)
        if key is None:
            return []
        matches=[
            row for row in self.siparisler
            if isinstance(row,dict) and not row.get('deleted_at')
            and self._kargo_kodu_esleme_anahtari(row.get('kod'))==key
        ]
        return sorted(matches,key=lambda row:str(row.get('tarih') or ''),reverse=True)

    def yeni_siparis_olustur(self, alanlar, kitaplar):
        """Katalog sepetini havuza ekler; eski JSON şemasını aynen kullanır."""
        if not str(alanlar.get("kod", "")).strip():
            raise ValueError("Kargo kodu / adres boş olamaz.")
        try:
            ciro = float(str(alanlar.get("ciro", 0)).replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise ValueError("Ciro sayısal olmalı.") from exc
        if not 0 <= ciro < 1_000_000_000:
            raise ValueError("Ciro geçerli aralıkta değil.")
        temiz = self._temiz_kitaplar(kitaplar)
        # ID yazımıyla sipariş kaydını tek dosyada bütünlüklü tutar.
        sid = max([0, self._son_id] + [int(s['id']) for s in self.siparisler if str(s.get('id','')).isdigit()]) + 1
        yeni = {"id": sid, "tarih": datetime.now().astimezone().isoformat(timespec="seconds"),
                "platform": str(alanlar.get("platform", "Manuel"))[:100],
                "kod": str(alanlar["kod"]).strip()[:500], "ciro": ciro,
                "siparis_turu": str(alanlar.get("siparis_turu", ""))[:100],
                "durum": "havuz", "kitaplar": temiz,
                "brut_tutar": float(alanlar.get("brut_tutar",ciro) or 0),
                "alici_adi": str(alanlar.get("alici_adi",""))[:255],
                "telefon": str(alanlar.get("telefon",""))[:20],
                "adres": str(alanlar.get("adres",""))[:512],
                "il": str(alanlar.get("il",""))[:120],
                "ilce": str(alanlar.get("ilce",""))[:120],
                "alici_il_id": str(alanlar.get("alici_il_id",""))[:20],
                "alici_ilce_id": str(alanlar.get("alici_ilce_id",""))[:20]}
        self.siparisler.append(yeni)
        try:
            self.siparisleri_kaydet()
        except Exception:
            self.siparisler.pop()
            raise
        # Sipariş dosyası otoritedir. Sayaç güncellemesi başarısız olsa bile
        # kalıcı siparişi var olmadığı sanıp tekrar oluşturmayız.
        self._son_id = sid
        try:
            self._atomik_json_yaz(self.sayac_dosyasi, {"son_id": sid})
        except OSError:
            pass
        return yeni

    def _temiz_kitaplar(self, kitaplar):
        if not isinstance(kitaplar, list) or not kitaplar:
            raise ValueError("En az bir kitap seçilmeli.")
        total = {}
        for k in kitaplar:
            code = str(k.get('kod','')).strip()
            kind = str(k.get('tur','SB')).upper()
            if code not in self.katalog or kind not in ('SB','RNK'):
                raise ValueError("Kitap kodu veya baskı türü geçersiz.")
            try:
                n, ready, box = (int(k.get(x,0)) for x in ('adet','hazir','koli'))
            except (TypeError, ValueError) as exc:
                raise ValueError("Adet, hazır ve koli sayısal olmalı.") from exc
            if not 1 <= n <= 100000 or not 0 <= box <= ready <= n:
                raise ValueError("Önce hazırla, sonra kolile. Adet 1-100000 aralığında olmalı.")
            key = (code,kind)
            if key not in total:
                total[key] = {'kod':code, 'tur':kind, 'adet':0, 'hazir':0, 'koli':0}
            for name,num in [('adet',n),('hazir',ready),('koli',box)]:
                total[key][name] += num
        return list(total.values())

    def sepeti_oku(self):
        if not os.path.exists(self.sepet_dosyasi):
            return {}
        with open(self.sepet_dosyasi,encoding='utf8') as file:
            cart=json.load(file)
        return cart if isinstance(cart,dict) else {}

    def sepeti_yaz(self, cart):
        if not isinstance(cart,dict):
            raise ValueError('Sepet veri biçimi hatalı.')
        self._atomik_json_yaz(self.sepet_dosyasi,cart)

    def yedek_al(self):
        folder = Path(self.siparis_dosyasi).parent / 'yedekler'
        folder.mkdir(parents=True,exist_ok=True)
        dest=folder/f"alfa_yedek_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        if os.path.exists(self.siparis_dosyasi):
            shutil.copy2(self.siparis_dosyasi,dest)
        else:
            dest.write_text('[]',encoding='utf8')
        return dest
