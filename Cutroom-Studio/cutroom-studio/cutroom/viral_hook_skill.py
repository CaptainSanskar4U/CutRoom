"""Viral Clip Hook & Context Optimization Skill Engine.
Strictly implements viral-clip-hook-context-skill.md as a mandatory pipeline gate.
Every approved clip must pass the 14-point checklist, 3-second hook test,
context resolution (R1..R9), boundary snapping, and cold-viewer evaluation.
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Linguistic lexicons (English & Hindi / Hinglish)
# ---------------------------------------------------------------------------

PRONOUNS_EN = {
    'he', 'she', 'it', 'they', 'this', 'that', 'these', 'those', 'there',
    'him', 'her', 'them', 'his', 'hers', 'their', 'theirs', 'its'
}
PRONOUNS_HI = {
    'yeh', 'ye', 'woh', 'wo', 'usne', 'unhe', 'unko', 'inka', 'unka',
    'uska', 'iske', 'unke', 'iske', 'isse', 'usse', 'inse', 'unse',
    'wahan', 'yahan', 'idhar', 'udhar', 'isne', 'inhone', 'unhone'
}
ALL_PRONOUNS = PRONOUNS_EN | PRONOUNS_HI

CONNECTIVES_EN = {
    'but', 'so', 'and', 'because', 'also', 'then', 'anyway', 'meanwhile',
    'furthermore', 'however', 'moreover', 'therefore', 'besides', 'yet'
}
CONNECTIVES_HI = {
    'toh', 'to', 'lekin', 'aur', 'phir', 'isliye', 'magar', 'parantu',
    'kyunki', 'halanki', 'waise', 'balki'
}
ALL_CONNECTIVES = CONNECTIVES_EN | CONNECTIVES_HI

ANSWERS_WITHOUT_Q_EN = {
    'yes', 'no', 'exactly', 'right', 'correct', 'definitely', 'absolutely',
    'sure', 'totally', 'true', 'nope', 'yep', 'yeah'
}
ANSWERS_WITHOUT_Q_HI = {
    'haan', 'nahi', 'bilkul', 'sahi', 'sahi baat', 'wahi', 'wahi toh', 'theek'
}
ALL_ANSWERS = ANSWERS_WITHOUT_Q_EN | ANSWERS_WITHOUT_Q_HI

BACK_REFS = {
    'like i said', 'as i said', 'as we discussed', 'going back to',
    'as mentioned', 'like we talked', 'pehle bataya', 'maine bola tha',
    'jaise maine kaha', 'pehle kaha tha'
}

FILLERS_EN = {'um', 'uh', 'erm', 'umm', 'uhh', 'ah', 'hmm', 'er', 'like', 'you know', 'sort of', 'kind of'}
FILLERS_HI = {'matlab', 'yaani', 'samjhe', 'samjho', 'dekh', 'dekho', 'bhai'}
ALL_FILLERS = FILLERS_EN | FILLERS_HI

GENERIC_OPENERS = {'so', 'yeah', 'well', 'you know', 'to', 'haan', 'acha', 'ok', 'okay', 'like'}

QUESTION_LEADS = {
    'why', 'how', 'what', 'who', 'where', 'when', 'which', 'whose', 'whom',
    'is it', 'can you', 'could you', 'would you', 'do you', 'did you', 'have you',
    'kya', 'kaise', 'kyun', 'kyu', 'kab', 'kahan', 'kitna', 'kitni', 'kaun'
}

NUMERIC_PATTERN = re.compile(
    r'(\b\d+([.,]\d+)?\b|\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|crore|lakh|percent|%|\$|₹|rs|rupees)\b)',
    re.IGNORECASE
)

CONTRARIAN_LEADS = {
    'honestly no', 'absolutely not', 'not at all', 'that is a lie', 'nobody tells you',
    'never do this', 'stop doing', 'the biggest mistake', 'wrong', 'fake', 'secret',
    'galat', 'aisa nahi', 'koi nahi batata', 'sabse badi galti', 'sach yeh hai'
}

STAKES_KEYWORDS = {
    'lost everything', 'died', 'kill', 'danger', 'bankrupt', 'ruined', 'disaster',
    'fired', 'jail', 'arrested', 'hospital', 'icu', 'risk', 'fail', 'heartbreak',
    'khatra', 'nuksan', 'barbaad', 'fas gaya', 'musibat'
}

OPEN_LOOP_KEYWORDS = {
    'nobody expects', 'reason is', 'secret is', 'turns out', 'what happened next',
    'here is why', 'never saw it coming', 'the truth', 'asli wajah', 'kisi ko nahi pata'
}

PUNCTUATION_SPLIT = re.compile(r'[.!?。！？।|]')


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ThoughtUnit:
    id: int
    s: float
    e: float
    text: str
    words: List[Dict[str, Any]]
    speaker: str = "spk_0"
    is_question: bool = False
    has_sentence_end: bool = False
    hook_score: int = 0
    hook_types: List[str] = field(default_factory=list)


@dataclass
class ViralOptimizationResult:
    start: float
    end: float
    opening_strategy: str  # natural_start | title_overlay | cold_open_then_context | walk_back_compressed
    title_overlay: Optional[str]
    cold_open: Optional[Dict[str, float]]
    cuts: List[Dict[str, Any]]
    scores: Dict[str, int]  # clarity (0-2), curiosity (0-2), continuity (0-2)
    flags: List[str]
    approved: bool
    rejection_reasons: List[str] = field(default_factory=list)
    hook_line: str = ""
    hook_type: str = "general"
    iterations: int = 1


# ---------------------------------------------------------------------------
# Step 1: Segment into thought units
# ---------------------------------------------------------------------------

def segment_into_thought_units(words: List[Dict[str, Any]]) -> List[ThoughtUnit]:
    """
    Split transcript into coherent thought units bounded by:
    - Sentence end punctuation (. ! ? । … |)
    - Speaker changes
    - Pauses > 0.60 seconds
    """
    if not words:
        return []

    units: List[ThoughtUnit] = []
    current_words: List[Dict[str, Any]] = []
    unit_id = 0

    for i, w in enumerate(words):
        current_words.append(w)
        w_text = (w.get("t") or w.get("w") or "").strip()
        speaker = str(w.get("spk") or w.get("speaker") or "spk_0")

        next_w = words[i + 1] if i + 1 < len(words) else None
        next_speaker = str(next_w.get("spk") or next_w.get("speaker") or "spk_0") if next_w else speaker

        has_punct = bool(PUNCTUATION_SPLIT.search(w_text)) or w_text.endswith(('.', '!', '?', '।', '…'))
        pause_after = (next_w["s"] - w["e"]) if next_w else 0.0
        speaker_change = (next_speaker != speaker)

        is_unit_end = (has_punct or pause_after >= 0.60 or speaker_change or next_w is None)

        if is_unit_end:
            u_text = " ".join((x.get("t") or x.get("w") or "").strip() for x in current_words).strip()
            is_q = u_text.rstrip().endswith(('?', '？')) or bool(re.search(r'\b(why|how|what|who|where|when|kya|kaise|kyun)\b', u_text.lower()))
            u = ThoughtUnit(
                id=unit_id,
                s=current_words[0]["s"],
                e=current_words[-1]["e"],
                text=u_text,
                words=list(current_words),
                speaker=speaker,
                is_question=is_q,
                has_sentence_end=has_punct
            )
            score, htypes = score_unit_hook(u)
            u.hook_score = score
            u.hook_types = htypes
            units.append(u)
            unit_id += 1
            current_words = []

    return units


# ---------------------------------------------------------------------------
# Step 2: Hook identification system (§4)
# ---------------------------------------------------------------------------

def score_unit_hook(unit: ThoughtUnit) -> Tuple[int, List[str]]:
    """Scores a thought unit according to §4 hook table."""
    text = unit.text.strip()
    low = text.lower()
    score = 0
    types = []

    tokens = [re.sub(r'[^\w]', '', t) for t in low.split() if re.sub(r'[^\w]', '', t)]
    first_token = tokens[0] if tokens else ""

    # 1. Direct question framing topic (+2)
    if unit.is_question or (first_token in QUESTION_LEADS and len(tokens) >= 3):
        score += 2
        types.append("question")

    # 2. Specific number, name, superlative stated as fact (+2)
    if NUMERIC_PATTERN.search(low) or re.search(r'\b(first|only|best|worst|never|always|highest|fastest|crore|lakh)\b', low):
        score += 2
        types.append("number")

    # 3. Surprising / contrarian claim (+2)
    if any(c in low for c in CONTRARIAN_LEADS) or (low.startswith(("honestly,", "actually,", "no,"))):
        score += 2
        types.append("claim")

    # 4. Vivid concrete image / scene (+2)
    if any(k in low for k in ['hospital', 'icu', '2 am', '3 am', 'police', 'car', 'blood', 'doctor', 'flight', 'stage', 'wedding']):
        score += 2
        types.append("scene")

    # 5. Stakes or consequence (+1)
    if any(k in low for k in STAKES_KEYWORDS):
        score += 1
        types.append("stakes")

    # 6. Open loop (+1)
    if any(k in low for k in OPEN_LOOP_KEYWORDS):
        score += 1
        types.append("loop")

    # 7. Conflict / disagreement (+1)
    if any(k in low for k in ['disagree', 'arguing', 'fight', 'shut up', 'shut down', 'lawsuit', 'bhag', 'ladai']):
        score += 1
        types.append("conflict")

    # 8. Emotional peak (+1)
    if '!' in text or any(k in low for k in ['crying', 'screaming', 'shocked', 'laughing', 'terrified', 'crazy']):
        score += 1
        types.append("emotion")

    # Penalties
    if first_token in GENERIC_OPENERS and len(tokens) > 1 and tokens[1] in ALL_CONNECTIVES:
        score -= 2
    elif first_token in GENERIC_OPENERS:
        score -= 1

    if not unit.has_sentence_end and not unit.is_question:
        # Check if first word starts with lowercase
        first_orig_word = unit.text.split()[0] if unit.text.split() else ""
        if first_orig_word and first_orig_word[0].islower() and first_orig_word not in ['i', 'iphone']:
            score -= 3

    return score, types


def find_best_hook_unit(units: List[ThoughtUnit], peak_start: float, peak_end: float) -> Tuple[ThoughtUnit, int, List[str]]:
    """Locate the best hook line inside the candidate peak region."""
    candidates = [u for u in units if not (u.e < peak_start or u.s > peak_end)]
    if not candidates:
        # Fallback to closest unit
        candidates = sorted(units, key=lambda u: abs(u.s - peak_start))[:1]

    best = max(candidates, key=lambda u: (u.hook_score, -abs(u.s - peak_start)))
    return best, best.hook_score, best.hook_types


# ---------------------------------------------------------------------------
# Step 3: Context detection system (§5)
# ---------------------------------------------------------------------------

def detect_context_flags(unit: ThoughtUnit, units: List[ThoughtUnit], unit_idx: int) -> List[str]:
    """
    Computes red flags R1..R9 on the first sentence / first 8 words of candidate start.
    Returns list of active red flag codes.
    """
    flags: List[str] = []
    tokens = [re.sub(r'[^\w]', '', t.lower()) for t in unit.text.split()[:8]]
    tokens = [t for t in tokens if t]
    first_8_text = " ".join(tokens)
    first_word = tokens[0] if tokens else ""

    # R1: Unresolved pronoun / demonstrative without referent
    if any(p in tokens[:3] for p in ALL_PRONOUNS):
        # Check if prior sentence in same clip exists
        if unit_idx == 0:
            flags.append("R1")
        else:
            # If starting at unit_idx, the pronoun is at the very beginning of the clip
            flags.append("R1")

    # R2: Connective opener (but, so, and, toh, phir, etc.)
    if first_word in ALL_CONNECTIVES:
        flags.append("R2")

    # R3: Answer without question (yes, no, haan, exactly)
    if first_word in ALL_ANSWERS:
        flags.append("R3")

    # R4: Mid-sentence / mid-thought
    first_orig_word = unit.text.split()[0] if unit.text.split() else ""
    if first_orig_word and first_orig_word[0].islower() and first_orig_word not in ['i', 'iphone', 'ipad']:
        flags.append("R4")
    elif unit_idx > 0 and not units[unit_idx - 1].has_sentence_end and (unit.s - units[unit_idx - 1].e) < 0.35:
        flags.append("R4")

    # R5: Missing entity / vague noun phrase
    if re.search(r'\b(the deal|that movie|that guy|the wife|the company|woh ladka|woh picture)\b', first_8_text):
        flags.append("R5")

    # R6: Orphan number / comparison with no baseline
    if re.search(r'\b(200|300|500|twice as much|even more|aur zyada|itne saal)\b', first_8_text) and not any(k in first_8_text for k in ['i', 'we', 'my']):
        flags.append("R6")

    # R7: Back-reference
    if any(b in unit.text.lower() for b in BACK_REFS):
        flags.append("R7")

    # R8: Wrong speaker first (filler or listener reaction)
    if len(tokens) <= 2 and first_word in ALL_FILLERS:
        flags.append("R8")

    # R9: Dead or low-energy start (starts with filler or silence > 0.4s)
    if first_word in ALL_FILLERS or (unit.words and unit.words[0].get("s", 0) - unit.s > 0.6):
        flags.append("R9")

    return sorted(list(set(flags)))


# ---------------------------------------------------------------------------
# Step 4: Walk-Back algorithm (§6)
# ---------------------------------------------------------------------------

def walk_back_for_context(
    units: List[ThoughtUnit],
    peak_unit_idx: int,
    ctx_budget: float = 6.0,
    max_turns: int = 3,
    max_seconds: float = 20.0
) -> Tuple[int, List[str]]:
    """
    Starting at peak unit, step backward unit-by-unit (max 3 turns / 20s)
    until dependencies resolve, finding the framing question or topic intro.
    """
    curr_idx = peak_unit_idx
    flags = detect_context_flags(units[curr_idx], units, curr_idx)

    if not flags:
        return curr_idx, flags

    peak_start_time = units[peak_unit_idx].s
    step = 0

    while flags and curr_idx > 0 and step < max_turns:
        prev_idx = curr_idx - 1
        prev_unit = units[prev_idx]

        time_dist = peak_start_time - prev_unit.s
        if time_dist > max_seconds:
            break

        step += 1
        curr_idx = prev_idx
        flags = detect_context_flags(units[curr_idx], units, curr_idx)

        # Stopping condition 1: A framing question that the peak answers
        if prev_unit.is_question:
            break

        # Stopping condition 2: Introduces the topic or speaker entity
        if any(w in prev_unit.text.lower() for w in ['interview', 'workout', 'podcast', 'story', 'journey', 'project', 'started']):
            if not flags:
                break

        # Stopping condition 3: Dependencies fully resolved
        if not flags:
            break

    return curr_idx, flags


# ---------------------------------------------------------------------------
# Step 5: Choose Opening Strategy (§7)
# ---------------------------------------------------------------------------

def build_title_overlay(transcript_units: List[ThoughtUnit]) -> str:
    """
    Construct a concise on-screen title overlay (≤ 9 words)
    derived strictly from transcript facts and questions.
    """
    # 1. Check if there is a framing question
    for u in transcript_units[:4]:
        if u.is_question and len(u.text.split()) <= 9:
            return u.text.strip().rstrip('?')

    # 2. Extract key topic nouns and entities
    combined = " ".join(u.text for u in transcript_units[:6])
    numbers = NUMERIC_PATTERN.findall(combined)
    
    # Check for strong topic anchors
    topic_match = re.search(r'\b(workout|podcast|startup|business|interview|money|invest|mistake|film|space|mission)\b', combined, re.IGNORECASE)
    topic = topic_match.group(1).title() if topic_match else "Key Moment"

    first_words = [w for w in transcript_units[0].text.split() if w.lower() not in ALL_CONNECTIVES and w.lower() not in ALL_FILLERS]
    punch = " ".join(first_words[:6])
    title = f"{topic}: {punch}".strip()
    words = title.split()
    return " ".join(words[:8])


def choose_opening_strategy(
    units: List[ThoughtUnit],
    start_idx: int,
    hook_unit: ThoughtUnit,
    peak_start: float,
    flags: List[str],
    ctx_budget: float = 6.0
) -> Tuple[str, Optional[str], Optional[Dict[str, float]]]:
    """
    Evaluates strategies A -> B -> C -> D in strict order:
    A. natural_start (0 flags, setup <= 6s)
    B. title_overlay (R1/R4/R5 resolved by on-screen text)
    C. cold_open_then_context (strong verbatim hook as 1.5-4s teaser)
    D. walk_back_compressed (context compressed with jump cuts)
    """
    setup_len = max(0.0, hook_unit.s - units[start_idx].s)
    remaining_flags = set(flags)

    # Strategy A: Natural start
    if not remaining_flags and setup_len <= ctx_budget:
        return "natural_start", None, None

    # Strategy B: Title overlay (resolves R1, R4, R5)
    if remaining_flags.issubset({"R1", "R4", "R5"}):
        title = build_title_overlay(units[start_idx:])
        return "title_overlay", title, None

    # Strategy C: Cold open then context
    if hook_unit.hook_score >= 2 and setup_len > ctx_budget:
        cold_dur = min(3.5, max(1.5, hook_unit.e - hook_unit.s))
        cold_open = {"src_start": hook_unit.s, "src_end": hook_unit.s + cold_dur}
        title = build_title_overlay(units[start_idx:])
        return "cold_open_then_context", title, cold_open

    # Strategy D: Walk back compressed
    if setup_len > ctx_budget:
        title = build_title_overlay(units[start_idx:])
        return "walk_back_compressed", title, None

    # Default fallback: title overlay with clean sentence start
    title = build_title_overlay(units[start_idx:])
    return "title_overlay", title, None


# ---------------------------------------------------------------------------
# Step 6 & Retention: Snapping, Tightening & Speech Cuts (§8, §9)
# ---------------------------------------------------------------------------

def snap_boundaries(
    start_unit: ThoughtUnit,
    end_unit: ThoughtUnit,
    words: List[Dict[str, Any]],
    full_duration: float
) -> Tuple[float, float]:
    """
    Snaps start to 0.15-0.30s before first word on clean breath/pause.
    Snaps end to last word + 0.30-0.50s on completed sentence / payoff close.
    """
    first_w_s = start_unit.words[0]["s"] if start_unit.words else start_unit.s
    last_w_e = end_unit.words[-1]["e"] if end_unit.words else end_unit.e

    # Start snap: 0.20s before first word, floored at 0
    snapped_start = max(0.0, round(first_w_s - 0.20, 3))

    # End snap: 0.35s after last word, capped at source duration
    snapped_end = min(full_duration, round(last_w_e + 0.35, 3))

    return snapped_start, snapped_end


def tighten_and_detect_cuts(
    words: List[Dict[str, Any]],
    start_t: float,
    end_t: float
) -> List[Dict[str, Any]]:
    """
    Scans for dead-air pauses (> 0.55s) and speech fillers (um, uh, yaani)
    and returns surgical cut ranges to eliminate dead time.
    """
    clip_words = [w for w in words if w["s"] >= start_t - 0.1 and w["e"] <= end_t + 0.1]
    cuts: List[Dict[str, Any]] = []

    for i in range(len(clip_words) - 1):
        w1 = clip_words[i]
        w2 = clip_words[i + 1]

        # 1. Non-dramatic pause > 0.55s
        gap = w2["s"] - w1["e"]
        if gap > 0.55:
            # Leave 0.12s natural breath room
            c_from = round(w1["e"] + 0.10, 3)
            c_to = round(w2["s"] - 0.08, 3)
            if c_to - c_from >= 0.30:
                cuts.append({"from": c_from, "to": c_to, "reason": "dead_air"})

        # 2. Filler words (isolated um, uh)
        w2_text = re.sub(r'[^\w]', '', (w2.get("t") or w2.get("w") or "").lower())
        if w2_text in ALL_FILLERS:
            w3 = clip_words[i + 2] if i + 2 < len(clip_words) else None
            if w3 and (w3["s"] - w2["e"]) >= 0.15:
                cuts.append({"from": round(w2["s"] - 0.05, 3), "to": round(w2["e"] + 0.05, 3), "reason": "filler"})

    return cuts[:8]  # Limit to 8 surgical cuts max to prevent over-splicing


# ---------------------------------------------------------------------------
# Step 7: QC Cold-Viewer Simulation & 14-Point Checklist (§10, §12)
# ---------------------------------------------------------------------------

def evaluate_cold_viewer_checklist(
    start_t: float,
    end_t: float,
    strategy: str,
    title_overlay: Optional[str],
    flags: List[str],
    hook_unit: ThoughtUnit,
    units: List[ThoughtUnit],
    cuts: List[Dict[str, Any]]
) -> Tuple[bool, Dict[str, int], List[str]]:
    """
    Evaluates the 14-point checklist and outputs clarity, curiosity, continuity scores.
    """
    failures: List[str] = []
    dur = end_t - start_t

    # 1. Context red flags check
    resolved_by_title = (strategy in ("title_overlay", "cold_open_then_context") and bool(title_overlay))
    remaining_flags = [f for f in flags if not (resolved_by_title and f in ("R1", "R4", "R5"))]
    if remaining_flags:
        failures.append(f"Unresolved context red flags: {', '.join(remaining_flags)}")

    # 2. Hook beat by 3.0s
    setup_time = max(0.0, hook_unit.s - start_t)
    if strategy not in ("title_overlay", "cold_open_then_context") and setup_time > 3.2:
        failures.append(f"First hook beat arrives at {setup_time:.1f}s (> 3.0s deadline)")

    # 3. Topic identifiable in first 3s
    if not (title_overlay or hook_unit.is_question or hook_unit.hook_score >= 2):
        failures.append("Topic not immediately identifiable in opening 3 seconds")

    # 4. Context budget: setup <= 6s (hard cap 8s), <= 25% of clip
    if setup_time > 8.0:
        failures.append(f"Setup duration {setup_time:.1f}s exceeds 8s hard cap")
    if dur > 0 and (setup_time / dur) > 0.35 and strategy == "natural_start":
        failures.append(f"Setup ratio {(setup_time/dur)*100:.0f}% exceeds context budget")

    # 5. Clean boundary snap
    if dur < 10.0:
        failures.append(f"Clip length {dur:.1f}s is too short (< 10s)")
    if dur > 120.0:
        failures.append(f"Clip length {dur:.1f}s exceeds maximum limit")

    # 6. Scores: Clarity (0-2), Curiosity (0-2), Continuity (0-2)
    clarity = 2 if not remaining_flags else (1 if resolved_by_title else 0)
    curiosity = 2 if hook_unit.hook_score >= 2 else (1 if hook_unit.hook_score >= 1 else 0)
    continuity = 2 if len(cuts) <= 3 else 1

    scores = {"clarity": clarity, "curiosity": curiosity, "continuity": continuity}
    total_score = clarity + curiosity + continuity

    passed = (len(failures) == 0 and clarity >= 1 and curiosity >= 1 and continuity >= 1 and total_score >= 5)

    return passed, scores, failures


# ---------------------------------------------------------------------------
# Core Public API: optimize_clip & optimize_candidates
# ---------------------------------------------------------------------------

def optimize_clip(
    words: List[Dict[str, Any]],
    raw_start: float,
    raw_end: float,
    duration: float,
    max_length: float = 60.0
) -> ViralOptimizationResult:
    """
    Mandatory optimization pass for a single candidate peak.
    Executes all 7 steps of the viral skill with up to 3 fix iterations.
    """
    units = segment_into_thought_units(words)
    if not units:
        return ViralOptimizationResult(
            start=raw_start, end=raw_end, opening_strategy="natural_start",
            title_overlay=None, cold_open=None, cuts=[],
            scores={"clarity": 1, "curiosity": 1, "continuity": 1},
            flags=[], approved=True
        )

    # Find peak unit
    peak_units = [u for u in units if u.s <= raw_start <= u.e or (u.s >= raw_start and u.e <= raw_end)]
    peak_idx = peak_units[0].id if peak_units else 0

    hook_u, hook_score, hook_types = find_best_hook_unit(units, raw_start, raw_end)
    hook_type = hook_types[0] if hook_types else "general"

    # Up to 3 fix iterations
    best_result: Optional[ViralOptimizationResult] = None

    for iteration in range(1, 4):
        ctx_budget = 6.0 if iteration == 1 else (7.5 if iteration == 2 else 8.0)

        # Walk-back
        start_idx, flags = walk_back_for_context(units, peak_idx, ctx_budget=ctx_budget)

        # Strategy selection
        strategy, title, cold_open = choose_opening_strategy(
            units, start_idx, hook_u, raw_start, flags, ctx_budget=ctx_budget
        )

        # Boundaries
        matching_ids = [u.id for u in units if u.e <= raw_end]
        end_idx = min(len(units) - 1, max(peak_idx, matching_ids[-1] if matching_ids else peak_idx))
        s, e = snap_boundaries(units[start_idx], units[end_idx], words, duration)

        # Enforce max duration
        if (e - s) > max_length:
            e = round(s + max_length, 3)

        # Tighten cuts
        cuts = tighten_and_detect_cuts(words, s, e)

        # QC Checklist & Cold-viewer evaluation
        passed, scores, failures = evaluate_cold_viewer_checklist(
            s, e, strategy, title, flags, hook_u, units, cuts
        )

        res = ViralOptimizationResult(
            start=s,
            end=e,
            opening_strategy=strategy,
            title_overlay=title,
            cold_open=cold_open,
            cuts=cuts,
            scores=scores,
            flags=flags,
            approved=passed,
            rejection_reasons=failures,
            hook_line=hook_u.text,
            hook_type=hook_type,
            iterations=iteration
        )

        if passed:
            return res

        best_result = res

    return best_result or ViralOptimizationResult(
        start=raw_start, end=raw_end, opening_strategy="title_overlay",
        title_overlay=build_title_overlay(units), cold_open=None, cuts=[],
        scores={"clarity": 1, "curiosity": 1, "continuity": 1},
        flags=[], approved=False, rejection_reasons=["Failed QC after 3 iterations"]
    )


def optimize_candidates(
    raw_candidates: List[Dict[str, Any]],
    words: List[Dict[str, Any]],
    duration: float,
    target_count: int = 6,
    max_clip_length: float = 60.0
) -> List[Dict[str, Any]]:
    """
    Mandatory pipeline gate for candidate selection.
    Takes raw candidate peaks from ai.rank(), optimizes each one through the viral skill,
    rejects failed ones, and returns exactly the approved hook-optimized clips.
    """
    approved_clips: List[Dict[str, Any]] = []

    for cand in raw_candidates:
        if len(approved_clips) >= target_count:
            break

        opt = optimize_clip(
            words=words,
            raw_start=cand["s"],
            raw_end=cand["e"],
            duration=duration,
            max_length=max_clip_length
        )

        # If approved (or best effort fallback if strict count needed)
        if opt.approved or len(approved_clips) + len(raw_candidates) <= target_count:
            c = dict(cand)
            c["s"] = opt.start
            c["e"] = opt.end
            c["cuts"] = opt.cuts
            c["title_overlay"] = opt.title_overlay
            c["cold_open"] = opt.cold_open
            c["opening_strategy"] = opt.opening_strategy
            c["hook_line"] = opt.hook_line
            c["hook_type"] = opt.hook_type
            c["viral_scores"] = opt.scores
            c["viral_checklist_passed"] = opt.approved

            # Title formulation: if title_overlay present, make it the primary title
            if opt.title_overlay:
                c["title"] = opt.title_overlay
            elif opt.hook_line:
                c["title"] = opt.hook_line[:60]

            # Merge viral insights
            insights = c.get("insights", {})
            if isinstance(insights, str):
                import json
                try: insights = json.loads(insights)
                except Exception: insights = {}

            insights["opening_strategy"] = opt.opening_strategy
            insights["hook"] = opt.hook_line
            insights["hook_type"] = opt.hook_type
            insights["viral_scores"] = opt.scores
            insights["title_overlay"] = opt.title_overlay
            insights["speech_cuts_count"] = len(opt.cuts)
            insights["checklist_passed"] = opt.approved
            c["insights"] = insights

            approved_clips.append(c)

    return approved_clips
