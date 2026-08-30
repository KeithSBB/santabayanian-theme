#!/bin/bash
set -euo pipefail
SRC="${1:-.}"
DEST="${2:-/var/www/santabayanian}"
if [ ! -f "$SRC/scripts/build-theme.py" ] || [ ! -f "$SRC/css/theme.css" ]; then
  echo "Usage: $0 <src-dir> [webroot]"
  exit 1
fi
mkdir -p "$DEST/scripts" "$DEST/css" "$DEST/js" "$DEST/images/site/mascot" "$DEST/deploy/theme-builder"
install -m 644 "$SRC/scripts/build-theme.py" "$DEST/scripts/build-theme.py"
install -m 644 "$SRC/css/theme.css" "$DEST/css/theme.css"
install -m 644 "$SRC/js/theme.js" "$DEST/js/theme.js"
rsync -a "$SRC/deploy/theme-builder/" "$DEST/deploy/theme-builder/"
if id nginx >/dev/null 2>&1; then
  chown nginx:nginx "$DEST/scripts/build-theme.py" "$DEST/css/theme.css" "$DEST/js/theme.js" || true
  chown -R nginx:nginx "$DEST/images/site" "$DEST/deploy/theme-builder" || true
fi
echo installed into "$DEST"
