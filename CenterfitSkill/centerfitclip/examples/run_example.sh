#!/usr/bin/env bash
# python scripts/analyze.py in.mp4 --out work/   (then LOOK at work/contact_sheet.jpg)
python scripts/analyze.py in.mp4 --out work/
python scripts/render.py in.mp4 work/analysis.json \
  --hook1 "भाई ये लोग" --hook2 "क्या कर रहे हैं?!" \
  --reactions examples/reactions.json \
  --teaser-mid "रुको... असली मज़ा आगे है" --teaser-late "आखिरी सीन मिस मत करना!" \
  --out work/final.mp4
python scripts/qc.py work/final.mp4 --source in.mp4 --analysis work/analysis.json --report work/render_report.json
