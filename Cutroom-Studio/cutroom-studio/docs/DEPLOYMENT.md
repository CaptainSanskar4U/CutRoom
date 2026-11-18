# Deployment and operations

## Architecture

```text
Browser ─── HTTPS ─── FastAPI API ─────── PostgreSQL (or local SQLite WAL)
                          │                     │
           private POSIX media volume     leased jobs and usage
                          │                     │
                          └──── processing workers ─── FFmpeg / libass
                                        └───────────── Whisper / CAM++ / MiniLM / YuNet
```

- **API:** owner-scoped JSON and same-origin static ES modules. Auth is Argon2id and hashed opaque session tokens. Secure cookies are used under HTTPS; the Arena preview uses partitioned cookies when served from its preview origin. Origin matching protects browser writes. Mark the reverse proxy as trusted and strip client-supplied forwarded headers at the edge.
- **Upload:** each PATCH is limited to 5 MiB. Offset and declared total are validated, chunks are fsynced, and DB offset is advanced under a per-project file lock. A retry truncates uncommitted tail bytes. Always resume with the exact original file; size/name are checked in the browser, not a full source digest.
- **Jobs:** PostgreSQL `FOR UPDATE SKIP LOCKED`, or serialized SQLite writes, claim one job at a time per worker. The worker renews a 90-second lease; interrupted jobs may be reclaimed up to three automatic attempts. Explicit retries reset attempts. Render jobs snapshot the edit before entering the queue. FFmpeg reports encoded output time; model percentages map to actual completed stages and transcript/video positions rather than a timer. Exports include separate SRT and do not mutate the source.
- **Media:** immutable sources/proxies after successful analysis, authenticated Range streaming and private media outputs, and tenant-checked images/fonts. Images are decoded and rewritten as PNG. Media tools restrict demuxing to allowed video containers, disable network protocols on inputs, run with deadlines, and do not shell-evaluate user input.
- **Inference:** files stay local by default. When enabled, hosted copy enrichment receives only excerpts from chosen moments (not original videos). `WHISPER_DEVICE=cpu` is default; CUDA requires a separately built and tested GPU image with matching libraries. Multilingual Whisper works independently of the English MiniLM signal; non-English scoring uses simpler features. Speaker embeddings are clustered, not matched to identifiable names.

## Scaling

1. Single dev host: SQLite and local volume are sufficient. Keep API and worker pointed at the same `CUTROOM_DATA`.
2. Concurrent/remote replicas: use `DATABASE_URL=postgresql://...` and a **shared writable POSIX volume with reliable `flock`, hardlinks and atomic rename**. Use identical paths inside API/worker containers. A local Docker named volume is appropriate for one node. Use a tested shared filesystem when adding hosts; do not put SQLite on NFS. S3 is not implemented.
3. Grow workers independently (`docker compose up -d --scale worker=2`), benchmark per source profile and reserve memory for decoding, PCM, model inference, previews and 4K exports. Increase API replicas only behind a reverse proxy with trusted HTTPS headers. Put high-volume or untrusted workloads in isolated worker instances with disk/CPU/RAM limits.
4. Configure a TLS proxy with bodies of at least 5 MiB (8 MiB for asset uploads), normal idle timeouts for small chunks, and streaming/Range support for video. Do not expose PostgreSQL or metrics publicly. Set `CUTROOM_PUBLIC_ORIGIN` to the one origin serving the browser UI. Place an edge rate limiter in front of public registration/imports.

## Environment and operational checks

| Setting | Effect |
|---|---|
| `DATABASE_URL` | Unset for SQLite; PostgreSQL URI in production. Use URL-safe credentials or percent encode. |
| `CUTROOM_DATA`, `CUTROOM_MODELS` | Private media and database root, model directory. The default ops model cache lives at `.cache/cutroom-models`. |
| `CUTROOM_MAX_BYTES`, `CUTROOM_MAX_SECONDS` | Default 2 GiB, 7,200 seconds, configurable. Processing budgets may be lower for a workspace. A maximum clip edit is 180 seconds. |
| `CUTROOM_THREADS` | Default 2 per worker for model and encoding. Limit replica count to capacity. |
| `CUTROOM_IMPORT_HOSTS` | Exact HTTPS host allowlist. Default: Wikimedia upload plus selected public NASA media hosts. Each redirect must be allowed; all DNS answers must be public and connections are pinned to resolved addresses with normal TLS verification. Use an egress firewall too. |
| `CUTROOM_GUEST` | `0` disables guest account creation. |
| `CUTROOM_PUBLIC_ORIGIN`, `CUTROOM_SECURE_COOKIE` | Public origin and cookie policy. Set `CUTROOM_SECURE_COOKIE=1` behind production TLS. |
| `CUTROOM_SCORE_WEIGHTS` | Optional JSON object keyed by hook, engagement, completeness, emotion, density, independence, confidence, duration, ending. Nonnegative weights are normalized. |
| `CUTROOM_METRICS_ENABLED` | `1` enables `/metrics`: live workers, queue counts per state/kind and free media bytes. Scrape internally only. |
| `CUTROOM_LLM_ENDPOINT`, `CUTROOM_LLM_API_KEY`, `CUTROOM_LLM_MODEL` | Opt-in OpenAI-compatible **chat completions URL**, key and model. Failures fall back to local extractive copy. Review provider privacy and timeout settings before enabling. |

Preview age-based cleanup with `python -m scripts.maintain`; add `--apply` only after reviewing your retention and backup policy. It expires old guest workspaces without active sessions or queued/running jobs and removes expired sessions, not registered accounts.

Application logs are stage/error oriented, not transcript logs. Monitor readiness, queue lag, repeated failures, idle worker count and disk occupancy. In front of a public deployment, avoid recording query strings, session cookies or private source URLs in reverse-proxy logs. Back up the database and private-media volume together; test restore and owner access. Do not include runtime media or secrets in images and source archives.

## Stripe (optional)

1. In Stripe, create a recurring Studio price and enable Customer Portal.
2. Set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`, and `CUTROOM_PUBLIC_ORIGIN`. Billing remains hidden if credentials are absent.
3. Register `/api/billing/webhook` for `customer.subscription.created`, `.updated`, and `.deleted`. The API checks signature age/signature and records event IDs idempotently. Use Stripe test mode to verify Checkout, activation, cancellation and retries before exposing real checkout. The app never collects payment-card details.

Default monthly allocation: 30 guest, 240 Creator, 1,500 Studio processing minutes. New source analysis counts against the allocation; examples/re-ranking/exports do not. Existing projects remain accessible when a subscription changes. Deleting a project does not refund already consumed processing time.

## Production gates still required

This workspace verifies core workflows locally and an ephemeral Postgres setup. It does **not** prove sustained load, multi-node storage behavior, abuse resistance, codec coverage, official platform integrations, or operational compliance. Before serving external traffic: load-test representative 2 GiB and long uploads; isolate codec/font decoders; configure rate limits, media retention, backup/restore and observability; add an email verification/reset flow and account lifecycle operations as required; test Stripe/LLM environments with your keys; and review redistribution/licensing. Ship data retention/deletion policies before enrolling external users. Production billing, CUDA, 4K throughput, Docker build/pull, social publishing and enterprise account workflows are not marked verified here.
