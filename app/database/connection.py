import json
import os
from threading import Lock


CONFIG_FILENAME = "db_config.json"


def _get_default_db_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_config_path():
    return os.path.join(_get_default_db_dir(), CONFIG_FILENAME)


def load_db_config():
    path = _get_config_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_db_config(config):
    path = _get_config_path()
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


class DatabaseConnection:
    _instance = None
    _lock = Lock()

    def __init__(self, db_url=None):
        if db_url is None:
            cfg = load_db_config()
            pg_url = cfg.get("postgresql_url", "").strip()
            if pg_url:
                db_url = pg_url
            else:
                db_url = os.path.join(_get_default_db_dir(), "biobank.db")
        self.db_url = db_url
        self.db_type = 'postgresql' if db_url and db_url.startswith('postgresql://') else 'sqlite'
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
        else:
            cur = self._conn.cursor()
            if params is not None:
                pg_sql = sql.replace('?', '%s')
                cur.execute(pg_sql, params)
            else:
                cur.execute(sql)
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
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_width_mm', '40');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_height_mm', '13');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('label_gap_mm', '3');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('print_gap_mm', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('web_port', '5000');
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
        statements = [
            """
            CREATE TABLE IF NOT EXISTS column_definitions (
                id SERIAL PRIMARY KEY,
                column_name TEXT UNIQUE NOT NULL,
                column_type TEXT DEFAULT 'TEXT',
                display_order INTEGER DEFAULT 0,
                is_required INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS specimens (
                id SERIAL PRIMARY KEY,
                qr_code TEXT UNIQUE NOT NULL,
                custom_fields TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_specimens_qr ON specimens(qr_code);",
            "CREATE INDEX IF NOT EXISTS idx_specimens_created ON specimens(created_at);",
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Sample ID', 'TEXT', 0, 1)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Sample Type', 'TEXT', 1, 1)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Patient Name', 'TEXT', 2, 1)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Collection Date', 'DATE', 3, 0)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Storage Location', 'TEXT', 4, 0)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO column_definitions (column_name, column_type, display_order, is_required)
            VALUES ('Notes', 'TEXT', 5, 0)
            ON CONFLICT (column_name) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('printer_backend', 'network')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('printer_host', '192.168.1.100')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('printer_port', '9100')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('label_width_mm', '40')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('label_height_mm', '13')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('label_gap_mm', '3')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('print_gap_mm', '1')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('web_port', '5000')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('backup_enabled', 'false')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('backup_interval_hours', '24')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            INSERT INTO settings (key, value) VALUES ('next_sample_id', '1')
            ON CONFLICT (key) DO NOTHING;
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        ]
        for stmt in statements:
            self._conn.execute(stmt.strip())
        self._conn.commit()
