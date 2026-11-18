import os
import sys
import json
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, r"e:\OpusClips\backend")

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.video import SourceVideo
from app.models.clip import Clip
from app.services.pipeline_orchestrator import process_video_pipeline
from app.services.rendering_engine import render_final_clip
from app.services.video_service import probe_video
from app.config import RENDERS_DIR

def run_e2e_test():
    print("==================================================")
    print(" AUTOCLIP STUDIO: PRODUCTION PIPELINE E2E TEST")
    print("==================================================")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "creator@opusclip.pro").first()
        assert user is not None, "Demo user should exist"
        print(f"✓ User authenticated: {user.email} (Plan: {user.plan}, Credits: {user.credits_remaining}m)")

        project = db.query(Project).filter(Project.user_id == user.id).first()
        assert project is not None, "Project should exist"
        print(f"✓ Active project: {project.title}")

        # Ingest test video
        test_video_path = "e:/OpusClips/podcast_interview.mp4"
        assert os.path.exists(test_video_path), "Test video should exist on disk"
        meta = probe_video(test_video_path)
        print(f"✓ Probed test video: {meta['width']}x{meta['height']} @ {meta['fps']}fps, duration: {meta['duration']:.2f}s")

        video_id = str(uuid.uuid4())
        video = SourceVideo(
            id=video_id,
            project_id=project.id,
            title="Secrets of Viral Growth (Podcast #42)",
            filename="podcast_interview.mp4",
            filepath=test_video_path,
            duration=meta["duration"],
            width=meta["width"],
            height=meta["height"],
            fps=meta["fps"],
            status="uploaded",
            progress=0
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        print(f"✓ Created SourceVideo record: {video.id}")

        # Run full pipeline
        print("\n--- Executing Full AI Pipeline (Audio -> Whisper -> Virality -> Reframing) ---")
        process_video_pipeline(
            video_id=video.id,
            aspect_ratio="9:16",
            min_clip_duration=15,
            max_clip_duration=45,
            caption_style="hormozi",
            target_clips_count=3
        )

        db.refresh(video)
        print(f"\n✓ Pipeline Status: {video.status} ({video.progress}%)")
        print(f"✓ Status Message: {video.status_message}")
        assert video.status == "completed", f"Pipeline should complete, got {video.status}"

        # Inspect generated clips
        clips = db.query(Clip).filter(Clip.video_id == video.id).order_by(Clip.virality_score.desc()).all()
        print(f"\n✓ Generated {len(clips)} Viral Clips:")
        assert len(clips) > 0, "At least 1 clip should be generated"

        for i, c in enumerate(clips):
            breakdown = json.loads(c.score_breakdown) if c.score_breakdown else {}
            print(f"\n  [Clip #{i+1}] {c.title}")
            print(f"    • Virality Score: {c.virality_score}/99 🔥")
            print(f"    • Time Range: {c.start_time:.1f}s - {c.end_time:.1f}s ({c.duration:.1f}s)")
            print(f"    • Rationale: {c.virality_reason}")
            print(f"    • Score Breakdown: Hook={breakdown.get('hook')}, Flow={breakdown.get('flow')}, Value={breakdown.get('value')}")
            print(f"    • Reframing: {c.aspect_ratio} (Crop Mode: {c.crop_mode}, Center X: {c.crop_x})")
            print(f"    • Preview Cut: {c.rendered_path}")

        # Test Server-Side Video Rendering & Caption Burning
        top_clip = clips[0]
        print(f"\n--- Testing Server-Side Video Rendering Engine on Top Clip #{top_clip.id} ---")
        output_mp4 = str(RENDERS_DIR / f"test_export_{top_clip.id}.mp4")
        words_data = json.loads(top_clip.custom_words_json) if top_clip.custom_words_json else []

        def on_progress(pct, msg):
            print(f"    [FFmpeg Render] {pct}% - {msg}")

        rendered_result = render_final_clip(
            source_video_path=video.filepath,
            output_video_path=output_mp4,
            start_time=top_clip.start_time,
            end_time=top_clip.end_time,
            aspect_ratio="9:16",
            crop_x_norm=top_clip.crop_x,
            crop_y_norm=top_clip.crop_y,
            crop_mode=top_clip.crop_mode,
            words=words_data,
            caption_style="hormozi",
            burn_captions=True,
            progress_callback=on_progress
        )

        assert os.path.exists(output_mp4), "Exported MP4 must exist"
        export_meta = probe_video(output_mp4)
        print(f"\n✓ Successfully Rendered Output Video: {output_mp4}")
        print(f"✓ Export File Size: {os.path.getsize(output_mp4) / 1024:.1f} KB")
        print(f"✓ Export Resolution: {export_meta['width']}x{export_meta['height']} (Expected 1080x1920 9:16 portrait)")
        print(f"✓ Export Duration: {export_meta['duration']:.2f}s")
        assert export_meta['width'] == 1080 and export_meta['height'] == 1920, "Must be vertical 9:16 (1080x1920)"

        print("\n==================================================")
        print(" ALL VERIFICATION CHECKS PASSED: 100% PRODUCTION READY")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_e2e_test()
