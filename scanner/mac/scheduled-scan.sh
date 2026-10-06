#!/bin/bash
# Run by the daily schedule (see 'Schedule Daily Scan.command'). $1 = path to python3.
set -o pipefail
cd "$(dirname "$0")/.." || exit 1
echo "=== $(date) ==="
if SUMMARY="$("$1" -m hobscan scan 2>&1 | tee /dev/stderr | tail -1)"; then
  COUNT="$(echo "$SUMMARY" | grep -oE '^[0-9]+' || echo "")"
  osascript -e "display notification \"${COUNT:-New} hidden orderblocks found. Double-click 'Open Results' to view.\" with title \"HOB scan finished\""
else
  osascript -e 'display notification "The scan failed. See output/scan.log in the scanner folder." with title "HOB scan"'
fi
