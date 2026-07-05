# NUBRI Biobank Label System

A desktop application for generating biobank specimen labels with QR codes,
printing to Xprinter thermal printers, and looking up specimen details
via a mobile-friendly web interface.

---

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [GUI Installer](#gui-installer)
- [Build .app Bundle (macOS)](#build-app-bundle-macos)
- [Build Standalone Installer](#build-standalone-installer)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Auto-Start on Boot](#auto-start-on-boot)
- [Project Structure](#project-structure)
- [Libraries Used](#libraries-used)

---

## Features

| Feature | Description |
|---------|-------------|
| **QR Code Labels** | Generate unique QR codes for every specimen |
| **Custom Fields** | Add, edit, delete, and reorder specimen columns from the UI |
| **Xprinter Printing** | ESC/POS thermal label printing via network, USB, or serial |
| **Desktop QR Scanning** | Scan QR codes using a webcam (OpenCV + pyzbar) |
| **Mobile Web Preview** | Responsive web interface with HTML5 camera QR scanning |
| **SQLite Auth** | Built-in sign in / sign up — no external server needed |
| **Password Hashing** | Passwords safely hashed with SHA-256 + salt |
| **Fast Search** | SQLite with WAL mode, indexed columns, JSON1 queries |
| **Google Drive Backup** | Automatic or manual database backup to Google Drive |
| **Auto-Start** | Web server auto-starts on boot (macOS LaunchAgents) |
| **GUI Installer** | Step-by-step setup wizard for zero-config installation |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Desktop App (PyQt5)                    │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐ │
│  │ Create   │  │ Search/  │  │Manage  │  │ Settings  │ │
│  │ Label    │  │ Scan     │  │Columns │  │           │ │
│  └────┬─────┘  └────┬─────┘  └────┬───┘  └─────┬─────┘ │
│       │              │              │            │       │
├───────┴──────────────┴──────────────┴────────────┴──────┤
│                    Core Modules                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐ │
│  │ Database │  │   QR     │  │Printer │  │  Auth    │ │
│  │ (SQLite) │  │ (qrcode) │  │(ESC/POS)│  │(SQLite) │ │
│  │          │  │ (pyzbar) │  │        │  │(hashed) │ │
│  └────┬─────┘  └──────────┘  └────────┘  └────┬─────┘ │
│       │                                        │       │
└───────┴────────────────────────────────────────┴───────┘
                │                              │
        ┌───────▼──────┐              ┌────────▼───────┐
        │   SQLite DB  │              │   Flask Web    │
        │  biobank.db  │              │   Server :5000 │
        │  (data +     │              │  (mobile QR    │
        │   users +    │              │   lookup)      │
        │   sessions)  │              └────────────────┘
        └──────────────┘
```

---

## Requirements

### System Requirements

- **Python** 3.8 or higher
- **OS**: macOS, Windows, or Linux
- **RAM**: 512 MB minimum, 2 GB recommended
- **Disk**: 200 MB for app + dependencies
- **Camera** (optional): For desktop QR scanning

### Python Dependencies

All dependencies are listed in `requirements.txt`:

| Library | Version | Purpose |
|---------|---------|---------|
| `PyQt5` | >=5.15.0 | Desktop GUI framework |
| `qrcode[pil]` | >=7.3.0 | QR code generation |
| `opencv-python` | >=4.5.0 | Camera QR scanning (desktop) |
| `pyzbar` | >=0.1.9 | QR code decoding |
| `python-escpos` | >=3.0 | Xprinter thermal printer ESC/POS protocol |
| `Pillow` | >=9.0.0 | Image handling for labels |
| `Flask` | >=2.0.0 | Web preview server |
| `requests` | >=2.25.0 | HTTP client |
| `google-api-python-client` | >=2.0.0 | Google Drive backup |
| `google-auth-httplib2` | >=0.1.0 | Google Drive auth |
| `google-auth-oauthlib` | >=0.4.0 | Google Drive OAuth |

### External Services (optional)

| Service | Purpose | How to Get It |
|---------|---------|---------------|
| **Google Drive API** | Database backup | Google Cloud Console → enable Drive API → download `client_secret.json` |

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run the app
python main.py

# 3. Create your account
#    Click "Create an account" on the login screen
```

That's it. No external servers needed. Everything runs locally.

---

## Detailed Installation

### 1. Install Python

**macOS** (Homebrew):
```bash
brew install python@3.11
```

**Windows**: Download from [python.org](https://python.org) — check "Add Python to PATH".

**Linux**:
```bash
sudo apt install python3 python3-pip python3-venv  # Debian/Ubuntu
sudo dnf install python3 python3-pip                # Fedora
```

### 2. Clone or Copy the Project

```bash
cd /path/to/NUBRI-Biobank-system
```

### 3. (Recommended) Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Install Optional Dependencies for Camera QR Scanning

Desktop camera scanning requires additional system libraries:

**macOS**:
```bash
brew install zbar
```

**Linux**:
```bash
sudo apt install libzbar0       # Debian/Ubuntu
sudo dnf install zbar           # Fedora
```

**Windows**: zbar is bundled with `pyzbar` — no extra steps needed.

### 6. Run the Application

```bash
python main.py
```

On first run:
1. The app creates `biobank.db` (SQLite database) automatically
2. A login dialog appears — click **Create an account** to register
3. Sign in and start creating specimen labels

---

## GUI Installer

The installer provides a step-by-step wizard for a zero-config setup:

```bash
pip install PyQt5        # (if not already installed)
python installer.py
```

The installer walks through:

1. **Welcome** — overview with system check (Python, pip)
2. **Configuration** — set web port, toggle desktop shortcut, optional features
3. **Installation** — live progress log showing:
   - Creating `~/Biobank/` directory structure
   - Installing Python dependencies
   - Copying application files
   - Creating configuration file
   - Creating desktop shortcut
4. **Finish** — success/failure status with next steps

---

## Build .app Bundle (macOS)

Create a standalone macOS `.app` that can be run without Python installed:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the .app
python build_app.py

# Build .app + create DMG for distribution
python build_app.py --dmg
```

The output appears in the `dist/` directory:
- `dist/NUBRI Biobank.app` — drag to Applications folder
- `dist/NUBRI Biobank.dmg` — disk image for sharing

---

## Build Standalone Installer

Build the GUI installer into a single executable that can run on any machine
without Python installed:

```bash
# Build for current platform
python build_installer.py

# Rebuild from scratch
python build_installer.py --clean

# Also create a ZIP
python build_installer.py --zip
```

Produces:
- **Windows**: `dist/NUBRI_Biobank_Installer.exe` (single file)
- **macOS**: `dist/NUBRI_Biobank_Installer.app`
- **Linux**: `dist/NUBRI_Biobank_Installer` (binary)

The installer embeds all application files (app/, main.py, requirements.txt,
scripts/) and PyQt5. The target machine only needs Python/pip to install
dependencies (the installer checks this).

---

## Configuration

### Settings Tab (within the app)

| Section | Setting | Description |
|---------|---------|-------------|
| **Printer** | Connection Type | `network` (recommended), `usb`, or `serial` |
| **Printer** | Host / IP | Printer IP address for network mode |
| **Printer** | Port | Network port (default: `9100` — ESC/POS standard) |
| **Printer** | Label Width/Height | Label dimensions in mm (default: 100 x 50) |
| **Web Server** | Port | Web preview port (default: `5000`) |
| **Backup** | Enable | Toggle automatic Google Drive backups |
| **Backup** | Interval | Hours between backups |
| **Backup** | Credentials | Path to `client_secret.json` from Google Cloud Console |

### Database

The SQLite database is created automatically at `./biobank.db` (or the path
specified with `--db`). The schema auto-migrates on first run with:
- `column_definitions` — dynamic field definitions
- `specimens` — specimen data with JSON custom fields
- `users` — user accounts (email + hashed password + salt)
- `sessions` — web session tokens
- `settings` — application configuration

---

## Usage Guide

### 1. Create a Label

1. Go to the **Create Label** tab
2. Fill in the specimen fields (dynamically generated from your column definitions)
3. Click **Generate Label & Save**
4. A QR code is generated and the specimen is saved to the database
5. The label can be printed to the Xprinter

### 2. Manage Columns

1. Go to the **Manage Columns** tab
2. Click **+ Add Column** to create new fields
3. Use **Edit** to rename or change field type
4. Use **Delete** to remove columns (data is preserved but hidden)
5. Use **Move Up / Move Down** to reorder fields on the entry form

### 3. Search / Scan

1. Go to the **Search / Scan** tab
2. Type a QR code or value into the search box
3. Click **Search** — results appear in the table
4. Double-click a row to see full specimen details
5. Click **Scan QR from Camera** to scan using your webcam

### 4. Print Labels

The app connects to Xprinter thermal printers via ESC/POS protocol:

- **Network (recommended)**: Connect the printer to your network, enter its IP
  and port (default: 9100) in Settings
- **USB**: Connect via USB, select `usb` backend
- **Serial**: Connect via serial port, select `serial` backend

The printer renders labels with:
- QR code (scannable)
- Field name-value pairs (up to 6 fields)
- Configurable label size

### 5. Web Preview (Mobile / Tablet)

1. The web server starts automatically on app launch (default port: 5000)
2. On your phone/tablet, open `http://<your-computer-ip>:5000`
3. Sign in or create an account from the web login page
4. Use the HTML5 camera to scan QR codes and view details in real time

To find your computer's IP:
```bash
ipconfig getifaddr en0   # macOS (Wi-Fi)
ipconfig                  # Windows
hostname -I               # Linux
```

### 6. Google Drive Backup

1. Go to **Google Cloud Console** → create a project → enable **Google Drive API**
2. Create OAuth 2.0 credentials → download as `client_secret.json`
3. Place the file in the `credentials/` folder or specify the path in Settings
4. Click **Backup Now** for an immediate backup, or enable automatic backups
5. Backups are stored in a `BiobankBackups` folder in your Google Drive

### 7. Sign In / Sign Out

- **Desktop**: App starts with a login dialog. Click **Create an account** to register,
  or sign in with your email and password. Use **File → Sign Out** to switch users.
- **Web**: Click **Sign Out** in the top-right corner, or use the login/signup
  form on the `/login` page.
- Passwords are hashed with SHA-256 + a random salt. They are never stored
  in plain text.

---

## Auto-Start on Boot

### Method 1: Web server with macOS LaunchAgents

Install the web preview server to start on login:

```bash
bash scripts/setup_autostart.sh
```

This installs `com.nubri.biobank-web.plist` in `~/Library/LaunchAgents/`,
which keeps the Flask web server running in the background.

```bash
# Check status
launchctl list | grep nubri

# Remove auto-start
bash scripts/setup_autostart.sh --uninstall
```

---

## Project Structure

```
NUBRI-Biobank-system/
├── main.py                     # Entry point — starts desktop app
├── installer.py                # PyQt5 GUI setup wizard
├── build_app.py                # PyInstaller .app bundle builder
├── build_installer.py          # PyInstaller standalone installer builder
├── requirements.txt            # Python dependencies
│
├── app/
│   ├── database/
│   │   ├── connection.py       # SQLite connection manager (WAL mode, auto-migrate)
│   │   ├── models.py           # Specimen CRUD, dynamic columns, settings
│   │   ├── auth.py             # User auth (signup/login/sessions) with hashed passwords
│   │   └── backup.py           # Google Drive backup/restore
│   │
│   ├── gui/
│   │   ├── main_window.py      # Tabbed main window + menu + sign out
│   │   ├── login_dialog.py     # Sign in / Sign up dialog (SQLite auth)
│   │   ├── label_form.py       # Dynamic specimen entry form
│   │   ├── search_dialog.py    # Search + camera QR scanning
│   │   ├── schema_manager.py   # Add/edit/delete/reorder columns
│   │   └── settings_widget.py  # Printer, web, backup config
│   │
│   ├── printer/
│   │   └── label_printer.py    # Xprinter ESC/POS thermal printing
│   │
│   ├── qr_code/
│   │   └── qr_handler.py       # QR generation + camera decode
│   │
│   └── web/
│       ├── server.py           # Flask web server with auth + QR lookup
│       └── server_headless.py  # Standalone web server runner (for launchd)
│
└── scripts/
    ├── com.nubri.biobank-web.plist    # macOS launchd plist for web server
    └── setup_autostart.sh             # Install/remove launchd services
```

---

## Libraries Used

### GUI & Desktop
- **[PyQt5](https://riverbankcomputing.com/software/pyqt/)** — Cross-platform desktop GUI framework. Provides windows, dialogs, tabs, tables, and all UI components. Chosen over tkinter for its professional look, advanced widgets, and styling capabilities.

### Database & Auth
- **SQLite3** (built-in) — Embedded relational database. Zero configuration, no server process needed. WAL mode enables concurrent reads during writes for fast performance. JSON1 extension allows querying dynamic custom fields.
- **hashlib** (built-in) — SHA-256 password hashing with random salt. No external auth server required — user accounts are stored securely in the local database.

### QR Codes
- **[qrcode](https://github.com/lincolnloop/python-qrcode)** — QR code generation. Creates high-quality QR codes with configurable error correction and box size.
- **[pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar)** — QR code decoding from images and video frames. Wraps the C zbar library.
- **[opencv-python](https://github.com/opencv/opencv-python)** — Camera access for real-time QR scanning from the desktop webcam.

### Printing
- **[python-escpos](https://github.com/python-escpos/python-escpos)** — ESC/POS protocol implementation for thermal printers. Supports network (TCP/IP), USB, and serial connections. Works with any ESC/POS-compatible printer including all Xprinter models.
- **[Pillow](https://python-pillow.org/)** — Image creation and manipulation for rendering labels with QR codes and text fields before printing.

### Web Server
- **[Flask](https://flask.palletsprojects.com/)** — Lightweight Python web framework for the mobile preview server. Serves the responsive HTML interface and REST API for specimen lookup.

### Cloud Backup
- **[google-api-python-client](https://github.com/googleapis/google-api-python-client)** — Google Drive API client for uploading database backups.
- **[google-auth-oauthlib](https://github.com/GoogleCloudPlatform/google-auth-library-python-oauthlib)** — OAuth 2.0 authentication flow for Google services.

### Network & HTTP
- **[requests](https://requests.readthedocs.io/)** — HTTP client for web server operations.

---

## Troubleshooting

### Camera not working for QR scanning
```bash
# macOS: grant camera permission in System Settings → Privacy → Camera
# Linux: ensure you're in the 'video' group
sudo usermod -a -G video $USER
# Re-login after running the above
```

### Xprinter not printing
- Verify the printer is on the same network
- Check the IP address in Settings
- Test with raw ESC/POS: `echo "Hello" | nc <printer-ip> 9100`
- For USB on macOS: System Settings → Printers & Scanners → Add Printer

### Web preview not accessible from phone
- Ensure both devices are on the same network
- Check firewall: `sudo firewall-cmd --add-port=5000/tcp` (Linux)
- Verify the IP address — use the local network IP, not 127.0.0.1

### Can't sign in
- First time? Click **Create an account** to register
- Passwords are case-sensitive and require at least 4 characters
- If you forget your password, delete the `users` table from the database
  (or ask an admin to recreate the account)

---
