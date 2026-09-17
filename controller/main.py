import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from controller.ui.main_window import MainWindow
from controller.utils.logging_config import logger

GLOBAL_APP_STYLESHEET = """
QWidget {
    color: #1e293b;
    font-family: 'Segoe UI', system-ui, sans-serif;
}

QMainWindow, QStackedWidget {
    background-color: #f8fafc;
}

QLabel {
    color: #1e293b;
}

QGroupBox {
    color: #1e293b;
    font-weight: bold;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 15px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #1e293b;
}

QTableWidget {
    background-color: #ffffff;
    color: #1e293b;
    gridline-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #e2e8f0;
    selection-color: #0f172a;
}

QTableWidget::item {
    color: #1e293b;
    padding: 4px;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #334155;
    font-weight: bold;
    padding: 6px;
    border: 1px solid #cbd5e1;
}

QLineEdit {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 2px solid #2563eb;
}

QSpinBox, QComboBox {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 6px 10px;
}

QListWidget {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
}

QListWidget::item {
    color: #1e293b;
    padding: 6px;
}

QListWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QCheckBox {
    color: #1e293b;
}

QDialog {
    background-color: #ffffff;
}

QScrollArea {
    border: none;
    background-color: #f8fafc;
}
"""


def main():
    logger.info("Starting LAN Office Control Center (Controller)...")
    app = QApplication(sys.argv)

    # Force light palette so OS Dark Mode does not override text with white
    palette = QPalette()
    palette.setColor(QPalette.WindowText, QColor("#1e293b"))
    palette.setColor(QPalette.Text, QColor("#1e293b"))
    palette.setColor(QPalette.ButtonText, QColor("#1e293b"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.Window, QColor("#f8fafc"))
    app.setPalette(palette)

    app.setStyleSheet(GLOBAL_APP_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
