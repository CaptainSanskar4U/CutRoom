#!/usr/bin/env python3
"""CenterFitClip QC gate. Usage: python qc.py final.mp4 --source original.mp4 --analysis work/analysis.json --report work/render_report.json"""
import argparse, json, re, subprocess, sys, os

def sh(c): return subprocess.run(c, capture_output=True, text=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--source"); ap.add_argument("--analysis"); ap.add_argument("--report")
    a = ap.parse_args(); res = []
    def chk(name, ok, detail=""): res.append((name, bool(ok), detail))
    j = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", a.video]).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video"); au = [s for s in j["streams"] if s["codec_type"] == "audio"]
    W, H = int(v["width"]), int(v["height"]); dur = float(j["format"]["duration"])
    chk("9:16 vertical", abs(W / H - 9 / 16) < 0.01, f"{W}x{H}")
    chk("H.264 + yuv420p", v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p", f"{v['codec_name']}/{v.get('pix_fmt')}")
    chk("audio present (AAC)", bool(au) and au[0]["codec_name"] == "aac")
    if a.source:
        sd = float(json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", a.source]).stdout)["format"]["duration"])
        chk("duration matches source (+-0.15s)", abs(sd - dur) <= 0.15, f"{dur:.2f}s vs {sd:.2f}s")
    l = sh(["ffmpeg", "-i", a.video, "-af", "loudnorm=print_format=json", "-f", "null", "-"]).stderr
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", l, re.S)
    if m:
        d = json.loads(m.group(0)); I, TP = float(d["input_i"]), float(d["input_tp"])
        chk("loudness -16..-12 LUFS", -16 <= I <= -12, f"{I:.1f} LUFS"); chk("true peak <= -1 dBTP", TP <= -1.0, f"{TP:.1f} dBTP")
    f0 = sh(["ffmpeg", "-v", "error", "-i", a.video, "-vf", "select=eq(n\\,0),signalstats,metadata=print", "-frames:v", "1", "-f", "null", "-"]).stderr
    r = sh(["ffmpeg", "-i", a.video, "-vf", "select=eq(n\\,0),signalstats,metadata=print:file=-", "-frames:v", "1", "-f", "null", "-"]).stdout
    y = re.search(r"YAVG=([0-9.]+)", r); chk("first frame is NOT black (no fade-in)", y and float(y.group(1)) > 25, f"YAVG={y.group(1) if y else '?'}")
    bd = sh(["ffmpeg", "-i", a.video, "-vf", "blackdetect=d=0.3:pix_th=0.05", "-an", "-f", "null", "-"]).stderr
    chk("no black/dead frames (>0.3s)", "black_start" not in bd)
    fz = sh(["ffmpeg", "-i", a.video, "-vf", "freezedetect=n=0.001:d=1.5", "-an", "-f", "null", "-"]).stderr
    chk("no frozen segments (>1.5s)", "freeze_start" not in fz)
    if a.analysis and a.report:
        an = json.load(open(a.analysis)); rp = json.load(open(a.report))
        chk("second box matches auto-detection", rp["second_box_rendered"] == an["layout"]["second_box"]["visible"],
            f"detected={an['layout']['second_box']['visible']} rendered={rp['second_box_rendered']}")
        cf = rp["content_fit"]; chk("clip fully inside frame, centered horizontally", cf["x"] >= 0 and cf["x"] + cf["width"] <= W and abs(cf["x"] - (W - cf["width"]) / 2) <= 1)
    out = os.path.splitext(a.video)[0] + "_qc_sheet.jpg"
    sh(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", f"fps=8/{dur},scale=216:-1,tile=8x1", "-frames:v", "1", out])
    print("\nCenterFitClip QC\n" + "-" * 60)
    for n, ok, d in res: print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d else ""))
    print("-" * 60 + f"\nContact sheet for MANUAL review: {out}\nManual items still required: see references/qc-checklist.md (sections B-E).")
    json.dump([dict(check=n, passed=ok, detail=d) for n, ok, d in res], open(os.path.splitext(a.video)[0] + "_qc.json", "w"), indent=2)
    sys.exit(0 if all(ok for _, ok, _ in res) else 1)

if __name__ == "__main__":
    main()
