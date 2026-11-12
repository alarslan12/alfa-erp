"""ALFACOPYCENTER — Windows user-session Print Surveillance supervisor.

Runs only after CURRENT USER logs in and explicitly enables startup via
the installer/app. No admin rights, Windows service changes, printer
commands, network credentials or PDF-content access.

Keeps AlfaPrintAgent alive with bounded restart attempts. If a remote printer
driver blocks WinSpool RPC for several minutes, only the helper subprocess
is restarted. The operating system's print queue is NEVER modified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from alfa_print_runtime import (
    PrintAgentLease, PrintAgentStartup, PrintSupervisorLease
)

POLL_SEC=15
FROZEN_TIMEOUT_SEC=360
MIN_RESTART_SEC=20
MAX_RESTART_SEC=120


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _snapshot_age(data_dir):
    file=Path(data_dir)/"print_monitor"/"print_history.sqlite3"
    if not file.is_file():
        return None
    try:
        db=sqlite3.connect(str(file),timeout=2)
        try:
            db.execute("PRAGMA query_only=ON")
            row=db.execute(
                "SELECT captured_at FROM collector_snapshot WHERE id=1"
            ).fetchone()
        finally:
            db.close()
        if not row:
            return None
        ts=datetime.fromisoformat(row[0])
        if ts.tzinfo is None:
            ts=ts.replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-ts).total_seconds())
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return None


def _log(data_dir,message):
    """Bounded local operational status only; never a PDF/document name."""
    try:
        root=Path(data_dir)/"print_monitor"
        root.mkdir(parents=True,exist_ok=True)
        target=root/"supervisor.log"
        if target.is_file() and target.stat().st_size>60*1024:
            target.replace(root/"supervisor.previous.log")
        with open(target,"a",encoding="utf-8") as out:
            out.write(_utc()+" "+str(message)[:140]+"\n")
    except OSError:
        pass


def _sleep(seconds):
    for _ in range(int(max(0,seconds))):
        time.sleep(1)


def main():
    if os.name!="nt":
        return 1
    if "--self-check" in sys.argv:
        # Offline build smoke test, no agent or printer started.
        root=Path(sys.executable).parent.parent
        # PyInstaller build: dist/AlfaPrintAgent/...
        # Installed suite: ALFACOPYCENTER/PrintAgent/...
        candidates=[
            root/"PrintAgent"/"AlfaPrintAgent.exe",
            root/"AlfaPrintAgent"/"AlfaPrintAgent.exe",
        ]
        if not any(path.is_file() for path in candidates):
            return 2
        return 0
    import argparse
    parser=argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data-dir",default=None)
    args=parser.parse_args()
    root=Path(args.data_dir or (
        Path(os.environ.get("LOCALAPPDATA") or Path.home())/"AlfaERP"
    )).resolve()
    startup=PrintAgentStartup(root)
    agent=startup.agent_executable
    if not agent.is_file():
        _log(root,"Missing AlfaPrintAgent.exe; supervisor not started")
        return 3
    lease=PrintSupervisorLease(root)
    if not lease.acquired:
        return 0

    child=None
    failures=0
    last_start=0.0
    try:
        _log(root,"User-session supervisor started")
        while True:
            # Respect user's in-app switch / HKCU Run preference.
            if not startup.enabled():
                _log(root,"User disabled Windows login print monitoring")
                break
            if child is not None and child.poll() is not None:
                _log(root,"Print agent stopped; restart will be attempted")
                child=None
                failures=min(failures+1,5)
            if child is None:
                # An ERP/standalone worker can own the print collection
                # lock; the AGENT mutex is separate from its own agent lease.
                active=PrintAgentLease(root)
                another_agent=not active.acquired
                active.close()
                if another_agent:
                    _sleep(POLL_SEC)
                    continue
                delay=min(MAX_RESTART_SEC,MIN_RESTART_SEC*(2**max(0,failures-1)))
                if last_start:
                    elapsed=time.monotonic()-last_start
                    if elapsed<delay:
                        _sleep(min(POLL_SEC,int(delay-elapsed)+1))
                        continue
                try:
                    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
                    child=subprocess.Popen(
                        [str(agent),"--data-dir",str(root)],
                        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,close_fds=True,
                        creationflags=flags)
                except OSError:
                    failures=min(failures+1,5)
                    _log(root,"Agent executable could not start")
                    _sleep(POLL_SEC)
                    continue
                last_start=time.monotonic()
                _log(root,"Print agent process launched")
                _sleep(POLL_SEC)
                continue
            # The agent records a heartbeat in SQLite at most once/minute.
            # No activity means either no printers or a hung driver; time
            # above 6 min suggests a stuck user-process, NOT spool deletion.
            if time.monotonic()-last_start>FROZEN_TIMEOUT_SEC:
                age=_snapshot_age(root)
                if age is None or age>FROZEN_TIMEOUT_SEC:
                    _log(root,"Stale collector: restarting only print-agent process")
                    child.terminate()
                    try:child.wait(timeout=6)
                    except subprocess.TimeoutExpired:child.kill()
                    child=None
                    failures=min(failures+1,5)
                    _sleep(POLL_SEC)
                    continue
                failures=0
            _sleep(POLL_SEC)
    except KeyboardInterrupt:
        pass
    finally:
        # When user disables the monitor, stop only OUR helper process.
        # No Windows spooler service/queue is modified.
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill()
        _log(root,"User-session supervisor exited")
        lease.close()
    return 0


if __name__=="__main__":
    sys.exit(main())
