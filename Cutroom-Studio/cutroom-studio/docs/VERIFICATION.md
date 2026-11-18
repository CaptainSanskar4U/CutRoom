# Verification record

**Environment:** Arena Linux sandbox, 2 CPU cores, Python 3.13, FFmpeg 7.1/libass/libx264, Chromium, SQLite WAL with a separate live worker. An isolated PostgreSQL 17 cluster was tested separately. Test credentials and generated media are not in the source bundle.

## Passed checks

| Test | Verified behavior |
|---|---|
| `python -m pytest -q` | Nine tests: ratio sizes, dynamic crop interpolation and scene changes, corrected SRT across trimmed ranges, direct URL admission, real segment ranking and no-speech mode, burned-in caption pixels, delayed audio alignment, session upgrade and ownership/validation boundaries. |
| `python tests/e2e_live.py` | Account registration, unauthorized media rejection, chunk offset conflict and resume across sign-out/in, 9,780,157-byte source upload, real transcription/tracking/ranking, 4:5 export geometry and saved edit changes, optimistic version conflict, image + text overlays, a half-second cut, edited SRT, background jobs, MP4 download and persistence. |
| `node tests/browser.mjs` | Clicked Upload video, used a real local source, waited for analysis, opened clip editor, selected 4:5, corrected a word, undid/redid, saved, rendered, downloaded actual MP4, verified corrected SRT, reopened the project. No page exceptions. 1440×900 desktop and 390×844 mobile screenshots were reviewed as a separate visual smoke test. |
| `bash scripts/test_postgres.sh` | Disposable Postgres 17: initialized schema, registered an account, loaded a sample, ensured exclusive job claim, rendered H.264, checked HTTP byte ranges and usage, signed out and verified access denied. |
| Direct URL import | Downloaded a real 24,101,047-byte NASA video over an approved TLS connection; the worker analyzed 59.754 seconds and found two clips. A Wikimedia test was rate-limited (429) and surfaced a clear import failure rather than bypassing the host. |
| REA | Bounded public accessibility captures; first-party OpenAPI contract inventory; first-party sample → edit → aspect ratio → save behavior completed. See [evidence matrix](REA-RESEARCH.md). |

### Real source run

- NASA/JSC interview, **185.04 seconds**, 9.78 MB source.
- **537** timed transcript words, **five** ranked cuts, and **349** sampled frames with detected faces in the remuxed preview run. This is measurement of detections, not ground-truth accuracy. Multiple provisional speaker groups were assigned.
- Edited render, **720 × 900**, **12.95 seconds**, 1.59 MB. FFprobe confirmed **H.264** video, **AAC** audio, expected dimensions and duration, and audio/video durations within 0.1 s; the SRT contained the corrected word.
- Caption on/off pixel comparison on a separate real excerpt showed differences in the subtitle region across two times while the source image remained materially unchanged.

## Run the browser and REA checks

With the API and worker already running:

```sh
npm install --prefix .cache/browser playwright
.cache/browser/node_modules/.bin/playwright install --with-deps chromium
PLAYWRIGHT_MODULE="$PWD/.cache/browser/node_modules/playwright/index.mjs" node tests/browser.mjs
```

For REA, install the official package in an isolated prefix using a supported Node version (tested Node 24.22.3, `rea-agents@6.9.0`). No agent setup is required. Pass your installed Chrome-family browser and REA executable to `scripts/rea_audit.py --browser /path/to/chromium --rea /path/to/rea`. Add `--public` to reproduce public reference observations. Audit output is placed in the excluded `.cache` directory. Run browser tests in an isolated test instance if you do not want test projects in the running database.

External provider live credentials, 4K throughput, multi-node storage behavior, full accessibility/language coverage, and maximum size workloads were not verified. No product-parity or accuracy benchmark against OpusClip was performed.

The final release smoke also verified three new prompt-ranked alternatives, a saved branded caption style, project duplication with individual clip thumbnails, and a real 16:9 dual-crop render. Latest REA records: `ev_0515add489857a96ec5e73a1c0e3f7101ab9ebc2d84352cdd18a5dd82016bfb5` (OpenAPI) and `ev_f66de317e4155d5a77d92464b8fecc462e1c38d0b976db322f8581f1dfad368b` (browser edit/save).
