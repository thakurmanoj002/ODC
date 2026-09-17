from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from controller.config.settings import controller_settings


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        title = QLabel("Controller Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        # General Settings Group
        gen_group = QGroupBox("General & Network Settings")
        form = QFormLayout(gen_group)
        form.setSpacing(12)

        self.ctrl_id_lbl = QLabel(controller_settings.controller_id)
        self.ctrl_id_lbl.setStyleSheet("font-weight: bold; color: #1a73e8;")
        form.addRow("Controller ID:", self.ctrl_id_lbl)

        self.name_edit = QLineEdit(controller_settings.controller_name)
        form.addRow("Controller Display Name:", self.name_edit)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(3, 60)
        self.interval_spin.setValue(controller_settings.refresh_interval_sec)
        self.interval_spin.setSuffix(" seconds")
        form.addRow("Health Check Interval:", self.interval_spin)

        self.discovery_chk = QCheckBox("Enable UDP LAN Agent Discovery Scanner")
        self.discovery_chk.setChecked(controller_settings.discovery_enabled)
        form.addRow("LAN Discovery:", self.discovery_chk)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(controller_settings.theme)
        form.addRow("Appearance Theme:", self.theme_combo)

        layout.addWidget(gen_group)

        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 8px 20px; font-weight: bold;"
        )
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def save_settings(self):
        cname = self.name_edit.text().strip()
        if not cname:
            QMessageBox.warning(self, "Validation Error", "Controller display name cannot be empty.")
            return

        controller_settings.controller_name = cname
        controller_settings.refresh_interval_sec = self.interval_spin.value()
        controller_settings.discovery_enabled = self.discovery_chk.isChecked()
        controller_settings.theme = self.theme_combo.currentText()
        controller_settings.save()

        QMessageBox.information(self, "Success", "Settings saved successfully.")
