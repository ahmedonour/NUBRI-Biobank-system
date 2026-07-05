#!/usr/bin/env python3
"""
Build NUBRI Biobank into a standalone macOS .app bundle using PyInstaller.

Usage:
    python build_app.py          # Build the .app
    python build_app.py --dmg    # Build .app + create DMG
"""

import os
import sys
import shutil
import subprocess
import platform


APP_NAME = "NUBRI Biobank"
APP_ENTRY = "main.py"
ICON_FILE = None  # Optional: path to .icns file


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def build_app():
    if not check_pyinstaller():
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
    os.makedirs(dist_dir, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",                   # GUI app, no terminal
        "--onefile",                    # Single executable inside .app
        "--add-data", f"app{os.pathsep}app",
        "--distpath", dist_dir,
        "--workpath", os.path.join(dist_dir, "build"),
        "--specpath", dist_dir,
        "--clean",
        "--noconfirm",
    ]

    if ICON_FILE and os.path.exists(ICON_FILE):
        cmd.extend(["--icon", ICON_FILE])

    # Hidden imports for PyInstaller
    for mod in ["PIL", "PIL._tkinter_finder", "qrcode", "escpos", "flask", "requests",
                 "googleapiclient", "pyzbar", "cv2"]:
        cmd.extend(["--hidden-import", mod])

    cmd.append(APP_ENTRY)

    print("Building .app bundle...")
    print(f"  Command: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    app_path = os.path.join(dist_dir, f"{APP_NAME}.app")
    if os.path.exists(app_path):
        print(f"\nSuccess! App bundle created at:\n  {app_path}")
        return app_path
    else:
        print("\nBuild failed: .app not found.")
        return None


def create_dmg(app_path):
    dmg_path = app_path.replace(".app", ".dmg")
    dmg_dir = os.path.dirname(app_path)
    app_name = os.path.basename(app_path)

    print(f"Creating DMG: {dmg_path}")

    # Symlink /Applications inside DMG
    link_target = "/Applications"
    link_name = "Applications"

    script = f"""
    tell application "Finder"
        tell disk "{APP_NAME}"
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set bounds of container window to {{400, 100, 900, 400}}
            set icon size of icon view options of container window to 80
            set arrangement of icon view options of container window to not arranged
            set position of item "{app_name}" of container window to {{100, 100}}
            set position of item "{link_name}" of container window to {{350, 100}}
            close
        end tell
    end tell
    """

    subprocess.check_call([
        "hdiutil", "create", "-volname", APP_NAME, "-srcfolder", dmg_dir,
        "-ov", "-format", "UDZO", dmg_path
    ])

    print(f"DMG created: {dmg_path}")
    return dmg_path


if __name__ == "__main__":
    app_path = build_app()
    if app_path and "--dmg" in sys.argv and platform.system() == "Darwin":
        create_dmg(app_path)
