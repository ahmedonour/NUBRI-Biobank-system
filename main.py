#!/usr/bin/env python3
"""
NUBRI Biobank Label System

A desktop application for generating biobank specimen labels with QR codes,
printing to Xprinter thermal printers, and looking up specimen details
via a mobile-friendly web interface.

Usage:
    python main.py
    python main.py --db /path/to/biobank.db
"""

import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="NUBRI Biobank Label System")
    parser.add_argument("--db", "-d", help="Path to SQLite database file (default: ./biobank.db)")
    args = parser.parse_args()

    db_path = args.db
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biobank.db")

    from PyQt5.QtWidgets import QApplication
    from app.gui.main_window import MainWindow
    from app.gui.theme import DARK_QSS

    app = QApplication(sys.argv)
    app.setApplicationName("NUBRI Biobank Label System")
    app.setOrganizationName("NUBRI")
    app.setStyleSheet(DARK_QSS)

    window = MainWindow(db_path=db_path)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
