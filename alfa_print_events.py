"""Windows spooler change notifications (read-only).

Uses WinSpool's native change handles to wake a background collector without
continuous high-frequency polling. Remote print servers may suppress events;
bounded periodic reconciliation remains mandatory. Never run on the Qt GUI
thread. No Windows service configuration or privileges are changed.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time

MAX_NOTIFY_PRINTERS = 32             # Windows WaitForMultipleObjects limit is 64.
RECONCILE_MS = 20000                  # Network printers may not emit notifications.
FALLBACK_MS = 10000
PRINTER_CHANGES = (
    0x00000002 |  # PRINTER_CHANGE_SET_PRINTER
    0x00000100 |  # PRINTER_CHANGE_ADD_JOB
    0x00000200 |  # PRINTER_CHANGE_SET_JOB
    0x00000400 |  # PRINTER_CHANGE_DELETE_JOB
    0x00000800    # PRINTER_CHANGE_WRITE_JOB
)
_WAIT_FAILED = 0xFFFFFFFF


class WinPrintChangeFeed:
    """Owns printer and notification HANDLEs; caller owns the polling thread.

    OpenPrinter handles must outlive their notification handles. Close in the
    reverse order. A failed change registration never blocks the fallback
    queue reconciliation.
    """

    def __init__(self, probe):
        if os.name != "nt":
            raise RuntimeError("Windows yazıcı değişim bildirimleri Windows gerektirir.")
        self.probe = probe
        self.api = probe.api
        self.kernel = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        self.first = self.api.FindFirstPrinterChangeNotification
        self.first.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
        ]
        self.first.restype = wintypes.HANDLE
        self.next = self.api.FindNextPrinterChangeNotification
        self.next.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p, ctypes.c_void_p
        ]
        self.next.restype = wintypes.BOOL
        self.close_notification = self.api.FindClosePrinterChangeNotification
        self.close_notification.argtypes = [wintypes.HANDLE]
        self.close_notification.restype = wintypes.BOOL
        self.wait_many = self.kernel.WaitForMultipleObjects
        self.wait_many.argtypes = [
            wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
            wintypes.BOOL, wintypes.DWORD
        ]
        self.wait_many.restype = wintypes.DWORD
        self._watched = {}  # printer -> (printer HANDLE, change HANDLE)
        self._unavailable = set()
        self._retry_at = {}
        self._invalid = ctypes.c_void_p(-1).value
        self._total_printers = 0

    def _drop(self, name):
        item = self._watched.pop(name, None)
        if item is not None:
            ph, nh = item
            try:
                self.close_notification(nh)
            finally:
                self.api.ClosePrinter(ph)

    def close(self):
        for name in list(self._watched):
            self._drop(name)
        self._unavailable.clear()
        self._retry_at.clear()

    def sync(self, printer_names):
        """Update subscriptions after a normal full queue snapshot.

        Printer enumeration isn't itself event-driven (USB device arrival,
        network connection changes), so the periodic refresh also discovers
        newly added printers.
        """
        names = list(dict.fromkeys(str(name) for name in printer_names if name))
        self._total_printers = len(names)
        current = set(names)
        for name in tuple(self._watched):
            if name not in current:
                self._drop(name)
        self._unavailable.intersection_update(current)
        for old_name in list(self._retry_at):
            if old_name not in current:
                self._retry_at.pop(old_name,None)
        # Retry inaccessible remote servers at most every 90 seconds,
        # not on every reconciliation and not never.
        for name in names[:MAX_NOTIFY_PRINTERS]:
            if name in self._watched:
                continue
            if name in self._unavailable:
                if time.monotonic() < self._retry_at.get(name,0):
                    continue
                self._unavailable.discard(name)
            ph = wintypes.HANDLE()
            if not self.api.OpenPrinterW(name, ctypes.byref(ph), None):
                self._unavailable.add(name)
                self._retry_at[name]=time.monotonic()+90
                continue
            nh = self.first(ph, PRINTER_CHANGES, 0, None)
            if not nh or int(nh) == self._invalid:
                self.api.ClosePrinter(ph)
                self._unavailable.add(name)
                self._retry_at[name]=time.monotonic()+90
                continue
            self._retry_at.pop(name,None)
            self._watched[name] = (ph, nh)

    @property
    def has_fallback(self):
        """At least one printer lacks event notifications."""
        return bool(self._unavailable) or self._total_printers > len(self._watched)

    def wait(self, interrupt, timeout_ms=RECONCILE_MS):
        """Return True for a change event, False for timeout or failure.

        Waits in 500ms chunks so app shutdown remains responsive.
        This function performs no network writes and issues no spooler
        commands; it only resets the signalled notification object.
        """
        timeout_ms = max(0, min(int(timeout_ms), RECONCILE_MS))
        begin = time.monotonic()
        while not interrupt():
            elapsed = int((time.monotonic() - begin) * 1000)
            if elapsed >= timeout_ms:
                return False
            budget = min(500, timeout_ms - elapsed)
            names = list(self._watched)
            if not names:
                time.sleep(budget / 1000.0)
                continue
            handles = (wintypes.HANDLE * len(names))(
                *(self._watched[name][1] for name in names)
            )
            result = int(self.wait_many(len(handles), handles, False, budget))
            if 0 <= result < len(handles):
                name = names[result]
                changed = wintypes.DWORD()
                ok = self.next(self._watched[name][1],
                               ctypes.byref(changed), None, None)
                if not ok:
                    self._drop(name)
                    self._unavailable.add(name)
                    self._retry_at[name]=time.monotonic()+90
                return True
            if result == _WAIT_FAILED:
                # Avoid an invalid-handle busy loop; fallback snapshot can
                # still track the queue even when subscriptions fail.
                self.close()
                self._unavailable.update(names)
                for name in names:
                    self._retry_at[name]=time.monotonic()+90
                return False
        return False
