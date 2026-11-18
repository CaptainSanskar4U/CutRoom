from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class VideoImportRequest(BaseModel):
    url: str
    project_id: Optional[str] = None
    title: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"
    caption_style: Optional[str] = "hormozi"

class VideoProcessRequest(BaseModel):
    aspect_ratio: Optional[str] = "9:16"
    min_clip_duration: Optional[int] = 15
    max_clip_duration: Optional[int] = 60
    caption_style: Optional[str] = "hormozi"
    target_clips_count: Optional[int] = 5

class VideoResponse(BaseModel):
    id: str
    project_id: str
    title: str
    filename: Optional[str] = None
    filepath: Optional[str] = None
    source_url: Optional[str] = None
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 30.0
    status: str
    progress: int = 0
    status_message: Optional[str] = None
    thumbnail_path: Optional[str] = None
    has_transcript: bool = False
    clip_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoDetailResponse(VideoResponse):
    transcript: Optional[Any] = None
    speakers: Optional[Any] = None
