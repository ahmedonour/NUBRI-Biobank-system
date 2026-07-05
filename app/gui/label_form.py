from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea,
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import pyqtSignal
from ..database.models import SpecimenModel, ColumnDefinition
from .print_dialog import PrintDialog


class LabelFormWidget(QWidget):
    label_created = pyqtSignal(str)

    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.specimen_model = SpecimenModel(self.db)
        self.column_def = ColumnDefinition(self.db)
        self.field_widgets = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Create New Specimen Label")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4da6ff; margin-bottom: 10px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        self.form_layout = QFormLayout(scroll_content)
        self.form_layout.setSpacing(10)
        self.form_layout.setContentsMargins(10, 10, 10, 10)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Generate Label & Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        self.print_btn = QPushButton("Print Label")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #43a047; }
        """)
        self.print_btn.clicked.connect(self._print_last)
        self.print_btn.setVisible(False)
        btn_layout.addWidget(self.print_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.clear_btn.clicked.connect(self._clear)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)
        self._rebuild_fields()

    def _rebuild_fields(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.field_widgets = {}
        columns = self.column_def.get_all()

        if not columns:
            self.form_layout.addRow(QLabel("No columns defined. Go to Manage Columns to add some."))
            return

        for col in columns:
            name = col["column_name"]
            is_required = col["is_required"]
            label_text = f"{name} {'*' if is_required else ''}"
            edit = QLineEdit()
            edit.setPlaceholderText(f"Enter {name}")
            self.field_widgets[name] = edit
            self.form_layout.addRow(QLabel(label_text), edit)

    def _save(self):
        data = {}
        missing = []
        columns = self.column_def.get_all()

        for col in columns:
            name = col["column_name"]
            widget = self.field_widgets.get(name)
            if widget:
                value = widget.text().strip()
                if col["is_required"] and not value:
                    missing.append(name)
                data[name] = value

        if missing:
            QMessageBox.warning(
                self, "Required Fields",
                f"Please fill in: {', '.join(missing)}"
            )
            return

        try:
            qr_code = self.specimen_model.create(data)
            self._last_qr = qr_code
            self._last_fields = dict(data)
            self.label_created.emit(qr_code)
            QMessageBox.information(
                self, "Label Created",
                f"Specimen saved successfully!\nQR Code: {qr_code}"
            )
            self.print_btn.setVisible(True)
            self._clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    def _print_last(self):
        if hasattr(self, '_last_qr') and self._last_qr:
            dlg = PrintDialog(self._last_qr, self._last_fields, self.db, self)
            dlg.exec_()

    def _clear(self):
        for widget in self.field_widgets.values():
            widget.clear()

    def refresh(self):
        self._rebuild_fields()
