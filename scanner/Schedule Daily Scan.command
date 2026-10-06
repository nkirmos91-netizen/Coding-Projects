#!/bin/bash
# Double-click to have your Mac run the scan automatically every day.
source "$(dirname "$0")/mac/common.sh"
LABEL="com.hobscan.daily"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "What time should the scan run each day? (24-hour time, e.g. 07:30)"
read -r -p "Time [07:30]: " WHEN
WHEN="${WHEN:-07:30}"
HOUR="${WHEN%%:*}"; MIN="${WHEN##*:}"
if ! [[ "$HOUR" =~ ^[0-9]{1,2}$ && "$MIN" =~ ^[0-9]{2}$ ]] || [ "$HOUR" -gt 23 ] || [ "$MIN" -gt 59 ]; then
  echo "That doesn't look like a time. Run this again and type it like 07:30."
  read -n1 -r -p "Press any key to close this window."; exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" output
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$SCANNER_DIR/mac/scheduled-scan.sh</string><string>$PY</string></array>
  <key>WorkingDirectory</key><string>$SCANNER_DIR</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$((10#$HOUR))</integer><key>Minute</key><integer>$((10#$MIN))</integer></dict>
  <key>StandardOutPath</key><string>$SCANNER_DIR/output/scan.log</string>
  <key>StandardErrorPath</key><string>$SCANNER_DIR/output/scan.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo
echo "Scheduled: the scan will run every day at $WHEN."
echo "If your Mac is asleep then, it runs when it wakes up. You'll get a notification when it's done."
echo "Results: double-click 'Open Results'. To turn this off: double-click 'Stop Daily Scan'."
echo "If you move this folder, run 'Schedule Daily Scan' again."
read -n1 -r -p "Press any key to close this window."
