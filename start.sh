#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import fastapi, uvicorn, multipart, yt_dlp, imageio_ffmpeg, faster_whisper" >/dev/null 2>&1; then
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
