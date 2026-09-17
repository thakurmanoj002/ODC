from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from controller.services.computer_service import computer_service
from controller.ui.dialogs.confirm_dialog import ConfirmDialog
from shared.models.responses import ActionResponse


class WifiActionWorker(QThread):
    action_completed = Signal(object)  # ActionResponse

    def __init__(self, action_type: str, agent_id: str):
        super().__init__()
        self.action_type = action_type
        self.agent_id = agent_id

    def run(self):
        if self.action_type == "STATUS":
            resp = computer_service.get_wifi_status(self.agent_id)
        elif self.action_type == "ON":
            resp = computer_service.wifi_on(self.agent_id)
        elif self.action_type == "OFF":
            resp = computer_service.wifi_off(self.agent_id)
        else:
            resp = ActionResponse(success=False, request_id="", action="", message="Invalid action")
        self.action_completed.emit(resp)


class WifiControlPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Wi-Fi Network Controls", parent)
        self.agent_id = None
        self.is_online = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()

        self.status_lbl = QLabel("UNKNOWN")
        self.status_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        form.addRow("Wi-Fi Status:", self.status_lbl)

        self.ssid_lbl = QLabel("--")
        form.addRow("Connected SSID:", self.ssid_lbl)

        self.adapter_lbl = QLabel("--")
        form.addRow("Wireless Adapter:", self.adapter_lbl)

        layout.addLayout(form)

        self.msg_lbl = QLabel()
        self.msg_lbl.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(self.msg_lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.clicked.connect(self.refresh_status)
        btn_layout.addWidget(self.refresh_btn)

        self.wifi_on_btn = QPushButton("Turn Wi-Fi ON")
        self.wifi_on_btn.setStyleSheet(
            "background-color: #e6f4ea; color: #0f9d58; border: 1px solid #34a853; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
        )
        self.wifi_on_btn.clicked.connect(self.turn_on_wifi)
        btn_layout.addWidget(self.wifi_on_btn)

        self.wifi_off_btn = QPushButton("Turn Wi-Fi OFF")
        self.wifi_off_btn.setStyleSheet(
            "background-color: #fce8e6; color: #ea4335; border: 1px solid #ea4335; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
        )
        self.wifi_off_btn.clicked.connect(self.turn_off_wifi)
        btn_layout.addWidget(self.wifi_off_btn)

        layout.addLayout(btn_layout)

    def set_computer(self, agent_id: str, is_online: bool, capabilities: list):
        self.agent_id = agent_id
        self.is_online = is_online

        has_wifi_cap = "WIFI_STATUS" in capabilities or "WIFI_ON" in capabilities or "WIFI_OFF" in capabilities

        if not has_wifi_cap:
            self.msg_lbl.setText("Wi-Fi control is unavailable on this computer.")
            self.msg_lbl.setStyleSheet("color: #ea4335; font-weight: bold;")
            self.status_lbl.setText("UNAVAILABLE")
            self.status_lbl.setStyleSheet("color: #999999;")
            self.wifi_on_btn.setEnabled(False)
            self.wifi_off_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            return

        self.msg_lbl.setText("")
        self.wifi_on_btn.setEnabled(is_online)
        self.wifi_off_btn.setEnabled(is_online)
        self.refresh_btn.setEnabled(is_online)

        if is_online:
            self.refresh_status()

    def _set_buttons_enabled(self, enabled: bool):
        self.wifi_on_btn.setEnabled(enabled and self.is_online)
        self.wifi_off_btn.setEnabled(enabled and self.is_online)
        self.refresh_btn.setEnabled(enabled and self.is_online)

    def refresh_status(self):
        if not self.agent_id or not self.is_online:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Querying Wi-Fi status...")

        self.worker = WifiActionWorker("STATUS", self.agent_id)
        self.worker.action_completed.connect(self.on_status_retrieved)
        self.worker.start()

    def on_status_retrieved(self, resp: ActionResponse):
        self._set_buttons_enabled(True)
        if resp.success and resp.data:
            state = resp.data.get("state", "UNKNOWN")
            ssid = resp.data.get("ssid") or "Not Connected"
            adapter = resp.data.get("adapter") or "Wireless Adapter"

            self.status_lbl.setText(state)
            if state == "CONNECTED":
                self.status_lbl.setStyleSheet("color: #0f9d58; font-weight: bold;")
            elif state == "DISABLED":
                self.status_lbl.setStyleSheet("color: #ea4335; font-weight: bold;")
            else:
                self.status_lbl.setStyleSheet("color: #f4b400; font-weight: bold;")

            self.ssid_lbl.setText(ssid)
            self.adapter_lbl.setText(adapter)
            self.msg_lbl.setText("Status updated successfully.")
        else:
            self.status_lbl.setText("UNAVAILABLE")
            self.status_lbl.setStyleSheet("color: #ea4335; font-weight: bold;")
            self.msg_lbl.setText(resp.message)

    def turn_on_wifi(self):
        if not self.agent_id or not self.is_online:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Enabling Wi-Fi adapter...")

        self.worker = WifiActionWorker("ON", self.agent_id)
        self.worker.action_completed.connect(self.on_wifi_action_completed)
        self.worker.start()

    def turn_off_wifi(self):
        if not self.agent_id or not self.is_online:
            return

        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Turn Off Wi-Fi",
            message=f"Are you sure you want to turn off Wi-Fi on computer '{self.agent_id}'?",
            warning_text="Warning: Disabling Wi-Fi may cause connection loss if this PC relies on Wi-Fi for LAN communication.",
            confirm_btn_text="Turn Off Wi-Fi",
        )

        if not confirmed:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Disabling Wi-Fi adapter...")

        self.worker = WifiActionWorker("OFF", self.agent_id)
        self.worker.action_completed.connect(self.on_wifi_action_completed)
        self.worker.start()

    def on_wifi_action_completed(self, resp: ActionResponse):
        self._set_buttons_enabled(True)
        if resp.success:
            QMessageBox.information(self, "Wi-Fi Control", resp.message)
            self.refresh_status()
        else:
            QMessageBox.critical(self, "Wi-Fi Control Failed", resp.message)
            self.msg_lbl.setText(f"Error: {resp.message}")
