# NUBRI Biobank Label System

Desktop application for generating biobank specimen labels with QR codes and barcodes, printing to Xprinter thermal printers, and looking up specimen details via a mobile-friendly web interface.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Build Standalone App](#build-standalone-app)
- [macOS Auto-Start (Web Server)](#macos-auto-start-web-server)
- [Google Drive Backup Setup](#google-drive-backup-setup)
- [Database](#database)
- [Label Designer](#label-designer)
- [Web Preview Interface](#web-preview-interface)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [Libraries Used](#libraries-used)

---

## Overview

NUBRI Biobank Label System is a full-featured desktop application designed for biobank and laboratory environments. It streamlines the process of:

1. **Generating** unique specimen labels with embedded QR codes and Code128 barcodes
2. **Printing** labels to Xprinter thermal printers (or any system printer)
3. **Tracking** specimens with a local SQLite or shared PostgreSQL database
4. **Searching** specimens via text search or QR code scanning (webcam or mobile camera)
5. **Customizing** the database schema (add/remove/reorder custom specimen fields)
6. **Previewing** specimen data on any device via a built-in Flask web server
7. **Backing up** the database to Google Drive automatically or manually

The app provides two parallel implementations:
- **`main.py`** — Single-file version using customtkinter (recommended for daily use and building)
- **`app/` package** — Modular version using PyQt5 (original architecture with native OS print dialog)

---

## Features

### Label Creation
| Feature | Description |
|---------|-------------|
| **Auto-generated Sample IDs** | Format: `NU` + 10-digit zero-padded number (e.g., `NU0000000001`) |
| **Dynamic Input Form** | Form fields auto-built from the current column definitions |
| **Real-time Label Preview** | Instant visual preview of the label as you type |
| **QR Code Generation** | Every specimen gets a unique QR code |
| **Code128 Barcode** | Barcode printed on every label |
| **Direct Print** | Print immediately after creating, or save to database first |

### Label Printing
| Feature | Description |
|---------|-------------|
| **Thermal Printing (ESC/POS)** | Xprinter printers via Network (TCP/IP port 9100), USB (vendor 0x0416), or Serial (RS-232) |
| **System Printing** | Native OS print dialog via PyQt5 QPrinter with proper paper sizing |
| **Print Dialog** | Preview, select number of copies, choose print mode (thermal/system), multi-copy gap control |
| **Label Designer** | Visual editor to customize label layout — position barcode, QR code, text fields, colors, borders, font size |

### Search & Scan
| Feature | Description |
|---------|-------------|
| **Text Search** | Search across QR codes and all custom fields |
| **Desktop Camera Scanning** | Scan QR codes using a webcam (OpenCV + pyzbar) |
| **Detail View** | Click any result to see full specimen details |

### Database Management
| Feature | Description |
|---------|-------------|
| **Paginated Browser** | Browse all specimens with 50-per-page pagination |
| **CSV Export** | Export the entire database to CSV |
| **CSV Import** | Import specimens from CSV (with template download) |
| **CSV Template** | Download a blank CSV template matching current schema |
| **Print from Table** | Print any specimen's label directly from the table |

### Schema Customization
| Feature | Description |
|---------|-------------|
| **Add Custom Columns** | Create new specimen fields (TEXT, NUMBER, or DATE types) |
| **Edit Columns** | Rename or change type of existing columns |
| **Delete Columns** | Remove custom columns from the schema |
| **Reorder Columns** | Drag/reorder columns in the input form |
| **Required Fields** | Mark any column as required for specimen entry |
| **Default Columns** | Sample ID, Sample Type, Patient Name, Collection Date, Storage Location, Notes |

### Web Preview (Mobile Interface)
| Feature | Description |
|---------|-------------|
| **Responsive Web UI** | Mobile-friendly interface served on port 8765 (default) |
| **Web Login/Signup** | Separate user accounts for web access |
| **QR Lookup** | Look up specimen details by QR code |
| **HTML5 Camera Scanning** | Scan QR codes using your phone's camera via the browser |
| **Authentication** | Session-based auth with Bearer token API |

### Google Drive Backup
| Feature | Description |
|---------|-------------|
| **Automatic Backup** | Scheduled backups at configurable intervals (default: 24 hours) |
| **Manual Backup** | Trigger a backup anytime from the Tools menu |
| **Backup Listing** | View all backups stored in Google Drive |
| **Restore** | Restore the database from any backup |
| **SQLite Mode** | Copies the `.db` file directly |
| **PostgreSQL Mode** | Runs `pg_dump` for a custom-format dump |

### Security & User Management
| Feature | Description |
|---------|-------------|
| **Login/Signup** | 3-step wizard: database setup → login → signup |
| **Password Hashing** | SHA-256 with salt for secure password storage |
| **Session Tokens** | Token-based auth for web API (expiring sessions) |
| **Sign Out** | Sign out from the desktop app |

### Settings
| Feature | Description |
|---------|-------------|
| **Printer Mode** | Switch between thermal (ESC/POS) and system printer |
| **Thermal Config** | Printer backend (network/USB/serial), IP address, port |
| **Label Dimensions** | Width and height in millimeters |
| **Roll Gap** | Physical gap between labels on continuous roll |
| **Multi-Copy Gap** | Spacing between copies when printing multiple labels |
| **Web Server Port** | Change the port for the Flask web server |
| **Google Drive Backup** | Enable/disable, set backup interval, trigger restore |
| **Database Switching** | Switch between SQLite and PostgreSQL at runtime |
| **Delete All Data** | Wipe all specimens from the database |
| **Label Designer** | Open the visual label layout editor |

### Auto-Generated Sample IDs
Sample IDs follow the format `NU` + 10-digit sequential number. The counter is stored in the database settings and auto-increments. This means every label gets a unique identifier without manual entry.

### Database Dual Support
- **SQLite** — Local file-based database (`biobank.db`), no server needed, perfect for single-PC use
- **PostgreSQL** — Shared database accessible from multiple PCs, ideal for lab teams

Database choice is made on first launch via the login dialog — no CLI configuration required.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.10+ | Core language |
| **GUI (single-file)** | customtkinter + tkinter | Modern dark-themed desktop UI |
| **GUI (modular)** | PyQt5 | Full native print dialog support |
| **Database** | SQLite (default) / PostgreSQL | Local or shared storage |
| **QR Generation** | qrcode[pil] | QR code on labels |
| **QR Scanning (Desktop)** | opencv-python + pyzbar | Webcam QR scanning |
| **QR Scanning (Web)** | HTML5 Camera API + JavaScript | Mobile browser QR scanning |
| **Barcode Generation** | python-barcode[images] | Code128 barcode on labels |
| **Thermal Printing** | python-escpos | ESC/POS protocol for Xprinter |
| **System Printing** | PyQt5 QPrinter | Native OS print dialog |
| **Web Server** | Flask + Waitress | Production WSGI for mobile preview |
| **Backup** | Google Drive API | Cloud database backups |
| **Serial** | pyserial | Serial printer connection |
| **Packaging** | PyInstaller | Single-file .app / .exe |
| **Image Processing** | Pillow | Label rendering |

---

## Project Structure

```
NUBRI-Biobank-system/
├── main.py                          # Single-file entry point (customtkinter, recommended)
├── app/                             # Modular PyQt5 application package
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py              # Re-exports all database modules
│   │   ├── connection.py            # DatabaseConnection (SQLite + PostgreSQL, auto-schema)
│   │   ├── models.py                # SpecimenModel, ColumnDefinition, SettingsModel
│   │   ├── auth.py                  # AuthManager (users, sessions, password hashing)
│   │   └── backup.py                # GoogleDriveBackup (auth, backup, list, restore)
│   ├── gui/
│   │   ├── __init__.py              # Re-exports MainWindow
│   │   ├── main_window.py           # MainWindow with tabs, menu bar, status bar
│   │   ├── login_dialog.py          # 3-step login/signup wizard
│   │   ├── label_form.py            # Specimen creation form with preview
│   │   ├── search_dialog.py         # Search + camera QR scanning
│   │   ├── database_view.py         # Paginated table browser + CSV import/export
│   │   ├── schema_manager.py        # Dynamic column management UI
│   │   ├── settings_widget.py       # Full settings panel
│   │   ├── print_dialog.py          # Print preview with options
│   │   ├── label_designer.py        # Visual label layout editor
│   │   └── theme.py                 # Dark Qt stylesheet
│   ├── printer/
│   │   ├── __init__.py              # Re-exports LabelRenderer, ThermalPrinter, SystemPrinter
│   │   └── label_printer.py         # Label rendering + printing logic
│   ├── qr_code/
│   │   ├── __init__.py              # Re-exports QRHandler
│   │   └── qr_handler.py            # QR generation, base64 encoding, camera decoding
│   └── web/
│       ├── __init__.py              # Re-exports WebServer
│       ├── server.py                # Flask routes and web page templates
│       └── server_headless.py       # Headless web server (auto-start without GUI)
├── scripts/
│   ├── com.nubri.biobank-web.plist  # macOS launchd plist for web server auto-start
│   └── setup_autostart.sh           # Install/uninstall launchd service
├── build_app.py                     # PyInstaller build script (from main.py)
├── build_installer.py               # GUI installer build script
├── setup_and_build.py               # All-in-one: venv + deps + PyInstaller build
├── installer.py                     # GUI installer wizard (PyQt5)
├── requirements.txt                 # Python dependencies
├── app.ico                          # Application icon
├── biobank.db                       # SQLite database (auto-created)
├── db_config.json                   # PostgreSQL URL config (auto-created)
└── credentials/                     # Google Drive client_secret.json (user-provided)
```

---

## Setup & Installation

### Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Optional:** PostgreSQL server (for multi-PC shared database)
- **Optional:** Google Cloud project (for Google Drive backup)
- **Optional:** Xprinter thermal printer (for label printing)

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### First Launch

1. **Database Setup Screen** — Choose database type:
   - **SQLite** (default): Local file, no configuration needed
   - **PostgreSQL**: Enter your connection URL (`postgresql://user:password@host:5432/dbname`)
2. **Login Screen** — Enter your email and password (if you already have an account)
3. **Signup Screen** — Create a new account (name, email, password)
4. The main application window opens with 5 tabs

### Multi-PC Setup (PostgreSQL)

```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Run the app and enter your PostgreSQL URL on the first screen
python main.py
```

All connected PCs share the same specimen database. Printer settings, label templates, and column definitions are also shared.

---

## Build Standalone App

### Method 1 — Build Script (Recommended)

```bash
python build_app.py --name "BioBank DB" --icon app.ico
```

### Method 2 — Direct PyInstaller

```bash
pyinstaller "BioBank DB.spec"
```

### Method 3 — All-in-One

```bash
python setup_and_build.py
```

This creates a virtual environment, installs dependencies, and builds a standalone executable.

### Output

- **macOS**: `dist/BioBank DB.app` or `dist/BioBank DB/`
- **Windows**: `dist/BioBank DB.exe` or `dist/BioBank DB/`

### GUI Installer

```bash
python build_installer.py
```

Produces a portable installer wizard that guides users through installation.

---

## macOS Auto-Start (Web Server)

To keep the web preview server running automatically at login:

```bash
chmod +x scripts/setup_autostart.sh
./scripts/setup_autostart.sh
```

This installs a `launchd` plist that starts the Flask web server when you log in.

To remove the auto-start:

```bash
./scripts/setup_autostart.sh --uninstall
```

---

## Google Drive Backup Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the JSON file
6. Create a `credentials/` directory in the project root
7. Place the JSON file as `credentials/client_secret.json`
8. Open the app → **Settings** → **Google Drive Backup** → Enable and configure

File structure:

```
credentials/
└── client_secret.json
```

The app will authenticate on first backup and store the token locally. Backups are stored in a `BiobankBackups` folder in your Google Drive.

---

## Database

### SQLite (Default)

- File: `biobank.db` (auto-created in project root)
- No server or configuration needed
- Ideal for single-PC use

### PostgreSQL

- Connection URL stored in `db_config.json` (auto-created)
- Shared database accessible from multiple PCs
- Requires PostgreSQL server and `psycopg2-binary`

### Schema Tables (auto-created)

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `column_definitions` | Dynamic specimen schema | id, column_name, column_type, display_order, is_required, is_active |
| `specimens` | All specimen records | id, qr_code (unique), custom_fields (JSON), timestamps |
| `settings` | Application settings | key (PK), value |
| `users` | User accounts | id, email, password_hash, salt, name |
| `sessions` | Web session tokens | id, user_id (FK), token, timestamps |

### Default Columns

1. Sample ID (auto-generated, required)
2. Sample Type (required)
3. Patient Name
4. Collection Date (DATE type)
5. Storage Location
6. Notes

### Default Settings

| Setting | Default Value |
|---------|---------------|
| Printer Backend | Network |
| Printer Host | 192.168.1.100 |
| Printer Port | 9100 |
| Label Width | 35 mm |
| Label Height | 15 mm |
| Roll Gap | 3 mm |
| Multi-Copy Gap | 1 mm |
| Web Server Port | 8765 |
| Backup Enabled | false |
| Backup Interval | 24 hours |
| Next Sample ID | 1 |

---

## Label Designer

The Label Designer is a visual editor that lets you customize the layout of printed labels.

### Customizable Elements

- **Code128 Barcode** — Position, size
- **QR Code** — Position, size
- **Sample ID Text** — Position, font size
- **Custom Field Data** — Select which fields appear on the label
- **Colors** — Foreground and background colors
- **Borders** — Toggle border around the label
- **Layout** — Drag elements to position them

Access via: **Settings → Label Designer** button

### Templates

The default template includes the QR code on the left and barcode + text on the right. Custom templates are stored in the database settings.

---

## Web Preview Interface

The built-in Flask web server provides a mobile-friendly interface for looking up specimens.

### Access

- Default URL: `http://localhost:8765`
- From other devices: `http://<your-ip>:8765`
- Visible in the app's status bar

### Pages

| Route | Description |
|-------|-------------|
| `/` | Specimen lookup home page (requires login) |
| `/login` | Web login page |
| `/api/web-login` | POST — Authenticate with email/password |
| `/api/web-signup` | POST — Create a new web account |
| `/api/logout` | POST — Log out |
| `/api/lookup` | GET — Lookup specimen by QR code (Bearer token auth) |
| `/api/decode-qr` | POST — Decode QR from base64 image captured by phone camera |
| `/api/me` | GET — Return current user info |

### Web Features

- **QR Input**: Type or paste a QR code value to look up a specimen
- **HTML5 Camera Scan**: Tap the camera button to open your phone's camera and scan a QR code
- **Specimen Details**: View all custom fields for the looked-up specimen
- **Responsive Design**: Works on phones, tablets, and desktops

---

## Usage Guide

### Creating a Label

1. Go to the **Create Label** tab
2. The **Sample ID** is auto-generated (NU + 10-digit number)
3. Fill in the specimen fields (Sample Type, Patient Name, etc.)
4. Preview updates in real-time on the right
5. Click **Print** to print directly, or **Save** to store in the database

### Printing Labels

1. From the **Create Label** tab — print immediately after creation
2. From the **Database** tab — select a specimen and click **Print Selected**
3. From the **Search** tab — view details and click **Print**

The print dialog lets you:
- Preview the label
- Set the number of copies
- Choose between **Thermal** (ESC/POS) or **System** (OS print dialog) mode

### Scanning QR Codes

**Desktop:**
1. Go to the **Search / Scan** tab
2. Click **Start Camera**
3. Hold a QR code up to your webcam
4. The decoded specimen appears in the results

**Mobile (via web interface):**
1. Open `http://<your-ip>:8765` on your phone
2. Log in
3. Tap the camera icon to use your phone's camera
4. Point at a label's QR code

### Managing Columns

1. Go to the **Manage Columns** tab
2. See the current list of specimen fields
3. **Add**: Enter a name and select type (TEXT, NUMBER, DATE)
4. **Edit**: Change name or type of existing fields
5. **Delete**: Remove unwanted fields
6. **Reorder**: Use the up/down arrows to change field order
7. **Toggle Required**: Mark fields as mandatory

### Managing the Database

1. Go to the **Database** tab
2. Browse specimens (50 per page, with pagination controls)
3. **Export CSV**: Download all data as a CSV file
4. **Import CSV**: Upload a CSV file to bulk-add specimens
5. **Download Template**: Get a blank CSV with the current schema
6. **Print**: Print any specimen's label from the table

### Settings

1. Go to the **Settings** tab
2. Configure printer, label dimensions, gap settings
3. Set the web server port
4. Configure Google Drive backup
5. Switch between SQLite and PostgreSQL
6. Open the Label Designer
7. Delete all data (with confirmation)

---

## Troubleshooting

### "no module named customtkinter"

```bash
pip install customtkinter
```

### "no module named psycopg2"

```bash
pip install psycopg2-binary
```

### Camera QR scanning not working

```bash
pip install opencv-python pyzbar
```

**macOS**: Check System Settings → Privacy & Security → Camera — ensure terminal/IDE has camera access.

### Xprinter not printing

1. Verify the printer IP in **Settings**
2. Test with netcat:
   ```bash
   echo "Hello" | nc <printer-ip> 9100
   ```
3. Check network connectivity between PC and printer
4. Ensure the printer is powered on and online

### PostgreSQL connection fails

1. Verify the server is running: `pg_isready`
2. Ensure port 5432 is open on the server firewall
3. Check the connection URL in `db_config.json`
4. Verify user credentials have database access

### Web server not accessible from phone

1. Check the app's status bar for the web URL
2. Ensure both devices are on the same network
3. Check firewall settings (macOS: System Settings → Network → Firewall)
4. Try `http://localhost:8765` on the PC first

### PyInstaller build fails

```bash
# Use the recommended build script
python build_app.py --name "BioBank DB" --icon app.ico
```

If using PyInstaller directly, ensure you have the correct `.spec` file and all dependencies installed.

### Google Drive backup fails

1. Verify `credentials/client_secret.json` exists and is valid
2. Check internet connectivity
3. Ensure the Google Drive API is enabled in your Google Cloud project
4. Re-authenticate by deleting the stored token (if any)

---

## Libraries Used

- **[customtkinter](https://github.com/TomSchimansky/CustomTkinter)** — Modern dark-themed GUI framework built on tkinter
- **[PyQt5](https://www.riverbankcomputing.com/software/pyqt/)** — Qt5 bindings for system print dialog (modular version)
- **[Flask](https://flask.palletsprojects.com/)** — Lightweight web framework for the mobile preview server
- **[Waitress](https://docs.pylonsproject.org/projects/waitress/)** — Production-grade WSGI server
- **[qrcode](https://github.com/lincolnloop/python-qrcode)** — QR code generation
- **[python-barcode](https://github.com/WhyNotHugo/python-barcode)** — Code128 barcode generation
- **[OpenCV](https://opencv.org/)** — Webcam access for desktop QR scanning
- **[pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar/)** — QR/barcode decoding from images
- **[python-escpos](https://github.com/python-escpos/python-escpos)** — ESC/POS thermal printer protocol
- **[pyserial](https://github.com/pyserial/pyserial)** — Serial port communication
- **[Pillow](https://python-pillow.org/)** — Image rendering and manipulation
- **[psycopg2-binary](https://www.psycopg.org/)** — PostgreSQL adapter
- **[google-api-python-client](https://github.com/googleapis/google-api-python-client)** — Google Drive API
- **[PyInstaller](https://pyinstaller.org/)** — Cross-platform application bundling

---

## License

Internal use — NUBRI Biobank
