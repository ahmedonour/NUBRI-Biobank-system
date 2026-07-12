#!/usr/bin/env python3
"""
Build NUBRI Biobank into a standalone executable using PyInstaller.
Now builds from the single-file main.py with customtkinter.

Usage:
    python build_app.py                    # Build executable
    python build_app.py --name "BioBank DB" --icon app.ico
"""

import os, sys, shutil, subprocess, platform

APP_ENTRY = "main.py"
DEFAULT_NAME = "BioBank DB"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def build(name=None, icon_path=None):
    name = name or DEFAULT_NAME
    dist_dir = os.path.join(PROJECT_DIR, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--onedir",
        "--noconfirm",
        "--clean",
        "--distpath", dist_dir,
        "--workpath", os.path.join(dist_dir, "build"),
        "--specpath", dist_dir,
    ]

    if platform.system() == "Darwin":
        cmd.append("--windowed")
    elif platform.system() == "Windows":
        cmd.append("--noconsole")

    if icon_path and os.path.exists(os.path.join(PROJECT_DIR, icon_path)):
        abs_icon = os.path.join(PROJECT_DIR, icon_path)
        cmd.extend(["--icon", abs_icon])

    # Hidden imports for dynamically loaded modules
    hidden = [
        "customtkinter",
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageTk",
        "qrcode",
        "cv2", "pyzbar.pyzbar", "barcode",
        "numpy",
        "psycopg2", "psycopg2.extras",
        "escpos.printer",
        "requests",
        "flask",
        "waitress",
        "google.oauth2.credentials",
        "google_auth_oauthlib.flow",
        "google.auth.transport.requests",
        "googleapiclient.discovery",
        "googleapiclient.http",
        "PyQt5", "PyQt5.QtWidgets", "PyQt5.QtPrintSupport", "PyQt5.QtGui", "PyQt5.QtCore",
    ]
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    # Collect all data/binaries for packages with native extensions
    collect_all = ["cv2", "barcode", "pyzbar", "PIL", "numpy"]
    for mod in collect_all:
        cmd.extend(["--collect-all", mod])

    cmd.append(APP_ENTRY)

    print("=" * 60)
    print(f"  Building: {name}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Icon:     {icon_path or 'default'}")
    print("=" * 60)
    print()
    print("Running PyInstaller...")
    print()

    subprocess.check_call(cmd, cwd=PROJECT_DIR)

    ext = ".exe" if platform.system() == "Windows" else ""
    out = os.path.join(dist_dir, f"{name}{ext}")
    if os.path.exists(out):
        size = os.path.getsize(out) / (1024 * 1024)
        print(f"\nSuccess! {size:.1f} MB — {out}")
    else:
        print(f"\nBuild failed: {out} not found.")
        sys.exit(1)


if __name__ == "__main__":
    icon = None
    name = DEFAULT_NAME
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--name" and i + 2 < len(sys.argv):
            name = sys.argv[i + 2]
        elif arg == "--icon" and i + 2 < len(sys.argv):
            icon = sys.argv[i + 2]
    build(name=name, icon_path=icon)
