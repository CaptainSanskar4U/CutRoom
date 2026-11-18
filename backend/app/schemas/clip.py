from pydantic import BaseModel
from typing import Optional, Any, List, Dict
from datetime import datetime

class ClipUpdateRequest(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    aspect_ratio: Optional[str] = None
    crop_mode: Optional[str] = None
    crop_x: Optional[float] = None
    crop_y: Optional[float] = None
    caption_style: Optional[str] = None
    caption_settings: Optional[Dict[str, Any]] = None
    custom_words: Optional[List[Dict[str, Any]]] = None

class ClipRenderRequest(BaseModel):
    aspect_ratio: Optional[str] = None
    crop_mode: Optional[str] = None
    caption_style: Optional[str] = None
    quality: Optional[str] = "high"  # high, medium
    burn_captions: Optional[bool] = True

class ClipResponse(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    duration: float
    title: str
    description: Optional[str] = None
    virality_score: int
    score_breakdown: Optional[Dict[str, Any]] = None
    virality_reason: Optional[str] = None
    hook_text: Optional[str] = None
    social_caption: Optional[str] = None
    aspect_ratio: str
    crop_mode: str
    crop_x: float
    crop_y: float
    caption_style: str
    caption_settings: Optional[Dict[str, Any]] = None
    custom_words: Optional[List[Dict[str, Any]]] = None
    thumbnail_url: Optional[str] = None
    video_preview_url: Optional[str] = None
    rendered_url: Optional[str] = None
    render_status: str
    render_progress: int
    render_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
