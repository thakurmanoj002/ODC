from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from controller.services.computer_service import computer_service
from controller.ui.dialogs.confirm_dialog import ConfirmDialog
from shared.models.responses import ActionResponse


class PowerActionWorker(QThread):
    action_completed = Signal(object)  # ActionResponse

    def __init__(self, action_type: str, agent_id: str):
        super().__init__()
        self.action_type = action_type
        self.agent_id = agent_id

    def run(self):
        if self.action_type == "LOCK":
            resp = computer_service.lock_pc(self.agent_id)
        elif self.action_type == "RESTART":
            resp = computer_service.restart_pc(self.agent_id)
        elif self.action_type == "SHUTDOWN":
            resp = computer_service.shutdown_pc(self.agent_id)
        else:
            resp = ActionResponse(success=False, request_id="", action="", message="Invalid action")
        self.action_completed.emit(resp)


class PowerControlPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Power Controls", parent)
        self.agent_id = None
        self.is_online = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.msg_lbl = QLabel("Manage remote computer power and workstation session state.")
        self.msg_lbl.setStyleSheet("color: #555555; font-size: 12px;")
        layout.addWidget(self.msg_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.lock_btn = QPushButton("Lock PC")
        self.lock_btn.setStyleSheet(
            "background-color: #f1f3f4; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 8px 16px; font-weight: bold;"
        )
        self.lock_btn.clicked.connect(self.lock_pc)
        btn_layout.addWidget(self.lock_btn)

        self.restart_btn = QPushButton("Restart PC")
        self.restart_btn.setStyleSheet(
            "background-color: #fef7e0; color: #b06000; border: 1px solid #fce8e6; border-radius: 4px; padding: 8px 16px; font-weight: bold;"
        )
        self.restart_btn.clicked.connect(self.restart_pc)
        btn_layout.addWidget(self.restart_btn)

        self.shutdown_btn = QPushButton("Shutdown PC")
        self.shutdown_btn.setStyleSheet(
            "background-color: #fce8e6; color: #c5221f; border: 1px solid #f8b4b0; border-radius: 4px; padding: 8px 16px; font-weight: bold;"
        )
        self.shutdown_btn.clicked.connect(self.shutdown_pc)
        btn_layout.addWidget(self.shutdown_btn)

        layout.addLayout(btn_layout)

    def set_computer(self, agent_id: str, is_online: bool, capabilities: list):
        self.agent_id = agent_id
        self.is_online = is_online

        has_lock = "LOCK_PC" in capabilities
        has_restart = "RESTART_PC" in capabilities
        has_shutdown = "SHUTDOWN_PC" in capabilities

        self.lock_btn.setEnabled(is_online and has_lock)
        self.restart_btn.setEnabled(is_online and has_restart)
        self.shutdown_btn.setEnabled(is_online and has_shutdown)

        if not is_online:
            self.msg_lbl.setText("Computer is OFFLINE. Power controls are disabled.")
        else:
            self.msg_lbl.setText("Select a power control action to execute on target computer.")

    def _set_buttons_enabled(self, enabled: bool):
        self.lock_btn.setEnabled(enabled and self.is_online)
        self.restart_btn.setEnabled(enabled and self.is_online)
        self.shutdown_btn.setEnabled(enabled and self.is_online)

    def lock_pc(self):
        if not self.agent_id or not self.is_online:
            return

        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Lock Workstation",
            message=f"Are you sure you want to lock computer '{self.agent_id}'?",
            confirm_btn_text="Lock Workstation",
        )
        if not confirmed:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Sending Lock PC request...")

        self.worker = PowerActionWorker("LOCK", self.agent_id)
        self.worker.action_completed.connect(self.on_power_action_completed)
        self.worker.start()

    def restart_pc(self):
        if not self.agent_id or not self.is_online:
            return

        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Restart Computer",
            message=f"Are you sure you want to restart computer '{self.agent_id}'?",
            warning_text="Warning: The computer will restart and the network connection may be temporarily lost.",
            confirm_btn_text="Restart Computer",
        )
        if not confirmed:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Sending Restart command...")

        self.worker = PowerActionWorker("RESTART", self.agent_id)
        self.worker.action_completed.connect(self.on_power_action_completed)
        self.worker.start()

    def shutdown_pc(self):
        if not self.agent_id or not self.is_online:
            return

        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Shut Down Computer",
            message=f"Are you sure you want to shut down computer '{self.agent_id}'?",
            warning_text="Warning: The computer will power off completely and will remain offline until manually turned on.",
            confirm_btn_text="Shut Down Computer",
        )
        if not confirmed:
            return

        self._set_buttons_enabled(False)
        self.msg_lbl.setText("Sending Shutdown command...")

        self.worker = PowerActionWorker("SHUTDOWN", self.agent_id)
        self.worker.action_completed.connect(self.on_power_action_completed)
        self.worker.start()

    def on_power_action_completed(self, resp: ActionResponse):
        self._set_buttons_enabled(True)
        if resp.success:
            QMessageBox.information(
                self,
                "Power Control Sent",
                f"{resp.message}\n\nNote: The computer status will update as it transitions offline.",
            )
            self.msg_lbl.setText(resp.message)
        else:
            QMessageBox.critical(self, "Power Control Failed", resp.message)
            self.msg_lbl.setText(f"Error: {resp.message}")
