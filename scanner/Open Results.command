#!/bin/bash
# Double-click to open the latest results page without running a new scan.
cd "$(dirname "$0")" || exit 1
if [ -f output/hob_scan.html ]; then
  open output/hob_scan.html
else
  echo "No results yet. Double-click 'Run Scan' first."
  read -n1 -r -p "Press any key to close this window."
fi
