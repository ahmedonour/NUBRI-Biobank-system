from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt
from ..database.models import SpecimenModel, ColumnDefinition
from .print_dialog import PrintDialog


class DatabaseViewWidget(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.specimen_model = SpecimenModel(self.db)
        self.column_def = ColumnDefinition(self.db)
        self._page = 0
        self._page_size = 50
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Database Browser")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4da6ff; margin-bottom: 6px;")
        layout.addWidget(title)

        info = QLabel("All specimens — click a row to see full details.")
        info.setStyleSheet("color: #9e9e9e; margin-bottom: 8px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._show_detail)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        nav = QHBoxLayout()
        self.count_label = QLabel("0 records")
        self.count_label.setStyleSheet("color: #9e9e9e;")
        nav.addWidget(self.count_label)

        nav.addStretch()

        self.prev_btn = QPushButton("← Prev")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 8px 16px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        self.prev_btn.clicked.connect(self._prev_page)
        nav.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("color: #e0e0e0; padding: 0 10px;")
        nav.addWidget(self.page_label)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 8px 16px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        self.next_btn.clicked.connect(self._next_page)
        nav.addWidget(self.next_btn)

        self.print_btn = QPushButton("Print Label")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white; padding: 8px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #43a047; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self._print_selected)
        nav.addWidget(self.print_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 8px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.refresh_btn.clicked.connect(self._load)
        nav.addWidget(self.refresh_btn)

        layout.addLayout(nav)

    def _load(self):
        columns = self.column_def.get_all()
        specimens = self.specimen_model.get_all(
            limit=self._page_size, offset=self._page * self._page_size
        )
        total = self.specimen_model.count()

        self.count_label.setText(f"{total} records")
        self.page_label.setText(f"Page {self._page + 1}")
        self.prev_btn.setEnabled(self._page > 0)
        self.next_btn.setEnabled((self._page + 1) * self._page_size < total)

        headers = ["QR Code"] + [c["column_name"] for c in columns] + ["Created", "Updated"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setRowCount(len(specimens))
        self.table.setSortingEnabled(False)

        for row, spec in enumerate(specimens):
            self.table.setItem(row, 0, QTableWidgetItem(spec["qr_code"]))
            fields = spec["custom_fields"]
            for ci, col in enumerate(columns):
                val = fields.get(col["column_name"], "")
                self.table.setItem(row, 1 + ci, QTableWidgetItem(str(val)))
            self.table.setItem(row, len(columns) + 1, QTableWidgetItem(spec["created_at"]))
            updated = spec.get("updated_at") or ""
            self.table.setItem(row, len(columns) + 2, QTableWidgetItem(updated))

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self._stored_specimens = specimens

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._load()

    def _next_page(self):
        self._page += 1
        self._load()

    def _on_selection_changed(self):
        self.print_btn.setEnabled(self.table.currentRow() >= 0)

    def _print_selected(self):
        row = self.table.currentRow()
        if row < 0 or not hasattr(self, "_stored_specimens") or row >= len(self._stored_specimens):
            return
        spec = self._stored_specimens[row]
        dlg = PrintDialog(spec["qr_code"], spec["custom_fields"], self.db, self)
        dlg.exec_()

    def _show_detail(self, item):
        row = item.row()
        if not hasattr(self, "_stored_specimens") or row >= len(self._stored_specimens):
            return
        spec = self._stored_specimens[row]
        columns = self.column_def.get_all()
        fields = spec["custom_fields"]

        html = f"<h3>Specimen: {spec['qr_code']}</h3><table>"
        for col in columns:
            html += f"<tr><td><b>{col['column_name']}:</b></td><td>{fields.get(col['column_name'], '')}</td></tr>"
        html += "</table>"
        html += f"<p style='color:#9e9e9e;font-size:11px;'>"
        html += f"Created: {spec['created_at']}<br>Updated: {spec.get('updated_at', '')}</p>"

        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Specimen — {spec['qr_code']}")
        dlg.setMinimumSize(420, 300)
        dlg.setModal(True)
        dlg_layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(html)
        dlg_layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 8px 20px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        close_btn.clicked.connect(dlg.accept)
        dlg_layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        dlg.exec_()
