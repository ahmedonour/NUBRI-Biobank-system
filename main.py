#!/usr/bin/env python3
"""
NUBRI Biobank Label System

Desktop app + auto-start PocketBase + web preview server.
"""

import os
import sys
import subprocess
import platform
import shutil
import zipfile
import tempfile
import urllib.request
import argparse


BIOBANK_DIR = os.path.join(os.path.expanduser("~"), "Biobank")
PB_DIR = os.path.join(BIOBANK_DIR, "pocketbase")
PB_BIN = os.path.join(PB_DIR, "pocketbase")
PB_DATA_DIR = os.path.join(BIOBANK_DIR, "pb_data")
LOGS_DIR = os.path.join(BIOBANK_DIR, "logs")
PB_PORT = "8090"


def _ensure_dirs():
    for d in [BIOBANK_DIR, PB_DIR, PB_DATA_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)


def _download_pocketbase():
    """Download PocketBase binary if not present."""
    if os.path.exists(PB_BIN):
        return

    os_name = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        arch = "amd64"
    elif arch in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        print(f"Warning: unsupported arch {arch}, PocketBase may not work.")

    url = (f"https://github.com/pocketbase/pocketbase/releases/latest/download/"
           f"pocketbase_{os_name}_{arch}.zip")

    print(f"Downloading PocketBase from {url}...")
    zip_path = tempfile.mktemp(suffix=".zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(PB_DIR)
        os.chmod(PB_BIN, 0o755)
        print(f"PocketBase installed at {PB_BIN}")
    finally:
        if os.path.exists(zip_path):
            os.unlink(zip_path)


def _start_pocketbase():
    """Start PocketBase server if not already running."""
    import urllib.request as req
    import urllib.error

    try:
        resp = req.urlopen(f"http://127.0.0.1:{PB_PORT}/api/health", timeout=2)
        if resp.status == 200:
            return  # Already running
    except (urllib.error.URLError, ConnectionError, OSError):
        pass

    _ensure_dirs()
    if not os.path.exists(PB_BIN):
        _download_pocketbase()

    log_path = os.path.join(LOGS_DIR, "pocketbase.log")
    err_path = os.path.join(LOGS_DIR, "pocketbase.err")

    with open(log_path, "a") as out, open(err_path, "a") as err:
        subprocess.Popen(
            [PB_BIN, "serve", "--http", f"127.0.0.1:{PB_PORT}", "--dir", PB_DATA_DIR],
            stdout=out, stderr=err,
            start_new_session=True
        )

    print(f"PocketBase started on http://127.0.0.1:{PB_PORT}")


def main():
    parser = argparse.ArgumentParser(description="NUBRI Biobank Label System")
    parser.add_argument("--db", "-d", help="Path to SQLite database file")
    parser.add_argument("--port", "-p", type=int, help="Web preview port")
    parser.add_argument("--no-pocketbase", action="store_true",
                        help="Skip auto-starting PocketBase")
    args = parser.parse_args()

    if not args.no_pocketbase:
        try:
            _start_pocketbase()
        except Exception as e:
            print(f"Warning: could not start PocketBase: {e}")
            print("You can start it manually with: pocketbase serve")

    db_path = args.db
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biobank.db")

    from PyQt5.QtWidgets import QApplication
    from app.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("NUBRI Biobank Label System")
    app.setOrganizationName("NUBRI")

    window = MainWindow(db_path=db_path)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
