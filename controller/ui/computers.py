from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor
from controller.database.database import db
from controller.services.computer_service import computer_service
from controller.services.discovery import discover_agents
from controller.ui.pairing import AddComputerDialog


class DiscoveryWorker(QThread):
    discovery_complete = Signal(list)

    def run(self):
        results = discover_agents()
        self.discovery_complete.emit(results)


class DiscoveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LAN Discovered Computers")
        self.resize(500, 350)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #202124; }
            QListWidget { background-color: #ffffff; color: #202124; border: 1px solid #cccccc; border-radius: 4px; }
            QPushButton { background-color: #f1f3f4; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 4px 10px; }
        """)
        self.init_ui()
        self.run_scan()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.status_lbl = QLabel("Scanning local network for active Agents...")
        self.status_lbl.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.status_lbl)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.clicked.connect(self.run_scan)
        btn_box.addWidget(self.rescan_btn)

        self.pair_btn = QPushButton("Pair Selected Agent")
        self.pair_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; font-weight: bold; border-radius: 4px; padding: 6px 12px;"
        )
        self.pair_btn.clicked.connect(self.pair_selected)
        btn_box.addWidget(self.pair_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

    def run_scan(self):
        self.list_widget.clear()
        self.status_lbl.setText("Scanning local network for active Agents (UDP Broadcast)...")
        self.rescan_btn.setEnabled(False)

        self.worker = DiscoveryWorker()
        self.worker.discovery_complete.connect(self.on_discovery_complete)
        self.worker.start()

    def on_discovery_complete(self, results):
        self.rescan_btn.setEnabled(True)
        if not results:
            self.status_lbl.setText("No active Agents found on LAN.")
            return

        self.status_lbl.setText(f"Found {len(results)} Agent(s) on LAN. Select one to pair:")
        for agent_info in results:
            item_text = f"{agent_info.computer_name} | ID: {agent_info.agent_id} | IP: {agent_info.ip_address}:{agent_info.port} [{agent_info.pairing_status}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, agent_info)
            self.list_widget.addItem(item)

    def pair_selected(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Required", "Please select an Agent from the list to pair.")
            return

        agent_info = current_item.data(Qt.UserRole)
        dialog = AddComputerDialog(self)
        dialog.ip_input.setText(agent_info.ip_address)
        dialog.port_input.setText(str(agent_info.port))
        if dialog.exec() == QDialog.Accepted:
            self.accept()


class ComputersView(QWidget):
    open_details_signal = Signal(str)  # agent_id

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Computers Management")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        scan_btn = QPushButton("Scan LAN Discovery")
        scan_btn.setStyleSheet(
            "background-color: #f1f3f4; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 6px 14px; font-weight: bold;"
        )
        scan_btn.clicked.connect(self.open_discovery_dialog)
        header_layout.addWidget(scan_btn)

        add_btn = QPushButton("+ Add Computer")
        add_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 6px 14px; font-weight: bold;"
        )
        add_btn.clicked.connect(self.open_add_dialog)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Computers Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Computer Name", "Agent ID", "IP Address", "OS", "Status", "Last Seen", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setMinimumHeight(400)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")

        layout.addWidget(self.table)
        self.load_computers()

    def load_computers(self):
        computers = db.get_all_computers()
        self.table.setRowCount(0)

        for row_idx, comp in enumerate(computers):
            self.table.insertRow(row_idx)

            self.table.setItem(row_idx, 0, QTableWidgetItem(comp.display_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(comp.agent_id))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{comp.ip_address}:{comp.port}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(comp.os_name))

            # Status
            status_item = QTableWidgetItem(comp.status)
            if comp.status == "ONLINE":
                status_item.setForeground(QColor("#0f9d58"))
            else:
                status_item.setForeground(QColor("#ea4335"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(row_idx, 4, status_item)

            self.table.setItem(row_idx, 5, QTableWidgetItem(comp.last_seen[:19] if comp.last_seen else "Never"))

            # Actions Cell (Widget with Details and Remove)
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(6)

            det_btn = QPushButton("Details")
            det_btn.setStyleSheet(
                "background-color: #e8f0fe; color: #1967d2; border: 1px solid #aecbfa; border-radius: 4px; padding: 2px 6px;"
            )
            aid = comp.agent_id
            det_btn.clicked.connect(lambda checked=False, agent_id=aid: self.open_details_signal.emit(agent_id))
            act_layout.addWidget(det_btn)

            rem_btn = QPushButton("Remove")
            rem_btn.setStyleSheet(
                "background-color: #fce8e6; color: #c5221f; border: 1px solid #f8b4b0; border-radius: 4px; padding: 2px 6px;"
            )
            cname = comp.display_name
            rem_btn.clicked.connect(lambda checked=False, agent_id=aid, name=cname: self.confirm_remove(agent_id, name))
            act_layout.addWidget(rem_btn)

            self.table.setCellWidget(row_idx, 6, actions_widget)

    def open_add_dialog(self):
        dialog = AddComputerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_computers()

    def open_discovery_dialog(self):
        dialog = DiscoveryDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_computers()

    def confirm_remove(self, agent_id: str, display_name: str):
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{display_name}' ({agent_id}) from this Controller?\n\nThis will remove it from the Controller database but will NOT stop or uninstall the Agent on the target PC.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            computer_service.remove_computer(agent_id)
            self.load_computers()
