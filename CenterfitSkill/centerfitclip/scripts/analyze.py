#!/usr/bin/env python3
"""CenterFitClip analyzer.
Reads the ORIGINAL video and writes analysis.json (+ contact_sheet.jpg):
  - content rectangle (the real footage inside any blurred bands)
  - person detection  -> decides AUTOMATICALLY whether the "second box" is shown
  - audio reaction peaks, speech-likeness, scene cuts
Usage: python analyze.py input.mp4 --out work/
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile
import numpy as np
try:
    import cv2
except ImportError:
    sys.exit("Missing deps: pip install opencv-python-headless numpy --break-system-packages")

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe(p):
    j = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", p]).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    n, d = v["r_frame_rate"].split("/")
    fps = float(n) / float(d) if float(d) else 30.0
    return dict(width=int(v["width"]), height=int(v["height"]), fps=round(fps, 3),
                duration=round(float(j["format"]["duration"]), 3),
                has_audio=any(s["codec_type"] == "audio" for s in j["streams"]))

def sample_frames(p, dur, tmp, max_frames=90):
    fps = min(2.0, max_frames / max(dur, 1.0))
    sh(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", f"fps={fps}", "-q:v", "3", f"{tmp}/f_%04d.jpg"])
    return [cv2.imread(f) for f in sorted(glob.glob(f"{tmp}/f_*.jpg"))]

# ---------- content rectangle (center-fit sources have blurred bands) ----------
def _smooth(v, n=7):
    return np.convolve(np.pad(v, n, mode="edge"), np.ones(n) / n, mode="same")[n:-n]

def _run(mask):
    best, s = (0, 0), None
    for i, m in enumerate(list(mask) + [False]):
        if m and s is None: s = i
        if not m and s is not None:
            if i - s > best[1] - best[0]: best = (s, i)
            s = None
    return best

def find_content(frames, W, H):
    full = dict(x=0, y=0, w=W, h=H, mode="full-frame")
    if W / H >= 1.5:
        full["mode"] = "landscape-source"; return full
    rows, cols = np.zeros(H), np.zeros(W)
    for f in frames:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        lap = np.abs(cv2.Laplacian(g, cv2.CV_32F, ksize=3))
        rows += lap.mean(1); cols += lap.mean(0)
    rows, cols = _smooth(rows / len(frames)), _smooth(cols / len(frames))
    def band(v, n):
        s, e = _run(v > max(np.percentile(v, 95) * 0.2, 0.3))
        if s > 0: s += 3          # trim the soft blur edge, never the frame border
        if e < n: e -= 3
        return s, e
    ys, ye = band(rows, H); xs, xe = band(cols, W)
    if (ye - ys) < 0.15 * H or (xe - xs) < 0.15 * W or ((ye - ys) > 0.97 * H and (xe - xs) > 0.97 * W):
        return full
    r = dict(x=xs - xs % 2, y=ys - ys % 2, w=(xe - xs) // 2 * 2, h=(ye - ys) // 2 * 2, mode="center-fit-extracted")
    return r

# ---------- person detection ----------
def _cluster(dets, radius):
    cl = []
    for d in dets:
        fi, x, y, w, h = d; cx, cy = x + w / 2, y + h / 2
        for c in cl:
            if abs(c["cx"] - cx) < radius and abs(c["cy"] - cy) < radius:
                c["m"].append(d); n = len(c["m"])
                c["cx"] += (cx - c["cx"]) / n; c["cy"] += (cy - c["cy"]) / n; break
        else:
            cl.append(dict(cx=cx, cy=cy, m=[d]))
    return cl

def _best(cl, nframes):
    if not cl: return None, 0.0, 0
    b = max(cl, key=lambda c: len({m[0] for m in c["m"]}))
    hits = len({m[0] for m in b["m"]})
    return b, hits / nframes, hits

def detect_person(frames, rc):
    n = len(frames); ox, oy, rw, rh = rc["x"], rc["y"], rc["w"], rc["h"]
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    ms = max(24, int(rw * 0.04)); dets = []
    for i, f in enumerate(frames):
        g = cv2.equalizeHist(cv2.cvtColor(f[oy:oy + rh, ox:ox + rw], cv2.COLOR_BGR2GRAY))
        for (x, y, w, h) in face.detectMultiScale(g, 1.1, 5, minSize=(ms, ms)):
            dets.append((i, ox + x, oy + y, w, h))
        for (x, y, w, h) in prof.detectMultiScale(g, 1.1, 8, minSize=(ms, ms)):
            dets.append((i, ox + x, oy + y, w, h))
    b, ratio, hits = _best(_cluster(dets, 0.12 * rw), n)
    out = dict(present=False, kind=None, presence_ratio=round(ratio, 3), frames_hit=hits, frames_total=n, bbox=None, crop=None)
    if b is not None and ratio >= 0.30:
        ms_ = np.median(np.array([m[1:] for m in b["m"]]), axis=0)
        fx, fy, fw, fh = [float(v) for v in ms_]
        if fw >= 0.03 * rw:
            cw = fw * 3.5; ch = cw / 1.6                       # 16:10 window, face + shoulders
            cx, cy = fx + fw / 2, fy + fh * 0.78
            cw = min(cw, rw); ch = min(ch, rh); cw = min(cw, ch * 1.6)
            x0 = min(max(cx - cw / 2, ox), ox + rw - cw); y0 = min(max(cy - ch / 2, oy), oy + rh - ch)
            out.update(present=True, kind="face", bbox=dict(x=int(fx), y=int(fy), w=int(fw), h=int(fh)),
                       crop=dict(x=int(x0) // 2 * 2, y=int(y0) // 2 * 2, w=int(cw) // 2 * 2, h=int(ch) // 2 * 2))
            return out
    # body fallback (no visible face): must be persistent and stable, otherwise it is ignored
    hog = cv2.HOGDescriptor(); hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    bd = []
    for i, f in enumerate(frames):
        sub = f[oy:oy + rh, ox:ox + rw]; sc = 640 / sub.shape[1] if sub.shape[1] > 640 else 1.0
        im = cv2.resize(sub, None, fx=sc, fy=sc) if sc != 1.0 else sub
        rects, wts = hog.detectMultiScale(im, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for (x, y, w, h), wt in zip(rects, np.ravel(wts)):
            if wt > 0.9: bd.append((i, ox + x / sc, oy + y / sc, w / sc, h / sc))
    b, ratio, hits = _best(_cluster(bd, 0.12 * rw), n)
    if b is not None and ratio >= 0.5:
        fx, fy, fw, fh = [float(v) for v in np.median(np.array([m[1:] for m in b["m"]]), axis=0)]
        ch = min(fh * 1.15, rh); cw = min(ch * 1.6, rw); cx, cy = fx + fw / 2, fy + fh / 2
        x0 = min(max(cx - cw / 2, ox), ox + rw - cw); y0 = min(max(cy - ch / 2, oy), oy + rh - ch)
        out.update(present=True, kind="body", presence_ratio=round(ratio, 3), frames_hit=hits,
                   bbox=dict(x=int(fx), y=int(fy), w=int(fw), h=int(fh)),
                   crop=dict(x=int(x0) // 2 * 2, y=int(y0) // 2 * 2, w=int(cw) // 2 * 2, h=int(ch) // 2 * 2))
    return out

# ---------- audio ----------
def analyze_audio(p, dur, tmp):
    wav = os.path.join(tmp, "a.wav")
    sh(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", wav])
    import wave
    try:
        w = wave.open(wav); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    except Exception:
        return dict(peaks=[], speech_ratio=0.0, speech_detected=False)
    if len(x) < 3200: return dict(peaks=[], speech_ratio=0.0, speech_detected=False)
    h = 800
    r = np.sqrt(np.convolve(x ** 2, np.ones(h) / h, "same"))[::h]
    d = np.diff(r, prepend=r[0]); thr75 = np.percentile(r, 75); peaks = []
    maxp = max(2, int(dur / 3))
    for i in np.argsort(-d):
        t = i * 0.05
        if r[i] > thr75 and 0.8 < t < dur - 0.8 and all(abs(t - q) > 1.8 for q in peaks):
            peaks.append(float(t))
        if len(peaks) >= maxp: break
    # speech-likeness: energy + 300-3400 Hz band share + not a pure tone
    win = 1600; nwin = len(x) // win; fr = np.fft.rfftfreq(win, 1 / 16000); band = (fr >= 300) & (fr <= 3400)
    rms = np.array([np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2)) for i in range(nwin)])
    gate = max(np.percentile(rms, 40) * 1.5, 200.0); flags = []
    for i in range(nwin):
        if rms[i] < gate: flags.append(False); continue
        pw = np.abs(np.fft.rfft(x[i * win:(i + 1) * win] * np.hanning(win))) ** 2
        tot = pw.sum() + 1e-9
        flags.append(bool(pw[band].sum() / tot > 0.55 and pw.max() / tot < 0.35))
    sr = float(np.mean(flags)) if flags else 0.0
    return dict(peaks=[round(p, 2) for p in sorted(peaks)], speech_ratio=round(sr, 3), speech_detected=sr >= 0.25)

def scene_cuts(p, rc, dur):
    vf = f"crop={rc['w']}:{rc['h']}:{rc['x']}:{rc['y']},select='gt(scene,0.25)',showinfo"
    r = sh(["ffmpeg", "-i", p, "-vf", vf, "-an", "-f", "null", "-"])
    ts = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    out = []
    for t in ts:
        if 0.5 < t < dur - 0.5 and (not out or t - out[-1] >= 0.8): out.append(round(t, 2))
    return out

def contact_sheet(frames, path, n=8):
    idx = np.linspace(0, len(frames) - 1, min(n, len(frames))).astype(int)
    tiles = []
    for i in idx:
        f = frames[i]; s = 240 / f.shape[0]; tiles.append(cv2.resize(f, None, fx=s, fy=s))
    cv2.imwrite(path, np.hstack(tiles))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("--out", default="work")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    info = probe(a.input)
    if info["width"] > 1920: print("WARN: >1080p source; detection runs at native size and may be slow.")
    with tempfile.TemporaryDirectory() as tmp:
        frames = sample_frames(a.input, info["duration"], tmp)
        if not frames: sys.exit("Could not decode frames.")
        rc = find_content(frames, info["width"], info["height"])
        person = detect_person(frames, rc)
        audio = analyze_audio(a.input, info["duration"], tmp) if info["has_audio"] else dict(peaks=[], speech_ratio=0.0, speech_detected=False)
        cuts = scene_cuts(a.input, rc, info["duration"])
        contact_sheet(frames, os.path.join(a.out, "contact_sheet.jpg"))
    visible = bool(person["present"])
    reason = (f"{person['kind']} detected in {person['frames_hit']}/{person['frames_total']} sampled frames "
              f"({person['presence_ratio']:.0%}) at a stable position" if visible else
              "no persistent human figure found in the footage -> second box hidden")
    res = dict(source=info, content_rect=rc, person=person, audio=audio, cuts=cuts,
               layout=dict(second_box=dict(visible=visible, reason=reason, crop=person["crop"] if visible else None),
                           speaker_offscreen=bool(audio["speech_detected"] and not visible)))
    json.dump(res, open(os.path.join(a.out, "analysis.json"), "w"), indent=2)
    print(json.dumps(res["layout"], indent=2)); print("content_rect:", rc); print("peaks:", audio["peaks"]); print("cuts:", cuts)

if __name__ == "__main__":
    main()
