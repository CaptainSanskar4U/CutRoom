from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models.template import Template
from app.services.caption_engine import STYLE_CONFIGS

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("")
def get_templates():
    presets = [
        {
            "id": "hormozi",
            "name": "Alex Hormozi Viral",
            "description": "High-contrast bold font, neon yellow/green active word highlighting, thick black outline. Built for viral retention.",
            "preview_text": "THIS IS HOW YOU GO VIRAL",
            "highlight_color": "#00FF66",
            "font_family": "Arial / Impact",
            "tag": "Most Popular"
        },
        {
            "id": "neon",
            "name": "Cyberpunk Neon",
            "description": "Vibrant cyan glowing text with subtle shadow. Perfect for tech, crypto, and modern video topics.",
            "preview_text": "The future of intelligence",
            "highlight_color": "#00FFFF",
            "font_family": "Trebuchet MS",
            "tag": "Trending"
        },
        {
            "id": "minimal",
            "name": "Minimalist Studio",
            "description": "Clean Helvetica styling with subtle gray-to-white highlight. Elegant for business, podcasts, and masterclasses.",
            "preview_text": "Simplicity is the ultimate sophistication",
            "highlight_color": "#FFFFFF",
            "font_family": "Helvetica",
            "tag": "Clean"
        },
        {
            "id": "beast",
            "name": "Beast Retention",
            "description": "Bold all-caps Impact font with fiery gold/orange accent. Drives maximum watch-time for dynamic YouTube Shorts.",
            "preview_text": "YOU WON'T BELIEVE THIS",
            "highlight_color": "#FFAA00",
            "font_family": "Impact",
            "tag": "High Energy"
        }
    ]
    return presets
