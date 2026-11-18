from sqlalchemy import Column, String, DateTime, Text, Boolean
from datetime import datetime
from app.database import Base

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    
    caption_style = Column(String, default="hormozi")
    font_family = Column(String, default="Arial")
    font_size = Column(String, default="medium")  # small, medium, large
    text_color = Column(String, default="#FFFFFF")
    highlight_color = Column(String, default="#00FF66")
    outline_color = Column(String, default="#000000")
    outline_width = Column(String, default="2")
    shadow_color = Column(String, default="#00000088")
    position = Column(String, default="bottom")  # top, middle, bottom
    max_lines = Column(String, default="2")

    aspect_ratio = Column(String, default="9:16")
    crop_mode = Column(String, default="auto_face")
    watermark_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
