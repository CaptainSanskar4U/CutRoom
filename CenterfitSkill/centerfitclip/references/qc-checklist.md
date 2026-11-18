# QC checklist - nothing ships until every box is ticked

## A. Automatic (`scripts/qc.py` must exit 0)
9:16 | H.264/yuv420p | AAC present | duration = source (+-0.15 s) | -16..-12 LUFS | TP <= -1 dBTP | first frame not black | no black/frozen segments | second box == auto-detection | clip inside frame and horizontally centered.

## B. Framing (open the contact sheet + 3 extra frames: 1 s, mid, last second)
- [ ] Clip is full width, not cropped to fill; burned-in subtitles fully visible, not clipped.
- [ ] Person (if any) fully visible in the clip AND in the box; face has margin; not cut at the box edge.
- [ ] Box present only if a person is really on screen; absent otherwise; no empty placeholder.
- [ ] Nothing important in the outer 5 % (shake overscan) or hidden behind platform UI where avoidable.

## C. Text
- [ ] Hook visible at frame 0, <= 2 lines, correct script/language, no typos, not oversized, not on faces.
- [ ] Reaction labels/teasers match what actually happens at that time; late teaser promise is true.
- [ ] No overlapping text; nothing cut at the edges; Devanagari shaping correct.
- [ ] No double subtitles; captions (if any) are accurate and in sync.

## D. Motion & look (watch the video, or step frames around each peak/cut)
- [ ] Zoom/shake only at real peaks, short, eased, no jitter after the effect ends.
- [ ] No effect > 0.4 s; no two heavy effects stacked; no metronome rhythm.
- [ ] Colors natural (skin not orange/plastic), no banding/blockiness, no soft/blurry hook text.
- [ ] No fade-in/out; ending hard-cuts and loops cleanly into the start.
- [ ] Overall feel: "a careful human edited this". If not -> `--intensity clean`.

## E. Audio
- [ ] Voice clear and dominant; SFX supportive, in sync with cuts/peaks, no clicks at start/end.
- [ ] No clipping, no silence gaps, no double audio.

## F. Delivery note (always include)
What was done | assumptions (generic labels? no transcript? detector uncertainty?) | person-box decision + reason | improvement tips (cover frame, caption, trending sound, post time) | offer one targeted fix.
