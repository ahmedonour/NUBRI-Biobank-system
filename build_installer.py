#!/usr/bin/env python3
"""
Build the NUBRI Biobank Installer into a standalone executable.

Produces:
  Windows:  dist/NUBRI_Biobank_Installer.exe   (single file)
  macOS:    dist/NUBRI_Biobank_Installer.app   (or .app bundle)
  Linux:    dist/NUBRI_Biobank_Installer       (single binary)

The installer executable embeds everything needed:
  - app/              (full application source)
  - main.py           (app entry point)
  - requirements.txt  (Python dependencies)
  - scripts/          (launchd plists, shell scripts)
  - PyQt5 + other deps (via PyInstaller)

Usage:
  python build_installer.py              # build for current platform
  python build_installer.py --clean      # rebuild from scratch
  python build_installer.py --name "My Installer"  # custom name
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NAME = "NUBRI_Biobank_Installer"
ENTRY_SCRIPT = "installer.py"


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def find_icon():
    """Look for an icon file in common locations."""
    for name in ("icon.ico", "icon.icns", "icon.png"):
        for base in (PROJECT_DIR, os.path.join(PROJECT_DIR, "assets")):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
    return None


def collect_data_dirs():
    """
    Return a list of (source_path, dest_within_bundle) tuples for
    every directory/file that must be embedded inside the installer.
    """
    items = []

    # Top-level items
    for entry in ["app", "scripts", "main.py", "requirements.txt"]:
        src = os.path.join(PROJECT_DIR, entry)
        if os.path.exists(src):
            items.append((src, entry))

    # Recursively add everything inside app/ (PyInstaller only adds
    # directories as empty unless we list their contents explicitly on
    # some platforms — doing the robust thing):
    app_src = os.path.join(PROJECT_DIR, "app")
    if os.path.isdir(app_src):
        for root, dirs, files in os.walk(app_src):
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, PROJECT_DIR)
                items.append((fp, rel))

    # Same for scripts/
    scripts_src = os.path.join(PROJECT_DIR, "scripts")
    if os.path.isdir(scripts_src):
        for root, dirs, files in os.walk(scripts_src):
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, PROJECT_DIR)
                items.append((fp, rel))

    return items


def build_installer(name=None, clean=False):
    if not check_pyinstaller():
        print("Installing PyInstaller...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"]
        )
        print()

    name = name or DEFAULT_NAME
    dist_dir = os.path.join(PROJECT_DIR, "dist")
    work_dir = os.path.join(dist_dir, "build")
    spec_dir = dist_dir

    if clean and os.path.exists(dist_dir):
        shutil.rmtree(dist_dir, ignore_errors=True)
    os.makedirs(dist_dir, exist_ok=True)

    # ── Build command ─────────────────────────────────────────────────
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--onefile",                       # single executable output
        "--noconfirm",
        "--clean",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--specpath", spec_dir,
    ]

    # Windowed vs console
    if platform.system() == "Darwin":
        cmd.append("--windowed")           # .app without terminal
    elif platform.system() == "Windows":
        cmd.append("--noconsole")          # .exe without console window

    # Collect data files
    data_items = collect_data_dirs()
    added = set()
    for src, dest in data_items:
        key = f"{src}{os.pathsep}{dest}"
        if key not in added:
            cmd.extend(["--add-data", key])
            added.add(key)

    # Hidden imports (so PyInstaller doesn't miss them)
    hidden = [
        "PyQt5", "PyQt5.QtCore", "PyQt5.QtWidgets", "PyQt5.QtGui",
        "PIL", "PIL._tkinter_finder",
        "qrcode", "requests", "flask", "escpos",
        "googleapiclient", "google_auth_oauthlib",
        "pyzbar", "cv2",
    ]
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    # Icon
    icon = find_icon()
    if icon:
        cmd.extend(["--icon", icon])

    cmd.append(os.path.join(PROJECT_DIR, ENTRY_SCRIPT))

    # ── Print summary ─────────────────────────────────────────────────
    is_win = platform.system() == "Windows"
    ext = ".exe" if is_win else ""
    out_name = f"{name}{ext}" if not (platform.system() == "Darwin" and not is_win) else f"{name}.app"
    if platform.system() == "Darwin":
        out_name = f"{name}.app"

    print("=" * 60)
    print(f"  Building: {name}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Output:   {os.path.join(dist_dir, out_name)}")
    print(f"  Bundled data files: {len(data_items)}")
    print("=" * 60)
    print()
    print("Running PyInstaller (this may take a few minutes)...")
    print()

    # ── Execute ───────────────────────────────────────────────────────
    try:
        subprocess.check_call(cmd, cwd=PROJECT_DIR)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code {e.returncode}")
        sys.exit(1)

    # ── Result ────────────────────────────────────────────────────────
    result = os.path.join(dist_dir, out_name)
    if os.path.exists(result):
        size_mb = 0
        if os.path.isfile(result):
            size_mb = os.path.getsize(result) / (1024 * 1024)
        elif os.path.isdir(result):
            total = 0
            for root, dirs, files in os.walk(result):
                for f in files:
                    total += os.path.getsize(os.path.join(root, f))
            size_mb = total / (1024 * 1024)

        print()
        print("=" * 60)
        print(f"  SUCCESS")
        print(f"  File:  {result}")
        print(f"  Size:  {size_mb:.1f} MB")
        print("=" * 60)
        print()
        print("  To distribute, share this single file.")
        if platform.system() == "Windows":
            print("  Users double-click the .exe to run the installer.")
        elif platform.system() == "Darwin":
            print("  Users double-click the .app to run the installer.")
        else:
            print(f"  Run: chmod +x '{result}' && ./'{result}'")
        print()
        return result
    else:
        print(f"\nBuild failed: {result} not found.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build NUBRI Biobank Installer executable")
    parser.add_argument("--name", default=DEFAULT_NAME, help=f"Output name (default: {DEFAULT_NAME})")
    parser.add_argument("--clean", action="store_true", help="Clean build directory before building")
    parser.add_argument("--zip", action="store_true", help="Create a ZIP archive of the output")
    args = parser.parse_args()

    result = build_installer(name=args.name, clean=args.clean)

    if args.zip and result:
        zippath = shutil.make_archive(
            result, "zip", os.path.dirname(result), os.path.basename(result)
        )
        print(f"  Archived: {zippath}")


if __name__ == "__main__":
    main()
