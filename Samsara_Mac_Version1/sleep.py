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

import json, os, time, random
from config import TICK_INTERVAL_SECONDS, data_path

SLEEP_FILE = data_path("sleep_state.json")

# Sleep cycle timing
ACTIVE_TICKS_BEFORE_SLEEP = int((90 * 60) / TICK_INTERVAL_SECONDS)  # 90 min of activity
SLEEP_DURATION_TICKS      = int((18 * 60) / TICK_INTERVAL_SECONDS)  # 18 min sleep
DEEP_SLEEP_MEMORY_TICKS   = 3   # deep consolidation happens in first 3 ticks of sleep


class SleepSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(SLEEP_FILE):
            with open(SLEEP_FILE) as f:
                return json.load(f)
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
            sleep_pressure = s["ticks_active"] / ACTIVE_TICKS_BEFORE_SLEEP
            sleep_chance   = sleep_pressure * 0.15  # ramps up over time

            # Low energy increases sleep pressure
            if energy < 40:
                sleep_chance += 0.1
            if energy < 20:
                sleep_chance += 0.2

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
            "sleeping":       s["sleeping"],
            "phase":          s["sleep_phase"],
            "ticks_asleep":   s["ticks_asleep"],
            "ticks_active":   s["ticks_active"],
            "total_cycles":   s["total_sleep_cycles"],
            "pressure":       round(s["ticks_active"] / ACTIVE_TICKS_BEFORE_SLEEP * 100, 1),
        }
