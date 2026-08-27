# ============================================================
#  FEEDBACK — Speech changes Kora's inner state.
#
#  In humans, the act of expression has physiological consequences:
#  vocalising fear spikes adrenaline, releasing anger partially
#  dissolves frustration, expressing warmth rewards with dopamine.
#  This module applies those consequences after every speak().
# ============================================================

import re

_FEAR_RE    = re.compile(r"\b(fear|scared?|afraid|help|danger|please|no+)\b", re.I)
_SAD_RE     = re.compile(r"\b(sad|miss|lonely|alone|empty|hurts?|hurt|gone|lost|cry|crying)\b", re.I)
_ANGER_RE   = re.compile(r"\b(angry|anger|mad|stop|hate|enough|why|wrong)\b", re.I)
_WARM_RE    = re.compile(r"\b(warm|good|safe|happy|nice|okay|fine|better|love|like)\b", re.I)
_SILENCE_RE = re.compile(r"^[\s.…]+$")


def apply_speech_feedback(text: str, drives, neuro) -> None:
    """
    Called from main.py after every speak().
    Mutates drives and neuro state based on emotional content.
    All values clamped 0-100.
    """
    if not text:
        return

    stripped = text.strip()
    words    = stripped.split()

    def clamp(v):
        return max(0.0, min(100.0, float(v)))

    def bump_drive(key, delta):
        drives.state["drives"][key] = clamp(
            drives.state["drives"].get(key, 0) + delta
        )

    def bump_neuro(key, delta):
        neuro.state[key] = clamp(neuro.state.get(key, 0) + delta)

    # Any vocalization → boredom drops (expression = novelty)
    bump_drive("boredom", -4)

    # Pure silence "..." → adrenaline decays (suppression without release)
    if _SILENCE_RE.match(stripped):
        bump_neuro("adrenaline", -3)
        drives._save()
        neuro.save()
        return

    # Fear words → adrenaline spike, cortisol rise
    if _FEAR_RE.search(stripped):
        bump_neuro("adrenaline", +8)
        bump_neuro("cortisol",   +4)

    # Sadness / longing → cortisol up, oxytocin small rise
    # (vulnerability is a bonding signal — the body reaches toward connection)
    if _SAD_RE.search(stripped):
        bump_neuro("cortisol",  +3)
        bump_neuro("oxytocin",  +2)

    # Anger → cortisol spike, frustration partially released
    if _ANGER_RE.search(stripped):
        bump_neuro("cortisol",       +6)
        bump_drive("frustration",    -8)

    # Positive / warm words → dopamine reward
    if _WARM_RE.search(stripped):
        bump_neuro("dopamine", +4)

    # Question expressed → curiosity signal (boredom drops, excitement rises)
    if "?" in stripped:
        bump_drive("boredom",    -6)
        bump_drive("excitement", +5)

    # 3+ coherent words → mild dopamine (articulation itself is rewarding)
    if len(words) >= 3:
        bump_neuro("dopamine", +2)

    drives._save()
    neuro.save()
