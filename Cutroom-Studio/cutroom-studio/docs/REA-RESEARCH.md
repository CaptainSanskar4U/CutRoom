# REA-led product evidence and reconstruction

**Date:** 2026-11-18. **Reference:** OpusClip public surfaces. **Implementation:** Cutroom, an independent application.

## Repository investigation

The empty repository placeholder was resolved to [morluto/rea](https://github.com/morluto/rea), commit `675287517c98c702ee88ad036c5e3b8dd4bcc7a7`. The checkout was inventoried (9,223 tracked paths). The review focused on the relevant architecture diagram, CLI dispatch and packaging, browser scenario contract, evidence levels, and provider/source boundaries; it was not a line-by-line audit of every platform provider and test. `rea-agents@6.9.0` ran on Node 24.22.3 via its isolated CLI, without installing a host agent plugin or altering agent settings. MIT attribution: [REA-MIT.txt](licenses/REA-MIT.txt).

REA provides a CLI/MCP adapter, provider orchestration, and bounded evidence capture. It is **not** a video app, a video analysis model, or a source of reusable upload/editor code. We used `capture-browser-scenario` for public accessibility evidence and first-party behavioral acceptance, and `inspect-api-contract` on Cutroom’s OpenAPI. These checks are reproducible with `scripts/rea_audit.py`. REA is a development/verification tool, not a production dependency. Native/decompilation, bundled-JavaScript capture, traffic replay, production accounts, and hidden routes were outside scope.

## Workflow: acquire → classify → specify → rebuild → verify

- **Acquire/observe:** clean browser instances, public URLs only, accessibility trees and final URLs only. No request/response bodies, network headers, HAR, source maps, scripts, or credentials. Read official help pages to cover documented editor states without accessing a private workspace.
- **Classify:** `Observed` means public UI evidence. `Documented` means vendor help/marketing, not a verified implementation detail. `Inferred` means a design expectation. `Unknown` means it was not observed and is not asserted.
- **Specify:** make one feature-level contract at a time; each is observable and testable. Do not reuse OpusClip copy, imagery, branding, or implementation.
- **Rebuild:** independent persistence, processing, UI and exports. Architect the owner, job, media, edit and export boundaries before wiring UI controls.
- **Verify:** reacquire first-party UI and API contract evidence with REA; test actual media/encoding with FFprobe, browser tests and HTTP integration tests. REA evidence alone does not verify a worker's output or equivalence to OpusClip.

## Feature evidence matrix

| Workflow | Reference evidence | Independent design / acceptance |
|---|---|---|
| Getting started | **Observed** [public site](https://www.opus.pro/). Dashboard requires ordinary sign-in; the public fetch redirected to login. **Documented** [getting started](https://help.opus.pro/docs/article/introduction-to-opusclip) and [supported sources](https://help.opus.pro/docs/article/what-import-sources-does-opusclip-support). | Guest samples, Argon2id email/password accounts, resumable local uploads, and allowlisted direct HTTPS media. Verify auth rotation, last-chunk resume, 401/404 ownership. No watch-page scraping. |
| Processing and results | **Observed** public [result walkthrough](https://help.opus.pro/docs/article/get-clips-faq-1) page. **Documented** title, description, transcript, ranked results and chronological sorting. **Unknown** authenticated screen transitions, internals, job timing. | Worker leases and retries; real bytes, model-derived stage milestones, measured encoding time; listen, rank, edit, or regenerate. |
| Scoring | **Documented** [Virality Score](https://help.opus.pro/docs/article/virality-score) discusses hook, flow, value, trend. **Unknown** model, weights, calibration, actual predictive accuracy. | Cut Score is only editorial ranking. Nine inspectable components, traceable timestamp ranges, configurable weights, no predicted views. |
| Reframe | **Documented** [subject tracking](https://help.opus.pro/docs/article/subject-tracking) and [manual crop](https://help.opus.pro/docs/article/how-to-manually-reframe-content). **Unknown** private model and active-speaker accuracy. | YuNet faces, approximate mouth-motion emphasis, shot changes and motion fallback; four ratios, manual controls, fit and a two-pane crop. Replay the same keyframe geometry in preview and FFmpeg. |
| Captions and trimming | **Documented** [caption editing](https://help.opus.pro/docs/article/captions-and-emojis) and [speech cleanup](https://help.opus.pro/docs/article/speech-cleanup). **Inferred** time edits and cuts belong with the source transcript. | Word-level alignment, editable text and timings, styles, selected filler/pause removal, timeline trims and undo/redo. Validate edited word appears in SRT and captions change rendered pixels. |
| Brand and layers | **Documented** [recipes](https://help.opus.pro/docs/article/how-to-use-recipes), [AI/stock B-roll](https://help.opus.pro/docs/article/ai-broll), [pricing feature matrix](https://www.opus.pro/pricing). | Save caption/font/logo/background kits, add text and timed user-owned image overlays, extractive B-roll search ideas. No licensed stock search or generative B-roll. |
| Delivery and account | **Documented** [MP4/4K](https://help.opus.pro/docs/article/download-and-post-in-4k), [NLE export](https://help.opus.pro/docs/article/import-to-davinci-resolve), [plans](https://help.opus.pro/docs/article/plans-and-credits). | Immutable job snapshots, H.264/AAC MP4, SRT, resolution/quality, persistent export history, owner-only file ranges; local usage and optional Stripe. No scheduler, direct social publishing or NLE XML. |

## Concrete observations retained

| REA operation | Evidence ID | What it supports |
|---|---|---|
| Public homepage accessibility | `ev_a03e1ed88e73855a0e5d7693d64272ad4c9b3e1248c052ed63fb6294b5baf0c2` | Product positioning and public entry points |
| Public results help accessibility | `ev_764112d58424cecacbbe928f38ea94c4084e0a454b2b42197f3706c457e0ae39` | Public result feature documentation |
| Initial dashboard navigation | `ev_2139d31ab0ecf6db62c3bfa608b759c46f29565b93246c995f2ee2a388a48c42` | App shell only; sign-in redirect separately confirmed by ordinary public fetch |

No authenticated interaction, loading or render timing on OpusClip is claimed. Public functionality is not evidence of exact back-end behavior or parity.

The repeatable audit also observed the [public scoring help](https://help.opus.pro/docs/article/virality-score) (`ev_510841baf821e8d445756e6da684638e644f26c9b562a62d4844dd787fe08ff6`), [public subject-tracking help](https://help.opus.pro/docs/article/subject-tracking) (`ev_823b9077a866898a33f21a96d21be80613d36728aa542c9adb0f0fb96b675f4b`), and [public captions help](https://help.opus.pro/docs/article/captions-and-emojis) (`ev_4411b29269f3e32b1803c2b1a032a33f6af29576fdee66b569987afb0c4a0191`). The first-party sample → editor → square crop → save scenario completed every step (`ev_33a335bd6f66d1caaed4353c774900215f6acb79812022b4b5b68e3418f7d96d`). These are evidence identifiers, not claims that the original product was copied or benchmarked.
