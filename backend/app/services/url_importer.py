import os
import uuid
from typing import Dict, Any, Optional, Callable
import yt_dlp
from app.config import UPLOADS_DIR

def download_video_from_url(
    url: str,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Downloads video using native Python yt_dlp module with best MP4 format up to 1080p.
    """
    target_dir = output_dir or str(UPLOADS_DIR)
    os.makedirs(target_dir, exist_ok=True)
    video_id = str(uuid.uuid4())
    output_template = os.path.join(target_dir, f"{video_id}.%(ext)s")

    if progress_callback:
        progress_callback(10, f"Fetching video metadata from link...")

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        title = info_dict.get('title', 'Imported Video')
        ext = info_dict.get('ext', 'mp4')

    final_filepath = None
    for f in os.listdir(target_dir):
        if f.startswith(video_id):
            final_filepath = os.path.join(target_dir, f)
            break

    if not final_filepath or not os.path.exists(final_filepath):
        # Fallback check for exact expected path
        candidate = os.path.join(target_dir, f"{video_id}.{ext}")
        if os.path.exists(candidate):
            final_filepath = candidate
        else:
            raise FileNotFoundError("Downloaded video file was not found on disk.")

    if progress_callback:
        progress_callback(100, "Download completed.")

    return {
        "filepath": final_filepath,
        "filename": os.path.basename(final_filepath),
        "title": title
    }
