"""Themed, accessible multi-line refund-reason input.

QInputDialog.getMultiLineText used the Windows white QPlainTextEdit palette
with inherited light text. This form explicitly styles both palettes.
"""
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout,
)


class ReturnReasonDialog(QDialog):
    def __init__(self, order_id, initial="", parent=None):
        super().__init__(parent)
        self.setObjectName("ReturnReasonDialog")
        self.setWindowTitle("ALFA ERP · İade sebebi")
        self.setMinimumWidth(470)
        self.setModal(True)
        light=str(QApplication.instance().property("alfa_theme") or "koyu")=="acik"
        bg,fg,field,border=(
            ("#faf8f3","#20374b","#ffffff","#879eb0") if light else
            ("#152235","#f2f8ff","#1e334c","#5f84a8")
        )
        self.setStyleSheet(
            "QDialog#ReturnReasonDialog {background:"+bg+";color:"+fg+";}"
            "QDialog#ReturnReasonDialog QLabel{background:transparent;color:"+fg+";font-size:12px;}"
            "QDialog#ReturnReasonDialog QPlainTextEdit{background:"+field+
            ";color:"+fg+";border:1px solid "+border+
            ";border-radius:8px;padding:9px;selection-background-color:#2872ad;}"
            "QDialog#ReturnReasonDialog QPushButton{background:"+field+
            ";color:"+fg+";border:1px solid "+border+
            ";border-radius:7px;padding:8px 16px;min-width:80px;}"
            "QDialog#ReturnReasonDialog QPushButton:hover{border:1px solid #79b9ec;}"
        )
        wrap=QVBoxLayout(self)
        wrap.setContentsMargins(18,18,18,16)
        wrap.setSpacing(12)
        label=QLabel("Sipariş #"+str(order_id)+" · İade sebebini yazın (1–500 karakter)")
        label.setWordWrap(True)
        wrap.addWidget(label)
        self.edit=QPlainTextEdit(str(initial or ""))
        self.edit.setPlaceholderText("İade gerekçesini girin…")
        self.edit.setFixedHeight(165)
        wrap.addWidget(self.edit)
        self.counter=QLabel("")
        wrap.addWidget(self.counter)
        buttons=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Kaydet")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        wrap.addWidget(buttons)
        self.edit.textChanged.connect(self._update_counter)
        self._update_counter()

    def _update_counter(self):
        value=" ".join(self.edit.toPlainText().split())
        count=len(value)
        self.counter.setText(str(count)+" / 500 karakter")
        self.counter.setStyleSheet(
            "color:#d15a69;" if count<1 or count>500 else "color:#4dc6a4;"
        )
        self.findChild(QDialogButtonBox).button(
            QDialogButtonBox.StandardButton.Ok
        ).setEnabled(1<=count<=500)

    @property
    def reason(self):
        return " ".join(self.edit.toPlainText().split())


def request_return_reason(parent, order_id, initial=""):
    dialog=ReturnReasonDialog(order_id, initial, parent)
    if dialog.exec()!=QDialog.DialogCode.Accepted:
        return "",False
    return dialog.reason,True
