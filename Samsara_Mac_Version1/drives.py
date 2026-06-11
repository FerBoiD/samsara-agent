# ============================================================
#  DRIVES — now initialized from DNA
# ============================================================

import json, os, time, random
from config import *


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

        # Cognitive state
        if d["energy"] < ENERGY_REST_THRESHOLD:
            cog["state"] = "rest"
        elif cog["lethargy"] > 60:
            cog["state"] = "lethargic"
        else:
            cog["state"] = "active"

        # Hunger
        d["hunger"] = max(0.0, d["hunger"] - HUNGER_DECAY_PER_TICK)

        # Energy
        if cog["state"] == "rest":
            d["energy"] = min(100.0, d["energy"] + ENERGY_RESTORE_RATE)
        else:
            d["energy"] = max(0.0, d["energy"] - ENERGY_DECAY_PER_TICK)

        # Boredom
        if ticks_since_novel > 5:
            d["boredom"] = min(100.0, d["boredom"] + BOREDOM_BUILD_PER_TICK)

        # Frustration
        if d["hunger"] < HUNGER_CRITICAL or d["boredom"] > BOREDOM_PENALTY_THRESHOLD:
            em["frustration"] = min(FRUSTRATION_MAX, em["frustration"] + FRUSTRATION_BUILD_UNMET)
        else:
            em["frustration"] = max(0.0, em["frustration"] - FRUSTRATION_DECAY_PER_TICK)

        # Anxiety
        if d["hunger"] < ANXIETY_TRIGGER_HUNGER:
            em["anxiety"] = min(ANXIETY_MAX, em["anxiety"] + ANXIETY_BUILD_RATE)
        else:
            decay = ANXIETY_DECAY_RATE * p.get("resilience", 0.5)
            em["anxiety"] = max(0.0, em["anxiety"] - decay)

        # Excitement decay
        em["excitement"] = max(0.0, em["excitement"] - EXCITEMENT_DECAY_PER_TICK)

        # Mood (inertia)
        pull  = MOOD_HUNGER_PULL      * max(0, (50 - d["hunger"]) / 50)
        pull += MOOD_BOREDOM_PULL     * (d["boredom"] / 100)
        pull += MOOD_FRUSTRATION_PULL * (em["frustration"] / 100)
        target = max(-100.0, min(100.0, em["mood"] + pull))
        em["mood"] = em["mood"] * MOOD_INERTIA + target * (1 - MOOD_INERTIA)

        # Lethargy
        ticks_inactive = s["age_ticks"] - cog["ticks_since_active"]
        if ticks_inactive > LETHARGY_BUILD_INACTIVE_TICKS:
            cog["lethargy"] = min(100.0, cog["lethargy"] + LETHARGY_BUILD_RATE)
            d["lifespan_ticks_lost"] += cog["lethargy"] * LETHARGY_LIFESPAN_DRAIN
        else:
            cog["lethargy"] = max(0.0, cog["lethargy"] - LETHARGY_DECAY_ACTIVE)

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
        d   = self.state["drives"]
        em  = self.state["emotion"]
        cog = self.state["cognition"]
        if d["hunger"] < HUNGER_DANGER:             return "dying"
        if d["hunger"] < HUNGER_CRITICAL:           return "hunger"
        if em["anxiety"] > 60:                      return "anxiety"
        if em["frustration"] > 70:                  return "frustration"
        if cog["state"] == "rest":                  return "rest"
        if d["boredom"] > BOREDOM_PENALTY_THRESHOLD:return "boredom"
        if em["excitement"] > 50:                   return "excitement"
        if d["boredom"] > 40:                       return "curiosity"
        return "neutral"

    def age_days(self):
        return round(self.state["age_ticks"] / self.state["ticks_per_day"], 2)

    def days_remaining(self):
        d = self.state["drives"]
        eff  = self.state["age_ticks"] + d["lifespan_ticks_lost"]
        maxt = LIFESPAN_DAYS * self.state["ticks_per_day"]
        return round(max(0, (maxt - eff) / self.state["ticks_per_day"]), 1)

    def summary(self):
        d   = self.state["drives"]
        em  = self.state["emotion"]
        cog = self.state["cognition"]
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
        }
