"""Read-only Canon/Epson Windows printer and vendor-tool inventory.

Uses documented WinSpool GetPrinterW (driver and port identity), plus
Windows installed-program uninstall registry metadata. It DOES NOT run,
scrape, inject into or impersonate proprietary Epson/Canon status utilities.
Those utilities may have no supported automation API. Vendor status is
gathered separately via standards-based IPP/SNMP.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

if os.name=="nt":
    import winreg
else:
    winreg=None

MAX_PRINTER_INFO=2*1024*1024
MAX_SOFTWARE_ENTRIES=600
VENDORS=("Epson","Canon")


class _PrinterInfo2(ctypes.Structure):
    _fields_=[
        ("server",wintypes.LPWSTR),("name",wintypes.LPWSTR),
        ("share",wintypes.LPWSTR),("port",wintypes.LPWSTR),
        ("driver",wintypes.LPWSTR),("comment",wintypes.LPWSTR),
        ("location",wintypes.LPWSTR),("devmode",ctypes.c_void_p),
        ("separator",wintypes.LPWSTR),("processor",wintypes.LPWSTR),
        ("datatype",wintypes.LPWSTR),("parameters",wintypes.LPWSTR),
        ("security",ctypes.c_void_p),("attributes",wintypes.DWORD),
        ("priority",wintypes.DWORD),("default_priority",wintypes.DWORD),
        ("start_time",wintypes.DWORD),("until_time",wintypes.DWORD),
        ("status",wintypes.DWORD),("jobs",wintypes.DWORD),
        ("average_ppm",wintypes.DWORD)
    ]


def _vendor(text):
    name=str(text or "").casefold()
    if "epson" in name:return "Epson"
    if "canon" in name:return "Canon"
    return "Bilinmiyor"


class WinPrinterVendorInventory:
    """Inspect only printers that the current Windows user can access."""

    def __init__(self,winspool):
        if os.name!="nt":
            raise RuntimeError("Windows üretici tanıma yalnız Windows'ta kullanılır.")
        self.api=winspool
        self.api.GetPrinterW.argtypes=[
            wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,
            wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)
        ]
        self.api.GetPrinterW.restype=wintypes.BOOL

    def _printer(self,name):
        handle=wintypes.HANDLE()
        if not self.api.OpenPrinterW(name,ctypes.byref(handle),None):
            return {"driver":"","port":"","error":"Windows yazıcı ayrıntısına erişilemiyor"}
        try:
            size=wintypes.DWORD()
            self.api.GetPrinterW(handle,2,None,0,ctypes.byref(size))
            if not size.value or size.value>MAX_PRINTER_INFO:
                return {"driver":"","port":"","error":"Windows yazıcı bilgisi çok büyük/bulunamadı"}
            buf=ctypes.create_string_buffer(size.value)
            if not self.api.GetPrinterW(
                handle,2,buf,len(buf),ctypes.byref(size)
            ):
                return {"driver":"","port":"","error":"Windows sürücü bilgisi okunamadı"}
            info=ctypes.cast(buf,ctypes.POINTER(_PrinterInfo2)).contents
            return {
                "driver":str(info.driver or "")[:180],
                "port":str(info.port or "")[:180],
                "windows_status":int(info.status),
                "windows_jobs":int(info.jobs),
                "error":""
            }
        finally:
            self.api.ClosePrinter(handle)

    def snapshot(self,names):
        result={}
        for name in list(names)[:80]:
            meta=self._printer(name)
            driver=meta.get("driver") or ""
            # A vendor name in Windows' driver ID is a clue, not a
            # model-specific or software-API compatibility guarantee.
            meta["vendor"]=_vendor(driver) if driver else _vendor(name)
            meta["vendor_basis"]="Windows sürücü adı" if driver else "Yazıcı adı (tahmini)"
            result[str(name)]=meta
        return result


def installed_vendor_tools():
    """Enumerate registered applications without launching them.

    This is host-wide software inventory, NOT proof the utility can
    communicate with any particular printer or expose a public API.
    """
    if winreg is None:return []
    path=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    scopes=[
        (winreg.HKEY_CURRENT_USER,0),
        (winreg.HKEY_LOCAL_MACHINE,winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE,winreg.KEY_WOW64_32KEY),
    ]
    found={}
    for root,flags in scopes:
        try:
            parent=winreg.OpenKey(root,path,0,winreg.KEY_READ|flags)
        except OSError:
            continue
        with parent:
            try:count=min(MAX_SOFTWARE_ENTRIES,winreg.QueryInfoKey(parent)[0])
            except OSError:continue
            for i in range(count):
                try:
                    keyname=winreg.EnumKey(parent,i)
                    with winreg.OpenKey(parent,keyname,0,winreg.KEY_READ) as key:
                        name=str(winreg.QueryValueEx(key,"DisplayName")[0] or "")[:160]
                        if not name:continue
                        try:publisher=str(winreg.QueryValueEx(key,"Publisher")[0] or "")[:110]
                        except OSError:publisher=""
                        vendor=_vendor(name+" "+publisher)
                        if vendor=="Bilinmiyor":continue
                        try:version=str(winreg.QueryValueEx(key,"DisplayVersion")[0] or "")[:65]
                        except OSError:version=""
                        item={
                            "vendor":vendor, "name":name,
                            "version":version,
                            "kind":"Windows'ta yüklü üretici yazılımı",
                            "integration":"Doğrudan üretici uygulaması API'si doğrulanmadı"
                        }
                        found[(vendor,name.casefold(),version)]=item
                except (OSError,ValueError):
                    continue
    return sorted(found.values(),key=lambda x:(x["vendor"],x["name"].casefold()))[:80]
