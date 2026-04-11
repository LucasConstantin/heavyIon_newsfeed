#!/usr/bin/env bash
set -euo pipefail

# Daily helper: regenerate arXiv feed files and serve them for Zotero.
# Optional overrides:
#   CONFIG=Heavy-Ion LOOKBACK_DAYS=10 MAX_RESULTS=200 PORT=8000 ./refresh_zotero_feed.sh
#
# Default behavior:
#   - If feeds/*_Xd_feed.xml files exist, refresh all of them.
#   - Otherwise, refresh CONFIG + LOOKBACK_DAYS only.

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

generate_feed() {
  local cfg="$1"
  local days="$2"
  echo "  -> ${cfg} (${days}d)"
  "$PYTHON_BIN" create_arxiv_feed.py \
    --search \
    -c "$cfg" \
    --lookback_days "$days" \
    --max_results "$MAX_RESULTS" \
    --base_feed_url "$BASE_FEED_URL"
}

echo "[1/2] Generating feeds..."
declare -A TARGETS=()

if [[ -d feeds ]]; then
  while IFS= read -r feed_file; do
    feed_name="$(basename "$feed_file")"
    if [[ "$feed_name" =~ ^(.+)_([0-9]+)d_feed\.xml$ ]]; then
      cfg="${BASH_REMATCH[1]}"
      days="${BASH_REMATCH[2]}"
      TARGETS["${cfg}|${days}"]=1
    fi
  done < <(find feeds -maxdepth 1 -type f -name '*_feed.xml' | sort)
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No existing feed pattern found; using CONFIG/LOOKBACK_DAYS defaults."
  generate_feed "$CONFIG" "$LOOKBACK_DAYS"
else
  echo "Refreshing ${#TARGETS[@]} existing feed target(s) from feeds/."
  for key in "${!TARGETS[@]}"; do
    cfg="${key%%|*}"
    days="${key##*|}"
    generate_feed "$cfg" "$days"
  done
fi

echo "[2/2] Starting local feed server for Zotero..."
echo "Serving at: http://${HOST}:${PORT}/feeds/"
echo "Press Ctrl+C to stop."

exec "$PYTHON_BIN" -m http.server "$PORT" --bind "$HOST"
