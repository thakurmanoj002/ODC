from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class ConfirmDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        warning_text: str = "",
        confirm_btn_text: str = "Confirm",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(420, 220)
        self.init_ui(title, message, warning_text, confirm_btn_text)

    def init_ui(self, title: str, message: str, warning_text: str, confirm_btn_text: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(heading)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #333333; font-size: 13px;")
        layout.addWidget(msg_lbl)

        if warning_text:
            warn_lbl = QLabel(warning_text)
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet(
                "color: #c5221f; background-color: #fce8e6; border: 1px solid #f8b4b0; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 11px;"
            )
            layout.addWidget(warn_lbl)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_btn_text)
        confirm_btn.setStyleSheet(
            "background-color: #ea4335; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold;"
        )
        confirm_btn.clicked.connect(self.accept)
        btn_box.addWidget(confirm_btn)

        layout.addLayout(btn_box)

    @classmethod
    def confirm_action(
        cls,
        parent,
        title: str,
        message: str,
        warning_text: str = "",
        confirm_btn_text: str = "Confirm",
    ) -> bool:
        dlg = cls(title, message, warning_text, confirm_btn_text, parent)
        return dlg.exec() == QDialog.Accepted
