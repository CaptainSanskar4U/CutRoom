---
name: fullscreenreframe
description: Full Screen Smart Reframing & Intelligent Cropping Skill - converts a 16:9 (or any non-9:16) video into a professionally framed 9:16 FULL SCREEN (crop-to-fill, no blur bars) short. Use whenever the user wants a full-screen / fill-the-screen vertical clip. Understands the whole scene (speaker, second person, objects, screens, background action) before choosing the crop; person tracking is ONE input, never the only one. Hold-first camera path, eased pans, speaker-turn cuts, mandatory QC with a "what was cropped out" report. Full Screen only - for blurred-backdrop Center Fit use the centerfitclip skill.
---

# Full Screen Smart Reframing & Intelligent Cropping Skill

**One job:** original video in -> 1080x1920 full-bleed 9:16 clip out, framed like a human editor would: the right things inside the window, calm camera, no stretched pixels.

**Most important rule:** NEVER sacrifice important scene information just to keep a face centered. Understand the whole scene first, then decide what belongs in the 9:16 window.

**Scope:** framing only (crop position, hold/pan/cut timing). Hooks, captions, SFX belong to other skills (e.g. centerfitclip); run them AFTER reframing. If the user wants blurred bars + uncropped footage, say this skill doesn't do that and stop.

## Requirements
`ffmpeg`/`ffprobe`, Python 3, `numpy`, `opencv-python-headless<5`. Optional (use if present, otherwise use the fallbacks stated below): `ultralytics` (YOLO objects), `faster-whisper` (transcript for deictic boosts), any VAD (`webrtcvad`/`silero`) for speaker activity.

## 1. Geometry (read first)
A 9:16 window cut from 16:9 is only **~31.6 % of the source width** (607 px of 1920) at full height. So the whole problem is choosing a horizontal position `x(t)` for a narrow window. Zoom-in is NOT free: it shrinks the window further and loses more.

```python
def window_size(src_w, src_h, ar=9/16, zoom=1.0):
    if src_w / src_h >= ar:      # wider than target: full-height window, slide in x
        h = src_h / zoom; return h * ar, h, "x"
    w = src_w / zoom             # narrower than target: full-width window, slide in y
    return w, w / ar, "y"
```
Rules: scale x and y by the same factor (never stretch); output 1080x1920; default `zoom = 1.0`. If the source already has blurred side bands (a center-fit export), crop to the real content rectangle first. Content that cannot physically fit in W is handled by section 6, never by distortion.

## 2. Workflow (in order)
1. **Probe** - fps, size, duration, audio present?
2. **Shots** - detect hard cuts (histogram), see 3.1. Every shot is framed independently; a cut is a free place to change framing.
3. **Analyze** each shot at 4 fps: people (head + torso) + tracking, speaker activity, objects/screens, action, saliency. Output `analysis.json` (schema in section 9).
4. **Look at the contact sheet** (1 frame per ~2 s with the proposed window drawn) before trusting the numbers.
5. **Plan** - per shot: weighted importance -> static crop -> add moves only when needed (sections 5-7). Output `crop_plan.json`.
6. **Render** - single pass, sub-pixel crop, audio copied from source (section 8).
7. **QC gate** (section 10). Fix and re-plan until it passes. Deliver with the "what was cropped out" report.

## 3. Scene understanding

### 3.1 Shot detection
```python
import cv2, numpy as np

def is_cut(prev_bgr, cur_bgr, thr=0.55):
    h = [cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256]) for f in (prev_bgr, cur_bgr)]
    for x in h: cv2.normalize(x, x)
    return cv2.compareHist(h[0], h[1], cv2.HISTCMP_CORREL) < thr
```

### 3.2 People: detect, then track (guidelines)
- Detect **faces** (Haar frontal + profile, also run profile on the horizontally flipped frame; or YuNet if the model file is available) at <= 960 px width, min face width 2.5 % of frame width. Add HOG/YOLO **person** only when no face is found (back to camera, small figures).
- Faces are lost when people look down/turn: **do not drop a track for 8 samples (2 s)**. Coast on the last position. This stops the crop jumping to "no person".
- Build two items per person: **head** (face box expanded 40 % each side, hard-cut-protected) and **torso** (face width x 3.2 wide, 4 face-heights tall, coverage only).
- Never trust one frame. A person counts only after >= 2 hits; a person "exists in the shot" if present in >= 30 % of samples.

```python
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROF = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")

def iou(a, b):
    iw = max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0])); ih = max(0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))
    inter = iw * ih; u = a[2]*a[3] + b[2]*b[3] - inter
    return inter / u if u else 0.0

def nms(boxes, thr=0.4):
    out = []
    for b in sorted(boxes, key=lambda b: -b[2]*b[3]):
        if all(iou(b, o) < thr for o in out): out.append(b)
    return out

def detect_faces(bgr, min_face=0.025):
    h, w = bgr.shape[:2]; s = 960 / w if w > 960 else 1.0
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if s != 1.0: g = cv2.resize(g, None, fx=s, fy=s)
    mf = max(20, int(min_face * g.shape[1])); boxes = []
    for (x, y, fw, fh) in FACE.detectMultiScale(g, 1.1, 5, minSize=(mf, mf)): boxes.append((x/s, y/s, fw/s, fh/s))
    for (x, y, fw, fh) in PROF.detectMultiScale(g, 1.1, 5, minSize=(mf, mf)): boxes.append((x/s, y/s, fw/s, fh/s))
    gf = cv2.flip(g, 1)
    for (x, y, fw, fh) in PROF.detectMultiScale(gf, 1.1, 5, minSize=(mf, mf)): boxes.append(((g.shape[1]-x-fw)/s, y/s, fw/s, fh/s))
    return nms(boxes)

class Tracker:
    def __init__(self, max_age=8, thr=0.15):
        self.tracks, self.nid, self.max_age, self.thr = {}, 0, max_age, thr
    def update(self, boxes):
        free = list(range(len(boxes)))
        for tid, tr in list(self.tracks.items()):
            best, bi = 0.0, None
            for i in free:
                v = iou(tr["box"], boxes[i])
                if v > best: best, bi = v, i
            if bi is not None and best >= self.thr:
                tr["box"] = tuple(0.6*n + 0.4*o for n, o in zip(boxes[bi], tr["box"]))
                tr["age"] = 0; tr["hits"] += 1; free.remove(bi)
            else:
                tr["age"] += 1
                if tr["age"] > self.max_age: del self.tracks[tid]
        for i in free:
            self.tracks[self.nid] = {"box": boxes[i], "age": 0, "hits": 1}; self.nid += 1
        return {k: v for k, v in self.tracks.items() if v["hits"] >= 2}
```

### 3.3 Who is the speaker
Combine, per track, smoothed over 0.8 s:
1. **Mouth motion**: mean abs frame-diff in the lower 40 % of the face box.
2. **Voice activity** (VAD on source audio): speaker candidates only count while speech is active.
3. Tie-break: larger, more frontal face; the person who spoke last.

```python
def mouth_energy(prev_g, g, box):
    x, y, w, h = [int(v) for v in box]; ys = y + int(0.6*h)
    a, b = prev_g[ys:y+h, x:x+w], g[ys:y+h, x:x+w]
    return float(np.mean(cv2.absdiff(a, b))) if a.shape == b.shape and a.size else 0.0
```
**Hysteresis:** the active speaker changes only after the new candidate leads for >= 0.7 s. Ignore back-channels shorter than 1.0 s ("hmm", "yeah", a laugh): keep the current framing.
No audio / no VAD: use mouth motion alone and say so in the delivery note.

### 3.4 Important objects, screens, action, background
Score every non-person candidate; keep it only if it earns weight.

| Candidate | How to find it | Notes |
|---|---|---|
| Object (YOLO available) | detections: laptop, tv, monitor, cell phone, book, bottle, car, animal, instrument, etc. | class prior x size x persistence |
| Screen / slide / whiteboard / product box (no YOLO) | `screen_boxes()` below: convex 4-gon, 3-60 % of frame, aspect 0.4-3 | high luminance variance = content |
| Action (something happening) | frame-diff blobs **outside** person boxes (`action_boxes()`) | ignore if motion > 35 % of frame (camera move/cut) |
| Salient region | spectral-residual saliency | weak signal, only breaks ties |
| Deictic boost | transcript within +-2 s says "look at this / here / yeh / dekho / ye dekho" | x1.5 on the best non-person candidate in that window |
| Burned-in captions / logos / watermarks | static text strips at frame edges | do NOT weight; flag "re-caption after reframing" |

```python
def screen_boxes(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY); H, W = g.shape
    e = cv2.dilate(cv2.Canny(g, 60, 160), np.ones((3, 3), np.uint8)); out = []
    for c in cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]:
        p = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(p) == 4 and cv2.isContourConvex(p):
            x, y, w, h = cv2.boundingRect(p)
            if 0.03 < w*h/(W*H) < 0.6 and 0.4 < w/h < 3.0: out.append((x, y, w, h))
    return nms(out)

def action_boxes(prev_g, g, person_boxes, thr=18, min_area=0.004):
    H, W = g.shape
    d = cv2.absdiff(cv2.GaussianBlur(prev_g, (5, 5), 0), cv2.GaussianBlur(g, (5, 5), 0))
    m = ((d > thr) * 255).astype(np.uint8)
    for (x, y, w, h) in person_boxes:
        m[int(max(0, y-h*0.3)):int(y+h*4), int(max(0, x-w)):int(x+2*w)] = 0
    if m.mean() / 255 > 0.35: return []
    m = cv2.dilate(m, np.ones((15, 15), np.uint8), iterations=2)
    out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, w, h = cv2.boundingRect(c)
        if w*h/(W*H) >= min_area: out.append((x, y, w, h))
    return out

def spectral_saliency(gray):
    s = cv2.resize(gray, (128, 72)).astype(np.float32)
    f = np.fft.fft2(s); lg = np.log(np.abs(f) + 1e-6)
    sr = lg - cv2.blur(lg, (3, 3))
    m = np.abs(np.fft.ifft2(np.exp(sr + 1j*np.angle(f)))) ** 2
    m = cv2.GaussianBlur(m, (0, 0), 2.5)
    return cv2.resize(m / (m.max() + 1e-9), (gray.shape[1], gray.shape[0]))
```
**Background relevance test:** a background region is relevant only if it is (a) a screen/slide/text block, (b) persistent action not caused by the speaker, or (c) a second person facing/reacting to the speaker. Static clutter, blurred bokeh, empty wall = irrelevant (weight 0).
No YOLO installed: rely on `screen_boxes` + `action_boxes` + saliency and state "object detector unavailable" in the delivery note.

### 3.5 Importance weights (the priority order is encoded here)

| Item | Weight | must-keep |
|---|---|---|
| Active speaker head | 1.00 | yes |
| Active speaker torso | 0.40 | no |
| Second participant (in conversation / spoke in last 5 s / reacting) head | 0.70 | yes, if it fits |
| Key object / screen / demo (class prior or deictic boost) | 0.80 | yes |
| Action region (persistent >= 1 s) | 0.60 | no |
| On-screen text/graphic that matters | 0.50 | no |
| Other visible people (not involved) | 0.25 | no |
| Salient background | 0.25 | no |
Multiply object/action/text weights by `min(1, visible_ratio / 0.4)` (persistence in the shot).

```python
from dataclasses import dataclass
@dataclass
class Item:
    kind: str                  # head|body|object|action|text|salient
    x0: float; y0: float; x1: float; y1: float
    weight: float
    must: bool = False
    label: str = ""
```

## 4. Intelligent crop selection

Hard constraints (checked before scoring): never slice through an active speaker's head; never place a window edge within 6 % of W of a head; do not cut a must-keep object in half if a position exists that keeps it whole. Prefer edges that fall in "valleys" of the importance profile (empty wall, gap between people), never through faces or objects.

```python
CFG = dict(step=8, face_cut_penalty=3.0, obj_cut_penalty=1.2, edge_margin=0.06, comp_w=0.15,
           move_cost=0.3, deadzone=0.08, dwell=0.7, min_hold=1.5, min_move=0.5,
           max_speed=0.5, jump_dist=0.6, anticipation=0.2)

def solve_x(items, src_w, W, cfg=CFG, prev_x=None, spk=None):
    best_x, best_s = 0.0, -1e9
    for x in np.arange(0, max(1, src_w - W + 1), cfg["step"]):
        s = 0.0
        for it in items:
            inter = max(0.0, min(it.x1, x + W) - max(it.x0, x)) / max(it.x1 - it.x0, 1.0)
            s += it.weight * inter
            if it.kind == "head":
                if 0.0 < inter < 1.0: s -= cfg["face_cut_penalty"] * it.weight
                elif inter == 1.0:
                    m = min(it.x0 - x, x + W - it.x1) / W
                    if m < cfg["edge_margin"]: s -= (cfg["edge_margin"] - m) * it.weight * 4
            elif it.must and 0.0 < inter < 1.0:
                s -= cfg["obj_cut_penalty"] * it.weight
        if spk is not None:   # composition: speaker near the middle, slight room toward where they look
            s -= cfg["comp_w"] * abs(((spk.x0 + spk.x1) / 2 - x) / W - 0.5)
        if prev_x is not None:
            s -= cfg["move_cost"] * abs(x - prev_x) / W
        if s > best_s: best_s, best_x = s, float(x)
    return best_x, best_s

def y_for_zoom(items, H_src, H_win):   # only used when zoom > 1: eyes at ~38 % from top, headroom kept
    heads = [i for i in items if i.kind == "head" and i.must]
    if not heads: return (H_src - H_win) / 2
    cy = sum((h.y0 + h.y1) / 2 for h in heads) / len(heads)
    return float(min(max(0, cy - 0.38 * H_win), H_src - H_win))
```

## 5. Multi-person framing logic

| Situation | Decision |
|---|---|
| 1 person, nothing else important | head+torso in window, speaker slightly off-center toward the side they face (lead room) |
| 1 person + important object/screen **within W** | keep both; center on their union, speaker head must stay whole |
| 2 people, union of heads **<= 0.94 W** | keep both, speaker gets the larger share; this is the default conversation shot |
| 2 people, union **> W** | hold on the active speaker; **hard cut** to the other at the start of their turn (multi-cam style). Never slow-pan back and forth |
| 3+ people | speaker + nearest neighbor(s) that fit; others dropped (they are weight 0.25) |
| Person + important background behind them | because W is narrow, keep the background item **if it lies in the same x-range**; otherwise see section 6 |
| Speaker off-screen (voice-over) | frame the most important object/action; no face logic |
| Person moves | moves only if they leave the dead-zone for >= dwell; then one eased pan |

Greedy must-keep resolution (highest weight first, add while the union still fits):
```python
def resolve_must_keep(items, W, fit=0.94):
    kept, dropped = [], []
    for it in sorted([i for i in items if i.must], key=lambda i: -i.weight):
        lo = min([k.x0 for k in kept] + [it.x0]); hi = max([k.x1 for k in kept] + [it.x1])
        (kept if hi - lo <= W * fit else dropped).append(it)
    for it in dropped: it.must = False; it.weight *= 0.3
    return kept, dropped          # dropped goes into the "cropped out" report
```

## 6. When it cannot all fit
Order of resolution (stop at the first that works):
1. Drop the lowest-weight member (usually a non-speaking person) - done by `resolve_must_keep`.
2. **Time-slice**: if the speaker and an important object/second person alternate with segments >= 2.5 s, plan segments with a cut or one eased pan between them (section 7).
3. **Choose by weight for that shot** (speaker 1.0 beats object 0.8 unless the narration points at the object -> deictic boost flips it for that window).
4. If the dropped must-keep weight is > 50 % of total must-keep weight for > 30 % of the runtime: **do not ship silently**. Add `"recommend_center_fit": true` to the plan and tell the user the clip loses too much in full screen. (Never solve it by stretching or squashing.)

## 7. Dynamic reframing and smooth motion

**Default = static crop per shot.** Compute the time-averaged importance for the shot -> `solve_x` once. Then check each 4 fps sample: if a must-keep item is cut or leaves the window in >= 10 % of samples, add moves with the rules below. Otherwise the shot stays locked.

Rules:
- **Dead-zone:** ignore target changes within +-8 % of W.
- **Dwell:** a new target must persist >= 0.7 s before the camera moves.
- **Min hold:** >= 1.5 s between moves; max 3 moves per 10 s.
- **Easing:** smoothstep; duration = `max(0.5 s, distance / (0.5 W per second))`; never linear, never overshoot.
- **Anticipation:** offline, so start the move 0.2 s before the change is visible (speaker's first word).
- **Cut instead of pan:** if the move is > 0.6 W and it is a speaker turn -> instant jump on the first word (1 frame). Long fast pans look amateur.
- **No zoom** by default. A single static punch-in (<= 1.25x, applied from the shot start, not animated) is allowed only when the subject is tiny and nothing important is lost. No continuous zoom, no shake.
- **Shot cuts:** reset `prev_x`; framing for the new shot is chosen fresh (no pan across a cut).
- Never move during a dead stretch of nothing happening.

```python
def plan_keyframes(samples, W, fps, cfg=CFG):
    """samples: [(t, x_target)] inside ONE shot. Returns keyframes [(t, x)]; hold between equal-x keyframes."""
    cur = samples[0][1]; kf = [(samples[0][0], cur)]; pending = None
    for t, x in samples[1:]:
        if abs(x - cur) <= cfg["deadzone"] * W: pending = None; continue
        if pending is None or abs(x - pending[1]) > cfg["deadzone"] * W: pending = (t, x); continue
        if t - pending[0] >= cfg["dwell"] and pending[0] - kf[-1][0] >= cfg["min_hold"]:
            start = max(kf[-1][0], pending[0] - cfg["anticipation"]); dist = abs(x - cur)
            dur = 1.0 / fps if dist > cfg["jump_dist"] * W else max(cfg["min_move"], dist / (cfg["max_speed"] * W))
            kf += [(start, cur), (start + dur, x)]; cur = x; pending = None
    return kf

def x_at(kf, t):
    if t <= kf[0][0]: return kf[0][1]
    for (t0, x0), (t1, x1) in zip(kf, kf[1:]):
        if t0 <= t < t1:
            u = (t - t0) / max(t1 - t0, 1e-6); u = u * u * (3 - 2 * u)
            return x0 + (x1 - x0) * u
    return kf[-1][1]
```

## 8. Render (single pass, sub-pixel, no stretch)
Integer-pixel crops make pans look steppy. Use an affine warp (sub-pixel) and pipe to ffmpeg; copy audio from the source.

```python
import subprocess
def render(src, plan, out, W, Hwin, fps, size=(1080, 1920)):
    cap = cv2.VideoCapture(src); s = size[1] / Hwin
    ff = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps),
        "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        t = i / fps; x = x_at(plan["kf"], t); y = plan.get("y", 0.0)
        M = np.float32([[s, 0, -x * s], [0, s, -y * s]])
        ff.stdin.write(cv2.warpAffine(fr, M, size, flags=cv2.INTER_LANCZOS4).tobytes()); i += 1
    ff.stdin.close(); ff.wait()
```
Upscaling 1080p -> 1920 high is soft by nature: Lanczos only, no heavy sharpening. For long videos, process per shot with the same function and `concat` losslessly.

## 9. Data contracts
`analysis.json`: `{fps, src_w, src_h, shots:[{start,end}], samples:[{t, shot, items:[{kind,x0,y0,x1,y1,weight,must,label}], speaker_track}], flags:{has_audio, yolo, vad}}`
`crop_plan.json`: `{W, Hwin, zoom, shots:[{start,end,kf:[[t,x]...], y, strategy:"static|moves|cuts", reasons:[...]}], cropped_out:[{t0,t1,label,weight}], recommend_center_fit:false}`

## 10. QC gate (automatic + manual)
Automatic (fail = re-plan):
- `head_cut_rate == 0`: for every sample, every must-keep head >= 90 % inside the window.
- `must_keep_coverage >= 0.95` of samples (excluding items logged as dropped).
- `hold_ratio >= 0.70` (share of runtime with the camera not moving).
- `max_speed <= 0.5 W/s`, moves per 10 s <= 3, no animated zoom, zoom factor <= 1.25.
- Output exactly 1080x1920; `scale_x == scale_y` (no stretch); A/V duration difference <= 40 ms.
- No dropped item with weight > 0.6 unless the user was told (`cropped_out` report).

```python
def motion_stats(kf, W, dur):
    moves = [(t0, t1, abs(x1 - x0)) for (t0, x0), (t1, x1) in zip(kf, kf[1:]) if x1 != x0]
    moving = sum(t1 - t0 for t0, t1, _ in moves)
    vmax = max([d / W / max(t1 - t0, 1e-6) for t0, t1, d in moves] + [0.0])
    return {"hold_ratio": 1 - moving / max(dur, 1e-6), "max_speed_W_per_s": vmax, "moves_per_10s": len(moves) * 10 / max(dur, 1e-6)}

def head_cut_rate(samples, kf, W):
    n = cut = 0
    for t, items in samples:
        x = x_at(kf, t)
        for it in items:
            if it.kind == "head" and it.must:
                n += 1; inter = max(0, min(it.x1, x + W) - max(it.x0, x)) / max(it.x1 - it.x0, 1)
                cut += inter < 0.9
    return cut / max(n, 1)
```
Manual (look at the images):
1. Contact sheet of 12+ frames incl. one frame before/after every move: faces whole, nothing important sliced.
2. Every cut or pan has a visible reason (speaker turn, subject left the zone).
3. Compare against the "cropped out" report: nothing the narration refers to is missing.
4. First frame is already well composed (it is the cover/preview).

## 11. Bad vs good framing

| Scene | Bad (face-only tracking) | Good |
|---|---|---|
| Presenter beside a slide/screen that matters | window locked on the face, slide cut in half | window on the union face+screen if it fits; if not, hold on the face and cut to the screen when narration says "look at this" |
| Two people talking, 0.8 W apart | follows one, the other half out of frame | both heads kept; speaker gets the larger share |
| Two people far apart | slow ping-pong pans on every "yeah" | hold on speaker; hard cut on each real turn; ignore back-channels < 1 s |
| Speaker walks 15 % of W | camera chases every step (wobble) | dead-zone ignores it; one eased move only if they exit the zone |
| Face edge touching window edge | nose or ear clipped | 6 % margin; edge placed in empty background |
| Action behind the speaker (cooking, demo) | only the face visible | action region weighted 0.6 and kept if it shares the x-range |
| Face lost for 1 s (looks down) | crop jumps to center | tracker coasts 2 s; framing holds |
| Constant slow zoom for "energy" | AI look, loses edges | no zoom; static or purposeful moves only |

## 12. Delivery note (always include)
What was done (shots, moves, cuts); what was dropped per shot (from `cropped_out`); what could not be verified (no YOLO, no audio/VAD, no transcript); whether `recommend_center_fit` was raised; reminder to add captions/hooks after reframing and keep them out of the bottom ~20 % (platform UI).
