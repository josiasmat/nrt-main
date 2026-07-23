#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$ROOT_DIR/src"
OUT_FILE="$ROOT_DIR/nrt.pyz"

if [[ ! -f "$SRC_DIR/nrt.py" ]]; then
  echo "error: expected entrypoint at $SRC_DIR/nrt.py" >&2
  exit 1
fi

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

cp "$SRC_DIR"/*.py "$BUILD_DIR"/

python -m zipapp "$BUILD_DIR" -m nrt:main -o "$OUT_FILE"
echo "Built $OUT_FILE"
