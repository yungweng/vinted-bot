#!/usr/bin/env bash
# Build Tailwind CSS for the dashboard.
# Requires `tailwindcss` v4 standalone binary on PATH, or pass path via TAILWIND_BIN.
# Download: https://github.com/tailwindlabs/tailwindcss/releases/latest
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
STATIC="$ROOT/src/vinted_bot/dashboard/static"

TW="${TAILWIND_BIN:-tailwindcss}"
if ! command -v "$TW" >/dev/null 2>&1; then
  if [ -x "/tmp/tailwindcss" ]; then
    TW="/tmp/tailwindcss"
  else
    echo "tailwindcss binary not found. Set TAILWIND_BIN or install it." >&2
    exit 1
  fi
fi

exec "$TW" -i "$STATIC/input.css" -o "$STATIC/output.css" --minify "$@"
