import sqlite3
import os
from threading import Lock


class DatabaseConnection:
    _instance = None
    _lock = Lock()

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "biobank.db"
            )
        self.db_path = db_path
        self.conn = None
        self._init_db()

    @classmethod
    def get_instance(cls, db_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
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
            VALUES ('Collection Date', 'TEXT', 3, 0);

            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Storage Location', 'TEXT', 4, 0);

            INSERT OR IGNORE INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Notes', 'TEXT', 5, 0);

            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_backend', 'network');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_host', '192.168.1.100');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('printer_port', '9100');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_width_mm', '100');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_height_mm', '50');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('web_port', '5000');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('backup_enabled', 'false');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('backup_interval_hours', '24');

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
        self.conn.commit()

    def get_connection(self):
        if self.conn is None:
            self._init_db()
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
