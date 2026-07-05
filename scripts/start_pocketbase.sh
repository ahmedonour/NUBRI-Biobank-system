#!/bin/bash
#
# Start PocketBase server for NUBRI Biobank.
# Downloads PocketBase automatically if not found.
#

set -euo pipefail

BIOBANK_DIR="$HOME/Biobank"
PB_DIR="$BIOBANK_DIR/pocketbase"
PB_BIN="$PB_DIR/pocketbase"
PB_PORT="${PB_PORT:-8090}"
PB_DATA_DIR="$BIOBANK_DIR/pb_data"

mkdir -p "$BIOBANK_DIR/logs"
mkdir -p "$PB_DATA_DIR"

# Detect platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

# Download PocketBase if missing
if [ ! -f "$PB_BIN" ]; then
    echo "PocketBase not found. Downloading..."
    mkdir -p "$PB_DIR"
    DOWNLOAD_URL="https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_${OS}_${ARCH}.zip"
    echo "  URL: $DOWNLOAD_URL"

    if command -v curl &>/dev/null; then
        curl -L -o /tmp/pocketbase.zip "$DOWNLOAD_URL"
    elif command -v wget &>/dev/null; then
        wget -O /tmp/pocketbase.zip "$DOWNLOAD_URL"
    else
        echo "Error: curl or wget required to download PocketBase."
        exit 1
    fi

    unzip -o /tmp/pocketbase.zip -d "$PB_DIR"
    rm /tmp/pocketbase.zip
    chmod +x "$PB_BIN"
    echo "PocketBase downloaded to $PB_BIN"
fi

echo "Starting PocketBase on port $PB_PORT..."
echo "  Data dir: $PB_DATA_DIR"
echo "  Admin UI: http://127.0.0.1:${PB_PORT}/_/"
echo "  Logs: $BIOBANK_DIR/logs/pocketbase.log"
echo ""

"$PB_BIN" serve \
    --http="127.0.0.1:${PB_PORT}" \
    --dir="$PB_DATA_DIR" \
    >> "$BIOBANK_DIR/logs/pocketbase.log" 2>&1 &

echo "PID: $!"
echo "PocketBase is running in the background."
