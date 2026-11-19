#!/usr/bin/env python3
"""CenterFitClip renderer: Center Fit 9:16 only (blurred backdrop + full-width clip). Never full-screen crop.
Usage:
  python render.py input.mp4 work/analysis.json --hook1 "line 1" --hook2 "line 2" --out final.mp4
Optional: --reactions r.json --captions c.json --teaser-mid "..." --teaser-late "..." --intensity balanced|clean --no-sfx
The second box is read from analysis.json (layout.second_box.visible). It is NEVER chosen by the user.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/hind/Hind-Bold.ttf"

def font():
    p = os.path.join(ROOT, "assets", "fonts", "Hind-Bold.ttf")
    if not (os.path.exists(p) and os.path.getsize(p) > 10000):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        subprocess.run(["curl", "-sL", "-o", p, FONT_URL])
    if os.path.exists(p) and os.path.getsize(p) > 10000: return p
    print("WARN: Hind-Bold.ttf unavailable; Devanagari text will NOT render correctly.")
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("analysis")
    ap.add_argument("--out", default="final.mp4")
    ap.add_argument("--hook1", default=""); ap.add_argument("--hook2", default="")
    ap.add_argument("--reactions"); ap.add_argument("--captions")
    ap.add_argument("--teaser-mid", default=""); ap.add_argument("--teaser-late", default="")
    ap.add_argument("--intensity", choices=["balanced", "clean"], default="balanced")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--size", choices=["auto", "720", "1080"], default="auto")
    ap.add_argument("--bg-style", choices=["blur", "black", "white"], default="blur")
    a = ap.parse_args()

    an = json.load(open(a.analysis)); src = an["source"]; rc = an["content_rect"]
    dur = src["duration"]
    W, H = (1080, 1920) if (a.size == "1080" or (a.size == "auto" and rc["w"] > 1000)) else (720, 1280)
    k = W / 720.0
    S = lambda v: int(round(v * k))
    ev = lambda v: int(v) // 2 * 2
    P = an["audio"]["peaks"]; C = an["cuts"]
    box = an["layout"]["second_box"]; has_box = bool(box["visible"])
    bal = a.intensity == "balanced"
    F = font(); work = os.path.dirname(os.path.abspath(a.out)) or "."
    tdir = os.path.join(work, "_text"); os.makedirs(tdir, exist_ok=True)
    tn = [0]

    # ---- geometry ----
    asp = rc["w"] / rc["h"]
    maxh = (0.40 if has_box else 0.62) * H
    tw = ev(min(W, maxh * asp)); th = ev(tw / asp)
    gap = S(45); bw = ev(0.8 * W); bh = ev(bw / 1.6); bd = S(8)
    if has_box:
        block = th + gap + bh + 2 * bd
        cy = int((H - block) / 2 + S(15))
    else:
        cy = (H - th) // 2
    cx = (W - tw) // 2
    bottom = cy + th + ((gap + bh + 2 * bd) if has_box else 0)

    # ---- motion expressions ----
    def punches(amp, rate):
        return "+".join(f"if(gte(on/30,{p}),{amp}*exp(-(on/30-{p})*{rate}),0)" for p in P) or "0"
    amp_g, amp_f, shake = (0.10, 0.16, 9) if bal else (0.05, 0.08, 0)
    Zg = "1+" + punches(amp_g, 6)
    if not bal:   # clean: add eased push-in per shot
        seg = [0] + C; end = C + [dur]; z = ""
        for s_, e_ in zip(seg, end): z += f"if(lt(on/30,{e_}),0.04*(1-cos(PI*(on/30-{s_})/{max(e_-s_,0.1)}))/2,"
        Zg += "+" + z + "0" + ")" * len(seg)
    Zf = "1+" + punches(amp_f, 5)
    A = "+".join(f"if(between(t,{p},{p+0.4}),{shake*k:.2f}*(1-(t-{p})/0.4),0)" for p in P) or "0"
    flash = "+".join([f"between(t,{p},{p+0.06})" for p in P] + [f"between(t,{c},{c+0.05})" for c in C]) or "0"
    glitch = "+".join([f"between(t,{p},{p+0.25})" for p in P] + [f"between(t,{c},{c+0.12})" for c in C]) or "0"

    # ---- text helper (textfile + expansion=none: no escaping problems, Unicode safe) ----
    def dt(text, size, color, y, enable, bw_=6, x="(w-text_w)/2", extra=""):
        tn[0] += 1; fp = os.path.join(tdir, f"t{tn[0]}.txt"); open(fp, "w", encoding="utf-8").write(text)
        f_esc = F.replace('\\', '/').replace(':', '\\:')
        fp_esc = fp.replace('\\', '/').replace(':', '\\:')
        return (f"drawtext=fontfile='{f_esc}':textfile='{fp_esc}':expansion=none:fontsize={S(size)}:fontcolor={color}:"
                f"borderw={S(bw_)}:bordercolor=black:x={x}:y={y}:enable='{enable}'{extra}")

    f = []
    if a.bg_style == "black":
        f.append(f"color=c=black:s={W}x{H}:d={dur}[bg]")
        f.append("[0:v]fps=30,split=" + ("2[b][c]" if has_box else "1[b]"))
    elif a.bg_style == "white":
        f.append(f"color=c=white:s={W}x{H}:d={dur}[bg]")
        f.append("[0:v]fps=30,split=" + ("2[b][c]" if has_box else "1[b]"))
    else:
        f.append("[0:v]fps=30,split=" + ("3[a][b][c]" if has_box else "2[a][b]"))
        f.append(f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma={S(30)},eq=brightness=-0.25:saturation=1.6[bg]")
    f.append(f"[b]crop={rc['w']}:{rc['h']}:{rc['x']}:{rc['y']},scale={tw}:{th}:flags=lanczos,"
             f"zoompan=z='{Zg}':x='iw/2-(iw/zoom/2)':y='ih-ih/zoom':d=1:s={tw}x{th}:fps=30,"
             f"eq=contrast=1.15:saturation=1.35:gamma=0.96,unsharp=5:5:1.0[g]")
    f.append(f"[bg][g]overlay={cx}:{cy}:shortest=1[v1]")
    last = "v1"
    if has_box:
        c = box["crop"]
        f.append(f"[c]crop={c['w']}:{c['h']}:{c['x']}:{c['y']},scale={bw}:{bh}:flags=lanczos,"
                 f"zoompan=z='{Zf}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={bw}x{bh}:fps=30,"
                 f"eq=contrast=1.1:saturation=1.25,unsharp=5:5:1.2,pad={bw+2*bd}:{bh+2*bd}:{bd}:{bd}:color=yellow[fc]")
        f.append(f"[v1][fc]overlay={(W-bw-2*bd)//2}:{cy+th+gap}:shortest=1[v2]"); last = "v2"
    f.append(f"[{last}]drawbox=x={cx}:y={cy-S(6)}:w={tw}:h={S(6)}:color=yellow:t=fill,"
             f"drawbox=x={cx}:y={cy+th}:w={tw}:h={S(6)}:color=yellow:t=fill[v3]")
    if shake:
        f.append(f"[v3]scale={ev(W*1.05)}:{ev(H*1.05)},crop={W}:{H}:x='(in_w-out_w)/2+({A})*sin(t*95)':"
                 f"y='(in_h-out_h)/2+({A})*0.6*cos(t*83)'[v4]")
    else:
        f.append("[v3]null[v4]")
    if a.bg_style == "white":
        fx = f"rgbashift=rh={-S(14)}:bh={S(14)}:rv={S(4)}:bv={-S(4)}:enable='{glitch}'" if bal else "null"
    elif bal:
        fx = f"rgbashift=rh={-S(14)}:bh={S(14)}:rv={S(4)}:bv={-S(4)}:enable='{glitch}',noise=alls=4:allf=t,vignette=PI/6"
    else:
        fx = "vignette=PI/8"
    f.append(f"[v4]{fx}[v5]")

    T = []
    h1y, h2y = cy - S(190), cy - S(123)
    if a.hook1: T.append(dt(a.hook1, 58, "white", f"'{h1y}+if(lt(t,0.25),(0.25-t)*{-S(400)},0)'", "lt(t,3.2)", 6))
    if a.hook2: T.append(dt(a.hook2, 72, "yellow", str(h2y), "between(t,0.15,3.2)", 7))
    if a.reactions:
        R = json.load(open(a.reactions))
        for i, r in enumerate(R):
            if isinstance(r, str):
                if i >= len(P): break
                r = dict(time=P[i], text=r)
            T.append(dt(r["text"], 68, "yellow" if i % 2 == 0 else "white", str(cy - S(150)), f"between(t,{r['time']},{r['time']+1.0})", 7))
    ty = bottom + S(24)
    if a.teaser_mid:  T.append(dt(a.teaser_mid, 50, "white", str(ty), f"between(t,{0.30*dur:.2f},{0.30*dur+2.6:.2f})", 6))
    if a.teaser_late: T.append(dt(a.teaser_late, 50, "yellow", str(ty), f"between(t,{0.72*dur:.2f},{0.72*dur+2.8:.2f})", 6))
    if a.captions:
        import textwrap
        for cp in json.load(open(a.captions)):
            lines = textwrap.wrap(cp["text"], 28)[:2]
            for li, ln in enumerate(lines):
                T.append(dt(ln, 44, "white", str(cy + th - S(120) + li * S(54)), f"between(t,{cp['start']},{cp['end']})", 5))
    bar = f"drawbox=x=0:y={H-S(8)}:w='{W}*t/{dur}':h={S(8)}:color=white@0.85:t=fill"
    flashbox = f"drawbox=x=0:y=0:w={W}:h={H}:color=white@0.85:t=fill:enable='{flash}'" if bal else ""
    chain = ",".join(T + [bar] + ([flashbox] if flashbox else []))
    f.append(f"[v5]{chain}[vo]")

    # ---- audio ----
    base = "[0:a]highpass=f=80,acompressor=threshold=-20dB:ratio=3,aformat=sample_rates=44100:channel_layouts=stereo[ao]" if src["has_audio"] \
        else f"anullsrc=r=44100:cl=stereo,atrim=0:{dur}[ao]"
    f.append(base); mix = ["[ao]"]
    if not a.no_sfx and P:
        f.append("aevalsrc='0.9*sin(2*PI*150*(1-exp(-6*t))/6)*exp(-4*t)':d=0.9:s=44100,aformat=channel_layouts=stereo,asplit=%d%s" % (len(P), "".join(f"[b{i}]" for i in range(len(P)))))
        for i, p in enumerate(P):
            d = int(p * 1000 - 20); f.append(f"[b{i}]adelay={d}|{d},volume=0.8[bx{i}]"); mix.append(f"[bx{i}]")
    if not a.no_sfx and C:
        f.append("anoisesrc=d=0.45:c=pink:a=0.5:r=44100,highpass=f=500,lowpass=f=7000,afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.15,aformat=channel_layouts=stereo,asplit=%d%s" % (len(C), "".join(f"[w{i}]" for i in range(len(C)))))
        for i, c_ in enumerate(C):
            d = int(max(0, c_ * 1000 - 300)); f.append(f"[w{i}]adelay={d}|{d},volume=0.9[wx{i}]"); mix.append(f"[wx{i}]")
    f.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-13.5:TP=-2.0,alimiter=limit=0.85:level=0,"
             f"afade=t=in:d=0.02,afade=t=out:st={dur-0.03:.2f}:d=0.03[aout]")

    fc = os.path.join(work, "filtergraph.txt"); open(fc, "w", encoding="utf-8").write(";\n".join(f))
    filter_flag = "-/filter_complex" if os.name == "nt" or not subprocess.run(["ffmpeg", "-h", "filter_complex_script"], capture_output=True).stdout else "-filter_complex_script"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.input, filter_flag, fc, "-map", "[vo]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{dur}", "-movflags", "+faststart", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: print(r.stderr[:2000]); sys.exit(1)
    rep = dict(output=a.out, size=[W, H], duration=dur, intensity=a.intensity, second_box_rendered=has_box,
               second_box_reason=box["reason"], content_fit=dict(width=tw, height=th, x=cx, y=cy),
               peaks_used=P, cuts_used=C, speaker_offscreen=an["layout"]["speaker_offscreen"])
    json.dump(rep, open(os.path.join(work, "render_report.json"), "w"), indent=2)
    print("rendered", a.out, "| second box:", "SHOWN" if has_box else "HIDDEN")

if __name__ == "__main__":
    main()
