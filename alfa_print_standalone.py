"""ALFACOPYCENTER Print Surveillance v2.0.0 — standalone Windows dashboard.

This is the user-facing print app. The separate AlfaPrintAgent.exe continues
collecting at the Windows user's sign-in when enabled. No administrator
elevation, spooler restart or job deletion is performed here.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QLabel, QHBoxLayout,
    QVBoxLayout, QWidget, QPushButton, QMessageBox
)
from ekran_yazdirma import PrintSurveillanceView
from alfa_print_diagnostics import diagnostic_report


APP_VERSION = "2.0.0"


def data_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "AlfaERP"


def bundled_icon() -> QIcon:
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for filename in ("assets/icons/alfa_print.ico",
                     "assets/branding/print.png"):
        path = bundle / filename
        if path.is_file():
            return QIcon(str(path))
    return QIcon()


class PrintWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALFACOPYCENTER · Yazdırma Kontrol Merkezi v" +
                            APP_VERSION)
        self.setMinimumSize(950, 640)
        self.resize(1510, 930)
        self.settings = QSettings("ALFACOPYCENTER", "PrintSurveillance")
        app = QApplication.instance()
        app.setProperty("alfa_theme",
            str(self.settings.value("theme", "koyu")))
        self.setWindowIcon(bundled_icon())

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        top = QHBoxLayout()
        title = QLabel("ALFACOPYCENTER  /  PRINT SURVEILLANCE  " +
                       APP_VERSION)
        title.setStyleSheet("font-weight:900;font-size:15px;")
        top.addWidget(title)
        top.addStretch()
        diagnostic=QPushButton("Sistem Kontrolü")
        diagnostic.setToolTip(
            "Windows Print Spooler, ajan, başlangıç ve SQLite geçmişini "
            "okur; izinleri veya yazdırma kuyruğunu değiştirmez.")
        diagnostic.clicked.connect(self.show_diagnostics)
        top.addWidget(diagnostic)
        update_button=QPushButton("Güncelleme Merkezi")
        update_button.setToolTip("Suite Personel, Yönetici, Banner Studio ve Print Center güncellemelerini denetler.")
        update_button.clicked.connect(self.open_update_center)
        top.addWidget(update_button)
        top.addWidget(QLabel("Tema"))
        themes = QComboBox()
        for label, key in (("Koyu", "koyu"), ("Açık", "acik"),
                           ("Yüksek kontrast", "kontrast")):
            themes.addItem(label, key)
        chosen = max(0, themes.findData(
            str(self.settings.value("theme", "koyu"))))
        themes.setCurrentIndex(chosen)
        themes.currentIndexChanged.connect(
            lambda: self.change_theme(str(themes.currentData())))
        top.addWidget(themes)
        root.addLayout(top)
        self.monitor = PrintSurveillanceView(data_directory(), self)
        self.monitor.notify.connect(
            lambda notice: self.statusBar().showMessage(
                str(notice)[:250], 14000))
        root.addWidget(self.monitor, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage(
            "Yerel Windows kuyrukları izleniyor. Fiziksel çıktı teyidi "
            "yazıcı telemetrisine ve operatör kontrolüne bağlıdır.")
        self.setStyleSheet("QMainWindow {background: #102033; color: #f3f8fe;}"
                           "QStatusBar {color: #d1e5f1;}")
        self.change_theme(str(themes.currentData()))

    def open_update_center(self):
        from suite_update_center import PrintSuiteUpdateDialog
        dialog=PrintSuiteUpdateDialog(self)
        dialog.exec()

    def change_theme(self, theme):
        theme = theme if theme in ("koyu", "acik", "kontrast") else "koyu"
        QApplication.instance().setProperty("alfa_theme", theme)
        self.settings.setValue("theme", theme)
        self.monitor.set_theme()
        colors = {
            "koyu": ("#102033", "#edf6ff"),
            "acik": ("#f5efe6", "#233b4d"),
            "kontrast": ("#05090f", "#ffffff"),
        }
        bg, fg = colors[theme]
        self.setStyleSheet(
            f"QMainWindow {{background:{bg};color:{fg};}}"
            f"QStatusBar {{color:{fg};background:{bg};}}"
            f"QLabel {{color:{fg};}}"
            f"QComboBox {{background:{bg};color:{fg};"
            "padding:5px;border:1px solid #6485a0;}}")

    def show_diagnostics(self):
        try:
            lines=diagnostic_report(data_directory())
            QMessageBox.information(
                self, "ALFACOPYCENTER · Yazdırma Sistem Kontrolü",
                "\\n".join(lines))
        except (OSError,ValueError) as exc:
            QMessageBox.warning(
                self,"Sistem Kontrolü",
                "Tanılama sırasında hata: "+str(exc)[:260])

    def closeEvent(self, event):
        self.monitor.stop()
        super().closeEvent(event)


def main() -> int:
    if os.name != "nt":
        print("ALFACOPYCENTER Print Surveillance requires Windows.")
        return 1
    if "--self-check" in sys.argv:
        # A Windows runner can verify the PyInstaller exe's imports and
        # SQLite schema without reading local printers or requiring elevation.
        import tempfile
        from alfa_print_plan import PrintPlanRepository
        with tempfile.TemporaryDirectory(prefix="alfa_print_selfcheck_") as root:
            repo=PrintPlanRepository(root)
            try:
                assert repo.list()==[]
                task=repo.create(printer="Fake local printer",book="Self-check",
                                 mode="SB",copies=1)
                assert repo.list()[0]["task_id"]==task
                repo.cancel_plan(task,"Self-check: no physical print")
            finally:
                repo.close()
        print("Print Surveillance standalone self-check OK")
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName("ALFACOPYCENTER Print Surveillance")
    app.setOrganizationName("ALFACOPYCENTER")
    window = PrintWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
