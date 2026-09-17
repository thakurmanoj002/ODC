import sys
import threading
import uvicorn
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon

from agent.config.settings import agent_settings
from agent.api.server import create_agent_app
from agent.network.discovery import DiscoveryResponder
from agent.system.network_info import get_local_ip
from agent.utils.logging_config import logger


class AgentSetupWindow(QMainWindow):
    def __init__(self, discovery_responder: DiscoveryResponder):
        super().__init__()
        self.discovery_responder = discovery_responder
        self.init_ui()

        # Timer to refresh status periodically
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_status_display)
        self.refresh_timer.start(3000)

    def init_ui(self):
        self.setWindowTitle("LAN Office Control Agent")
        self.setMinimumSize(460, 480)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        title_label = QLabel("LAN Office Control Agent")
        title_font = QFont("Segoe UI", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel("Background Administration Service (Windows)")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666666;")
        layout.addWidget(subtitle_label)

        # Info Group Box
        info_group = QGroupBox("Agent Information")
        form_layout = QFormLayout(info_group)
        form_layout.setSpacing(10)

        self.agent_id_label = QLabel(agent_settings.agent_id)
        self.agent_id_label.setStyleSheet("font-weight: bold; color: #1a73e8;")
        form_layout.addRow("Agent ID:", self.agent_id_label)

        self.name_edit = QLineEdit(agent_settings.computer_name)
        form_layout.addRow("Computer Name:", self.name_edit)

        self.ip_label = QLabel(get_local_ip())
        form_layout.addRow("Local IP:", self.ip_label)

        self.port_label = QLabel(str(agent_settings.server_port))
        form_layout.addRow("Port:", self.port_label)

        self.version_label = QLabel(agent_settings.agent_version)
        form_layout.addRow("Agent Version:", self.version_label)

        layout.addWidget(info_group)

        # Security & Pairing Group
        security_group = QGroupBox("Pairing & Authentication")
        sec_layout = QVBoxLayout(security_group)

        code_box = QHBoxLayout()
        code_title = QLabel("PAIRING CODE:")
        code_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        self.pairing_code_val = QLabel(agent_settings.pairing_code)
        self.pairing_code_val.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.pairing_code_val.setStyleSheet(
            "background-color: #e8f0fe; color: #1967d2; border-radius: 6px; padding: 4px 12px;"
        )
        code_box.addWidget(code_title)
        code_box.addSpacing(10)
        code_box.addWidget(self.pairing_code_val)
        code_box.addStretch()

        sec_layout.addLayout(code_box)

        self.status_badge = QLabel()
        self.update_status_display()
        sec_layout.addWidget(self.status_badge)

        layout.addWidget(security_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Display Name")
        save_btn.clicked.connect(self.save_name)
        btn_layout.addWidget(save_btn)

        regen_code_btn = QPushButton("Regenerate Code")
        regen_code_btn.clicked.connect(self.regenerate_code)
        btn_layout.addWidget(regen_code_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setCentralWidget(main_widget)

    def update_status_display(self):
        self.agent_id_label.setText(agent_settings.agent_id)
        self.pairing_code_val.setText(agent_settings.pairing_code)
        self.ip_label.setText(get_local_ip())

        if agent_settings.pairing_status == "PAIRED":
            self.status_badge.setText(
                f"Status: PAIRED with Controller ({agent_settings.trusted_controller_id or 'Unknown'})"
            )
            self.status_badge.setStyleSheet(
                "font-weight: bold; color: #0f9d58; padding: 6px; background-color: #e6f4ea; border-radius: 4px;"
            )
        else:
            self.status_badge.setText("Status: UNPAIRED (Ready for pairing)")
            self.status_badge.setStyleSheet(
                "font-weight: bold; color: #ea4335; padding: 6px; background-color: #fce8e6; border-radius: 4px;"
            )

    def save_name(self):
        new_name = self.name_edit.text().strip()
        if new_name:
            agent_settings.computer_name = new_name
            agent_settings.save()
            QMessageBox.information(self, "Success", "Computer display name updated.")

    def regenerate_code(self):
        agent_settings.pairing_code = agent_settings._generate_pairing_code()
        agent_settings.save()
        self.update_status_display()
        QMessageBox.information(
            self, "New Pairing Code", f"Generated new pairing code: {agent_settings.pairing_code}"
        )


def run_agent_server(app_fastapi, port: int):
    uvicorn.run(app_fastapi, host="0.0.0.0", port=port, log_level="warning")


def main():
    logger.info("Starting LAN Office Control Agent...")

    # Start UDP Discovery responder
    discovery_responder = DiscoveryResponder()
    discovery_responder.start()

    # Start FastAPI Server in background daemon thread
    fastapi_app = create_agent_app()
    server_thread = threading.Thread(
        target=run_agent_server,
        args=(fastapi_app, agent_settings.server_port),
        daemon=True,
    )
    server_thread.start()
    logger.info(f"Agent API server listening on 0.0.0.0:{agent_settings.server_port}")

    # Launch PySide6 GUI for agent setup/status
    app = QApplication(sys.argv)
    window = AgentSetupWindow(discovery_responder)
    window.show()

    ret = app.exec()
    discovery_responder.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()
