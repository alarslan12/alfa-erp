"""ALFA Banner Studio: fixed-canvas, 1..30 cover layouts; no cloud calls."""
from __future__ import annotations
import math, os, re, json, unicodedata, random
from dataclasses import dataclass, asdict
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

CANVAS=(1200,1600)
PALETTES={
 'Bordo / Parşömen': {'base':'#EEE2CF','end':'#CFB297','ink':'#38252A','accent':'#8B2944','deep':'#421F30','gold':'#C7964C','paper':'#FFF8ED'},
 'Zümrüt / Krem': {'base':'#EBE7DA','end':'#B9CFBD','ink':'#263C35','accent':'#276F60','deep':'#153E3F','gold':'#D0A45D','paper':'#FDF9F0'},
 'Petrol / Altın': {'base':'#193F4D','end':'#102632','ink':'#FFF3DD','accent':'#EBC88E','deep':'#0F3542','gold':'#DDAE5B','paper':'#F6ECD7'},
 'Kiremit / Kum': {'base':'#F1E1CC','end':'#D8B18E','ink':'#573329','accent':'#AE603A','deep':'#653B32','gold':'#D1A05A','paper':'#FFFAF3'},
 'Gece Mavisi': {'base':'#253650','end':'#12243A','ink':'#FCF3DF','accent':'#D3AD6D','deep':'#152943','gold':'#D8B169','paper':'#F6EDDE'},
 'Lavanta / Krem': {'base':'#EEE7E5','end':'#CFC4DD','ink':'#40374E','accent':'#795F97','deep':'#494066','gold':'#D7B171','paper':'#FFFAF3'},
 'Zeytin / Fildişi': {'base':'#F0E9D6','end':'#BCC5A5','ink':'#3E4736','accent':'#63744C','deep':'#344937','gold':'#CAA360','paper':'#FFFDF5'},
 'Grafit / Bronz': {'base':'#424548','end':'#1E282C','ink':'#F6EADA','accent':'#D7AA76','deep':'#253239','gold':'#D1A268','paper':'#FBF3E8'},
}
STYLES=['Vintage Koleksiyon','Modern Vitrin','Editoryal','Sergi Çerçevesi','Raf Düzeni','Minimal Premium']
LAYOUTS=['Akıllı','Büyük Kapak','Kompakt Izgara','Sergi Dizilimi','Dengeli Sıralar']
SLOGANS=['Güncel kaynaklar · Özenli baskı','Sınava hazırlıkta doğru kaynak','Kitapları keşfet · Setini oluştur','Temel · Klinik · Tam Set','Kitap koduyla hızlı sipariş','Detaylı bilgi için mesaj gönder','Kaynak seçimini kolaylaştırıyoruz']


def normalize(s):
 s=unicodedata.normalize('NFKD',str(s or '').casefold())
 s=''.join(c for c in s if not unicodedata.combining(c))
 return re.sub(r'[^a-z0-9]+',' ',s).strip()


def from_hex(s):
 s=s.strip('#');return tuple(int(s[i:i+2],16) for i in (0,2,4))


def mix(a,b,p):
 return tuple(int(a[i]*(1-p)+b[i]*p) for i in range(3))


def font_paths(bold=False,serif=False):
 win=os.environ.get('WINDIR','C:/Windows')
 base=f'{win}/Fonts'
 if serif:
  names=['georgiab.ttf','timesbd.ttf','Georgia Bold.ttf'] if bold else ['georgia.ttf','times.ttf']
 else:
  names=['segoeuib.ttf','arialbd.ttf','verdanab.ttf'] if bold else ['segoeui.ttf','arial.ttf','verdana.ttf']
 for name in names:yield f'{base}/{name}'
 if serif:
  yield '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
 else:
  yield '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
 yield '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'

@lru_cache(160)
def font(size,bold=False,serif=False):
 for path in font_paths(bold,serif):
  try:return ImageFont.truetype(path,size)
  except OSError:continue
 return ImageFont.load_default()



class ScaledDraw:
 """Draw at logical 1200x1600 coordinates on a genuine high-DPI canvas."""
 def __init__(self,image,scale=1):
  self.draw=ImageDraw.Draw(image);self.scale=max(1,int(scale))
 def _xy(self,box):
  if isinstance(box,(list,tuple)) and box and isinstance(box[0],(list,tuple)):
   return [tuple(round(c*self.scale) for c in point) for point in box]
  return tuple(round(c*self.scale) for c in box)
 def textbbox(self,xy,text,**kwargs):
  return self.draw.textbbox(self._xy(xy),text,**kwargs)
 def text(self,xy,text,**kwargs):
  return self.draw.text(self._xy(xy),text,**kwargs)
 def rounded_rectangle(self,xy,**kwargs):
  if 'radius' in kwargs:kwargs['radius']=round(kwargs['radius']*self.scale)
  if 'width' in kwargs:kwargs['width']=max(1,round(kwargs['width']*self.scale))
  return self.draw.rounded_rectangle(self._xy(xy),**kwargs)
 def rectangle(self,xy,**kwargs):
  if 'width' in kwargs:kwargs['width']=max(1,round(kwargs['width']*self.scale))
  return self.draw.rectangle(self._xy(xy),**kwargs)
 def ellipse(self,xy,**kwargs):
  if 'width' in kwargs:kwargs['width']=max(1,round(kwargs['width']*self.scale))
  return self.draw.ellipse(self._xy(xy),**kwargs)
 def arc(self,xy,start,end,**kwargs):
  if 'width' in kwargs:kwargs['width']=max(1,round(kwargs['width']*self.scale))
  return self.draw.arc(self._xy(xy),start,end,**kwargs)
 def line(self,xy,**kwargs):
  if 'width' in kwargs:kwargs['width']=max(1,round(kwargs['width']*self.scale))
  return self.draw.line(self._xy(xy),**kwargs)

def fitted(draw,text,box,max_size,min_size=14,bold=True,serif=False,fill='#111',anchor='mm',stroke=0,stroke_fill=None):
 """Text stays within a hard bounding box to prevent price/footer overflow."""
 x1,y1,x2,y2=box; text=str(text or '')
 scale=getattr(draw,'scale',1)
 size=max_size
 while size>min_size:
  f=font(round(size*scale),bold,serif)
  bounds=draw.textbbox((0,0),text,font=f,stroke_width=round(stroke*scale))
  if bounds[2]-bounds[0] <= (x2-x1-4)*scale and bounds[3]-bounds[1]<=(y2-y1-4)*scale:break
  size-=1
 x=(x1+x2)/2 if anchor=='mm' else x1+6
 y=(y1+y2)/2
 draw.text((x,y),text,font=font(round(size*scale),bold,serif),fill=fill,anchor=anchor,
           stroke_width=round(stroke*scale),stroke_fill=stroke_fill)


def alpha_surface(size):return Image.new('RGBA',size,(0,0,0,0))


@dataclass
class Settings:
 title_series:str='TTS'
 title_set:str='TEMEL SET'
 subtitle:str=''
 show_subtitle:bool=False
 eyebrow:str='TUSDATA · TUS HAZIRLIK'
 edition:str='37. BASKI'
 theme:str='Bordo / Parşömen'
 style:str='Vintage Koleksiyon'
 layout:str='Akıllı'
 offer:str='SB + RENKLİ'
 sb_price:str='2.800 TL'
 color_price:str='3.000 TL'
 sb_single_price:str='600 TL'
 color_single_price:str='750 TL'
 badge:str='+100 TL'
 badge_enabled:bool=False
 shop_name:str='DTY KİTAP'
 account_name:str='@kitapmagazam'
 logo_path:str=''
 logo_position:str='Sol'
 slogan:str='Güncel kaynaklar · Özenli baskı'
 brand_message:str='Tanıdık kalite, aynı özen.'
 note1:str='İlan fiyatı tek kitap içindir; set fiyatı için mesaj atınız.'
 note2:str='Lütfen bu ilanı doğrudan satın almayınız.'
 note3:str='Siparişten önce kitap kodunu ve baskı türünü belirtiniz.'
 cover_zoom:int=100
 cover_spacing:int=12
 show_codes:bool=False
 show_edition_badge:bool=True
 edition_font_size:int=28
 cover_edition_font_size:int=22
 cover_badge_font_size:int=23
 export_scale:int=2


def canonical_book_code(value):
 """One stable identity for Excel 71, 71.0, '071' and cover '71 - ...'."""
 if value is None or isinstance(value,bool):
  return ''
 if isinstance(value,float) and (not math.isfinite(value)):
  return ''
 text=str(value).strip().replace('\u00a0',' ')
 if re.fullmatch(r'\d+(?:[.,]0+)?',text):
  return str(int(text.replace(',','.').split('.')[0]))
 return text.upper()


def valid_page_count(value):
 """Return a valid page count, or None when unspecified/invalid.

 Page count is optional; book code and name determine catalog membership.
 """
 if value is None or isinstance(value,bool):return None
 text=str(value).strip().replace('\u00a0','').replace(' ','')
 if not re.fullmatch(r'\d+(?:[.,]0+)?',text):return None
 pages=int(float(text.replace(',','.')))
 return pages if 0<pages<=100000 else None


def read_excel(path):
 """Strict, order-preserving Excel catalog import with explicit collision checks.

 Header may be below introductory rows. Duplicate normalized book codes cause
 rejection, never silent replacement. A non-book sheet may be safely ignored.
 """
 from openpyxl import load_workbook
 book=load_workbook(path,read_only=True,data_only=True)
 try:
  output=[];seen={};problems=[];found_header=False
  aliases={
   'code':{'kitap kodu','kitap kod','kod','code','urun kodu','urun kod','stok kodu','sku'},
   'name':{'kitap adi','kitap ad','kitap ismi','kitap isim','kitap adı','ad','isim','name','title','urun adi','urun ad'},
   'group':{'kitap grubu','kitap grup','grup','group_name','kategori','alt grup','altgrup'},
   'pages':{'sayfa sayisi','sayfa say','sayfa','sayfa adedi','pages'},
   'color':{'renkli','supports_color','renkli opsiyon','renkli baski'}
  }
  def header_key(value):
   text=str(value or '').replace('İ','i').replace('I','i').replace('ı','i').casefold()
   text=unicodedata.normalize('NFKD',text)
   text=''.join(c for c in text if not unicodedata.combining(c))
   return re.sub(r'[^a-z0-9]+',' ',text).strip()
  expected={k:{header_key(w) for w in names} for k,names in aliases.items()}
  for sheet in book.worksheets:
   rows=sheet.iter_rows(values_only=True)
   columns=None;header_number=0
   # Decorative title rows or merged headers must not hide the real columns.
   for number,row in enumerate(rows,1):
    if number>40:break
    mapping={}
    for i,value in enumerate(row):
     key=header_key(value)
     for col,words in expected.items():
      if key in words and col not in mapping:
       mapping[col]=i
    if 'code' in mapping and 'name' in mapping:
     columns=mapping;header_number=number;found_header=True;break
   if columns is None:continue
   group=''
   for row_number,row in enumerate(rows,header_number+1):
    def cell(key):
     i=columns.get(key)
     return row[i] if i is not None and i<len(row) else None
    raw_group=cell('group')
    if raw_group is not None and str(raw_group).strip():
     group=' '.join(str(raw_group).split())
    raw_code=cell('code')
    code=canonical_book_code(raw_code)
    name=' '.join(str(cell('name') or '').split())
    pages=valid_page_count(cell('pages'))
    # Excel has empty placeholders that carry a code but no book name.
    # A real named book remains valid even when its page count is blank.
    # Do not create catalog entries for name-less placeholders.
    if not code or not name:continue
    if len(code)>55 or len(name)>180:
     problems.append(f'{sheet.title} satır {row_number}: kod veya başlık çok uzun')
     continue
    if code in seen:
     first=seen[code]
     raise ValueError(f'Tekrarlanan kitap kodu {code}: {first} ve {sheet.title} satır {row_number}. Excel düzeltilmeden katalog değiştirilmeyecek.')
    seen[code]=f'{sheet.title} satır {row_number}'
    raw_color=cell('color')
    colored=bool(raw_color) if isinstance(raw_color,(int,bool)) else header_key(raw_color) in ('evet','yes','var','renkli','true','1')
    output.append({'id':code,'code':code,'name':name,'group':group,'pages':pages,'color':colored,'cover_override':'','badge_override':'','edition_override':''})
  if not found_header:
   raise ValueError('Excel başlıkları bulunamadı. Kitap Kodu ve Kitap Adı sütunlarını kontrol et.')
  if not output:
   raise ValueError('Excel içinde geçerli kitap bulunamadı; eski katalog korundu.')
  if problems:
   # Never silently accept a partial catalog: the user must fix the source.
   details='; '.join(problems[:5])
   raise ValueError(f'Excelde {len(problems)} geçersiz ürün satırı var: {details}. Eski katalog korundu.')
  return output
 finally:
  book.close()

def upright_cover(image):
 """Orient landscape artwork for portrait book slots; never rewrite original.

 First honor embedded EXIF orientation, then rotate remaining landscape
 image 270 degrees clockwise, with canvas expansion so nothing is cropped.
 """
 source=ImageOps.exif_transpose(image)
 if source.width>source.height:
  source=source.rotate(270,expand=True,resample=Image.Resampling.BICUBIC)
 return source


def cover_files(folder):
 """Index images by exact code and by unnumbered title, never mixed prefixes."""
 by_code={};by_name={}
 if not folder or not Path(folder).is_dir():return by_code,by_name
 for root,dirs,files in os.walk(folder):
  dirs.sort()
  for filename in sorted(files):
   p=Path(root)/filename
   if p.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):continue
   stem=p.stem.strip()
   # Explicit code needs a separator: '71 - title', '071_title', or '71'.
   m=re.match(r'^#?(\d+)(?=$|[ _.-])',stem)
   if m:
    code=canonical_book_code(m.group(1))
    by_code.setdefault(code,[]).append(str(p))
    tail=stem[m.end():].lstrip(' -._')
    # Numbered artwork belongs to its code only, never a different name match.
   else:
    by_name.setdefault(normalize(stem),str(p))
 return by_code,by_name


def get_cover(row,index):
 override=row.get('cover_override')
 if override and Path(override).is_file():return override
 by_code,by_name=index
 code=canonical_book_code(row.get('code'))
 name=normalize(row.get('name'))
 matches=by_code.get(code,[])
 if isinstance(matches,str):matches=[matches]
 # Prefer a code-title pair, otherwise accept a code-only filename.
 # A reused numeric prefix with a different title is NOT the same book.
 exact=[];bare=[]
 for candidate in matches:
  stem=Path(candidate).stem.strip()
  marker=re.match(r'^#?(\d+)(?=$|[ _.-])',stem)
  title=normalize(stem[marker.end():].lstrip(' -._')) if marker else ''
  if title and name and (title==name or title.endswith(name) or name.endswith(title)):
   exact.append(candidate)
  elif not title:
   bare.append(candidate)
 if exact:return exact[-1]
 if bare:return bare[-1]
 # Name-only covers are valid, but a numbered cover belongs exclusively to
 # that number; do not attach it to a different book via fuzzy similarity.
 return by_name.get(name)

def columns_for(n,layout):
 if n==1:return 1
 if layout=='Kompakt Izgara':
  return max(2,min(7,math.ceil(math.sqrt(n*1.5))))
 if layout=='Büyük Kapak':
  for top,bottom in [(2,2),(4,2),(6,3),(8,4),(10,5),(12,4),(15,5),(18,6),(20,5),(24,6),(30,6)]:
   if n<=top:return bottom
 if layout=='Sergi Dizilimi':
  return 2 if n<=4 else 3 if n<=9 else 4 if n<=16 else 5 if n<=25 else 6
 if layout=='Dengeli Sıralar':
  return min(6,max(1,math.ceil(math.sqrt(n*1.2))))
 for maximum,cols in [(1,1),(2,2),(3,3),(4,2),(6,3),(8,4),(10,5),(12,4),(15,5),(16,4),(20,5),(24,6),(30,6)]:
  if n<=maximum:return cols
 return 6


class Renderer:
 def __init__(self,settings,books,index,scale=1):
  self.scale=max(1,min(3,int(scale)))
  self.settings=settings
  self.books=list(books)[:30]
  self.index=index
  self.positions=[]

 def render(self):
  """Reference-style poster: compact headings, large central book covers.

  Critical sale elements stay between 200..1400 to tolerate marketplace
  square thumbnail crops. Final PNG size is ALWAYS 1200×1600.
  """
  cfg=self.settings;p=PALETTES.get(cfg.theme,PALETTES['Zümrüt / Krem'])
  accent=from_hex(p['accent']); deep=from_hex(p['deep']);gold=from_hex(p['gold'])
  paper=from_hex(p['paper']);ink=from_hex(p['ink'])
  dark_bg=cfg.theme in ('Petrol / Altın','Gece Mavisi','Grafit / Bronz')
  heading=paper if dark_bg else deep
  img=self._background(p)
  d=ScaledDraw(img,self.scale)
  style=cfg.style
  # The reference had uninterrupted book imagery, not giant title cards.
  # Thin ornamental frame sits outside the crop-safe content.
  if style in ('Vintage Koleksiyon','Sergi Çerçevesi'):
   d.rounded_rectangle((52,42,1148,1550),radius=33,outline=gold,width=3)
   d.rounded_rectangle((64,54,1136,1538),radius=26,outline=mix(gold,from_hex(p['base']),.47),width=1)
  elif style=='Editoryal':
   d.line((78,68,1122,68),fill=gold,width=4)
   d.line((78,1539,1122,1539),fill=gold,width=4)
  elif style=='Raf Düzeni':
   for yy in (580,792,1010):d.line((92,yy,1108,yy),fill=mix(gold,heading,.38),width=3)
  elif style=='Modern Vitrin':
   d.rounded_rectangle((75,70,1125,285),radius=34,fill=mix(deep,accent,.55))
  # An optical center axis runs through the complete headline.
  # The upper third is deliberately taller than in v3.2.
  eyecolor=paper if dark_bg or style=='Modern Vitrin' else deep
  fitted(d,cfg.eyebrow,(110,68,1090,125),35,min_size=17,bold=True,fill=eyecolor)
  titlebox=(82,126,1118,276)
  title_ink=paper if style=='Modern Vitrin' else heading
  fitted(d,cfg.title_series,titlebox,135,min_size=35,bold=True,
         serif=style in ('Vintage Koleksiyon','Editoryal'),fill=title_ink)
  title_type=str(cfg.title_set).strip().upper()
  d.rounded_rectangle((253,286,947,367),radius=19,fill=deep if dark_bg else accent)
  fitted(d,title_type,(273,297,927,357),47,min_size=20,bold=True,
         serif=style=='Vintage Koleksiyon',fill=paper)
  # Real cover stage stays above the relocated edition badge.
  stage=(70,394,1130,971)
  if style in ('Sergi Çerçevesi','Raf Düzeni'):
   col=mix(paper,from_hex(p['base']),.25)
   d.rounded_rectangle((74,392,1126,973),radius=20,fill=col,outline=gold,width=3)
  self._covers(img,stage,cfg,p)
  # Edition pill is directly ABOVE the book-count label, not beside title.
  if cfg.show_edition_badge and str(cfg.edition).strip():
   self._edition(img,cfg.edition,gold,deep,paper,cfg.edition_font_size)
  desc=(str(cfg.subtitle).strip() if cfg.show_subtitle and str(cfg.subtitle).strip()
        else (f'{len(self.books)} KİTAP  ·  {title_type}' if len(self.books)>1
              else '1 KİTAP  ·  TEK KİTAP'))
  d.rounded_rectangle((246,1050,954,1097),radius=16,fill=deep)
  fitted(d,desc,(263,1058,937,1091),26,min_size=17,bold=True,fill=paper)
  # Stable price positions regardless of visual layout / number of books.
  if cfg.offer=='SB + RENKLİ':
   self._price_panel(img,(90,1111,566,1251),'SİYAH-BEYAZ',cfg.sb_single_price,cfg.sb_price,p)
   self._price_panel(img,(634,1111,1110,1251),'RENKLİ',cfg.color_single_price,cfg.color_price,p)
  else:
   self._price_panel(img,(240,1111,960,1251),'SİYAH-BEYAZ',cfg.sb_single_price,cfg.sb_price,p)
  # Mandatory warnings: spacious, legible, NEVER obscured by brand name.
  d.rounded_rectangle((78,1272,1122,1425),radius=23,fill=paper,outline=gold,width=3)
  messages=[cfg.note1,cfg.note2,cfg.note3]
  for i,note in enumerate(messages):
   if not str(note or '').strip():continue
   top=1284+45*i
   d.ellipse((103,top+12,119,top+28),fill=accent)
   fitted(d,note,(142,top+2,1081,top+39),25,min_size=17,
          bold=(i==1),fill=deep,anchor='lm')
  # Dedicated brand panel: can never collide with legal notices.
  d.rounded_rectangle((84,1442,1116,1540),radius=23,
                      fill=mix(deep,accent,.29))
  self._footer(img,cfg,p)
  fitted(d,cfg.slogan,(165,1553,1035,1586),18,min_size=12,
         bold=False,fill=heading)
  return img

 def _background(self,p):
  # fast native resize of 256px gradient, not ~2 million Python pixel loops
  start=from_hex(p['base']);stop=from_hex(p['end'])
  scale=self.scale
  gradient=Image.new('RGB',(1,256))
  for y in range(256):
   t=y/255
   gradient.putpixel((0,y),mix(start,stop,t))
  canvas=gradient.resize((CANVAS[0]*scale,CANVAS[1]*scale),Image.Resampling.BILINEAR)
  d=ScaledDraw(canvas,scale)
  style=self.settings.style;accent=from_hex(p['accent']);gold=from_hex(p['gold'])
  if style in ('Vintage Koleksiyon','Editoryal'):
   for i in range(5):
    d.arc((-150-i*25,-200-i*22,470+i*30,390+i*25),15,82,fill=mix(gold,start,.4),width=2)
    d.arc((770-i*30,1180-i*25,1450+i*22,1730+i*25),180,255,fill=mix(gold,stop,.45),width=2)
  elif style in ('Modern Vitrin','Sergi Çerçevesi'):
   d.ellipse((1000,-90,1320,240),outline=gold,width=10)
   d.rounded_rectangle((-125,1160,300,1570),radius=110,outline=mix(gold,stop,.35),width=5)
  elif style=='Raf Düzeni':
   for y in (535,747,960):d.line((90,y,1110,y),fill=mix(gold,start,.4),width=5)
  # deterministic low-contrast paper grain
  noise=Image.effect_noise((300,400),30).convert('L').resize(canvas.size,Image.Resampling.BILINEAR)
  canvas=Image.blend(canvas,Image.merge('RGB',(noise,noise,noise)),0.045)
  return canvas

 def _edition(self,img,label,gold,dark,paper,point_size=28):
  """Edition pill centred under book covers and above count/ribbon."""
  d=ScaledDraw(img,self.scale)
  box=(412,984,788,1040)
  d.rounded_rectangle(box,radius=18,fill=dark,outline=gold,width=3)
  fitted(d,label,(428,991,772,1032),max(16,min(60,int(point_size))),
         min_size=14,bold=True,serif=True,fill=paper)

 def _covers(self,img,rect,cfg,p):
  """Transparent, proportional cover images; no white card or lift shadow.

  The spacing slider changes actual inter-cover distance, not merely cell
  margins. All layout presets produce different real arrangements.
  """
  n=len(self.books)
  if not n:return
  x1,y1,x2,y2=rect
  cols=min(n,columns_for(n,cfg.layout))
  if cfg.layout=='Büyük Kapak':
   cols=max(1,min(cols,4 if n<=12 else 5))
  if cfg.layout=='Kompakt Izgara':
   cols=max(1,min(n,math.ceil(math.sqrt(n*2.0))))
  if cfg.layout=='Sergi Dizilimi':
   cols=min(n,2 if n<=5 else 3 if n<=9 else 4 if n<=16 else 5 if n<=25 else 6)
  if cfg.layout=='Dengeli Sıralar':
   cols=min(n,max(1,round(math.sqrt(n*1.35))))
  rows=math.ceil(n/cols)
  space=max(0,min(65,int(getattr(cfg,'cover_spacing',12))))
  gapx=space
  gapy=max(0,round(space*0.82))
  # Consistent cover ratio approximates portrait textbook covers.
  stage_w=x2-x1;stage_h=y2-y1
  # All rows stay in the same stage and cannot hit price/footer blocks.
  maxh=(stage_h-gapy*(rows-1))/rows
  maxw=(stage_w-gapx*(cols-1))/cols
  zoom=max(.70,min(1.18,cfg.cover_zoom/100))
  cover_h=max(37,min(maxh, maxw/.70)*zoom)
  cover_w=min(maxw,cover_h*.70)
  cover_h=min(maxh,cover_w/.70)
  # A single book should not fill the entire poster width.
  if n==1:
   cover_h=min(cover_h,640);cover_w=min(cover_w,cover_h*.70)
  row_height=cover_h+gapy
  used_h=rows*cover_h+(rows-1)*gapy
  top=y1+(stage_h-used_h)/2
  gold=from_hex(p['gold'])
  accent=from_hex(p['accent'])
  ink=from_hex(p['deep']);paper=from_hex(p['paper'])
  draw=ScaledDraw(img,self.scale)
  self.positions=[]
  for index,book in enumerate(self.books):
   r,c=divmod(index,cols)
   count_this_row=min(cols,n-r*cols)
   width_row=count_this_row*cover_w+(count_this_row-1)*gapx
   row_left=x1+(stage_w-width_row)/2
   if cfg.layout=='Sergi Dizilimi' and r%2 and count_this_row>1:
    # Very slight alternating row indentation that visibly differentiates
    # the "exhibition" preset while staying within the stage.
    row_left+=min(14,max(0,(stage_w-width_row)/3))
   bx=int(row_left+c*(cover_w+gapx))
   by=int(top+r*row_height)
   cw=int(cover_w);ch=int(cover_h)
   cover=get_cover(book,self.index)
   iw=cw;ih=ch;ix=bx;iy=by
   try:
    if not cover:raise FileNotFoundError
    with Image.open(cover) as original:
     pic=ImageOps.contain(upright_cover(original).convert('RGBA'),(cw*self.scale,ch*self.scale),method=Image.Resampling.LANCZOS)
    iw,ih=pic.size
    iw=iw/self.scale;ih=ih/self.scale
    ix=bx+(cw-iw)/2;iy=by+(ch-ih)/2
    # Original image pixels are sampled directly for HD/Ultra HD export.
    img.paste(pic,(round(ix*self.scale),round(iy*self.scale)),pic)
   except (OSError,ValueError,FileNotFoundError):
    draw.rounded_rectangle((bx,by,bx+cw,by+ch),radius=5,
                           outline=gold,width=2)
    fitted(draw,'KAPAK YOK',(bx+5,by+5,bx+cw-5,by+ch-5),17,
           min_size=10,fill=ink)
   # Per-book price and edition are scaled to each visible cover.
   # User font sliders go up to 86; a small cover still clamps within the
   # physical book's footprint rather than covering its neighbour.
   custom_badge=str(book.get('badge_override') or '').strip()
   badge=custom_badge or str(cfg.badge or '').strip()
   if badge and (bool(custom_badge) or cfg.badge_enabled) and iw>=42:
    pref=max(10,min(86,int(cfg.cover_badge_font_size)))
    limitw=max(37,iw*.93)
    targetw=len(badge)*pref*.67+19
    bw=min(limitw,max(52,targetw))
    bh=min(max(28,pref*1.48),max(28,ih*.32),95)
    rx=ix+iw-bw;ry=iy+2
    draw.rounded_rectangle((rx,ry,rx+bw,ry+bh),radius=7,
                           fill=accent,outline=gold,width=2)
    fitted(draw,badge,(rx+3,ry+2,rx+bw-3,ry+bh-2),pref,
           min_size=8,fill=paper)
   edition=str(book.get('edition_override') or '').strip()
   if edition and iw>=40:
    pref=max(10,min(86,int(cfg.cover_edition_font_size)))
    limitw=max(38,iw*.98)
    targetw=len(edition)*pref*.55+18
    bw=min(limitw,max(58,targetw))
    bh=min(max(28,pref*1.44),max(28,ih*.32),95)
    ex=ix+iw/2-bw/2;ey=iy+ih-bh-1
    draw.rounded_rectangle((ex,ey,ex+bw,ey+bh),radius=7,
                           fill=ink,outline=gold,width=2)
    fitted(draw,edition,(ex+3,ey+2,ex+bw-3,ey+bh-2),pref,
           min_size=8,fill=paper)
   if cfg.show_codes and iw>=90:
    code=str(book.get('code') or '')
    if code:
     draw.rounded_rectangle((ix+4,iy+4,ix+56,iy+25),radius=6,fill=paper)
     fitted(draw,code,(ix+5,iy+5,ix+55,iy+24),13,min_size=10,fill=ink)
   # Hit-box matches true visible cover, not empty slot.
   self.positions.append((ix,iy,ix+iw,iy+ih,index))

 def _price_panel(self,img,rect,title,single,set_price,p):
  """Two optically aligned, inset price pills: single above, set below."""
  d=ScaledDraw(img,self.scale);x1,y1,x2,y2=rect
  paper=from_hex(p['paper']);deep=from_hex(p['deep']);gold=from_hex(p['gold'])
  d.rounded_rectangle((x1,y1,x2,y2),radius=19,
                      fill=paper,outline=gold,width=2)
  d.rounded_rectangle((x1+5,y1+5,x2-5,y1+35),radius=10,fill=deep)
  fitted(d,title,(x1+14,y1+7,x2-14,y1+33),19,min_size=14,fill=paper)
  d.rounded_rectangle((x1+9,y1+43,x2-9,y1+80),radius=10,
                      fill=mix(paper,gold,.08),outline=mix(gold,paper,.35),width=1)
  d.rounded_rectangle((x1+9,y1+86,x2-9,y2-8),radius=10,
                      fill=mix(paper,gold,.17),outline=mix(gold,paper,.15),width=1)
  available=x2-x1-18
  labelw=max(104,min(150,available*.35))
  sep=x1+9+labelw
  d.line((sep,y1+51,sep,y1+72),fill=mix(gold,paper,.35),width=1)
  d.line((sep,y1+93,sep,y2-17),fill=mix(gold,paper,.35),width=1)
  fitted(d,'TEK KİTAP',(x1+14,y1+48,sep-5,y1+75),16,min_size=12,
         bold=True,fill=deep)
  fitted(d,single,(sep+6,y1+44,x2-16,y1+79),28,min_size=14,
         bold=True,fill=deep)
  fitted(d,'SET FİYATI',(x1+14,y1+91,sep-5,y2-14),17,min_size=12,
         bold=True,fill=deep)
  fitted(d,set_price,(sep+6,y1+87,x2-16,y2-10),36,min_size=18,
         bold=True,fill=deep)

 def _footer(self,img,cfg,p):
  """Logo-free, centered typography inside dedicated brand panel."""
  d=ScaledDraw(img,self.scale)
  paper=from_hex(p['paper']);gold=from_hex(p['gold'])
  fitted(d,cfg.shop_name,(115,1447,1085,1485),32,min_size=17,
         bold=True,serif=True,fill=paper)
  fitted(d,cfg.account_name,(115,1484,1085,1511),21,min_size=13,
         bold=True,fill=gold)
  fitted(d,cfg.brand_message,(115,1512,1085,1536),17,min_size=11,
         bold=False,fill=paper)


def square_preview(img):
 w,h=img.size;top=(h-w)//2
 return img.crop((0,top,w,top+w))


def make_book(code,name,cover=''):
 return {'id':str(code or name),'code':str(code),'name':name,'group':'Harici / Özel Kapak','pages':None,'color':False,'cover_override':cover,'badge_override':''}


def save_project(path,settings,books,excel='',covers=''):
 payload={'schema':2,'settings':asdict(settings),'books':books,'catalog_path':excel,'covers_path':covers}
 Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')


def load_project(path):
 obj=json.loads(Path(path).read_text(encoding='utf-8'))
 if not isinstance(obj,dict) or obj.get('schema')!=2:raise ValueError('Banner Studio v2 projesi değil')
 raw=obj.get('settings') or {};valid=Settings.__dataclass_fields__
 cfg=Settings(**{k:v for k,v in raw.items() if k in valid})
 books=obj.get('books') or []
 if not isinstance(books,list) or len(books)>30:raise ValueError('En fazla 30 kitap kullanılabilir')
 return cfg,books,str(obj.get('catalog_path') or ''),str(obj.get('covers_path') or '')
