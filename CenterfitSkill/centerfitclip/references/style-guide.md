# Style guide - creative direction, psychology, motion, sound

## North star
Subtle, clean, human. The viewer should feel the energy, not see the effects. When unsure, do less. The approved look ("v4 balanced"): Center Fit, enlarged facecam box, small clean hook, reaction-synced punch-zoom with a *light* shake, synthesized whoosh/boom, thin progress line, hard-cut loop.

## Retention psychology (why each element exists)
- **Scroll-stop (0-3 s):** viewers decide in ~1.5 s. Frame 0 must already be bright, readable and intriguing - never fade from black. One question-style hook in the *viewer's language* (e.g. "भाई ये लोग / क्या कर रहे हैं?!"). Curiosity gap > description. Never promise what the video doesn't deliver.
- **Pattern interrupts:** a change every ~2-3 s keeps attention. Use *real* events (loudest reaction, scene cut) - irregular spacing reads as human; evenly spaced pulses read as a preset.
- **Open loops:** teaser at ~30 % ("wait, the real fun is ahead") and ~72 % ("don't miss the last scene") hit the usual drop-off points. The late teaser may only promise something that exists (check the last peak/cut).
- **Goal-gradient:** thin progress line along the bottom - people finish what shows an end.
- **Loop:** end on a hard cut that flows back into the hook; replays count as watch time. No fade-out, no outro card, no "subscribe" banner.
- **Social proof of emotion:** an enlarged, readable face (the person box) sells reactions better than any effect.
- Cover frame/caption are the user's job: recommend the most expressive face frame and a one-line question caption in the delivery note.

## Motion rules (natural camera feel)
| Element | Rule |
|---|---|
| Punch-zoom | on real reaction peaks only; clip +10 %, person box +16 %; ease-out (`exp(-t*6)`); anchored bottom-center so subtitles/person stay in frame |
| Shake | <= 9 px at 720 w (~1.25 %), <= 0.4 s decay, only at peaks, sin/cos mix (never a single-axis wobble), never continuous |
| Glitch / RGB split | <= 0.25 s at peaks, 0.12 s at cuts, shift <= 14 px; never full-time |
| Flash | white 0.85, <= 0.06 s, peaks + cuts only |
| Push-in (clean mode) | <= 4 %, cosine-eased, restarts on each real cut |
| Transitions | keep the source's real cuts (hard cuts); a whoosh may support a cut, no wipes/spins/stock transitions |
| Fades | none at start or end (video). Audio gets 20-30 ms edge fades only to avoid clicks |
If the user says it feels artificial: switch to `--intensity clean` (no shake/glitch/flash/grain) and re-check against the AI-look list.

## AI-look list (never do)
Metronome zooms; shake on every beat; thick neon outlines; emoji/sticker spam; text bigger than ~12 % of frame height; oversaturation (>1.35) or crunchy sharpening; heavy grain; fake captions or invented quotes; generic CTA banners; random stock SFX; text that jitters while being read; two effects firing at once for no reason; fade from black.

## Look
Backdrop: same footage, blurred (sigma 30 @720), darker (-0.25), saturated 1.6 - frames the clip without competing. Clip: contrast 1.15, saturation 1.35, gamma 0.96, light unsharp - maintain skin tones; if faces look orange/plastic, reduce to 1.05/1.1. Yellow 6 px rules above/below the clip as a consistent frame.

## Sound design
Original voice always dominant. Synthesized only (no copyrighted audio): sub-boom at reaction peaks (0.8 vol), pink-noise whoosh landing on cuts (0.9 vol, starts 300 ms before). Chain: highpass 80 Hz -> compressor (-20 dB, 3:1) -> mix -> loudnorm -13.5 -> limiter 0.85 (level off) -> target -14 LUFS (+-2), TP <= -1 dBTP. Optional by the user: trending music at -22 dB under speech - add it in the posting app (licensing).

## Text style
Font Hind Bold (Devanagari + Latin). Hook line 1 white 58 px, line 2 yellow 72 px (@720 w), black outline 6-7 px, slides in 0.25 s, shown 0-3.2 s. Reaction labels 68 px, 1.0 s, alternate yellow/white, from the real peak. Teasers 50 px, 2.6-2.8 s. Keep all text inside 90 % of width, horizontally centered, never over the person's face.
