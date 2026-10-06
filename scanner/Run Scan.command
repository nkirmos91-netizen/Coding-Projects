#!/bin/bash
# Double-click to run a full scan and open the ranked results page.
source "$(dirname "$0")/mac/common.sh"
echo "Running the hidden orderblock scan. This takes a few minutes..."
echo
if "$PY" -m hobscan scan; then
  open output/hob_scan.html
  echo
  echo "Done. The results page has opened in your browser."
else
  echo
  echo "The scan stopped with an error. Send a screenshot of this window to Claude."
fi
read -n1 -r -p "Press any key to close this window."
