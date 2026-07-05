from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QCheckBox, QMessageBox, QGroupBox, QSpinBox,
    QFileDialog
)
from ..database.models import SettingsModel


class SettingsWidget(QWidget):
    def __init__(self, db=None, db_path=None):
        super().__init__()
        self.db = db
        self.db_path = db_path
        self.settings = SettingsModel(self.db)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8; margin-bottom: 10px;")
        layout.addWidget(title)

        pb_group = QGroupBox("PocketBase Server")
        pb_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #ddd;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """)
        pb_layout = QFormLayout(pb_group)

        self.pocketbase_url = QLineEdit()
        self.pocketbase_url.setPlaceholderText("http://127.0.0.1:8090")
        pb_layout.addRow("Server URL:", self.pocketbase_url)

        pb_note = QLabel("PocketBase handles authentication for both the desktop app and web preview. "
                         "Users collection is used for sign in / sign out.")
        pb_note.setStyleSheet("color: #666; font-size: 11px; font-weight: normal;")
        pb_note.setWordWrap(True)
        pb_layout.addRow(pb_note)

        layout.addWidget(pb_group)

        printer_group = QGroupBox("Xprinter Thermal Printer")
        printer_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #ddd;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """)
        printer_layout = QFormLayout(printer_group)

        self.printer_backend = QComboBox()
        self.printer_backend.addItems(["network", "usb", "serial"])
        printer_layout.addRow("Connection Type:", self.printer_backend)

        self.printer_host = QLineEdit()
        self.printer_host.setPlaceholderText("e.g. 192.168.1.100")
        printer_layout.addRow("Host / IP:", self.printer_host)

        self.printer_port = QLineEdit()
        self.printer_port.setPlaceholderText("e.g. 9100")
        printer_layout.addRow("Port:", self.printer_port)

        self.label_width = QLineEdit()
        self.label_width.setPlaceholderText("mm (e.g. 100)")
        printer_layout.addRow("Label Width:", self.label_width)

        self.label_height = QLineEdit()
        self.label_height.setPlaceholderText("mm (e.g. 50)")
        printer_layout.addRow("Label Height:", self.label_height)

        printer_note = QLabel("Note: Xprinter uses standard ESC/POS protocol. "
                              "Connect via network (recommended), USB, or serial.")
        printer_note.setStyleSheet("color: #666; font-size: 11px; font-weight: normal; margin-top: 5px;")
        printer_note.setWordWrap(True)
        printer_layout.addRow(printer_note)

        layout.addWidget(printer_group)

        web_group = QGroupBox("Web Preview Server")
        web_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #ddd;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """)
        web_layout = QFormLayout(web_group)

        self.web_port = QLineEdit()
        self.web_port.setPlaceholderText("e.g. 5000")
        web_layout.addRow("Port:", self.web_port)

        web_note = QLabel("Open http://<your-computer-ip>:<port> on your phone/tablet "
                          "to scan QR codes and view specimen details.")
        web_note.setStyleSheet("color: #666; font-size: 11px; font-weight: normal;")
        web_note.setWordWrap(True)
        web_layout.addRow(web_note)

        layout.addWidget(web_group)

        backup_group = QGroupBox("Google Drive Backup")
        backup_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 1px solid #ddd;
                border-radius: 8px; margin-top: 10px; padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """)
        backup_layout = QFormLayout(backup_group)

        self.backup_enabled = QCheckBox("Enable automatic backups")
        backup_layout.addRow("", self.backup_enabled)

        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 168)
        self.backup_interval.setSuffix(" hours")
        backup_layout.addRow("Backup Interval:", self.backup_interval)

        self.credentials_path = QLineEdit()
        self.credentials_path.setPlaceholderText("Path to client_secret.json")
        backup_layout.addRow("Credentials:", self.credentials_path)

        self.browse_creds_btn = QPushButton("Browse")
        self.browse_creds_btn.clicked.connect(self._browse_credentials)
        backup_layout.addRow("", self.browse_creds_btn)

        self.backup_now_btn = QPushButton("Backup Now")
        self.backup_now_btn.clicked.connect(self._backup_now)
        backup_layout.addRow("", self.backup_now_btn)

        layout.addWidget(backup_group)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1557b0; }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _load_settings(self):
        all_settings = self.settings.get_all()
        self.pocketbase_url.setText(all_settings.get("pocketbase_url", "http://127.0.0.1:8090"))
        self.printer_backend.setCurrentText(all_settings.get("printer_backend", "network"))
        self.printer_host.setText(all_settings.get("printer_host", ""))
        self.printer_port.setText(all_settings.get("printer_port", "9100"))
        self.label_width.setText(all_settings.get("label_width_mm", "100"))
        self.label_height.setText(all_settings.get("label_height_mm", "50"))
        self.web_port.setText(all_settings.get("web_port", "5000"))
        self.backup_enabled.setChecked(all_settings.get("backup_enabled", "false") == "true")
        self.backup_interval.setValue(int(all_settings.get("backup_interval_hours", "24")))

    def _save_settings(self):
        self.settings.set("pocketbase_url", self.pocketbase_url.text())
        self.settings.set("printer_backend", self.printer_backend.currentText())
        self.settings.set("printer_host", self.printer_host.text())
        self.settings.set("printer_port", self.printer_port.text())
        self.settings.set("label_width_mm", self.label_width.text())
        self.settings.set("label_height_mm", self.label_height.text())
        self.settings.set("web_port", self.web_port.text())
        self.settings.set("backup_enabled", "true" if self.backup_enabled.isChecked() else "false")
        self.settings.set("backup_interval_hours", str(self.backup_interval.value()))
        QMessageBox.information(self, "Settings Saved", "All settings have been saved successfully.")

    def _browse_credentials(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Google Drive client_secret.json", "",
            "JSON Files (*.json)"
        )
        if path:
            self.credentials_path.setText(path)

    def _backup_now(self):
        try:
            from ..database.backup import GoogleDriveBackup
            backup = GoogleDriveBackup(self.db_path)
            name = backup.backup()
            QMessageBox.information(self, "Backup Complete", f"Backup saved as: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")
