# Shared by the double-click scripts. Finds a Python 3.11+ and moves to the scanner folder.
SCANNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCANNER_DIR" || exit 1

find_python() {
  for p in "$(command -v python3)" /Library/Frameworks/Python.framework/Versions/*/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -x "$p" ] && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      echo "$p"; return 0
    fi
  done
  return 1
}

PY="$(find_python)"
if [ -z "$PY" ]; then
  echo "Python 3.11 or newer wasn't found. Install it from python.org, then try again."
  read -n1 -r -p "Press any key to close this window."
  exit 1
fi

[ -f config.toml ] || cp config.example.toml config.toml
"$PY" -c 'import yfinance, requests' 2>/dev/null || "$PY" -m pip install -q -r requirements.txt
