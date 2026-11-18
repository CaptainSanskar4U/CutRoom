import os
import json
import uuid
import traceback
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.video import SourceVideo
from app.models.clip import Clip
from app.config import AUDIO_DIR, THUMBNAILS_DIR, RENDERS_DIR
from app.services.video_service import probe_video, extract_audio, generate_thumbnail, cut_video_clip
from app.services.transcription_service import transcribe_audio
from app.services.virality_engine import extract_candidate_clips
from app.services.cv_reframing import analyze_video_faces
from app.services.rendering_engine import render_final_clip
from app.services.url_importer import download_video_from_url

def process_video_pipeline(
    video_id: str,
    aspect_ratio: str = "9:16",
    min_clip_duration: int = 15,
    max_clip_duration: int = 60,
    caption_style: str = "hormozi",
    target_clips_count: int = 5
):
    """
    Background worker orchestrating the complete end-to-end AI repurposing workflow:
    Download (if URL) -> Probe & Audio -> Whisper AI -> Virality Scoring -> OpenCV Reframing -> Auto Render Top Clip.
    """
    db: Session = SessionLocal()
    try:
        video = db.query(SourceVideo).filter(SourceVideo.id == video_id).first()
        if not video:
            print(f"[Pipeline] Video {video_id} not found.")
            return

        print(f"[Pipeline] Starting processing for video: {video.title} ({video.id})")

        # Step 0: Download from URL if needed
        if (not video.filepath or not os.path.exists(video.filepath)) and video.source_url:
            video.status = "downloading"
            video.progress = 5
            video.status_message = "Downloading video from link (yt-dlp)..."
            db.commit()

            try:
                info = download_video_from_url(video.source_url)
                video.filepath = info["filepath"]
                video.filename = info["filename"]
                if not video.title or video.title == "Imported Video Link":
                    video.title = info["title"]
                db.commit()
            except Exception as dl_err:
                raise RuntimeError(f"Failed downloading video from URL: {str(dl_err)}")

        # Step 1: Probe metadata
        video.status = "extracting_audio"
        video.progress = 15
        video.status_message = "Probing video format and extracting audio..."
        db.commit()

        meta = probe_video(video.filepath)
        video.duration = meta["duration"]
        video.width = meta["width"]
        video.height = meta["height"]
        video.fps = meta["fps"]

        # Generate main video thumbnail
        thumb_path = str(THUMBNAILS_DIR / f"{video.id}_thumb.jpg")
        generate_thumbnail(video.filepath, thumb_path, timestamp=min(2.0, meta["duration"] * 0.1))
        video.thumbnail_path = thumb_path
        db.commit()

        # Step 2: Extract audio
        audio_path = str(AUDIO_DIR / f"{video.id}.wav")
        extract_audio(video.filepath, audio_path)
        video.audio_path = audio_path

        # Step 3: Transcribe with word timestamps
        video.status = "transcribing"
        video.progress = 35
        video.status_message = "Transcribing speech and generating word timestamps (Whisper AI)..."
        db.commit()

        transcript_data = transcribe_audio(audio_path)
        video.transcript_json = json.dumps(transcript_data)
        db.commit()

        # Step 4: AI Virality Analysis & Clip Candidate Generation
        video.status = "analyzing_virality"
        video.progress = 60
        video.status_message = "Analyzing viral hooks, narrative flow, and engagement potential..."
        db.commit()

        candidate_clips = extract_candidate_clips(
            transcript_data=transcript_data,
            min_duration=float(min_clip_duration),
            max_duration=float(max_clip_duration),
            target_count=target_clips_count
        )

        print(f"[Pipeline] Isolated {len(candidate_clips)} high-scoring viral candidate clips.")

        # Step 5: Computer Vision Face Tracking & Dynamic Reframing
        video.status = "tracking_faces"
        video.progress = 80
        video.status_message = "Tracking active speakers and calculating smooth framing..."
        db.commit()

        created_clip_ids = []

        for idx, cand in enumerate(candidate_clips):
            clip_id = str(uuid.uuid4())
            # Face tracking
            cv_results = analyze_video_faces(
                video.filepath,
                start_time=cand["start_time"],
                end_time=cand["end_time"]
            )

            primary_x = cv_results.get("primary_center_x", 0.5)
            primary_y = cv_results.get("primary_center_y", 0.5)
            is_multi = cv_results.get("is_multi_speaker", False)

            # Generate clip preview thumbnail
            clip_thumb_path = str(THUMBNAILS_DIR / f"clip_{clip_id}.jpg")
            generate_thumbnail(
                video.filepath,
                clip_thumb_path,
                timestamp=cand["start_time"] + min(1.0, cand["duration"] * 0.2)
            )

            # Generate lightweight framed web preview cut
            clip_preview_path = str(RENDERS_DIR / f"preview_{clip_id}.mp4")
            try:
                cut_video_clip(
                    video_path=video.filepath,
                    start_time=cand["start_time"],
                    end_time=cand["end_time"],
                    output_path=clip_preview_path,
                    framed=True,
                    aspect_ratio=aspect_ratio
                )
            except Exception as e:
                print(f"[Pipeline] Preview cut warning: {e}")
                clip_preview_path = None

            # Choose high-precision framing: default to fit_blur (Ambient Blur) so content fits 100%
            default_crop_mode = "split_screen" if is_multi else "fit_blur"

            # Create Clip record in database
            clip_record = Clip(
                id=clip_id,
                video_id=video.id,
                start_time=cand["start_time"],
                end_time=cand["end_time"],
                duration=cand["duration"],
                title=cand["title"],
                description=cand["description"],
                virality_score=cand["virality_score"],
                score_breakdown=json.dumps(cand["score_breakdown"]),
                virality_reason=cand["virality_reason"],
                hook_text=cand["hook_text"],
                social_caption=cand["social_caption"],
                aspect_ratio=aspect_ratio,
                crop_mode=default_crop_mode,
                crop_x=primary_x,
                crop_y=primary_y,
                caption_style=caption_style,
                caption_settings=json.dumps({"line_count": 2, "font_size": "medium", "uppercase": True}),
                custom_words_json=json.dumps(cand["words"]),
                thumbnail_path=clip_thumb_path,
                rendered_path=clip_preview_path,
                render_status="idle",
                render_progress=0
            )
            db.add(clip_record)
            db.commit()
            created_clip_ids.append(clip_id)

        # Pre-render top #1 viral clip directly to ready-to-post MP4!
        if created_clip_ids:
            top_clip = db.query(Clip).filter(Clip.id == created_clip_ids[0]).first()
            if top_clip:
                out_path = str(RENDERS_DIR / f"export_{top_clip.id}_{aspect_ratio.replace(':', 'x')}.mp4")
                try:
                    words_data = json.loads(top_clip.custom_words_json) if top_clip.custom_words_json else []
                    render_final_clip(
                        source_video_path=video.filepath,
                        output_video_path=out_path,
                        start_time=top_clip.start_time,
                        end_time=top_clip.end_time,
                        aspect_ratio=aspect_ratio,
                        crop_x_norm=top_clip.crop_x,
                        crop_y_norm=top_clip.crop_y,
                        crop_mode=top_clip.crop_mode,
                        words=words_data,
                        caption_style=caption_style,
                        burn_captions=True
                    )
                    top_clip.rendered_path = out_path
                    top_clip.render_status = "completed"
                    top_clip.render_progress = 100
                    top_clip.render_message = "Ready to download and post directly!"
                    db.commit()
                    print(f"[Pipeline] Auto-rendered ready-to-post top clip: {out_path}")
                except Exception as ex:
                    print(f"[Pipeline] Top clip auto-render warning: {ex}")

        # Finalize video state
        video.status = "completed"
        video.progress = 100
        video.status_message = f"Generated {len(candidate_clips)} viral clips ready to post!"
        db.commit()
        print(f"[Pipeline] Video {video_id} processing completed successfully.")

    except Exception as e:
        traceback.print_exc()
        db.rollback()
        video = db.query(SourceVideo).filter(SourceVideo.id == video_id).first()
        if video:
            video.status = "failed"
            video.status_message = f"Processing error: {str(e)}"
            db.commit()
    finally:
        db.close()
