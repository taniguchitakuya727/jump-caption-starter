#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

PORT="${JUMP_CAPTION_PORT:-8000}"
LOCAL_URL="http://127.0.0.1:${PORT}"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

echo
echo "========================================"
echo " Jump Caption friend subtitle editor"
echo "========================================"
echo

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg was not found on this Mac."
  echo "Install it with: brew install ffmpeg"
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Installing/updating Python packages..."
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -e .

mkdir -p outputs uploads

echo
echo "Local URL:"
echo "  ${LOCAL_URL}"
if [[ -n "$LAN_IP" ]]; then
  echo
  echo "Friend URL on the same Wi-Fi:"
  echo "  http://${LAN_IP}:${PORT}"
else
  echo
  echo "Could not detect Wi-Fi IP automatically."
  echo "Check System Settings > Wi-Fi > Details > IP address."
fi
echo
echo "Keep this terminal open while your friend edits subtitles."
echo "Press Control-C to stop."
echo

if command -v open >/dev/null 2>&1; then
  open "$LOCAL_URL" >/dev/null 2>&1 || true
fi

export JUMP_CAPTION_HOST="0.0.0.0"
export JUMP_CAPTION_PORT="$PORT"
export JUMP_CAPTION_FRIEND_EDITOR="1"
export PYTHONUTF8="1"
export PYTHONIOENCODING="utf-8"

".venv/bin/python" -m app
