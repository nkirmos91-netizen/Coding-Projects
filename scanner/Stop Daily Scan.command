#!/bin/bash
# Double-click to stop the automatic daily scan.
LABEL="com.hobscan.daily"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "The daily scan is turned off."
read -n1 -r -p "Press any key to close this window."
