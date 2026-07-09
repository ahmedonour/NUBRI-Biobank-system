#!/usr/bin/env python3
"""
NUBRI Biobank Label System — Single-file build (customtkinter)
"""

import os, sys, json, csv, io, uuid, hashlib, base64, shutil, subprocess
import tempfile, platform, threading, socket, argparse
from datetime import datetime, timedelta
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import qrcode
from tkinter import messagebox, filedialog, colorchooser

APP_NAME = "NUBRI Biobank"
FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "biobank.db")
CONFIG_PATH = os.path.join(DB_DIR, "db_config.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Helpers ─────────────────────────────────────────────────────────

def _load_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()

def load_db_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

def save_db_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def _get_db_url():
    cfg = load_db_config()
    pg = cfg.get("postgresql_url", "").strip()
    return pg if pg else DB_PATH

# ── Database Connection ─────────────────────────────────────────────

class DatabaseConnection:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_url=None):
        self.db_url = db_url or _get_db_url()
        self.db_type = 'postgresql' if self.db_url.startswith('postgresql://') else 'sqlite'
        self._conn = None
        self._init_db()

    @classmethod
    def get_instance(cls, db_url=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_url)
        return cls._instance

    def _init_db(self):
        if self.db_type == 'postgresql':
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self._conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        else:
            import sqlite3
            self._conn = sqlite3.connect(self.db_url, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def execute(self, sql, params=None):
        if self.db_type == 'sqlite':
            if params is not None:
                return self._conn.execute(sql, params)
            return self._conn.execute(sql)
        cur = self._conn.cursor()
        pg_sql = sql.replace('?', '%s')
        cur.execute(pg_sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def get_connection(self):
        return self

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        if self.db_type == 'postgresql':
            self._create_tables_postgresql()
        else:
            self._create_tables_sqlite()

    def _create_tables_sqlite(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS column_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                column_name TEXT UNIQUE NOT NULL,
                column_type TEXT DEFAULT 'TEXT',
                display_order INTEGER DEFAULT 0,
                is_required INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS specimens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_code TEXT UNIQUE NOT NULL,
                custom_fields TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_specimens_qr ON specimens(qr_code);
            CREATE INDEX IF NOT EXISTS idx_specimens_created ON specimens(created_at);
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Sample ID', 'TEXT', 0, 1);
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Sample Type', 'TEXT', 1, 1);
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Patient Name', 'TEXT', 2, 1);
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Collection Date', 'DATE', 3, 0);
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Storage Location', 'TEXT', 4, 0);
            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Notes', 'TEXT', 5, 0);
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_backend', 'network');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_host', '192.168.1.100');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_port', '9100');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_width_mm', '35');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_height_mm', '15');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_gap_mm', '3');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('web_port', '8765');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('backup_enabled', 'false');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('backup_interval_hours', '24');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('next_sample_id', '1');
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)
        self._conn.commit()

    def _create_tables_postgresql(self):
        stmts = [
            "CREATE TABLE IF NOT EXISTS column_definitions (id SERIAL PRIMARY KEY, column_name TEXT UNIQUE NOT NULL, column_type TEXT DEFAULT 'TEXT', display_order INTEGER DEFAULT 0, is_required INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS specimens (id SERIAL PRIMARY KEY, qr_code TEXT UNIQUE NOT NULL, custom_fields TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE INDEX IF NOT EXISTS idx_specimens_qr ON specimens(qr_code);",
            "CREATE INDEX IF NOT EXISTS idx_specimens_created ON specimens(created_at);",
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Sample ID', 'TEXT', 0, 1) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Sample Type', 'TEXT', 1, 1) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Patient Name', 'TEXT', 2, 1) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Collection Date', 'DATE', 3, 0) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Storage Location', 'TEXT', 4, 0) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES ('Notes', 'TEXT', 5, 0) ON CONFLICT (column_name) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('printer_backend', 'network') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('printer_host', '192.168.1.100') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('printer_port', '9100') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('label_width_mm', '35') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('label_height_mm', '15') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('label_gap_mm', '3') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('web_port', '8765') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('backup_enabled', 'false') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('backup_interval_hours', '24') ON CONFLICT (key) DO NOTHING;",
            "INSERT INTO settings (key, value) VALUES ('next_sample_id', '1') ON CONFLICT (key) DO NOTHING;",
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, name TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS sessions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, token TEXT UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id));",
            "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        ]
        for s in stmts:
            self._conn.execute(s.strip())
        self._conn.commit()


# ── Models ───────────────────────────────────────────────────────────

class ColumnDefinition:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()

    def get_all(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM column_definitions WHERE is_active = 1 ORDER BY display_order"
        ).fetchall()]

    def add(self, name, col_type="TEXT", required=False):
        r = self.conn.execute("SELECT COALESCE(MAX(display_order), -1) + 1 AS n FROM column_definitions").fetchone()
        nxt = r["n"]
        self.conn.execute("INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES (?, ?, ?, ?)",
                          (name, col_type, nxt, 1 if required else 0))
        self.conn.commit()

    def update(self, cid, column_name=None, column_type=None, is_required=None, display_order=None):
        flds, vals = [], []
        if column_name is not None: flds.append("column_name = ?"); vals.append(column_name)
        if column_type is not None: flds.append("column_type = ?"); vals.append(column_type)
        if is_required is not None: flds.append("is_required = ?"); vals.append(1 if is_required else 0)
        if display_order is not None: flds.append("display_order = ?"); vals.append(display_order)
        if flds:
            vals.append(cid)
            self.conn.execute(f"UPDATE column_definitions SET {', '.join(flds)} WHERE id = ?", vals)
            self.conn.commit()

    def delete(self, cid):
        self.conn.execute("UPDATE column_definitions SET is_active = 0 WHERE id = ?", (cid,))
        self.conn.commit()

    def reorder(self, ordered_ids):
        for i, cid in enumerate(ordered_ids):
            self.conn.execute("UPDATE column_definitions SET display_order = ? WHERE id = ?", (i, cid))
        self.conn.commit()


class SpecimenModel:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()

    @staticmethod
    def generate_qr_code():
        return str(uuid.uuid4()).replace("-", "")[:16].upper()

    def create(self, fields):
        qr = fields.get("Sample ID") or self.generate_qr_code()
        self.conn.execute("INSERT INTO specimens (qr_code, custom_fields) VALUES (?, ?)", (qr, json.dumps(fields)))
        self.conn.commit()
        return qr

    def get_by_qr(self, qr):
        r = self.conn.execute("SELECT * FROM specimens WHERE qr_code = ?", (qr,)).fetchone()
        if r:
            d = dict(r)
            d["custom_fields"] = json.loads(d["custom_fields"])
            return d
        return None

    def get_by_id(self, sid):
        r = self.conn.execute("SELECT * FROM specimens WHERE id = ?", (sid,)).fetchone()
        if r:
            d = dict(r)
            d["custom_fields"] = json.loads(d["custom_fields"])
            return d
        return None

    def update(self, sid, fields):
        self.conn.execute("UPDATE specimens SET custom_fields = ?, updated_at = ? WHERE id = ?",
                          (json.dumps(fields), datetime.now().isoformat(), sid))
        self.conn.commit()

    def search(self, query, column_name=None):
        like = f"%{query}%"
        if column_name:
            fp = f"$.{column_name}"
            sql = "SELECT * FROM specimens WHERE json_extract(custom_fields, ?) LIKE ? ORDER BY created_at DESC"
            cur = self.conn.execute(sql, (fp, like))
        else:
            sql = "SELECT * FROM specimens WHERE qr_code LIKE ? OR custom_fields LIKE ? ORDER BY created_at DESC"
            cur = self.conn.execute(sql, (like, like))
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["custom_fields"] = json.loads(d["custom_fields"])
            res.append(d)
        return res

    def get_all(self, limit=100, offset=0):
        cur = self.conn.execute("SELECT * FROM specimens ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["custom_fields"] = json.loads(d["custom_fields"])
            res.append(d)
        return res

    def count(self):
        return self.conn.execute("SELECT COUNT(*) AS c FROM specimens").fetchone()["c"]

    def get_all_unpaginated(self):
        cur = self.conn.execute("SELECT * FROM specimens ORDER BY created_at DESC")
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["custom_fields"] = json.loads(d["custom_fields"])
            res.append(d)
        return res

    def export_to_csv(self, path, columns):
        names = [c["column_name"] for c in columns]
        specs = self.get_all_unpaginated()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["QR Code"] + names + ["Created", "Updated"])
            for s in specs:
                cf = s["custom_fields"]
                w.writerow([s["qr_code"]] + [cf.get(n, "") for n in names] + [s.get("created_at", ""), s.get("updated_at", "")])

    def import_from_csv(self, path, columns):
        names = [c["column_name"] for c in columns]
        imported, errors = 0, []
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("Empty CSV file")
            for num, row in enumerate(reader, 2):
                try:
                    data = {n: row.get(n, "").strip() for n in names}
                    qr = row.get("QR Code", "").strip()
                    if qr:
                        ex = self.get_by_qr(qr)
                        if ex:
                            self.update(ex["id"], data)
                        else:
                            self.conn.execute("INSERT INTO specimens (qr_code, custom_fields) VALUES (?, ?)", (qr, json.dumps(data)))
                    else:
                        self.create(data)
                    self.conn.commit()
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {num}: {e}")
        return imported, errors

    @staticmethod
    def get_template_csv(columns):
        names = [c["column_name"] for c in columns]
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["QR Code"] + names + ["Created", "Updated"])
        w.writerow(["NU0000000001"] + [""] * (len(names) + 2))
        return out.getvalue()

    def delete_all(self):
        self.conn.execute("DELETE FROM specimens")
        if self.db.db_type == 'postgresql':
            self.conn.execute("ALTER SEQUENCE specimens_id_seq RESTART WITH 1")
        else:
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name='specimens'")
        self.conn.commit()


class SettingsModel:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()

    def get(self, key, default=None):
        r = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return r["value"] if r else default

    def set(self, key, value):
        if self.db.db_type == 'postgresql':
            self.conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, str(value)))
        else:
            self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    def get_all(self):
        return {r["key"]: r["value"] for r in self.conn.execute("SELECT * FROM settings").fetchall()}

    def get_next_sample_id(self):
        raw = self.get("next_sample_id", "1")
        try: num = int(raw)
        except ValueError: num = 1
        return f"NU{num:010d}"

    def increment_next_sample_id(self):
        raw = self.get("next_sample_id", "1")
        try: num = int(raw)
        except ValueError: num = 1
        self.set("next_sample_id", str(num + 1))


# ── Authentication ──────────────────────────────────────────────────

class AuthManager:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()
        self._current_user = None

    @staticmethod
    def _hash_password(password):
        salt = os.urandom(32).hex()
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return salt, h

    @staticmethod
    def _verify_password(password, salt, stored):
        return hashlib.sha256((salt + password).encode()).hexdigest() == stored

    def signup(self, email, password, name=""):
        email = email.strip().lower()
        if not email or not password:
            raise ValueError("Email and password are required.")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")
        ex = self.conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if ex:
            raise ValueError(f"User '{email}' already exists.")
        salt, h = self._hash_password(password)
        self.conn.execute("INSERT INTO users (email, password_hash, salt, name) VALUES (?, ?, ?, ?)", (email, h, salt, name))
        self.conn.commit()
        return self._login_after_signup(email)

    def login(self, email, password):
        email = email.strip().lower()
        r = self.conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not r:
            raise PermissionError("Invalid email or password.")
        if not self._verify_password(password, r["salt"], r["password_hash"]):
            raise PermissionError("Invalid email or password.")
        self._current_user = dict(r)
        return self._current_user

    def _login_after_signup(self, email):
        r = self.conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        self._current_user = dict(r) if r else None
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

    def create_session(self, user_id, expiry_hours=24):
        token = str(uuid.uuid4())
        expires = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        self.conn.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (user_id, token, expires))
        self.conn.commit()
        return token

    def validate_session(self, token):
        now = "NOW()" if self.db.db_type == 'postgresql' else "datetime('now')"
        r = self.conn.execute(
            f"SELECT s.*, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > {now})",
            (token,)
        ).fetchone()
        if r:
            return {"id": r["user_id"], "email": r["email"], "name": r["name"]}
        return None

    def delete_session(self, token):
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.conn.commit()


# ── Google Drive Backup ─────────────────────────────────────────────

class GoogleDriveBackup:
    def __init__(self, db_url, credentials_dir=None):
        self.db_url = db_url
        self.is_postgresql = db_url.startswith("postgresql://")
        if credentials_dir is None:
            credentials_dir = os.path.join(DB_DIR, "credentials")
        self.credentials_dir = credentials_dir
        self.token_path = os.path.join(credentials_dir, "token.json")
        self.creds_path = os.path.join(credentials_dir, "client_secret.json")
        self.service = None

    def _authenticate(self):
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.creds_path):
                    raise FileNotFoundError(f"Google Drive client_secret.json not found. Place it in: {self.credentials_dir}")
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())
        self.service = build("drive", "v3", credentials=creds)

    def _ensure_backup_folder(self):
        from googleapiclient.discovery import build
        q = "name='BiobankBackups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        res = self.service.files().list(q=q, spaces="drive", fields="files(id)").execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        f = self.service.files().create(body={"name": "BiobankBackups", "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()
        return f["id"]

    def _create_backup_file(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.is_postgresql:
            name = f"biobank_pg_backup_{ts}.dump"
            tmp = tempfile.NamedTemporaryFile(suffix=".dump", delete=False)
            tmp.close()
            try:
                subprocess.run(["pg_dump", "--no-owner", "--no-acl", "-Fc", self.db_url, "-f", tmp.name], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                os.unlink(tmp.name); raise RuntimeError(f"pg_dump failed: {e.stderr}") from e
            except FileNotFoundError:
                os.unlink(tmp.name); raise RuntimeError("pg_dump not found. Install PostgreSQL client tools.")
            return tmp.name, name
        name = f"biobank_backup_{ts}.db"
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        shutil.copy2(self.db_url, tmp.name)
        tmp.close()
        return tmp.name, name

    def backup(self):
        from googleapiclient.http import MediaFileUpload
        if not self.service:
            self._authenticate()
        fid = self._ensure_backup_folder()
        tmp, name = self._create_backup_file()
        try:
            media = MediaFileUpload(tmp, mimetype="application/octet-stream", resumable=True)
            self.service.files().create(body={"name": name, "parents": [fid]}, media_body=media).execute()
        finally:
            os.unlink(tmp)
        return name

    def list_backups(self):
        if not self.service:
            self._authenticate()
        fid = self._ensure_backup_folder()
        res = self.service.files().list(q=f"'{fid}' in parents and trashed=false", spaces="drive", orderBy="createdTime desc", fields="files(id, name, createdTime, size)").execute()
        return res.get("files", [])

    def restore(self, file_id, restore_path):
        from googleapiclient.http import MediaIoBaseDownload
        if not self.service:
            self._authenticate()
        req = self.service.files().get_media(fileId=file_id)
        with open(restore_path, "wb") as f:
            dl = MediaIoBaseDownload(f, req)
            done = False
            while not done:
                _, done = dl.next_chunk()


# ── QR Handler ──────────────────────────────────────────────────────

class QRHandler:
    @staticmethod
    def generate(data, box_size=10, border=2):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=border)
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    @staticmethod
    def generate_base64(data, box_size=10, border=2):
        img = QRHandler.generate(data, box_size, border)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def decode_from_camera(timeout=30):
        import cv2
        from pyzbar.pyzbar import decode as pyzbar_decode
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while timeout > 0:
            ret, frame = cap.read()
            if not ret:
                continue
            results = pyzbar_decode(frame)
            for r in results:
                cap.release()
                cv2.destroyAllWindows()
                return r.data.decode("utf-8")
            cv2.imshow("QR Scanner - Press ESC to cancel", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
            timeout -= 0.05
        cap.release()
        cv2.destroyAllWindows()
        return None


# ── Label Printer ───────────────────────────────────────────────────

DEFAULT_TEMPLATE = {
    "width_mm": 35, "height_mm": 15, "show_qr": True, "show_qr_code": False,
    "show_sample_id": True, "barcode_height_pct": 60, "barcode_width_pct": 90,
    "qr_code_size_pct": 40, "bg_color": "#ffffff", "text_color": "#000000",
}

class LabelRenderer:
    def __init__(self, width_mm=35, height_mm=15, dpi=203):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.dpi = dpi

    @property
    def width_px(self):
        return int(self.width_mm / 25.4 * self.dpi)

    @property
    def height_px(self):
        return int(self.height_mm / 25.4 * self.dpi)

    def render(self, qr_code, fields_dict, max_fields=None, template=None):
        tpl = dict(DEFAULT_TEMPLATE)
        if template:
            tpl.update(template)
        w, h = self.width_px, self.height_px
        img = Image.new("RGB", (w, h), tpl["bg_color"])
        draw = ImageDraw.Draw(img)
        margin = max(1, int(h * 3 / 100))
        gap = max(2, int(h * 2 / 100))
        qr_gap = max(4, int(h * 4 / 100))
        show_bc = tpl.get("show_qr", True)
        show_qr_flag = tpl.get("show_qr_code", False)
        barcode_data = fields_dict.get("Sample ID", qr_code) or ""
        bar_h = bar_w = bar_x = bar_y = qr_size = qr_x = qr_y = 0
        bar_y = margin
        qr_y = margin
        if show_bc:
            bar_h = min(int(h * tpl.get("barcode_height_pct", 60) / 100), h - 2 * margin)
            bar_w = max(int(w * tpl.get("barcode_width_pct", 90) / 100), 1)
        if show_qr_flag:
            qr_size = min(max(int(h * tpl.get("qr_code_size_pct", 40) / 100), 1), h - 2 * margin)
        group_w = (bar_w if show_bc else 0) + (qr_gap if show_bc and show_qr_flag else 0) + (qr_size if show_qr_flag else 0)
        group_x = (w - group_w) // 2
        content_bottom = margin
        if show_bc:
            bar_x = group_x
            self._draw_code128(draw, barcode_data, bar_x, bar_y, bar_w, bar_h)
            content_bottom = bar_y + bar_h
        if show_qr_flag:
            qr_x = (bar_x + bar_w + qr_gap) if show_bc else group_x
            qr_y = bar_y + (bar_h - qr_size) // 2 if (show_bc and bar_h > 0) else margin
            self._draw_qr_code(img, barcode_data, qr_x, qr_y, qr_size)
            content_bottom = max(content_bottom, qr_y + qr_size)
        if tpl.get("show_sample_id", True) and barcode_data:
            text_y = content_bottom + gap
            avail = h - text_y - margin
            if avail > 6:
                font_scale = tpl.get("font_scale", 100) / 100.0
                fs = max(6, int(min(avail * 0.9 * font_scale, int(w * 0.15 * font_scale))))
                font = _load_font(fs)
                tw = draw.textlength(barcode_data, font)
                draw.text(((w - tw) / 2, text_y), barcode_data, fill=tpl["text_color"], font=font)
        return img

    def _draw_qr_code(self, img, data, x, y, size):
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=0)
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_img = qr_img.resize((size, size), Image.LANCZOS)
        img.paste(qr_img, (x, y))

    def _draw_code128(self, draw, data, x, y, width, height):
        import barcode
        code128 = barcode.get_barcode_class("code128")
        pattern = code128(data).build()[0]
        total = len(pattern)
        bounds = [int(x + i * width / total) for i in range(total + 1)]
        for i, bit in enumerate(pattern):
            if bit == "1":
                x1, x2 = bounds[i], bounds[i + 1]
                if x2 > x1:
                    draw.rectangle([x1, y, x2 - 1, y + height], fill="black")


class ThermalPrinter:
    def __init__(self, backend="network", host="192.168.1.100", port=9100):
        self.backend = backend
        self.host = host
        self.port = port
        self._printer = None

    def connect(self):
        from escpos.printer import Network, Usb, Serial
        if self.backend == "network":
            self._printer = Network(self.host, port=self.port)
        elif self.backend == "usb":
            self._printer = Usb(0x0416, 0x5011, timeout=5)
        elif self.backend == "serial":
            self._printer = Serial(devfile="/dev/ttyS0", baudrate=9600)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def disconnect(self):
        if self._printer:
            self._printer.close()
            self._printer = None

    def print_label(self, img, copies=1, gap_mm=0):
        if not self._printer:
            self.connect()
        gap_px = int(gap_mm / 25.4 * 203) if gap_mm > 0 else 0
        th = img.height * copies + gap_px * (copies - 1)
        combined = Image.new("RGB", (img.width, max(1, th)), "white")
        for i in range(copies):
            combined.paste(img, (0, i * (img.height + gap_px)))
        path = os.path.join(tempfile.gettempdir(), f"thermal_label_{id(img)}_combined.png")
        combined.save(path)
        self._printer.image(path)
        os.unlink(path)
        self._printer.cut()


def print_label(qr_code, fields_dict, printer_mode="system", printer_name=None,
                backend="network", host="192.168.1.100", port=9100,
                thermal_copies=1, label_width_mm=35, label_height_mm=15,
                label_gap_mm=3, template=None):
    renderer = LabelRenderer(width_mm=label_width_mm, height_mm=label_height_mm)
    img = renderer.render(qr_code, fields_dict, template=template)
    if printer_mode == "thermal":
        tp = ThermalPrinter(backend, host, port)
        try:
            tp.print_label(img, copies=thermal_copies, gap_mm=label_gap_mm)
        finally:
            tp.disconnect()
    else:
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt5.QtGui import QPixmap, QPainter
            from PyQt5.QtCore import Qt, QSizeF
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            printer = QPrinter(QPrinter.HighResolution)
            printer.setFullPage(True)
            printer.setPaperSize(QSizeF(label_width_mm, label_height_mm), QPrinter.Millimeter)
            printer.setCopyCount(thermal_copies)
            if printer_name:
                printer.setPrinterName(printer_name)
            dialog = QPrintDialog(printer)
            if dialog.exec_() != QPrintDialog.Accepted:
                return
            pixmap = QPixmap.fromImage(_pil_to_qimage(img))
            painter = QPainter(printer)
            try:
                pr = printer.pageRect(QPrinter.DevicePixel)
                scaled = pixmap.scaled(pr.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, scaled)
            finally:
                painter.end()
        except Exception:
            tmp = os.path.join(tempfile.gettempdir(), f"label_{qr_code}.png")
            img.save(tmp)
            if platform.system() == "Darwin":
                subprocess.run(["open", tmp])
            elif platform.system() == "Windows":
                os.startfile(tmp, "print")
            else:
                subprocess.run(["xdg-open", tmp])


def _pil_to_qimage(img):
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    from PyQt5.QtGui import QImage
    return QImage(data, img.width, img.height, QImage.Format_RGBA8888)


# ── Flask Web Server ────────────────────────────────────────────────

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign In — Biobank</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
.login-card{background:white;border-radius:16px;padding:32px 28px;box-shadow:0 4px 20px rgba(0,0,0,0.1);width:100%;max-width:380px}
h1{font-size:1.4rem;color:#1a73e8;text-align:center;margin-bottom:4px}
p.sub{color:#666;text-align:center;font-size:0.9rem;margin-bottom:24px}
input{width:100%;padding:12px 14px;border:2px solid #ddd;border-radius:8px;font-size:1rem;outline:none;margin-bottom:12px;transition:border-color 0.2s}
input:focus{border-color:#1a73e8}
button{width:100%;padding:12px;background:#1a73e8;color:white;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;transition:background 0.2s}
button:hover{background:#1557b0}button:disabled{opacity:0.5;cursor:not-allowed}
.error{color:#e74c3c;font-size:0.85rem;text-align:center;margin-top:8px;display:none}.error.visible{display:block}
.switch-btn{background:none;border:none;color:#1a73e8;font-size:0.85rem;text-decoration:underline;cursor:pointer;display:block;margin:12px auto 0;padding:4px}
.switch-btn:hover{color:#1557b0}.page{display:none}.page.active{display:block}
</style></head><body>
<div class="login-card"><h1>NUBRI Biobank</h1><p class="sub" id="subtitle">Sign in to access specimen data</p>
<div id="login-page" class="page active">
<input type="email" id="email" placeholder="Email" autocomplete="email">
<input type="password" id="password" placeholder="Password" autocomplete="current-password">
<button id="login-btn" onclick="webLogin()">Sign In</button>
<button class="switch-btn" onclick="showSignup()">Create an account</button>
<div class="error" id="login-error">Invalid credentials</div></div>
<div id="signup-page" class="page">
<input type="text" id="signup-name" placeholder="Full name (optional)">
<input type="email" id="signup-email" placeholder="Email">
<input type="password" id="signup-password" placeholder="Password (min 4 chars)">
<input type="password" id="signup-confirm" placeholder="Confirm password">
<button id="signup-btn" onclick="webSignup()">Create Account</button>
<button class="switch-btn" onclick="showLogin()">Already have an account? Sign in</button>
<div class="error" id="signup-error">Error</div></div></div>
<script>
function showSignup(){document.getElementById('login-page').classList.remove('active');document.getElementById('signup-page').classList.add('active');document.getElementById('subtitle').textContent='Create a new account'}
function showLogin(){document.getElementById('signup-page').classList.remove('active');document.getElementById('login-page').classList.add('active');document.getElementById('subtitle').textContent='Sign in to access specimen data'}
document.getElementById('password').addEventListener('keydown',function(e){if(e.key==='Enter')webLogin()})
document.getElementById('signup-confirm').addEventListener('keydown',function(e){if(e.key==='Enter')webSignup()})
function webLogin(){const btn=document.getElementById('login-btn'),email=document.getElementById('email').value.trim(),password=document.getElementById('password').value,errEl=document.getElementById('login-error');if(!email||!password){errEl.textContent='Please fill in all fields.';errEl.classList.add('visible');return}
btn.disabled=true;btn.textContent='Signing in...';errEl.classList.remove('visible')
fetch('/api/web-login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})}).then(r=>r.json()).then(d=>{if(d.token){localStorage.setItem('session_token',d.token);localStorage.setItem('session_user',JSON.stringify(d.user));window.location.href='/'}else{errEl.textContent=d.error||'Login failed';errEl.classList.add('visible');btn.disabled=false;btn.textContent='Sign In'}}).catch(()=>{errEl.textContent='Connection error';errEl.classList.add('visible');btn.disabled=false;btn.textContent='Sign In'})}
function webSignup(){const btn=document.getElementById('signup-btn'),name=document.getElementById('signup-name').value.trim(),email=document.getElementById('signup-email').value.trim(),password=document.getElementById('signup-password').value,confirm=document.getElementById('signup-confirm').value,errEl=document.getElementById('signup-error');if(!email||!password){errEl.textContent='Email and password required.';errEl.classList.add('visible');return}
if(password!==confirm){errEl.textContent='Passwords do not match.';errEl.classList.add('visible');return}
btn.disabled=true;btn.textContent='Creating account...';errEl.classList.remove('visible')
fetch('/api/web-signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password,name})}).then(r=>r.json()).then(d=>{if(d.token){localStorage.setItem('session_token',d.token);localStorage.setItem('session_user',JSON.stringify(d.user));window.location.href='/'}else{errEl.textContent=d.error||'Signup failed';errEl.classList.add('visible');btn.disabled=false;btn.textContent='Create Account'}}).catch(()=>{errEl.textContent='Connection error';errEl.classList.add('visible');btn.disabled=false;btn.textContent='Create Account'})}
</script></body></html>
"""

SPECIMEN_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Biobank Barcode Lookup</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#333;padding:16px;min-height:100vh}
.container{max-width:600px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
h1{font-size:1.5rem;color:#1a73e8}
.signout-btn{background:none;border:1px solid #ddd;padding:6px 14px;border-radius:6px;color:#666;cursor:pointer;font-size:0.85rem}
.signout-btn:hover{background:#f0f0f0}
.scan-area{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-bottom:16px}
#qr-video{width:100%;max-width:400px;display:block;margin:0 auto 12px;border-radius:8px;background:#000}
#scan-btn{display:block;width:100%;padding:14px;background:#1a73e8;color:white;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;margin-bottom:12px}
#scan-btn:disabled{opacity:0.5}#scan-btn.scanning{background:#e74c3c}
input[type="text"]{width:100%;padding:12px 16px;border:2px solid #ddd;border-radius:8px;font-size:1rem;outline:none}
input[type="text"]:focus{border-color:#1a73e8}
.result-card{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none}
.result-card.visible{display:block}
.result-card h2{font-size:1.1rem;color:#1a73e8;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #e8f0fe}
.field{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0}
.field-label{color:#666;font-size:0.9rem}.field-value{font-weight:600;text-align:right;max-width:60%;word-break:break-word}
.not-found{background:#fff3f3;color:#c0392b;padding:20px;border-radius:8px;text-align:center;display:none}.not-found.visible{display:block}
.loading{text-align:center;padding:20px;color:#666;display:none}.loading.visible{display:block}
.spinner{border:3px solid #f3f3f3;border-top:3px solid #1a73e8;border-radius:50%;width:30px;height:30px;animation:spin 1s linear infinite;margin:0 auto 10px}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
</style></head><body>
<div class="container"><div class="header"><h1>Biobank Barcode Lookup</h1><button class="signout-btn" onclick="signOut()">Sign Out</button></div>
<div class="scan-area"><video id="qr-video" autoplay muted playsinline></video><button id="scan-btn" onclick="toggleScanner()">Open Camera Scanner</button><input type="text" id="qr-input" placeholder="Scan barcode or enter ID..." onkeydown="if(event.key==='Enter')lookup()"></div>
<div class="loading" id="loading"><div class="spinner"></div>Looking up...</div>
<div class="not-found" id="not-found">Specimen not found.</div>
<div class="result-card" id="result"><h2 id="specimen-header">Specimen Details</h2><div id="fields-container"></div></div></div>
<script>
function getToken(){return localStorage.getItem('session_token')}
function authFetch(url,opts){opts=opts||{};opts.headers=opts.headers||{};opts.headers['Authorization']='Bearer '+getToken();return fetch(url,opts).then(r=>{if(r.status===401){localStorage.removeItem('session_token');localStorage.removeItem('session_user');window.location.href='/login';throw new Error('Unauthorized')};return r})}
function signOut(){const t=getToken();if(t) fetch('/api/logout',{method:'POST',headers:{'Authorization':'Bearer '+t}});localStorage.removeItem('session_token');localStorage.removeItem('session_user');window.location.href='/login'}
if(!getToken()) window.location.href='/login'
let sa=false,vs=null
async function toggleScanner(){const btn=document.getElementById('scan-btn'),v=document.getElementById('qr-video');if(sa){stopScanner();return}
try{vs=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});v.srcObject=vs;await v.play();sa=true;btn.textContent='Stop Scanner';btn.classList.add('scanning');scanQR()}catch(e){alert('Camera access denied')}}
function stopScanner(){const btn=document.getElementById('scan-btn'),v=document.getElementById('qr-video');if(vs){vs.getTracks().forEach(t=>t.stop());vs=null};v.srcObject=null;sa=false;btn.textContent='Open Camera Scanner';btn.classList.remove('scanning')}
function scanQR(){if(!sa)return;const v=document.getElementById('qr-video');if(v.readyState===v.HAVE_ENOUGH_DATA){const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);authFetch('/api/decode-qr',{method:'POST',body:JSON.stringify({image:c.toDataURL('image/png')}),headers:{'Content-Type':'application/json'}}).then(r=>r.json()).then(d=>{if(d.qr_code){stopScanner();document.getElementById('qr-input').value=d.qr_code;lookup()}}).catch(()=>{})}
requestAnimationFrame(scanQR)}
function showLoad(){document.getElementById('loading').classList.add('visible');document.getElementById('result').classList.remove('visible');document.getElementById('not-found').classList.remove('visible')}
function lookup(){const q=document.getElementById('qr-input').value.trim();if(!q)return;showLoad();authFetch('/api/lookup?qr='+encodeURIComponent(q)).then(r=>r.json()).then(d=>{document.getElementById('loading').classList.remove('visible');if(d.error){document.getElementById('not-found').classList.add('visible');document.getElementById('result').classList.remove('visible');return}
document.getElementById('not-found').classList.remove('visible');document.getElementById('specimen-header').textContent='Specimen: '+q;const c=document.getElementById('fields-container');c.innerHTML='';d.fields.forEach(f=>{const div=document.createElement('div');div.className='field';div.innerHTML='<span class="field-label">'+f.name+'</span><span class="field-value">'+(f.value||'-')+'</span>';c.appendChild(div)});const m=document.createElement('div');m.style.marginTop='12px';m.style.paddingTop='8px';m.style.borderTop='2px solid #e8f0fe';m.style.fontSize='0.8rem';m.style.color='#999';m.innerHTML='Created: '+d.created_at;c.appendChild(m);document.getElementById('result').classList.add('visible')}).catch(()=>{})}
</script></body></html>
"""


class WebServer:
    def __init__(self, db=None, port=8765, auth=None):
        self.db = db
        self.port = port
        self.auth = auth
        self.auth_manager = AuthManager(db)
        from flask import Flask, request, jsonify, render_template_string
        self.app = Flask(__name__)
        self._setup_routes()
        self.server_thread = None

    def _require_auth(self):
        from flask import request
        h = request.headers.get("Authorization", "")
        if not h.startswith("Bearer "):
            return None
        return self.auth_manager.validate_session(h[7:])

    def _setup_routes(self):
        from flask import request, jsonify, render_template_string
        app = self.app
        sm = SpecimenModel(self.db)
        cd = ColumnDefinition(self.db)

        @app.route("/")
        def index():
            return render_template_string(SPECIMEN_TEMPLATE)

        @app.route("/login")
        def login_page():
            return render_template_string(LOGIN_TEMPLATE)

        @app.route("/api/web-login", methods=["POST"])
        def web_login():
            data = request.get_json() or {}
            try:
                user = self.auth_manager.login(data.get("email","").strip(), data.get("password",""))
                if not user:
                    return jsonify({"error":"Invalid credentials"}),401
                token = self.auth_manager.create_session(user["id"])
                return jsonify({"token":token,"user":{"id":user["id"],"email":user["email"]}})
            except PermissionError as e:
                return jsonify({"error":str(e)}),401
            except Exception as e:
                return jsonify({"error":str(e)}),500

        @app.route("/api/web-signup", methods=["POST"])
        def web_signup():
            data = request.get_json() or {}
            try:
                user = self.auth_manager.signup(data.get("email","").strip(), data.get("password",""), data.get("name",""))
                if not user:
                    return jsonify({"error":"Signup failed"}),500
                token = self.auth_manager.create_session(user["id"])
                return jsonify({"token":token,"user":{"id":user["id"],"email":user["email"]}})
            except (ValueError, PermissionError) as e:
                return jsonify({"error":str(e)}),400
            except Exception as e:
                return jsonify({"error":str(e)}),500

        @app.route("/api/logout", methods=["POST"])
        def web_logout():
            h = request.headers.get("Authorization","")
            if h.startswith("Bearer "):
                self.auth_manager.delete_session(h[7:])
            return jsonify({"ok":True})

        @app.route("/api/lookup")
        def api_lookup():
            user = self._require_auth()
            if not user:
                return jsonify({"error":"Unauthorized"}),401
            qr = request.args.get("qr","")
            if not qr:
                return jsonify({"error":"No QR code"}),400
            spec = sm.get_by_qr(qr)
            if not spec:
                res = sm.search(qr, column_name="Sample ID")
                spec = res[0] if res else None
            if not spec:
                return jsonify({"error":"Not found"}),404
            cols = cd.get_all()
            fields = [{"name":c["column_name"],"value":spec["custom_fields"].get(c["column_name"],"")} for c in cols]
            return jsonify({"id":spec["id"],"qr_code":spec["qr_code"],"fields":fields,"created_at":spec["created_at"],"updated_at":spec["updated_at"]})

        @app.route("/api/decode-qr", methods=["POST"])
        def api_decode_qr():
            user = self._require_auth()
            if not user:
                return jsonify({"error":"Unauthorized"}),401
            try:
                from PIL import Image
                from pyzbar.pyzbar import decode as pyzbar_decode
                data = request.get_json()
                if not data or "image" not in data:
                    return jsonify({"error":"No image"}),400
                img = Image.open(io.BytesIO(base64.b64decode(data["image"].split(",")[1])))
                res = pyzbar_decode(img)
                return jsonify({"qr_code":res[0].data.decode("utf-8") if res else None})
            except Exception as e:
                return jsonify({"error":str(e)}),500

        @app.route("/api/me")
        def api_me():
            user = self._require_auth()
            if not user:
                return jsonify({"error":"Unauthorized"}),401
            return jsonify(user)

    def start(self):
        def run():
            try:
                from waitress import serve
                serve(self.app, host="0.0.0.0", port=self.port)
            except ImportError:
                self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()

    def stop(self):
        try:
            import requests
            requests.get(f"http://127.0.0.1:{self.port}/shutdown", timeout=2)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════

def _style_btn(color="#2b7ed4"):
    return color

def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class SimpleTable(ctk.CTkFrame):
    def __init__(self, master, columns, select_cb=None, **kw):
        super().__init__(master, **kw)
        self.columns = columns
        self.select_cb = select_cb
        self.rows = []
        self._selected = -1
        self._header = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self._header.pack(fill="x")
        for i, col in enumerate(columns):
            lbl = ctk.CTkLabel(self._header, text=col, font=("", 12, "bold"), anchor="w")
            lbl.grid(row=0, column=i, padx=(8 if i==0 else 2), pady=4, sticky="ew")
            self._header.grid_columnconfigure(i, weight=1, minsize=80)
        self._body = ctk.CTkScrollableFrame(self)
        self._body.pack(fill="both", expand=True)
        self._data = []

    def set_data(self, data):
        for w in self._body.winfo_children():
            w.destroy()
        self.rows = []
        self._data = data
        for idx, item in enumerate(data):
            fg = "#1e1e1e" if idx % 2 == 0 else "#252525"
            rf = ctk.CTkFrame(self._body, fg_color=fg, corner_radius=2)
            rf.pack(fill="x", pady=0)
            rf._item_idx = idx
            rf.bind("<Button-1>", lambda e, i=idx: self._select(i))
            for ci, col in enumerate(self.columns):
                val = str(item.get(col, ""))
                lbl = ctk.CTkLabel(rf, text=val, anchor="w", font=("", 11))
                lbl.grid(row=0, column=ci, padx=(8 if ci==0 else 2), pady=4, sticky="ew")
                lbl.bind("<Button-1>", lambda e, i=idx: self._select(i))
                rf.grid_columnconfigure(ci, weight=1, minsize=80)
            self.rows.append(rf)
        self._highlight()

    def _select(self, idx):
        self._selected = idx
        self._highlight()
        if self.select_cb:
            self.select_cb(idx)

    def selected_row(self):
        if 0 <= self._selected < len(self._data):
            return self._data[self._selected]
        return None

    def selected_index(self):
        return self._selected

    def _highlight(self):
        for i, rf in enumerate(self.rows):
            if i == self._selected:
                rf.configure(fg_color="#1a3a5c")
            else:
                rf.configure(fg_color="#1e1e1e" if i % 2 == 0 else "#252525")


# ── Login Dialog ────────────────────────────────────────────────────

class LoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.db = db
        self.auth = None
        self.title("NUBRI Biobank — Sign In")
        self.geometry("500x540")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(self, text="NUBRI Biobank System", font=("", 20, "bold"), text_color="#4da6ff")
        title.grid(row=0, column=0, pady=(20, 5))

        self.stack = ctk.CTkFrame(self, fg_color="transparent")
        self.stack.grid(row=1, column=0, sticky="nsew", padx=20)
        self.grid_rowconfigure(1, weight=1)

        pages = [self._db_setup_page(), self._login_page(), self._signup_page()]
        self._page_frames = []
        for i, p in enumerate(pages):
            p.grid(row=0, column=0, sticky="nsew")
            self._page_frames.append(p)

        self._status = ctk.CTkLabel(self, text="", text_color="#ef5350")
        self._status.grid(row=2, column=0, pady=(0, 15))

        cfg = load_db_config()
        self._show_page(0 if cfg.get("postgresql_url","").strip() else 1)

    def _show_page(self, idx):
        for i, p in enumerate(self._page_frames):
            p.grid_remove()
        self._page_frames[idx].grid()

    def _db_setup_page(self):
        f = ctk.CTkFrame(self.stack, fg_color="transparent")
        ctk.CTkLabel(f, text="Connect to a shared database", text_color="#9e9e9e", font=("", 12)).pack(pady=(10, 2))
        ctk.CTkLabel(f, text="Enter PostgreSQL URL to share data.\nSkip to use local SQLite.", text_color="#757575", font=("", 11)).pack()
        self._db_url = ctk.CTkEntry(f, placeholder_text="postgresql://user:password@host:5432/dbname")
        self._db_url.pack(fill="x", pady=(15, 8))
        ctk.CTkButton(f, text="Connect & Continue", fg_color="#4caf50", hover_color="#43a047", command=self._connect_db).pack(fill="x", pady=5)
        ctk.CTkButton(f, text="Use Local SQLite", fg_color="transparent", hover_color="#333", text_color="#9e9e9e", command=lambda: self._show_page(1)).pack(pady=5)
        return f

    def _login_page(self):
        f = ctk.CTkFrame(self.stack, fg_color="transparent")
        ctk.CTkLabel(f, text="Sign in to continue", text_color="#9e9e9e").pack(pady=(10, 12))
        self._l_email = ctk.CTkEntry(f, placeholder_text="Email")
        self._l_email.pack(fill="x", pady=4)
        self._l_pass = ctk.CTkEntry(f, placeholder_text="Password", show="*")
        self._l_pass.pack(fill="x", pady=4)
        self._l_pass.bind("<Return>", lambda e: self._login())
        self._l_btn = ctk.CTkButton(f, text="Sign In", command=self._login)
        self._l_btn.pack(fill="x", pady=8)
        ctk.CTkButton(f, text="Create an account", fg_color="transparent", hover_color="#333", text_color="#4da6ff", command=lambda: self._show_page(2)).pack()
        return f

    def _signup_page(self):
        f = ctk.CTkFrame(self.stack, fg_color="transparent")
        ctk.CTkLabel(f, text="Create a new account", text_color="#9e9e9e").pack(pady=(10, 12))
        self._s_name = ctk.CTkEntry(f, placeholder_text="Full name (optional)")
        self._s_name.pack(fill="x", pady=3)
        self._s_email = ctk.CTkEntry(f, placeholder_text="Email")
        self._s_email.pack(fill="x", pady=3)
        self._s_pass = ctk.CTkEntry(f, placeholder_text="Password (min 4 chars)", show="*")
        self._s_pass.pack(fill="x", pady=3)
        self._s_confirm = ctk.CTkEntry(f, placeholder_text="Confirm password", show="*")
        self._s_confirm.pack(fill="x", pady=3)
        self._s_confirm.bind("<Return>", lambda e: self._signup())
        self._s_btn = ctk.CTkButton(f, text="Create Account", fg_color="#4caf50", hover_color="#43a047", command=self._signup)
        self._s_btn.pack(fill="x", pady=8)
        ctk.CTkButton(f, text="Already have an account? Sign in", fg_color="transparent", hover_color="#333", text_color="#4da6ff", command=lambda: self._show_page(1)).pack()
        return f

    def _set_status(self, msg):
        self._status.configure(text=msg)

    def _set_loading(self, loading):
        state = "disabled" if loading else "normal"
        for btn in (self._l_btn, self._s_btn):
            btn.configure(state=state)
        # We show a simple status instead of button text change

    def _connect_db(self):
        url = self._db_url.get().strip()
        if not url:
            self._set_status("Enter a URL or skip")
            return
        if not url.startswith("postgresql://"):
            self._set_status("URL must start with postgresql://")
            return
        save_db_config({"postgresql_url": url})
        messagebox.showinfo("Restart Required", "Save the URL and restart the app to switch databases.")
        self.destroy()

    def _login(self):
        email = self._l_email.get().strip()
        password = self._l_pass.get()
        if not email or not password:
            self._set_status("Fill in all fields.")
            return
        self._set_loading(True)
        try:
            self.auth = AuthManager(self.db)
            self.auth.login(email, password)
            self.destroy()
        except PermissionError as e:
            self._set_status(str(e))
            self._set_loading(False)

    def _signup(self):
        name = self._s_name.get().strip()
        email = self._s_email.get().strip()
        password = self._s_pass.get()
        confirm = self._s_confirm.get()
        if not email or not password:
            self._set_status("Email and password required.")
            return
        if password != confirm:
            self._set_status("Passwords do not match.")
            return
        if len(password) < 4:
            self._set_status("Password must be at least 4 chars.")
            return
        self._set_loading(True)
        try:
            self.auth = AuthManager(self.db)
            self.auth.signup(email, password, name)
            self.destroy()
        except ValueError as e:
            self._set_status(str(e))
            self._set_loading(False)


# ── Label Form Widget ───────────────────────────────────────────────

class LabelFormWidget(ctk.CTkFrame):
    def __init__(self, master, db, on_label_created=None, **kw):
        super().__init__(master, **kw)
        self.db = db
        self.specimen_model = SpecimenModel(db)
        self.column_def = ColumnDefinition(db)
        self.settings_model = SettingsModel(db)
        self.on_label_created = on_label_created
        self.field_widgets = {}
        self._last_qr = None
        self._last_fields = None
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Create New Specimen Label", font=("", 18, "bold"), text_color="#4da6ff").grid(row=0, column=0, columnspan=2, pady=(10, 5))

        # ── Left: form ──
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(left)
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=5)
        self._form_inner = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._form_inner.pack(fill="x", expand=True)

        btnf = ctk.CTkFrame(left, fg_color="transparent")
        btnf.grid(row=1, column=0, pady=10)
        self._save_btn = ctk.CTkButton(btnf, text="Generate Label & Save", command=self._save)
        self._save_btn.pack(side="left", padx=4)
        ctk.CTkButton(btnf, text="Clear", fg_color="#555", hover_color="#666", command=self._clear).pack(side="left", padx=4)

        # ── Right: preview panel ──
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(0, 5))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=0)
        right.grid_rowconfigure(2, weight=2)
        right.grid_columnconfigure(0, weight=1)

        # Preview image
        pf = ctk.CTkFrame(right)
        pf.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        pf.grid_columnconfigure(0, weight=1)
        pf.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(pf, text="Label Preview", font=("", 13, "bold"), text_color="#9e9e9e").grid(row=0, column=0, pady=(4, 0))
        self._preview_label = ctk.CTkLabel(pf, text="", anchor="center")
        self._preview_label.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Print button
        self._print_preview_btn = ctk.CTkButton(right, text="Print Label", fg_color="#4caf50", hover_color="#43a047", command=self._save_and_print)
        self._print_preview_btn.grid(row=1, column=0, pady=4)

        # Text data preview
        tf = ctk.CTkFrame(right)
        tf.grid(row=2, column=0, sticky="nsew")
        tf.grid_columnconfigure(0, weight=1)
        tf.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(tf, text="Data Preview", font=("", 13, "bold"), text_color="#9e9e9e").grid(row=0, column=0, pady=(4, 0))
        self._text_preview = ctk.CTkTextbox(tf, state="disabled")
        self._text_preview.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self._rebuild_fields()

    def _rebuild_fields(self):
        for w in self._form_inner.winfo_children():
            w.destroy()
        self.field_widgets = {}
        cols = self.column_def.get_all()
        if not cols:
            ctk.CTkLabel(self._form_inner, text="No columns defined. Go to Manage Columns to add some.").pack()
            self._update_preview()
            return
        for col in cols:
            name = col["column_name"]
            req = col["is_required"]
            label = f"{name} {'*' if req else ''}"
            ctk.CTkLabel(self._form_inner, text=label).pack(anchor="w", pady=(6, 0))
            if name == "Sample ID":
                w = ctk.CTkEntry(self._form_inner, state="readonly", width=300)
                w.configure(textvariable=ctk.StringVar(value=self.settings_model.get_next_sample_id()))
                w.configure(fg_color="#2a2a2a", text_color="#4da6ff")
            elif col.get("column_type") == "DATE":
                w = ctk.CTkEntry(self._form_inner, placeholder_text="YYYY-MM-DD", width=300)
                w.insert(0, datetime.now().strftime("%Y-%m-%d"))
            else:
                w = ctk.CTkEntry(self._form_inner, placeholder_text=f"Enter {name}", width=300)
            w.pack(anchor="w", pady=2)
            w.bind("<KeyRelease>", lambda e, n=name: self._update_preview())
            self.field_widgets[name] = w
        self._update_preview()

    def _get_field_data(self):
        data = {}
        cols = self.column_def.get_all()
        for col in cols:
            name = col["column_name"]
            w = self.field_widgets.get(name)
            if w:
                data[name] = w.get().strip() if name != "Sample ID" else w.get()
        return data

    def _update_preview(self):
        data = self._get_field_data()
        # Generate label image preview
        try:
            sample_id = data.get("Sample ID", "N/A")
            renderer = LabelRenderer()
            img = renderer.render(sample_id, data)
            disp_w = min(280, img.width)
            disp_h = int(disp_w * img.height / img.width)
            photo = ImageTk.PhotoImage(img.resize((disp_w, disp_h), Image.LANCZOS))
            self._preview_label.configure(image=photo)
            self._preview_label.image = photo
        except Exception:
            self._preview_label.configure(image="")
            self._preview_label.image = None
        # Update text preview
        self._text_preview.configure(state="normal")
        self._text_preview.delete("0.0", "end")
        for k, v in data.items():
            self._text_preview.insert("end", f"{k}: {v}\n")
        self._text_preview.configure(state="disabled")

    def _save(self):
        data = {}
        missing = []
        cols = self.column_def.get_all()
        for col in cols:
            name = col["column_name"]
            w = self.field_widgets.get(name)
            if w:
                if name == "Sample ID":
                    value = w.get()
                else:
                    value = w.get().strip()
                if col["is_required"] and not value:
                    missing.append(name)
                data[name] = value
        if missing:
            messagebox.showwarning("Required Fields", f"Please fill in: {', '.join(missing)}")
            return
        try:
            qr = self.specimen_model.create(data)
            self.settings_model.increment_next_sample_id()
            self._last_qr = qr
            self._last_fields = dict(data)
            messagebox.showinfo("Label Created", f"Specimen saved!\nSample ID: {qr}")
            if self.on_label_created:
                self.on_label_created(qr)
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _save_and_print(self):
        data = {}
        missing = []
        cols = self.column_def.get_all()
        for col in cols:
            name = col["column_name"]
            w = self.field_widgets.get(name)
            if w:
                if name == "Sample ID":
                    value = w.get()
                else:
                    value = w.get().strip()
                if col["is_required"] and not value:
                    missing.append(name)
                data[name] = value
        if missing:
            messagebox.showwarning("Required Fields", f"Please fill in: {', '.join(missing)}")
            return
        try:
            qr = self.specimen_model.create(data)
            self.settings_model.increment_next_sample_id()
            self._last_qr = qr
            self._last_fields = dict(data)
            if self.on_label_created:
                self.on_label_created(qr)
            s = self.settings_model.get_all()
            mode = s.get("printer_mode", "system")
            is_thermal = mode == "thermal"
            tpl = load_template(self.settings_model) if self.settings_model else None
            print_label(
                qr_code=qr, fields_dict=data,
                printer_mode="thermal" if is_thermal else "system",
                backend=s.get("printer_backend", "network") if is_thermal else "network",
                host=s.get("printer_host", "192.168.1.100") if is_thermal else "192.168.1.100",
                port=int(s.get("printer_port", "9100")) if is_thermal else 9100,
                thermal_copies=1,
                label_width_mm=int(s.get("label_width_mm", "35")),
                label_height_mm=int(s.get("label_height_mm", "15")),
                label_gap_mm=int(s.get("label_gap_mm", "3")),
                template=tpl,
            )
            messagebox.showinfo("Printed", "Label saved and sent to printer.")
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save & print: {e}")

    def _clear(self):
        for name, w in self.field_widgets.items():
            if name == "Sample ID":
                w.configure(state="normal")
                w.delete(0, "end")
                w.insert(0, self.settings_model.get_next_sample_id())
                w.configure(state="readonly")
            else:
                w.delete(0, "end")
        self._update_preview()

    def refresh(self):
        self._rebuild_fields()


# ── Search Widget ───────────────────────────────────────────────────

class SearchWidget(ctk.CTkFrame):
    def __init__(self, master, db, **kw):
        super().__init__(master, **kw)
        self.db = db
        self.specimen_model = SpecimenModel(db)
        self.column_def = ColumnDefinition(db)
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Search & Scan Specimens", font=("", 18, "bold"), text_color="#4da6ff").grid(row=0, column=0, pady=(10, 5))

        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=1, column=0, sticky="ew", padx=5)
        sf.grid_columnconfigure(0, weight=1)
        self._search_input = ctk.CTkEntry(sf, placeholder_text="Scan barcode or type to search...", width=400)
        self._search_input.grid(row=0, column=0, sticky="w", padx=(0, 4))
        self._search_input.bind("<Return>", lambda e: self._search())
        ctk.CTkButton(sf, text="Search", width=80, command=self._search).grid(row=0, column=1, padx=2)
        ctk.CTkButton(sf, text="Scan QR", width=100, fg_color="#4caf50", hover_color="#43a047", command=self._scan_qr).grid(row=0, column=2, padx=(2, 0))

        self._table = SimpleTable(self, ["QR Code", "Details", "Created"], select_cb=self._on_select)
        self._table.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        df = ctk.CTkFrame(self)
        df.grid(row=3, column=0, sticky="nsew", padx=5, pady=(0, 5))
        df.grid_columnconfigure(0, weight=1)
        df.grid_rowconfigure(1, weight=1)
        self._detail_label = ctk.CTkLabel(df, text="Search results appear here.", text_color="#9e9e9e")
        self._detail_label.grid(row=0, column=0, sticky="w")
        self._detail_text = ctk.CTkTextbox(df)
        self._detail_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    def _search(self):
        q = self._search_input.get().strip()
        results = self.specimen_model.get_all(limit=200) if not q else self.specimen_model.search(q)
        cols = self.column_def.get_all()
        data = []
        for s in results:
            cf = s["custom_fields"]
            summary = "; ".join(f"{c['column_name']}: {cf.get(c['column_name'], '-')}" for c in cols[:3])
            data.append({"QR Code": s["qr_code"], "Details": summary, "Created": s["created_at"], "_id": s["id"]})
        self._table.set_data(data)

    def _scan_qr(self):
        try:
            qr = QRHandler.decode_from_camera(timeout=60)
            if qr:
                self._search_input.delete(0, "end")
                self._search_input.insert(0, qr)
                self._search()
        except ImportError:
            messagebox.showwarning("Camera Not Available", "Camera scanning requires OpenCV and pyzbar.\npip install opencv-python pyzbar")

    def _on_select(self, idx):
        row = self._table.selected_row()
        if not row:
            return
        spec = self.specimen_model.get_by_qr(row["QR Code"])
        if not spec:
            return
        cols = self.column_def.get_all()
        cf = spec["custom_fields"]
        html = f"Specimen: {spec['qr_code']}\n"
        for c in cols:
            html += f"{c['column_name']}: {cf.get(c['column_name'], '')}\n"
        html += f"\nCreated: {spec['created_at']}\nUpdated: {spec.get('updated_at', '')}"
        self._detail_label.configure(text=f"Details for: {spec['qr_code']}")
        self._detail_text.delete("0.0", "end")
        self._detail_text.insert("0.0", html)


# ── Database View Widget ────────────────────────────────────────────

class DatabaseViewWidget(ctk.CTkFrame):
    def __init__(self, master, db, **kw):
        super().__init__(master, **kw)
        self.db = db
        self.specimen_model = SpecimenModel(db)
        self.column_def = ColumnDefinition(db)
        self._page = 0
        self._page_size = 50
        self._stored = []
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        r0 = ctk.CTkFrame(self, fg_color="transparent")
        r0.grid(row=0, column=0, sticky="ew", padx=5, pady=(10, 0))
        r0.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(r0, text="Database Browser", font=("", 18, "bold"), text_color="#4da6ff").grid(row=0, column=0, sticky="w")
        self._count_label = ctk.CTkLabel(r0, text="0 records", text_color="#9e9e9e")
        self._count_label.grid(row=0, column=1, sticky="e")

        self._cols = []
        self._table = SimpleTable(self, ["QR Code", "Created", "Updated"], select_cb=self._on_select)
        self._table.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(nav, text="Prev", fg_color="#555", hover_color="#666", command=self._prev).pack(side="left", padx=2)
        self._page_label = ctk.CTkLabel(nav, text="Page 1")
        self._page_label.pack(side="left", padx=10)
        ctk.CTkButton(nav, text="Next", fg_color="#555", hover_color="#666", command=self._next).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="Print", fg_color="#4caf50", hover_color="#43a047", command=self._print_sel).pack(side="left", padx=10)
        ctk.CTkButton(nav, text="Refresh", command=self._load).pack(side="left", padx=2)
        sep = ctk.CTkLabel(nav, text="|", text_color="#555")
        sep.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="Export CSV", fg_color="#ff9800", hover_color="#f57c00", command=self._export).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="Import CSV", fg_color="#9c27b0", hover_color="#7b1fa2", command=self._import_csv).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="Template", fg_color="#607d8b", hover_color="#455a64", command=self._template).pack(side="left", padx=2)

        self._load()

    def _load(self):
        cols = self.column_def.get_all()
        self._cols = cols
        specimens = self.specimen_model.get_all(limit=self._page_size, offset=self._page * self._page_size)
        total = self.specimen_model.count()
        headers = ["QR Code"] + [c["column_name"] for c in cols] + ["Created", "Updated"]
        data = []
        self._stored = specimens
        for s in specimens:
            cf = s["custom_fields"]
            row = {"QR Code": s["qr_code"]}
            for c in cols:
                row[c["column_name"]] = cf.get(c["column_name"], "")
            row["Created"] = s["created_at"]
            row["Updated"] = s.get("updated_at", "")
            data.append(row)
        self._table.destroy()
        self._table = SimpleTable(self, headers, select_cb=self._on_select)
        self._table.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self._table.set_data(data)
        self._count_label.configure(text=f"{total} records")
        self._page_label.configure(text=f"Page {self._page + 1}")

    def _prev(self):
        if self._page > 0:
            self._page -= 1
            self._load()

    def _next(self):
        self._page += 1
        self._load()

    def _on_select(self, idx):
        pass  # could highlight print button

    def _print_sel(self):
        row = self._table.selected_row()
        if not row:
            return
        sidx = self._table.selected_index()
        if sidx < 0 or sidx >= len(self._stored):
            return
        spec = self._stored[sidx]
        PrintDialog(self, spec["qr_code"], spec["custom_fields"], self.db)

    def _export(self):
        cols = self.column_def.get_all()
        if not cols:
            messagebox.showinfo("Info", "No columns defined.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            self.specimen_model.export_to_csv(path, cols)
            messagebox.showinfo("Exported", f"Exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")

    def _import_csv(self):
        cols = self.column_def.get_all()
        if not cols:
            messagebox.showinfo("Info", "No columns defined.")
            return
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            imported, errors = self.specimen_model.import_from_csv(path, cols)
            msg = f"Imported {imported} records."
            if errors:
                msg += f"\n\nErrors:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += f"\n... and {len(errors)-5} more"
            messagebox.showinfo("Import Complete", msg)
            self._load()
        except Exception as e:
            messagebox.showerror("Error", f"Import failed:\n{e}")

    def _template(self):
        cols = self.column_def.get_all()
        if not cols:
            messagebox.showinfo("Info", "No columns defined.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                f.write(SpecimenModel.get_template_csv(cols))
            messagebox.showinfo("Template Saved", f"Template saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template:\n{e}")


# ── Schema Manager Widget ───────────────────────────────────────────

class AddColumnDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Column")
        self.geometry("400x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Column Name:").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 2))
        self._name = ctk.CTkEntry(self, placeholder_text="e.g. Freezer Row")
        self._name.grid(row=1, column=0, sticky="ew", padx=20, pady=4)

        ctk.CTkLabel(self, text="Type:").grid(row=2, column=0, sticky="w", padx=20, pady=(10, 2))
        self._type = ctk.CTkOptionMenu(self, values=["TEXT", "NUMBER", "DATE"])
        self._type.grid(row=3, column=0, sticky="ew", padx=20, pady=4)

        self._req = ctk.CTkCheckBox(self, text="Required field")
        self._req.grid(row=4, column=0, sticky="w", padx=20, pady=8)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=5, column=0, pady=10)
        ctk.CTkButton(bf, text="OK", width=80, command=self._ok).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="Cancel", width=80, fg_color="#555", hover_color="#666", command=self.destroy).pack(side="left", padx=4)

    def _ok(self):
        self.result = {"name": self._name.get().strip(), "type": self._type.get(), "required": self._req.get()}
        self.destroy()


class SchemaManagerWidget(ctk.CTkFrame):
    def __init__(self, master, db, on_schema_changed=None, **kw):
        super().__init__(master, **kw)
        self.db = db
        self.column_def = ColumnDefinition(db)
        self.on_schema_changed = on_schema_changed
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Manage Custom Columns", font=("", 18, "bold"), text_color="#4da6ff").grid(row=0, column=0, pady=(10, 2))
        ctk.CTkLabel(self, text="Add, edit, or remove columns.", text_color="#9e9e9e").grid(row=1, column=0, sticky="w", padx=5)

        self._table = SimpleTable(self, ["Column Name", "Type", "Required", "Order"])
        self._table.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(bf, text="+ Add Column", command=self._add).pack(side="left", padx=2)
        ctk.CTkButton(bf, text="Edit", fg_color="#555", hover_color="#666", command=self._edit).pack(side="left", padx=2)
        ctk.CTkButton(bf, text="Delete", fg_color="#ef5350", hover_color="#e53935", command=self._delete).pack(side="left", padx=2)
        ctk.CTkButton(bf, text="Move Up", fg_color="#555", hover_color="#666", command=self._move_up).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="Move Down", fg_color="#555", hover_color="#666", command=self._move_down).pack(side="left", padx=2)
        self._load()

    def _load(self):
        cols = self.column_def.get_all()
        data = []
        self._col_ids = []
        for c in cols:
            data.append({"Column Name": c["column_name"], "Type": c["column_type"], "Required": "Yes" if c["is_required"] else "No", "Order": str(c["display_order"])})
            self._col_ids.append(c["id"])
        self._table.set_data(data)

    def _add(self):
        dlg = AddColumnDialog(self)
        self.wait_window(dlg)
        if dlg.result and dlg.result["name"]:
            try:
                self.column_def.add(dlg.result["name"], dlg.result["type"], dlg.result["required"])
                self._load()
                if self.on_schema_changed:
                    self.on_schema_changed()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _edit(self):
        idx = self._table.selected_index()
        if idx < 0:
            return
        cols = self.column_def.get_all()
        if idx >= len(cols):
            return
        c = cols[idx]
        dlg = AddColumnDialog(self)
        dlg.title("Edit Column")
        dlg._name.insert(0, c["column_name"])
        dlg._type.set(c["column_type"])
        if c["is_required"]:
            dlg._req.select()
        self.wait_window(dlg)
        if dlg.result and dlg.result["name"]:
            try:
                self.column_def.update(c["id"], dlg.result["name"], dlg.result["type"], dlg.result["required"])
                self._load()
                if self.on_schema_changed:
                    self.on_schema_changed()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _delete(self):
        idx = self._table.selected_index()
        if idx < 0 or idx >= len(self._col_ids):
            return
        cols = self.column_def.get_all()
        if idx >= len(cols):
            return
        name = cols[idx]["column_name"]
        if messagebox.askyesno("Confirm Delete", f"Delete column '{name}'?"):
            try:
                self.column_def.delete(cols[idx]["id"])
                self._load()
                if self.on_schema_changed:
                    self.on_schema_changed()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _move_up(self):
        idx = self._table.selected_index()
        if idx <= 0:
            return
        ids = list(self._col_ids)
        ids[idx], ids[idx - 1] = ids[idx - 1], ids[idx]
        self.column_def.reorder(ids)
        self._load()
        if self.on_schema_changed:
            self.on_schema_changed()

    def _move_down(self):
        idx = self._table.selected_index()
        if idx < 0 or idx >= len(self._col_ids) - 1:
            return
        ids = list(self._col_ids)
        ids[idx], ids[idx + 1] = ids[idx + 1], ids[idx]
        self.column_def.reorder(ids)
        self._load()
        if self.on_schema_changed:
            self.on_schema_changed()


# ── Label Designer Dialog ───────────────────────────────────────────

def load_template(settings_model):
    raw = settings_model.get("label_template")
    if raw:
        try:
            merged = dict(DEFAULT_TEMPLATE)
            merged.update(json.loads(raw))
            return merged
        except (json.JSONDecodeError, TypeError):
            pass
    return dict(DEFAULT_TEMPLATE)

def save_template(settings_model, template):
    settings_model.set("label_template", json.dumps(template))


class LabelDesignerDialog(ctk.CTkToplevel):
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.db = db
        self.settings = SettingsModel(db) if db else None
        self._loading = True
        self._setup_ui()
        self.geometry("900x800")
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        self.title("Label Designer")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Customise Label Layout", font=("", 18, "bold"), text_color="#4da6ff").grid(row=0, column=0, pady=5)

        main = ctk.CTkFrame(self)
        main.grid(row=2, column=0, sticky="nsew", padx=5)
        main.grid_columnconfigure(0, weight=1, minsize=300)
        main.grid_columnconfigure(1, weight=2, minsize=400)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # -- size
        sf = ctk.CTkFrame(left)
        sf.pack(fill="x", pady=4)
        ctk.CTkLabel(sf, text="Label Size (mm)", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        sw = ctk.CTkFrame(sf, fg_color="transparent")
        sw.pack(fill="x", padx=5, pady=4)
        self._w_spin = ctk.CTkEntry(sw, width=60, placeholder_text="40")
        self._w_spin.pack(side="left")
        ctk.CTkLabel(sw, text="×").pack(side="left", padx=4)
        self._h_spin = ctk.CTkEntry(sw, width=60, placeholder_text="13")
        self._h_spin.pack(side="left")

        # -- barcode
        bg = ctk.CTkFrame(left)
        bg.pack(fill="x", pady=4)
        ctk.CTkLabel(bg, text="Barcode", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self._show_qr = ctk.CTkCheckBox(bg, text="Show barcode", command=self._upd)
        self._show_qr.pack(anchor="w", padx=5)
        self._show_id = ctk.CTkCheckBox(bg, text="Show sample number", command=self._upd)
        self._show_id.pack(anchor="w", padx=5)
        self._bc_h = ctk.CTkSlider(bg, from_=20, to=90, command=lambda v: self._upd())
        self._bc_h.pack(fill="x", padx=5, pady=2)
        self._bc_w = ctk.CTkSlider(bg, from_=30, to=100, command=lambda v: self._upd())
        self._bc_w.pack(fill="x", padx=5, pady=2)
        self._show_qr_code = ctk.CTkCheckBox(bg, text="Show QR code", command=self._upd)
        self._show_qr_code.pack(anchor="w", padx=5)
        self._qr_size = ctk.CTkSlider(bg, from_=20, to=80, command=lambda v: self._upd())
        self._qr_size.pack(fill="x", padx=5, pady=2)

        # -- colors
        cg = ctk.CTkFrame(left)
        cg.pack(fill="x", pady=4)
        ctk.CTkLabel(cg, text="Colors", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self._bg_color = self._color_row(cg, "Background")
        self._text_color = self._color_row(cg, "Value text")
        self._label_color = self._color_row(cg, "Field labels")

        # -- text
        tg = ctk.CTkFrame(left)
        tg.pack(fill="x", pady=4)
        ctk.CTkLabel(tg, text="Text", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self._font_scale = ctk.CTkSlider(tg, from_=50, to=180, command=lambda v: self._upd())
        self._font_scale.pack(fill="x", padx=5, pady=2)
        self._show_labels = ctk.CTkCheckBox(tg, text="Show field labels", command=self._upd)
        self._show_labels.pack(anchor="w", padx=5)
        self._align = ctk.CTkOptionMenu(tg, values=["left", "center", "right"], command=lambda v: self._upd())
        self._align.pack(fill="x", padx=5, pady=2)
        self._max_fields = ctk.CTkEntry(tg, placeholder_text="4")
        self._max_fields.pack(fill="x", padx=5, pady=2)

        # fields
        fg = ctk.CTkFrame(left)
        fg.pack(fill="x", pady=4)
        ctk.CTkLabel(fg, text="Fields to show", font=("", 12, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self._field_cbs = {}
        if self.settings:
            cd = ColumnDefinition(self.db)
            for col in cd.get_all():
                cb = ctk.CTkCheckBox(fg, text=col["column_name"], command=self._upd)
                cb.pack(anchor="w", padx=10)
                self._field_cbs[col["column_name"]] = cb

        # right - preview
        ctk.CTkLabel(right, text="Preview", font=("", 14, "bold")).pack(pady=5)
        self._preview = ctk.CTkLabel(right, text="", width=400, height=200)
        self._preview.pack(fill="both", expand=True, padx=5, pady=5)

        bf = ctk.CTkFrame(self)
        bf.grid(row=3, column=0, pady=10)
        ctk.CTkButton(bf, text="Save Template", command=self._save).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="Cancel", fg_color="#555", hover_color="#666", command=self.destroy).pack(side="left", padx=4)

        self._loading = False
        self._upd()

    def _color_row(self, parent, label):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=5, pady=1)
        ctk.CTkLabel(f, text=label, width=80).pack(side="left")
        btn = ctk.CTkButton(f, text="", width=30, height=24, fg_color="#ffffff", hover_color="#eee", command=lambda: self._pick_color(btn))
        btn.pack(side="right")
        return btn

    def _pick_color(self, btn):
        c = colorchooser.askcolor(color=btn.cget("fg_color") or "#ffffff")[1]
        if c:
            btn.configure(fg_color=c)
            self._upd()

    def _upd(self, *_):
        if self._loading:
            return
        try:
            w = int(self._w_spin.get() or 40)
        except ValueError:
            w = 40
        try:
            h = int(self._h_spin.get() or 13)
        except ValueError:
            h = 13
        tpl = {
            "width_mm": w, "height_mm": h,
            "show_qr": bool(self._show_qr.get()),
            "show_sample_id": bool(self._show_id.get()),
            "barcode_height_pct": int(self._bc_h.get()),
            "barcode_width_pct": int(self._bc_w.get()),
            "show_qr_code": bool(self._show_qr_code.get()),
            "qr_code_size_pct": int(self._qr_size.get()),
            "bg_color": self._bg_color.cget("fg_color") or "#ffffff",
            "text_color": self._text_color.cget("fg_color") or "#000000",
            "label_color": self._label_color.cget("fg_color") or "#666666",
            "font_scale": int(self._font_scale.get()),
            "show_labels": bool(self._show_labels.get()),
            "text_align": self._align.get(),
        }
        try:
            tpl["max_fields"] = int(self._max_fields.get() or 4)
        except ValueError:
            tpl["max_fields"] = 4
        renderer = LabelRenderer(width_mm=w, height_mm=h)
        img = renderer.render("NU0000000001", {"Sample ID": "NU0000000001", "Type": "Blood", "Patient": "J. Doe"}, template=tpl)
        photo = ImageTk.PhotoImage(img.resize((min(400, img.width), int(min(400, img.width) * img.height / img.width)), Image.LANCZOS))
        self._preview.configure(image=photo)
        self._preview.image = photo

    def _save(self):
        tpl = {
            "width_mm": int(self._w_spin.get() or 35),
            "height_mm": int(self._h_spin.get() or 15),
            "show_qr": bool(self._show_qr.get()),
            "show_sample_id": bool(self._show_id.get()),
            "barcode_height_pct": int(self._bc_h.get()),
            "barcode_width_pct": int(self._bc_w.get()),
            "show_qr_code": bool(self._show_qr_code.get()),
            "qr_code_size_pct": int(self._qr_size.get()),
            "bg_color": self._bg_color.cget("fg_color") or "#ffffff",
            "text_color": self._text_color.cget("fg_color") or "#000000",
            "label_color": self._label_color.cget("fg_color") or "#666666",
            "font_scale": int(self._font_scale.get()),
            "show_labels": bool(self._show_labels.get()),
            "text_align": self._align.get(),
            "max_fields": int(self._max_fields.get() or 4),
            "fields": [n for n, cb in self._field_cbs.items() if cb.get()],
        }
        if self.settings:
            save_template(self.settings, tpl)
            self.settings.set("label_width_mm", str(tpl["width_mm"]))
            self.settings.set("label_height_mm", str(tpl["height_mm"]))
            messagebox.showinfo("Saved", "Label template saved.")
            self.destroy()


# ── Print Dialog ────────────────────────────────────────────────────

class PrintDialog(ctk.CTkToplevel):
    def __init__(self, parent, qr_code, fields_dict, db=None):
        super().__init__(parent)
        self.qr_code = qr_code
        self.fields_dict = fields_dict
        self.db = db
        self.settings = SettingsModel(db) if db else None
        self.title(f"Print Label — {qr_code}")
        self.geometry("550x500")
        self.transient(parent)
        self.grab_set()
        self.after(100, self.lift)
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"Print Label — {self.qr_code}", font=("", 16, "bold"), text_color="#4da6ff").grid(row=0, column=0, pady=(10, 5))

        pf = ctk.CTkScrollableFrame(self)
        pf.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self._preview = ctk.CTkLabel(pf, text="", width=400, height=150)
        self._preview.pack(pady=5)

        ctk.CTkLabel(pf, text="Printer Mode:").pack(anchor="w")
        self._mode = ctk.CTkOptionMenu(pf, values=["System Printer", "Thermal (ESC/POS)"], command=self._on_mode)
        self._mode.pack(fill="x", pady=2)

        self._thermal_frame = ctk.CTkFrame(pf)
        self._thermal_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(self._thermal_frame, text="Connection:").pack(anchor="w")
        self._backend = ctk.CTkOptionMenu(self._thermal_frame, values=["network", "usb", "serial"])
        self._backend.pack(fill="x", pady=2)
        ctk.CTkLabel(self._thermal_frame, text="Address:").pack(anchor="w")
        self._addr = ctk.CTkLabel(self._thermal_frame, text="192.168.1.100:9100", text_color="#9e9e9e")
        self._addr.pack(anchor="w")

        ctk.CTkLabel(pf, text="Copies:").pack(anchor="w")
        self._copies = ctk.CTkEntry(pf, placeholder_text="1")
        self._copies.insert(0, "1")
        self._copies.pack(fill="x", pady=2)

        bf = ctk.CTkFrame(self)
        bf.grid(row=2, column=0, pady=10)
        ctk.CTkButton(bf, text="Print", command=self._do_print).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="Cancel", fg_color="#555", hover_color="#666", command=self.destroy).pack(side="left", padx=4)

        self._on_mode(None)

    def _on_mode(self, _):
        is_thermal = self._mode.get() == "Thermal (ESC/POS)"
        self._thermal_frame.pack() if is_thermal else self._thermal_frame.pack_forget()

    def _do_print(self):
        try:
            is_thermal = self._mode.get() == "Thermal (ESC/POS)"
            copies = int(self._copies.get() or 1)
            host = "192.168.1.100"
            port = 9100
            if is_thermal:
                addr = self._addr.cget("text")
                if ":" in addr:
                    host, port = addr.split(":")
                    port = int(port)
            tpl = load_template(self.settings) if self.settings else None
            print_label(
                qr_code=self.qr_code, fields_dict=self.fields_dict,
                printer_mode="thermal" if is_thermal else "system",
                backend=self._backend.get() if is_thermal else "network",
                host=host, port=port, thermal_copies=copies,
                label_width_mm=int(self.settings.get("label_width_mm","40")) if self.settings else 40,
                label_height_mm=int(self.settings.get("label_height_mm","13")) if self.settings else 13,
                template=tpl,
            )
            messagebox.showinfo("Printed", "Label sent to printer.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print:\n{e}")


# ── Settings Widget ─────────────────────────────────────────────────

class SettingsWidget(ctk.CTkScrollableFrame):
    def __init__(self, master, db=None, db_path=None, **kw):
        super().__init__(master, **kw)
        self.db = db
        self.db_path = db_path or (db.db_url if db else "")
        self.settings_model = SettingsModel(db) if db else None
        self.grid_columnconfigure(0, weight=1)
        self._setup_ui()

    def _setup_ui(self):
        ctk.CTkLabel(self, text="Settings", font=("", 18, "bold"), text_color="#4da6ff").pack(anchor="w", pady=(10, 5))

        # Printer
        pg = ctk.CTkFrame(self)
        pg.pack(fill="x", pady=5)
        ctk.CTkLabel(pg, text="Printer Settings", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        f = ctk.CTkFrame(pg, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(f, text="Mode:", width=100).pack(side="left")
        self._printer_mode = ctk.CTkOptionMenu(f, values=["System Printer", "Thermal (ESC/POS)"], command=self._on_printer)
        self._printer_mode.pack(side="left", fill="x", expand=True)

        self._thermal_f = ctk.CTkFrame(pg, fg_color="transparent")
        self._thermal_f.pack(fill="x", padx=10, pady=2)
        self._printer_backend = ctk.CTkOptionMenu(self._thermal_f, values=["network", "usb", "serial"], width=200)
        self._printer_backend.pack(anchor="w", pady=2)
        self._printer_host = ctk.CTkEntry(self._thermal_f, placeholder_text="192.168.1.100", width=300)
        self._printer_host.pack(anchor="w", pady=2)
        self._printer_port = ctk.CTkEntry(self._thermal_f, placeholder_text="9100", width=300)
        self._printer_port.pack(anchor="w", pady=2)

        sz = ctk.CTkFrame(pg, fg_color="transparent")
        sz.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(sz, text="Label size (mm):").pack(side="left", padx=(0, 6))
        self._lw = ctk.CTkEntry(sz, width=60, placeholder_text="35")
        self._lw.pack(side="left")
        ctk.CTkLabel(sz, text="×").pack(side="left", padx=4)
        self._lh = ctk.CTkEntry(sz, width=60, placeholder_text="15")
        self._lh.pack(side="left")
        self._gap = ctk.CTkEntry(sz, width=60, placeholder_text="3")
        self._gap.pack(side="left", padx=(20, 0))

        ctk.CTkButton(pg, text="Design Label Layout", fg_color="#ff9800", hover_color="#f57c00", command=self._open_designer).pack(anchor="w", padx=10, pady=4)

        # Web
        wg = ctk.CTkFrame(self)
        wg.pack(fill="x", pady=5)
        ctk.CTkLabel(wg, text="Web Preview Server", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        wf = ctk.CTkFrame(wg, fg_color="transparent")
        wf.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(wf, text="Port:", width=100).pack(side="left")
        self._web_port = ctk.CTkEntry(wf, placeholder_text="8765", width=100)
        self._web_port.pack(side="left")
        ctk.CTkLabel(wg, text="Open http://<ip>:<port> on your phone", text_color="#9e9e9e", font=("", 11)).pack(anchor="w", padx=10, pady=2)

        # Backup
        bg = ctk.CTkFrame(self)
        bg.pack(fill="x", pady=5)
        ctk.CTkLabel(bg, text="Google Drive Backup", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        self._backup_enabled = ctk.CTkCheckBox(bg, text="Enable automatic backups")
        self._backup_enabled.pack(anchor="w", padx=10)
        bf = ctk.CTkFrame(bg, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(bf, text="Interval (hours):", width=120).pack(side="left")
        self._backup_interval = ctk.CTkEntry(bf, placeholder_text="24", width=100)
        self._backup_interval.pack(side="left")
        ctk.CTkButton(bg, text="Backup Now", command=self._backup_now).pack(anchor="w", padx=10, pady=4)

        # DB
        dg = ctk.CTkFrame(self)
        dg.pack(fill="x", pady=5)
        ctk.CTkLabel(dg, text="Database", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        db_type = "PostgreSQL" if (self.db and self.db.db_type == 'postgresql') else "SQLite"
        ctk.CTkLabel(dg, text=f"Current: {db_type}", text_color="#4da6ff", font=("", 12, "bold")).pack(anchor="w", padx=10)
        self._pg_url = ctk.CTkEntry(dg, placeholder_text="postgresql://user:password@host:5432/dbname", width=500)
        self._pg_url.pack(anchor="w", padx=10, pady=4)
        pdf = ctk.CTkFrame(dg, fg_color="transparent")
        pdf.pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(pdf, text="Connect PostgreSQL", width=160, command=self._connect_pg).pack(side="left", padx=2)
        ctk.CTkButton(pdf, text="Use SQLite", fg_color="#555", hover_color="#666", width=120, command=self._disconnect_pg).pack(side="left", padx=2)

        ctk.CTkButton(self, text="Delete All Data", fg_color="#d32f2f", hover_color="#b71c1c", command=self._delete_all).pack(anchor="w", padx=5, pady=10)

        ctk.CTkButton(self, text="Save Settings", command=self._save).pack(pady=10)

        self._load_settings()

    def _load_settings(self):
        if not self.settings_model:
            return
        s = self.settings_model.get_all()
        mode = s.get("printer_mode", "system")
        self._printer_mode.set("System Printer" if mode == "system" else "Thermal (ESC/POS)")
        self._printer_backend.set(s.get("printer_backend", "network"))
        self._printer_host.insert(0, s.get("printer_host", ""))
        self._printer_port.insert(0, s.get("printer_port", "9100"))
        self._lw.insert(0, s.get("label_width_mm", "35"))
        self._lh.insert(0, s.get("label_height_mm", "15"))
        self._gap.insert(0, s.get("label_gap_mm", "3"))
        self._web_port.insert(0, s.get("web_port", "8765"))
        self._backup_enabled.select() if s.get("backup_enabled") == "true" else None
        self._backup_interval.insert(0, s.get("backup_interval_hours", "24"))
        self._on_printer(None)

    def _on_printer(self, _):
        is_thermal = self._printer_mode.get() == "Thermal (ESC/POS)"
        if is_thermal:
            self._thermal_f.pack(fill="x", padx=10, pady=2)
        else:
            self._thermal_f.pack_forget()

    def _open_designer(self):
        LabelDesignerDialog(self, db=self.db)

    def _save(self):
        if not self.settings_model:
            return
        self.settings_model.set("printer_mode", "system" if self._printer_mode.get() == "System Printer" else "thermal")
        self.settings_model.set("printer_backend", self._printer_backend.get())
        self.settings_model.set("printer_host", self._printer_host.get())
        self.settings_model.set("printer_port", self._printer_port.get())
        self.settings_model.set("label_width_mm", self._lw.get() or "35")
        self.settings_model.set("label_height_mm", self._lh.get() or "15")
        self.settings_model.set("label_gap_mm", self._gap.get() or "3")
        self.settings_model.set("web_port", self._web_port.get() or "8765")
        self.settings_model.set("backup_enabled", "true" if self._backup_enabled.get() else "false")
        self.settings_model.set("backup_interval_hours", self._backup_interval.get() or "24")
        messagebox.showinfo("Saved", "Settings saved successfully.")

    def _connect_pg(self):
        url = self._pg_url.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Enter a PostgreSQL URL.")
            return
        if not url.startswith("postgresql://"):
            messagebox.showwarning("Invalid URL", "URL must start with postgresql://")
            return
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
            conn.close()
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            return
        save_db_config({"postgresql_url": url})
        messagebox.showinfo("Saved", "PostgreSQL URL saved. Restart the app.")

    def _disconnect_pg(self):
        save_db_config({})
        self._pg_url.delete(0, "end")
        messagebox.showinfo("Disconnected", "PostgreSQL removed. Restart to use SQLite.")

    def _delete_all(self):
        if messagebox.askyesno("Delete All Data", "Delete ALL specimen data?\n\nThis cannot be undone!"):
            if messagebox.askyesno("Confirm", "Are you sure?"):
                try:
                    SpecimenModel(self.db).delete_all()
                    messagebox.showinfo("Deleted", "All data deleted.")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

    def _backup_now(self):
        try:
            GoogleDriveBackup(self.db_path).backup()
            messagebox.showinfo("Backup Complete", "Database backed up to Google Drive.")
        except FileNotFoundError as e:
            messagebox.showwarning("Credentials Missing", str(e))
        except Exception as e:
            messagebox.showerror("Backup Failed", str(e))


# ── Main Window ─────────────────────────────────────────────────────

class MainWindow(ctk.CTk):
    def __init__(self, db_path=None):
        super().__init__()
        self.db = DatabaseConnection.get_instance(db_path)
        self.db_path = self.db.db_url
        self.auth = None
        self.web_server = None
        self.title("NUBRI Biobank Label System")
        self.geometry("1100x750")
        self.minsize(900, 700)

        if not self._authenticate():
            self.destroy()
            return

        self._setup_ui()
        self._setup_menu_bar()
        self._start_web_server()

    def _authenticate(self):
        dlg = LoginDialog(self, db=self.db)
        self.wait_window(dlg)
        if dlg.auth:
            self.auth = dlg.auth
            return True
        return False

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        tab_names = ["Create Label", "Search / Scan", "Database", "Manage Columns", "Settings"]
        for name in tab_names:
            self._tabs.add(name)

        self._label_form = LabelFormWidget(self._tabs.tab("Create Label"), self.db, on_label_created=self._on_label_created)
        self._label_form.pack(fill="both", expand=True)

        self._search = SearchWidget(self._tabs.tab("Search / Scan"), self.db)
        self._search.pack(fill="both", expand=True)

        self._db_view = DatabaseViewWidget(self._tabs.tab("Database"), self.db)
        self._db_view.pack(fill="both", expand=True)

        self._schema = SchemaManagerWidget(self._tabs.tab("Manage Columns"), self.db, on_schema_changed=lambda: self._label_form.refresh())
        self._schema.pack(fill="both", expand=True)

        self._settings = SettingsWidget(self._tabs.tab("Settings"), self.db, self.db_path)
        self._settings.pack(fill="both", expand=True)

        # Status bar
        sb = ctk.CTkFrame(self, fg_color="#2b2b2b", height=28)
        sb.grid(row=1, column=0, sticky="ew")
        sb.grid_columnconfigure(0, weight=1)
        self._status = ctk.CTkEntry(sb, state="readonly", fg_color="#2b2b2b", text_color="#e0e0e0", border_width=0)
        self._status.grid(row=0, column=0, sticky="ew", padx=8)
        db_text = f"DB: PostgreSQL" if self.db.db_type == 'postgresql' else "DB: SQLite"
        db_color = "#4caf50" if self.db.db_type == 'postgresql' else "#9e9e9e"
        ctk.CTkLabel(sb, text=db_text, text_color=db_color, font=("", 11, "bold")).grid(row=0, column=1, sticky="e", padx=8)
        if self.auth and self.auth.is_authenticated:
            ctk.CTkLabel(sb, text=f"Signed in: {self.auth.get_user_name()}", text_color="#4caf50", font=("", 11)).grid(row=0, column=2, sticky="e", padx=8)

    def _setup_menu_bar(self):
        import tkinter as tk
        mb = tk.Menu(self, bg="#2b2b2b", fg="#e0e0e0", activebackground="#333", activeforeground="#4da6ff")
        file_menu = tk.Menu(mb, tearoff=0, bg="#2b2b2b", fg="#e0e0e0", activebackground="#333", activeforeground="#4da6ff")
        file_menu.add_command(label="Sign Out", command=self._sign_out)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close)
        mb.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(mb, tearoff=0, bg="#2b2b2b", fg="#e0e0e0", activebackground="#333", activeforeground="#4da6ff")
        tools_menu.add_command(label="Refresh Forms", command=self._refresh_all)
        tools_menu.add_command(label="Backup Now", command=self._backup_now)
        mb.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(mb, tearoff=0, bg="#2b2b2b", fg="#e0e0e0", activebackground="#333", activeforeground="#4da6ff")
        help_menu.add_command(label="About", command=self._show_about)
        mb.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=mb)

    def _set_status(self, text):
        self._status.configure(state="normal")
        self._status.delete(0, "end")
        self._status.insert(0, text)
        self._status.configure(state="readonly")

    def _refresh_all(self):
        self._label_form.refresh()
        self._db_view._load()
        self._set_status("Forms refreshed")

    def _show_about(self):
        messagebox.showinfo("About", "NUBRI Biobank Label System v1.0\n\nDesktop app for biobank specimen labels with QR codes.")

    def _sign_out(self):
        if messagebox.askyesno("Sign Out", "Are you sure?"):
            if self.auth:
                self.auth.logout()
            if self.web_server:
                self.web_server.stop()
                self.web_server = None
            self.destroy()
            MainWindow(db_path=self.db_path)
            self.quit()

    def _start_web_server(self):
        try:
            settings = SettingsModel(self.db)
            port = int(settings.get("web_port", "8765"))
            self.web_server = WebServer(self.db, port=port, auth=self.auth)
            self.web_server.start()
            ip = _get_local_ip()
            self._set_status(f"Web preview: http://{ip}:{port}")
        except Exception as e:
            self._set_status(f"Web server failed: {e}")

    def _on_label_created(self, qr_code):
        self._set_status(f"Last label created: {qr_code}")

    def _backup_now(self):
        try:
            name = GoogleDriveBackup(self.db_path).backup()
            messagebox.showinfo("Backup Complete", f"Backup saved as: {name}")
        except FileNotFoundError:
            messagebox.showwarning("Credentials Missing", "Place client_secret.json in the credentials/ folder.")
        except Exception as e:
            messagebox.showerror("Backup Failed", str(e))

    def close(self):
        if self.web_server:
            self.web_server.stop()
        self.destroy()


# ── Entry ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NUBRI Biobank Label System")
    parser.add_argument("--db", "-d", help="Database path or PostgreSQL URL")
    args = parser.parse_args()
    app = MainWindow(db_path=args.db)
    app.mainloop()

if __name__ == "__main__":
    main()
