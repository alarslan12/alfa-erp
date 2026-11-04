"""Windows paired-device client; private device token DPAPI protected."""
import os,json,ctypes,urllib.request,urllib.error
from ctypes import wintypes
from pathlib import Path
from alfa_bulut import PROJECT_URL,PUBLISHABLE_KEY
DATA=Path(os.environ.get('ALFA_ERP_DATA_DIR') or Path(os.environ.get('LOCALAPPDATA') or Path.home()/'.local'/'share')/'AlfaERP')
ENDPOINT=PROJECT_URL.rstrip('/')+'/functions/v1/alfa-erp-device'
SECRET=DATA/'alfa_cihaz.bin'
class DeviceError(RuntimeError):
    def __init__(self,message,status=None):
        super().__init__(message)
        self.status=status
    @property
    def permanent(self):return self.status in (400,409,413,422)


def crypt(data,decrypt=False):
    if os.name!='nt':raise DeviceError('Windows cihaz eşleştirmesi gerekli.')
    class Blob(ctypes.Structure):_fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    buff=ctypes.create_string_buffer(data);src=Blob(len(data),ctypes.cast(buff,ctypes.POINTER(ctypes.c_byte)));out=Blob()
    dll=ctypes.windll.crypt32
    dll.CryptProtectData.argtypes=[ctypes.POINTER(Blob),ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    dll.CryptUnprotectData.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p];ctypes.windll.kernel32.LocalFree.restype=ctypes.c_void_p
    ok=(dll.CryptUnprotectData(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out)) if decrypt else
        dll.CryptProtectData(ctypes.byref(src),'ALFA ERP',None,None,None,1,ctypes.byref(out)))
    if not ok:raise DeviceError('Windows cihaz anahtarı işlenemedi.')
    try:return ctypes.string_at(out.pbData,out.cbData)
    finally:ctypes.windll.kernel32.LocalFree(ctypes.cast(out.pbData,ctypes.c_void_p))

def get_token():
    try:
        token=crypt(SECRET.read_bytes(),True).decode('ascii')
        return token if len(token)==64 else None
    except (OSError,UnicodeError,DeviceError):return None

def save_token(token):
    if len(token)!=64:raise DeviceError('Geçersiz cihaz anahtarı')
    DATA.mkdir(parents=True,exist_ok=True);tmp=SECRET.with_suffix('.tmp')
    tmp.write_bytes(crypt(token.encode('ascii')));os.replace(tmp,SECRET)

def api(action,token=None,admin_jwt=None,timeout=15,**kwargs):
    payload={'action':action,**kwargs}
    if token:payload['device_token']=token
    headers={'apikey':PUBLISHABLE_KEY,'Content-Type':'application/json'}
    if admin_jwt:headers['Authorization']='Bearer '+admin_jwt
    req=urllib.request.Request(ENDPOINT,json.dumps(payload,ensure_ascii=False).encode(),headers,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:msg=json.loads(exc.read().decode()).get('error')
        except (ValueError,UnicodeError):msg=None
        raise DeviceError(str(msg or f'HTTP {exc.code}')[:300],status=exc.code) from None
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        raise DeviceError('Bağlantı geçici olarak kesildi. İşlem kuyrukta korunuyor.') from exc

class Workstation:
    def __init__(self,token=None):self.token=token or get_token()
    @property
    def paired(self):return bool(self.token)
    def sync(self,known=None,notification=False,last_order_number=0):
        """Single authenticated request: revision check + only changed data.

        No recurring full-catalog download and no separate pulse HTTP call.
        """
        params={'known':dict(known or {})}
        if notification:
            params.update(mode='notifications',last_order_number=max(0,int(last_order_number or 0)))
        return api('sync',self.token,timeout=20 if not notification else 12,**params)

    def snapshot(self):return api('snapshot',self.token,timeout=25)
    def pulse(self):return api('pulse',self.token,timeout=8)
    def transition(self,events):return api('transition',self.token,events=events,timeout=12)['results']
    def progress(self,events):return api('progress',self.token,events=events,timeout=15)['results']
    def inventory_sale(self,product_id,quantity,sale_price):
        return api('inventory_sale',self.token,product_id=product_id,quantity=quantity,sale_price=sale_price,timeout=15)
    def commit(self,edits):return api('commit',self.token,edits=edits,timeout=30)['results']
