from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox,
    QStackedWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class LoginDialog(QDialog):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.auth = None
        self.setWindowTitle("NUBRI Biobank — Sign In")
        self.setFixedSize(420, 520)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel("NUBRI Biobank System")
        title.setFont(QFont("", 18, QFont.Bold))
        title.setStyleSheet("color: #4da6ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.stack.addWidget(self._login_page())
        self.stack.addWidget(self._signup_page())

        layout.addSpacing(5)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ef5350; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _style_input(self):
        return ""

    def _style_btn(self, color="#4da6ff"):
        return f"""
            QPushButton {{
                background-color: {color}; color: white; padding: 14px;
                border: none; border-radius: 6px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self._darken(color)}; }}
            QPushButton:disabled {{ background-color: #555; }}
        """

    @staticmethod
    def _darken(hex_color):
        c = hex_color.lstrip("#")
        r = max(int(c[0:2], 16) - 30, 0)
        g = max(int(c[2:4], 16) - 30, 0)
        b = max(int(c[4:6], 16) - 30, 0)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Login page ────────────────────────────────────────────────────

    def _login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)

        subtitle = QLabel("Sign in to continue")
        subtitle.setStyleSheet("color: #9e9e9e; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email")
        layout.addWidget(self.login_email)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.returnPressed.connect(self._login)
        layout.addWidget(self.login_password)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setStyleSheet(self._style_btn())
        self.login_btn.clicked.connect(self._login)
        layout.addWidget(self.login_btn)

        self.switch_to_signup_btn = QPushButton("Create an account")
        self.switch_to_signup_btn.setStyleSheet(
            "QPushButton { background: none; border: none; color: #4da6ff; "
            "font-size: 12px; text-decoration: underline; padding: 5px; }"
        )
        self.switch_to_signup_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(self.switch_to_signup_btn, alignment=Qt.AlignCenter)

        return page

    # ── Sign up page ──────────────────────────────────────────────────

    def _signup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)

        subtitle = QLabel("Create a new account")
        subtitle.setStyleSheet("color: #9e9e9e; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        self.signup_name = QLineEdit()
        self.signup_name.setPlaceholderText("Full name (optional)")
        layout.addWidget(self.signup_name)

        self.signup_email = QLineEdit()
        self.signup_email.setPlaceholderText("Email")
        layout.addWidget(self.signup_email)

        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Password (min 4 characters)")
        self.signup_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.signup_password)

        self.signup_confirm = QLineEdit()
        self.signup_confirm.setPlaceholderText("Confirm password")
        self.signup_confirm.setEchoMode(QLineEdit.Password)
        self.signup_confirm.returnPressed.connect(self._signup)
        layout.addWidget(self.signup_confirm)

        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setStyleSheet(self._style_btn("#4caf50"))
        self.signup_btn.clicked.connect(self._signup)
        layout.addWidget(self.signup_btn)

        self.back_to_login_btn = QPushButton("Already have an account? Sign in")
        self.back_to_login_btn.setStyleSheet(
            "QPushButton { background: none; border: none; color: #4da6ff; "
            "font-size: 12px; text-decoration: underline; padding: 5px; }"
        )
        self.back_to_login_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(self.back_to_login_btn, alignment=Qt.AlignCenter)

        return page

    # ── Actions ───────────────────────────────────────────────────────

    def _login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text()

        if not email or not password:
            self.status_label.setText("Please fill in all fields.")
            return

        self._set_loading(True, "Signing in...")
        from ..database.auth import AuthManager

        try:
            self.auth = AuthManager(self.db)
            self.auth.login(email, password)
            self.accept()
        except PermissionError as e:
            self.status_label.setText(str(e))
            self._set_loading(False, "Sign In")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self._set_loading(False, "Sign In")

    def _signup(self):
        name = self.signup_name.text().strip()
        email = self.signup_email.text().strip()
        password = self.signup_password.text()
        confirm = self.signup_confirm.text()

        if not email or not password:
            self.status_label.setText("Email and password are required.")
            return
        if password != confirm:
            self.status_label.setText("Passwords do not match.")
            return
        if len(password) < 4:
            self.status_label.setText("Password must be at least 4 characters.")
            return

        self._set_loading(True, "Creating account...")
        from ..database.auth import AuthManager

        try:
            self.auth = AuthManager(self.db)
            self.auth.signup(email, password, name)
            self.accept()
        except ValueError as e:
            self.status_label.setText(str(e))
            self._set_loading(False, "Create Account")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self._set_loading(False, "Create Account")

    def _set_loading(self, loading, text):
        if self.stack.currentIndex() == 0:
            self.login_btn.setEnabled(not loading)
            self.login_btn.setText(text)
        else:
            self.signup_btn.setEnabled(not loading)
            self.signup_btn.setText(text)
