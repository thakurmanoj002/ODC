from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from controller.database.database import db
from controller.services.computer_service import computer_service
from controller.ui.panels.system_panel import SystemMetricsPanel
from controller.ui.panels.network_panel import NetworkInfoPanel
from controller.ui.panels.wifi_panel import WifiControlPanel
from controller.ui.panels.power_panel import PowerControlPanel
from controller.ui.panels.app_panel import ApplicationControlPanel
from controller.ui.panels.files_panel import FileManagerPanel
from shared.models.responses import SystemInfoResponse, NetworkInfoResponse


class FetchInfoWorker(QThread):
    info_fetched = Signal(object, object, str)  # sys_info, net_info, error_msg

    def __init__(self, ip: str, port: int, token: str):
        super().__init__()
        self.ip = ip
        self.port = port
        self.token = token

    def run(self):
        sys_info = None
        net_info = None
        err = ""
        try:
            from controller.services.agent_client import agent_client
            sys_info = agent_client.get_system_info(self.ip, self.port, self.token)
            net_info = agent_client.get_network_info(self.ip, self.port, self.token)
        except Exception as e:
            err = str(e)
        if not sys_info:
            err = "Failed to communicate with Agent. Check if computer is Online."
        self.info_fetched.emit(sys_info, net_info, err)


class ComputerDetailsView(QWidget):
    back_signal = Signal()

    def __init__(self):
        super().__init__()
        self.agent_id = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for responsive scaling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top Nav Bar
        top_nav = QHBoxLayout()
        back_btn = QPushButton("← Back to Computers")
        back_btn.clicked.connect(self.back_signal.emit)
        top_nav.addWidget(back_btn)
        top_nav.addStretch()

        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 6px 14px; font-weight: bold;"
        )
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_nav.addWidget(self.refresh_btn)

        layout.addLayout(top_nav)

        # Header Info Card
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;")
        h_layout = QHBoxLayout(header_card)

        v_info = QVBoxLayout()
        self.title_lbl = QLabel("Computer Details")
        self.title_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        v_info.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel("IP: -- | Agent ID: --")
        self.subtitle_lbl.setStyleSheet("color: #666666;")
        v_info.addWidget(self.subtitle_lbl)

        h_layout.addLayout(v_info)
        h_layout.addStretch()

        self.status_badge = QLabel("OFFLINE")
        self.status_badge.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.status_badge.setStyleSheet(
            "padding: 6px 14px; background-color: #fce8e6; color: #ea4335; border-radius: 4px;"
        )
        h_layout.addWidget(self.status_badge)

        layout.addWidget(header_card)

        # Modular Feature Panels
        self.power_panel = PowerControlPanel()
        layout.addWidget(self.power_panel)

        self.wifi_panel = WifiControlPanel()
        layout.addWidget(self.wifi_panel)

        self.app_panel = ApplicationControlPanel()
        layout.addWidget(self.app_panel)

        self.files_panel = FileManagerPanel()
        layout.addWidget(self.files_panel)

        self.sys_panel = SystemMetricsPanel()
        layout.addWidget(self.sys_panel)

        self.net_panel = NetworkInfoPanel()
        layout.addWidget(self.net_panel)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_agent_id(self, agent_id: str):
        self.agent_id = agent_id
        self.refresh_data()

    def refresh_data(self):
        if not self.agent_id:
            return

        comp = db.get_computer_by_agent_id(self.agent_id)
        if not comp:
            QMessageBox.warning(self, "Error", "Computer record not found.")
            return

        self.title_lbl.setText(comp.display_name)
        self.subtitle_lbl.setText(f"IP: {comp.ip_address}:{comp.port} | Agent ID: {comp.agent_id}")

        is_online = (comp.status == "ONLINE")

        if is_online:
            self.status_badge.setText("ONLINE")
            self.status_badge.setStyleSheet(
                "padding: 6px 14px; background-color: #e6f4ea; color: #0f9d58; border-radius: 4px;"
            )
        else:
            self.status_badge.setText("OFFLINE")
            self.status_badge.setStyleSheet(
                "padding: 6px 14px; background-color: #fce8e6; color: #ea4335; border-radius: 4px;"
            )

        capabilities = db.get_computer_capabilities(self.agent_id)

        # Configure Modular Panels
        self.wifi_panel.set_computer(self.agent_id, is_online, capabilities)
        self.power_panel.set_computer(self.agent_id, is_online, capabilities)
        self.app_panel.set_computer(self.agent_id, is_online, capabilities)
        self.files_panel.set_computer(self.agent_id, is_online, capabilities)

        if not comp.auth_token:
            QMessageBox.warning(self, "Unpaired", "This computer is not paired yet.")
            return

        if is_online:
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Loading...")

            self.worker = FetchInfoWorker(comp.ip_address, comp.port, comp.auth_token)
            self.worker.info_fetched.connect(self.on_info_fetched)
            self.worker.start()

    def on_info_fetched(self, sys_info: SystemInfoResponse, net_info: NetworkInfoResponse, error_msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Status")

        if sys_info:
            db.update_computer_status(self.agent_id, "ONLINE")
            self.status_badge.setText("ONLINE")
            self.status_badge.setStyleSheet(
                "padding: 6px 14px; background-color: #e6f4ea; color: #0f9d58; border-radius: 4px;"
            )
            self.sys_panel.update_metrics(sys_info)
        else:
            db.update_computer_status(self.agent_id, "OFFLINE")
            self.status_badge.setText("OFFLINE")
            self.status_badge.setStyleSheet(
                "padding: 6px 14px; background-color: #fce8e6; color: #ea4335; border-radius: 4px;"
            )

        if net_info:
            self.net_panel.update_info(net_info)
