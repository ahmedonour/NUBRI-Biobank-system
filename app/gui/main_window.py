import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar,
    QLabel, QAction, QMessageBox, QApplication
)
from .label_form import LabelFormWidget
from .search_dialog import SearchWidget
from .database_view import DatabaseViewWidget
from .schema_manager import SchemaManagerWidget
from .settings_widget import SettingsWidget
from .login_dialog import LoginDialog
from ..web import WebServer
from ..database.connection import DatabaseConnection


class MainWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.db_path = db_path
        self.db = DatabaseConnection.get_instance(db_path)
        self.auth = None
        self.web_server = None

        self.setWindowTitle("NUBRI Biobank Label System")
        self.setMinimumSize(900, 700)

        if not self._authenticate():
            sys.exit(0)

        self._setup_ui()
        self._setup_menu()
        self._start_web_server()

    def _authenticate(self):
        dialog = LoginDialog(db=self.db, parent=self)
        if dialog.exec_() == LoginDialog.Accepted:
            self.auth = dialog.auth
            return True
        return False

    def _setup_ui(self):
        self.tabs = QTabWidget()

        self.label_form = LabelFormWidget(self.db)
        self.search_widget = SearchWidget(self.db)
        self.database_view = DatabaseViewWidget(self.db)
        self.schema_manager = SchemaManagerWidget(self.db)
        self.settings_widget = SettingsWidget(self.db, self.db_path)

        self.tabs.addTab(self.label_form, "Create Label")
        self.tabs.addTab(self.search_widget, "Search / Scan")
        self.tabs.addTab(self.database_view, "Database")
        self.tabs.addTab(self.schema_manager, "Manage Columns")
        self.tabs.addTab(self.settings_widget, "Settings")

        self.label_form.label_created.connect(self._on_label_created)
        self.label_form.label_created.connect(lambda _: self.database_view._load())
        self.schema_manager.schema_changed.connect(lambda: self.label_form.refresh())
        self.setCentralWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        self._update_user_status()

    def _update_user_status(self):
        if self.auth and self.auth.is_authenticated:
            name = self.auth.get_user_name()
            self.user_label = QLabel(f"Signed in as: {name}")
            self.user_label.setStyleSheet("color: #4caf50; font-weight: bold; padding: 0 10px;")
            self.status_bar.addPermanentWidget(self.user_label)
        else:
            self.user_label = QLabel("Not signed in")
            self.user_label.setStyleSheet("color: #ef5350; padding: 0 10px;")
            self.status_bar.addPermanentWidget(self.user_label)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        signout_action = QAction("Sign Out", self)
        signout_action.setShortcut("Ctrl+Shift+S")
        signout_action.triggered.connect(self._sign_out)
        file_menu.addAction(signout_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("Tools")
        refresh_action = QAction("Refresh Forms", self)
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self._refresh_all)
        tools_menu.addAction(refresh_action)

        backup_action = QAction("Backup Database Now", self)
        backup_action.triggered.connect(self._backup_now)
        tools_menu.addAction(backup_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _sign_out(self):
        reply = QMessageBox.question(
            self, "Sign Out",
            "Are you sure you want to sign out?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.auth:
                self.auth.logout()
            if self.web_server:
                self.web_server.stop()
                self.web_server = None
            self.close()
            new_window = MainWindow(db_path=self.db_path)
            new_window.show()

    def _start_web_server(self):
        try:
            from ..database.models import SettingsModel
            settings = SettingsModel(self.db)
            port = int(settings.get("web_port", "5000"))
            self.web_server = WebServer(self.db, port=port, auth=self.auth)
            self.web_server.start()
            ip = self._get_local_ip()
            self.status_label.setText(f"Web preview: http://{ip}:{port}")
        except Exception as e:
            self.status_label.setText(f"Web server failed: {str(e)}")

    def _get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _on_label_created(self, qr_code):
        self.status_label.setText(f"Last label created: {qr_code}")

    def _refresh_all(self):
        self.label_form.refresh()
        self.database_view._load()
        self.status_label.setText("Forms refreshed")

    def _backup_now(self):
        try:
            from ..database.backup import GoogleDriveBackup
            backup = GoogleDriveBackup(self.db_path)
            name = backup.backup()
            QMessageBox.information(self, "Backup Complete", f"Backup saved as: {name}")
        except FileNotFoundError:
            QMessageBox.warning(
                self, "Credentials Missing",
                "Place your Google Drive client_secret.json in the credentials/ folder."
            )
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    def _show_about(self):
        QMessageBox.about(
            self, "About NUBRI Biobank Label System",
            "NUBRI Biobank Label System v1.0\n\n"
            "Desktop application for generating and managing\n"
            "biobank specimen labels with QR codes.\n\n"
            "Features:\n"
            "- SQLite user authentication\n"
            "- Customizable specimen fields\n"
            "- QR code generation & scanning\n"
            "- Xprinter thermal label printing\n"
            "- Mobile web preview with QR lookup\n"
            "- Google Drive backup"
        )

    def closeEvent(self, event):
        if self.web_server:
            self.web_server.stop()
        event.accept()
