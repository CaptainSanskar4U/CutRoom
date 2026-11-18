import os
import sys
import json
import subprocess

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath("backend"))

from app.services.cv_reframing import analyze_video_faces, compute_crop_parameters
from app.services.caption_engine import generate_ass_subtitle_file
from app.services.rendering_engine import render_final_clip
from app.services.video_service import probe_video

def main():
    print("==================================================")
    print("TESTING OPUSCLIP PRECISION FRAMING & ALIGNMENT")
    print("==================================================")

    video_path = os.path.abspath("podcast_interview.mp4")
    if not os.path.exists(video_path):
        print("ERROR: podcast_interview.mp4 not found!")
        sys.exit(1)

    meta = probe_video(video_path)
    print(f"[1] Source video probed: {meta['width']}x{meta['height']} @ {meta['fps']}fps, duration={meta['duration']}s")

    # Step 1: Test CV Face Tracking
    print("\n[2] Testing Active Speaker CV Face Tracking...")
    face_info = analyze_video_faces(video_path, start_time=0.0, end_time=10.0, sample_count=8)
    print(f"   Face tracking result: {face_info}")
    assert "primary_center_x" in face_info
    assert "primary_center_y" in face_info
    print("   CV Face Tracking: SUCCESS")

    # Sample word timestamps for subtitle testing
    sample_words = [
        {"word": "The", "start": 0.5, "end": 0.8},
        {"word": "secret", "start": 0.8, "end": 1.2},
        {"word": "to", "start": 1.2, "end": 1.4},
        {"word": "going", "start": 1.4, "end": 1.7},
        {"word": "viral", "start": 1.7, "end": 2.2},
        {"word": "on", "start": 2.2, "end": 2.4},
        {"word": "YouTube", "start": 2.4, "end": 2.9},
        {"word": "Shorts", "start": 2.9, "end": 3.4},
        {"word": "is", "start": 3.4, "end": 3.6},
        {"word": "precision", "start": 3.6, "end": 4.1},
        {"word": "framing", "start": 4.1, "end": 4.6}
    ]

    # Step 2: Test ASS subtitle generation with safe zone MarginV
    print("\n[3] Testing ASS Subtitle Generation in Social Safe Zone...")
    ass_path = os.path.abspath("backend/storage/subtitles/test_safezone.ass")
    generate_ass_subtitle_file(
        words=sample_words,
        output_ass_path=ass_path,
        clip_start_offset=0.0,
        style_name="hormozi",
        play_res_x=1080,
        play_res_y=1920
    )
    with open(ass_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "MarginV" in content
    assert "480" in content, f"Expected MarginV: 480 in ASS file, got:\n{content[:500]}"
    print("   ASS Subtitle Safe Zone: SUCCESS (MarginV: 480 verified)")

    # Step 3: Test render_final_clip with crop_mode="fit_blur" (Signature Ambient Blur)
    print("\n[4] Testing render_final_clip with crop_mode='fit_blur'...")
    out_fit_blur = os.path.abspath("backend/storage/renders/test_fit_blur_output.mp4")
    render_final_clip(
        source_video_path=video_path,
        output_video_path=out_fit_blur,
        start_time=0.0,
        end_time=5.0,
        aspect_ratio="9:16",
        crop_mode="fit_blur",
        words=sample_words,
        caption_style="hormozi",
        burn_captions=True
    )
    assert os.path.exists(out_fit_blur), "Output file was not created!"
    meta_fit = probe_video(out_fit_blur)
    print(f"   Fit Blur output: {meta_fit['width']}x{meta_fit['height']} @ {meta_fit['fps']}fps, duration={meta_fit['duration']}s")
    assert meta_fit["width"] == 1080
    assert meta_fit["height"] == 1920
    print("   Crop Mode 'fit_blur': SUCCESS (1080x1920 verified)")

    # Step 4: Test render_final_clip with crop_mode="auto_face"
    print("\n[5] Testing render_final_clip with crop_mode='auto_face'...")
    out_face = os.path.abspath("backend/storage/renders/test_auto_face_output.mp4")
    render_final_clip(
        source_video_path=video_path,
        output_video_path=out_face,
        start_time=0.0,
        end_time=5.0,
        aspect_ratio="9:16",
        crop_x_norm=face_info["primary_center_x"],
        crop_y_norm=face_info["primary_center_y"],
        crop_mode="auto_face",
        words=sample_words,
        caption_style="neon",
        burn_captions=True
    )
    assert os.path.exists(out_face), "Output file was not created!"
    meta_face = probe_video(out_face)
    print(f"   Auto Face output: {meta_face['width']}x{meta_face['height']} @ {meta_face['fps']}fps")
    assert meta_face["width"] == 1080
    assert meta_face["height"] == 1920
    print("   Crop Mode 'auto_face': SUCCESS (1080x1920 verified)")

    # Step 5: Test render_final_clip with crop_mode="split_screen"
    print("\n[6] Testing render_final_clip with crop_mode='split_screen'...")
    out_split = os.path.abspath("backend/storage/renders/test_split_screen_output.mp4")
    render_final_clip(
        source_video_path=video_path,
        output_video_path=out_split,
        start_time=0.0,
        end_time=5.0,
        aspect_ratio="9:16",
        crop_mode="split_screen",
        words=sample_words,
        caption_style="beast",
        burn_captions=True
    )
    assert os.path.exists(out_split), "Output file was not created!"
    meta_split = probe_video(out_split)
    print(f"   Split Screen output: {meta_split['width']}x{meta_split['height']} @ {meta_split['fps']}fps")
    assert meta_split["width"] == 1080
    assert meta_split["height"] == 1920
    print("   Crop Mode 'split_screen': SUCCESS (1080x1920 verified)")

    print("\n==================================================")
    print("ALL PRECISION FRAMING & RENDERING TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    main()
