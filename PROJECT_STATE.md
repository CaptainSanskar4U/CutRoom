# CutRoom Project State & Architecture Handover

> **FOR FUTURE AGENTS / DEVELOPERS:**  
> Read this document to get 100% full context of the project architecture, recent major features, decisions made, and exact implementation details.

---

## 📌 Executive Summary

CutRoom is an AI video repurposing platform that turns long-form content (YouTube links or local uploads) into retention-optimized vertical shorts (TikTok, Reels, Shorts).

As of the latest commits:
1. **Simplified to Exactly Two Layout Choices:**
   - **Center Fit:** Video centered preserving original aspect ratio with blurred ambient backdrop + execution of the **CenterFitClip AI Editing Skill**.
   - **Full Screen:** Video expanded edge-to-edge (9:16) with **Deep-Learning Steadicam Face Tracking** and **Safe Person-Edge Clamping** (zero clipping of speaker).
2. **Strict Subtitle Language Translation:**
   - User selection of target subtitle language (e.g., English for a Hindi video) translates subtitles while strictly preserving word-level timing and synchronization.
3. **Enhance & Polish Stage Powered by CenterFitClip Skill:**
   - When **Center Fit** is selected, Stage 5 (**Enhance & Polish**) executes the provided **CenterFitClip Video Editing Skill** (`CenterfitSkill/centerfitclip/`).
   - The Full Screen workflow remains completely untouched.

---

## 🎬 Two Core Layout Modes

### 1. Center Fit (`layout: 'fit'`)
- **Philosophy:** Preserves full 16:9 widescreen context with an automatic, framed **Second Box** (facecam box) underneath.
- **Workflow Execution:**
  During the **Enhance & Polish** stage (80%–100%), CutRoom invokes `cutroom/centerfit_skill.py`, which executes:
  1. `analyze.py`: Automatically detects the real content rectangle, audio reaction peaks, scene cuts, and clusters human faces. If a human speaker is stable in $\ge 30\%$ of sampled frames, `layout.second_box.visible = True`. If voice-over only, the box stays hidden.
  2. **Text Assets Formulation:**
     - **Hook Line 1 (White 58 px):** Setup line.
     - **Hook Line 2 (Yellow 72 px):** Punchline / curiosity gap.
     - Font: `Hind-Bold.ttf` with black outline.
     - Captions: Relative word timestamps chunked into clean 1–2 line cues.
     - Reactions: Emotional exclamations (`"WHOA!"`, `"WATCH THIS!"`) timed to audio peaks.
     - Teasers: Open loops at 30% and 72% for clips $\ge 15$s.
  3. `render.py`: Renders vertical 9:16 composite with reaction-synced punch-zooms ($+10\%$ clip, $+16\%$ facecam box), 6 px yellow framing lines, and synthesized audio design (sub-booms on peaks, whooshes on cuts, normalized to $-13.5$ LUFS).
  4. `qc.py`: Mandatory quality gate verifying aspect ratio, loudness ($-16 \dots -12$ LUFS), true peak ($\le -1$ dBTP), frame integrity, and geometry.
  5. **Pre-rendered Clip Delivery:** The certified MP4 is stored at `data/media/projects/{project_id}/clips/{clip_id}.mp4` and served via `/api/clips/{clip_id}/video`.

### 2. Full Screen (`layout: 'track'`)
- **Philosophy:** 9:16 edge-to-edge crop with intelligent camera tracking.
- **Key Fixes Implemented:**
  - Removed background saliency energy drift that previously pulled the crop window toward high-contrast gameplay elements and sliced the speaker off the frame edge.
  - Added **Safe Person-Edge Clamping**:
    $$\text{half\_crop} = 0.5 \times \frac{9}{16} \times \frac{h}{w}$$
    The horizontal camera center $\text{aim}_x$ is mathematically constrained so the detected person boundary $[p_{\text{left}}, p_{\text{right}}]$ is never cut off or clipped.
  - Verified on live reaction footage: speaker's head, shoulders, and expressions remain centered and completely unclipped with generous safety margins.

---

## 🌐 Subtitle Translation Engine

- **Problem Solved:** When a user selected English subtitles for a Hindi video, subtitles previously remained in Hindi because YouTube native tracks (`hi-orig`) were downloaded to avoid rate limits, and YouTube's auto-translate scraper endpoint returned HTTP 429.
- **Solution (`cutroom/intelligence.py`):**
  - Added `translate_transcript(words, target_lang, progress=None)`:
    Groups transcript words into natural sentence boundaries, translates them via a dedicated translation pipeline, and computes proportional timestamps ($w_{\text{dur}} = c_{\text{dur}} / N_{\text{words}}$) so word-level synchronization and karaoke animations remain intact.
  - Integrated into `worker.py` in both YouTube platform telemetry and local Whisper transcription paths.

---

## 🔄 The 5-Stage Processing Workflow

All projects progress through 5 distinct stages visible in the UI:
1. **Prepare Video** (0%–15%): Media download, platform telemetry snatching (auditory peaks & audience heatmap), and 480p proxy creation.
2. **Transcribe** (15%–40%): Platform native subtitle ingestion or Whisper transcription + automatic target language translation.
3. **Rank Clips** (40%–60%): Tri-signal virality ranking (Hook curiosity + Vocal acoustic energy + Replay heatmap).
4. **Track Subjects** (60%–80%): Precision OpenCV YuNet CNN face tracking and Steadicam camera trajectory computation.
5. **Enhance & Polish** (80%–100%):
   - **If Center Fit (`fit`):** Executes `CenterFitClip` Skill suite end-to-end for every candidate clip, generating finished 9:16 shorts with automatic second boxes, punch-zooms, hook cards, and QC certification.
   - **If Full Screen (`track`):** Applies kinetic typography, hook cards, and safe edge boundaries.

---

## 📂 Key File & Directory Map

| Path | Purpose |
| :--- | :--- |
| `CenterfitSkill/centerfitclip/` | Standalone CenterFitClip video editing skill package (`scripts/analyze.py`, `render.py`, `qc.py`, `assets/fonts/Hind-Bold.ttf`). |
| `Cutroom-Studio/cutroom-studio/cutroom/centerfit_skill.py` | Python bridge that executes `analyze.py`, text asset formulation, `render.py`, and `qc.py`. |
| `Cutroom-Studio/cutroom-studio/cutroom/worker.py` | Core background job runner (`analysis_job`, `analyze_file`, `render_job`, `add_clips`). |
| `Cutroom-Studio/cutroom-studio/cutroom/video.py` | FFmpeg rendering engine, tracking logic, safe person clamping, and clip export. |
| `Cutroom-Studio/cutroom-studio/cutroom/intelligence.py` | Virality ranking, transcript translation (`translate_transcript`), and voice clustering. |
| `Cutroom-Studio/cutroom-studio/cutroom/api.py` | FastAPI application, project/clip endpoints, and `/api/clips/{id}/video` streaming. |
| `Cutroom-Studio/cutroom-studio/web/assets/ui.js` | UI definitions (exposes only `fit` Center Fit and `track` Full Screen). |
| `Cutroom-Studio/cutroom-studio/web/assets/editor.js` | Interactive clip editor with pre-rendered Center Fit player and live Full Screen framing. |
| `Cutroom-Studio/cutroom-studio/web/assets/app.js` | Dashboard cards, progress bar stages, and modal video previewers. |

---

## 🧪 Verified Test Projects

1. **Project `4cda24df9239403ab64486e37186f517` (Full Screen Verified):**
   - Source: *GTA 6 Reaction* (Hindi audio).
   - Target Subtitles: English (`en`).
   - Output: Translated English subtitles with centered speaker framing, zero face clipping.
2. **Project `0eae4404fa8840128e6c4d7c6e854246` (Center Fit Verified):**
   - Source: *GTA 6 Reaction* (Hindi audio).
   - Layout: Center Fit (`fit`).
   - Output: Both clips passed QC certification (`qc_passed: True`), second box rendered automatically at 66% and 40% face persistence, 2-line Hind typography, reaction zooms, and sound design.

---

## 🚀 Running the Services

- **CutRoom Studio (Port 3000):**
  ```powershell
  $env:PYTHONPATH="E:\OpusClips\Cutroom-Studio\cutroom-studio"; python -m uvicorn cutroom.api:app --host 0.0.0.0 --port 3000 --app-dir E:\OpusClips\Cutroom-Studio\cutroom-studio
  ```
- **AutoClip Backend (Port 8000, optional microservice):**
  ```powershell
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir e:\OpusClips\backend
  ```
