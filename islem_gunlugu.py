"""ALFA ERP JSONL denetim izi: eski sipariş dosyası -> yeni kayıt farkları.

Mevcut siparişler için geçmiş üretmez; yalnızca bu sürümden sonraki başarılı
kayıt işlemlerini yazar. Günlük, sipariş JSON'undan ayrı dosyadadır.
"""
from collections import deque
from datetime import datetime
from pathlib import Path
import json
import os
import uuid


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')


def _num(value):
    try: return round(float(value or 0), 2)
    except (TypeError, ValueError): return 0.0


def _items(order):
    return {(str(x.get('kod', '')), str(x.get('tur', 'SB')).upper()): x
            for x in order.get('kitaplar', []) if isinstance(x, dict)}


def compare_orders(before, after):
    """Önemli olaylar ve küçük kitap ilerleme olaylarını ayrı üretir."""
    old = {str(x['id']): x for x in before if isinstance(x, dict) and 'id' in x}
    new = {str(x['id']): x for x in after if isinstance(x, dict) and 'id' in x}
    events = []

    def add(sid, kind, title, detail='', *, micro=False, oldval=None, newval=None, metadata=None):
        events.append({'siparis_id': sid, 'tur': kind, 'baslik': title,
                       'aciklama': detail, 'mikro': micro,
                       'onceki': oldval, 'sonraki': newval,
                       'meta': metadata or {}})

    for sid in sorted(set(old) | set(new), key=lambda s: (not s.isdigit(), int(s) if s.isdigit() else s)):
        a, b = old.get(sid), new.get(sid)
        if a is None:
            add(sid, 'olusturuldu', 'Sipariş oluşturuldu',
                f"#{sid} · {b.get('platform', 'Manuel')} · Havuz",
                newval=b.get('durum', 'havuz'))
            continue
        if b is None:
            add(sid, 'silindi', 'Sipariş kalıcı olarak silindi',
                f"#{sid} · Silinmeden önceki durum: {a.get('durum', 'aktif')}",
                oldval=a.get('durum', 'aktif'),
                metadata={'kitap_satiri': len(a.get('kitaplar', []))})
            continue
        sa, sb = a.get('durum', 'aktif'), b.get('durum', 'aktif')
        if sa != sb:
            labels = {'havuz':'Havuz','aktif':'Aktif','tamamlandi':'Tamamlandı'}
            add(sid, 'durum', 'Sipariş durumu değişti',
                f"{labels.get(sa, sa)} → {labels.get(sb, sb)}",
                oldval=sa, newval=sb)
        if _num(a.get('kargo_ucreti')) != _num(b.get('kargo_ucreti')) or a.get('kargo_turu') != b.get('kargo_turu'):
            add(sid, 'kargo', 'Kargo gideri kaydedildi / güncellendi',
                f"{_num(b.get('kargo_ucreti')):,.2f} TL · {b.get('kargo_turu', 'Diğer')}",
                oldval=_num(a.get('kargo_ucreti')), newval=_num(b.get('kargo_ucreti')))
        if _num(a.get('ciro')) != _num(b.get('ciro')):
            add(sid, 'ciro', 'Sipariş cirosu değişti',
                f"{_num(a.get('ciro')):,.2f} → {_num(b.get('ciro')):,.2f} TL",
                oldval=_num(a.get('ciro')), newval=_num(b.get('ciro')))
        for field, friendly in (('platform','platform'), ('kod','kargo bilgisi'), ('siparis_turu','sipariş türü')):
            if a.get(field) != b.get(field):
                # Kargo kodunu ve açık adres içeriğini loglara çoğaltma.
                add(sid, 'duzenleme', f'Sipariş {friendly} değişti',
                    'Sipariş düzenleme ekranında güncellendi' if field == 'kod' else
                    f"{str(a.get(field,'-'))[:80]} → {str(b.get(field,'-'))[:80]}")
        ai, bi = _items(a), _items(b)
        for key in sorted(set(ai) | set(bi)):
            x, y = ai.get(key), bi.get(key)
            code, variant = key
            if x is None or y is None or int(x.get('adet', 0)) != int(y.get('adet', 0)):
                add(sid, 'kitap', f'Kitap adedi değişti · #{code} {variant}',
                    f"{int(x.get('adet', 0)) if x else 0} → {int(y.get('adet', 0)) if y else 0} adet",
                    oldval=int(x.get('adet', 0)) if x else 0,
                    newval=int(y.get('adet', 0)) if y else 0,
                    metadata={'kod':code, 'baski':variant})
            if x is None or y is None:
                continue
            for field, label in (('hazir','Hazırlandı'), ('koli','Kolilendi')):
                prev, curr = int(x.get(field, 0)), int(y.get(field, 0))
                if prev != curr:
                    action = label if curr > prev else f'{label} geri alındı'
                    add(sid, 'ilerleme', f'{action} · #{code} {variant}',
                        f"{label}: {prev} → {curr}", micro=True, oldval=prev, newval=curr,
                        metadata={'kod':code, 'baski':variant, 'alan':field, 'fark':curr-prev})
    return events


class AuditLog:
    def __init__(self, data_dir):
        self.path = Path(data_dir) / 'alfa_islem_gunlugu.jsonl'
        self.last_error = None

    def record_diff(self, before, after):
        events = compare_orders(before, after)
        if not events:
            return 0
        timestamp = now_iso()
        user = os.getenv('ALFA_ERP_OPERATOR') or os.getenv('USERNAME') or os.getenv('USER') or 'Yerel kullanıcı'
        device = os.getenv('COMPUTERNAME') or os.getenv('HOSTNAME') or 'Bu cihaz'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open('a', encoding='utf-8', newline='\n') as handle:
                for event in events:
                    record = {'olay_id': str(uuid.uuid4()), 'zaman':timestamp,
                              'kullanici':user[:100], 'cihaz':device[:100], **event}
                    handle.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            self.last_error = None
        except OSError as exc:
            # Sipariş kaydı zaten başarıyla yazılmıştır; asla yanlış rollback yapma.
            self.last_error = str(exc)
        return len(events)

    def record_action(self,kind,title,detail='',metadata=None):
        """Sipariş dışındaki kritik muhasebe durum değişikliklerini kaydet."""
        event = {
            'olay_id':str(uuid.uuid4()), 'zaman':now_iso(),
            'kullanici':(os.getenv('ALFA_ERP_OPERATOR') or os.getenv('USERNAME') or
                        os.getenv('USER') or 'Yerel kullanıcı')[:100],
            'cihaz':(os.getenv('COMPUTERNAME') or os.getenv('HOSTNAME') or 'Bu cihaz')[:100],
            'siparis_id':'Muhasebe', 'tur':str(kind), 'baslik':str(title),
            'aciklama':str(detail), 'mikro':False, 'onceki':None,
            'sonraki':None, 'meta':metadata or {},
        }
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with self.path.open('a',encoding='utf-8',newline='\n') as handle:
                handle.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')
                handle.flush();os.fsync(handle.fileno())
            self.last_error=None
        except OSError as exc:
            self.last_error=str(exc)

    def read(self, limit=5000):
        if not self.path.is_file():
            return []
        with self.path.open('r', encoding='utf-8') as handle:
            lines = deque(handle, maxlen=limit)
        result = []
        for line in lines:
            try:
                item = json.loads(line)
                if isinstance(item, dict) and 'tur' in item:
                    result.append(item)
            except (ValueError, TypeError):
                continue
        return list(reversed(result))


def group_events(entries, window_seconds=120):
    """Birkaç dakika içindeki aynı siparişe ait küçük ilerlemeleri tek kartta göster."""
    result = []
    block = None
    for item in entries:
        if not item.get('mikro'):
            block = None
            result.append({'main':item, 'children':[]})
            continue
        when = datetime.fromisoformat(item['zaman'])
        if (block and block['main']['siparis_id'] == item['siparis_id'] and
                abs((datetime.fromisoformat(block['main']['zaman']) - when).total_seconds()) <= window_seconds):
            block['children'].append(item)
        else:
            block = {'main': {**item, 'baslik':'Kitap hazırlama / kolileme hareketleri'}, 'children':[item]}
            result.append(block)
    return result
