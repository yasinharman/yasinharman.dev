#!/usr/bin/env bash
# Frontend (Vite) ve backend (FastAPI) sunucularini birlikte baslatir.
# Ctrl+C ikisini birden kapatir; biri duserse digeri de kapanir.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
BACKEND_PORT="${BACKEND_PORT:-8000}"

if [ ! -x "$VENV/bin/uvicorn" ]; then
  echo "HATA: $VENV yok veya eksik. Once calistirin: npm run setup" >&2
  exit 1
fi

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "HATA: frontend/node_modules yok. Once calistirin: npm run setup" >&2
  exit 1
fi

pids=()

# uvicorn --reload ve npm gibi surecler alt surec dogurur; tum agaci kapatmak gerekir.
kill_tree() {
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    kill_tree "$child"
  done
  kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
  trap - INT TERM EXIT
  local pid
  for pid in "${pids[@]:-}"; do
    [ -n "$pid" ] && kill_tree "$pid"
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Backend .env'i calisma dizinine gore okudugu icin cwd backend/ olmali.
( cd "$ROOT/backend" && exec "$VENV/bin/uvicorn" app.main:app --reload --port "$BACKEND_PORT" ) &
pids+=("$!")

( cd "$ROOT/frontend" && exec npm run dev ) &
pids+=("$!")

# Biri duserse cleanup devreye girip digerini de kapatir.
wait -n
