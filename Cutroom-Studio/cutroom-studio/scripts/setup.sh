#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for bin in ffmpeg ffprobe; do
  if ! command -v "$bin" >/dev/null; then
    echo "Install FFmpeg with libx264 and libass (Debian: apt-get install ffmpeg fontconfig fonts-dejavu-core fonts-liberation fonts-noto-core)." >&2
    exit 1
  fi
done
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python -m scripts.bootstrap_models
.venv/bin/python -m scripts.prepare_samples
printf '\nCutroom is ready. In separate terminals run:\n  make worker\n  make serve\n'
