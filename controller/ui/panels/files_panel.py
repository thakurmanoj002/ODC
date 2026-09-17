from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QProgressBar,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from controller.services.computer_service import computer_service
from controller.ui.dialogs.confirm_dialog import ConfirmDialog
from shared.models.responses import ActionResponse


class FileActionWorker(QThread):
    action_completed = Signal(object)  # ActionResponse

    def __init__(self, action_type: str, agent_id: str, root_id: str, relative_path: str = "", extra_param: str = ""):
        super().__init__()
        self.action_type = action_type
        self.agent_id = agent_id
        self.root_id = root_id
        self.relative_path = relative_path
        self.extra_param = extra_param

    def run(self):
        if self.action_type == "GET_DIR":
            resp = computer_service.get_directory(self.agent_id, self.root_id, self.relative_path)
        elif self.action_type == "CREATE_FOLDER":
            resp = computer_service.create_folder(self.agent_id, self.root_id, self.relative_path, self.extra_param)
        elif self.action_type == "RENAME":
            resp = computer_service.rename_path(self.agent_id, self.root_id, self.relative_path, self.extra_param)
        elif self.action_type == "DELETE":
            resp = computer_service.delete_path(self.agent_id, self.root_id, self.relative_path)
        else:
            resp = ActionResponse(success=False, request_id="", action="", message="Invalid action")
        self.action_completed.emit(resp)


class FileManagerPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("File & Folder Management", parent)
        self.agent_id = None
        self.is_online = False
        self.current_root_id = "shared"
        self.current_relative_path = ""
        self.roots_list = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Header Status
        self.msg_lbl = QLabel("Browse and manage files in approved logical roots.")
        self.msg_lbl.setStyleSheet("color: #555555; font-size: 12px;")
        main_layout.addWidget(self.msg_lbl)

        body_layout = QHBoxLayout()

        # Left Sidebar: Approved Roots List
        roots_layout = QVBoxLayout()
        lbl_roots = QLabel("Approved Roots")
        lbl_roots.setFont(QFont("Segoe UI", 10, QFont.Bold))
        roots_layout.addWidget(lbl_roots)

        self.roots_widget = QListWidget()
        self.roots_widget.setFixedWidth(160)
        self.roots_widget.itemClicked.connect(self.on_root_selected)
        roots_layout.addWidget(self.roots_widget)

        body_layout.addLayout(roots_layout)

        # Right Section: Browser Table & Toolbar
        browser_layout = QVBoxLayout()

        # Toolbar & Breadcrumb
        top_bar = QHBoxLayout()
        self.breadcrumb_lbl = QLabel("shared /")
        self.breadcrumb_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.breadcrumb_lbl.setStyleSheet("color: #1a73e8;")
        top_bar.addWidget(self.breadcrumb_lbl)
        top_bar.addStretch()

        self.up_btn = QPushButton("↑ Up")
        self.up_btn.clicked.connect(self.navigate_up)
        top_bar.addWidget(self.up_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_directory)
        top_bar.addWidget(self.refresh_btn)

        self.new_folder_btn = QPushButton("+ New Folder")
        self.new_folder_btn.setStyleSheet(
            "background-color: #1a73e8; color: white; border-radius: 4px; padding: 4px 10px; font-weight: bold;"
        )
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        top_bar.addWidget(self.new_folder_btn)

        browser_layout.addLayout(top_bar)

        # File List Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Modified", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setMinimumHeight(250)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.table.setStyleSheet("QTableWidget { background-color: #ffffff; gridline-color: #f0f0f0; }")

        browser_layout.addWidget(self.table)

        # Bottom Progress Bar
        progress_box = QHBoxLayout()
        self.progress_lbl = QLabel("Ready")
        self.progress_lbl.setStyleSheet("color: #666666; font-size: 11px;")
        progress_box.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        progress_box.addWidget(self.progress_bar)

        browser_layout.addLayout(progress_box)
        body_layout.addLayout(browser_layout)
        main_layout.addLayout(body_layout)

    def set_computer(self, agent_id: str, is_online: bool, capabilities: list):
        self.agent_id = agent_id
        self.is_online = is_online

        has_file_cap = "GET_DIRECTORY" in capabilities

        if not has_file_cap:
            self.msg_lbl.setText("File & folder management is unavailable on this computer.")
            self.msg_lbl.setStyleSheet("color: #ea4335; font-weight: bold;")
            self.set_controls_enabled(False)
            self.table.setRowCount(0)
            self.roots_widget.clear()
            return

        self.msg_lbl.setText("Browse and manage files in approved logical roots.")
        self.msg_lbl.setStyleSheet("color: #555555; font-size: 12px;")
        self.set_controls_enabled(is_online)

        if is_online:
            self.refresh_directory()

    def set_controls_enabled(self, enabled: bool):
        self.refresh_btn.setEnabled(enabled)
        self.up_btn.setEnabled(enabled)
        self.new_folder_btn.setEnabled(enabled)

    def update_breadcrumb(self):
        rel = self.current_relative_path.replace("\\", "/")
        b_text = f"{self.current_root_id} / {rel}" if rel else f"{self.current_root_id} /"
        self.breadcrumb_lbl.setText(b_text)

    def on_root_selected(self, item: QListWidgetItem):
        root_info = item.data(Qt.UserRole)
        if root_info:
            self.current_root_id = root_info.get("root_id", "shared")
            self.current_relative_path = ""
            self.refresh_directory()

    def refresh_directory(self):
        if not self.agent_id or not self.is_online:
            return

        self.set_controls_enabled(False)
        self.msg_lbl.setText("Loading directory items...")
        self.update_breadcrumb()

        self.worker = FileActionWorker("GET_DIR", self.agent_id, self.current_root_id, self.current_relative_path)
        self.worker.action_completed.connect(self.on_dir_retrieved)
        self.worker.start()

    def on_dir_retrieved(self, resp: ActionResponse):
        self.set_controls_enabled(self.is_online)
        if resp.success and resp.data:
            items = resp.data.get("items", [])
            roots = resp.data.get("roots", [])

            self.populate_roots(roots)
            self.populate_items(items)
            self.msg_lbl.setText("Directory loaded successfully.")
        else:
            self.msg_lbl.setText(f"Failed to list directory: {resp.message}")

    def populate_roots(self, roots: list):
        if roots and self.roots_widget.count() == 0:
            for r in roots:
                item = QListWidgetItem(r.get("display_name", r.get("root_id")))
                item.setData(Qt.UserRole, r)
                self.roots_widget.addItem(item)
                if r.get("root_id") == self.current_root_id:
                    item.setSelected(True)

    def populate_items(self, items: list):
        self.table.setRowCount(0)
        for row_idx, item in enumerate(items):
            self.table.insertRow(row_idx)

            iname = item.get("name", "")
            itype = item.get("type", "file")
            isize = item.get("size", 0)
            imod = item.get("modified", "")[:19].replace("T", " ") if item.get("modified") else ""

            # Name Item
            name_item = QTableWidgetItem(f"📁 {iname}" if itype == "folder" else f"📄 {iname}")
            name_item.setData(Qt.UserRole, item)
            self.table.setItem(row_idx, 0, name_item)

            self.table.setItem(row_idx, 1, QTableWidgetItem(itype.capitalize()))

            size_str = "--" if itype == "folder" else f"{round(isize / 1024, 1)} KB"
            self.table.setItem(row_idx, 2, QTableWidgetItem(size_str))
            self.table.setItem(row_idx, 3, QTableWidgetItem(imod))

            # Actions Cell (Rename & Delete)
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(4)

            ren_btn = QPushButton("Rename")
            ren_btn.setStyleSheet(
                "background-color: #f1f3f4; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 2px 6px;"
            )
            ren_btn.clicked.connect(lambda checked=False, name=iname: self.rename_item(name))
            act_layout.addWidget(ren_btn)

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                "background-color: #fce8e6; color: #c5221f; border: 1px solid #f8b4b0; border-radius: 4px; padding: 2px 6px;"
            )
            del_btn.clicked.connect(lambda checked=False, name=iname, t=itype: self.delete_item(name, t))
            act_layout.addWidget(del_btn)

            self.table.setCellWidget(row_idx, 4, act_widget)

    def on_item_double_clicked(self, table_item: QTableWidgetItem):
        row = table_item.row()
        item_data = self.table.item(row, 0).data(Qt.UserRole)
        if item_data and item_data.get("type") == "folder":
            folder_name = item_data.get("name")
            if self.current_relative_path:
                self.current_relative_path = f"{self.current_relative_path}/{folder_name}"
            else:
                self.current_relative_path = folder_name
            self.refresh_directory()

    def navigate_up(self):
        if not self.current_relative_path:
            return

        parts = self.current_relative_path.replace("\\", "/").strip("/").split("/")
        if len(parts) > 1:
            self.current_relative_path = "/".join(parts[:-1])
        else:
            self.current_relative_path = ""
        self.refresh_directory()

    def create_new_folder(self):
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Enter new folder name:")
        if ok and folder_name.strip():
            self.set_controls_enabled(False)
            self.msg_lbl.setText(f"Creating folder '{folder_name}'...")

            self.worker = FileActionWorker(
                "CREATE_FOLDER", self.agent_id, self.current_root_id, self.current_relative_path, folder_name.strip()
            )
            self.worker.action_completed.connect(self.on_file_action_completed)
            self.worker.start()

    def rename_item(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Item", f"Enter new name for '{old_name}':", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            rel_target = f"{self.current_relative_path}/{old_name}" if self.current_relative_path else old_name
            self.set_controls_enabled(False)
            self.msg_lbl.setText(f"Renaming '{old_name}'...")

            self.worker = FileActionWorker(
                "RENAME", self.agent_id, self.current_root_id, rel_target, new_name.strip()
            )
            self.worker.action_completed.connect(self.on_file_action_completed)
            self.worker.start()

    def delete_item(self, item_name: str, item_type: str):
        confirmed = ConfirmDialog.confirm_action(
            self,
            title="Delete Item",
            message=f"Are you sure you want to delete {item_type} '{item_name}'?",
            warning_text="Warning: If this is a folder, all of its contents will be permanently deleted.",
            confirm_btn_text="Delete",
        )
        if not confirmed:
            return

        rel_target = f"{self.current_relative_path}/{item_name}" if self.current_relative_path else item_name
        self.set_controls_enabled(False)
        self.msg_lbl.setText(f"Deleting '{item_name}'...")

        self.worker = FileActionWorker("DELETE", self.agent_id, self.current_root_id, rel_target)
        self.worker.action_completed.connect(self.on_file_action_completed)
        self.worker.start()

    def on_file_action_completed(self, resp: ActionResponse):
        self.set_controls_enabled(self.is_online)
        if resp.success:
            QMessageBox.information(self, "File Management", resp.message)
            self.refresh_directory()
        else:
            QMessageBox.critical(self, "Action Failed", resp.message)
            self.msg_lbl.setText(f"Error: {resp.message}")
