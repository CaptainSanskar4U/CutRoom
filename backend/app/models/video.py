from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SourceVideo(Base):
    __tablename__ = "source_videos"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    fps = Column(Float, default=30.0)
    audio_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    status = Column(String, default="uploaded")  # uploaded, extracting_audio, transcribing, analyzing_virality, tracking_faces, completed, failed
    progress = Column(Integer, default=0)
    status_message = Column(String, default="Video uploaded")
    
    transcript_json = Column(Text, nullable=True)  # Full segments with word timestamps
    speakers_json = Column(Text, nullable=True)  # Diarization / speaker turns
    face_tracks_json = Column(Text, nullable=True)  # Detected face tracking coordinate ranges

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="videos")
    clips = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
