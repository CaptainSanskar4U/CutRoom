from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.video import SourceVideo
from app.models.clip import Clip
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_projects = db.query(Project).filter(Project.user_id == current_user.id).count()
    user_videos = db.query(SourceVideo).join(Project).filter(Project.user_id == current_user.id).all()
    total_videos = len(user_videos)
    
    video_ids = [v.id for v in user_videos]
    total_clips = db.query(Clip).filter(Clip.video_id.in_(video_ids)).count() if video_ids else 0
    exported_clips = db.query(Clip).filter(Clip.video_id.in_(video_ids), Clip.render_status == "completed").count() if video_ids else 0

    total_processed_duration = sum(v.duration for v in user_videos)
    minutes_processed = round(total_processed_duration / 60.0, 1)

    return {
        "total_projects": total_projects,
        "total_videos": total_videos,
        "total_clips_generated": total_clips,
        "exported_clips": exported_clips,
        "minutes_processed": minutes_processed,
        "credits_remaining": current_user.credits_remaining,
        "plan": current_user.plan
    }
