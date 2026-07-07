#!/usr/bin/env python3
"""
NUBRI Biobank — Setup & Build Script

One-command setup:
    python setup_and_build.py

Does everything:
  1. Ensures Python 3.10+ is available
  2. Creates a virtual environment
  3. Installs all dependencies
  4. Installs PyInstaller
  5. Builds a standalone .exe (Windows) or .app (macOS)

Run with --venv-path to customise the venv location (default: ./venv).
"""

import os
import sys
import subprocess
import argparse
import platform
import shutil
from pathlib import Path


PROJECT_DIR = Path(__file__).parent.resolve()
REQUIREMENTS = PROJECT_DIR / "requirements.txt"
ENTRY_POINT = PROJECT_DIR / "main.py"
APP_NAME = "NUBRI_Biobank"

MIN_PYTHON = (3, 10)


def parse_args():
    p = argparse.ArgumentParser(description="Setup & build NUBRI Biobank")
    p.add_argument("--venv-path", default=str(PROJECT_DIR / "venv"),
                   help="Virtual environment directory")
    p.add_argument("--python", help="Path to Python 3.10+ executable")
    return p.parse_args()


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def check_python(python_exe=None):
    """Ensure Python 3.10+ is available. Return path to python executable."""
    candidates = [python_exe] if python_exe else []
    system = platform.system()
    if system == "Windows":
        candidates += [
            r"C:\Python310\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python312\python.exe",
            r"C:\Python313\python.exe",
        ]
    # Common names
    candidates += [sys.executable, "python3", "python"]

    for exe in candidates:
        if not exe:
            continue
        try:
            r = subprocess.run([exe, "--version"],
                               capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                continue
            ver_str = r.stdout.strip().replace("Python ", "")
            parts = tuple(int(x) for x in ver_str.split(".")[:2])
            if parts >= MIN_PYTHON:
                print(f"  Found Python {ver_str} at: {exe}")
                return exe
        except Exception:
            continue

    print(f"\n  Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required but not found.")
    print(f"  Download from: https://www.python.org/downloads/")
    if system == "Windows":
        print(f"  Make sure to check 'Add Python to PATH' during install.")
    sys.exit(1)


def install_python_if_missing():
    """On Windows, try to install Python 3.10+ via official installer."""
    system = platform.system()
    if system != "Windows":
        return  # macOS/Linux: just ask user to install

    # Check if already installed
    exe = check_python()
    if exe:
        return exe

    print("  Attempting to download Python installer...")
    import urllib.request
    version = "3.10.11"
    url = f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe"
    installer = PROJECT_DIR / f"python-{version}-amd64.exe"

    try:
        urllib.request.urlretrieve(url, installer)
        print(f"  Downloaded: {installer}")
    except Exception as e:
        print(f"  Download failed: {e}")
        print("  Please install Python 3.10+ manually from python.org")
        sys.exit(1)

    print("  Running installer (this may open a UAC prompt)...")
    subprocess.check_call([str(installer), "/quiet", "InstallAllUsers=1",
                           "PrependPath=1"])
    installer.unlink()

    # Re-check
    return check_python()


def create_venv(python_exe, venv_path):
    """Create or reuse a virtual environment."""
    venv = Path(venv_path)
    if venv.exists():
        print(f"  Virtual env exists at: {venv}")
    else:
        print(f"  Creating virtual environment at: {venv}...")
        subprocess.check_call([python_exe, "-m", "venv", str(venv)])

    # Return path to python inside venv
    if platform.system() == "Windows":
        py = venv / "Scripts" / "python.exe"
    else:
        py = venv / "bin" / "python"
    if not py.exists():
        print(f"  ERROR: {py} not found after venv creation.")
        sys.exit(1)
    print(f"  Using: {py}")
    return str(py)


def install_deps(python_exe):
    """Install all dependencies from requirements.txt + PyInstaller."""
    print("  Upgrading pip...")
    subprocess.check_call([python_exe, "-m", "pip", "install",
                           "--upgrade", "pip"])

    if REQUIREMENTS.exists():
        print(f"  Installing from {REQUIREMENTS}...")
        subprocess.check_call([python_exe, "-m", "pip", "install",
                               "-r", str(REQUIREMENTS)])

    print("  Installing PyInstaller...")
    subprocess.check_call([python_exe, "-m", "pip", "install",
                           "pyinstaller"])


def build_exe(python_exe):
    """Build a standalone executable with PyInstaller."""
    system = platform.system()
    dist_dir = PROJECT_DIR / "dist"
    work_dir = dist_dir / "build"
    spec_dir = dist_dir

    dist_dir.mkdir(exist_ok=True)

    cmd = [
        python_exe, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--noconfirm",
        "--clean",
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
    ]

    # Windowed mode (no console)
    if system == "Windows":
        cmd.append("--noconsole")
        out_name = f"{APP_NAME}.exe"
    elif system == "Darwin":
        cmd.append("--windowed")
        out_name = f"{APP_NAME}.app"
    else:
        out_name = APP_NAME

    # Bundle the app package
    cmd.extend(["--add-data", f"app{os.pathsep}app"])

    # Hidden imports for PyInstaller
    for mod in ["PIL", "qrcode", "escpos", "flask", "requests",
                "googleapiclient", "pyzbar", "cv2",
                "barcode", "barcode.codex"]:
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(ENTRY_POINT))

    print(f"  Output: {out_name}")
    print("  Running PyInstaller (may take a few minutes)...")
    subprocess.check_call(cmd, cwd=PROJECT_DIR)

    result = dist_dir / out_name
    if result.exists():
        size = result.stat().st_size / (1024 * 1024) if result.is_file() else 0
        print(f"\n  SUCCESS: {result} ({size:.1f} MB)" if size else f"\n  SUCCESS: {result}")
    else:
        print(f"\n  Build may have failed — check {dist_dir} for output.")
        sys.exit(1)


def main():
    args = parse_args()

    print(f"\n  NUBRI Biobank — Setup & Build")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Project:  {PROJECT_DIR}")

    step("1/4 — Checking Python")
    python_exe = install_python_if_missing()
    if not python_exe:
        python_exe = check_python(args.python)

    step("2/4 — Creating virtual environment")
    venv_python = create_venv(python_exe, args.venv_path)

    step("3/4 — Installing dependencies")
    install_deps(venv_python)

    step("4/4 — Building executable")
    build_exe(venv_python)

    print(f"\n{'='*60}")
    print(f"  ALL DONE!")
    print(f"  Executable is in: {PROJECT_DIR / 'dist'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
