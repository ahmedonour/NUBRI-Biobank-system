from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QCheckBox, QMessageBox, QGroupBox, QSpinBox,
    QFileDialog, QScrollArea
)
from ..database.models import SettingsModel, SpecimenModel
from ..database.connection import load_db_config, save_db_config


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
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4da6ff; margin-bottom: 10px; overflow:scroll;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)

        printer_group = QGroupBox("Printer Settings")
        printer_group.setMinimumHeight(200)
        printer_layout = QFormLayout(printer_group)

        self.printer_mode = QComboBox()
        self.printer_mode.addItems(["System Printer", "Thermal (ESC/POS)"])
        self.printer_mode.currentIndexChanged.connect(self._on_printer_mode_change)
        printer_layout.addRow("Printer Mode:", self.printer_mode)

        self.thermal_widget = QWidget()
        thermal_layout = QFormLayout(self.thermal_widget)
        thermal_layout.setContentsMargins(0, 0, 0, 0)

        self.printer_backend = QComboBox()
        self.printer_backend.addItems(["network", "usb", "serial"])
        thermal_layout.addRow("Connection Type:", self.printer_backend)

        self.printer_host = QLineEdit()
        self.printer_host.setPlaceholderText("e.g. 192.168.1.100")
        thermal_layout.addRow("Host / IP:", self.printer_host)

        self.printer_port = QLineEdit()
        self.printer_port.setPlaceholderText("e.g. 9100")
        thermal_layout.addRow("Port:", self.printer_port)

        printer_layout.addRow(self.thermal_widget)

        size_row = QHBoxLayout()
        self.label_width = QSpinBox()
        self.label_width.setRange(10, 200)
        self.label_width.setSuffix(" mm")
        self.label_width.setValue(40)
        self.label_height = QSpinBox()
        self.label_height.setRange(5, 150)
        self.label_height.setSuffix(" mm")
        self.label_height.setValue(13)
        size_row.addWidget(QLabel("W:"))
        size_row.addWidget(self.label_width)
        size_row.addWidget(QLabel("H:"))
        size_row.addWidget(self.label_height)
        size_row.addStretch()
        printer_layout.addRow("Label Size:", size_row)

        gap_row = QHBoxLayout()
        self.label_gap = QSpinBox()
        self.label_gap.setRange(0, 20)
        self.label_gap.setSuffix(" mm")
        self.label_gap.setValue(3)
        gap_row.addWidget(self.label_gap)
        gap_row.addStretch()
        printer_layout.addRow("Gap between:", gap_row)

        self.design_btn = QPushButton("Design Label Layout")
        self.design_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800; color: white; padding: 0px 0px;
                border: none; border-radius: 6px; font-weight: bold; height: 40px; width: 150px;
            }
            QPushButton:hover { background-color: #f57c00; }
        """)
        self.design_btn.clicked.connect(self._open_designer)
        printer_layout.addRow("", self.design_btn)

        printer_note = QLabel(
            "Thermal mode: Xprinter ESC/POS via network/USB/serial.\n"
            "System mode: uses your OS print dialog (labels print at 50×30mm)."
        )
        printer_note.setStyleSheet("color: #9e9e9e; font-size: 11px; font-weight: normal; margin-top: 5px;")
        printer_note.setWordWrap(True)
        printer_layout.addRow(printer_note)

        content_layout.addWidget(printer_group)

        web_group = QGroupBox("Web Preview Server")
        # web_group.setMinimumHeight(300)
        # web_group.setStyleSheet("height: 150px;")
        web_layout = QFormLayout(web_group)

        self.web_port = QLineEdit()
        self.web_port.setPlaceholderText("e.g. 5000")
        web_layout.addRow("Port:", self.web_port)

        web_note = QLabel("Open http://<your-computer-ip>:<port> on your phone/tablet "
                          "to scan QR codes and view specimen details.")
        web_note.setStyleSheet("color: #9e9e9e; font-size: 11px; font-weight: normal;")
        web_note.setWordWrap(True)
        web_layout.addRow(web_note)

        content_layout.addWidget(web_group)

        backup_group = QGroupBox("Google Drive Backup")
        backup_layout = QFormLayout(backup_group)

        self.backup_enabled = QCheckBox("Enable automatic backups")
        backup_layout.addRow("", self.backup_enabled)

        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 168)
        self.backup_interval.setSuffix(" hours")
        backup_layout.addRow("Backup Interval:", self.backup_interval)

        self.credentials_path = QLineEdit()
        self.credentials_path.setPlaceholderText("Path to client_secret.json")
        self.credentials_path.setStyleSheet("width: 300px;")
        backup_layout.addRow("Credentials:", self.credentials_path)

        self.browse_creds_btn = QPushButton("Browse")
        self.browse_creds_btn.clicked.connect(self._browse_credentials)
        backup_layout.addRow("", self.browse_creds_btn)

        self.backup_now_btn = QPushButton("Backup Now")
        self.backup_now_btn.clicked.connect(self._backup_now)
        backup_layout.addRow("", self.backup_now_btn)

        content_layout.addWidget(backup_group)

        db_group = QGroupBox("Database")
        db_layout = QVBoxLayout(db_group)

        conn_status = "PostgreSQL" if self.db.db_type == 'postgresql' else "SQLite"
        self.conn_status_label = QLabel(f"Current connection: {conn_status}")
        self.conn_status_label.setStyleSheet("font-weight: bold; color: #4da6ff;")
        db_layout.addWidget(self.conn_status_label)

        pg_form = QFormLayout()
        self.pg_url_input = QLineEdit()
        self.pg_url_input.setPlaceholderText("postgresql://user:password@host:5432/dbname")
        pg_form.addRow("PostgreSQL URL:", self.pg_url_input)

        pg_btn_row = QHBoxLayout()
        self.connect_pg_btn = QPushButton("Connect to PostgreSQL")
        self.connect_pg_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 8px 16px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.connect_pg_btn.clicked.connect(self._connect_postgresql)
        pg_btn_row.addWidget(self.connect_pg_btn)

        self.disconnect_pg_btn = QPushButton("Use SQLite Instead")
        self.disconnect_pg_btn.setStyleSheet("""
            QPushButton {
                background-color: #666; color: white; padding: 8px 16px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #555; }
        """)
        self.disconnect_pg_btn.clicked.connect(self._disconnect_postgresql)
        pg_btn_row.addWidget(self.disconnect_pg_btn)

        db_layout.addLayout(pg_form)
        db_layout.addLayout(pg_btn_row)
        db_layout.addWidget(QLabel("Changes take effect after restarting the app."))

        db_layout.addSpacing(16)

        self.delete_all_btn = QPushButton("Delete All Data")
        self.delete_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        self.delete_all_btn.clicked.connect(self._delete_all_data)
        db_layout.addWidget(self.delete_all_btn)
        db_layout.addWidget(QLabel("Permanently deletes all specimen records. This cannot be undone."))
        content_layout.addWidget(db_group)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        content_layout.addLayout(btn_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _load_settings(self):
        all_settings = self.settings.get_all()
        mode = all_settings.get("printer_mode", "system")
        self.printer_mode.setCurrentIndex(0 if mode == "system" else 1)
        self.printer_backend.setCurrentText(all_settings.get("printer_backend", "network"))
        self.printer_host.setText(all_settings.get("printer_host", ""))
        self.printer_port.setText(all_settings.get("printer_port", "9100"))

        self.label_width.setValue(int(all_settings.get("label_width_mm", "40")))
        self.label_height.setValue(int(all_settings.get("label_height_mm", "13")))
        self.label_gap.setValue(int(all_settings.get("label_gap_mm", "3")))

        self.web_port.setText(all_settings.get("web_port", "5000"))
        self.backup_enabled.setChecked(all_settings.get("backup_enabled", "false") == "true")
        self.backup_interval.setValue(int(all_settings.get("backup_interval_hours", "24")))

        cfg = load_db_config()
        saved_url = cfg.get("postgresql_url", "")
        if saved_url:
            self.pg_url_input.setText(saved_url)
        self._on_printer_mode_change()

    def _on_printer_mode_change(self):
        is_thermal = self.printer_mode.currentIndex() == 1
        self.thermal_widget.setVisible(is_thermal)

    def _open_designer(self):
        from .label_designer import LabelDesignerDialog
        dlg = LabelDesignerDialog(db=self.db, parent=self)
        dlg.exec_()

    def _save_settings(self):
        mode = "system" if self.printer_mode.currentIndex() == 0 else "thermal"
        self.settings.set("printer_mode", mode)
        self.settings.set("printer_backend", self.printer_backend.currentText())
        self.settings.set("printer_host", self.printer_host.text())
        self.settings.set("printer_port", self.printer_port.text())

        self.settings.set("label_width_mm", str(self.label_width.value()))
        self.settings.set("label_height_mm", str(self.label_height.value()))
        self.settings.set("label_gap_mm", str(self.label_gap.value()))

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

    def _connect_postgresql(self):
        url = self.pg_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a PostgreSQL connection URL.")
            return
        if not url.startswith("postgresql://"):
            QMessageBox.warning(self, "Invalid URL", "URL must start with postgresql://")
            return
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect:\n{e}")
            return
        save_db_config({"postgresql_url": url})
        QMessageBox.information(
            self, "Saved",
            "PostgreSQL URL saved. Restart the app to connect."
        )

    def _disconnect_postgresql(self):
        save_db_config({})
        self.pg_url_input.clear()
        QMessageBox.information(
            self, "Disconnected",
            "PostgreSQL configuration removed. Restart the app to use SQLite."
        )

    def _delete_all_data(self):
        reply = QMessageBox.warning(
            self, "Delete All Data",
            "Are you sure you want to delete ALL specimen data?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            confirm = QMessageBox.question(
                self, "Confirm",
                "Type YES to confirm permanent deletion of all records.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    model = SpecimenModel(self.db)
                    model.delete_all()
                    QMessageBox.information(self, "Deleted", "All specimen data has been deleted.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

    def _backup_now(self):
        try:
            from ..database.backup import GoogleDriveBackup
            backup = GoogleDriveBackup(self.db_path)
            name = backup.backup()
            QMessageBox.information(self, "Backup Complete", f"Backup saved as: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")
