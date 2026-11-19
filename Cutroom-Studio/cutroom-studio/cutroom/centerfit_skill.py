"""CenterFitClip Skill Bridge.
Strictly executes the CenterFitClip Skill (e:/OpusClips/CenterfitSkill/centerfitclip)
during the Enhance & Polish stage for Center Fit videos.
Full Screen videos remain completely unchanged.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LOG = logging.getLogger(__name__)

# Search paths for the skill package
SKILL_PATHS = [
    Path("e:/OpusClips/CenterfitSkill/centerfitclip"),
    Path(os.path.expanduser("~/.gemini/config/skills/centerfitclip")),
    Path(__file__).parent.parent.parent.parent / "CenterfitSkill" / "centerfitclip",
]

def find_skill_root() -> Path:
    for p in SKILL_PATHS:
        if (p / "scripts" / "analyze.py").is_file() and (p / "scripts" / "render.py").is_file():
            return p.resolve()
    raise RuntimeError("CenterFitClip skill not found. Ensure e:/OpusClips/CenterfitSkill/centerfitclip exists.")


def split_hook(title: str, hook_text: str = "") -> tuple[str, str]:
    """Splits headline into hook line 1 (setup) and line 2 (punchline), following style guide."""
    raw = (hook_text or title or "").strip()
    # Remove bracket tags like [Music]
    import re
    cleaned = re.sub(r"\[.*?\]", "", raw).strip()
    if not cleaned:
        cleaned = "CHECK THIS OUT"
    
    # Try splitting by natural punctuation
    for sep in ("?", "!", ":", "-", "।", "|", ","):
        if sep in cleaned:
            parts = [p.strip() for p in cleaned.split(sep, 1) if p.strip()]
            if len(parts) >= 2:
                h1 = parts[0] + (sep if sep in ("?", "!") else "")
                h2 = parts[1][:45]
                return h1[:35].upper(), h2.upper()

    # Split by word count (first 3-4 words for line 1, rest for line 2)
    words = cleaned.split()
    if len(words) <= 3:
        return "WAIT FOR THIS", cleaned.upper()
    mid = min(4, max(2, len(words) // 2))
    return " ".join(words[:mid]).upper(), " ".join(words[mid:mid + 6]).upper()


def extract_clip_segment(source_path: Path, start_at: float, end_at: float, out_path: Path):
    """Losslessly or near-losslessly cuts the candidate clip segment."""
    dur = max(0.5, end_at - start_at)
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-ss", f"{start_at:.3f}",
        "-t", f"{dur:.3f}",
        "-i", str(source_path),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def build_captions_json(words: list, start_at: float, end_at: float, out_path: Path):
    """Groups words in [start_at, end_at] into natural subtitle cues with relative timestamps."""
    clip_words = [w for w in words if start_at - 0.05 <= w["s"] <= end_at + 0.05]
    if not clip_words:
        out_path.write_text("[]", encoding="utf-8")
        return

    # Group into short cues of 3-6 words or at punctuation
    cues = []
    cur = []
    for w in clip_words:
        cur.append(w)
        rel_s = max(0.0, round(cur[0]["s"] - start_at, 2))
        rel_e = max(rel_s + 0.1, round(cur[-1]["e"] - start_at, 2))
        dur = rel_e - rel_s
        text = " ".join(x.get("t") or x.get("w", "") for x in cur)
        w_text = w.get("t") or w.get("w", "")
        if len(cur) >= 4 or dur >= 1.8 or w_text.endswith((".", "!", "?", "।", "…", ",")):
            cues.append(dict(start=rel_s, end=rel_e, text=text))
            cur = []
    if cur:
        rel_s = max(0.0, round(cur[0]["s"] - start_at, 2))
        rel_e = max(rel_s + 0.1, round(cur[-1]["e"] - start_at, 2))
        cues.append(dict(start=rel_s, end=rel_e, text=" ".join(x.get("t") or x.get("w", "") for x in cur)))

    out_path.write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8")


def execute_centerfit_skill(
    source_video: Path,
    cand: dict,
    transcript_words: list,
    output_mp4: Path,
    progress_cb=None
) -> dict:
    """
    Executes the CenterFitClip Skill strictly through its 5-step workflow:
    1. analyze.py -> content rectangle, automatic second_box detection, audio peaks, scene cuts.
    2. Write text assets -> hook1, hook2, captions.json, reactions.json, teasers.
    3. render.py -> Center Fit 9:16 layout, zoompan punch-zooms, sound design, Hind font typography.
    4. qc.py -> Quality control gate verification.
    5. Returns metadata.
    """
    skill_root = find_skill_root()
    scripts_dir = skill_root / "scripts"
    analyze_py = scripts_dir / "analyze.py"
    render_py = scripts_dir / "render.py"
    qc_py = scripts_dir / "qc.py"

    start_at = cand["s"]
    end_at = cand["e"]
    dur = end_at - start_at

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="centerfit_stage_") as td:
        work = Path(td)
        clip_in = work / "input.mp4"
        analysis_json = work / "analysis.json"
        captions_json = work / "captions.json"
        reactions_json = work / "reactions.json"
        rendered_mp4 = work / "final.mp4"
        report_json = work / "render_report.json"

        # 1. Extract segment
        if progress_cb: progress_cb(10, "Extracting clip segment...")
        extract_clip_segment(source_video, start_at, end_at, clip_in)

        # 2. Step 1: Analyze
        if progress_cb: progress_cb(25, "CenterFitClip: Detecting content rectangle & second box...")
        r_ana = subprocess.run(
            [sys.executable, str(analyze_py), str(clip_in), "--out", str(work)],
            capture_output=True, text=True
        )
        if r_ana.returncode != 0:
            LOG.warning("centerfit_analyze_warning err=%s", r_ana.stderr)

        analysis_data = {}
        if analysis_json.is_file():
            try:
                analysis_data = json.loads(analysis_json.read_text(encoding="utf-8"))
            except Exception: pass

        # 3. Step 2 & 3: Text Assets
        if progress_cb: progress_cb(45, "CenterFitClip: Formulating hook typography & captions...")
        title_for_hook = cand.get("title_overlay") or cand.get("title", "")
        hook_sub = cand.get("hook_line") or cand.get("hook", "")
        hook1, hook2 = split_hook(title_for_hook, hook_sub)
        build_captions_json(transcript_words, start_at, end_at, captions_json)

        # Reaction labels from audio peaks
        peaks = analysis_data.get("audio", {}).get("peaks", [])
        reactions = []
        labels = ["WHOA!", "NO WAY!", "WATCH THIS!", "WAIT!", "LOOK!"]
        for i, p in enumerate(peaks):
            reactions.append(dict(time=p, text=labels[i % len(labels)]))
        reactions_json.write_text(json.dumps(reactions, indent=2), encoding="utf-8")

        # Teasers for open-loops
        teaser_mid = "WAIT, WATCH WHAT HAPPENS..." if dur >= 15 else ""
        teaser_late = "DON'T MISS THE END!" if dur >= 20 else ""

        # 4. Step 4: Render
        if progress_cb: progress_cb(60, "CenterFitClip: Rendering 9:16 layout, punch-zooms & sound design...")
        bg_style = cand.get("background_style") or cand.get("edit", {}).get("background_style", "blur")
        if bg_style not in ("blur", "black", "white"):
            bg_style = "blur"
        render_cmd = [
            sys.executable, str(render_py),
            str(clip_in), str(analysis_json),
            "--hook1", hook1,
            "--hook2", hook2,
            "--captions", str(captions_json),
            "--reactions", str(reactions_json),
            "--bg-style", bg_style,
            "--out", str(rendered_mp4),
        ]
        if teaser_mid:
            render_cmd.extend(["--teaser-mid", teaser_mid])
        if teaser_late:
            render_cmd.extend(["--teaser-late", teaser_late])

        r_ren = subprocess.run(render_cmd, capture_output=True, text=True)
        if r_ren.returncode != 0:
            LOG.error("centerfit_render_failed err=%s", r_ren.stderr)
            raise RuntimeError(f"CenterFitClip render failed: {r_ren.stderr[:500]}")

        # 5. Step 5: QC Gate
        if progress_cb: progress_cb(85, "CenterFitClip: Running automated QC gate...")
        qc_passed = True
        qc_details = ""
        r_qc = subprocess.run(
            [
                sys.executable, str(qc_py),
                str(rendered_mp4),
                "--source", str(clip_in),
                "--analysis", str(analysis_json),
                "--report", str(report_json),
            ],
            capture_output=True, text=True
        )
        if r_qc.returncode != 0:
            qc_passed = False
            qc_details = r_qc.stdout
            LOG.info("centerfit_qc_nonfatal output=%s", qc_details)

        # 6. Finalize output
        if progress_cb: progress_cb(95, "CenterFitClip: Finalizing output...")
        import shutil
        shutil.copyfile(str(rendered_mp4), str(output_mp4))

        sec_box = analysis_data.get("layout", {}).get("second_box", {})
        return dict(
            skill="CenterFitClip",
            second_box_visible=sec_box.get("visible", False),
            second_box_reason=sec_box.get("reason", ""),
            hook1=hook1,
            hook2=hook2,
            qc_passed=qc_passed,
            output_file=str(output_mp4),
            duration=dur
        )
