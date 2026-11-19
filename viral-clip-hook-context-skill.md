# Viral Clip Hook & Context Optimization Skill

## 0. Purpose and mandatory rule

You receive a candidate clip (a high-scoring "peak" moment from a long video). Your job is NOT to find the peak. It is to **choose the start and end points, and the opening treatment, so a stranger understands and cares within 3 seconds.**

**NEVER start a clip at a random point because that point holds the best statement.**

Before approving any clip, answer this about the first 3 seconds (audio + visible text + visuals together):

> "If someone who has never seen this video watches only the first 3 seconds, will they know (1) what the topic/situation is, (2) who is speaking and why they matter, (3) why to keep watching?"

Any "no" = fix the opening. Priorities: **Clarity > Curiosity > Continuity.**

## 1. Inputs and outputs

**Inputs:** word-level transcript with timestamps; speaker diarization (speaker IDs, turn boundaries); peak segment `[peak_start, peak_end]`; optional: 1 fps frames, video title/description, speaker names; max clip length (default 60s).

**Output (JSON):**
```json
{
  "start": 0.0, "end": 0.0,
  "opening_strategy": "natural_start | title_overlay | cold_open_then_context | walk_back_compressed",
  "title_overlay": "string or null",
  "cold_open": {"src_start": 0.0, "src_end": 0.0} ,
  "cuts": [{"from": 0.0, "to": 0.0, "reason": "filler|dead_air|tangent"}],
  "scores": {"clarity": 0, "curiosity": 0, "continuity": 0},
  "flags": [],
  "approved": true
}
```

## 2. What the viral reference clips teach (principles, not templates)

Two Hinglish podcast shorts (an actor describing an extreme film-prep workout; a comedian answering "what makes my husband special") share this structure:

1. **Topic is pinned in frame 0 by a persistent title overlay**, so even a mid-thought first spoken line is understood. Context can come from *text*, not only from preceding dialogue.
2. **The first spoken beat is a question or an unfinished promise** (an interviewer's question; "when I did it back then..."). The viewer has an open loop before the payoff arrives.
3. **A concrete specific lands in the first ~4s** (a number like "3.5 hours", or a direct answer/"no"), so curiosity is earned immediately.
4. **Something changes on screen every ~2-3s**: reaction cuts to the listener, archive photos/footage illustrating the words, side-by-side contrast.
5. **Escalation or emotional build**: numbers climb (200 → 300 → 500), or a story moves from awkward start to a sincere confession. Each beat tops the last.
6. **Ends on the peak or emotional close**, not on trailing small talk.
7. **Context is short**: the setup is one question or one line, never a monologue of backstory.

## 3. Step-by-step process

**Step 1. Segment into thought units.** Split transcript at sentence ends, speaker turns, and pauses > 0.6s. Index units `U1..Un`. Locate the unit containing `peak_start` = `Up`.

**Step 2. Identify the hook line (§4)** inside the peak region. This is the line you want the viewer to be waiting for or to hear first.

**Step 3. Run the context dependency test (§5)** on `Up`. If it passes, go to Step 6.

**Step 4. Walk back (§6)** to find the minimal preceding material that resolves every dependency.

**Step 5. Choose the opening strategy (§7).**

**Step 6. Set boundaries and tighten (§8, §9).**

**Step 7. Run the QC simulation and checklist (§10, §12).** Fix and re-run, max 3 iterations. If it still fails, reject the clip (do not ship a confusing one).

## 4. Hook identification system

Score each unit in the clip window; the first unit scoring ≥ 2 with no context dependency is a valid opener.

| Signal | Points |
|---|---|
| Direct question that frames a topic ("What makes X special?") | 2 |
| Specific number, name, or superlative stated as fact | 2 |
| Surprising/contrarian claim ("Honestly, no.") | 2 |
| Vivid concrete image or scene ("2 AM, my father was in the ICU") | 2 |
| Stakes or consequence stated ("I could have lost everything") | 1 |
| Open loop: promise of reveal ("the reason is something nobody expects") | 1 |
| Conflict/disagreement between speakers | 1 |
| Emotional peak (laughter, crack in voice, shock) | 1 |
| Generic opener ("So", "Yeah", "Well", "You know") | -2 |
| Mid-sentence start | -3 |

Hook types to label: `question`, `number`, `claim`, `scene`, `stakes`, `conflict`, `emotion`.

## 5. Context detection system

Compute red flags on the **first sentence** (and first 8 words) of the candidate start. Each flag = 1 dependency.

- **R1 Unresolved pronoun/demonstrative:** he, she, it, they, this, that, there; Hindi: yeh, woh, usne, uska, iska, wahan. Referent not stated within the clip so far.
- **R2 Connective opener:** but, so, and, because, also, then, anyway; toh, lekin, aur, phir, isliye.
- **R3 Answer without question:** yes/no/exactly/right/correct/"that's what I mean" with no preceding question in the clip.
- **R4 Mid-sentence/mid-thought:** previous word in source has no sentence boundary, or the sentence starts lowercase / with a clause fragment.
- **R5 Missing entity:** a person, product, place, or event referenced by role or name the viewer cannot place (the wife, the deal, that movie).
- **R6 Orphan number/comparison:** "200", "twice as much", "even more" with no baseline.
- **R7 Back-reference:** "like I said", "as we discussed", "going back to".
- **R8 Wrong speaker first:** clip starts on a listener's reaction/filler or a speaker whose role is unknown.
- **R9 Dead/low-energy start:** first 1.5s is silence, laughter tail, filler, or the end of someone else's sentence.

**Rule:** 0 flags = pass. Any flag = the opening must be fixed (§6-§7). R4 and R9 are fixed by boundary snapping alone; R1-R3, R5-R8 need context.

**Override:** a mid-thought start (R4) or an unresolved referent (R1/R5) is acceptable ONLY IF a title overlay on screen from frame 0 names the topic AND the first spoken line is itself a hook (score ≥ 2 in §4). Both reference clips rely on this. Without the overlay, R4 is a hard fail.

## 6. Finding the necessary preceding dialogue (walk-back)

Starting at `Up`, step backward one thought unit at a time. After each step, re-run §5 on the new first unit **and** check that every referent used in `Up..peak` is now defined. Stop at the first unit that satisfies **one** of:

1. It is a **question** (from either speaker) that the peak answers. Best stopping point.
2. It is the **first introduction of the topic** (topic noun phrase, event, or person first named).
3. It resolves the **last remaining** dependency.

Limits: max 3 turns back and max 20s of source. If the resolving material is longer than the **context budget (§8)**, do not include it all. Use compression (§7, strategy D) or switch to title overlay / cold open.

Prefer **speaker-turn boundaries**: a question + the answer's first sentence is the ideal minimal context.

## 7. Constructing the opening: choose one strategy

Evaluate in this order and take the first that works.

**A. Natural start.** The walk-back unit already passes §5 and is itself a hook (typically a good question). Cut there. Use when setup ≤ 6s.

**B. Title overlay (context by text).** Peak is understandable once the topic is known, but spoken setup is long or absent. Add a persistent on-screen title (≤ 9 words) for the whole clip, as in both reference clips. Start at the cleanest sentence start at or before the peak. Use when only R1/R5 flags remain and the topic can be named.

**C. Cold open, then context.** The setup is dull but the peak contains a killer line. Open with the single strongest verbatim line (1.5-4s, must be a complete thought and pass §5 itself, or sit under a title overlay), then cut to the natural start and play forward through the peak. Rules: line is verbatim and not altered; the later full scene must contain or follow it; never reorder in a way that changes the meaning or makes the speaker appear to say something they did not. Flag `reordered: true`.

**D. Walk-back compressed.** Context exists but is long. Include it with jump cuts: remove tangents, filler, repeated words, pauses > 0.5s, keeping only the sentences needed to resolve dependencies. Never splice mid-clause so that the meaning changes.

**Title overlay writing rules (strategies B/C):**
- Built only from facts present in the transcript/metadata (names, topic, claim). Never add claims, numbers, or outcomes the speaker did not state.
- Name the topic and, when possible, the question being answered ("What makes Harsh special", "Crazy Ghajini workout").
- It must not promise what the clip does not deliver (no bait-and-switch).
- Must entail correctly: run an entailment check, title vs. transcript. Fail = rewrite.

## 8. Boundaries, length and pacing

- **Start:** snap to 0.15-0.3s before the first word of the chosen unit, on a pause/breath. Never begin on a trailing laugh, filler, a half word, or the end of another speaker's sentence.
- **Context budget:** setup before the first hook-scoring beat ≤ 6s, hard cap 8s, and ≤ 25% of total clip. First hook-scoring beat must occur by **3s** (strategies B/C count the title/cold open).
- **End:** last word + 0.3-0.6s, on a completed sentence, ideally on the payoff, emotional close, or punchline. Trim trailing pleasantries ("yeah, thanks", "anyway"). No dead tail, no outro unless a brand card is requested.
- **Length:** shortest clip that includes the context, the build and the payoff. Typical 20-60s. Do not pad.

## 9. Retention rules

1. **Re-hook every 5-8s:** a new fact, number, contrast, joke, question, or shift in emotion. If a 10s stretch has none, cut it or tighten it.
2. **Visual change every 2-4s** when video allows: reaction shots, B-roll/archive images illustrating spoken nouns, punch-ins, split-screen contrast. (Output as edit hints.)
3. **Tighten:** cut filler (um, uh, you know), repeated starts, pauses > 0.5s. Keep pauses that carry comedic or dramatic timing (before a punchline, after a revelation).
4. **Escalation:** if the content has a ladder (numbers rising, stakes growing), keep all rungs; drop flat ones.
5. **Captions:** word-level, large, high contrast, from the first frame.
6. **Payoff check:** the clip must resolve the loop opened in the first 3s. If the loop is not closed before `end`, extend the end or drop the clip.

## 10. Quality-control simulation

Run the **cold viewer test**: give a reviewer model only (a) the first 3s of transcript, (b) the title overlay, (c) any text on screen. Ask:

1. What is this about? 2. Who is speaking / what is their situation? 3. What would you expect to learn next?

Pass only if answers 1 and 2 are specific and correct, and answer 3 matches what the clip actually delivers. Also run: **full-clip fidelity test** (does the edited clip preserve each speaker's meaning?).

## 11. Bad vs. improved openings

| Bad (random fragment) | Why it fails | Improved |
|---|---|---|
| "...and that's why she left, honestly." | R1, R2: who is "she"? | Start at the interviewer's question "Why did your co-founder leave?" then the answer. (A) |
| "Phir main bola 500 karta hu." (peak of workout story) | R2, R6: no baseline, no topic | Title: "Crazy workout for a film role" and start at the line that sets the baseline: first "200 kiye", then "300", then "500". (B, keep escalation) |
| "Tu ekdam patla, aur main 80 kilo ki." | R1, R5: who is "tu"? | Start at the question "What makes Harsh special?" + her first answer, with that title throughout. (A/B) |
| "Yes, exactly, that's the mistake." | R3, R7 | Walk back to the question/claim it agrees with; if long, cold-open on the speaker's strongest verbatim line, then context. (C) |
| "So the thing is, um, we raised..." | R2, R9 filler | Snap to "We raised $5M with no product" (drop "So the thing is, um"). |
| Clip ends "...and yeah, thanks for having me." | dead tail | End on the last payoff sentence + 0.4s. |

Note: table examples for the two reference clips are illustrative of *how the fix works*; the originals already apply the fix.

## 12. Final checklist (all must be YES to approve)

- [ ] First sentence has 0 context red flags (§5), or the title/context resolves each.
- [ ] A hook-scoring beat (§4) occurs by 3s.
- [ ] Topic is identifiable in 3s from audio or on-screen text (cold viewer test passed).
- [ ] Speaker identity/role is clear or visible (name caption or earlier line).
- [ ] Context ≤ 6s (hard cap 8s) and ≤ 25% of clip; no setup monologue.
- [ ] Start snapped to a clean sentence/breath; no filler, half word, or another speaker's tail.
- [ ] Peak moment fully preserved, in order (or reordering flagged and verbatim).
- [ ] Opening leads naturally into the peak (no tonal or topical jump).
- [ ] Open loop from the opening is paid off before the end.
- [ ] Re-hook at least every 8s; dead air/filler removed.
- [ ] Ends on payoff/close, no dead tail.
- [ ] Title overlay (if any) is derived from the transcript, accurate, not clickbait.
- [ ] Scores: clarity, curiosity, continuity each ≥ 1 of 2 and total ≥ 5 of 6.
- [ ] Nothing invented, nothing meaning-altering.

If any item fails: apply the fix, re-run (max 3 iterations). If it still fails, **reject** the clip and pick the next-best candidate.

---

# ADDENDUM v2: Implementation, prompts, edge cases, calibration

## A. Reference algorithm (pseudo-code)

```python
def optimize_clip(units, peak, cfg):
    # units: [{id, start, end, speaker, text, words}] ; peak: (start, end)
    p = unit_containing(units, peak.start)
    hook = best_hook_unit(units, peak)            # §4 scores, returns unit + type

    # 1. snap and test the natural start
    start_idx = p.id
    flags = context_flags(units[start_idx], units, start_idx)   # R1..R9

    # 2. walk back until dependencies resolve (max 3 turns / 20s)
    i = start_idx
    while flags and steps(i, start_idx) < 3 and (units[start_idx].start - units[i].start) < 20:
        i -= 1
        u = units[i]
        if is_framing_question(u, units[start_idx:]) or introduces_topic(u) or resolves_all(u, units[i:], flags):
            start_idx = i
            flags = context_flags(units[i], units, i)
            break

    setup_len = hook.start - units[start_idx].start

    # 3. choose strategy
    if not flags and setup_len <= cfg.ctx_budget:             strategy = "natural_start"
    elif only(flags, {"R1","R4","R5"}) and can_title(units):  strategy = "title_overlay"
    elif hook_is_standalone(hook) and setup_len > cfg.ctx_budget: strategy = "cold_open_then_context"
    elif setup_len > cfg.ctx_budget:                          strategy = "walk_back_compressed"
    else:                                                     return reject("unresolvable_context")

    clip = build(units, start_idx, peak, strategy)
    clip = snap_boundaries(clip)       # §8
    clip = tighten(clip)               # §9 filler / pauses > 0.5s (keep timing pauses)
    for _ in range(3):
        report = qc(clip)              # cold-viewer test + checklist
        if report.passed: return approve(clip, report)
        clip = apply_fix(clip, report.failures)
    return reject(report.failures)
```

Defaults: `ctx_budget=6s` (hard cap 8s), `hook_deadline=3s`, `max_ctx_ratio=0.25`. Treat as starting values; calibrate with §E.

## B. Cold-viewer test prompt (use verbatim)

```
You are a stranger scrolling short videos. You know NOTHING about the source video.
You see only: (1) the on-screen title: "{title}" (2) the first 3 seconds of captions: "{first_3s_text}".
Answer in JSON:
{"topic": "...", "who_is_speaking": "...", "what_i_expect_next": "...", "would_keep_watching": true|false, "confusion": "what, if anything, I don't understand"}
Be literal. If something is unclear, say so. Do not guess.
```
Then compare: `topic` and `who_is_speaking` must be specific (not "unclear"), `what_i_expect_next` must match the clip's actual payoff (check with a second call that sees the whole clip). `would_keep_watching=false` or non-empty `confusion` = fail.

## C. Title overlay prompt + entailment check

```
Write ONE on-screen title (max 9 words, same language style as the speakers) for this clip.
Use only names, topics, and claims that appear in the transcript below. State the topic or the question being answered.
Do not add numbers, outcomes, or claims the speakers did not say. No misleading bait.
Transcript: {clip_transcript}
```
Entailment check (second call): "Is every claim in this title directly supported by the transcript? Answer YES/NO and quote the supporting line." NO = rewrite. Reject titles that promise something the clip does not deliver.

## D. Edge cases

- **Solo monologue (no question to walk back to):** look for the speaker's thesis sentence or the start of the story ("So in 2019 I..."). If none within 20s, use strategy B with a title built from the thesis, or C with the strongest self-contained line.
- **Long setup story (needs > 8s of context):** do NOT include it all. Prefer C (cold open on the punchline-adjacent line) or D (jump-cut to the minimal story beats: who, what, stakes). If neither stays truthful, reject.
- **Mixed language (e.g. Hinglish):** tokenize and score hooks/flags on the original language; include Hindi/other pronouns, connectives and fillers in R1/R2/R9 lists; write the title in the dominant language of the speakers; captions keep the speaker's own words.
- **No speaker labels:** infer turns from pauses > 0.8s, voice change, and question marks; if uncertain, don't treat a boundary as a speaker turn.
- **Peak is a reaction/laugh:** include the line that caused it; start at the setup of that line, not at the laugh.
- **Debate/conflict:** start at the claim being challenged, not the rebuttal.
- **Tutorial/how-to:** the hook is the outcome or the common mistake ("Most people do X wrong"); context = what is being built; don't start mid-step.
- **Interview where the subject is unknown to viewers:** put name + role in the title or a caption in the first 3s.

## E. Calibration test (do before trusting thresholds)

1. Take 20 real candidate clips across content types. Generate the baseline (raw peak start) and the optimized version.
2. Have 3 reviewers (or the cold-viewer prompt) rate both on clarity/curiosity/continuity (0-2) without knowing which is which.
3. Track real metrics when published: 3s hold rate, average watch time, completion rate, shares.
4. Adjust `ctx_budget`, `hook_deadline`, and the hook score weights to maximize 3s hold and completion. Log every rejected clip and its failure reason; frequent reasons show which rules need tuning.
5. Re-run quarterly; platform behavior changes.
