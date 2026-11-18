# CutRoom — AI Video Repurposing & Viral Clip Studio

CutRoom is an end-to-end, high-performance platform for turning long-form videos and podcasts into high-engagement vertical clips (TikTok, YouTube Shorts, Instagram Reels) with AI face tracking, animated subtitles, smart virality scoring, and cloud synchronization.

---

## 🌟 Key Features

- **AI Steadicam & Precision Reframing:** Automatically tracks active speakers and centers faces for 9:16, 1:1, 4:5, and 16:9 aspect ratios.
- **Dynamic Animated Subtitles:** Word-level synchronized caption animations with viral presets:
  - *Pulse* (Pop & Pill)
  - *Hormozi* (Bold Impact)
  - *Beast* (Viral Pop)
  - *Cinema* (Minimal Glow)
  - *Studio*, *Spotlight*, and *Mono*
- **Virality Scoring & Clip Selection:** Transcript analysis identifying the highest-retention hooks, quotes, and narrative climaxes.
- **Interactive Web Studio Editor:** Real-time trimming, caption repositioning, layout switching, brand kit application, and instant preview.
- **Lean Low-Memory Encoding:** Robust FFmpeg pipeline featuring thread capping, lookahead buffer optimization, and automatic memory-constrained fallbacks.
- **Cloud Storage & Sync:** Seamless integration with Supabase Storage and PostgreSQL for centralized job queues and instant cloud MP4 exports.

---

## 🏗️ Architecture

```
CutRoom/
├── Cutroom-Studio/
│   └── cutroom-studio/           # CutRoom Studio application (Port 3000)
│       ├── cutroom/              # Core Python engine (API, video, audio, AI, store, worker)
│       ├── web/                  # Studio frontend (assets, landing page, editor, CSS, JS)
│       ├── docs/                 # System architecture and API documentation
│       ├── samples/              # Test video footage
│       ├── scripts/              # Maintenance and CLI utilities
│       ├── tests/                # Pipeline and worker tests
│       ├── Dockerfile            # Container build configuration
│       ├── compose.yaml          # Multi-container orchestration
│       ├── requirements.txt      # Python dependencies
│       └── supabase_schema.sql   # Database schema for Supabase
├── backend/                      # AutoClip microservice backend (FastAPI, Port 8000)
│   └── app/                      # Auth, project management, and clip services
├── frontend/                     # AutoClip web interface (React + Vite + Tailwind)
│   ├── src/                      # UI components, pages, and hooks
│   └── package.json
└── README.md                     # Monorepo documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11 / 3.13)
- **FFmpeg 6.0+** (Added to system PATH)
- **Node.js 18+** (Optional, for AutoClip React UI)

### 2. Environment Configuration
Copy `.env.example` to `.env` in `Cutroom-Studio/cutroom-studio/`:
```bash
cp Cutroom-Studio/cutroom-studio/.env.example Cutroom-Studio/cutroom-studio/.env
```
Configure your Supabase PostgreSQL connection string in `.env`:
```env
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

### 3. Launching CutRoom Studio
```bash
cd Cutroom-Studio/cutroom-studio
pip install -r requirements.txt
python -m uvicorn cutroom.api:app --host 0.0.0.0 --port 3000
```
Open **`http://localhost:3000`** in your browser to access the landing page and Studio.

### 4. Database Setup (Supabase)
Run the SQL queries from `Cutroom-Studio/cutroom-studio/supabase_schema.sql` in the Supabase SQL Editor to initialize all tables:
- `users`, `sessions`, `projects`, `clips`, `jobs`, `assets`, `brands`, `presets`, `usage`
- Enable public bucket access for `cutroom-media` in Supabase Storage.

---

## 🛠️ Technology Stack

- **Backend:** FastAPI, Uvicorn, Psycopg 3 (PostgreSQL pooler)
- **AI & Video Processing:** FFmpeg, OpenCV, ONNX Runtime (YuNet face detection), Faster-Whisper
- **Cloud & Storage:** Supabase Storage, PostgreSQL
- **Frontend:** Vanilla JS / ES Modules (CutRoom Studio) & React / Tailwind / Vite (AutoClip)

---

## 📄 License
This project is proprietary and confidential. All rights reserved.
