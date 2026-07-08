import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveBackup:
    def __init__(self, db_url, credentials_dir=None):
        self.db_url = db_url
        self.is_postgresql = db_url.startswith("postgresql://")
        if credentials_dir is None:
            credentials_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "credentials"
            )
        self.credentials_dir = credentials_dir
        self.token_path = os.path.join(credentials_dir, "token.json")
        self.creds_path = os.path.join(credentials_dir, "client_secret.json")
        self.service = None

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.creds_path):
                    raise FileNotFoundError(
                        "Google Drive client_secret.json not found. "
                        f"Place it in: {self.credentials_dir}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())
        self.service = build("drive", "v3", credentials=creds)

    def _ensure_backup_folder(self):
        query = "name='BiobankBackups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, spaces="drive", fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        file_metadata = {
            "name": "BiobankBackups",
            "mimeType": "application/vnd.google-apps.folder"
        }
        file = self.service.files().create(body=file_metadata, fields="id").execute()
        return file["id"]

    def _create_backup_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.is_postgresql:
            backup_name = f"biobank_pg_backup_{timestamp}.dump"
            tmp = tempfile.NamedTemporaryFile(suffix=".dump", delete=False)
            tmp.close()
            try:
                subprocess.run(
                    ["pg_dump", "--no-owner", "--no-acl", "-Fc", self.db_url, "-f", tmp.name],
                    check=True, capture_output=True, text=True
                )
            except subprocess.CalledProcessError as e:
                os.unlink(tmp.name)
                raise RuntimeError(f"pg_dump failed: {e.stderr}") from e
            except FileNotFoundError as e:
                os.unlink(tmp.name)
                raise RuntimeError(
                    "pg_dump not found. Install PostgreSQL client tools."
                ) from e
            return tmp.name, backup_name
        else:
            backup_name = f"biobank_backup_{timestamp}.db"
            tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            shutil.copy2(self.db_url, tmp.name)
            tmp.close()
            return tmp.name, backup_name

    def backup(self):
        if not self.service:
            self._authenticate()
        folder_id = self._ensure_backup_folder()
        tmp_path, backup_name = self._create_backup_file()

        try:
            media = MediaFileUpload(tmp_path, mimetype="application/octet-stream", resumable=True)
            file_metadata = {
                "name": backup_name,
                "parents": [folder_id]
            }
            self.service.files().create(body=file_metadata, media_body=media).execute()
        finally:
            os.unlink(tmp_path)

        return backup_name

    def list_backups(self):
        if not self.service:
            self._authenticate()
        folder_id = self._ensure_backup_folder()
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces="drive",
            orderBy="createdTime desc",
            fields="files(id, name, createdTime, size)"
        ).execute()
        return results.get("files", [])

    def restore(self, file_id, restore_path):
        if not self.service:
            self._authenticate()
        request = self.service.files().get_media(fileId=file_id)
        with open(restore_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
