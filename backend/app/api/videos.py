import os
import uuid
import shutil
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.video import VideoResponse, VideoDetailResponse, VideoImportRequest, VideoProcessRequest
from app.api.auth import get_current_user
from app.config import UPLOADS_DIR, THUMBNAILS_DIR
from app.services.video_service import probe_video, generate_thumbnail
from app.services.pipeline_orchestrator import process_video_pipeline

router = APIRouter(prefix="/api/videos", tags=["videos"])

@router.get("", response_model=List[VideoResponse])
def list_videos(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SourceVideo).join(Project).filter(Project.user_id == current_user.id)
    if project_id:
        query = query.filter(SourceVideo.project_id == project_id)
    videos = query.order_by(SourceVideo.created_at.desc()).all()

    results = []
    for v in videos:
        results.append(VideoResponse(
            id=v.id,
            project_id=v.project_id,
            title=v.title,
            filename=v.filename,
            filepath=v.filepath,
            source_url=v.source_url,
            duration=v.duration,
            width=v.width,
            height=v.height,
            fps=v.fps,
            status=v.status,
            progress=v.progress,
            status_message=v.status_message,
            thumbnail_path=f"/storage/thumbnails/{os.path.basename(v.thumbnail_path)}" if v.thumbnail_path else None,
            has_transcript=v.transcript_json is not None,
            clip_count=len(v.clips),
            created_at=v.created_at,
            updated_at=v.updated_at
        ))
    return results

@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    auto_process: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project
    project = None
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        project = db.query(Project).filter(Project.user_id == current_user.id).first()
        if not project:
            project = Project(id=str(uuid.uuid4()), user_id=current_user.id, title="Default Project")
            db.add(project)
            db.commit()
            db.refresh(project)

    video_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    save_filename = f"{video_id}{ext}"
    dest_path = UPLOADS_DIR / save_filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Initial metadata probe
    meta = {"duration": 0.0, "width": 0, "height": 0, "fps": 30.0}
    thumb_path = None
    try:
        meta = probe_video(str(dest_path))
        thumb_path = str(THUMBNAILS_DIR / f"{video_id}_thumb.jpg")
        generate_thumbnail(str(dest_path), thumb_path, timestamp=min(1.0, meta["duration"] * 0.1))
    except Exception as e:
        print(f"[Upload] Probe warning: {e}")

    video_record = SourceVideo(
        id=video_id,
        project_id=project.id,
        title=title or os.path.splitext(file.filename)[0],
        filename=file.filename,
        filepath=str(dest_path),
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        fps=meta["fps"],
        thumbnail_path=thumb_path,
        status="uploaded",
        progress=0,
        status_message="Video uploaded successfully"
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    # Automatically launch pipeline
    background_tasks.add_task(process_video_pipeline, video_id=video_id)

    return VideoResponse(
        id=video_record.id,
        project_id=video_record.project_id,
        title=video_record.title,
        filename=video_record.filename,
        filepath=video_record.filepath,
        source_url=video_record.source_url,
        duration=video_record.duration,
        width=video_record.width,
        height=video_record.height,
        fps=video_record.fps,
        status=video_record.status,
        progress=video_record.progress,
        status_message=video_record.status_message,
        thumbnail_path=f"/storage/thumbnails/{os.path.basename(thumb_path)}" if thumb_path else None,
        has_transcript=False,
        clip_count=0,
        created_at=video_record.created_at,
        updated_at=video_record.updated_at
    )

@router.post("/import-url", response_model=VideoResponse)
def import_video_url(
    req: VideoImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find or create user project
    project = None
    if req.project_id:
        project = db.query(Project).filter(Project.id == req.project_id, Project.user_id == current_user.id).first()
    if not project:
        project = db.query(Project).filter(Project.user_id == current_user.id).first()
        if not project:
            project = Project(id=str(uuid.uuid4()), user_id=current_user.id, title="Default Project")
            db.add(project)
            db.commit()
            db.refresh(project)

    clean_url = req.url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="Video URL cannot be empty")

    video_id = str(uuid.uuid4())
    video_record = SourceVideo(
        id=video_id,
        project_id=project.id,
        title=req.title or "Imported Video Link",
        filename="importing.mp4",
        filepath="",
        source_url=clean_url,
        status="downloading",
        progress=5,
        status_message="Downloading video from link (yt-dlp)..."
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    # Launch complete background pipeline immediately: downloads video + isolates viral hooks + renders top clip
    background_tasks.add_task(
        process_video_pipeline,
        video_id=video_record.id,
        aspect_ratio=req.aspect_ratio or "9:16",
        caption_style=req.caption_style or "hormozi"
    )

    return VideoResponse(
        id=video_record.id,
        project_id=video_record.project_id,
        title=video_record.title,
        filename=video_record.filename,
        filepath=video_record.filepath,
        source_url=video_record.source_url,
        duration=0.0,
        width=0,
        height=0,
        fps=30.0,
        status=video_record.status,
        progress=video_record.progress,
        status_message=video_record.status_message,
        thumbnail_path=None,
        has_transcript=False,
        clip_count=0,
        created_at=video_record.created_at,
        updated_at=video_record.updated_at
    )

@router.get("/{video_id}", response_model=VideoDetailResponse)
def get_video(
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

    transcript_obj = json.loads(video.transcript_json) if video.transcript_json else None
    speakers_obj = json.loads(video.speakers_json) if video.speakers_json else None

    return VideoDetailResponse(
        id=video.id,
        project_id=video.project_id,
        title=video.title,
        filename=video.filename,
        filepath=video.filepath,
        source_url=video.source_url,
        duration=video.duration,
        width=video.width,
        height=video.height,
        fps=video.fps,
        status=video.status,
        progress=video.progress,
        status_message=video.status_message,
        thumbnail_path=f"/storage/thumbnails/{os.path.basename(video.thumbnail_path)}" if video.thumbnail_path else None,
        has_transcript=video.transcript_json is not None,
        clip_count=len(video.clips),
        transcript=transcript_obj,
        speakers=speakers_obj,
        created_at=video.created_at,
        updated_at=video.updated_at
    )

@router.post("/{video_id}/process")
def process_video(
    video_id: str,
    options: VideoProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(SourceVideo).join(Project).filter(
        SourceVideo.id == video_id,
        Project.user_id == current_user.id
    ).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status in ["downloading", "extracting_audio", "transcribing", "analyzing_virality", "tracking_faces"]:
        return {"message": "Video is already being processed", "status": video.status}

    background_tasks.add_task(
        process_video_pipeline,
        video_id=video_id,
        aspect_ratio=options.aspect_ratio or "9:16",
        min_clip_duration=options.min_clip_duration or 15,
        max_clip_duration=options.max_clip_duration or 60,
        caption_style=options.caption_style or "hormozi",
        target_clips_count=options.target_clips_count or 5
    )

    return {"message": "AI video repurposing pipeline initiated", "video_id": video_id}

@router.delete("/{video_id}")
def delete_video(
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

    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
