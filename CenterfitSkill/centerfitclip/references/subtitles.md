# Subtitles, hook text and language accuracy

## Golden rules
1. **Language = the video's language.** Hindi speech -> Devanagari (not Hinglish/romanized) unless the user asks. English -> English. Mixed -> mirror the speaker.
2. **Never invent speech.** Captions come from real transcription (`scripts/transcribe.py`, Whisper) and are proof-read. No transcription tool = no captions; say so.
3. **Never double-subtitle.** If the source already has burned-in subtitles (common in reaction videos), keep them fully visible (that's why the content rectangle is detected, not guessed) and add nothing in the same zone.
4. **Hook/labels/teasers are editorial text, not quotes.** Write them in the viewer's language from what the video actually shows. Don't attribute words to people unless they said them.
5. Fix misheard names/terms; keep fillers only if they carry emotion; keep numbers/names exact.

## Hindi specifics
- Use the bundled Hind Bold (correct conjuncts/matras; verified rendering of "क्या", "हैं?!"). Never fall back to a Latin-only font for Devanagari.
- Don't split a word across lines; wrap at ~28 characters, max 2 lines.
- Punctuation: "?!" and "..." fine; avoid emoji (not rendered, looks cheap).

## Styling
- Captions (when generated): 44 px white, 5 px black outline, centered, inside the clip's lower third, <= 2 lines, 1-2.5 s each, appear exactly with speech (+-0.1 s).
- Hook: 2 lines, <= ~6 words per line, line 2 emphasized in yellow.
- Reaction labels: 2-3 words, one emotion each, from the real peak, 1.0 s.
- Teasers: short promise, 2.6-2.8 s, below the block.
- Everything readable on a phone at arm's length: contrast against backdrop, outline, no overlap with the face.

## Reaction labels when no transcript exists
Use short, neutral exclamations that fit any reaction (e.g. "अरे यार!", "ये क्या था?!"), keep them sparse, and **tell the user they are generic**. Replace them with what the speaker really says when a transcript is available.

## JSON formats
`reactions.json`: `["text1","text2",...]` (assigned to detected peaks in order) or `[{"time":3.25,"text":"..."}]`.
`captions.json`: `[{"start":0.0,"end":1.8,"text":"..."}]`.
