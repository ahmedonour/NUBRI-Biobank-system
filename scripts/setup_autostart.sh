#!/bin/bash
#
# Setup auto-start for PocketBase and Biobank web server on macOS
# Uses launchd to keep services running and auto-start on boot.
#
# Usage:
#   ./setup_autostart.sh [--user <username>] [--uninstall]
#

set -euo pipefail

BIOBANK_DIR="$HOME/Biobank"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USERNAME="${1:-$(whoami)}"

mkdir -p "$BIOBANK_DIR/logs"
mkdir -p "$LAUNCH_AGENTS_DIR"

process_plist() {
    local src="$1"
    local dest="$2"
    sed "s/{{USER}}/$USERNAME/g" "$src" > "$dest"
    chmod 644 "$dest"
    launchctl unload "$dest" 2>/dev/null || true
    launchctl load -w "$dest"
    echo "  Loaded: $(basename "$dest")"
}

echo "=== NUBRI Biobank Auto-Start Setup ==="
echo ""

if [ "${2:-}" = "--uninstall" ]; then
    echo "Removing auto-start..."
    for plist in com.nubri.pocketbase com.nubri.biobank-web; do
        dest="$LAUNCH_AGENTS_DIR/$plist.plist"
        if [ -f "$dest" ]; then
            launchctl unload "$dest" 2>/dev/null || true
            rm "$dest"
            echo "  Removed: $plist"
        fi
    done
    echo "Done."
    exit 0
fi

echo "Setting up auto-start for:"

if [ -f "$SCRIPT_DIR/com.nubri.pocketbase.plist" ]; then
    process_plist \
        "$SCRIPT_DIR/com.nubri.pocketbase.plist" \
        "$LAUNCH_AGENTS_DIR/com.nubri.pocketbase.plist"
fi

if [ -f "$SCRIPT_DIR/com.nubri.biobank-web.plist" ]; then
    process_plist \
        "$SCRIPT_DIR/com.nubri.biobank-web.plist" \
        "$LAUNCH_AGENTS_DIR/com.nubri.biobank-web.plist"
fi

echo ""
echo "Services will auto-start on login."
echo "To check status: launchctl list | grep nubri"
echo "To stop: launchctl stop com.nubri.<name>"
echo "To remove: $0 --uninstall"
