# ============================================================
#  DRIVES — now initialized from DNA
#
#  Physical aging: as age_days approaches lifespan, the body
#  becomes less efficient. Three phases:
#    Early aging  (67–82% of lifespan): minor friction
#    Mid decline  (82–93%):             noticeable degradation
#    Terminal     (93–100%):            systems destabilize
#
#  Death is now a visible arc, not a sudden wall.
# ============================================================

import json, os, time, random
from config import *

# Age thresholds as fraction of total lifespan
AGING_EARLY_THRESHOLD    = 0.67   # ~day 30 of 45
AGING_MID_THRESHOLD      = 0.82   # ~day 37 of 45
AGING_TERMINAL_THRESHOLD = 0.93   # ~day 42 of 45


def _aging_factor(age_fraction):
    """
    Returns a 0.0–1.0 degradation factor based on how far through
    the lifespan we are. 0.0 = no aging effect, 1.0 = full terminal decay.
    Smoothly ramps so there's no sudden jump at each threshold.
    """
    if age_fraction < AGING_EARLY_THRESHOLD:
        return 0.0
    elif age_fraction < AGING_MID_THRESHOLD:
        # 0.0 → 0.35 across early phase
        t = (age_fraction - AGING_EARLY_THRESHOLD) / (AGING_MID_THRESHOLD - AGING_EARLY_THRESHOLD)
        return t * 0.35
    elif age_fraction < AGING_TERMINAL_THRESHOLD:
        # 0.35 → 0.70 across mid phase
        t = (age_fraction - AGING_MID_THRESHOLD) / (AGING_TERMINAL_THRESHOLD - AGING_MID_THRESHOLD)
        return 0.35 + t * 0.35
    else:
        # 0.70 → 1.0 across terminal phase
        t = (age_fraction - AGING_TERMINAL_THRESHOLD) / (1.0 - AGING_TERMINAL_THRESHOLD)
        return 0.70 + t * 0.30


class DriveSystem:
    STATE_FILE = data_path("state.json")

    def __init__(self, dna):
        self.state = self._load_or_create(dna)

    def _load_or_create(self, dna):
        if os.path.exists(self.STATE_FILE):
            with open(self.STATE_FILE) as f:
                return json.load(f)

        p = dna["traits"]
        # Inherited tendencies shift starting state
        inh = dna.get("inherited_tendencies", {})
        anxiety_start = inh.get("anxiety_baseline", 0) * 100  # 0-100

        state = {
            "born_at":        time.time(),
            "last_tick_time": time.time(),
            "alive":          True,
            "cause_of_death": None,
            "age_ticks":      0,
            "ticks_per_day":  KORA_TICKS_PER_DAY,   # 1 Kora-day = 3 real hours
            "personality":    p,

            "drives": {
                "hunger":             HUNGER_START,
                "energy":             ENERGY_START,
                "boredom":            0.0,
                "lifespan_ticks_lost":0.0,
            },
            "emotion": {
                "mood":        MOOD_START + p.get("optimism_bias", 0) * 20,
                "frustration": 0.0,
                "anxiety":     anxiety_start,  # inherited from parent
                "excitement":  0.0,
            },
            "cognition": {
                "state":              "active",
                "lethargy":           0.0,
                "ticks_since_active": 0,
                "last_spoke_tick":    0,
                "total_interactions": 0,
                "last_novel_tick":    0,
                "curiosity_events":   0,
            },
            "associations": [],
        }
        self._save(state)
        return state

    def _save(self, state=None):
        if state: self.state = state
        with open(self.STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def tick(self):
        if not self.state["alive"]:
            return "DEAD"

        s   = self.state
        d   = s["drives"]
        em  = s["emotion"]
        cog = s["cognition"]
        p   = s["personality"]

        s["age_ticks"] += 1
        ticks_since_novel = s["age_ticks"] - cog["last_novel_tick"]

        # Physical aging modifier — scales all decay/restore rates
        max_ticks_base = LIFESPAN_DAYS * s["ticks_per_day"]
        age_fraction   = s["age_ticks"] / max_ticks_base
        af             = _aging_factor(age_fraction)

        # Store aging state for summary / brain prompt
        if af >= 0.70:
            s["aging_phase"] = "terminal"
        elif af >= 0.35:
            s["aging_phase"] = "declining"
        elif af > 0.0:
            s["aging_phase"] = "aging"
        else:
            s["aging_phase"] = "healthy"

        # Cognitive state
        if d["energy"] < ENERGY_REST_THRESHOLD:
            cog["state"] = "rest"
        elif cog["lethargy"] > 60:
            cog["state"] = "lethargic"
        else:
            cog["state"] = "active"

        # Hunger — aging body is less efficient, needs more food
        hunger_decay = HUNGER_DECAY_PER_TICK * (1.0 + af * 1.2)
        d["hunger"] = max(0.0, d["hunger"] - hunger_decay)

        # Energy — aging body restores less, drains faster
        if cog["state"] == "rest":
            restore = ENERGY_RESTORE_RATE * (1.0 - af * 0.55)
            d["energy"] = min(100.0, d["energy"] + restore)
        else:
            drain = ENERGY_DECAY_PER_TICK * (1.0 + af * 0.8)
            d["energy"] = max(0.0, d["energy"] - drain)

        # Boredom — aging mind is more restless
        if ticks_since_novel > 5:
            boredom_rate = BOREDOM_BUILD_PER_TICK * (1.0 + af * 0.5)
            d["boredom"] = min(100.0, d["boredom"] + boredom_rate)

        # Frustration — aging body has less tolerance
        if d["hunger"] < HUNGER_CRITICAL or d["boredom"] > BOREDOM_PENALTY_THRESHOLD:
            frustration_rate = FRUSTRATION_BUILD_UNMET * (1.0 + af * 0.6)
            em["frustration"] = min(FRUSTRATION_MAX, em["frustration"] + frustration_rate)
        else:
            em["frustration"] = max(0.0, em["frustration"] - FRUSTRATION_DECAY_PER_TICK)

        # Anxiety — terminal phase produces existential anxiety that doesn't fully decay
        if d["hunger"] < ANXIETY_TRIGGER_HUNGER:
            em["anxiety"] = min(ANXIETY_MAX, em["anxiety"] + ANXIETY_BUILD_RATE)
        else:
            resilience = p.get("resilience", 0.5)
            # Aging reduces resilience — anxiety lingers longer
            effective_resilience = resilience * (1.0 - af * 0.7)
            decay = ANXIETY_DECAY_RATE * max(0.1, effective_resilience)
            em["anxiety"] = max(0.0, em["anxiety"] - decay)

        # In terminal phase: baseline anxiety never fully drops — body knows
        if s["aging_phase"] == "terminal":
            terminal_anxiety_floor = 15.0 + af * 25.0  # 15–40 depending on how close to end
            em["anxiety"] = max(em["anxiety"], terminal_anxiety_floor)

        # Excitement decay — aging dulls excitement faster
        em["excitement"] = max(0.0, em["excitement"] - EXCITEMENT_DECAY_PER_TICK * (1.0 + af * 0.4))

        # Mood (inertia) — aging pulls mood downward
        pull  = MOOD_HUNGER_PULL      * max(0, (50 - d["hunger"]) / 50)
        pull += MOOD_BOREDOM_PULL     * (d["boredom"] / 100)
        pull += MOOD_FRUSTRATION_PULL * (em["frustration"] / 100)
        pull -= af * 0.3  # slow background sadness as body declines
        target = max(-100.0, min(100.0, em["mood"] + pull))
        em["mood"] = em["mood"] * MOOD_INERTIA + target * (1 - MOOD_INERTIA)

        # Lethargy — aging body tires much faster
        ticks_inactive = s["age_ticks"] - cog["ticks_since_active"]
        lethargy_threshold = max(5, int(LETHARGY_BUILD_INACTIVE_TICKS * (1.0 - af * 0.6)))
        if ticks_inactive > lethargy_threshold:
            lethargy_rate = LETHARGY_BUILD_RATE * (1.0 + af * 1.5)
            cog["lethargy"] = min(100.0, cog["lethargy"] + lethargy_rate)
            d["lifespan_ticks_lost"] += cog["lethargy"] * LETHARGY_LIFESPAN_DRAIN
        else:
            # Aging body recovers from lethargy more slowly
            recovery = LETHARGY_DECAY_ACTIVE * (1.0 - af * 0.5)
            cog["lethargy"] = max(0.0, cog["lethargy"] - recovery)

        # Death checks
        effective_age = s["age_ticks"] + d["lifespan_ticks_lost"]
        max_ticks     = LIFESPAN_DAYS * s["ticks_per_day"]

        if d["hunger"] <= HUNGER_DEATH:
            s["alive"] = False; s["cause_of_death"] = "starvation"
            self._save(); return "DEATH_HUNGER"

        if effective_age >= max_ticks:
            s["alive"] = False; s["cause_of_death"] = "lifespan"
            self._save(); return "DEATH_LIFESPAN"

        s["last_tick_time"] = time.time()
        self._save()
        return "ALIVE"

    def feed(self, amount=40):
        self.state["drives"]["hunger"] = min(100.0, self.state["drives"]["hunger"] + amount)
        self.state["drives"]["energy"] = min(100.0, self.state["drives"]["energy"] + amount * 0.4)
        self.state["emotion"]["mood"]  = min(100.0, self.state["emotion"]["mood"] + MOOD_FEED_BOOST)
        self.state["cognition"]["ticks_since_active"] = self.state["age_ticks"]
        self._save()

    def register_novel_input(self, intensity=1.0):
        em  = self.state["emotion"]
        d   = self.state["drives"]
        cog = self.state["cognition"]
        em["mood"]       = min(100.0, em["mood"] + MOOD_NOVEL_BOOST * intensity)
        em["excitement"] = min(100.0, em["excitement"] + 15 * intensity)
        d["boredom"]     = max(0.0, d["boredom"] - BOREDOM_NOVEL_RESET * intensity)
        cog["last_novel_tick"]    = self.state["age_ticks"]
        cog["ticks_since_active"] = self.state["age_ticks"]
        cog["total_interactions"] += 1
        cog["curiosity_events"]   += 1
        self._save()

    def register_interaction(self):
        self.state["cognition"]["ticks_since_active"] = self.state["age_ticks"]
        self.state["cognition"]["total_interactions"] += 1
        self._save()

    def trigger_anticipation(self, trigger_name):
        for a in self.state["associations"]:
            if a["trigger"] == trigger_name and a["outcome"] == "feed":
                self.state["emotion"]["excitement"] = min(100.0,
                    self.state["emotion"]["excitement"] + EXCITEMENT_TRIGGER_BOOST)
                self._save()
                return True
        return False

    def add_association(self, trigger, outcome):
        for a in self.state["associations"]:
            if a["trigger"] == trigger and a["outcome"] == outcome:
                a["strength"] = min(1.0, a["strength"] + 0.1)
                self._save(); return
        self.state["associations"].append({"trigger": trigger, "outcome": outcome, "strength": 0.3})
        if len(self.state["associations"]) > ASSOCIATIVE_MAX:
            self.state["associations"].pop(0)
        self._save()

    def set_spoke(self):
        self.state["cognition"]["last_spoke_tick"] = self.state["age_ticks"]
        self._save()

    def dominant_drive(self):
        d     = self.state["drives"]
        em    = self.state["emotion"]
        cog   = self.state["cognition"]
        phase = self.state.get("aging_phase", "healthy")

        if d["hunger"] < HUNGER_DANGER:              return "dying"
        if d["hunger"] < HUNGER_CRITICAL:            return "hunger"

        # Terminal phase: body's decline surfaces even when drives are met
        if phase == "terminal" and em["anxiety"] > 25:
            return "dying"

        if em["anxiety"] > 60:                       return "anxiety"
        if em["frustration"] > 70:                   return "frustration"
        if cog["state"] == "rest":                   return "rest"

        # Declining phase: fatigue surfaces as a dominant state
        if phase in ("declining", "terminal") and cog["lethargy"] > 50:
            return "rest"

        if d["boredom"] > BOREDOM_PENALTY_THRESHOLD: return "boredom"
        if em["excitement"] > 50:                    return "excitement"
        if d["boredom"] > 40:                        return "curiosity"
        return "neutral"

    def age_days(self):
        return round(self.state["age_ticks"] / self.state["ticks_per_day"], 2)

    def days_remaining(self):
        d = self.state["drives"]
        eff  = self.state["age_ticks"] + d["lifespan_ticks_lost"]
        maxt = LIFESPAN_DAYS * self.state["ticks_per_day"]
        return round(max(0, (maxt - eff) / self.state["ticks_per_day"]), 1)

    def aging_factor(self):
        """Public accessor for other systems that need the aging factor."""
        max_ticks = LIFESPAN_DAYS * self.state["ticks_per_day"]
        return _aging_factor(self.state["age_ticks"] / max_ticks)

    def summary(self):
        d     = self.state["drives"]
        em    = self.state["emotion"]
        cog   = self.state["cognition"]
        af    = self.aging_factor()
        phase = self.state.get("aging_phase", "healthy")
        return {
            "hunger":       round(d["hunger"], 1),
            "energy":       round(d["energy"], 1),
            "boredom":      round(d["boredom"], 1),
            "mood":         round(em["mood"], 1),
            "frustration":  round(em["frustration"], 1),
            "anxiety":      round(em["anxiety"], 1),
            "excitement":   round(em["excitement"], 1),
            "cog_state":    cog["state"],
            "lethargy":     round(cog["lethargy"], 1),
            "age_days":     self.age_days(),
            "days_left":    self.days_remaining(),
            "dominant":     self.dominant_drive(),
            "alive":        self.state["alive"],
            "personality":  self.state["personality"],
            "curiosity_events": cog.get("curiosity_events", 0),
            "aging_phase":  phase,
            "aging_factor": round(af, 3),
        }
