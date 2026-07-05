#!/usr/bin/env python3
"""
NUBRI Biobank System — GUI Installer

Standalone setup wizard. Works both as a Python script and as a
PyInstaller-bundled .exe/.app. When bundled, all application files
are embedded inside the executable and extracted at runtime.

Usage (as script):      python installer.py
Usage (as .exe/.app):   double-click the built executable
"""

import os
import sys
import subprocess
import platform
import shutil
import zipfile
import tempfile
import json
import urllib.request
import urllib.error
from pathlib import Path

# ── Resolve resource path ──────────────────────────────────────────────
# When bundled with PyInstaller, files live inside sys._MEIPASS.
# When running as a script, files live next to this file.
def _resource_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


RESOURCE_DIR = _resource_path()

APP_NAME = "NUBRI Biobank"
INSTALL_DIR = Path.home() / "Biobank"
PB_DIR = INSTALL_DIR / "pocketbase"
PB_DATA_DIR = INSTALL_DIR / "pb_data"
LOGS_DIR = INSTALL_DIR / "logs"
CREDENTIALS_DIR = INSTALL_DIR / "credentials"
DB_PATH = INSTALL_DIR / "biobank.db"

# Bundled files shipped inside the executable
BUNDLED_ITEMS = ["app", "main.py", "requirements.txt", "scripts"]

# ── PyQt5 import (bail early with clear message if missing) ────────────
try:
    from PyQt5.QtWidgets import (
        QApplication, QWizard, QWizardPage, QVBoxLayout,
        QLabel, QPushButton, QProgressBar, QTextEdit, QCheckBox,
        QLineEdit, QFormLayout, QMessageBox, QGroupBox, QSpinBox,
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
except ImportError:
    print("PyQt5 is required to run the installer.")
    print("Install it first:  pip install PyQt5")
    sys.exit(1)

# ── Helpers ────────────────────────────────────────────────────────────

SYSTEM = platform.system()


def _check_python():
    """Return (installed: bool, path: str, version: str)."""
    try:
        r = subprocess.run(
            [sys.executable or "python3", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return True, sys.executable, r.stdout.strip()
    except Exception:
        pass
    # Fallback: check PATH
    for exe in ("python3", "python"):
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return True, shutil.which(exe) or exe, r.stdout.strip()
        except Exception:
            continue
    return False, "", ""


def _pip_installed():
    try:
        r = subprocess.run(
            [sys.executable or "python3", "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except Exception:
        return False


def _python_download_url():
    os_name = platform.system().lower()
    if os_name == "windows":
        return "https://www.python.org/downloads/"
    if os_name == "darwin":
        return "https://www.python.org/downloads/"
    return "https://www.python.org/downloads/"


# ── Install worker ─────────────────────────────────────────────────────

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks

    def run(self):
        total = len(self.tasks)
        for i, (name, func) in enumerate(self.tasks):
            self.progress.emit(int((i / total) * 100), f"Running: {name}")
            self.log.emit(f"[{i+1}/{total}] {name}...")
            try:
                func()
                self.log.emit(f"  {chr(10003)} {name}")
            except Exception as e:
                self.log.emit(f"  {chr(10007)} {name}: {str(e)}")
                self.finished.emit(False, f"Failed at step: {name}\n{str(e)}")
                return
        self.progress.emit(100, "Installation complete!")
        self.finished.emit(True, "All steps completed successfully.")


# ── Wizard Pages ───────────────────────────────────────────────────────

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(f"Welcome to {APP_NAME}")
        self.setSubTitle("This wizard installs everything needed to run the Biobank Label System.")

        layout = QVBoxLayout(self)

        has_py, py_path, py_ver = _check_python()
        has_pip = _pip_installed()

        status = []
        if has_py:
            status.append(f"<li>Python: <span style='color:#27ae60'>{chr(10003)}</span> {py_ver}</li>")
        else:
            status.append(f"<li>Python: <span style='color:#e74c3c'>{chr(10007)}</span> not found — will prompt to download</li>")
        if has_pip:
            status.append(f"<li>pip: <span style='color:#27ae60'>{chr(10003)}</span> available</li>")
        else:
            status.append(f"<li>pip: <span style='color:#e74c3c'>{chr(10007)}</span> not found — will install</li>")

        info = QLabel(
            f"<h3>{APP_NAME} v1.0</h3>"
            "<p>This installer will:</p>"
            "<ul>"
            "<li>Install Python dependencies</li>"
            "<li>Copy application files</li>"
            "<li>Download &amp; configure PocketBase server</li>"
            "<li>Create desktop shortcut</li>"
            "</ul>"
            f"<p><b>Install target:</b> {INSTALL_DIR}</p>"
            "<hr><p><b>System check:</b></p><ul>"
            + "".join(status) +
            "</ul><hr>"
            "<p>Click <b>Next</b> to begin.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)


class ConfigPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Configuration")
        self.setSubTitle("Choose installation options.")

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.pb_port = QSpinBox()
        self.pb_port.setRange(1024, 65535)
        self.pb_port.setValue(8090)
        form.addRow("PocketBase Port:", self.pb_port)

        self.web_port = QSpinBox()
        self.web_port.setRange(1024, 65535)
        self.web_port.setValue(5000)
        form.addRow("Web Preview Port:", self.web_port)

        layout.addLayout(form)
        layout.addSpacing(10)

        self.desktop_cb = QCheckBox("Create desktop shortcut")
        self.desktop_cb.setChecked(True)
        layout.addWidget(self.desktop_cb)

        self.autostart_cb = QCheckBox(
            "Auto-start PocketBase on login" +
            (" (macOS only)" if SYSTEM != "Darwin" else "")
        )
        self.autostart_cb.setChecked(SYSTEM == "Darwin")
        self.autostart_cb.setEnabled(SYSTEM == "Darwin")
        layout.addWidget(self.autostart_cb)

        self.install_printer_cb = QCheckBox("Install ESC/POS printer support (recommended)")
        self.install_printer_cb.setChecked(True)
        layout.addWidget(self.install_printer_cb)

        self.install_camera_cb = QCheckBox("Install QR camera scanning support")
        self.install_camera_cb.setChecked(True)
        layout.addWidget(self.install_camera_cb)

        layout.addStretch()


class InstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing")
        self.setSubTitle("Please wait while the installation runs.")

        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; color: #d4d4d4;
                font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px;
            }
        """)
        layout.addWidget(self.log_output)

    def initializePage(self):
        config = self.wizard().config_page
        tasks = self._build_tasks(config)
        self.worker = InstallWorker(tasks)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_output.append)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _build_tasks(self, config):
        tasks = []
        target = INSTALL_DIR

        # 1. Check Python
        def check_python():
            installed, path, ver = _check_python()
            if not installed or not _pip_installed():
                url = _python_download_url()
                raise RuntimeError(
                    "Python is not installed or pip is missing.\n\n"
                    f"Please download and install Python from:\n{url}\n\n"
                    "Make sure to check 'Add Python to PATH' during installation.\n"
                    "Then re-run this installer."
                )

        tasks.append(("Checking Python installation", check_python))

        # 2. Create directories
        def mkdirs():
            for d in [target, PB_DIR, PB_DATA_DIR, LOGS_DIR, CREDENTIALS_DIR]:
                d.mkdir(parents=True, exist_ok=True)

        tasks.append(("Creating directories", mkdirs))

        # 3. Install Python deps
        def install_deps():
            python = _check_python()[1] or sys.executable or "python3"
            cmd = [python, "-m", "pip", "install", "--upgrade", "pip"]
            subprocess.check_call(cmd, timeout=120)

            req_file = RESOURCE_DIR / "requirements.txt"
            cmd = [python, "-m", "pip", "install", "-r", str(req_file)]
            if not config.install_camera_cb.isChecked():
                cmd.extend(["--no-deps", "opencv-python", "pyzbar"])
            if not config.install_printer_cb.isChecked():
                cmd.extend(["--no-deps", "python-escpos"])
            subprocess.check_call(cmd, timeout=300)

        tasks.append(("Installing Python dependencies", install_deps))

        # 4. Copy app files
        def copy_app():
            for item in ["app", "main.py", "requirements.txt"]:
                src = RESOURCE_DIR / item
                dst = target / item
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        tasks.append(("Copying application files", copy_app))

        # 5. Download PocketBase
        def download_pb():
            pb_bin = PB_DIR / ("pocketbase.exe" if SYSTEM == "Windows" else "pocketbase")
            if pb_bin.exists():
                return

            os_name = platform.system().lower()
            arch = platform.machine().lower()
            if arch in ("x86_64", "amd64"):
                arch = "amd64"
            elif arch in ("aarch64", "arm64"):
                arch = "arm64"
            else:
                raise RuntimeError(f"Unsupported architecture: {arch}")

            if os_name == "windows":
                ext = ".exe"
            else:
                ext = ""

            url = (f"https://github.com/pocketbase/pocketbase/releases/latest/download/"
                   f"pocketbase_{os_name}_{arch}.zip")

            self.log.emit(f"    Downloading: {url}")
            zip_path = tempfile.mktemp(suffix=".zip")
            try:
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(str(PB_DIR))
                if SYSTEM != "Windows":
                    pb_bin.chmod(0o755)
            finally:
                Path(zip_path).unlink(missing_ok=True)

        tasks.append(("Downloading PocketBase", download_pb))

        # 6. Create config file
        def create_config():
            cfg = {
                "pocketbase_url": f"http://127.0.0.1:{config.pb_port.value()}",
                "web_port": str(config.web_port.value()),
                "printer_backend": "network",
                "printer_host": "192.168.1.100",
                "printer_port": "9100",
                "label_width_mm": "100",
                "label_height_mm": "50",
                "backup_enabled": "false",
                "backup_interval_hours": "24",
            }
            with open(target / "config.json", "w") as f:
                json.dump(cfg, f, indent=2)

        tasks.append(("Creating configuration file", create_config))

        # 7. Setup auto-start (macOS LaunchAgents)
        if SYSTEM == "Darwin" and config.autostart_cb.isChecked():
            def setup_autostart():
                launch_agents = Path.home() / "Library" / "LaunchAgents"
                launch_agents.mkdir(parents=True, exist_ok=True)

                for plist_name in ("com.nubri.pocketbase.plist", "com.nubri.biobank-web.plist"):
                    src = RESOURCE_DIR / "scripts" / plist_name
                    if not src.exists():
                        continue
                    dest = launch_agents / plist_name
                    content = src.read_text().replace("{{USER}}", os.environ.get("USER", ""))
                    dest.write_text(content)
                    subprocess.run(["launchctl", "load", "-w", str(dest)])

            tasks.append(("Setting up auto-start (macOS)", setup_autostart))

        # 8. Create desktop / start shortcut
        if config.desktop_cb.isChecked():
            def create_shortcut():
                python = _check_python()[1] or sys.executable or "python3"
                desktop = Path.home() / "Desktop"

                if SYSTEM == "Windows":
                    # Batch file
                    bat = desktop / f"{APP_NAME}.bat"
                    bat.write_text(
                        f'@echo off\r\n'
                        f'cd /d "{target}"\r\n'
                        f'"{python}" main.py\r\n'
                        f'pause\r\n'
                    )
                    # Also create a .ps1 for better UX
                    ps1 = desktop / f"{APP_NAME}.ps1"
                    ps1.write_text(
                        f'Set-Location "{target}"\r\n'
                        f'& "{python}" main.py\r\n'
                    )
                elif SYSTEM == "Darwin":
                    # .command file
                    cmd = desktop / f"{APP_NAME}.command"
                    cmd.write_text(f'cd "{target}" && "{python}" main.py\n')
                    cmd.chmod(0o755)
                else:
                    # .desktop file (Linux)
                    desktop_entry = desktop / f"{APP_NAME}.desktop"
                    desktop_entry.write_text(
                        f'[Desktop Entry]\n'
                        f'Type=Application\n'
                        f'Name={APP_NAME}\n'
                        f'Exec={python} "{target}/main.py"\n'
                        f'Path={target}\n'
                        f'Terminal=false\n'
                    )
                    desktop_entry.chmod(0o755)

            tasks.append(("Creating desktop shortcut", create_shortcut))

        return tasks

    def _on_finished(self, success, message):
        self.wizard().finish_page.set_status(message, success)
        self.wizard().button(QWizard.FinishButton).setEnabled(True)


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Complete")
        self.setSubTitle("")

        layout = QVBoxLayout(self)

        self.status_icon = QLabel()
        layout.addWidget(self.status_icon)

        self.status_text = QLabel()
        self.status_text.setWordWrap(True)
        layout.addWidget(self.status_text)

        info = QLabel(
            "<hr>"
            "<h4>Next Steps:</h4>"
            "<ol>"
            "<li>Open PocketBase Admin UI at <b>http://127.0.0.1:8090/_/</b></li>"
            "<li>Create an admin account, then add users in <b>Collections → Users</b></li>"
            f"<li>Run the app: double-click the desktop shortcut or:<br>"
            f"    <code>python3 \"{INSTALL_DIR / 'main.py'}\"</code></li>"
            "<li>Sign in with the PocketBase user credentials</li>"
            "</ol>"
            "<hr>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

    def set_status(self, message, success):
        if success:
            self.status_icon.setText("Installation Successful!")
            self.status_icon.setStyleSheet("font-size: 18px; font-weight: bold; color: #27ae60;")
        else:
            self.status_icon.setText("Installation Failed")
            self.status_icon.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c;")
        self.status_text.setText(message)


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Installer")
        self.setMinimumSize(640, 520)
        self.setWizardStyle(QWizard.ModernStyle)

        self.welcome_page = WelcomePage()
        self.config_page = ConfigPage()
        self.install_page = InstallPage()
        self.finish_page = FinishPage()

        self.addPage(self.welcome_page)
        self.addPage(self.config_page)
        self.addPage(self.install_page)
        self.addPage(self.finish_page)

        self.setStyleSheet("""
            QWizard { background-color: #fafafa; }
            QWizardPage { background-color: white; }
            QLabel { color: #333; }
        """)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(f"{APP_NAME} Installer")

    wizard = InstallerWizard()
    wizard.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
