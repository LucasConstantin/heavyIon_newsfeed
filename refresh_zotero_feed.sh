#!/usr/bin/env bash
set -euo pipefail

# Daily helper: regenerate arXiv feed files and serve them for Zotero.
# Optional overrides:
#   CONFIG=Heavy-Ion LOOKBACK_DAYS=10 MAX_RESULTS=200 PORT=8000 ./refresh_zotero_feed.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG="${CONFIG:-Heavy-Ion}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-10}"
MAX_RESULTS="${MAX_RESULTS:-200}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_FEED_URL="${BASE_FEED_URL:-http://${HOST}:${PORT}/feeds}"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Error: neither 'python' nor 'python3' was found in PATH." >&2
  exit 1
fi

echo "[1/2] Generating feeds..."
"$PYTHON_BIN" create_arxiv_feed.py \
  --search \
  -c "$CONFIG" \
  --lookback_days "$LOOKBACK_DAYS" \
  --max_results "$MAX_RESULTS" \
  --base_feed_url "$BASE_FEED_URL"

echo "[2/2] Starting local feed server for Zotero..."
echo "Serving at: http://${HOST}:${PORT}/feeds/"
echo "Press Ctrl+C to stop."

exec "$PYTHON_BIN" -m http.server "$PORT" --bind "$HOST"
