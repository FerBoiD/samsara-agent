# ============================================================
#  SLEEP SYSTEM
#
#  Sleep cycle: every ~90 minutes of active time
#  Duration: 15-20 minutes per cycle
#  During sleep: memory consolidates, DNA gets updated fragments
#
#  At SESSION END (shutdown): deep sleep runs full consolidation
#  → writes everything important into DNA for next generation
#
#  Gen 1 sleeps. Gen 2 is born knowing Gen 1 slept.
# ============================================================

import json, os, time, random, math
from datetime import datetime
from config import TICK_INTERVAL_SECONDS, data_path

SLEEP_FILE = data_path("sleep_state.json")

# Sleep cycle timing
SLEEP_MIN_ACTIVE_TICKS    = 120                                       # 20 min mandatory awake before sleep possible
ACTIVE_TICKS_BEFORE_SLEEP = int((60 * 60) / TICK_INTERVAL_SECONDS)   # pressure ramps over 60 min window
SLEEP_DURATION_TICKS      = int((6 * 60) / TICK_INTERVAL_SECONDS)    # 6 min sleep
DEEP_SLEEP_MEMORY_TICKS   = 3   # deep consolidation happens in first 3 ticks of sleep


def circadian_sleep_pressure():
    """
    Returns a 0.0–1.0 multiplier for sleep pressure based on real time of day.
    Peaks at ~3am (most drowsy), troughs at ~10am (most alert).
    Uses a cosine curve shifted so midnight = high pressure.
    This is purely additive — it doesn't force sleep, just nudges it.
    """
    hour = datetime.now().hour + datetime.now().minute / 60.0
    # Cosine with period 24h, peak at hour 3, trough at hour 15
    pressure = 0.5 + 0.5 * math.cos(math.pi * (hour - 3) / 12)
    return round(pressure, 3)


def circadian_alertness_modifier():
    """
    Returns a text description of the circadian state for brain.py context.
    """
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return "deep-night"    # very high sleep pressure
    elif 6 <= hour < 10:
        return "early-morning" # waking, still a bit groggy
    elif 10 <= hour < 14:
        return "midday"        # most alert
    elif 14 <= hour < 17:
        return "afternoon"     # mild post-lunch dip
    elif 17 <= hour < 21:
        return "evening"       # relaxed
    else:
        return "late-night"    # sleep pressure building


class SleepSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(SLEEP_FILE):
            with open(SLEEP_FILE) as f:
                state = json.load(f)
            # Cap leftover ticks_active so a long previous session doesn't
            # cause immediate sleep on restart
            state["ticks_active"] = min(state["ticks_active"], SLEEP_MIN_ACTIVE_TICKS - 1)
            return state
        return {
            "sleeping":            False,
            "sleep_phase":         None,    # "light" | "deep" | "rem"
            "ticks_asleep":        0,
            "ticks_active":        0,
            "total_sleep_cycles":  0,
            "last_consolidation":  0,       # tick of last memory consolidation
            "consolidation_done_this_cycle": False,
        }

    def save(self):
        with open(SLEEP_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  TICK
    # ----------------------------------------------------------
    def tick(self, drives_summary, neuro_modifiers, memory, dna):
        """
        Returns: "sleeping" | "waking" | "awake" | "consolidating"
        """
        s = self.state
        energy   = drives_summary["energy"]
        dominant = drives_summary["dominant"]

        # Can't sleep if adrenaline is high or critically hungry
        blocked = (
            neuro_modifiers["sleep_blocked"] or
            dominant in ("dying", "hunger")
        )

        if not s["sleeping"]:
            s["ticks_active"] += 1

            # Should we fall asleep?
            # Sleep pressure only builds after mandatory awake minimum
            if s["ticks_active"] < SLEEP_MIN_ACTIVE_TICKS:
                sleep_chance = 0.0
            else:
                ramp           = s["ticks_active"] - SLEEP_MIN_ACTIVE_TICKS
                sleep_pressure = min(1.0, ramp / ACTIVE_TICKS_BEFORE_SLEEP)
                sleep_chance   = sleep_pressure * 0.15

            # Circadian rhythm — nudge only, not dominant
            circ = circadian_sleep_pressure()
            sleep_chance += circ * 0.03   # max +0.03 at 3am

            if not blocked and (random.random() < sleep_chance or energy < 15):
                self._enter_sleep()
                self.save()
                return "sleeping"

            self.save()
            return "awake"

        else:
            # Currently sleeping
            s["ticks_asleep"] += 1

            # Determine sleep phase
            if s["ticks_asleep"] <= 2:
                s["sleep_phase"] = "light"
            elif s["ticks_asleep"] <= DEEP_SLEEP_MEMORY_TICKS:
                s["sleep_phase"] = "deep"
                # Deep sleep: consolidate memory into DNA
                if not s["consolidation_done_this_cycle"]:
                    self._consolidate(memory, dna, drives_summary)
                    s["consolidation_done_this_cycle"] = True
                    self.save()
                    return "consolidating"
            else:
                s["sleep_phase"] = "rem"

            # Should we wake up?
            if s["ticks_asleep"] >= SLEEP_DURATION_TICKS:
                self._wake_up()
                self.save()
                return "waking"

            # Adrenaline spike wakes us up
            if blocked and s["ticks_asleep"] > 2:
                self._wake_up()
                self.save()
                return "waking"

            self.save()
            if s["sleep_phase"] == "rem":
                return "rem"
            return "sleeping"

    def _enter_sleep(self):
        self.state["sleeping"]     = True
        self.state["ticks_asleep"] = 0
        self.state["sleep_phase"]  = "light"
        self.state["consolidation_done_this_cycle"] = False
        print("[SLEEP] Entering sleep...")

    def _wake_up(self):
        self.state["sleeping"]            = False
        self.state["sleep_phase"]         = None
        self.state["ticks_asleep"]        = 0
        self.state["ticks_active"]        = 0
        self.state["total_sleep_cycles"] += 1
        print(f"[SLEEP] Waking up. Total cycles: {self.state['total_sleep_cycles']}")

    # ----------------------------------------------------------
    #  MEMORY CONSOLIDATION
    # ----------------------------------------------------------
    def _consolidate(self, memory, dna, drives_summary):
        """
        Deep sleep consolidation:
        1. Identify most important memories from today
        2. Write them as fragments into DNA
        3. Prune redundant short-term memories
        4. Update inherited tendencies in DNA
        """
        print("[SLEEP] Deep consolidation running...")

        # Decay faded memories before consolidating — only the strong survive
        memory.decay()

        # Get top emotional memories
        emotional = memory.data.get("emotional_events", [])
        emotional.sort(key=lambda x: x.get("intensity", 0), reverse=True)
        top_memories = emotional[:3]

        # Write to DNA as consolidated fragments
        existing = dna.get("consolidated_memories", [])
        for mem in top_memories:
            fragment = {
                "text":      mem["text"][:60],
                "emotion":   mem["dominant"],
                "intensity": mem["intensity"],
                "cycle":     self.state["total_sleep_cycles"],
            }
            # Don't duplicate
            if not any(e["text"] == fragment["text"] for e in existing):
                existing.append(fragment)

        # Keep only top 10 in DNA
        existing.sort(key=lambda x: x.get("intensity", 0), reverse=True)
        dna["consolidated_memories"] = existing[:10]

        # Update anxiety baseline in DNA
        current_anxiety = drives_summary.get("anxiety", 0)
        old_baseline    = dna["inherited_tendencies"].get("anxiety_baseline", 0)
        # Rolling average — anxiety history slowly shifts DNA
        dna["inherited_tendencies"]["anxiety_baseline"] = round(
            old_baseline * 0.8 + (current_anxiety / 100) * 0.2, 3
        )

        from dna import save_dna
        save_dna(dna)
        self.state["last_consolidation"] = self.state["total_sleep_cycles"]
        print("[SLEEP] Consolidation complete. DNA updated.")

    def full_consolidation(self, memory, dna, drives_state, neuro_state,
                           total_interactions, cause_of_death):
        """
        Called at session end / death.
        Full lifetime consolidation into DNA.
        """
        print("[SLEEP] FULL LIFETIME CONSOLIDATION...")
        from dna import consolidate_to_dna

        # Add neuro history to drives_state for consolidation
        drives_state["oxytocin"] = neuro_state.get("oxytocin", 0)

        consolidate_to_dna(
            dna,
            drives_state,
            memory.data,
            total_interactions,
            cause_of_death
        )
        print("[SLEEP] Full consolidation done. Parent DNA ready for Gen 2.")

    # ----------------------------------------------------------
    #  STATE
    # ----------------------------------------------------------
    def summary(self):
        s = self.state
        return {
            "sleeping":          s["sleeping"],
            "phase":             s["sleep_phase"],
            "ticks_asleep":      s["ticks_asleep"],
            "ticks_active":      s["ticks_active"],
            "total_cycles":      s["total_sleep_cycles"],
            "pressure":          round(s["ticks_active"] / ACTIVE_TICKS_BEFORE_SLEEP * 100, 1),
            "circadian_pressure":circadian_sleep_pressure(),
            "time_of_day":       circadian_alertness_modifier(),
        }
