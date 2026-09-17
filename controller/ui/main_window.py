import sys
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QLabel,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QColor

from controller.config.settings import controller_settings
from controller.services.computer_service import computer_service
from controller.ui.dashboard import DashboardView
from controller.ui.computers import ComputersView
from controller.ui.computer_details import ComputerDetailsView
from controller.ui.activity import ActivityView
from controller.ui.settings import SettingsView


class StatusPollWorker(QThread):
    poll_finished = Signal()

    def run(self):
        computer_service.update_all_statuses()
        self.poll_finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Office Control Center (Controller)")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.init_ui()

        # Background Polling Timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.trigger_background_poll)
        self.poll_timer.start(controller_settings.refresh_interval_sec * 1000)
        self.trigger_background_poll()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(
            """
            QFrame {
                background-color: #1e293b;
                border-right: 1px solid #334155;
            }
            QPushButton {
                color: #94a3b8;
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
                border-radius: 6px;
                margin: 4px 10px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #334155;
            }
            QPushButton:checked {
                color: #ffffff;
                background-color: #2563eb;
            }
            """
        )
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 15, 0, 15)

        # App Brand
        brand_lbl = QLabel("LAN CONTROL")
        brand_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        brand_lbl.setStyleSheet("color: #ffffff; margin-left: 20px; margin-bottom: 20px;")
        sb_layout.addWidget(brand_lbl)

        # Navigation Buttons
        self.nav_btn_dashboard = QPushButton("  Dashboard")
        self.nav_btn_dashboard.setCheckable(True)
        self.nav_btn_dashboard.setChecked(True)
        self.nav_btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        sb_layout.addWidget(self.nav_btn_dashboard)

        self.nav_btn_computers = QPushButton("  Computers")
        self.nav_btn_computers.setCheckable(True)
        self.nav_btn_computers.clicked.connect(lambda: self.switch_page(1))
        sb_layout.addWidget(self.nav_btn_computers)

        self.nav_btn_activity = QPushButton("  Activity Log")
        self.nav_btn_activity.setCheckable(True)
        self.nav_btn_activity.clicked.connect(lambda: self.switch_page(3))
        sb_layout.addWidget(self.nav_btn_activity)

        self.nav_btn_settings = QPushButton("  Settings")
        self.nav_btn_settings.setCheckable(True)
        self.nav_btn_settings.clicked.connect(lambda: self.switch_page(4))
        sb_layout.addWidget(self.nav_btn_settings)

        sb_layout.addStretch()

        # Controller Identity Footer
        ctrl_info = QLabel(f"{controller_settings.controller_name}\n({controller_settings.controller_id})")
        ctrl_info.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 20px; margin-bottom: 10px;")
        sb_layout.addWidget(ctrl_info)

        main_layout.addWidget(sidebar)

        # --- Content Area (QStackedWidget) ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f8fafc;")

        self.dashboard_view = DashboardView()
        self.dashboard_view.open_details_signal.connect(self.open_computer_details)
        self.stack.addWidget(self.dashboard_view)  # Index 0

        self.computers_view = ComputersView()
        self.computers_view.open_details_signal.connect(self.open_computer_details)
        self.stack.addWidget(self.computers_view)  # Index 1

        self.details_view = ComputerDetailsView()
        self.details_view.back_signal.connect(lambda: self.switch_page(1))
        self.stack.addWidget(self.details_view)  # Index 2

        self.activity_view = ActivityView()
        self.stack.addWidget(self.activity_view)  # Index 3

        self.settings_view = SettingsView()
        self.stack.addWidget(self.settings_view)  # Index 4

        main_layout.addWidget(self.stack)

        self.setCentralWidget(main_widget)

    def switch_page(self, index: int):
        self.nav_btn_dashboard.setChecked(index == 0)
        self.nav_btn_computers.setChecked(index == 1 or index == 2)
        self.nav_btn_activity.setChecked(index == 3)
        self.nav_btn_settings.setChecked(index == 4)

        if index == 0:
            self.dashboard_view.load_data()
        elif index == 1:
            self.computers_view.load_computers()
        elif index == 3:
            self.activity_view.load_activities()

        self.stack.setCurrentIndex(index)

    def open_computer_details(self, agent_id: str):
        self.details_view.set_agent_id(agent_id)
        self.switch_page(2)

    def trigger_background_poll(self):
        self.poll_worker = StatusPollWorker()
        self.poll_worker.poll_finished.connect(self.on_poll_finished)
        self.poll_worker.start()

    def on_poll_finished(self):
        # Refresh current active view data if dashboard or computers list is showing
        curr = self.stack.currentIndex()
        if curr == 0:
            self.dashboard_view.load_data()
        elif curr == 1:
            self.computers_view.load_computers()
