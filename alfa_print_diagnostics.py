"""Read-only diagnostics for the ALFACOPYCENTER Windows print monitor.

Never requests elevation, restarts Spooler, changes device permissions,
deletes jobs or touches the Windows print queue. Diagnostics may be run while
printing continues.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import sqlite3

from alfa_print_monitor import read_collector_snapshot
from alfa_print_runtime import PrintAgentStartup, PrintAgentLease


def spooler_state() -> str:
    if os.name!="nt":
        return "Windows dışı sistem"
    api=ctypes.WinDLL("advapi32.dll",use_last_error=True)
    open_manager=api.OpenSCManagerW
    open_manager.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD]
    open_manager.restype=wintypes.HANDLE
    open_service=api.OpenServiceW
    open_service.argtypes=[wintypes.HANDLE,wintypes.LPCWSTR,wintypes.DWORD]
    open_service.restype=wintypes.HANDLE
    close=api.CloseServiceHandle
    close.argtypes=[wintypes.HANDLE]
    close.restype=wintypes.BOOL

    class ServiceStatus(ctypes.Structure):
        _fields_=[
            ("type",wintypes.DWORD),("state",wintypes.DWORD),
            ("accepted",wintypes.DWORD),("win32_exit",wintypes.DWORD),
            ("service_exit",wintypes.DWORD),("checkpoint",wintypes.DWORD),
            ("hint",wintypes.DWORD),("pid",wintypes.DWORD),
            ("flags",wintypes.DWORD)
        ]
    status_call=api.QueryServiceStatusEx
    status_call.argtypes=[
        wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD)
    ]
    status_call.restype=wintypes.BOOL
    manager=open_manager(None,None,0x0001)  # SC_MANAGER_CONNECT only
    if not manager:
        return "Hizmet sorgusu için Windows izin vermedi (yükseltme yapılmadı)"
    try:
        service=open_service(manager,"Spooler",0x0004)  # SERVICE_QUERY_STATUS only
        if not service:
            return "Spooler durumunu okuma izni yok veya hizmet bulunamadı"
        try:
            status=ServiceStatus()
            required=wintypes.DWORD()
            if not status_call(service,0,ctypes.byref(status),
                               ctypes.sizeof(status),ctypes.byref(required)):
                return "Windows Spooler durum sorgusu başarısız"
            return {
                1:"Durduruldu",2:"Başlatılıyor",3:"Durduruluyor",
                4:"Çalışıyor",5:"Devam edecek",6:"Duraklatılıyor",
                7:"Duraklatıldı"
            }.get(int(status.state),"Durum bilinmiyor")
        finally:
            close(service)
    finally:
        close(manager)


def diagnostic_report(data_dir) -> list[str]:
    root=Path(data_dir)
    output=[]
    output.append("Windows Print Spooler: "+spooler_state())
    registration=PrintAgentStartup(root)
    output.append("Arka plan EXE: "+(
        "Kurulu" if registration.available else
        "Bu kurulum yolunda bulunamadı"))
    output.append("Windows oturum açılışında otomatik başlatma: "+(
        "Etkin" if registration.enabled() else "Devre dışı / farklı sürüm"))
    lease=None
    try:
        lease=PrintAgentLease(root)
        output.append("Bu kullanıcı oturumunda arka plan ajanı: "+
            ("Çalışıyor" if not lease.acquired else "Çalışmıyor"))
    except OSError as exc:
        output.append("Ajan kilidi okunamadı: "+str(exc)[:110])
    finally:
        if lease is not None:
            lease.close()
    data=read_collector_snapshot(root)
    if data:
        captured=str(data.get("captured_at") or "")
        try:
            past=datetime.fromisoformat(captured)
            if past.tzinfo is None:
                past=past.replace(tzinfo=timezone.utc)
            age=max(0, int((datetime.now(timezone.utc)-past).total_seconds()))
            output.append(
                "Son spool kontrolü: "+str(age)+
                " saniye önce"+(" (GÜNCEL)" if age<90 else " (ESKİ / incele)"))
        except ValueError:
            output.append("Son spool kontrolü: tarih okunamadı")
        printers=data.get("printers") or []
        output.append("Windows'ta görülen yazıcı sayısı: "+str(len(printers)))
        trouble=[str(p.get("name","?"))[:100] for p in printers
                 if p.get("error")]
        if trouble:
            output.append("Erişilemeyen yazıcılar: "+", ".join(trouble[:5]))
        output.append("Kayıtlı kitap baskı planı: "+str(len(data.get("tasks") or [])))
    else:
        output.append("İzleme anlık durumu bulunamadı (henüz açılmamış olabilir)")
    database=root/"print_monitor"/"print_history.sqlite3"
    if database.is_file():
        try:
            db=sqlite3.connect(str(database),timeout=2)
            try:
                db.execute("PRAGMA query_only=ON")
                output.append("Yerel SQLite geçmişi: erişilebilir")
            finally:
                db.close()
        except sqlite3.Error as exc:
            output.append("Yerel geçmiş veritabanı: "+str(exc)[:120])
    try:
        free=shutil.disk_usage(root).free//(1024**2)
        output.append("Yerel boş alan: "+str(free)+" MiB")
    except OSError:
        output.append("Yerel disk alanı okunamadı")
    output.append("")
    output.append("İzleme mevcut Windows hesabının izinleriyle çalışır.")
    output.append("Bilgisayar kapalıyken/oturum kapalıyken baskı izlenemez.")
    output.append("Windows kuyruk sayacı fiziksel PDF son sayfası değildir.")
    return output
