import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

def probe_video(video_path: str) -> Dict[str, Any]:
    """Extract metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    
    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration == 0.0 and video_stream:
        duration = float(video_stream.get("duration", 0.0))
        
    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    
    # Calculate FPS
    fps = 30.0
    if video_stream and "r_frame_rate" in video_stream:
        parts = video_stream["r_frame_rate"].split("/")
        if len(parts) == 2 and float(parts[1]) > 0:
            fps = round(float(parts[0]) / float(parts[1]), 2)
            
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": audio_stream is not None,
        "format": data.get("format", {}).get("format_name", "")
    }

def extract_audio(video_path: str, output_wav_path: str) -> str:
    """Extract 16kHz mono 16-bit PCM audio for Whisper."""
    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_wav_path

def generate_thumbnail(video_path: str, output_jpg_path: str, timestamp: float = 1.0) -> str:
    """Extract a frame as thumbnail."""
    os.makedirs(os.path.dirname(output_jpg_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(max(0.1, timestamp)),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_jpg_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_jpg_path

def cut_video_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    framed: bool = True,
    aspect_ratio: str = "9:16"
) -> str:
    """
    Extracts high-quality web-ready preview clip.
    When framed=True, composes with ambient blur so preview fits perfectly across the screen.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    duration = max(0.5, end_time - start_time)

    if framed and aspect_ratio == "9:16":
        # Fast 720x1280 ambient blur composition for instant browser playback
        filter_str = (
            "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=20:4[bg];"
            "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-threads", "0",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path
