#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
APP_ENV="${FLASK_ENV:-development}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found at $PYTHON_BIN"
  echo "Create it with: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

echo "[1/2] Resetting database for env: $APP_ENV"
"$PYTHON_BIN" scripts/reset_db.py --env "$APP_ENV"

echo "[2/2] Starting Flask app"
"$PYTHON_BIN" run.py
