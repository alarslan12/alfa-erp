"""ALFA ERP Qt kitap kataloğu: 4 sütun, filtre, toplu işlem ve canlı sepet."""
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFrame,QGridLayout,QLineEdit,QComboBox,QSpinBox,
 QScrollArea,QLabel,QCheckBox,QDialog,QFormLayout,QDoubleSpinBox,QFileDialog,QMessageBox,QSizePolicy,QButtonGroup,QPushButton,QGraphicsOpacityEffect,QApplication)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent, QPropertyAnimation, QRect, QEasingCurve
from utils import metin_eslesiyor_mu, otomatik_platform_bul,format_kargo_kodu
from datetime import datetime
from PySide6.QtGui import QDoubleValidator
from widgets import cover_label, text,button,panel,clear_layout,scrollable,error,confirm

PAGE_SIZE=48

class FloatingPrice(QWidget):
    """Boş başlangıçlı, odaklanınca yukarı kayan fiyat etiketi."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('FloatingPrice')
        self.setFixedHeight(49)
        self.edit=QLineEdit(self)
        self.edit.setObjectName('FloatingPriceInput')
        self.edit.setValidator(QDoubleValidator(0.0,999999999.0,2,self))
        self.edit.setPlaceholderText('')
        self.label=QLabel('Fiyat (TL)',self)
        self.label.setObjectName('FloatingPriceLabel')
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.edit.installEventFilter(self)
        self.edit.textChanged.connect(self._refresh)
        self._raised=False
        self._animation=QPropertyAnimation(self.label,b'geometry',self)
        self._animation.setDuration(155)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._refresh(animate=False)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.edit.setGeometry(0,0,self.width(),self.height())
        self._refresh(animate=False)
    def eventFilter(self,obj,event):
        if obj is self.edit and event.type() in (QEvent.Type.FocusIn,QEvent.Type.FocusOut):
            QTimer.singleShot(0,self._refresh)
        return super().eventFilter(obj,event)
    def _refresh(self,*args,animate=True):
        raised=self.edit.hasFocus() or bool(self.edit.text().strip())
        rect=QRect(12,3 if raised else 13,max(90,self.width()-24),16 if raised else 22)
        self.label.setProperty('raised',raised)
        light = bool(QApplication.instance() and QApplication.instance().property('alfa_theme') == 'acik')
        active_color = '#b6844c' if light else '#f1b46f'
        idle_color = '#7f7b72' if light else '#8c99ac'
        self.label.setStyleSheet(f'color:{active_color};font-size:10px;' if raised else f'color:{idle_color};font-size:12px;')
        if not animate or self._raised==raised:
            self._animation.stop();self.label.setGeometry(rect)
        else:
            self._animation.stop();self._animation.setStartValue(self.label.geometry())
            self._animation.setEndValue(rect);self._animation.start()
        self._raised=raised
    def value(self):
        raw=self.edit.text().strip().replace(' ','').replace(',','.')
        try:return max(0.0,float(raw)) if raw else 0.0
        except ValueError:return 0.0
    def setValue(self,value):
        self.edit.setText('' if not value else str(value).replace('.',','))
    def clear(self):self.edit.clear()

class KitapKarti(QWidget):
    """Dikey kapak ve kapağa sıfır boşlukla bitişen çift sayaç."""
    COVER_W = 174
    COVER_H = 245

    def __init__(self,book,covers,cart,on_quantity):
        super().__init__()
        self.book=book
        self._quantity_controls={}
        self.setObjectName('StandaloneBook')
        self.setFixedWidth(180)
        self.setFixedHeight(313)
        v=QVBoxLayout(self)
        v.setContentsMargins(3,0,3,0)
        v.setSpacing(0)

        # Kitap başlığı ve sayfa bilgisi: kapakla aynı genişlikte, köşeli tek başlık bandı.
        header=QWidget()
        header.setObjectName('StandaloneHeader')
        header.setFixedSize(self.COVER_W,40)
        header_l=QVBoxLayout(header)
        header_l.setContentsMargins(3,1,3,1)
        header_l.setSpacing(0)
        name=QLabel(book['isim'])
        name.setObjectName('StandaloneName')
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        # 26px reserves two readable lines, without a tall empty heading.
        name.setFixedHeight(26)
        name.setToolTip(f"[{book['kod']}] {book['isim']}")
        header_l.addWidget(name)
        pages=QLabel(f"#{book['kod']} · {book['sayfa']} sayfa")
        pages.setObjectName('StandalonePages')
        pages.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pages.setFixedHeight(12)
        header_l.addWidget(pages)
        v.addWidget(header,0,Qt.AlignmentFlag.AlignHCenter)

        # Kapak: dış kart, fon veya dekoratif çerçeve bulunmaz.
        # Kapak ve sayaç aynı dikey blokta, aralarında sıfır piksel boşlukla durur.
        media=QWidget()
        media.setObjectName('StandaloneMedia')
        media.setFixedWidth(self.COVER_W)
        media_l=QVBoxLayout(media)
        media_l.setContentsMargins(0,0,0,0)
        media_l.setSpacing(0)
        cover=cover_label(book,covers,self.COVER_W,self.COVER_H)
        cover.setObjectName('StandaloneCover')
        light = bool(QApplication.instance() and QApplication.instance().property('alfa_theme') == 'acik')
        edge = '#ccb9a1' if light else '#45546a'
        cover.setStyleSheet(f'QLabel#StandaloneCover {{ background: transparent; border-left: 1px solid {edge}; border-right: 1px solid {edge}; border-bottom: 1px solid {edge}; border-top: 0; border-radius: 0; padding: 0; }}')
        media_l.addWidget(cover)

        quantities=QWidget()
        quantities.setObjectName('StandaloneQuantities')
        quantities.setFixedSize(self.COVER_W,27)
        quantities_l=QHBoxLayout(quantities)
        quantities_l.setContentsMargins(0,0,0,0)
        quantities_l.setSpacing(0)
        for kind in ('SB','RNK'):
            # SB and RNK meet flush: no visible white divider.
            strip=QWidget()
            strip.setObjectName('StandaloneCounterSB' if kind=='SB' else 'StandaloneCounterRNK')
            strip.setFixedSize((self.COVER_W-2)//2,27)
            row=QHBoxLayout(strip)
            row.setContentsMargins(0,0,0,0)
            row.setSpacing(0)
            tag=QLabel(kind)
            tag.setObjectName('StandaloneSB' if kind=='SB' else 'StandaloneRNK')
            tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag.setFixedWidth(20)
            minus=QPushButton('−')
            minus.setObjectName('StandaloneStep')
            minus.setFixedSize(20,27)
            count=QLabel(str(int(cart.get(str(book['kod']),{}).get(kind,0))))
            count.setObjectName('StandaloneCount')
            count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count.setMinimumWidth(25)
            plus=QPushButton('+')
            plus.setObjectName('StandaloneStep')
            plus.setFixedSize(20,27)
            row.addWidget(tag)
            row.addWidget(minus)
            row.addWidget(count)
            row.addWidget(plus)
            state={'value':int(cart.get(str(book['kod']),{}).get(kind,0))}
            self._quantity_controls[kind]=(state,count)
            def step(delta,st=state,label=count,k=kind):
                st['value']=max(0,min(99999,st['value']+delta))
                label.setText(str(st['value']))
                on_quantity(str(book['kod']),k,st['value'])
            minus.clicked.connect(lambda _=False,f=step:f(-1))
            plus.clicked.connect(lambda _=False,f=step:f(1))
            if kind=='RNK' and book.get('renkli_opsiyon') is False:
                minus.setEnabled(False)
                plus.setEnabled(False)
            quantities_l.addWidget(strip)
        media_l.addWidget(quantities)
        v.addWidget(media,0,Qt.AlignmentFlag.AlignHCenter)
        v.addStretch(1)

    def set_display_quantity(self,kind,value):
        state,label=self._quantity_controls[kind]
        state['value']=int(value)
        label.setText(str(value))

def _ask_before_duplicate_shipping_code(parent,db,code):
    """Explicit warning for duplicate tracking/shipping codes, no new API call."""
    matches=db.ayni_kargo_kodlu_siparisler(code)
    if not matches:return True
    statuses={'havuz':'Havuzda','aktif':'Aktif / hazırlanıyor',
              'tamamlandi':'Tamamlandı'}
    details=[]
    for previous in matches:
        stamp=str(previous.get('tarih') or '')
        try:stamp=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone().strftime('%d.%m.%Y %H:%M')
        except (ValueError,TypeError,OverflowError):stamp=stamp[:19] or 'Tarih bilinmiyor'
        status=statuses.get(db.siparis_durumu(previous),'Bilinmiyor')
        number=str(previous.get('bulut_siparis_no') or previous.get('id') or '?')
        details.append(f"#{number}  ·  {stamp}  ·  {status}")
    notice=QMessageBox(parent)
    notice.setIcon(QMessageBox.Icon.Warning)
    notice.setWindowTitle('Kargo kodu daha önce kullanılmış')
    notice.setText(f'{code} koduyla daha önce {len(matches)} sipariş oluşturulmuş.')
    lines='\n'.join(details[:7])
    if len(details)>7:
        lines+=f'\n… ve {len(details)-7} diğer sipariş'
        notice.setDetailedText('\n'.join(details))
    notice.setInformativeText(
        'Önceki siparişler:\n'+lines+
        '\n\nBu kodla bir sipariş daha oluşturmak istiyor musun?')
    accept=notice.addButton('Yine de oluştur',QMessageBox.ButtonRole.AcceptRole)
    cancel=notice.addButton('Vazgeç',QMessageBox.ButtonRole.RejectRole)
    notice.setDefaultButton(cancel)
    notice.exec()
    return notice.clickedButton() is accept


class SiparisBilgiDialog(QDialog):
    def __init__(self,db,cart,parent=None):
        super().__init__(parent);self.db=db;self.cart=cart;self.setWindowTitle('Siparişi havuza ekle');self.setMinimumWidth(430)
        lay=QVBoxLayout(self);lay.setSpacing(12);lay.setContentsMargins(20,18,20,20)
        lay.addWidget(text('Yeni sipariş','PageTitle'))
        form=QFormLayout();form.setSpacing(10)
        self.shipping=QLineEdit();self.shipping.setPlaceholderText('Kargo kodu veya açık adres');self.shipping.textChanged.connect(self.auto_platform)
        self.platform_value='Dolap'
        self.revenue=QDoubleSpinBox();self.revenue.setDecimals(2);self.revenue.setMaximum(999999999);self.revenue.setSuffix(' TL')
        self.order_type=QComboBox();self.order_type.addItems(['Normal Sipariş','Özel Sipariş','Toplu Sipariş'])
        form.addRow('Kargo kodu / adres',self.shipping)
        form.addRow('Ciro',self.revenue);form.addRow('Sipariş türü',self.order_type)
        lay.addLayout(form)
        item_count=sum(int(q) for variants in cart.values() for q in variants.values())
        lay.addWidget(text(f'{item_count} adet kitap havuza kaydedilecek.','Muted'))
        row=QHBoxLayout();row.addStretch();cancel=button('Vazgeç');submit=button('Havuza kaydet','Accent')
        cancel.clicked.connect(self.reject);submit.clicked.connect(self.commit);row.addWidget(cancel);row.addWidget(submit);lay.addLayout(row)
    def auto_platform(self,value):
        platform=otomatik_platform_bul(value)
        self.platform_value=platform
    def commit(self):
        items=[]
        for code,variants in self.cart.items():
            for kind in ('SB','RNK'):
                amount=int(variants.get(kind,0))
                if amount>0:items.append({'kod':code,'tur':kind,'adet':amount,'hazir':0,'koli':0})
        code=format_kargo_kodu(self.shipping.text(),self.platform_value)
        if code and not _ask_before_duplicate_shipping_code(self,self.db,code):
            return
        try:
            self.db.yeni_siparis_olustur({'kod':code,'platform':self.platform_value,
                'ciro':self.revenue.value(),'siparis_turu':self.order_type.currentText()},items)
        except Exception as exc:return error(self,str(exc))
        self.accept()

class KatalogView(QWidget):
    order_created = Signal()
    def __init__(self,db,covers):
        super().__init__();self.db=db;self.covers=covers
        raw=db.sepeti_oku();self.cart={str(k):{'SB':max(0,int(v.get('SB',0))), 'RNK':max(0,int(v.get('RNK',0)))} for k,v in raw.items() if isinstance(v,dict) and str(k) in db.katalog}
        self.page=0;self.last_filter=[];self._last_columns=0
        self._cart_timer=QTimer(self);self._cart_timer.setSingleShot(True)
        self._cart_timer.setInterval(45)
        self._cart_timer.timeout.connect(self.update_cart)
        root=QHBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        main=QWidget();main_v=QVBoxLayout(main);main_v.setContentsMargins(0,0,0,0);main_v.setSpacing(9)
        toolbar=QWidget();toolbar.setObjectName('CatalogToolbar');self.toolbar=toolbar;tool=QHBoxLayout(toolbar);tool.setContentsMargins(0,0,0,0);tool.setSpacing(0)
        first=QHBoxLayout();first.setSpacing(7)
        self.search=QLineEdit();self.search.setPlaceholderText('⌕  Kitap adı, alt kategori (ÇTS, TTS vb.) veya kod ile arayın...')
        self._search_timer=QTimer(self);self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(220)
        self._search_timer.timeout.connect(self.reset_results)
        self.search.textChanged.connect(lambda _value:self._search_timer.start())
        self.search.setMinimumWidth(180);first.addWidget(self.search,1)
        add_sb=button('＋ SB Ekle');add_sb.setObjectName('QuickSB');add_rnk=button('＋ RNK Ekle');add_rnk.setObjectName('QuickRNK')
        sub_sb=button('− SB Çıkar');sub_rnk=button('− RNK Çıkar')
        add_sb.clicked.connect(lambda:self.bulk('SB',1));add_rnk.clicked.connect(lambda:self.bulk('RNK',1))
        sub_sb.clicked.connect(lambda:self.bulk('SB',-1));sub_rnk.clicked.connect(lambda:self.bulk('RNK',-1))
        for b in (add_sb,sub_sb,add_rnk,sub_rnk):first.addWidget(b)
        self.result_label=text('303 kitap','Muted')
        first.addWidget(self.result_label)
        tool.addLayout(first)
        self.cards=QWidget();self.grid=QGridLayout(self.cards);self.grid.setHorizontalSpacing(2);self.grid.setVerticalSpacing(5);self.grid.setContentsMargins(0,0,3,4)
        self.scroller=scrollable(self.cards);main_v.addWidget(self.scroller,1)
        paginator=QHBoxLayout();paginator.addStretch();self.page_text=text('1 / 1','Muted')
        self.prev=button('‹ Önceki');self.next=button('Sonraki ›')
        self.prev.clicked.connect(lambda:self.change_page(-1));self.next.clicked.connect(lambda:self.change_page(1))
        for w in (self.prev,self.page_text,self.next):paginator.addWidget(w)
        main_v.addLayout(paginator);root.addWidget(main,1)
        self.side=panel();self.side.setObjectName('BasketPanel');self.side.setFixedWidth(280)
        side_l=QVBoxLayout(self.side);side_l.setContentsMargins(8,8,8,8);side_l.setSpacing(6)
        h=QHBoxLayout();h.addWidget(text('Sepet','Title'));h.addStretch()
        clear=button('▤  Hepsini Kaldır');clear.setObjectName('DangerText')
        clear.clicked.connect(self.clear_cart);h.addWidget(clear);side_l.addLayout(h)
        self.cart_body=QWidget();self.cart_layout=QVBoxLayout(self.cart_body)
        self.cart_layout.setContentsMargins(0,0,3,0);self.cart_layout.setSpacing(7)
        side_l.addWidget(scrollable(self.cart_body),1)
        totals=QFrame();totals.setObjectName('BasketTotals');tot_l=QVBoxLayout(totals)
        tot_l.setContentsMargins(6,7,6,7);tot_l.setSpacing(2)
        self.cart_count=text('0 adet','Title');self.cart_pages=text('0 sayfa','Muted')
        tot_l.addWidget(self.cart_count);tot_l.addWidget(self.cart_pages);side_l.addWidget(totals)
        types=QHBoxLayout();types.setSpacing(5)
        self.normal_btn=button('Normal Sipariş');self.normal_btn.setCheckable(True);self.normal_btn.setChecked(True)
        self.special_btn=button('TELAFİ SİPARİŞ');self.special_btn.setCheckable(True)
        self.type_group=QButtonGroup(self);self.type_group.setExclusive(True)
        self.type_group.addButton(self.normal_btn);self.type_group.addButton(self.special_btn)
        self.normal_btn.setObjectName('OrderType');self.special_btn.setObjectName('OrderType')
        types.addWidget(self.normal_btn);types.addWidget(self.special_btn);side_l.addLayout(types)
        self.shipping=QLineEdit();self.shipping.setPlaceholderText('📦  Kargo Kodu veya Açık Adres')
        self.shipping.textChanged.connect(self.auto_platform)
        self._shipping_formatting=False
        side_l.addWidget(self.shipping)
        self.platform_value='Dolap'
        self.platform_hint=text('Platform: Dolap (otomatik)','Muted');side_l.addWidget(self.platform_hint)
        self.revenue=FloatingPrice();side_l.addWidget(self.revenue)
        self.order_btn=button('🚀  Siparişi Sisteme Kaydet','Success')
        self.order_btn.clicked.connect(self.make_order);side_l.addWidget(self.order_btn)
        root.addWidget(self.side)
        self.reset_results();self.update_cart()

    def filtered(self):
        q=self.search.text()
        rows=[book for book in self.db.kitaplar if metin_eslesiyor_mu(q,book)]
        # Both the initial Excel and Firebase-origin catalog use stable
        # numerical order; data/code values are not rewritten.
        def book_key(book):
            code=str(book.get('kod') or '').strip()
            return (0,int(code),code) if code.isdecimal() else (1,code.casefold(),code)
        return sorted(rows,key=book_key)
    def reset_results(self,*args):self.page=0;self.refresh_grid()
    def _column_count(self):
        # Görünür katalog genişliğini kullan; tüm pencere genişliğini değil.
        available=max(400,self.scroller.viewport().width()-12)
        return max(2,min(6,available//184))
    def refresh_grid(self):
        clear_layout(self.grid);self.last_filter=self.filtered();n=len(self.last_filter)
        pages=max(1,(n+PAGE_SIZE-1)//PAGE_SIZE);self.page=min(self.page,pages-1)
        shown=self.last_filter[self.page*PAGE_SIZE:(self.page+1)*PAGE_SIZE]
        columns=self._column_count()
        self._visible_cards=[]
        for i,book in enumerate(shown):
            card=KitapKarti(book,self.covers,self.cart,self.set_qty)
            self.grid.addWidget(card,i//columns,i%columns)
            self._visible_cards.append(card)
        for col in range(9):self.grid.setColumnStretch(col,1 if col<columns else 0)
        self.grid.setRowStretch((len(shown)+columns-1)//columns,1)
        self.result_label.setText(f'{n} sonuç');self.page_text.setText(f'{self.page+1} / {pages}')
        self.prev.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'scroller'):
            columns=self._column_count()
            if self._last_columns!=columns:
                self._last_columns=columns
                QTimer.singleShot(0,self.refresh_grid)
    def change_page(self,d):self.page+=d;self.refresh_grid();self.scroller.verticalScrollBar().setValue(0)
    def set_qty(self,code,kind,value):
        qty=self.cart.setdefault(code,{'SB':0,'RNK':0});qty[kind]=int(value)
        if not (qty['SB'] or qty['RNK']):self.cart.pop(code,None)
        self.db.sepeti_yaz(self.cart);self._cart_timer.start()
    def bulk(self,kind,sign):
        # Arama ve grup filtresine uyan TÜM kitaplar; yalnızca o anki 30 kart değil.
        # Hiç filtre yoksa 303 kitabın tamamı hedeflenir.
        targets=self.filtered()
        if not targets:return
        changed=0
        for book in targets:
            code=str(book['kod'])
            if kind=='RNK' and book.get('renkli_opsiyon') is False:continue
            q=self.cart.setdefault(code,{'SB':0,'RNK':0})
            q[kind]=max(0,min(99999,int(q.get(kind,0))+sign))
            if not q['SB'] and not q['RNK']:self.cart.pop(code,None)
            changed+=1
        if not changed:return error(self,'Bu kitaplarda seçilen baskı türü bulunmuyor.')
        self.db.sepeti_yaz(self.cart);self._cart_timer.start();self.refresh_grid()
    def update_cart(self):
        clear_layout(self.cart_layout)
        total=pages=0;groups={}
        for code,variant in self.cart.items():
            book=self.db.katalog.get(code)
            if not book:continue
            qty=int(variant.get('SB',0))+int(variant.get('RNK',0))
            if not qty:continue
            total+=qty;pages+=qty*int(book['sayfa'])
            subgroup=str(book.get('alt_grup') or book.get('alt_kategori') or book.get('grup') or 'Diğer')
            groups.setdefault(subgroup,[]).append((code,book,variant))
        for subgroup,entries in groups.items():
            frame=QFrame();frame.setObjectName('BasketGroup');block=QVBoxLayout(frame)
            block.setContentsMargins(2,4,2,4);block.setSpacing(3)
            title=QLabel('▣  '+subgroup);title.setObjectName('BasketGroupTitle');title.setWordWrap(True)
            block.addWidget(title)
            for code,book,variant in entries:
                item=QFrame();item.setObjectName('BasketRow');row=QHBoxLayout(item)
                row.setSpacing(5);row.setContentsMargins(3,3,3,3)
                row.addWidget(cover_label(book,self.covers,30,40))
                body=QVBoxLayout();body.setSpacing(1)
                name=QLabel(f"[{code}] {book['isim']}");name.setWordWrap(True)
                name.setMaximumHeight(33);name.setStyleSheet('font-size:11px;font-weight:700;')
                body.addWidget(name)
                controls=QHBoxLayout();controls.setSpacing(4)
                for kind in ('SB','RNK'):
                    q=int(variant.get(kind,0))
                    if q<=0:continue
                    pill=QWidget();pill.setObjectName('BasketPillSB' if kind=='SB' else 'BasketPillRNK')
                    pill_row=QHBoxLayout(pill);pill_row.setContentsMargins(3,0,3,0);pill_row.setSpacing(2)
                    label=QLabel(kind);label.setObjectName('BasketPillText')
                    minus=QPushButton('−');minus.setObjectName('BasketPillStep');minus.setFixedSize(17,19)
                    amount=QLabel(str(q));amount.setObjectName('BasketPillCount');amount.setAlignment(Qt.AlignmentFlag.AlignCenter);amount.setMinimumWidth(16)
                    plus=QPushButton('+');plus.setObjectName('BasketPillStep');plus.setFixedSize(17,19)
                    minus.clicked.connect(lambda _=False,c=code,k=kind:self.adjust_cart(c,k,-1))
                    plus.clicked.connect(lambda _=False,c=code,k=kind:self.adjust_cart(c,k,1))
                    for widget in (label,minus,amount,plus):pill_row.addWidget(widget)
                    controls.addWidget(pill)
                controls.addStretch()
                body.addLayout(controls)
                row.addLayout(body,1)
                block.addWidget(item)
            self.cart_layout.addWidget(frame)
        if not total:self.cart_layout.addWidget(text('Sepet boş. Katalogdan kitap ekleyin.','Muted',True))
        self.cart_layout.addStretch()
        self.cart_count.setText(f'📌  {len(self.cart)} Çeşit ({total} Kitap)')
        self.cart_pages.setText(f'Toplam: {pages:,} Sayfa')
        self.order_btn.setEnabled(total>0)
    def auto_platform(self,value):
        if self._shipping_formatting:
            return
        formatted=format_kargo_kodu(value)
        if formatted != value:
            old_cursor=self.shipping.cursorPosition()
            digits_before=sum(c.isdigit() for c in value[:old_cursor])
            self._shipping_formatting=True
            try:
                self.shipping.setText(formatted)
                if formatted.replace(' ', '').isdigit():
                    position=0;seen=0
                    while position<len(formatted) and seen<digits_before:
                        if formatted[position].isdigit():seen+=1
                        position+=1
                    self.shipping.setCursorPosition(position)
                else:
                    self.shipping.setCursorPosition(min(old_cursor,len(formatted)))
            finally:
                self._shipping_formatting=False
        platform=otomatik_platform_bul(formatted)
        self.platform_value=platform
        self.platform_hint.setText(f'Platform: {platform} (otomatik)')
    def adjust_cart(self,code,kind,delta):
        values=self.cart.get(str(code))
        if not values:return
        values[kind]=max(0,min(99999,int(values.get(kind,0))+delta))
        if not (values.get('SB',0) or values.get('RNK',0)):
            self.cart.pop(str(code),None)
        self.db.sepeti_yaz(self.cart)
        self._cart_timer.start()
        self._sync_visible_quantity(code,kind)
    def _sync_visible_quantity(self,code,kind):
        for card in getattr(self,'_visible_cards',[]):
            if str(card.book['kod'])==str(code):
                card.set_display_quantity(kind,self.cart.get(str(code),{}).get(kind,0))
    def remove_cart(self,code):
        self.cart.pop(code,None);self.db.sepeti_yaz(self.cart);self.update_cart();self.refresh_grid()
    def clear_cart(self):
        if self.cart and not confirm(self,'Sepetteki tüm kitaplar temizlensin mi?'):return
        self.cart.clear();self.db.sepeti_yaz(self.cart);self.update_cart();self.refresh_grid()
    def make_order(self):
        if not self.cart:return
        items=[]
        for code,variants in self.cart.items():
            for kind in ('SB','RNK'):
                amount=int(variants.get(kind,0))
                if amount>0:items.append({'kod':code,'tur':kind,'adet':amount,'hazir':0,'koli':0})
        info={'kod':format_kargo_kodu(self.shipping.text(),self.platform_value),
              'platform':self.platform_value,'ciro':self.revenue.value(),
              'siparis_turu':'Telafi Sipariş' if self.special_btn.isChecked() else 'Normal Sipariş'}
        if info['kod'] and not _ask_before_duplicate_shipping_code(self,self.db,info['kod']):
            return
        try:self.db.yeni_siparis_olustur(info,items)
        except Exception as exc:return error(self,str(exc))
        self.cart.clear();self.db.sepeti_yaz(self.cart)
        self.shipping.clear();self.revenue.clear();self.normal_btn.setChecked(True)
        self.update_cart();self.refresh_grid();self.order_created.emit()
    def import_one_cover(self,book):
        path,_=QFileDialog.getOpenFileName(self,'Kitap kapağı seç','','Görseller (*.png *.jpg *.jpeg *.webp *.bmp)')
        if path:
            try:self.covers.import_file(book,path);self.refresh_grid();self.update_cart()
            except Exception as exc:error(self,exc)
    def import_covers(self):
        folder=QFileDialog.getExistingDirectory(self,'Kapakların olduğu klasör')
        if folder:
            try:
                count=self.covers.import_folder(folder);self.refresh_grid();self.update_cart()
                QMessageBox.information(self,'Kapaklar',f'{count} kapak katalog ile eşleşerek aktarıldı.')
            except Exception as exc:error(self,exc)
