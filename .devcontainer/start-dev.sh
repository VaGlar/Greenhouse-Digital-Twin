#!/usr/bin/env bash
# Runs on every Codespace start (postStartCommand) — brings up both the
# backend API and the frontend dev server in the background so opening the
# Codespace is enough; nothing needs to be typed into a terminal by hand.
set -e
cd "$(dirname "$0")/.."

mkdir -p .devcontainer/logs

if ! pgrep -f "uvicorn api.main:app" > /dev/null; then
  # --reload: without it, a stale server process silently keeps serving old Python
  # code after `git pull` (the pgrep guard above skips starting a new one), even
  # though the working tree is up to date -- confusing to debug from the outside.
  nohup .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8123 > .devcontainer/logs/api.log 2>&1 &
fi

if ! pgrep -f "vite --port 5173" > /dev/null; then
  (cd frontend && nohup npm run dev -- --port 5173 --host 0.0.0.0 > ../.devcontainer/logs/vite.log 2>&1 &)
fi
