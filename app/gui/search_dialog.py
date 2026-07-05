from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QFormLayout,
    QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from ..database.models import SpecimenModel, ColumnDefinition


class SearchWidget(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.specimen_model = SpecimenModel(self.db)
        self.column_def = ColumnDefinition(self.db)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Search & Scan Specimens")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8; margin-bottom: 10px;")
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by QR code or any field value...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 16px; border: 2px solid #ddd;
                border-radius: 8px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #1a73e8; }
        """)
        self.search_input.returnPressed.connect(self._search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1557b0; }
        """)
        self.search_btn.clicked.connect(self._search)
        search_layout.addWidget(self.search_btn)

        self.scan_btn = QPushButton("Scan QR from Camera")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        self.scan_btn.clicked.connect(self._scan_qr)
        search_layout.addWidget(self.scan_btn)

        layout.addLayout(search_layout)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["QR Code", "Details", "Created"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd; border-radius: 6px;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa; padding: 8px;
                border: none; border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
        """)
        self.results_table.itemDoubleClicked.connect(self._show_detail)
        layout.addWidget(self.results_table)

        detail_group = QGroupBox("Detail View")
        detail_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #ddd;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """)
        detail_layout = QVBoxLayout(detail_group)

        self.detail_label = QLabel("Double-click a row or scan a QR code to see details.")
        self.detail_label.setStyleSheet("color: #666; font-style: italic;")
        detail_layout.addWidget(self.detail_label)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("border: none; background: transparent; font-size: 13px;")
        detail_layout.addWidget(self.detail_text)

        layout.addWidget(detail_group)

    def _search(self):
        query = self.search_input.text().strip()
        if not query:
            results = self.specimen_model.get_all(limit=200)
        else:
            results = self.specimen_model.search(query)

        self.results_table.setRowCount(len(results))
        columns = self.column_def.get_all()

        for row, specimen in enumerate(results):
            qr_item = QTableWidgetItem(specimen["qr_code"])
            qr_item.setData(Qt.UserRole, specimen["id"])
            self.results_table.setItem(row, 0, qr_item)

            fields = specimen["custom_fields"]
            summary = "; ".join(
                f"{c['column_name']}: {fields.get(c['column_name'], '-')}"
                for c in columns[:3]
            )
            self.results_table.setItem(row, 1, QTableWidgetItem(summary))
            self.results_table.setItem(row, 2, QTableWidgetItem(specimen["created_at"]))

    def _scan_qr(self):
        try:
            from ..qr_code import QRHandler
            qr_code = QRHandler.decode_from_camera(timeout=60)
            if qr_code:
                self.search_input.setText(qr_code)
                self._search()
                self._show_detail_for_qr(qr_code)
        except ImportError:
            QMessageBox.warning(
                self, "Camera Not Available",
                "Camera QR scanning requires OpenCV and pyzbar.\n"
                "Install: pip install opencv-python pyzbar"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Scan failed: {str(e)}")

    def _show_detail(self, item):
        row = item.row()
        qr_item = self.results_table.item(row, 0)
        if qr_item:
            self._show_detail_for_qr(qr_item.text())

    def _show_detail_for_qr(self, qr_code):
        specimen = self.specimen_model.get_by_qr(qr_code)
        if not specimen:
            self.detail_label.setText("Specimen not found.")
            self.detail_text.clear()
            return

        columns = self.column_def.get_all()
        fields = specimen["custom_fields"]

        html = f"<h3>Specimen: {specimen['qr_code']}</h3>"
        html += "<table>"
        for col in columns:
            name = col["column_name"]
            value = fields.get(name, "")
            html += f"<tr><td><b>{name}:</b></td><td>{value}</td></tr>"
        html += "</table>"
        html += f"<p style='color:#999;font-size:11px;'>Created: {specimen['created_at']}<br>Updated: {specimen['updated_at']}</p>"

        self.detail_label.setText(f"Details for: {specimen['qr_code']}")
        self.detail_text.setHtml(html)
