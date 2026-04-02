#!/bin/bash
# Install/uninstall the flight tracker launchd job (runs every 10s)

PLIST_NAME="com.jakubigla.flight-tracker"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
UV_PATH="$(which uv)"

install() {
    cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}/scripts/flight_tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>${UV_PATH}</string>
        <string>run</string>
        <string>python</string>
        <string>flight_tracker.py</string>
    </array>
    <key>StartInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${REPO_DIR}/scripts/flight_tracker/data/cron.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_DIR}/scripts/flight_tracker/data/cron.log</string>
</dict>
</plist>
EOF

    launchctl load "$PLIST_PATH"
    echo "Installed and started: ${PLIST_NAME}"
    echo "Log: ${REPO_DIR}/scripts/flight_tracker/data/cron.log"
}

uninstall() {
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm -f "$PLIST_PATH"
    echo "Uninstalled: ${PLIST_NAME}"
}

case "${1:-install}" in
    install)   install ;;
    uninstall) uninstall ;;
    *)         echo "Usage: $0 [install|uninstall]" ;;
esac
