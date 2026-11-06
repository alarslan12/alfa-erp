"""ALFA ERP Print Surveillance - optional user-session tray agent.

No elevation, no Windows service installation, no Firebase or network cloud
access. Installed beside the ERP executable; autostart requires the user's
explicit opt-in from Yazdırma Kontrol Merkezi.

The PrintMonitor named mutex allows this agent to take over after the ERP
closes (or wait without double-collecting while ERP remains open).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from alfa_print_monitor import PrintMonitor
from alfa_print_runtime import PrintAgentLease


def main():
    if os.name != "nt":
        return 1
    parser=argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data-dir",type=str,default=None)
    args=parser.parse_args()
    folder=Path(args.data_dir or (
        Path(os.environ.get("LOCALAPPDATA") or Path.home())/"AlfaERP"
    )).expanduser()
    instance_lock=PrintAgentLease(folder)
    if not instance_lock.acquired:
        # A previous login agent already owns this Windows session.
        return 0

    app=QApplication(["AlfaPrintAgent"])
    app.setApplicationName("ALFA ERP Yazdırma İzleme")
    app.setQuitOnLastWindowClosed(False)
    # Some kiosk/remote Windows sessions don't expose the notification area.
    # Collection MUST still continue; the standalone Print Surveillance app
    # can inspect the same SQLite journal and change the startup preference.
    has_tray=QSystemTrayIcon.isSystemTrayAvailable()

    icon_file=Path(getattr(sys,"_MEIPASS",Path(__file__).parent)) / (
        "assets/icons/alfa_print.ico"
    )
    icon=QIcon(str(icon_file)) if icon_file.exists() else QIcon()
    if icon.isNull():
        icon=app.style().standardIcon(
            QStyle.StandardPixmap.SP_ComputerIcon)

    tray=QSystemTrayIcon(icon) if has_tray else None
    if tray is not None:
        tray.setToolTip("ALFACOPYCENTER · Yazdırma izleme etkin")
    menu=QMenu()
    title=QAction("ALFA ERP Yazdırma Kontrol Merkezi",menu)
    title.setEnabled(False)
    menu.addAction(title)
    menu.addSeparator()
    stop=QAction("Bu oturumda izlemeyi durdur",menu)
    stop.triggered.connect(app.quit)
    menu.addAction(stop)
    if tray is not None:
        tray.setContextMenu(menu)
        tray.show()

    current={"worker":None,"last_data":None,"failed":""}
    def begin_worker():
        worker=PrintMonitor(folder)
        if tray is not None:
            worker.warning.connect(lambda message:tray.showMessage(
                "ALFACOPYCENTER · Yazdırma",str(message)[:240],
                QSystemTrayIcon.MessageIcon.Warning,8000))
            worker.failed.connect(lambda message:tray.setToolTip(
                "ALFACOPYCENTER · Yazıcı izleme: "+str(message)[:100]))
        worker.failed.connect(lambda message:
            current.__setitem__("failed",str(message)[:180]))
        worker.updated.connect(lambda payload:
            current.__setitem__("last_data",payload.get("captured_at")))
        current["worker"]=worker
        worker.start()

    begin_worker()
    watchdog=QTimer()
    watchdog.setInterval(18000)
    def check_worker():
        worker=current["worker"]
        if worker is None or worker.isRunning():
            return
        # Restart only a FINISHED Qt worker. Stuck Windows printer RPCs
        # must not be forcibly terminated from the GUI thread.
        worker.deleteLater()
        begin_worker()
    watchdog.timeout.connect(check_worker)
    watchdog.start()

    def cleanup():
        watchdog.stop()
        worker=current["worker"]
        if worker is None:
            if tray is not None:tray.hide()
            return
        worker.requestInterruption()
        # Unreachable remote spooler RPC can block this worker. Waiting
        # indefinitely would prevent Windows logout. The OS will tear
        # down this user process; SQLite's WAL preserves committed rows.
        ended=worker.wait(3500)
        if tray is not None:tray.hide()
        if not ended:
            # A stalled remote printer RPC cannot be safely interrupted.
            # End only this optional helper process; committed SQLite
            # transactions survive via WAL and the Windows spooler is not
            # touched. Avoid destroying a still-running QThread in Qt.
            os._exit(0)

    app.aboutToQuit.connect(cleanup)
    try:
        return app.exec()
    finally:
        instance_lock.close()


if __name__=="__main__":
    sys.exit(main())
