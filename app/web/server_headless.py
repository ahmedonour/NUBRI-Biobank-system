#!/usr/bin/env python3
"""
Headless web server runner — starts the Flask preview server independently.
Used by launchd for auto-start without the desktop GUI.

Usage:
    python -m app.web.server_headless --db /path/to/biobank.db --port 5000
"""

import os
import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NUBRI Biobank Headless Web Server")
    parser.add_argument("--db", default=None, help="Path to SQLite database")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    args = parser.parse_args()

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    from app.database.connection import DatabaseConnection
    from app.database.models import SettingsModel
    from app.web.server import WebServer

    db = DatabaseConnection.get_instance(args.db)
    settings = SettingsModel(db)

    server = WebServer(db, port=args.port)
    server.start()

    print(f"Web server running on http://0.0.0.0:{args.port}")
    print("Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()
        print("Server stopped.")
