import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
AUDIO_DIR = STORAGE_DIR / "audio"
THUMBNAILS_DIR = STORAGE_DIR / "thumbnails"
RENDERS_DIR = STORAGE_DIR / "renders"
SUBTITLES_DIR = STORAGE_DIR / "subtitles"

for d in [STORAGE_DIR, UPLOADS_DIR, AUDIO_DIR, THUMBNAILS_DIR, RENDERS_DIR, SUBTITLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'autoclip.db'}")

SECRET_KEY = os.getenv("SECRET_KEY", "autoclip-super-secure-production-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")  # Options: tiny, base, small, medium
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

DEFAULT_ASPECT_RATIOS = ["9:16", "1:1", "16:9", "4:5"]
DEFAULT_CAPTION_STYLES = ["hormozi", "neon", "minimal", "beast"]
