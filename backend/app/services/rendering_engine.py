import subprocess
import os
from typing import Dict, Any, Optional, Callable
from app.services.caption_engine import generate_ass_subtitle_file
from app.services.cv_reframing import compute_crop_parameters
from app.services.video_service import probe_video
from app.config import SUBTITLES_DIR

def render_final_clip(
    source_video_path: str,
    output_video_path: str,
    start_time: float,
    end_time: float,
    aspect_ratio: str = "9:16",
    crop_x_norm: float = 0.5,
    crop_y_norm: float = 0.35,
    crop_mode: str = "fit_blur",
    words: Optional[list] = None,
    caption_style: str = "hormozi",
    burn_captions: bool = True,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Renders high-quality production MP4 with pixel-perfect framing and ASS karaoke captions.
    Supported crop modes:
      - 'fit_blur' (default): Full video preserved in center, ambient motion-blurred video filling top/bottom.
      - 'auto_face': Face-centered crop with cinematic 35% eye-level headroom.
      - 'split_screen': Stacked dual speaker split-screen for interviews/podcasts.
    """
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    meta = probe_video(source_video_path)
    orig_w = meta["width"] or 1920
    orig_h = meta["height"] or 1080
    total_clip_duration = max(0.5, end_time - start_time)

    # Calculate target dimensions
    if aspect_ratio == "9:16":
        out_w, out_h = 1080, 1920
    elif aspect_ratio == "1:1":
        out_w, out_h = 1080, 1080
    elif aspect_ratio == "4:5":
        out_w, out_h = 1080, 1350
    elif aspect_ratio == "16:9":
        out_w, out_h = 1920, 1080
    else:
        out_w, out_h = 1080, 1920

    # Subtitle preparation
    ass_path = None
    ass_dir = str(SUBTITLES_DIR)
    ass_file = None
    if burn_captions and words and len(words) > 0:
        clip_slug = os.path.splitext(os.path.basename(output_video_path))[0]
        ass_path = str(SUBTITLES_DIR / f"{clip_slug}.ass")
        generate_ass_subtitle_file(
            words=words,
            output_ass_path=ass_path,
            clip_start_offset=start_time,
            style_name=caption_style,
            play_res_x=out_w,
            play_res_y=out_h
        )
        ass_file = os.path.basename(ass_path)
        ass_dir = os.path.dirname(ass_path)

    if progress_callback:
        progress_callback(15, f"Composing {aspect_ratio} layout with {crop_mode} framing...")

    # Build filter complex according to chosen framing mode
    if crop_mode == "fit_blur":
        # Signature OpusClip ambient blur: entire content centered, blurred background filling entire screen
        filter_complex = (
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=25:5[bg];"
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        if ass_file and os.path.exists(ass_path):
            filter_complex += f",ass={ass_file}[v]"
        else:
            filter_complex += "[v]"

    elif crop_mode == "split_screen":
        # Dual speaker split-screen: Speaker 1 on top, Speaker 2 on bottom
        half_h = out_h // 2
        spk_crop_w = int(round(orig_w * 0.5))
        spk_crop_w = spk_crop_w - (spk_crop_w % 2)
        filter_complex = (
            f"[0:v]crop={spk_crop_w}:{orig_h}:0:0,scale={out_w}:{half_h}:force_original_aspect_ratio=increase,crop={out_w}:{half_h}[spk1];"
            f"[0:v]crop={spk_crop_w}:{orig_h}:{orig_w - spk_crop_w}:0,scale={out_w}:{half_h}:force_original_aspect_ratio=increase,crop={out_w}:{half_h}[spk2];"
            f"[spk1][spk2]vstack"
        )
        if ass_file and os.path.exists(ass_path):
            filter_complex += f",ass={ass_file}[v]"
        else:
            filter_complex += "[v]"

    else:
        # Default/auto_face: Face Centered Lock with cinematic headroom
        cx, cy, cw, ch = compute_crop_parameters(
            orig_width=orig_w,
            orig_height=orig_h,
            aspect_ratio=aspect_ratio,
            center_x=crop_x_norm,
            center_y=crop_y_norm
        )
        filter_complex = (
            f"[0:v]crop={cw}:{ch}:{cx}:{cy},"
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h}"
        )
        if ass_file and os.path.exists(ass_path):
            filter_complex += f",ass={ass_file}[v]"
        else:
            filter_complex += "[v]"

    cmd = [
        "ffmpeg",
        "-y",
        "-threads", "0",
        "-ss", str(start_time),
        "-i", os.path.abspath(source_video_path),
        "-t", str(total_clip_duration),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        os.path.abspath(output_video_path)
    ]

    if progress_callback:
        progress_callback(40, "Encoding high-retention video frames...")

    result = subprocess.run(cmd, cwd=ass_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render error (exit {result.returncode}): {result.stderr[-500:]}")

    if progress_callback:
        progress_callback(100, "Render completed successfully!")

    return output_video_path
