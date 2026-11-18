import os
from typing import List, Dict, Any, Optional

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# Color converter to ASS &HBBGGRR format
def hex_to_ass_color(hex_color: str, alpha: str = "00") -> str:
    c = hex_color.lstrip("#")
    if len(c) == 6:
        r, g, b = c[0:2], c[2:4], c[4:6]
        return f"&H{alpha}{b}{g}{r}&"
    return "&H00FFFFFF&"

STYLE_CONFIGS = {
    "hormozi": {
        "Fontname": "Arial",
        "Fontsize": 64,
        "PrimaryColour": "&H00FFFFFF&",    # Inactive words (White)
        "SecondaryColour": "&H0000FF00&",  # Active word highlight (Neon Green BGR: 00FF00)
        "OutlineColour": "&H00000000&",    # Thick Black outline
        "BackColour": "&H90000000&",
        "Bold": "-1",
        "Italic": "0",
        "BorderStyle": "1",
        "Outline": "4",
        "Shadow": "2",
        "Alignment": "2",                  # Bottom-center
        "BaseMarginV": 480,                # Social Platform Safe Zone (~25% from bottom in 1920h)
        "Uppercase": True
    },
    "neon": {
        "Fontname": "Trebuchet MS",
        "Fontsize": 60,
        "PrimaryColour": "&H00F0F0F0&",
        "SecondaryColour": "&H00FFFF00&",  # Cyan highlight (BGR)
        "OutlineColour": "&H00221100&",
        "BackColour": "&H90000000&",
        "Bold": "-1",
        "Italic": "0",
        "BorderStyle": "1",
        "Outline": "3",
        "Shadow": "3",
        "Alignment": "2",
        "BaseMarginV": 480,
        "Uppercase": False
    },
    "minimal": {
        "Fontname": "Helvetica",
        "Fontsize": 52,
        "PrimaryColour": "&H00CCCCCC&",
        "SecondaryColour": "&H00FFFFFF&",  # Pure white active
        "OutlineColour": "&H00111111&",
        "BackColour": "&H00000000&",
        "Bold": "0",
        "Italic": "0",
        "BorderStyle": "1",
        "Outline": "2",
        "Shadow": "1",
        "Alignment": "2",
        "BaseMarginV": 460,
        "Uppercase": False
    },
    "beast": {
        "Fontname": "Impact",
        "Fontsize": 68,
        "PrimaryColour": "&H00FFFFFF&",
        "SecondaryColour": "&H000088FF&",  # Bright Orange/Gold active highlight (BGR)
        "OutlineColour": "&H00000000&",
        "BackColour": "&H90000000&",
        "Bold": "-1",
        "Italic": "0",
        "BorderStyle": "1",
        "Outline": "5",
        "Shadow": "2",
        "Alignment": "2",
        "BaseMarginV": 480,
        "Uppercase": True
    }
}

def generate_ass_subtitle_file(
    words: List[Dict[str, Any]],
    output_ass_path: str,
    clip_start_offset: float = 0.0,
    style_name: str = "hormozi",
    words_per_phrase: int = 4,
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    custom_overrides: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates an Advanced SubStation Alpha file with karaoke highlight tags.
    Scales safe-zone margins and font sizes dynamically to match the output canvas resolution.
    """
    os.makedirs(os.path.dirname(output_ass_path), exist_ok=True)
    cfg = STYLE_CONFIGS.get(style_name, STYLE_CONFIGS["hormozi"]).copy()
    if custom_overrides:
        cfg.update(custom_overrides)

    # Scale font size and margin relative to 1920 canvas height
    scale_factor = play_res_y / 1920.0
    effective_font_size = max(24, int(round(cfg["Fontsize"] * scale_factor)))
    effective_margin_v = max(40, int(round(cfg["BaseMarginV"] * scale_factor)))

    header = f"""[Script Info]
Title: AutoClip Studio Karaoke Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg["Fontname"]},{effective_font_size},{cfg["PrimaryColour"]},{cfg["SecondaryColour"]},{cfg["OutlineColour"]},{cfg["BackColour"]},{cfg["Bold"]},{cfg["Italic"]},0,0,100,100,0,0,{cfg["BorderStyle"]},{cfg["Outline"]},{cfg["Shadow"]},{cfg["Alignment"]},40,40,{effective_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    
    # Chunk words into groups (e.g. 3 to 4 words per screen for high retention)
    i = 0
    num_words = len(words)
    while i < num_words:
        chunk = words[i:i + words_per_phrase]
        if not chunk:
            break

        chunk_start = max(0.0, chunk[0]["start"] - clip_start_offset)
        chunk_end = max(chunk_start + 0.3, chunk[-1]["end"] - clip_start_offset)

        # Build karaoke text
        karaoke_parts = []
        for w in chunk:
            w_text = w["word"].strip()
            if cfg.get("Uppercase", False):
                w_text = w_text.upper()

            w_start = max(0.0, w["start"] - clip_start_offset)
            w_end = max(w_start + 0.1, w["end"] - clip_start_offset)
            duration_cs = max(10, int(round((w_end - w_start) * 100)))

            karaoke_parts.append(f"{{\\k{duration_cs}}}{w_text} ")

        line_text = "".join(karaoke_parts).strip()
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)

        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")
        i += len(chunk)

    full_content = header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    return output_ass_path
