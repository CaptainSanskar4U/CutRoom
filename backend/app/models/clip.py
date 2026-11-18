from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, index=True)
    video_id = Column(String, ForeignKey("source_videos.id"), nullable=False)

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    virality_score = Column(Integer, default=85)
    score_breakdown = Column(Text, nullable=True)  # JSON {hook, flow, value, emotional_intensity, context, ending}
    virality_reason = Column(Text, nullable=True)
    hook_text = Column(Text, nullable=True)
    social_caption = Column(Text, nullable=True)

    aspect_ratio = Column(String, default="9:16")  # 9:16, 1:1, 16:9, 4:5
    crop_mode = Column(String, default="auto_face")  # auto_face, split_screen, center, manual
    crop_x = Column(Float, default=0.5)  # Normalized 0.0 to 1.0
    crop_y = Column(Float, default=0.5)

    caption_style = Column(String, default="hormozi")  # hormozi, neon, minimal, beast
    caption_settings = Column(Text, nullable=True)  # JSON font, colors, position, etc.
    custom_words_json = Column(Text, nullable=True)  # Editable word list with timestamps

    thumbnail_path = Column(String, nullable=True)
    rendered_path = Column(String, nullable=True)
    render_status = Column(String, default="idle")  # idle, rendering, completed, failed
    render_progress = Column(Integer, default=0)
    render_message = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    video = relationship("SourceVideo", back_populates="clips")
