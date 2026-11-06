"""One local Windows print collector per ALFA ERP data directory.

A per-Windows-session named mutex prevents the ERP, another ERP window and
the optional tray agent from repeatedly polling the same spooler and writing
duplicate history. Registry autostart is opt-in under CURRENT USER only.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import subprocess
import sys

if os.name == "nt":
    import winreg
else:
    winreg = None

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_NAME = "ALFA_ERP_Print_Monitor"


class PrintCollectorLease:
    def __init__(self, data_dir, prefix="ALFA_ERP_PRINT_"):
        self.acquired=False
        self.handle=None
        if os.name != "nt":
            return
        digest=hashlib.sha256(
            str(Path(data_dir).resolve()).casefold().encode("utf-8")
        ).hexdigest()[:24]
        name="Local\\"+str(prefix)+digest
        self.kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[
            ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype=wintypes.HANDLE
        self.kernel.ReleaseMutex.argtypes=[wintypes.HANDLE]
        self.kernel.ReleaseMutex.restype=wintypes.BOOL
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.kernel.CloseHandle.restype=wintypes.BOOL
        ctypes.set_last_error(0)
        handle=self.kernel.CreateMutexW(None,True,name)
        if not handle:
            raise OSError("Yazdırma izleme kilidi açılamadı (Win32 %d)." %
                          ctypes.get_last_error())
        if ctypes.get_last_error()==183:  # ERROR_ALREADY_EXISTS
            self.kernel.CloseHandle(handle)
            return
        self.handle=handle
        self.acquired=True

    def close(self):
        if self.handle:
            if self.acquired:
                self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle=None
            self.acquired=False


class PrintAgentLease(PrintCollectorLease):
    """Only one tray-agent process per user data folder and Windows session."""

    def __init__(self,data_dir):
        super().__init__(data_dir,prefix="ALFA_ERP_AGENT_")


class PrintAgentStartup:
    """HKCU only; no admin elevation, service or machine-wide Run keys."""

    def __init__(self, data_dir):
        self.data_dir=Path(data_dir)
        self.executable=(Path(sys.executable).parent/"PrintAgent"/"AlfaPrintAgent.exe")

    @property
    def available(self):
        return os.name=="nt" and self.executable.is_file()

    def _command(self):
        return subprocess.list2cmdline(
            [str(self.executable), "--data-dir", str(self.data_dir)])

    def enabled(self):
        if not self.available:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY) as key:
                stored,kind=winreg.QueryValueEx(key,STARTUP_NAME)
                return kind==winreg.REG_SZ and stored==self._command()
        except OSError:
            return False

    def set_enabled(self, enabled):
        if os.name!="nt":
            raise OSError("Windows oturum başlatma özelliği Windows gerektirir.")
        if enabled and not self.available:
            raise FileNotFoundError(
                "AlfaPrintAgent.exe bulunamadı. Eklenti henüz kurulmamış.")
        if enabled:
            with winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                    winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(
                    key,STARTUP_NAME,0,winreg.REG_SZ,self._command())
            # Start now too: the user requested it via the UI. The named
            # mutex guarantees no duplicate collector if ERP is already open.
            flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
            subprocess.Popen(
                [str(self.executable),"--data-dir",str(self.data_dir)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                close_fds=True,creationflags=flags
            )
            return
        try:
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                    winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key,STARTUP_NAME)
        except FileNotFoundError:
            pass
        # The currently running agent can be stopped from its tray menu.
        # Deleting Run does not kill a process or alter the Windows spooler.
