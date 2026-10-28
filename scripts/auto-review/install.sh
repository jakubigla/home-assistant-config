#!/usr/bin/env bash
# Install (or remove with --uninstall) the launchd agents for the autonomous HA reviews.
# Schedules are local time: daily 23:30, weekly Sun 22:00, monthly 1st 22:00.
# launchd runs jobs missed during sleep once the Mac wakes.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
UID_="$(id -u)"

schedule_for() {
  case "$1" in
    daily)   echo "<key>Hour</key><integer>23</integer><key>Minute</key><integer>30</integer>" ;;
    weekly)  echo "<key>Weekday</key><integer>0</integer><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer>" ;;
    monthly) echo "<key>Day</key><integer>1</integer><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer>" ;;
  esac
}

for period in daily weekly monthly; do
  label="com.jakubigla.ha-auto-review.$period"
  plist="$AGENTS/$label.plist"
  launchctl bootout "gui/$UID_/$label" 2>/dev/null || true
  [ "${1:-}" = "--uninstall" ] && { rm -f "$plist"; echo "removed $label"; continue; }
  cat >"$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$HERE/run.sh</string><string>$period</string>
  </array>
  <key>StartCalendarInterval</key><dict>$(schedule_for "$period")</dict>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/ha-auto-review/launchd-$period.err</string>
</dict></plist>
PLIST
  mkdir -p "$HOME/Library/Logs/ha-auto-review"
  launchctl bootstrap "gui/$UID_" "$plist"
  echo "installed $label"
done
