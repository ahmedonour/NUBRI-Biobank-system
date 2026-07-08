import json, csv, io
import uuid
from datetime import datetime
from .connection import DatabaseConnection


class ColumnDefinition:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()

    def get_all(self):
        cursor = self.conn.execute(
            "SELECT * FROM column_definitions WHERE is_active = 1 ORDER BY display_order"
        )
        return [dict(row) for row in cursor.fetchall()]

    def add(self, column_name, column_type="TEXT", is_required=False):
        cursor = self.conn.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM column_definitions"
        )
        next_order = cursor.fetchone()["next_order"]
        self.conn.execute(
            "INSERT INTO column_definitions (column_name, column_type, display_order, is_required) VALUES (?, ?, ?, ?)",
            (column_name, column_type, next_order, 1 if is_required else 0)
        )
        self.conn.commit()

    def update(self, col_id, column_name=None, column_type=None, is_required=None, display_order=None):
        fields = []
        values = []
        if column_name is not None:
            fields.append("column_name = ?")
            values.append(column_name)
        if column_type is not None:
            fields.append("column_type = ?")
            values.append(column_type)
        if is_required is not None:
            fields.append("is_required = ?")
            values.append(1 if is_required else 0)
        if display_order is not None:
            fields.append("display_order = ?")
            values.append(display_order)
        if fields:
            values.append(col_id)
            self.conn.execute(
                f"UPDATE column_definitions SET {', '.join(fields)} WHERE id = ?",
                values
            )
            self.conn.commit()

    def delete(self, col_id):
        self.conn.execute("UPDATE column_definitions SET is_active = 0 WHERE id = ?", (col_id,))
        self.conn.commit()

    def reorder(self, ordered_ids):
        for idx, col_id in enumerate(ordered_ids):
            self.conn.execute(
                "UPDATE column_definitions SET display_order = ? WHERE id = ?",
                (idx, col_id)
            )
        self.conn.commit()


class SpecimenModel:
    def __init__(self, db=None):
        self.db = db or DatabaseConnection.get_instance()
        self.conn = self.db.get_connection()

    def generate_qr_code(self):
        return str(uuid.uuid4()).replace("-", "")[:16].upper()

    def create(self, custom_fields_dict):
        qr_code = custom_fields_dict.get("Sample ID") or self.generate_qr_code()
        self.conn.execute(
            "INSERT INTO specimens (qr_code, custom_fields) VALUES (?, ?)",
            (qr_code, json.dumps(custom_fields_dict))
        )
        self.conn.commit()
        return qr_code

    def get_by_qr(self, qr_code):
        cursor = self.conn.execute(
            "SELECT * FROM specimens WHERE qr_code = ?",
            (qr_code,)
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["custom_fields"] = json.loads(result["custom_fields"])
            return result
        return None

    def get_by_id(self, specimen_id):
        cursor = self.conn.execute(
            "SELECT * FROM specimens WHERE id = ?",
            (specimen_id,)
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["custom_fields"] = json.loads(result["custom_fields"])
            return result
        return None

    def update(self, specimen_id, custom_fields_dict):
        self.conn.execute(
            "UPDATE specimens SET custom_fields = ?, updated_at = ? WHERE id = ?",
            (json.dumps(custom_fields_dict), datetime.now().isoformat(), specimen_id)
        )
        self.conn.commit()

    def search(self, query, column_name=None):
        like_query = f"%{query}%"
        db_type = self.db.db_type
        if column_name:
            if db_type == 'postgresql':
                sql = """
                    SELECT * FROM specimens
                    WHERE custom_fields::json ->> ? LIKE ?
                    ORDER BY created_at DESC
                """
            else:
                sql = """
                    SELECT * FROM specimens
                    WHERE json_extract(custom_fields, ?) LIKE ?
                    ORDER BY created_at DESC
                """
            field_path = f"$.{column_name}" if db_type == 'sqlite' else column_name
            cursor = self.conn.execute(sql, (field_path, like_query))
        else:
            if db_type == 'postgresql':
                sql = """
                    SELECT * FROM specimens
                    WHERE qr_code LIKE ?
                    OR custom_fields::text LIKE ?
                    ORDER BY created_at DESC
                """
            else:
                sql = """
                    SELECT * FROM specimens
                    WHERE qr_code LIKE ?
                    OR custom_fields LIKE ?
                    ORDER BY created_at DESC
                """
            cursor = self.conn.execute(sql, (like_query, like_query))
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["custom_fields"] = json.loads(result["custom_fields"])
            results.append(result)
        return results

    def get_all(self, limit=100, offset=0):
        cursor = self.conn.execute(
            "SELECT * FROM specimens ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["custom_fields"] = json.loads(result["custom_fields"])
            results.append(result)
        return results

    def count(self):
        cursor = self.conn.execute("SELECT COUNT(*) AS count FROM specimens")
        return cursor.fetchone()["count"]

    def get_all_unpaginated(self):
        cursor = self.conn.execute("SELECT * FROM specimens ORDER BY created_at DESC")
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["custom_fields"] = json.loads(result["custom_fields"])
            results.append(result)
        return results

    def export_to_csv(self, filepath, columns):
        specimens = self.get_all_unpaginated()
        col_names = [c["column_name"] for c in columns]
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["QR Code"] + col_names + ["Created", "Updated"])
            for spec in specimens:
                fields = spec["custom_fields"]
                row = [spec["qr_code"]]
                row.extend(fields.get(n, "") for n in col_names)
                row.append(spec.get("created_at", ""))
                row.append(spec.get("updated_at", ""))
                writer.writerow(row)

    def import_from_csv(self, filepath, columns):
        col_names = [c["column_name"] for c in columns]
        imported = 0
        errors = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("Empty CSV file")
            for row_num, row in enumerate(reader, start=2):
                try:
                    data = {}
                    for n in col_names:
                        data[n] = row.get(n, "").strip()
                    qr_code = row.get("QR Code", "").strip()
                    if qr_code:
                        existing = self.get_by_qr(qr_code)
                        if existing:
                            self.update(existing["id"], data)
                        else:
                            self.conn.execute(
                                "INSERT INTO specimens (qr_code, custom_fields) VALUES (?, ?)",
                                (qr_code, json.dumps(data))
                            )
                    else:
                        self.create(data)
                    self.conn.commit()
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {e}")
        return imported, errors

    @staticmethod
    def get_template_csv(columns):
        col_names = [c["column_name"] for c in columns]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["QR Code"] + col_names + ["Created", "Updated"])
        writer.writerow(["NU0000000001"] + [""] * (len(col_names) + 2))
        return output.getvalue()

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
        cursor = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set(self, key, value):
        if self.db.db_type == 'postgresql':
            self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, str(value))
            )
        else:
            self.conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
        self.conn.commit()

    def get_all(self):
        cursor = self.conn.execute("SELECT * FROM settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    def get_next_sample_id(self):
        raw = self.get("next_sample_id", "1")
        try:
            num = int(raw)
        except ValueError:
            num = 1
        return f"NU{num:010d}"

    def increment_next_sample_id(self):
        raw = self.get("next_sample_id", "1")
        try:
            num = int(raw)
        except ValueError:
            num = 1
        self.set("next_sample_id", str(num + 1))
