#!/usr/bin/env bash
# Build azieltether-0.1.0.tar.gz into the Worker public/ assets directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="0.1.0"
NAME="azieltether-${VER}"
OUT_DIR="$ROOT/workers/download-tracker/public"
OUT="$OUT_DIR/${NAME}.tar.gz"
mkdir -p "$OUT_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/$NAME"
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'dist' \
    --exclude '*.egg-info' \
    --exclude '.wrangler' \
    --exclude 'workers/download-tracker/public/*.tar.gz' \
    --exclude '.azieltether-local' \
    "$ROOT/" "$TMP/$NAME/"
else
  tar -C "$ROOT" \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'dist' \
    --exclude '*.egg-info' \
    --exclude '.wrangler' \
    --exclude 'workers/download-tracker/public/*.tar.gz' \
    -cf - . | tar -C "$TMP/$NAME" -xf -
fi
tar -C "$TMP" -czf "$OUT" "$NAME"
echo "Wrote $OUT ($(wc -c < "$OUT") bytes)"
