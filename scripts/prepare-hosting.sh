#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC="$ROOT/public"

mkdir -p "$PUBLIC/static"
if [ -d "$ROOT/static" ]; then
  rsync -a --delete "$ROOT/static/" "$PUBLIC/static/"
  echo "✅ Static files copied to public/static/"
else
  echo "⚠️ No static/ directory found"
fi
