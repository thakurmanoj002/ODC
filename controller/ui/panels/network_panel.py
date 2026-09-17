from PySide6.QtWidgets import QWidget, QGroupBox, QFormLayout, QLabel
from shared.models.responses import NetworkInfoResponse


class NetworkInfoPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Network Information", parent)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.net_ip_val = QLabel("--")
        layout.addRow("Local IP:", self.net_ip_val)

        self.net_host_val = QLabel("--")
        layout.addRow("Hostname:", self.net_host_val)

        self.net_state_val = QLabel("--")
        layout.addRow("Network State:", self.net_state_val)

    def update_info(self, net_info: NetworkInfoResponse):
        self.net_ip_val.setText(net_info.local_ip)
        self.net_host_val.setText(net_info.hostname)
        self.net_state_val.setText(net_info.network_state)
