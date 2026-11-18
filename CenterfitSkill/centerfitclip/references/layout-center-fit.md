# Center Fit layout (9:16)

Canvas 720x1280 (1080x1920 when the content is >1000 px wide). Constants below are for 720 and scale with `k = W/720`.

## Layers
1. **Backdrop:** whole source scaled to *cover* the canvas, blurred - never black bars.
2. **Clip:** the real content rectangle at **full canvas width**, aspect preserved, NEVER cropped to fill. If the content is taller than the allowed height (vertical sources), it is contain-fit (narrower, centered).
3. **Person box (only if detected):** 576x360 (16:10) framed crop of the person, 8 px yellow border, 45 px under the clip.
4. **Text, progress line.**

## Content rectangle
- Landscape source -> whole frame.
- Already center-fit (portrait with blurred bands) -> rows/columns with high Laplacian sharpness averaged over frames; longest run; 3 px trimmed from interior edges only; must be 15-97 % of the frame, else fall back to full frame. This also guarantees burned-in subtitles at the clip's edge are included (a hand-guessed crop clipped them before).

## Vertical placement
- With box: block = clip + 45 + box(376); top = (H - block)/2 + 15. Hook lines sit at clip_top-190 and -123.
- Without box: clip top = (H - clip)/2; hook the same offsets above it. Larger empty backdrop is intentional - don't add filler.
- Platform UI: keep key text out of the bottom ~15 % when possible; teasers sit directly under the block - shift or shorten if they'd collide.

## Keeping people fully visible
- Never crop the clip horizontally. Punch-zoom is temporary (<=10 %) and anchored bottom-center so the facecam/subtitles never leave the frame.
- Person box crop: face width x 3.5, 16:10, centered on face with 22 % extra below (shoulders). Must contain the whole face and head with margin; clamp (shift, don't shrink) at the content border. If the face touches the crop edge -> widen to x 4.0 and re-render.
- Text never overlaps a face.
- Shake uses a 5 % overscan of the *final composite* only, so nothing important sits on the border.

## Person detection edge cases
| Case | Result |
|---|---|
| Facecam over gameplay | box shown (stable cluster) |
| Talking head full frame | box shown; clip + box both show the speaker (acceptable; consider `--intensity clean`) |
| Characters in game/film that move or appear briefly | ignored (<30 % persistence / unstable) |
| Pure voice-over, no human on screen | box hidden, `speaker_offscreen: true` |
| Back-view person / no face | body detector, stricter (>=50 %); otherwise hidden |
| Crowd / many faces | most persistent stable cluster wins; if none persists -> hidden |
| Silent person | still counts as a person (visible human) |
| Audio-only tone/music, no human | hidden |
Always sanity-check against the contact sheet; if the detector is clearly wrong, report it in the delivery note instead of silently overriding.
