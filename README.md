# NUBRI Biobank Label System

Desktop application for generating biobank specimen labels with QR codes,
printing to Xprinter thermal printers, and looking up specimen details
via a mobile-friendly web interface.

---

## Features

| Feature | Description |
|---------|-------------|
| **QR Code Labels** | Generate unique QR codes for every specimen |
| **Custom Fields** | Add, edit, delete, and reorder specimen columns from the UI |
| **Xprinter Printing** | ESC/POS thermal label printing via network, USB, or serial |
| **Desktop QR Scanning** | Scan QR codes using a webcam (OpenCV + pyzbar) |
| **Mobile Web Preview** | Responsive web interface with HTML5 camera QR scanning (Flask + Waitress) |
| **Dual Database** | SQLite (local, single-PC) or PostgreSQL (shared, multi-PC) |
| **On-Screen DB Setup** | Enter PostgreSQL URL on first-launch login screen — no CLI needed |
| **Google Drive Backup** | Automatic or manual database backup (SQLite file or pg_dump) |
| **Single-File Build** | Everything in one `main.py` — easy to bundle with PyInstaller |

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

- **Single PC**: Use SQLite — no external servers needed
- **Multi-PC**: Use PostgreSQL — enter the connection URL on first launch

---

## Build Standalone App

```bash
# macOS
python build_app.py --name "BioBank DB" --icon app.ico

# Windows
python build_app.py --name "BioBank DB" --icon app.ico
```

Output in `dist/`:
- **macOS**: `dist/BioBank DB.app`
- **Windows**: `dist/BioBank DB.exe`

No hidden import configuration needed — the single-file structure with
customtkinter avoids all PyInstaller namespace package issues.

---

## Tech Stack

| Layer | Library | Notes |
|-------|---------|-------|
| **GUI** | customtkinter | Modern dark theme, built on tkinter (stdlib) |
| **Database** | SQLite / psycopg2 | Dual support, auto-schema creation |
| **QR** | qrcode / pyzbar / OpenCV | Generate + scan (camera + web) |
| **Printing** | python-escpos | Xprinter ESC/POS thermal printers |
| **Web Server** | Flask + Waitress | Production WSGI for mobile preview |
| **Backup** | google-api-python-client | Google Drive backup |
| **Bundling** | PyInstaller | Single-file .app / .exe |

---

## Project Structure

```
main.py                     # Everything — database, GUI, printer, QR, web server
build_app.py                # PyInstaller build script
requirements.txt            # Python dependencies
app.ico                     # Application icon
credentials/                # Google Drive client_secret.json (user-provided)
biobank.db                  # SQLite database (auto-created)
```

---

## Libraries Used

- **[customtkinter](https://github.com/TomSchimansky/CustomTkinter)** — Modern dark-themed GUI framework built on tkinter. Zero namespace-package issues with PyInstaller.
- **[Flask](https://flask.palletsprojects.com/)** + **[Waitress](https://docs.pylonsproject.org/projects/waitress/)** — Production-grade WSGI web server for the mobile preview.
- **[qrcode](https://github.com/lincolnloop/python-qrcode)** — QR code generation.
- **[python-escpos](https://github.com/python-escpos/python-escpos)** — ESC/POS thermal printer protocol.
- **[Pillow](https://python-pillow.org/)** — Image rendering for labels.
- **[psycopg2-binary](https://www.psycopg.org/)** — PostgreSQL adapter (optional).
- **[google-api-python-client](https://github.com/googleapis/google-api-python-client)** — Google Drive backup.

---

## Configuration

Settings are managed through the **Settings** tab in the app: printer mode,
label dimensions, web port, Google Drive backup, and database connection.

The web server runs on port 5000 by default using Waitress (production WSGI).
Open `http://<your-ip>:5000` on your phone to scan QR codes and view specimens.

---

## Troubleshooting

### "no module named customtkinter"
```bash
pip install customtkinter
```

### Camera QR scanning not working
```bash
pip install opencv-python pyzbar
# macOS: System Settings → Privacy → Camera
```

### Xprinter not printing
- Check the printer IP in **Settings**
- Test: `echo "Hello" | nc <printer-ip> 9100`

### PostgreSQL connection fails
- Verify the server is running: `pg_isready`
- Ensure port 5432 is open on the server firewall
