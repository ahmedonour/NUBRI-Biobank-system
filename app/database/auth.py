import hashlib
import os
import uuid
from datetime import datetime, timedelta
from .connection import DatabaseConnection


class AuthManager:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()
        self._current_user = None

    # ── Password hashing ───────────────────────────────────────────────

    @staticmethod
    def _hash_password(password):
        salt = os.urandom(32).hex()
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return salt, h

    @staticmethod
    def _verify_password(password, salt, stored_hash):
        return hashlib.sha256((salt + password).encode()).hexdigest() == stored_hash

    # ── User management ────────────────────────────────────────────────

    def signup(self, email, password, name=""):
        email = email.strip().lower()
        if not email or not password:
            raise ValueError("Email and password are required.")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")

        existing = self.conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise ValueError(f"User '{email}' already exists.")

        salt, h = self._hash_password(password)
        self.conn.execute(
            "INSERT INTO users (email, password_hash, salt, name) VALUES (?, ?, ?, ?)",
            (email, h, salt, name)
        )
        self.conn.commit()
        return self._login_after_signup(email)

    def login(self, email, password):
        email = email.strip().lower()
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            raise PermissionError("Invalid email or password.")

        if not self._verify_password(password, row["salt"], row["password_hash"]):
            raise PermissionError("Invalid email or password.")

        self._current_user = dict(row)
        return self._current_user

    def _login_after_signup(self, email):
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        self._current_user = dict(row) if row else None
        return self._current_user

    def logout(self):
        self._current_user = None

    @property
    def is_authenticated(self):
        return self._current_user is not None

    @property
    def current_user(self):
        return self._current_user

    def get_user_email(self):
        return self._current_user.get("email", "") if self._current_user else ""

    def get_user_name(self):
        return self._current_user.get("name", self.get_user_email()) if self._current_user else ""

    # ── Session tokens (for web auth) ──────────────────────────────────

    def create_session(self, user_id, expiry_hours=24):
        token = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        self.conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at)
        )
        self.conn.commit()
        return token

    def validate_session(self, token):
        now_func = "NOW()" if self.db.db_type == 'postgresql' else "datetime('now')"
        row = self.conn.execute(
            f"SELECT s.*, u.email, u.name FROM sessions s "
            f"JOIN users u ON u.id = s.user_id "
            f"WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > {now_func})",
            (token,)
        ).fetchone()
        if row:
            return {"id": row["user_id"], "email": row["email"], "name": row["name"]}
        return None

    def delete_session(self, token):
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.conn.commit()
