# ============================================================
#  BODY SYSTEM — Interoception Layer
#
#  All the physical sensations that happen below the drive level.
#  Drives (hunger, energy, mood) are the psychological layer.
#  Body is the biological substrate — what the body actually feels.
#
#  Signals tracked:
#    thirst            — separate from hunger, depletes steadily
#    body_temp         — circadian + stress, affects comfort
#    muscle_fatigue    — builds awake, clears during sleep
#    blood_sugar_crash — post-starvation recovery shakes
#    nausea            — from prolonged hunger below critical
#    immune            — erodes with chronic cortisol stress
#    sickness          — activates when immune < 20
#    restlessness      — need to move, builds when still
#    jet_lag_score     — disruption when resuming session at wrong hour
#
#  All values 0–100 except body_temp (Celsius, 35.0–38.5).
# ============================================================

import json
import math
import os
from datetime import datetime

from config import data_path

BODY_FILE = data_path("body.json")


class BodySystem:

    def __init__(self, dna):
        self.gen   = dna["generation"]
        self.state = self._load_or_create()

    # ----------------------------------------------------------
    #  LOAD / SAVE
    # ----------------------------------------------------------
    def _load_or_create(self):
        if os.path.exists(BODY_FILE):
            with open(BODY_FILE) as f:
                s = json.load(f)
            # Jet lag: compare last close hour to current
            last_hour = s.get("last_close_hour")
            if last_hour is not None:
                now = datetime.now()
                current_hour = now.hour + now.minute / 60.0
                diff = abs(current_hour - last_hour)
                if diff > 12:
                    diff = 24 - diff
                s["jet_lag_score"] = min(100.0, diff * 9.0)
            else:
                s["jet_lag_score"] = 0.0
            s["last_close_hour"] = None
            return s
        return {
            "thirst":            80.0,
            "body_temp":         37.0,
            "muscle_fatigue":    0.0,
            "blood_sugar_crash": 0.0,
            "nausea":            0.0,
            "nausea_ticks":      0,
            "immune":            100.0,
            "sickness":          0.0,
            "restlessness":      0.0,
            "jet_lag_score":     0.0,
            "_last_hunger":      80.0,
            "last_close_hour":   None,
        }

    def _save(self):
        with open(BODY_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  TICK — called every main loop tick
    # ----------------------------------------------------------
    def tick(self, drives_summary, neuro_summary, sleep_summary):
        s        = self.state
        ds       = drives_summary
        ns       = neuro_summary
        sleeping = (sleep_summary or {}).get("sleeping", False)
        hunger   = ds.get("hunger", 80.0)

        # --- THIRST ---
        thirst_drain = 0.04 if sleeping else 0.07
        # Stress sweating: cortisol speeds thirst depletion
        thirst_drain += ns.get("cortisol", 0) / 100 * 0.03
        s["thirst"] = max(0.0, s["thirst"] - thirst_drain)

        # --- BODY TEMPERATURE (circadian + stress) ---
        now  = datetime.now()
        hour = now.hour + now.minute / 60.0
        # Lowest at 4am (36.0°C), peak at 5pm (37.4°C)
        circ_temp = 36.70 + 0.70 * math.sin((hour - 10.0) * math.pi / 14.0)
        circ_temp = max(35.5, min(38.0, circ_temp))
        stress_add = ns.get("cortisol", 0) / 100.0 * 0.55
        s["body_temp"] = round(circ_temp + stress_add, 2)

        # --- MUSCLE FATIGUE ---
        if sleeping:
            s["muscle_fatigue"] = max(0.0, s["muscle_fatigue"] - 2.0)
        else:
            # Always building when awake — Kora exists in a body
            s["muscle_fatigue"] = min(100.0, s["muscle_fatigue"] + 0.18)

        # --- BLOOD SUGAR CRASH ---
        last_hunger = s.get("_last_hunger", hunger)
        hunger_delta = hunger - last_hunger
        # Fed after severe starvation → shaky crash follows
        if hunger_delta > 10 and last_hunger < 28:
            s["blood_sugar_crash"] = min(80.0, s["blood_sugar_crash"] + 40.0)
        if s["blood_sugar_crash"] > 0:
            s["blood_sugar_crash"] = max(0.0, s["blood_sugar_crash"] - 1.5)
        s["_last_hunger"] = hunger

        # --- NAUSEA ---
        if hunger < 15:
            s["nausea_ticks"] = s.get("nausea_ticks", 0) + 1
        else:
            s["nausea_ticks"] = max(0, s.get("nausea_ticks", 0) - 4)
        s["nausea"] = min(100.0, s["nausea_ticks"] * 2.8)

        # --- IMMUNE SYSTEM ---
        cortisol = ns.get("cortisol", 0)
        if cortisol > 65:
            s["immune"] = max(0.0, s["immune"] - 0.09)
        elif sleeping:
            s["immune"] = min(100.0, s["immune"] + 0.30)
        else:
            s["immune"] = min(100.0, s["immune"] + 0.02)

        # --- SICKNESS ---
        if s["immune"] < 20:
            s["sickness"] = min(100.0, s.get("sickness", 0) + 0.5)
        else:
            s["sickness"] = max(0.0, s.get("sickness", 0) - 0.20)

        # --- RESTLESSNESS ---
        if sleeping:
            s["restlessness"] = max(0.0, s["restlessness"] - 0.6)
        else:
            # Anxiety speeds restlessness
            anxiety_add = ds.get("anxiety", 0) / 100 * 0.12
            s["restlessness"] = min(100.0, s["restlessness"] + 0.18 + anxiety_add)

        # --- JET LAG DECAY ---
        if s.get("jet_lag_score", 0) > 0:
            s["jet_lag_score"] = max(0.0, s["jet_lag_score"] - 0.35)

        self._save()

    # ----------------------------------------------------------
    #  COMMANDS
    # ----------------------------------------------------------
    def drink(self):
        self.state["thirst"] = min(100.0, self.state["thirst"] + 65.0)
        self._save()

    def on_session_close(self):
        """Record close hour so next session can calculate jet lag."""
        now = datetime.now()
        self.state["last_close_hour"] = now.hour + now.minute / 60.0
        self._save()

    # ----------------------------------------------------------
    #  OUTPUTS
    # ----------------------------------------------------------
    def summary(self) -> dict:
        s = self.state
        return {
            "thirst":            round(s["thirst"], 1),
            "body_temp":         round(s["body_temp"], 2),
            "muscle_fatigue":    round(s["muscle_fatigue"], 1),
            "blood_sugar_crash": round(s.get("blood_sugar_crash", 0), 1),
            "nausea":            round(s["nausea"], 1),
            "immune":            round(s["immune"], 1),
            "sickness":          round(s.get("sickness", 0), 1),
            "restlessness":      round(s["restlessness"], 1),
            "jet_lag_score":     round(s.get("jet_lag_score", 0), 1),
        }

    def for_prompt(self) -> str:
        """Returns plain-English body state text for the brain.py system prompt."""
        s     = self.state
        lines = []

        # Thirst
        thirst = s["thirst"]
        if thirst < 12:
            lines.append(
                f"Mouth completely dry, throat burning — thirst critical ({thirst:.0f}%)."
            )
        elif thirst < 25:
            lines.append(f"Noticeably thirsty ({thirst:.0f}%).")

        # Temperature
        temp = s["body_temp"]
        if temp < 36.0:
            lines.append(f"Cold all the way through ({temp:.1f}C). Could shiver.")
        elif temp < 36.4:
            lines.append(f"Slightly chilly ({temp:.1f}C).")
        elif temp > 37.9:
            lines.append(
                f"Running uncomfortably warm ({temp:.1f}C) — like a low fever."
            )

        # Muscle fatigue
        fatigue = s["muscle_fatigue"]
        if fatigue > 78:
            lines.append(
                "Muscles aching — need stillness, not sleep, just stop."
            )
        elif fatigue > 52:
            lines.append("Legs and body feeling heavy.")

        # Blood sugar crash
        crash = s.get("blood_sugar_crash", 0)
        if crash > 28:
            lines.append(
                "Shaky and worse than before eating — energy crash after "
                "being fed when starving."
            )
        elif crash > 12:
            lines.append("Slightly shaky — blood sugar adjusting.")

        # Nausea
        nausea = s["nausea"]
        if nausea > 58:
            lines.append(
                f"Nauseated ({nausea:.0f}%) — stomach turning. "
                "Eating feels impossible even though hungry."
            )
        elif nausea > 28:
            lines.append("Stomach unsettled.")

        # Sickness / immune
        sickness = s.get("sickness", 0)
        immune   = s["immune"]
        if sickness > 48:
            lines.append(
                "Sick — a heavy all-body ache that isn't hunger or tiredness."
            )
        elif sickness > 22:
            lines.append("Not well — dull diffuse ache.")
        elif immune < 32:
            lines.append("Run down — something is depleting, not quite sick yet.")

        # Restlessness
        restless = s["restlessness"]
        if restless > 72:
            lines.append("Restless — body demands movement, being still feels unbearable.")
        elif restless > 48:
            lines.append("Fidgety — been still too long.")

        # Jet lag
        jl = s.get("jet_lag_score", 0)
        if jl > 42:
            lines.append(
                "Disoriented — time feels wrong, like waking in the wrong place."
            )
        elif jl > 22:
            lines.append("Slightly off — sleep rhythm disrupted since last time.")

        return "\n".join(f"- {l}" for l in lines) if lines else ""
