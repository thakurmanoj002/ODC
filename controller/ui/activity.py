from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from controller.database.database import db


class ActivityView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Activity & Audit Logs")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 6px 14px; font-weight: bold;"
        )
        refresh_btn.clicked.connect(self.load_activities)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Filter Bar
        filter_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter logs by computer or action...")
        self.search_edit.textChanged.connect(self.filter_logs)
        filter_layout.addWidget(self.search_edit)

        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Computer", "Action", "Status", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setMinimumHeight(400)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")

        layout.addWidget(self.table)
        self.load_activities()

    def load_activities(self):
        self.records = db.get_recent_activities(limit=200)
        self.display_records(self.records)

    def display_records(self, records):
        self.table.setRowCount(0)
        for row_idx, rec in enumerate(records):
            self.table.insertRow(row_idx)

            ts_str = rec.created_at[:19].replace("T", " ") if rec.created_at else ""
            self.table.setItem(row_idx, 0, QTableWidgetItem(ts_str))
            self.table.setItem(row_idx, 1, QTableWidgetItem(rec.computer_name or rec.computer_id or "System"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(rec.action))

            status_item = QTableWidgetItem(rec.status)
            if rec.status == "SUCCESS":
                status_item.setForeground(QColor("#0f9d58"))
            elif rec.status == "WARNING":
                status_item.setForeground(QColor("#f4b400"))
            else:
                status_item.setForeground(QColor("#ea4335"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(row_idx, 3, status_item)

            self.table.setItem(row_idx, 4, QTableWidgetItem(rec.message))

    def filter_logs(self, query: str):
        q = query.lower().strip()
        if not q:
            self.display_records(self.records)
            return

        filtered = [
            r for r in self.records
            if q in (r.computer_name or "").lower()
            or q in (r.computer_id or "").lower()
            or q in (r.action or "").lower()
            or q in (r.message or "").lower()
        ]
        self.display_records(filtered)
