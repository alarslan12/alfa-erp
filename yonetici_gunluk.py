"""ALFA ERP cloud audit: one category per business action, expandable book details.

Legacy individual book events are grouped in the viewer; future Firebase
bulk progress writes store only a single compact batch entry per order.
This widget never initiates network requests.
"""
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QFrame,QScrollArea,QLineEdit,QComboBox
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
    activities=sorted((x for x in (payload.get('device_activity') or []) if isinstance(x,dict)),
                      key=lambda x:_sort_time(x.get('created_at')))
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
            key=(key_order,str(raw.get('device_id') or source),'progress')
            group=groups.get(key)
            # A rolling 120-second window measured from the first action.
            # Never combine activity across different orders or devices.
            if group is None or _sort_time(stamp)-_sort_time(group['first_stamp'])>120:
                group={'stamp':stamp,'first_stamp':stamp,'icon':'▤',
                       'title':'Kitapların durumu değiştirildi',
                       'detail':'Hazırlama ve kolileme işlemleri',
                       'orders':names,'source':source,'lines':[]}
                groups[key]=group
                entries.append(group)
            group['stamp']=stamp
            group['lines'].extend(
                _timestamp(stamp)+'  ·  '+_progress_line(e)
                for e in events if isinstance(e,dict))
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
            title='Envanter satışı yapıldı';icon='▥';lines=['Ürün satışı kaydedildi']
        elif action=='order_notice_acknowledged':
            title='Sipariş notu onaylandı';icon='✓';lines=['Not / güncelleme okundu']
        elif action in ('shipping_fee','shipping_fee_updated'):
            title='Kargo ücreti güncellendi';icon='₺';lines=['Kargo gideri kaydı']
        elif action in ('return_state','return','return_updated'):
            title='İade durumu değiştirildi';icon='↶';lines=['İade işlemi kaydedildi']
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
        # A timestamp alone is not evidence of a duplicate: do not drop
        # independent historical events merely because they occurred together.
        if entity=='orders' and any(
                row['orders']==_order_name(raw.get('entity_id'),lookup)
                and abs(_sort_time(stamp)-_sort_time(row['stamp']))<1
                and row['title']=='Sipariş kaydedildi'
                and action=='INSERT' for row in entries):
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
        filters=QHBoxLayout()
        self.search=QLineEdit()
        self.search.setPlaceholderText('Sipariş no, bilgisayar, işlem veya tarih…')
        self.search.textChanged.connect(self.render)
        filters.addWidget(self.search,1)
        self.kind_filter=QComboBox()
        self.kind_filter.addItem('Tüm aktiviteler','')
        for name in ('Kitapların durumu değiştirildi','Sipariş durumu değiştirildi',
                     'Sipariş kaydedildi','Sipariş notu onaylandı','Envanter satışı yapıldı',
                     'Kargo ücreti güncellendi','İade durumu değiştirildi'):
            self.kind_filter.addItem(name,name)
        self.kind_filter.currentIndexChanged.connect(self.render)
        filters.addWidget(self.kind_filter)
        root.addLayout(filters)
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

    def render(self,*_):
        if not hasattr(self,'cards') or not hasattr(self,'entries'):
            return
        while self.cards.count():
            item=self.cards.takeAt(0)
            if item.widget():item.widget().deleteLater()
        query=self.search.text().strip().casefold()
        kind=self.kind_filter.currentData()
        rows=[row for row in self.entries if (not kind or row['title']==kind)
              and (not query or query in (
                  row['title']+' '+row['orders']+' '+row['source']+' '+
                  _timestamp(row['stamp'])+' '+' '.join(str(x) for x in row.get('lines',[]))).casefold())]
        self.counter.setText(str(len(rows))+'/'+str(len(self.entries))+' işlem grubu')
        if not rows:
            note=QLabel('Gösterilecek işlem bulunmuyor.')
            note.setObjectName('OwnerMuted')
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note.setMinimumHeight(100)
            self.cards.addWidget(note)
        previous_day=None
        for row in rows[:240]:
            moment=_datetime(row['stamp'])
            day=moment.astimezone().strftime('%d.%m.%Y') if moment else 'Tarihi bilinmeyen'
            if day!=previous_day:
                heading=QLabel(day);heading.setObjectName('OwnerAuditDay')
                self.cards.addWidget(heading)
                previous_day=day
            card=QFrame();card.setObjectName('OwnerAuditCard')
            body=QHBoxLayout(card);body.setContentsMargins(12,8,12,8)
            body.setSpacing(12)
            icon=QLabel(row['icon']);icon.setObjectName('OwnerAuditIcon')
            icon.setProperty('level','major' if row['title'] in (
                'Sipariş kaydedildi','Sipariş durumu değiştirildi','İade durumu değiştirildi') else 'minor')
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(38,38);body.addWidget(icon)
            info=QVBoxLayout();info.setSpacing(4)
            title=QLabel(row['title']);title.setTextFormat(Qt.TextFormat.PlainText)
            title.setObjectName('OwnerAuditTitle')
            title.setWordWrap(True);info.addWidget(title)
            subtitle=QLabel(row['orders']+'  •  '+row['detail'])
            subtitle.setTextFormat(Qt.TextFormat.PlainText)
            subtitle.setObjectName('OwnerBody');subtitle.setWordWrap(True)
            info.addWidget(subtitle)
            stamp=_timestamp(row['stamp'])
            if row.get('first_stamp') and row['first_stamp']!=row['stamp']:
                stamp=_timestamp(row['first_stamp'])+' — '+stamp
            foot=QLabel(stamp+'   ·   '+row['source'])
            foot.setTextFormat(Qt.TextFormat.PlainText)
            foot.setObjectName('OwnerAuditTime');info.addWidget(foot)
            foot.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lines=row.get('lines') or []
            if lines:
                expand=QPushButton('▸  Ayrıntıları göster ('+str(len(lines))+')')
                expand.setObjectName('OwnerAuditExpand')
                expand.setCheckable(True)
                detail=QLabel('\n'.join('•  '+str(line) for line in lines))
                detail.setTextFormat(Qt.TextFormat.PlainText)
                detail.setObjectName('OwnerBody');detail.setWordWrap(True)
                detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                detail.setVisible(False)
                expand.toggled.connect(detail.setVisible)
                expand.toggled.connect(
                    lambda checked,b=expand,n=len(lines):
                    b.setText(('▾  Ayrıntıları gizle' if checked else
                               '▸  Ayrıntıları göster ('+str(n)+')')))
                info.addWidget(expand,0,Qt.AlignmentFlag.AlignLeft)
                info.addWidget(detail)
            body.addLayout(info,1)
            self.cards.addWidget(card)
        self.cards.addStretch()
