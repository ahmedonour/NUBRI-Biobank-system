#!/bin/bash
#
# Setup auto-start for Biobank web server on macOS.
# Uses launchd to keep the web preview server running.
#
# Usage:
#   ./setup_autostart.sh              # install
#   ./setup_autostart.sh --uninstall  # remove
#

set -euo pipefail

BIOBANK_DIR="$HOME/Biobank"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USERNAME="$(whoami)"

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

if [ "${1:-}" = "--uninstall" ]; then
    echo "Removing auto-start..."
    for plist in com.nubri.biobank-web; do
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

echo "Setting up auto-start for web server..."

if [ -f "$SCRIPT_DIR/com.nubri.biobank-web.plist" ]; then
    process_plist \
        "$SCRIPT_DIR/com.nubri.biobank-web.plist" \
        "$LAUNCH_AGENTS_DIR/com.nubri.biobank-web.plist"
fi

echo ""
echo "Web server will auto-start on login."
echo "Check: launchctl list | grep nubri"
echo "Remove: $0 --uninstall"
