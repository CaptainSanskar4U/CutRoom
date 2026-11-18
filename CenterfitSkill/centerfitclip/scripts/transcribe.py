#!/usr/bin/env python3
"""Optional: real captions. Usage: python transcribe.py input.mp4 --lang hi --out work/captions.json
Uses faster-whisper or openai-whisper if installed (models download on first use; needs internet).
Output: [{"start":0.0,"end":1.8,"text":"..."}]  -> review by a human/agent for accuracy before rendering."""
import argparse, json, sys
ap = argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("--lang", default=None); ap.add_argument("--out", default="captions.json")
a = ap.parse_args(); segs = None
try:
    from faster_whisper import WhisperModel
    m = WhisperModel("small", compute_type="int8"); it, _ = m.transcribe(a.input, language=a.lang, vad_filter=True)
    segs = [dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip()) for s in it]
except ImportError:
    try:
        import whisper
        r = whisper.load_model("small").transcribe(a.input, language=a.lang)
        segs = [dict(start=round(s["start"], 2), end=round(s["end"], 2), text=s["text"].strip()) for s in r["segments"]]
    except ImportError:
        sys.exit("No whisper installed. Do NOT invent captions. Either install faster-whisper, or render without --captions.")
json.dump(segs, open(a.out, "w"), ensure_ascii=False, indent=2); print(len(segs), "segments ->", a.out)
