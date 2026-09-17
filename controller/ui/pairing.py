from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from controller.services.computer_service import computer_service


class AddComputerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add & Pair New Office Computer")
        self.setFixedSize(420, 320)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #202124; font-size: 13px; }
            QLineEdit {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 2px solid #1a73e8; }
            QPushButton {
                background-color: #f1f3f4;
                color: #202124;
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e8eaed; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Add Office Computer")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #1a73e8; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Enter target computer's IP address, port (8766), and 6-digit pairing code from Agent terminal.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #5f6368; font-size: 12px;")
        layout.addWidget(desc)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.ip_input = QLineEdit("127.0.0.1")
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("color: #202124; font-weight: bold;")
        form_layout.addRow(ip_label, self.ip_input)

        self.port_input = QLineEdit("8766")
        port_label = QLabel("Port:")
        port_label.setStyleSheet("color: #202124; font-weight: bold;")
        form_layout.addRow(port_label, self.port_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. 482913")
        code_label = QLabel("Pairing Code:")
        code_label.setStyleSheet("color: #202124; font-weight: bold;")
        form_layout.addRow(code_label, self.code_input)

        layout.addLayout(form_layout)

        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet("font-weight: bold; color: #1a73e8;")
        layout.addWidget(self.status_lbl)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.pair_btn = QPushButton("Connect & Pair")
        self.pair_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold;"
        )
        self.pair_btn.clicked.connect(self.perform_pairing)
        btn_box.addWidget(self.pair_btn)

        layout.addLayout(btn_box)

    def perform_pairing(self):
        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()
        code = self.code_input.text().strip()

        if not ip or not port_str or not code:
            QMessageBox.warning(self, "Validation Error", "Please fill in IP, Port, and Pairing Code.")
            return

        try:
            port = int(port_str)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Port must be a valid integer.")
            return

        self.status_lbl.setText("Connecting and verifying pairing code...")
        self.pair_btn.setEnabled(False)
        self.repaint()

        success, msg, comp = computer_service.pair_and_add_computer(ip, port, code)

        self.pair_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Pairing Successful", msg)
            self.accept()
        else:
            self.status_lbl.setText("")
            QMessageBox.critical(self, "Pairing Failed", msg)
