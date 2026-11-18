#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
api_pid=''
web_pid=''
cleanup() {
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  [[ -z "$web_pid" ]] || kill "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
api_pid=$!
npm --prefix frontend run dev -- --hostname 127.0.0.1 &
web_pid=$!
wait -n "$api_pid" "$web_pid"
