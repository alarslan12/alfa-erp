"""Banner Studio process ownership and browser-tab lifetime.

The HTTP server belongs to a single Windows process; the browser is just a
client. Closing the last editor tab must not leave a windowless EXE behind.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from urllib.request import urlopen


class BrowserSessions:
    def __init__(self, clock=None, startup_timeout=120, close_grace=12,
                 heartbeat_timeout=900):
        import threading
        self.clock = clock or time.monotonic
        self.startup_timeout = startup_timeout
        self.close_grace = close_grace
        self.heartbeat_timeout = heartbeat_timeout
        self.started = self.clock()
        self.seen = False
        self.sessions = {}
        self.empty_since = None
        self.lock = threading.RLock()

    def event(self, client_id: str, action: str) -> None:
        with self.lock:
            now = self.clock()
            if action == "open":
                self.sessions[client_id] = now
                self.seen = True
                self.empty_since = None
            elif action == "heartbeat":
                # An in-flight heartbeat after a tab's close must not revive it.
                if client_id in self.sessions:
                    self.sessions[client_id] = now
            elif action == "closed":
                self.sessions.pop(client_id, None)
                if self.seen and not self.sessions and self.empty_since is None:
                    self.empty_since = now
            else:
                raise ValueError("Unknown studio presence action")

    def should_exit(self) -> bool:
        with self.lock:
            now = self.clock()
            for client_id, last in list(self.sessions.items()):
                if now - last > self.heartbeat_timeout:
                    del self.sessions[client_id]
            if self.sessions:
                self.empty_since = None
                return False
            if not self.seen:
                return now - self.started >= self.startup_timeout
            if self.empty_since is None:
                self.empty_since = now
            return now - self.empty_since >= self.close_grace


class SingleStudio:
    """OS mutex releases on process termination (including forced termination)."""
    def __init__(self):
        self.kernel = None
        self.handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        import ctypes
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = self.kernel.CreateMutexW
        create.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        create.restype = ctypes.c_void_p
        self.handle = create(None, False, r"Local\ALFACOPYCENTER_BannerStudio_Pro")
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        return error != 183  # ERROR_ALREADY_EXISTS

    def close(self) -> None:
        if self.handle:
            import ctypes
            self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def write_active_server(path: Path, port: int) -> None:
    payload = {"app": "ALFA Banner Studio Pro", "pid": os.getpid(), "port": port}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, path)


def remove_active_server(path: Path, port: int) -> None:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("pid") == os.getpid() and saved.get("port") == port:
            path.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass


def open_existing_studio(path: Path, open_browser, *, attempts=24, wait=0.25) -> bool:
    """Only open a port after verifying it's our own running application."""
    for attempt in range(attempts):
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            port = int(saved["port"])
            if not 1 <= port <= 65535:
                raise ValueError("Invalid local port")
            url = f"http://127.0.0.1:{port}"
            with urlopen(url + "/api/studio/info", timeout=1.2) as response:
                identity = json.load(response)
            if (identity.get("app") == "ALFA Banner Studio Pro" and
                    identity.get("pid") == saved.get("pid") and
                    identity.get("port") == port):
                open_browser(url)
                return True
        except (OSError, ValueError, TypeError, KeyError):
            if attempt + 1 < attempts:
                time.sleep(wait)
    return False
