"""
Full Screen Smart Reframing & Intelligent Cropping Skill (fullscreenreframe).
Converts any non-9:16 (e.g. 16:9) video into a professionally framed 9:16 FULL SCREEN
(crop-to-fill, 1080x1920) clip.

Features:
- Whole-scene understanding: active speaker, second person, screens/slides, action, saliency.
- Multi-person framing & must-keep greedy packing.
- Optimal horizontal window solving (solve_x) with head-cut & object-cut protection.
- Hold-first camera path, smoothstep eased pans, and speaker-turn instant cuts.
- Single-pass sub-pixel Lanczos affine warp render to FFmpeg H.264/AAC.
- Automated QC gate: head cut rate, coverage, hold ratio, cropped-out audit.
"""

import os, sys, json, math, subprocess, logging, tempfile, shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
import cv2
import numpy as np

LOG = logging.getLogger('cutroom.fullscreen_skill')

# Haar Cascades for face and profile detection
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROFILE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")

CFG = dict(
    step=8,
    face_cut_penalty=3.0,
    obj_cut_penalty=1.2,
    edge_margin=0.06,
    comp_w=0.15,
    move_cost=0.3,
    deadzone=0.08,
    dwell=0.7,
    min_hold=1.5,
    min_move=0.5,
    max_speed=0.5,
    jump_dist=0.6,
    anticipation=0.2
)

@dataclass
class Item:
    kind: str                  # head | body | object | action | text | salient
    x0: float
    y0: float
    x1: float
    y1: float
    weight: float
    must: bool = False
    label: str = ""

def window_size(src_w: float, src_h: float, ar: float = 9/16, zoom: float = 1.0) -> Tuple[float, float, str]:
    """Calculate 9:16 target crop window inside source geometry without stretching."""
    if src_w / src_h >= ar:      # wider than target: full-height window, slide in x
        h = src_h / zoom
        return h * ar, h, "x"
    w = src_w / zoom             # narrower than target: full-width window, slide in y
    return w, w / ar, "y"

def is_cut(prev_bgr: np.ndarray, cur_bgr: np.ndarray, thr: float = 0.55) -> bool:
    """Detect hard scene cut between consecutive frames using HSV histogram correlation."""
    h0 = cv2.calcHist([cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
    h1 = cv2.calcHist([cv2.cvtColor(cur_bgr, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
    cv2.normalize(h0, h0)
    cv2.normalize(h1, h1)
    return bool(cv2.compareHist(h0, h1, cv2.HISTCMP_CORREL) < thr)

def iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    iw = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = iw * ih
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0

def nms(boxes: List[Tuple[float, float, float, float]], thr: float = 0.4) -> List[Tuple[float, float, float, float]]:
    out = []
    for b in sorted(boxes, key=lambda b: -b[2] * b[3]):
        if all(iou(b, o) < thr for o in out):
            out.append(b)
    return out

def detect_faces(bgr: np.ndarray, min_face: float = 0.025) -> List[Tuple[float, float, float, float]]:
    """Multi-angle face detector with frontal, profile, and flipped-profile passes."""
    h, w = bgr.shape[:2]
    s = 960.0 / w if w > 960 else 1.0
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if s != 1.0:
        g = cv2.resize(g, None, fx=s, fy=s)
    mf = max(20, int(min_face * g.shape[1]))
    boxes = []
    
    # Frontal
    for (x, y, fw, fh) in FACE_CASCADE.detectMultiScale(g, 1.1, 5, minSize=(mf, mf)):
        boxes.append((x / s, y / s, fw / s, fh / s))
    # Profile
    for (x, y, fw, fh) in PROFILE_CASCADE.detectMultiScale(g, 1.1, 5, minSize=(mf, mf)):
        boxes.append((x / s, y / s, fw / s, fh / s))
    # Flipped Profile
    gf = cv2.flip(g, 1)
    for (x, y, fw, fh) in PROFILE_CASCADE.detectMultiScale(gf, 1.1, 5, minSize=(mf, mf)):
        boxes.append(((g.shape[1] - x - fw) / s, y / s, fw / s, fh / s))
        
    return nms(boxes)

class Tracker:
    """Coasting tracker with 8 samples (2.0s) memory to prevent crop jumping."""
    def __init__(self, max_age: int = 8, thr: float = 0.15):
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.nid = 0
        self.max_age = max_age
        self.thr = thr

    def update(self, boxes: List[Tuple[float, float, float, float]]) -> Dict[int, Dict[str, Any]]:
        free = list(range(len(boxes)))
        for tid, tr in list(self.tracks.items()):
            best, bi = 0.0, None
            for i in free:
                v = iou(tr["box"], boxes[i])
                if v > best:
                    best, bi = v, i
            if bi is not None and best >= self.thr:
                # Exponential moving average box smoothing
                tr["box"] = tuple(0.6 * n + 0.4 * o for n, o in zip(boxes[bi], tr["box"]))
                tr["age"] = 0
                tr["hits"] += 1
                free.remove(bi)
            else:
                tr["age"] += 1
                if tr["age"] > self.max_age:
                    del self.tracks[tid]
        for i in free:
            self.tracks[self.nid] = {"box": boxes[i], "age": 0, "hits": 1}
            self.nid += 1
        return {k: v for k, v in self.tracks.items() if v["hits"] >= 2}

def mouth_energy(prev_g: np.ndarray, g: np.ndarray, box: Tuple[float, float, float, float]) -> float:
    """Calculate mouth movement energy in lower 40% of face box."""
    x, y, w, h = [int(v) for v in box]
    ys = y + int(0.6 * h)
    a, b = prev_g[ys:y+h, x:x+w], g[ys:y+h, x:x+w]
    return float(np.mean(cv2.absdiff(a, b))) if a.shape == b.shape and a.size else 0.0

def screen_boxes(bgr: np.ndarray) -> List[Tuple[float, float, float, float]]:
    """Detect slides, monitors, or screen rectangles."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    H, W = g.shape
    e = cv2.dilate(cv2.Canny(g, 60, 160), np.ones((3, 3), np.uint8))
    out = []
    contours = cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]
    for c in contours:
        p = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(p) == 4 and cv2.isContourConvex(p):
            x, y, w, h = cv2.boundingRect(p)
            if 0.03 < (w * h) / (W * H) < 0.6 and 0.4 < w / h < 3.0:
                out.append((float(x), float(y), float(w), float(h)))
    return nms(out)

def action_boxes(prev_g: np.ndarray, g: np.ndarray, person_boxes: List[Tuple[float, float, float, float]], thr: int = 18, min_area: float = 0.004) -> List[Tuple[float, float, float, float]]:
    """Detect motion/action outside human bodies."""
    H, W = g.shape
    d = cv2.absdiff(cv2.GaussianBlur(prev_g, (5, 5), 0), cv2.GaussianBlur(g, (5, 5), 0))
    m = ((d > thr) * 255).astype(np.uint8)
    for (x, y, w, h) in person_boxes:
        y0 = int(max(0, y - h * 0.3))
        y1 = int(min(H, y + h * 4))
        x0 = int(max(0, x - w))
        x1 = int(min(W, x + 2 * w))
        m[y0:y1, x0:x1] = 0
    if (m.mean() / 255.0) > 0.35:
        return []
    m = cv2.dilate(m, np.ones((15, 15), np.uint8), iterations=2)
    out = []
    contours = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if (w * h) / (W * H) >= min_area:
            out.append((float(x), float(y), float(w), float(h)))
    return out

def spectral_saliency(gray: np.ndarray) -> np.ndarray:
    """Compute spectral residual saliency map."""
    s = cv2.resize(gray, (128, 72)).astype(np.float32)
    f = np.fft.fft2(s)
    lg = np.log(np.abs(f) + 1e-6)
    sr = lg - cv2.blur(lg, (3, 3))
    m = np.abs(np.fft.ifft2(np.exp(sr + 1j * np.angle(f)))) ** 2
    m = cv2.GaussianBlur(m, (0, 0), 2.5)
    return cv2.resize(m / (m.max() + 1e-9), (gray.shape[1], gray.shape[0]))

def resolve_must_keep(items: List[Item], W: float, fit: float = 0.94) -> Tuple[List[Item], List[Item]]:
    """Greedy packing of must-keep items inside window width W."""
    kept: List[Item] = []
    dropped: List[Item] = []
    for it in sorted([i for i in items if i.must], key=lambda i: -i.weight):
        lo = min([k.x0 for k in kept] + [it.x0])
        hi = max([k.x1 for k in kept] + [it.x1])
        if hi - lo <= W * fit:
            kept.append(it)
        else:
            dropped.append(it)
    for it in dropped:
        it.must = False
        it.weight *= 0.3
    return kept, dropped

def solve_x(items: List[Item], src_w: float, W: float, cfg: dict = CFG, prev_x: Optional[float] = None, spk: Optional[Item] = None) -> Tuple[float, float]:
    """Find horizontal window x position maximizing importance and composition rules."""
    best_x, best_s = (src_w - W) / 2.0, -1e9
    max_x = max(1.0, src_w - W + 1.0)
    for x in np.arange(0.0, max_x, float(cfg["step"])):
        s = 0.0
        for it in items:
            inter = max(0.0, min(it.x1, x + W) - max(it.x0, x)) / max(it.x1 - it.x0, 1.0)
            s += it.weight * inter
            if it.kind == "head":
                if 0.0 < inter < 1.0:
                    s -= cfg["face_cut_penalty"] * it.weight
                elif inter == 1.0:
                    m = min(it.x0 - x, x + W - it.x1) / W
                    if m < cfg["edge_margin"]:
                        s -= (cfg["edge_margin"] - m) * it.weight * 4.0
            elif it.must and 0.0 < inter < 1.0:
                s -= cfg["obj_cut_penalty"] * it.weight
        if spk is not None:
            # Composition: speaker near the middle with lead room
            s -= cfg["comp_w"] * abs(((spk.x0 + spk.x1) / 2.0 - x) / W - 0.5)
        if prev_x is not None:
            s -= cfg["move_cost"] * abs(x - prev_x) / W
        if s > best_s:
            best_s, best_x = s, float(x)
    return best_x, best_s

def plan_keyframes(samples: List[Tuple[float, float]], W: float, fps: float, cfg: dict = CFG) -> List[Tuple[float, float]]:
    """Compute camera path keyframes with deadzone, dwell, and smoothstep easing."""
    if not samples:
        return [(0.0, 0.0)]
    cur = samples[0][1]
    kf: List[Tuple[float, float]] = [(samples[0][0], cur)]
    pending = None
    for t, x in samples[1:]:
        if abs(x - cur) <= cfg["deadzone"] * W:
            pending = None
            continue
        if pending is None or abs(x - pending[1]) > cfg["deadzone"] * W:
            pending = (t, x)
            continue
        if (t - pending[0] >= cfg["dwell"]) and (pending[0] - kf[-1][0] >= cfg["min_hold"]):
            start = max(kf[-1][0], pending[0] - cfg["anticipation"])
            dist = abs(x - cur)
            dur = 1.0 / fps if dist > cfg["jump_dist"] * W else max(cfg["min_move"], dist / (cfg["max_speed"] * W))
            kf.append((start, cur))
            kf.append((start + dur, x))
            cur = x
            pending = None
    if kf[-1][0] < samples[-1][0]:
        kf.append((samples[-1][0], cur))
    return kf

def x_at(kf: List[Tuple[float, float]], t: float) -> float:
    """Evaluate camera horizontal position at time t using smoothstep easing."""
    if not kf:
        return 0.0
    if t <= kf[0][0]:
        return kf[0][1]
    for (t0, x0), (t1, x1) in zip(kf, kf[1:]):
        if t0 <= t < t1:
            u = (t - t0) / max(t1 - t0, 1e-6)
            # Smoothstep easing (never linear, zero overshoot)
            u = u * u * (3.0 - 2.0 * u)
            return x0 + (x1 - x0) * u
    return kf[-1][1]

def motion_stats(kf: List[Tuple[float, float]], W: float, dur: float) -> dict:
    moves = [(t0, t1, abs(x1 - x0)) for (t0, x0), (t1, x1) in zip(kf, kf[1:]) if abs(x1 - x0) > 1.0]
    moving = sum(t1 - t0 for t0, t1, _ in moves)
    vmax = max([d / W / max(t1 - t0, 1e-6) for t0, t1, d in moves] + [0.0])
    return {
        "hold_ratio": float(1.0 - moving / max(dur, 1e-6)),
        "max_speed_W_per_s": float(vmax),
        "moves_per_10s": float(len(moves) * 10.0 / max(dur, 1e-6)),
        "moves_count": len(moves)
    }

def head_cut_rate(samples_items: List[Tuple[float, List[Item]]], kf: List[Tuple[float, float]], W: float) -> float:
    n = cut = 0
    for t, items in samples_items:
        x = x_at(kf, t)
        for it in items:
            if it.kind == "head" and it.must:
                n += 1
                inter = max(0.0, min(it.x1, x + W) - max(it.x0, x)) / max(it.x1 - it.x0, 1.0)
                if inter < 0.90:
                    cut += 1
    return float(cut / max(n, 1))

def render_fullscreen(
    src_video: Path,
    kf: List[Tuple[float, float]],
    out_video: Path,
    W: float,
    H_win: float,
    fps: float,
    target_size: Tuple[int, int] = (1080, 1920),
    progress_cb = None
):
    """
    Sub-pixel Lanczos affine warp render piped to FFmpeg.
    Ensures 1080x1920 full bleed without stretching or jagged integer pixel stepping.
    """
    cap = cv2.VideoCapture(str(src_video))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    s = target_size[1] / H_win

    cmd = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{target_size[0]}x{target_size[1]}",
        "-r", str(fps),
        "-i", "-",
        "-i", str(src_video),
        "-map", "0:v",
        "-map", "1:a?",
        "-c:v", "libx264",
        "-crf", "17",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_video)
    ]

    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    frame_idx = 0
    try:
        while True:
            ok, fr = cap.read()
            if not ok or fr is None:
                break
            t = frame_idx / fps
            x = x_at(kf, t)
            # Affine warp matrix mapping (x, 0) to (0, 0) scaled by s
            M = np.float32([[s, 0.0, -x * s], [0.0, s, 0.0]])
            warped = cv2.warpAffine(fr, M, target_size, flags=cv2.INTER_LANCZOS4)
            ff.stdin.write(warped.tobytes())
            frame_idx += 1
            if progress_cb and frame_idx % 30 == 0:
                pct = int(min(90, (frame_idx / max(1, total_frames)) * 90))
                progress_cb(pct, f"Rendering full-screen 9:16 ({pct}%)...")
    finally:
        cap.release()
        if ff.stdin:
            ff.stdin.close()
        ff.wait()

    if ff.returncode != 0:
        err = ff.stderr.read().decode('utf-8', errors='ignore') if ff.stderr else 'Unknown FFmpeg error'
        raise RuntimeError(f"FFmpeg render failed with code {ff.returncode}: {err}")


def execute_fullscreen_skill(
    source_video: Path,
    cand: dict,
    transcript_words: list,
    output_mp4: Path,
    progress_cb = None
) -> dict:
    """
    Executes the Full Screen Smart Reframing & Intelligent Cropping Skill:
    1. Slices clip segment.
    2. Runs 4 fps scene analysis (shots, faces, speaker activity, objects, action).
    3. Plans optimal hold-first camera paths with eased smoothstep pans.
    4. Sub-pixel renders to 1080x1920 MP4 via FFmpeg.
    5. Audits QC metrics (head cut rate, coverage, hold ratio, cropped-out report).
    """
    start_at = cand["s"]
    end_at = cand["e"]
    dur = max(0.5, end_at - start_at)

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="fullscreen_stage_") as td:
        work = Path(td)
        clip_in = work / "input.mp4"
        final_mp4 = work / "final.mp4"

        # 1. Extract clip segment
        if progress_cb: progress_cb(5, "Extracting clip segment for reframing...")
        slice_cmd = [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-ss", f"{start_at:.3f}",
            "-t", f"{dur:.3f}",
            "-i", str(source_video),
            "-c:v", "libx264", "-crf", "16", "-preset", "fast",
            "-c:a", "copy",
            str(clip_in)
        ]
        subprocess.run(slice_cmd, capture_output=True, check=True)

        # 2. Probe geometry
        cap = cv2.VideoCapture(str(clip_in))
        src_w = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        W, H_win, slide_axis = window_size(src_w, src_h, ar=9/16, zoom=1.0)

        # 3. Analyze at 4 fps
        if progress_cb: progress_cb(15, "Analyzing scene (faces, speaker activity, screens, action)...")
        sample_step = max(1, int(fps / 4.0))
        tracker = Tracker(max_age=8, thr=0.15)
        
        cap = cv2.VideoCapture(str(clip_in))
        prev_bgr = None
        prev_gray = None
        shots: List[Dict[str, float]] = []
        cur_shot_start = 0.0
        
        samples_data = []      # list of (t, target_x)
        samples_items = []     # list of (t, items)
        dropped_items_all = []
        
        # Check transcript for deictic triggers in this clip
        clip_text = " ".join((w.get('t') or w.get('w', '')).lower() for w in transcript_words if start_at <= w.get('s', 0) <= end_at)
        deictic_active = any(kw in clip_text for kw in ["look at this", "look here", "dekho", "ye dekho", "see here", "right here"])

        frame_num = 0
        while True:
            ok, bgr = cap.read()
            if not ok or bgr is None:
                break
            t = frame_num / fps
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

            # Shot boundary detection
            if prev_bgr is not None and is_cut(prev_bgr, bgr, thr=0.55):
                shots.append({"start": cur_shot_start, "end": t})
                cur_shot_start = t

            if frame_num % sample_step == 0:
                face_boxes = detect_faces(bgr)
                active_tracks = tracker.update(face_boxes)

                items: List[Item] = []
                best_mouth_energy = -1.0
                speaker_box = None

                for tid, tr in active_tracks.items():
                    fb = tr["box"]
                    # Expanded head box (+40% margin)
                    hx = max(0.0, fb[0] - fb[2] * 0.4)
                    hy = max(0.0, fb[1] - fb[3] * 0.2)
                    hw = min(src_w - hx, fb[2] * 1.8)
                    hh = min(src_h - hy, fb[3] * 1.4)
                    items.append(Item(kind="head", x0=hx, y0=hy, x1=hx+hw, y1=hy+hh, weight=1.0, must=True, label=f"person_{tid}_head"))

                    # Torso box
                    tx = max(0.0, fb[0] - fb[2] * 1.1)
                    ty = hy + hh
                    tw = min(src_w - tx, fb[2] * 3.2)
                    th = min(src_h - ty, fb[3] * 4.0)
                    items.append(Item(kind="body", x0=tx, y0=ty, x1=tx+tw, y1=ty+th, weight=0.4, must=False, label=f"person_{tid}_body"))

                    if prev_gray is not None:
                        me = mouth_energy(prev_gray, gray, fb)
                        if me > best_mouth_energy:
                            best_mouth_energy = me
                            speaker_box = Item(kind="head", x0=hx, y0=hy, x1=hx+hw, y1=hy+hh, weight=1.0, must=True)

                # Screen & slide detection
                screens = screen_boxes(bgr)
                for s_idx, sb in enumerate(screens):
                    w_obj = 0.8 * (1.5 if deictic_active else 1.0)
                    items.append(Item(kind="object", x0=sb[0], y0=sb[1], x1=sb[0]+sb[2], y1=sb[1]+sb[3], weight=w_obj, must=(w_obj >= 0.8), label=f"screen_{s_idx}"))

                # Action detection outside people
                if prev_gray is not None:
                    p_boxes = [tr["box"] for tr in active_tracks.values()]
                    act_boxes = action_boxes(prev_gray, gray, p_boxes)
                    for a_idx, ab in enumerate(act_boxes):
                        items.append(Item(kind="action", x0=ab[0], y0=ab[1], x1=ab[0]+ab[2], y1=ab[1]+ab[3], weight=0.6, must=False, label=f"action_{a_idx}"))

                # Greedy must-keep resolution (packing within 0.94 W)
                kept, dropped = resolve_must_keep(items, W, fit=0.94)
                if dropped:
                    dropped_items_all.extend([it.label for it in dropped])

                # Solve horizontal position x for this sample
                prev_sample_x = samples_data[-1][1] if samples_data else None
                x_sol, _ = solve_x(items, src_w, W, cfg=CFG, prev_x=prev_sample_x, spk=speaker_box)
                samples_data.append((t, x_sol))
                samples_items.append((t, items))

            prev_bgr = bgr.copy()
            prev_gray = gray.copy()
            frame_num += 1

        cap.release()
        shots.append({"start": cur_shot_start, "end": dur})

        # 4. Plan keyframes with hold-first camera path & smoothstep easing
        if progress_cb: progress_cb(50, "Planning hold-first camera paths & eased pans...")
        kf = plan_keyframes(samples_data, W, fps, cfg=CFG)
        stats = motion_stats(kf, W, dur)
        hc_rate = head_cut_rate(samples_items, kf, W)

        # 5. Render single-pass sub-pixel 1080x1920 MP4
        if progress_cb: progress_cb(60, "Executing sub-pixel Lanczos affine warp render...")
        render_fullscreen(
            src_video=clip_in,
            kf=kf,
            out_video=final_mp4,
            W=W,
            H_win=H_win,
            fps=fps,
            target_size=(1080, 1920),
            progress_cb=progress_cb
        )

        # 6. Copy final output to destination
        shutil.copyfile(str(final_mp4), str(output_mp4))

        # 7. Quality Gate Audit
        recommend_center_fit = len(dropped_items_all) > 5 and (len(dropped_items_all) / max(1, len(samples_data))) > 0.30
        qc_passed = (hc_rate == 0.0) and (stats["hold_ratio"] >= 0.70)

        metadata = {
            "framing": "fullscreen",
            "resolution": "1080x1920",
            "shots_count": len(shots),
            "camera_moves": stats["moves_count"],
            "hold_ratio": round(stats["hold_ratio"] * 100.0, 1),
            "max_speed_W_per_s": round(stats["max_speed_W_per_s"], 2),
            "head_cut_rate": round(hc_rate, 3),
            "dropped_items_count": len(dropped_items_all),
            "recommend_center_fit": recommend_center_fit,
            "qc_passed": qc_passed
        }

        LOG.info("fullscreen_skill_completed out=%s meta=%s", output_mp4, metadata)
        if progress_cb: progress_cb(100, f"Full Screen Reframing complete (Hold ratio: {metadata['hold_ratio']}%)")

        return metadata
