from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QWidget,
    QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from ..database.models import SpecimenModel, ColumnDefinition, SettingsModel
from ..printer.label_printer import print_label, LabelRenderer


class PrintDialog(QDialog):
    def __init__(self, qr_code, fields_dict, db=None, parent=None):
        super().__init__(parent)
        self.qr_code = qr_code
        self.fields_dict = fields_dict
        self.db = db
        self.settings = SettingsModel(db) if db else None
        self.setWindowTitle("Print Label")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._load_settings()
        self._update_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(f"Print Label — {self.qr_code}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4da6ff;")
        layout.addWidget(title)

        self.preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(self.preview_group)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 180)
        scroll = QScrollArea()
        scroll.setWidget(self.preview_label)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(280)
        preview_layout.addWidget(scroll)
        layout.addWidget(self.preview_group)

        printer_group = QGroupBox("Printer Options")
        form = QFormLayout(printer_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["System Printer", "Thermal (ESC/POS)"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        form.addRow("Printer Mode:", self.mode_combo)

        self.thermal_backend = QComboBox()
        self.thermal_backend.addItems(["network", "usb", "serial"])
        form.addRow("Thermal Connection:", self.thermal_backend)

        self.thermal_host = QLabel("192.168.1.100:9100")
        self.thermal_host.setStyleSheet("color: #9e9e9e;")
        form.addRow("Thermal Address:", self.thermal_host)

        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 99)
        self.copies_spin.setValue(1)
        form.addRow("Copies:", self.copies_spin)

        layout.addWidget(printer_group)

        btn_layout = QHBoxLayout()
        self.print_btn = QPushButton("Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 10px 30px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.print_btn.clicked.connect(self._do_print)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555; color: #e0e0e0; padding: 10px 30px;
                border: none; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.print_btn)
        layout.addLayout(btn_layout)

        self._on_mode_change()

    def _load_settings(self):
        if not self.settings:
            return
        mode = self.settings.get("printer_mode", "system")
        self.mode_combo.setCurrentIndex(0 if mode == "system" else 1)
        self.thermal_backend.setCurrentText(
            self.settings.get("printer_backend", "network")
        )
        host = self.settings.get("printer_host", "192.168.1.100")
        port = self.settings.get("printer_port", "9100")
        self.thermal_host.setText(f"{host}:{port}")

    def _on_mode_change(self):
        is_thermal = self.mode_combo.currentIndex() == 1
        self.thermal_backend.setVisible(is_thermal)
        self.thermal_host.setVisible(is_thermal)

    def _update_preview(self):
        from .label_designer import load_template
        tpl = load_template(self.settings) if self.settings else None
        w = tpl.get("width_mm", 40) if tpl else 40
        h = tpl.get("height_mm", 13) if tpl else 13
        self.preview_group.setTitle(f"Preview ({w}×{h}mm)")
        renderer = LabelRenderer(width_mm=w, height_mm=h)
        img = renderer.render(self.qr_code, self.fields_dict, template=tpl)
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(400, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)

    def _do_print(self):
        try:
            is_thermal = self.mode_combo.currentIndex() == 1
            copies = self.copies_spin.value()
            host = "192.168.1.100"
            port = 9100

            if is_thermal:
                host, port_str = self.thermal_host.text().split(":")
                port = int(port_str)

            from .label_designer import load_template
            tpl = load_template(self.settings) if self.settings else None
            lw = tpl.get("width_mm", 40) if tpl else 40
            lh = tpl.get("height_mm", 13) if tpl else 13

            print_label(
                qr_code=self.qr_code,
                fields_dict=self.fields_dict,
                printer_mode="thermal" if is_thermal else "system",
                backend=self.thermal_backend.currentText() if is_thermal else "network",
                host=host,
                port=port,
                thermal_copies=copies,
                label_width_mm=lw,
                label_height_mm=lh,
                label_gap_mm=int(self.settings.get("label_gap_mm", "3")) if self.settings else 3,
                template=tpl,
            )
            QMessageBox.information(self, "Printed", "Label sent to printer.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print:\n{str(e)}")
