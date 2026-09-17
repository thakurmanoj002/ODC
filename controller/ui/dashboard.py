from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from controller.database.database import db
from controller.database.models import ComputerRecord


class StatCard(QFrame):
    def __init__(self, title: str, value: str, color_hex: str = "#1a73e8"):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            f"""
            StatCard {{
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #666666; font-size: 13px;")
        
        self.val_label = QLabel(value)
        self.val_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.val_label.setStyleSheet(f"color: {color_hex};")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.val_label)

    def set_value(self, val: str):
        self.val_label.setText(val)


class DashboardView(QWidget):
    open_details_signal = Signal(str)  # Emits agent_id

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        header_layout = QHBoxLayout()
        title = QLabel("Dashboard Overview")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 6px 14px; font-weight: bold;"
        )
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Stat Cards Layout
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        self.card_total = StatCard("Total Computers", "0", "#1a73e8")
        self.card_online = StatCard("Online", "0", "#0f9d58")
        self.card_offline = StatCard("Offline", "0", "#ea4335")

        stats_layout.addWidget(self.card_total)
        stats_layout.addWidget(self.card_online)
        stats_layout.addWidget(self.card_offline)

        layout.addLayout(stats_layout)

        # Recent Computers Section
        recent_group = QGroupBox("Managed Computers Summary")
        recent_layout = QVBoxLayout(recent_group)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Computer Name", "Agent ID", "IP Address", "OS", "Status", "Action"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setMinimumHeight(250)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")

        recent_layout.addWidget(self.table)
        layout.addWidget(recent_group)

        self.load_data()

    def load_data(self):
        computers = db.get_all_computers()
        total_count = len(computers)
        online_count = sum(1 for c in computers if c.status == "ONLINE")
        offline_count = total_count - online_count

        self.card_total.set_value(str(total_count))
        self.card_online.set_value(str(online_count))
        self.card_offline.set_value(str(offline_count))

        self.table.setRowCount(0)
        for row_idx, comp in enumerate(computers):
            self.table.insertRow(row_idx)

            self.table.setItem(row_idx, 0, QTableWidgetItem(comp.display_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(comp.agent_id))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{comp.ip_address}:{comp.port}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(comp.os_name))

            # Status Badge
            status_item = QTableWidgetItem(comp.status)
            if comp.status == "ONLINE":
                status_item.setForeground(QColor("#0f9d58"))
            else:
                status_item.setForeground(QColor("#ea4335"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(row_idx, 4, status_item)

            # Details Button
            btn = QPushButton("View Details")
            btn.setStyleSheet(
                "background-color: #e8f0fe; color: #1967d2; border: 1px solid #aecbfa; border-radius: 4px; padding: 4px 8px;"
            )
            # Capture agent_id in lambda
            agent_id = comp.agent_id
            btn.clicked.connect(lambda checked=False, aid=agent_id: self.open_details_signal.emit(aid))
            self.table.setCellWidget(row_idx, 5, btn)
