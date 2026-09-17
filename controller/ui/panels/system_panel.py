from PySide6.QtWidgets import QWidget, QGroupBox, QFormLayout, QProgressBar, QLabel
from PySide6.QtCore import Qt
from shared.models.responses import SystemInfoResponse


class SystemMetricsPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Live System Metrics", parent)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #1a73e8; }")
        layout.addRow("CPU Usage:", self.cpu_bar)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #0f9d58; }")
        layout.addRow("RAM Usage:", self.ram_bar)

        self.ram_detail_lbl = QLabel("-- GB / -- GB")
        layout.addRow("Memory Detail:", self.ram_detail_lbl)

        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_bar.setStyleSheet("QProgressBar::chunk { background-color: #f4b400; }")
        layout.addRow("Disk Usage:", self.disk_bar)

        self.os_val = QLabel("--")
        layout.addRow("Operating System:", self.os_val)

        self.uptime_val = QLabel("--")
        layout.addRow("Uptime:", self.uptime_val)

        self.agent_ver_val = QLabel("--")
        layout.addRow("Agent Version:", self.agent_ver_val)

    def update_metrics(self, sys_info: SystemInfoResponse):
        self.cpu_bar.setValue(int(sys_info.cpu_usage))
        self.ram_bar.setValue(int(sys_info.ram_usage))
        self.ram_detail_lbl.setText(f"{sys_info.used_ram_gb} GB used of {sys_info.total_ram_gb} GB total")
        self.disk_bar.setValue(int(sys_info.disk_usage))
        self.os_val.setText(f"{sys_info.os_name} {sys_info.os_version}")
        
        hours = int(sys_info.uptime_seconds // 3600)
        mins = int((sys_info.uptime_seconds % 3600) // 60)
        self.uptime_val.setText(f"{hours}h {mins}m ({int(sys_info.uptime_seconds)}s)")
        self.agent_ver_val.setText(sys_info.agent_version)
