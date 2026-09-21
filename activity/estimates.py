"""Duration and MET estimates that the model is not allowed to invent.

MET × kg × hours is fine for continuous work (a run, a cycle). It is a poor fit
for a lift: 3×12 bench press is a few minutes of effort plus rest, not a 30
minute session at 5 MET.
"""

import re
from decimal import Decimal

STRENGTH_MET_LIGHT = Decimal("3.5")
STRENGTH_MET_VIGOROUS = Decimal("6.0")
SECONDS_PER_REP = 5
REST_SECONDS_BETWEEN_SETS = 90
SINGLE_LIFT_FALLBACK_MINUTES = Decimal("8")
INVENTED_DURATION_MINUTES = Decimal("20")

STRENGTH_WORDS = (
    "bench",
    "press",
    "squat",
    "deadlift",
    "curl",
    "row",
    "lunge",
    "dumbbell",
    "barbell",
    "kettlebell",
    "lift",
    "sets",
    "reps",
    "weight training",
)

VIGOROUS_WORDS = ("circuit", "crossfit", "hiit", "amrap", "emom", "superset")

SET_RE = re.compile(r"(\d+)\s*sets?", re.I)
REP_RE = re.compile(r"(\d+)\s*reps?", re.I)
SET_X_REP_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.I)
MINUTES_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:min|mins|minutes?)\b", re.I)


def _d(value):
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def parse_sets_reps(text, sets=None, reps=None):
    """Prefer explicit tool args, then patterns like 3x12 or '3 sets of 12'."""
    if sets and reps:
        return int(sets), int(reps)

    text = text or ""
    match = SET_X_REP_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))

    set_match = SET_RE.search(text)
    rep_match = REP_RE.search(text)
    if set_match and rep_match:
        return int(set_match.group(1)), int(rep_match.group(1))

    return None, None


def minutes_for_sets_reps(sets, reps, rest_seconds=REST_SECONDS_BETWEEN_SETS):
    """Clock time for a single lift: work plus typical rest between sets."""
    sets = int(sets)
    reps = int(reps)
    work = sets * reps * SECONDS_PER_REP
    rest = max(sets - 1, 0) * rest_seconds
    minutes = Decimal(work + rest) / Decimal(60)
    if minutes < 1:
        return Decimal("1")
    return minutes.quantize(Decimal("0.1"))


def is_strength(text):
    lowered = (text or "").lower()
    for word in STRENGTH_WORDS:
        if " " in word:
            if word in lowered:
                return True
        elif re.search(rf"\b{re.escape(word)}\b", lowered):
            return True
    return False


def user_stated_minutes(text):
    match = MINUTES_RE.search(text or "")
    return Decimal(match.group(1)) if match else None


def resolve_duration(text, duration_minutes=None, sets=None, reps=None, source=None):
    """Duration the user actually trained, not a 30-minute default."""
    parsed_sets, parsed_reps = parse_sets_reps(text, sets, reps)
    if parsed_sets and parsed_reps:
        return minutes_for_sets_reps(parsed_sets, parsed_reps)

    stated = user_stated_minutes(text)
    if stated is not None:
        return stated

    duration = _d(duration_minutes)
    if duration is None:
        return SINGLE_LIFT_FALLBACK_MINUTES if is_strength(text) else Decimal("10")

    # Manual log-sheet picks are trusted. AI 30-minute defaults for a lift are not.
    if source == "ai" and is_strength(text) and duration >= INVENTED_DURATION_MINUTES:
        return SINGLE_LIFT_FALLBACK_MINUTES

    return duration


def resolve_strength_met(text, met_value=None, sets=None, reps=None):
    """Typical lifting is 3.5 MET; circuits can go to 6. MET tables assume continuous work."""
    lowered = (text or "").lower()
    if any(word in lowered for word in VIGOROUS_WORDS):
        return STRENGTH_MET_VIGOROUS

    parsed_sets, parsed_reps = parse_sets_reps(text, sets, reps)
    volume = (parsed_sets or 0) * (parsed_reps or 0)
    if parsed_sets and parsed_reps and volume < 80:
        return STRENGTH_MET_LIGHT
    if volume >= 80:
        return STRENGTH_MET_VIGOROUS

    if met_value:
        met = _d(met_value)
        return min(max(met, STRENGTH_MET_LIGHT), STRENGTH_MET_VIGOROUS)

    return STRENGTH_MET_LIGHT
