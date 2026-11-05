"""ALFA ERP cloud audit: one category per business action, expandable book details.

Legacy individual book events are grouped in the viewer; future Firebase
bulk progress writes store only a single compact batch entry per order.
This widget never initiates network requests.
"""
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QFrame,QScrollArea
)


def _datetime(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except (ValueError,TypeError,OverflowError):
        return None


def _timestamp(value):
    d=_datetime(value)
    return d.astimezone().strftime('%d.%m.%Y  %H:%M:%S') if d else str(value or '—')[:19]


def _sort_time(value):
    d=_datetime(value)
    return d.timestamp() if d else 0.0


def _order_name(value,lookup):
    number=lookup.get(str(value))
    return '#'+str(number) if number else 'Sipariş '+str(value or '')[:8]


def _progress_line(event):
    code=str(event.get('book_code') or '')
    kind=str(event.get('print_type') or '')
    dr=int(event.get('delta_ready') or 0)
    dk=int(event.get('delta_boxed') or 0)
    changes=[]
    if dr:changes.append(('Hazırlandı ' if dr>0 else 'Hazırlama geri alındı ')+str(abs(dr)))
    if dk:changes.append(('Kolilendi ' if dk>0 else 'Kolileme geri alındı ')+str(abs(dk)))
    return '#'+code+' '+kind+' · '+(', '.join(changes) if changes else 'Durum güncellendi')


def make_audit_entries(payload,orders):
    """Group per-book progress into a single expandable business action."""
    lookup={str(o.get('bulut_id')):o.get('bulut_siparis_no') or o.get('id')
            for o in orders if isinstance(o,dict) and o.get('bulut_id')}
    entries=[]
    groups={}
    activities=payload.get('device_activity') or []
    for raw in activities:
        if not isinstance(raw,dict):continue
        action=str(raw.get('action') or '')
        stamp=str(raw.get('created_at') or '')
        source=str(raw.get('device_name') or 'Bilinmeyen bilgisayar')
        ids=raw.get('order_ids') or []
        key_order=str(ids[0]) if ids else ''
        names=', '.join(_order_name(x,lookup) for x in ids[:3]) or 'Genel işlem'
        details=raw.get('details') or {}
        events=details.get('events') if isinstance(details,dict) else []
        events=events if isinstance(events,list) else []
        if action in ('progress','progress_bulk'):
            # Group older single-book events into one display-only block when
            # they share the same order, device and short update window.
            bucket=int(_sort_time(stamp)//12)
            key=(key_order,source,bucket,'progress')
            if key not in groups:
                entry={'stamp':stamp,'icon':'✓',
                       'title':'Kitapların durumu değiştirildi',
                       'detail':'Hazırlama ve kolileme işlemleri',
                       'orders':names,'source':source,'lines':[]}
                groups[key]=entry
                entries.append(entry)
            group=groups[key]
            if _sort_time(stamp)>_sort_time(group['stamp']):
                group['stamp']=stamp
            group['lines'].extend(_progress_line(e) for e in events if isinstance(e,dict))
            continue
        if action=='transition':
            labels={'havuz':'Havuz','aktif':'Aktif','tamamlandi':'Tamamlandı'}
            lines=[labels.get(str(e.get('from_status') or ''),'—')+' → '+
                   labels.get(str(e.get('to_status') or ''),'—')
                   for e in events if isinstance(e,dict)]
            title='Sipariş durumu değiştirildi'
            icon='➜'
        elif action=='commit':
            title='Sipariş kaydedildi';icon='＋';lines=['Sipariş oluşturuldu veya düzenlendi']
        elif action=='inventory_sale':
            title='Envanter satışı yapıldı';icon='◆';lines=['Ürün satışı kaydedildi']
        else:
            title='Diğer işlem';icon='•';lines=[action or 'İşlem kaydı']
        entries.append({'stamp':stamp,'icon':icon,'title':title,
                        'detail':'İşlem ayrıntıları','orders':names,
                        'source':source,'lines':lines})

    # Preserve meaningful historical business audit after migration without
    # flooding the screen with SQL trigger rows for each book.
    for raw in payload.get('audit_events') or []:
        if not isinstance(raw,dict):continue
        entity=str(raw.get('entity_name') or '')
        action=str(raw.get('action') or '')
        if entity not in ('orders','accounting_days'):continue
        stamp=str(raw.get('created_at') or '')
        # Prefer Firebase event log when it describes this recent action.
        if any(abs(_sort_time(stamp)-_sort_time(row['stamp']))<8
               for row in entries):
            continue
        changes=raw.get('changed_fields') or []
        if entity=='orders':
            title=('Sipariş oluşturuldu' if action=='INSERT' else
                   'Sipariş silindi' if action=='DELETE' else
                   'Sipariş bilgileri değiştirildi')
            detail=', '.join(str(x) for x in changes) or 'Sipariş güncellendi'
            names=_order_name(raw.get('entity_id'),lookup)
        else:
            title='Muhasebe durumu değiştirildi';detail='Ödeme bilgisi güncellendi'
            names='Muhasebe'
        entries.append({'stamp':stamp,'icon':'•','title':title,
                        'detail':'Geçmiş bulut işlemi','orders':names,
                        'source':'Bulut işlem kaydı','lines':[detail]})

    for row in entries:
        count=len(row['lines'])
        if row['title']=='Kitapların durumu değiştirildi':
            row['detail']=str(count)+' kitap hareketi · ayrıntılar açılabilir'
    entries.sort(key=lambda row:_sort_time(row['stamp']),reverse=True)
    return entries[:240]


class AuditFeed(QWidget):
    """Compact cards. Expand detail only when requested, without extra reads."""
    def __init__(self,parent=None):
        super().__init__(parent)
        root=QVBoxLayout(self);root.setContentsMargins(0,2,0,0);root.setSpacing(10)
        head=QHBoxLayout()
        title=QLabel('İŞLEM GÜNLÜĞÜ');title.setObjectName('OwnerHeading')
        head.addWidget(title);head.addStretch()
        self.counter=QLabel('Henüz yüklenmedi');self.counter.setObjectName('OwnerMuted')
        head.addWidget(self.counter);root.addLayout(head)
        hint=QLabel('Tek bir işlem başlığına tıklayarak kitap bazındaki ayrıntıları görebilirsin.')
        hint.setObjectName('OwnerMuted');hint.setWordWrap(True);root.addWidget(hint)
        self.scroll=QScrollArea();self.scroll.setObjectName('OwnerAuditScroll')
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        host=QWidget();host.setObjectName('OwnerAuditHost')
        self.cards=QVBoxLayout(host);self.cards.setSpacing(8)
        self.cards.setContentsMargins(2,2,8,12)
        self.scroll.setWidget(host);root.addWidget(self.scroll,1)
        self.entries=[]
        self.render()

    def set_entries(self,payload,orders):
        self.entries=make_audit_entries(payload,orders)
        self.render()

    def render(self):
        while self.cards.count():
            item=self.cards.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.counter.setText(str(len(self.entries))+' işlem grubu')
        if not self.entries:
            note=QLabel('Gösterilecek işlem bulunmuyor.')
            note.setObjectName('OwnerMuted')
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note.setMinimumHeight(100)
            self.cards.addWidget(note)
        for row in self.entries[:150]:
            card=QFrame();card.setObjectName('OwnerAuditCard')
            body=QHBoxLayout(card);body.setContentsMargins(15,13,15,13)
            body.setSpacing(12)
            icon=QLabel(row['icon']);icon.setObjectName('OwnerAuditIcon')
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(38,38);body.addWidget(icon)
            info=QVBoxLayout();info.setSpacing(6)
            title=QLabel(row['title']);title.setObjectName('OwnerAuditTitle')
            title.setWordWrap(True);info.addWidget(title)
            subtitle=QLabel(row['orders']+'  •  '+row['detail'])
            subtitle.setObjectName('OwnerBody');subtitle.setWordWrap(True)
            info.addWidget(subtitle)
            foot=QLabel(_timestamp(row['stamp'])+'   ·   '+row['source'])
            foot.setObjectName('OwnerMuted');info.addWidget(foot)
            lines=row.get('lines') or []
            if lines:
                expand=QPushButton('▸  Ayrıntıları göster ('+str(len(lines))+')')
                expand.setObjectName('OwnerAuditExpand')
                expand.setCheckable(True)
                detail=QLabel('\n'.join('•  '+str(line) for line in lines))
                detail.setObjectName('OwnerBody');detail.setWordWrap(True)
                detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                detail.setVisible(False)
                expand.toggled.connect(detail.setVisible)
                expand.toggled.connect(
                    lambda checked,b=expand,n=len(lines):
                    b.setText(('▾  Ayrıntıları gizle' if checked else
                               '▸  Ayrıntıları göster ('+str(n)+')')))
                info.addWidget(expand);info.addWidget(detail)
            body.addLayout(info,1)
            self.cards.addWidget(card)
        self.cards.addStretch()
