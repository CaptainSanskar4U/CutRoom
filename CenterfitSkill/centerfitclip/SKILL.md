---
name: centerfitclip
description: CenterFitClip Skill - turns an original video into a polished, natural-looking, retention-optimized vertical (9:16) CENTER FIT short for Reels/Shorts/TikTok. Use whenever the user gives a video and wants it edited for virality, engagement or "center fit" output. Covers hook design, synced punch-zoom/sound design, Hindi/English caption accuracy, uncropped framing, an AUTOMATIC person-box (second box) that appears only when a human is actually in the footage, and a mandatory QC gate. Center Fit only - never full-screen/crop-to-fill.
---

# CenterFitClip Skill

**One job:** original video in -> finished 9:16 *Center Fit* clip out (blurred backdrop + full-width, uncropped footage in the middle), edited like a careful human editor: smooth, motivated, hook-first, never "AI-looking".

**Scope rule:** Center Fit only. If the user asks for full-screen / crop-to-fill, say this skill doesn't do that and stop.

## Requirements
`ffmpeg`/`ffprobe` (libx264, drawtext, zoompan), Python 3 with `numpy` and `opencv-python-headless<5` (see `requirements.txt`). Font `assets/fonts/Hind-Bold.ttf` (Latin + Devanagari, OFL) ships with the skill; `render.py` re-downloads it if missing. Optional: `faster-whisper`/`whisper` for real captions.

## Workflow (do these in order - do not skip)
1. **Analyze** - `python scripts/analyze.py INPUT.mp4 --out work/`
   Produces `analysis.json` (content rectangle, person detection, reaction peaks, scene cuts, speech-likeness) and `contact_sheet.jpg`. **Look at the contact sheet** and read `analysis.json` before deciding anything.
2. **Understand the video** - what is it, what language is spoken/shown, what is the single most curious moment? Everything below (hook, labels, teasers) must come from what is *actually* in the video.
3. **Write the text assets** (see `references/subtitles.md`):
   - hook (2 lines, source language/script), optional reaction labels (one per peak), optional two teasers, captions only if real transcription exists.
4. **Render** - `python scripts/render.py INPUT.mp4 work/analysis.json --hook1 "..." --hook2 "..." [--reactions r.json] [--captions c.json] [--teaser-mid "..."] [--teaser-late "..."] [--intensity balanced|clean] --out final.mp4`
5. **QC gate** - `python scripts/qc.py final.mp4 --source INPUT.mp4 --analysis work/analysis.json --report work/render_report.json`, then do the manual checks in `references/qc-checklist.md`. Fix and re-render until everything passes. Only then deliver.
6. **Deliver** the file + a short summary: what was done, what was assumed (e.g. generic reaction labels), what the user could improve (cover frame, caption, posting time).

Keep renders to one pass whenever possible (single filtergraph). Re-render only for a real defect.

## The Second Box (person box) - AUTOMATIC, never user-selected
The second box is the enlarged, framed crop of the on-screen person (facecam / talking head) shown below the main clip. **Visibility is decided only by `analyze.py` -> `layout.second_box.visible`.** There is no user toggle, no guessing from the filename or prompt.

Decision logic (implemented in `analyze.py`):
1. Find the real content area (strip blurred bands of already-center-fit sources).
2. Sample frames (<=2 fps, <=90 frames). Detect faces (Haar frontal+profile) inside the content area.
3. Cluster detections by position. The best cluster must appear in **>= 30 %** of sampled frames at a **stable position** with face width **>= 3 %** of content width. This rejects game/movie characters that move and appear briefly.
4. If no face qualifies, try a body (HOG) detector with a stricter rule (**>= 50 %** frames, stable). Otherwise: **no person**.
5. `visible = person found`. The box crop is computed automatically (face width x 3.5, 16:10, shoulders included, clamped inside the content area).
6. Speech without a visible person (voice-over/off-screen speaker) -> `speaker_offscreen: true`, **box stays hidden** (there is nothing to show). Say so in the delivery note.
7. Layout adapts: **with box** -> clip + box block centered vertically, hook above. **Without box** -> clip alone, vertically centered, larger breathing room, hook above. No empty placeholder, ever.

UI contract: a UI/agent must read `analysis.json -> layout.second_box.visible` and render the box only if `true`; `qc.py` fails the export if rendered != detected.

## Non-negotiables (details in references/)
- **Center Fit geometry:** full-width, never cropped to fill; person and subtitles fully visible (`references/layout-center-fit.md`).
- **Natural motion:** motivated, short, eased; shake <= 1.25 % of width, only on real reaction peaks; no metronome zooms (`references/style-guide.md`).
- **No AI look:** no fake captions, no emoji spam, no neon strokes, no fade-from-black, no generic "subscribe" text, no continuous effects.
- **Hook in <= 3 s**, first frame already visible, text <= 2 lines and never huge (58/72 px at 720 wide).
- **Retention:** open-loop teasers at ~30 % and ~72 %, thin progress line, hard-cut ending that loops.
- **Subtitles:** exact source language and script; never invent speech; never double-subtitle burned-in subs (`references/subtitles.md`).
- **Audio:** -14 LUFS (+-2), true peak <= -1 dBTP, synthesized SFX only, always under the voice.
- **Honesty:** if something couldn't be verified (no transcription, no audio analysis), say it in the delivery note.

## Files
`scripts/analyze.py` `scripts/render.py` `scripts/qc.py` `scripts/transcribe.py` | `references/style-guide.md` `layout-center-fit.md` `subtitles.md` `qc-checklist.md` | `examples/*.json`
