# ============================================================
#  NEUROCHEMICALS
#  Adrenaline, Oxytocin, Dopamine — surges that override drives
#
#  These are NOT drives. They are temporary chemical states
#  that modulate everything else.
# ============================================================

import json, os, time
from config import TICK_INTERVAL_SECONDS, data_path


NEURO_FILE = data_path("neuro.json")


class NeurochemicalSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(NEURO_FILE):
            with open(NEURO_FILE) as f:
                return json.load(f)
        return {
            # Adrenaline: spikes on threat/shock, crashes after
            "adrenaline":      0.0,   # 0–100
            "adrenaline_crash":False,  # True during post-spike crash

            # Oxytocin: builds with gentle sustained care
            # This is how attachment forms
            "oxytocin":        20.0,  # 0–100, starts low
            "oxytocin_history":0.0,   # cumulative lifetime oxytocin (for DNA)

            # Dopamine: prediction error reward signal
            # Spikes on surprise, crashes after over-stimulation
            "dopamine":        30.0,
            "dopamine_satiation":0.0, # builds when too much stimulation

            # Cortisol: chronic stress — builds slowly, very slow decay
            "cortisol":        0.0,   # 0–100

            # Caretaker trust — builds with oxytocin history
            "caretaker_trust": 0.3,   # 0–1.0
        }

    def save(self):
        with open(NEURO_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  TICK — decay all chemicals each tick
    # ----------------------------------------------------------
    def tick(self, drives_summary):
        s = self.state
        hunger    = drives_summary["hunger"]
        dominant  = drives_summary["dominant"]

        # --- ADRENALINE ---
        # Faster decay — text conversation should not stay flooded
        if s["adrenaline"] > 5:
            s["adrenaline"] = max(0.0, s["adrenaline"] - 8.0)   # was 4.0
            if s["adrenaline"] < 5 and not s["adrenaline_crash"]:
                s["adrenaline_crash"] = True
        elif s["adrenaline_crash"]:
            s["adrenaline_crash"] = False

        # Hunger below danger triggers adrenaline automatically
        if hunger < 10:
            s["adrenaline"] = min(100.0, s["adrenaline"] + 8.0)

        # --- OXYTOCIN ---
        # Decays very slowly — attachment is durable
        s["oxytocin"] = max(0.0, s["oxytocin"] - 0.05)

        # --- DOPAMINE ---
        s["dopamine"] = max(10.0, s["dopamine"] - 0.5)
        s["dopamine_satiation"] = max(0.0, s["dopamine_satiation"] - 0.3)

        # --- CORTISOL ---
        # Builds with sustained stress
        if dominant in ("dying", "hunger", "frustration", "anxiety"):
            s["cortisol"] = min(100.0, s["cortisol"] + 0.8)
        else:
            s["cortisol"] = max(0.0, s["cortisol"] - 0.2)

        # Caretaker trust builds slowly with oxytocin
        if s["oxytocin"] > 50:
            s["caretaker_trust"] = min(1.0, s["caretaker_trust"] + 0.001)

        self.save()

    # ----------------------------------------------------------
    #  TRIGGERS
    # ----------------------------------------------------------
    def trigger_adrenaline(self, intensity=50.0):
        """Sudden threat, shock, loud noise, near-death."""
        self.state["adrenaline"] = min(100.0, self.state["adrenaline"] + intensity)
        # Adrenaline suppresses oxytocin temporarily
        self.state["oxytocin"] = max(0.0, self.state["oxytocin"] - 10.0)
        self.save()

    def trigger_oxytocin(self, amount=8.0):
        """Gentle touch, being fed when desperate, sustained kind interaction."""
        self.state["oxytocin"] = min(100.0, self.state["oxytocin"] + amount)
        self.state["oxytocin_history"] += amount
        # Oxytocin suppresses cortisol
        self.state["cortisol"] = max(0.0, self.state["cortisol"] - amount * 0.3)
        self.save()

    def trigger_dopamine(self, amount=15.0):
        """Surprise, novel input, prediction error reward."""
        # Diminishing returns — satiation reduces effect
        effective = amount * (1 - self.state["dopamine_satiation"] / 100)
        self.state["dopamine"] = min(100.0, self.state["dopamine"] + effective)
        self.state["dopamine_satiation"] = min(100.0, self.state["dopamine_satiation"] + amount * 0.3)
        self.save()

    def trigger_feed_reward(self, hunger_before):
        """Being fed — oxytocin + dopamine, proportional to how hungry it was."""
        desperation = max(0, (50 - hunger_before) / 50)  # 0 to 1
        self.trigger_oxytocin(amount=5 + desperation * 20)
        self.trigger_dopamine(amount=10 + desperation * 15)
        # Adrenaline drop if it was in danger
        if hunger_before < 15:
            self.state["adrenaline"] = max(0.0, self.state["adrenaline"] - 30)
        self.save()

    def on_sudden_input(self):
        """Unexpected input — gentle adrenaline + dopamine spike.
        Tuned for text conversation — not physical robot startle."""
        self.trigger_adrenaline(intensity=4.0)    # was 15.0 — way too high for text
        self.trigger_dopamine(amount=10.0)         # was 12.0 — slight reduction

    def on_kind_interaction(self):
        """Calm, sustained, gentle interaction."""
        self.trigger_oxytocin(amount=3.0)          # was 5.0 — slower trust build, more realistic
        self.state["cortisol"] = max(0.0, self.state["cortisol"] - 2.0)  # was 3.0
        self.save()

    # ----------------------------------------------------------
    #  READ
    # ----------------------------------------------------------
    def modifiers(self):
        """Returns modifiers other systems should apply."""
        s = self.state
        return {
            # Adrenaline: forces alertness, boosts talkativeness
            "talk_multiplier":    1.0 + (s["adrenaline"] / 100) * 1.5
                                      - (0.5 if s["adrenaline_crash"] else 0),
            "sleep_blocked":      s["adrenaline"] > 50,  # was 30 — only block sleep if truly alarmed
            "anxiety_boost":      s["cortisol"] / 100 * 20,

            # Oxytocin: reduces anxiety, increases warmth
            "anxiety_reduction":  s["oxytocin"] / 100 * 15,
            "mood_boost":         s["oxytocin"] / 100 * 10,
            "caretaker_trust":    s["caretaker_trust"],

            # Dopamine: predicts how exciting novel input feels
            "novelty_sensitivity":1.0 + (100 - s["dopamine_satiation"]) / 100,

            # Crash state
            "in_crash":           s["adrenaline_crash"],
            "cortisol_level":     s["cortisol"],
        }

    def summary(self):
        s = self.state
        return {
            "adrenaline":      round(s["adrenaline"], 1),
            "oxytocin":        round(s["oxytocin"], 1),
            "dopamine":        round(s["dopamine"], 1),
            "cortisol":        round(s["cortisol"], 1),
            "caretaker_trust": round(s["caretaker_trust"], 2),
            "in_crash":        s["adrenaline_crash"],
        }
