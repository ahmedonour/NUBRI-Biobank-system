DARK_QSS = """
QMainWindow, QDialog, QWidget, QStackedWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QLabel {
    color: #e0e0e0;
    background: transparent;
}

QLineEdit {
    padding: 16px 20px;
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    font-size: 13px;
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #264f78;
}
QLineEdit:focus {
    border-color: #4da6ff;
}
QLineEdit::placeholder {
    color: #888;
}

QTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 6px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 15px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #e0e0e0;
}

QTableWidget {
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    gridline-color: #3c3c3c;
    background-color: #2d2d2d;
    color: #e0e0e0;
}
QHeaderView::section {
    background-color: #333;
    color: #e0e0e0;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #3c3c3c;
    font-weight: bold;
}
QTableWidget::item {
    color: #e0e0e0;
}
QTableWidget::item:selected {
    background-color: #264f78;
}

QScrollArea {
    border: none;
    background: transparent;
}

QComboBox, QSpinBox {
    padding: 16px 20px;
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
    font-size: 13px;
}
QComboBox:hover, QSpinBox:hover {
    border-color: #4da6ff;
}
QComboBox::drop-down {
    border: none;
    background-color: #3c3c3c;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #264f78;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    background-color: #1e1e1e;
    padding: 10px;
}
QTabBar::tab {
    padding: 16px 50px;
    margin-right: 2px;
    background-color: #2d2d2d;
    color: #9e9e9e;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #4da6ff;
    color: #4da6ff;
}
QTabBar::tab:hover {
    background-color: #333;
}

QStatusBar {
    background-color: #2d2d2d;
    color: #9e9e9e;
    border-top: 1px solid #3c3c3c;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border-bottom: 1px solid #3c3c3c;
}
QMenuBar::item:selected {
    background-color: #333;
}
QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
}
QMenu::item:selected {
    background-color: #264f78;
}

QScrollBar:vertical {
    background-color: #2d2d2d;
    width: 12px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #555;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #2d2d2d;
    height: 12px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #555;
    border-radius: 6px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #777;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QDialogButtonBox QPushButton {
    padding: 8px 16px;
}
"""
