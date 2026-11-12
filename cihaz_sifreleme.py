"""Local Windows DPAPI encryption for Firebase device sessions.

No network client, no remote credentials, and no embedded admin password.
The DPAPI format is compatible with existing firebase_owner_session.bin and
firebase_staff_session.bin files.
"""
import os, sys, ctypes
from ctypes import wintypes
from pathlib import Path

DATA=Path(os.environ.get('ALFA_ERP_DATA_DIR') or
    Path(os.environ.get('LOCALAPPDATA') or Path.home()/'.local'/'share')/'AlfaERP')
APP_ROOT=(Path(sys.executable).resolve().parent if getattr(sys,'frozen',False)
          else Path(__file__).resolve().parent)
RESOURCE_ROOT=Path(__file__).resolve().parent
OWNER_APP=((RESOURCE_ROOT/'YONETICI_SURUMU.flag').is_file()
           or (APP_ROOT/'YONETICI_SURUMU.flag').is_file()
           or (getattr(sys,'frozen',False)
               and Path(sys.executable).name.lower()=='alfaerpyonetici.exe'))


class DeviceError(RuntimeError):
    pass


def crypt(data, decrypt=False):
    """Encrypt or decrypt bytes through Windows DPAPI; never transmit secrets."""
    if os.name!='nt':
        raise DeviceError('Windows cihaz şifrelemesi gerekli.')
    class Blob(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    buff=ctypes.create_string_buffer(data)
    src=Blob(len(data),ctypes.cast(buff,ctypes.POINTER(ctypes.c_byte)))
    out=Blob()
    dll=ctypes.windll.crypt32
    dll.CryptProtectData.argtypes=[
        ctypes.POINTER(Blob),ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p,
        ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    dll.CryptUnprotectData.argtypes=[
        ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,
        ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype=ctypes.c_void_p
    ok=(dll.CryptUnprotectData(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out))
        if decrypt else dll.CryptProtectData(
            ctypes.byref(src),'ALFA ERP',None,None,None,1,ctypes.byref(out)))
    if not ok:
        raise DeviceError('Windows cihaz kimliği işlenemedi.')
    try:
        return ctypes.string_at(out.pbData,out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(out.pbData,ctypes.c_void_p))
