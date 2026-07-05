from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox,
    QDialogButtonBox, QSpacerItem, QSizePolicy, QCheckBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth = None
        self.settings = QSettings("NUBRI", "Biobank")
        self.setWindowTitle("Sign In — NUBRI Biobank")
        self.setFixedSize(420, 340)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #fafafa;
            }
        """)
        self._setup_ui()
        self._load_saved()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel("NUBRI Biobank System")
        title.setFont(QFont("", 18, QFont.Bold))
        title.setStyleSheet("color: #1a73e8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sign in with your PocketBase account")
        subtitle.setStyleSheet("color: #666; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(15)

        form = QFormLayout()
        form.setSpacing(8)

        self.server_url = QLineEdit()
        self.server_url.setPlaceholderText("http://127.0.0.1:8090")
        self.server_url.setStyleSheet(self._input_style())
        form.addRow("Server URL:", self.server_url)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your@email.com")
        self.email_input.setStyleSheet(self._input_style())
        form.addRow("Email:", self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.returnPressed.connect(self._login)
        form.addRow("Password:", self.password_input)

        self.remember_check = QCheckBox("Remember server URL")
        self.remember_check.setStyleSheet("color: #555;")
        form.addRow("", self.remember_check)

        layout.addLayout(form)
        layout.addSpacing(10)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white; padding: 12px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1557b0; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.login_btn.clicked.connect(self._login)
        layout.addWidget(self.login_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _input_style(self):
        return """
            QLineEdit {
                padding: 8px 12px; border: 2px solid #ddd;
                border-radius: 6px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a73e8; }
        """

    def _load_saved(self):
        saved_url = self.settings.value("pocketbase_url", "")
        if saved_url:
            self.server_url.setText(saved_url)
            self.remember_check.setChecked(True)

    def _login(self):
        server_url = self.server_url.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not server_url or not email or not password:
            self.status_label.setText("Please fill in all fields.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")
        self.status_label.setText("")

        from ..auth.pocketbase_client import PocketBaseAuth

        try:
            self.auth = PocketBaseAuth(base_url=server_url)
            self.auth.login(email, password)

            if self.remember_check.isChecked():
                self.settings.setValue("pocketbase_url", server_url)
            else:
                self.settings.remove("pocketbase_url")

            self.accept()
        except PermissionError as e:
            self.status_label.setText(str(e))
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")
        except Exception as e:
            self.status_label.setText(f"Connection error: {str(e)}")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")
