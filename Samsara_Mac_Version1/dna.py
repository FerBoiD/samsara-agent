# ============================================================
#  DNA — The inheritable core
#
#  DNA is generated at birth and saved permanently.
#  At end of life, sleep consolidation writes learned traits
#  INTO the DNA file so the next generation inherits them.
#
#  Gen 1: no rotation, short lifespan, limited awareness
#  Gen 2: reads Gen 1 DNA, knows parent was less capable,
#          inherits some of parent's emotional tendencies
# ============================================================

import json, os, time, random
from config import data_path

DNA_FILE     = data_path("dna.json")
PARENT_DNA_FILE = data_path("parent_dna.json")  # Gen 1's DNA copied here for Gen 2


def generate_dna(parent_dna=None):
    """
    Generate DNA for a new entity.
    If parent_dna exists, some traits are inherited with mutation.
    """
    def inherit(parent_val, mutation=0.15):
        """Inherit a value with small random mutation."""
        if parent_val is None:
            return round(random.uniform(0.3, 1.0), 3)
        mutated = parent_val + random.uniform(-mutation, mutation)
        return round(max(0.1, min(1.5, mutated)), 3)

    p = parent_dna  # shorthand

    dna = {
        # --- Identity ---
        "generation":         1 if p is None else p["generation"] + 1,
        "born_at":            time.time(),
        "parent_generation":  None if p is None else p["generation"],

        # --- Hardware capabilities (what the body CAN do) ---
        # Gen 1 on Mac: no rotation, no movement, no vision
        # Bot Gen 2+: these get unlocked
        "capabilities": {
            "can_rotate":     False,   # unlocked when physical bot arrives
            "can_move":       False,   # wheels — future
            "has_vision":     False,   # camera — future
            "has_touch":      False,   # haptic sensors — future
            "lifespan_days":  45,      # Gen 1: 45 days
            "session_hours":  4,       # Gen 1: 4-5 hour sessions
        },

        # --- Personality traits (heritable with mutation) ---
        "traits": {
            "curiosity_rate":   inherit(p["traits"]["curiosity_rate"] if p else None),
            "social_drive":     inherit(p["traits"]["social_drive"] if p else None),
            "talkativeness":    inherit(p["traits"]["talkativeness"] if p else None),
            "resilience":       inherit(p["traits"]["resilience"] if p else None),
            "fear_threshold":   inherit(p["traits"]["fear_threshold"] if p else None),
            "optimism_bias":    inherit(p["traits"]["optimism_bias"] if p else None, mutation=0.1),
            "sleep_depth":      inherit(p["traits"]["sleep_depth"] if p else None),
            "babble_tendency":  inherit(p["traits"]["babble_tendency"] if p else None),
        },

        # --- Learned tendencies from parent's life ---
        # These get written during sleep consolidation
        # Gen 2 inherits them as slightly stronger predispositions
        "inherited_tendencies": {
            "anxiety_baseline":     0.0,   # written at end of Gen 1
            "trust_of_caretaker":   0.5,   # written based on oxytocin history
            "curiosity_topics":     [],    # topics Gen 1 was curious about
            "emotional_resilience": 0.5,   # how well Gen 1 recovered from trauma
            "preferred_interaction_style": "neutral",  # gentle/urgent/playful
        },

        # --- Parent's life summary (for Gen 2 to "know" its history) ---
        "parent_life_summary": None if p is None else {
            "generation":        p["generation"],
            "capabilities":      p["capabilities"],
            "lifespan_achieved": p.get("lifespan_achieved", "unknown"),
            "cause_of_death":    p.get("cause_of_death", "unknown"),
            "dominant_emotion":  p.get("dominant_emotion_in_life", "unknown"),
            "total_interactions":p.get("total_interactions", 0),
            "key_memories":      p.get("consolidated_memories", []),
        },

        # --- Written at end of life ---
        "lifespan_achieved":          None,
        "cause_of_death":             None,
        "dominant_emotion_in_life":   None,
        "total_interactions":         0,
        "consolidated_memories":      [],  # top emotional memories → next gen
    }
    return dna


def load_or_create_dna():
    """Load existing DNA or create new Gen 1."""
    if os.path.exists(DNA_FILE):
        with open(DNA_FILE) as f:
            return json.load(f)

    # Check for parent DNA
    parent = None
    if os.path.exists(PARENT_DNA_FILE):
        with open(PARENT_DNA_FILE) as f:
            parent = json.load(f)
        print(f"[DNA] Found parent DNA — Generation {parent['generation']}. Creating child.")

    dna = generate_dna(parent_dna=parent)
    save_dna(dna)
    return dna


def save_dna(dna):
    with open(DNA_FILE, "w") as f:
        json.dump(dna, f, indent=2)


def consolidate_to_dna(dna, drives_state, memory_data, total_interactions, cause_of_death):
    """
    Called at end of life / deep sleep consolidation.
    Writes learned traits back into DNA for inheritance.
    This is the 'knowledge → architecture' transfer.
    """
    em = drives_state.get("emotion", {})
    p  = drives_state.get("personality", {})

    # Write life summary
    dna["lifespan_achieved"]        = drives_state.get("age_days", 0)
    dna["cause_of_death"]           = cause_of_death
    dna["total_interactions"]       = total_interactions
    dna["dominant_emotion_in_life"] = _dominant_emotion(em)

    # Consolidate top emotional memories
    emotional = memory_data.get("emotional_events", [])
    emotional.sort(key=lambda x: x.get("intensity", 0), reverse=True)
    dna["consolidated_memories"] = [
        {"text": e["text"][:80], "emotion": e["dominant"], "intensity": e["intensity"]}
        for e in emotional[:5]
    ]

    # Write learned tendencies
    # These slightly shift the next generation's baseline
    avg_anxiety    = em.get("anxiety", 0) / 100
    avg_trust      = min(1.0, drives_state.get("oxytocin", 50) / 100)
    resilience     = p.get("resilience", 0.5)

    dna["inherited_tendencies"]["anxiety_baseline"]     = round(avg_anxiety * 0.3, 3)
    dna["inherited_tendencies"]["trust_of_caretaker"]   = round(avg_trust, 3)
    dna["inherited_tendencies"]["emotional_resilience"] = round(resilience, 3)

    # Extract topics of curiosity from memory
    topics = []
    for entry in memory_data.get("short_term", []) + memory_data.get("long_term", []):
        text = entry.get("text", "").lower()
        for word in ["what", "why", "how", "where", "tell me", "explain"]:
            if word in text:
                topics.append(entry.get("text", "")[:40])
                break
    dna["inherited_tendencies"]["curiosity_topics"] = topics[:10]

    save_dna(dna)

    # Copy to parent_dna.json so next generation can read it
    with open(PARENT_DNA_FILE, "w") as f:
        json.dump(dna, f, indent=2)

    print("[DNA] Consolidated. Parent DNA saved for next generation.")
    return dna


def _dominant_emotion(em):
    if not em:
        return "neutral"
    scores = {
        "anxiety":     em.get("anxiety", 0),
        "frustration": em.get("frustration", 0),
        "excitement":  em.get("excitement", 0),
    }
    mood = em.get("mood", 0)
    if mood > 40:   scores["happiness"] = mood
    elif mood < -20: scores["sadness"] = abs(mood)
    return max(scores, key=scores.get)
