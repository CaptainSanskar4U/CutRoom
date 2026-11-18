import os
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.video import SourceVideo
from app.models.clip import Clip
from app.models.project import Project
from app.schemas.clip import ClipResponse, ClipUpdateRequest, ClipRenderRequest
from app.api.auth import get_current_user
from app.config import RENDERS_DIR
from app.services.rendering_engine import render_final_clip
from app.services.video_service import cut_video_clip

router = APIRouter(prefix="/api/clips", tags=["clips"])

def serialize_clip(clip: Clip) -> ClipResponse:
    score_breakdown = json.loads(clip.score_breakdown) if clip.score_breakdown else None
    caption_settings = json.loads(clip.caption_settings) if clip.caption_settings else None
    custom_words = json.loads(clip.custom_words_json) if clip.custom_words_json else None

    thumb_url = f"/storage/thumbnails/{os.path.basename(clip.thumbnail_path)}" if clip.thumbnail_path else None
    preview_url = f"/storage/renders/{os.path.basename(clip.rendered_path)}" if clip.rendered_path and os.path.exists(clip.rendered_path) else None
    rendered_url = preview_url if clip.render_status == "completed" else None

    return ClipResponse(
        id=clip.id,
        video_id=clip.video_id,
        start_time=clip.start_time,
        end_time=clip.end_time,
        duration=clip.duration,
        title=clip.title,
        description=clip.description,
        virality_score=clip.virality_score,
        score_breakdown=score_breakdown,
        virality_reason=clip.virality_reason,
        hook_text=clip.hook_text,
        social_caption=clip.social_caption,
        aspect_ratio=clip.aspect_ratio,
        crop_mode=clip.crop_mode,
        crop_x=clip.crop_x,
        crop_y=clip.crop_y,
        caption_style=clip.caption_style,
        caption_settings=caption_settings,
        custom_words=custom_words,
        thumbnail_url=thumb_url,
        video_preview_url=preview_url,
        rendered_url=rendered_url,
        render_status=clip.render_status,
        render_progress=clip.render_progress,
        render_message=clip.render_message,
        created_at=clip.created_at,
        updated_at=clip.updated_at
    )

@router.get("", response_model=List[ClipResponse])
def list_clips(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(SourceVideo).join(Project).filter(
        SourceVideo.id == video_id,
        Project.user_id == current_user.id
    ).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    clips = db.query(Clip).filter(Clip.video_id == video_id).order_by(Clip.virality_score.desc()).all()
    return [serialize_clip(c) for c in clips]

@router.get("/{clip_id}", response_model=ClipResponse)
def get_clip(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    clip = db.query(Clip).join(SourceVideo).join(Project).filter(
        Clip.id == clip_id,
        Project.user_id == current_user.id
    ).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return serialize_clip(clip)

@router.put("/{clip_id}", response_model=ClipResponse)
def update_clip(
    clip_id: str,
    data: ClipUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    clip = db.query(Clip).join(SourceVideo).join(Project).filter(
        Clip.id == clip_id,
        Project.user_id == current_user.id
    ).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if data.title is not None:
        clip.title = data.title
    if data.start_time is not None:
        clip.start_time = round(data.start_time, 2)
    if data.end_time is not None:
        clip.end_time = round(data.end_time, 2)
    if data.start_time is not None or data.end_time is not None:
        clip.duration = round(clip.end_time - clip.start_time, 2)

    if data.aspect_ratio is not None:
        clip.aspect_ratio = data.aspect_ratio
    if data.crop_mode is not None:
        clip.crop_mode = data.crop_mode
    if data.crop_x is not None:
        clip.crop_x = data.crop_x
    if data.crop_y is not None:
        clip.crop_y = data.crop_y
    if data.caption_style is not None:
        clip.caption_style = data.caption_style
    if data.caption_settings is not None:
        clip.caption_settings = json.dumps(data.caption_settings)
    if data.custom_words is not None:
        clip.custom_words_json = json.dumps(data.custom_words)

    db.commit()
    db.refresh(clip)
    return serialize_clip(clip)

def background_render_worker(clip_id: str, options: dict):
    """Background rendering worker with database progress updates."""
    db: Session = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            return

        clip.render_status = "rendering"
        clip.render_progress = 5
        clip.render_message = "Starting export render..."
        db.commit()

        video = clip.video
        output_filename = f"export_{clip.id}_{clip.aspect_ratio.replace(':', 'x')}.mp4"
        output_path = str(RENDERS_DIR / output_filename)

        words_data = json.loads(clip.custom_words_json) if clip.custom_words_json else []

        def progress_cb(pct: int, msg: str):
            clip.render_progress = pct
            clip.render_message = msg
            db.commit()

        render_final_clip(
            source_video_path=video.filepath,
            output_video_path=output_path,
            start_time=clip.start_time,
            end_time=clip.end_time,
            aspect_ratio=options.get("aspect_ratio") or clip.aspect_ratio,
            crop_x_norm=clip.crop_x,
            crop_y_norm=clip.crop_y,
            crop_mode=options.get("crop_mode") or clip.crop_mode or "fit_blur",
            words=words_data,
            caption_style=options.get("caption_style") or clip.caption_style,
            burn_captions=options.get("burn_captions", True),
            progress_callback=progress_cb
        )

        clip.rendered_path = output_path
        clip.render_status = "completed"
        clip.render_progress = 100
        clip.render_message = "Video exported successfully!"
        db.commit()
        print(f"[RenderWorker] Export completed for clip {clip_id}: {output_path}")

    except Exception as e:
        print(f"[RenderWorker] Error rendering clip {clip_id}: {e}")
        db.rollback()
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if clip:
            clip.render_status = "failed"
            clip.render_message = f"Render failed: {str(e)}"
            db.commit()
    finally:
        db.close()

@router.post("/{clip_id}/render", response_model=ClipResponse)
def trigger_render(
    clip_id: str,
    req: ClipRenderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    clip = db.query(Clip).join(SourceVideo).join(Project).filter(
        Clip.id == clip_id,
        Project.user_id == current_user.id
    ).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip.render_status = "rendering"
    clip.render_progress = 1
    clip.render_message = "Queued for rendering..."
    if req.aspect_ratio:
        clip.aspect_ratio = req.aspect_ratio
    if req.caption_style:
        clip.caption_style = req.caption_style
    if req.crop_mode:
        clip.crop_mode = req.crop_mode
    db.commit()

    background_tasks.add_task(
        background_render_worker,
        clip_id=clip.id,
        options={
            "aspect_ratio": req.aspect_ratio or clip.aspect_ratio,
            "crop_mode": req.crop_mode or clip.crop_mode,
            "caption_style": req.caption_style or clip.caption_style,
            "burn_captions": req.burn_captions
        }
    )

    return serialize_clip(clip)

@router.delete("/{clip_id}")
def delete_clip(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    clip = db.query(Clip).join(SourceVideo).join(Project).filter(
        Clip.id == clip_id,
        Project.user_id == current_user.id
    ).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    db.delete(clip)
    db.commit()
    return {"message": "Clip deleted successfully"}
