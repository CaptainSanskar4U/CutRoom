# Cutroom Studio

**A working, independently implemented AI video clipping and editing workspace.** Upload a video, find editable short clips with a local model pipeline, adjust the cut and captions, and download a real MP4.

If you're using the live preview, open one of the **Recent projects** samples to get straight to the editor, or choose **Upload video**. Samples use real footage, captions, tracking and analysis. Guest work is private to that browser session; create an account from Settings to keep it across devices on the same deployment.

## Run locally

Requires Python **3.13**, Linux (or a POSIX host with FFmpeg and file locking), and FFmpeg with `libx264`, `libass`, and AAC. On Debian:

```sh
sudo apt-get install ffmpeg fontconfig fonts-dejavu-core fonts-liberation fonts-noto-core
bash scripts/setup.sh
```

Model bootstrap verifies about 200 MB of downloads. A first run may be slower while models warm up. You do **not** need an AI API key. In separate terminals:

```sh
make worker
make serve
```

Open `http://localhost:3000`. `GET /healthz` checks the API/database; `GET /readyz` also checks for a live worker. `data/` holds local SQLite and private media. Set `CUTROOM_DATA` to change the data directory; leave it in the same location for both processes. The API has Swagger at `/api/docs`; the published OpenAPI JSON is `/api/openapi.json`.

## What works

| Area | Implementation |
|---|---|
| Workspace | Private guest workspaces, Argon2id email/password accounts, HTTP-only opaque sessions, saved projects, rename, duplicate, delete, usage, defaults, and brand kits. |
| Inputs | Resumable chunked uploads, per-workspace size/usage limits, FFprobe validation, owned browser previews, allowlisted direct HTTPS import. No downloading from private or platform watch pages. |
| AI clips | Faster-Whisper transcription with word timing and language detection; CAM++ speaker clustering; English MiniLM semantics plus boundary, lexical, delivery, and visual signals. Optional focus, four length targets, explainable Cut Score, alternate ranking, extractive titles, descriptions, hooks and social copy. Visual fallback for non-speech sources. |
| Editor | Live preview; waveform timeline, trims and seek; caption text/timing, preset and typography controls; undo/redo; face/motion tracking, crop, fit and two-pane framing; 9:16, 16:9, 1:1 or 4:5; text/images, logos, fonts, fades, volume, watermark, reviewed filler-word/word-gap cuts. |
| Delivery | Persisted background jobs, render snapshots, accurate FFmpeg progress, retries, batch queue, export history, preview, MP4 and SRT downloads. 480p, 720p, 1080p and 2160p on the short side (4K can upscale). |
| Deployment | SQLite locally or PostgreSQL, independent API and workers, persistent shared media, health checks, optional Prometheus-format metrics, optional Stripe Checkout and portal. |

Cut Score is a ranking aid, **not** a prediction of reach. Speaker labels and active-face selection are estimates; review the result or use manual framing. The browser preview uses the same timing and crop keyframes, but font metrics/line breaks can vary by platform. Export preview plays the authoritative rendered MP4.

## Deploy

```sh
cp .env.example .env
# Fill POSTGRES_PASSWORD with a long, URL-safe value (e.g. openssl rand -hex 32).
docker compose up --build -d
```

The default compose port is bound to loopback. For a public deployment, put TLS in front, set `CUTROOM_PUBLIC_ORIGIN=https://your-domain`, configure trusted forwarded headers and persistent backups, and keep PostgreSQL internal. See [deployment and operations](docs/DEPLOYMENT.md) for scale, monitoring, credentials, sandboxing, and production gates.

## Verify

```sh
.venv/bin/pip install -r requirements-dev.txt
make test
make e2e                  # API and worker must already be running
bash scripts/test_postgres.sh # Requires local Postgres 17 binaries
```

The live test uploads a real 3:05 source, reconnects to resume it, checks ownership, verifies downloaded H.264/AAC with FFprobe, and signs back in to verify persistence. The core suite also checks burned-in caption pixels. See [verification record](docs/VERIFICATION.md).

## Scope and reference

[REA research and evidence](docs/REA-RESEARCH.md) records the upstream repository, feature-level evidence, and public/private boundary. Cutroom is not affiliated with OpusClip. No proprietary code or assets were copied. It is a functional core application, **not** a claim of commercial feature parity or better highlight quality. Native social scheduling, platform-specific importers, external stock/generative B-roll, NLE XML, and enterprise team controls are not implemented. Billing and hosted LLM copy enrichment require operator credentials and were not exercised with a live provider. [Media, model, font and tool credits](docs/THIRD-PARTY.md).
