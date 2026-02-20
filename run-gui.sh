#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUI_DIR="$SCRIPT_DIR/super-system-gui"

echo "Building Super System GUI..."
cd "$GUI_DIR"
swift build 2>&1

echo ""
echo "Launching Super System GUI..."
exec "$GUI_DIR/.build/debug/SuperSystemGUI"
