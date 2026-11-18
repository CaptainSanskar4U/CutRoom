from sqlalchemy import Column, String, DateTime, Integer
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    plan = Column(String, default="Pro")  # Free, Pro, Enterprise
    credits_remaining = Column(Integer, default=120)  # minutes of video processing
    created_at = Column(DateTime, default=datetime.utcnow)
