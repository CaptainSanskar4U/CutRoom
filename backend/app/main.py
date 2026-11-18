import os
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import engine, Base, SessionLocal
from app.config import STORAGE_DIR, UPLOADS_DIR, RENDERS_DIR, THUMBNAILS_DIR
from app.models.user import User
from app.models.project import Project
from app.services.auth_service import hash_password

from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.videos import router as videos_router
from app.api.clips import router as clips_router
from app.api.templates import router as templates_router
from app.api.stats import router as stats_router

# Initialize database schema
Base.metadata.create_all(bind=engine)

# Seed default demo account if empty
db = SessionLocal()
try:
    demo_user = db.query(User).filter(User.email == "creator@opusclip.pro").first()
    if not demo_user:
        user_id = str(uuid.uuid4())
        demo_user = User(
            id=user_id,
            email="creator@opusclip.pro",
            hashed_password=hash_password("password123"),
            full_name="Alex Creator",
            plan="Pro",
            credits_remaining=240
        )
        db.add(demo_user)
        default_proj = Project(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="AI Repurposing Master Project",
            status="active"
        )
        db.add(default_proj)
        db.commit()
        print("[DB] Initialized demo account: creator@opusclip.pro / password123")
finally:
    db.close()

app = FastAPI(
    title="AutoClip Studio API",
    description="Production-Grade OpusClip Competitor AI Video Repurposing Engine",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts
app.mount("/storage/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/storage/renders", StaticFiles(directory=str(RENDERS_DIR)), name="renders")
app.mount("/storage/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# API Routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(videos_router)
app.include_router(clips_router)
app.include_router(templates_router)
app.include_router(stats_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AutoClip Studio Engine",
        "version": "2.0.0",
        "features": {
            "faster_whisper": True,
            "opencv_face_tracking": True,
            "ffmpeg_karaoke_subtitles": True,
            "virality_scoring": True,
            "yt_dlp_import": True
        }
    }

# Mount frontend production build as final fallback
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
