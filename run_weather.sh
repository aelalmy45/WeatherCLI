#!/data/data/com.termux/files/usr/bin/bash
# Resolve the repo directory from this script's own location (following
# symlinks), so scheduled jobs work no matter where the repo was cloned.
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
exec /data/data/com.termux/files/usr/bin/python3 "$SCRIPT_DIR/weather.py"
