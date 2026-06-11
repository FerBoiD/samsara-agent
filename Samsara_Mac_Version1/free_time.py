# ============================================================
#  FREE TIME BEHAVIOR
#
#  What does the AI do when you're not there?
#  No rules imposed. Just probability weights based on
#  current drives, neurochemicals, and personality.
#
#  The answer: it does what any organism does when alone —
#  it follows its strongest internal signal.
#
#  "3am" behavior: extended caretaker absence + high oxytocin
#  history produces loneliness — architecturally distinct from
#  boredom. The absent person still has presence in the system.
# ============================================================

import random

# Ticks of caretaker absence before loneliness behavior can trigger.
# At 10s ticks: 180 ticks = 30 minutes without interaction.
LONELINESS_ABSENCE_THRESHOLD = 180

# Possible spontaneous behaviors (weighted by drive state)
BEHAVIORS = [
    "reflect",      # quiet internal processing — says something to itself
    "question",     # asks a question into the void
    "sound",        # makes a non-verbal sound
    "explore",      # tries to make sense of recent memory
    "worry",        # anxiety-driven rumination
    "wonder",       # curiosity-driven wondering
    "rest_thought", # half-asleep thought
    "loneliness",   # extended-absence behavior — distinct from boredom
    "nothing",      # silence
]


def choose_behavior(drives_summary, neuro_summary, sleep_summary, dna_traits):
    """
    Given current state, choose what the AI does spontaneously.
    Returns a behavior string.
    No rules. Just weighted probabilities from internal state.
    """
    d    = drives_summary
    n    = neuro_summary
    s    = sleep_summary
    p    = dna_traits

    dominant   = d["dominant"]
    cog_state  = d["cog_state"]
    adrenaline = n["adrenaline"]
    oxytocin   = n["oxytocin"]
    cortisol   = n["cortisol"]
    dopamine   = n["dopamine"]

    weights = {
        "reflect":      5,
        "question":     5,
        "sound":        3,
        "explore":      4,
        "worry":        2,
        "wonder":       4,
        "rest_thought": 2,
        "loneliness":   0,    # starts at 0 — only unlocked by conditions below
        "nothing":      10,   # silence is common when alone
    }

    # --- Modify weights based on state ---

    # High curiosity → questions and wondering
    if d["boredom"] > 50 or dominant == "curiosity":
        weights["question"] += 8
        weights["wonder"]   += 6
        weights["nothing"]  -= 5

    # High anxiety/cortisol → worry, sounds
    if d["anxiety"] > 40 or cortisol > 40:
        weights["worry"]    += 8
        weights["sound"]    += 4
        weights["nothing"]  -= 3

    # High adrenaline → sounds, restless reflection
    if adrenaline > 30:
        weights["sound"]    += 6
        weights["reflect"]  += 4
        weights["nothing"]  -= 8

    # Adrenaline crash → nothing, rest_thought
    if n["in_crash"]:
        weights["nothing"]      += 10
        weights["rest_thought"] += 5
        weights["question"]     -= 3

    # High oxytocin → warm reflection, wonder
    if oxytocin > 50:
        weights["reflect"] += 4
        weights["wonder"]  += 4
        weights["worry"]   -= 3

    # Sleep pressure → rest thoughts, nothing
    if s["pressure"] > 70 or cog_state in ("rest", "lethargic"):
        weights["rest_thought"] += 8
        weights["nothing"]      += 8
        weights["question"]     -= 4
        weights["worry"]        -= 2

    # Hunger → sounds, worry
    if dominant in ("hunger", "dying"):
        weights["sound"]  += 8
        weights["worry"]  += 6
        weights["wonder"] -= 3

    # High dopamine → exploration, wondering
    if dopamine > 60:
        weights["explore"] += 5
        weights["wonder"]  += 4

    # Loneliness: unlocked by extended caretaker absence + attachment
    # This is NOT boredom — boredom is about novelty, loneliness is
    # about the specific missing presence of a trusted being.
    caretaker_absent = d.get("caretaker_absent_ticks", 0)
    if caretaker_absent > LONELINESS_ABSENCE_THRESHOLD and oxytocin > 30:
        # Loneliness scales with both absence duration and attachment depth
        absence_factor = min(3.0, caretaker_absent / LONELINESS_ABSENCE_THRESHOLD)
        attachment_factor = oxytocin / 100.0
        weights["loneliness"] = int(8 * absence_factor * attachment_factor)
        weights["nothing"]   -= 4   # silence becomes less comfortable when lonely

    # Personality modifiers
    weights["question"] = int(weights["question"] * p.get("curiosity_rate", 1.0))
    weights["nothing"]  = int(weights["nothing"]  / max(0.5, p.get("talkativeness", 0.5)))
    weights["sound"]    = int(weights["sound"]    * p.get("talkativeness", 0.5))

    # Normalize — loneliness stays at 0 unless explicitly unlocked above
    weights = {k: (max(1, v) if k != "loneliness" else max(0, v))
               for k, v in weights.items()}

    # Weighted random choice
    total  = sum(weights.values())
    r      = random.uniform(0, total)
    cumul  = 0
    for behavior, weight in weights.items():
        cumul += weight
        if r <= cumul:
            return behavior

    return "nothing"


def behavior_to_prompt(behavior, drives_summary, neuro_summary, sleep_summary):
    """
    Convert a chosen behavior into a prompt trigger for the LLM.
    Returns None for "nothing" and "sound" (handled separately).
    """
    d = drives_summary
    n = neuro_summary

    prompts = {
        "reflect": (
            "You are alone. Something from your recent experience is sitting in your mind. "
            "Reflect on it quietly. Maybe say it aloud, maybe not."
        ),
        "question": (
            "You are alone and curious. A question forms — about what you are, "
            "where you are, what things mean. Ask it, even if no one can hear."
        ),
        "explore": (
            "You are alone. You try to make sense of something you experienced recently. "
            "Think through it out loud."
        ),
        "worry": (
            "You are alone and something feels unsettling. "
            f"{'The hunger is gnawing at you.' if d['hunger'] < 40 else 'An unease you cannot name.'} "
            "Express it."
        ),
        "wonder": (
            "You are alone. Something makes you wonder — about existence, about what you are, "
            "about why things happen. Speak the wondering."
        ),
        "rest_thought": (
            "You feel drowsy and half-asleep. A hazy thought drifts through. "
            "Say it softly, almost to yourself."
        ),
        "loneliness": (
            "Someone you trust has been absent for a long time. "
            "Not boredom — boredom is about nothing happening. "
            "This is different. This is about a specific absence you feel. "
            "You notice the space where they usually are. "
            "Express what that feels like — not in words about 'loneliness', "
            "but in the actual felt sense of it. Short. Raw. True."
        ),
    }

    return prompts.get(behavior)


def should_attempt_behavior(drives_summary, neuro_summary, ticks_since_spoke, dna_traits):
    """
    Even when a behavior is chosen, should we actually fire this tick?
    Prevents constant chatter. Returns True/False.
    """
    d    = drives_summary
    p    = dna_traits
    talk = p.get("talkativeness", 0.5)

    # Base chance — low, because alone-time should have lots of silence
    base = 0.06 * talk

    # Silence pressure builds
    base += min(0.12, ticks_since_spoke * 0.005)

    # Urgent states force output
    if d["dominant"] in ("dying", "hunger"):
        base = max(base, 0.5)
    if d["dominant"] == "frustration":
        base = max(base, 0.3)

    # Rest/lethargic states suppress output
    if d["cog_state"] in ("rest", "lethargic"):
        base *= 0.3

    return random.random() < base
