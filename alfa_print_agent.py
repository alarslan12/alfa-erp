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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from alfa_print_monitor import PrintMonitor


def main():
    if os.name != "nt":
        return 1
    parser=argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data-dir",type=str,default=None)
    args=parser.parse_args()
    folder=Path(args.data_dir or (
        Path(os.environ.get("LOCALAPPDATA") or Path.home())/"AlfaERP"
    )).expanduser()

    app=QApplication(["AlfaPrintAgent"])
    app.setApplicationName("ALFA ERP Yazdırma İzleme")
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        # No hidden, uncontrollable monitor if desktop tray is unavailable.
        return 2

    icon_file=Path(getattr(sys,"_MEIPASS",Path(__file__).parent)) / (
        "assets/icons/alfa_personel.ico"
    )
    icon=QIcon(str(icon_file)) if icon_file.exists() else QIcon()
    if icon.isNull():
        icon=app.style().standardIcon(
            QStyle.StandardPixmap.SP_ComputerIcon)

    tray=QSystemTrayIcon(icon)
    tray.setToolTip("ALFA ERP · Yazdırma izleme etkin")
    menu=QMenu()
    title=QAction("ALFA ERP Yazdırma Kontrol Merkezi",menu)
    title.setEnabled(False)
    menu.addAction(title)
    menu.addSeparator()
    stop=QAction("Bu oturumda izlemeyi durdur",menu)
    stop.triggered.connect(app.quit)
    menu.addAction(stop)
    tray.setContextMenu(menu)
    tray.show()

    worker=PrintMonitor(folder)
    worker.warning.connect(lambda message:tray.showMessage(
        "ALFA ERP · Yazdırma",str(message)[:240],
        QSystemTrayIcon.MessageIcon.Warning,8000))
    worker.failed.connect(lambda message:tray.setToolTip(
        "ALFA ERP · Yazıcı izleme: "+str(message)[:120]))
    worker.start()

    def cleanup():
        worker.requestInterruption()
        # Unreachable remote spooler RPC can block this worker. Waiting
        # indefinitely would prevent Windows logout. The OS will tear
        # down this user process; SQLite's WAL preserves committed rows.
        worker.wait(3500)
        tray.hide()

    app.aboutToQuit.connect(cleanup)
    return app.exec()


if __name__=="__main__":
    sys.exit(main())
