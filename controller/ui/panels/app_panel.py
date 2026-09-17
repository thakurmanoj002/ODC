from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from controller.services.computer_service import computer_service
from controller.ui.dialogs.confirm_dialog import ConfirmDialog
from shared.models.responses import ActionResponse


class AppActionWorker(QThread):
    action_completed = Signal(object)  # ActionResponse

    def __init__(self, action_type: str, agent_id: str, app_id: str = ""):
        super().__init__()
        self.action_type = action_type
        self.agent_id = agent_id
        self.app_id = app_id

    def run(self):
        if self.action_type == "GET_RUNNING":
            resp = computer_service.get_running_applications(self.agent_id)
        elif self.action_type == "START":
            resp = computer_service.start_allowed_application(self.agent_id, self.app_id)
        elif self.action_type == "STOP":
            resp = computer_service.stop_allowed_application(self.agent_id, self.app_id)
        else:
            resp = ActionResponse(success=False, request_id="", action="", message="Invalid action")
        self.action_completed.emit(resp)


class ApplicationControlPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Application & Process Controls", parent)
        self.agent_id = None
        self.is_online = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Status Header
        header_layout = QHBoxLayout()
        self.msg_lbl = QLabel("Manage allowed applications and running processes.")
        self.msg_lbl.setStyleSheet("color: #555555; font-size: 12px;")
        header_layout.addWidget(self.msg_lbl)
        header_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh Apps")
        self.refresh_btn.clicked.connect(self.refresh_applications)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # Section 1: Running Applications Table
        lbl_running = QLabel("Active Running Applications")
        lbl_running.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(lbl_running)

        self.running_table = QTableWidget(0, 5)
        self.running_table.setHorizontalHeaderLabels(["Application", "PID", "CPU %", "RAM (MB)", "Action"])
        self.running_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.running_table.verticalHeader().setDefaultSectionSize(38)
        self.running_table.setMinimumHeight(180)
        self.running_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.running_table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")
        layout.addWidget(self.running_table)

        # Section 2: Configured Allowed Applications Table
        lbl_allowed = QLabel("Configured Allowed Applications")
        lbl_allowed.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(lbl_allowed)

        self.allowed_table = QTableWidget(0, 4)
        self.allowed_table.setHorizontalHeaderLabels(["Application Name", "Executable", "Status", "Action"])
        self.allowed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.allowed_table.verticalHeader().setDefaultSectionSize(38)
        self.allowed_table.setMinimumHeight(200)
        self.allowed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.allowed_table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")
        layout.addWidget(self.allowed_table)

    def set_computer(self, agent_id: str, is_online: bool, capabilities: list):
        self.agent_id = agent_id
        self.is_online = is_online

        has_app_cap = (
            "GET_RUNNING_APPLICATIONS" in capabilities
            or "START_ALLOWED_APP" in capabilities
            or "STOP_ALLOWED_APP" in capabilities
        )

        if not has_app_cap:
            self.msg_lbl.setText("Application control is unavailable on this computer.")
            self.msg_lbl.setStyleSheet("color: #ea4335; font-weight: bold;")
            self.refresh_btn.setEnabled(False)
            self.running_table.setRowCount(0)
            self.allowed_table.setRowCount(0)
            return

        self.msg_lbl.setText("Manage allowed applications and running processes.")
        self.msg_lbl.setStyleSheet("color: #555555; font-size: 12px;")
        self.refresh_btn.setEnabled(is_online)

        if is_online:
            self.refresh_applications()

    def refresh_applications(self):
        if not self.agent_id or not self.is_online:
            return

        self.refresh_btn.setEnabled(False)
        self.msg_lbl.setText("Querying applications...")

        self.worker = AppActionWorker("GET_RUNNING", self.agent_id)
        self.worker.action_completed.connect(self.on_apps_retrieved)
        self.worker.start()

    def on_apps_retrieved(self, resp: ActionResponse):
        self.refresh_btn.setEnabled(self.is_online)
        if resp.success and resp.data:
            running_apps = resp.data.get("running_apps", [])
            allowed_apps = resp.data.get("allowed_apps", [])

            self.populate_running_table(running_apps)
            self.populate_allowed_table(allowed_apps, running_apps)
            self.msg_lbl.setText("Applications list updated.")
        else:
            self.msg_lbl.setText(f"Failed to fetch apps: {resp.message}")

    def populate_running_table(self, running_apps: list):
        self.running_table.setRowCount(0)
        for row_idx, app in enumerate(running_apps):
            self.running_table.insertRow(row_idx)

            self.running_table.setItem(row_idx, 0, QTableWidgetItem(app.get("name", "")))
            self.running_table.setItem(row_idx, 1, QTableWidgetItem(str(app.get("pid", ""))))
            self.running_table.setItem(row_idx, 2, QTableWidgetItem(f"{app.get('cpu_percent', 0.0)}%"))
            self.running_table.setItem(row_idx, 3, QTableWidgetItem(f"{app.get('memory_mb', 0.0)} MB"))

            stop_btn = QPushButton("Close App")
            stop_btn.setStyleSheet(
                "background-color: #fce8e6; color: #c5221f; border: 1px solid #f8b4b0; border-radius: 4px; padding: 4px 8px; font-weight: bold;"
            )
            app_id = app.get("app_id", "")
            app_name = app.get("name", "")
            stop_btn.clicked.connect(lambda checked=False, aid=app_id, name=app_name: self.confirm_stop_app(aid, name))
            self.running_table.setCellWidget(row_idx, 4, stop_btn)

    def populate_allowed_table(self, allowed_apps: list, running_apps: list):
        self.allowed_table.setRowCount(0)
        running_ids = {a.get("app_id") for a in running_apps}

        for row_idx, app in enumerate(allowed_apps):
            self.allowed_table.insertRow(row_idx)

            app_id = app.get("app_id", "")
            disp_name = app.get("display_name", "")
            exec_name = app.get("executable_name", "")
            enabled = app.get("enabled", True)

            self.allowed_table.setItem(row_idx, 0, QTableWidgetItem(disp_name))
            self.allowed_table.setItem(row_idx, 1, QTableWidgetItem(exec_name))

            # Status Badge
            if not enabled:
                status_item = QTableWidgetItem("● Disabled")
                status_item.setForeground(QColor("#ea4335"))
            elif app_id in running_ids:
                status_item = QTableWidgetItem("● Running")
                status_item.setForeground(QColor("#0f9d58"))
            else:
                status_item = QTableWidgetItem("○ Not Running")
                status_item.setForeground(QColor("#666666"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.allowed_table.setItem(row_idx, 2, status_item)

            # Start Action Button
            start_btn = QPushButton("Launch App")
            start_btn.setStyleSheet(
                "background-color: #e8f0fe; color: #1967d2; border: 1px solid #aecbfa; border-radius: 4px; padding: 4px 8px; font-weight: bold;"
            )
            start_btn.setEnabled(enabled and self.is_online)
            start_btn.clicked.connect(lambda checked=False, aid=app_id, name=disp_name: self.start_app(aid, name))
            self.allowed_table.setCellWidget(row_idx, 3, start_btn)

    def start_app(self, app_id: str, display_name: str):
        if not self.agent_id or not self.is_online:
            return

        self.refresh_btn.setEnabled(False)
        self.msg_lbl.setText(f"Launching '{display_name}'...")

        self.worker = AppActionWorker("START", self.agent_id, app_id)
        self.worker.action_completed.connect(self.on_app_action_completed)
        self.worker.start()

    def confirm_stop_app(self, app_id: str, display_name: str):
        if not self.agent_id or not self.is_online:
            return

        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Close Application",
            message=f"Are you sure you want to close application '{display_name}' on computer '{self.agent_id}'?",
            confirm_btn_text="Close Application",
        )
        if not confirmed:
            return

        self.refresh_btn.setEnabled(False)
        self.msg_lbl.setText(f"Stopping '{display_name}'...")

        self.worker = AppActionWorker("STOP", self.agent_id, app_id)
        self.worker.action_completed.connect(self.on_app_action_completed)
        self.worker.start()

    def on_app_action_completed(self, resp: ActionResponse):
        self.refresh_btn.setEnabled(self.is_online)
        if resp.success:
            QMessageBox.information(self, "Application Action", resp.message)
            self.refresh_applications()
        else:
            QMessageBox.critical(self, "Action Failed", resp.message)
            self.msg_lbl.setText(f"Error: {resp.message}")
