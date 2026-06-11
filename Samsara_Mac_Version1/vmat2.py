# ============================================================
#  VMAT2 — Deliberation Buffer
#
#  The pause between urge and action.
#  Gen 1: almost no pause (pure reflex)
#  Gen 6: meaningful deliberation window
#
#  During the buffer, competing signals can influence outcome.
#  The urge is FELT but not yet ACTED ON.
#  This is where choice begins to exist.
# ============================================================

import json, os
from config import (VMAT2_BASE_BUFFER_TICKS, VMAT2_GROWTH_PER_GEN,
                    VMAT2_MAX_BUFFER_TICKS, data_path)

VMAT2_FILE = data_path("vmat2.json")


class VMAT2System:

    def __init__(self, generation):
        self.generation = generation
        self.buffer_size = min(
            VMAT2_MAX_BUFFER_TICKS,
            VMAT2_BASE_BUFFER_TICKS + (generation - 1) * VMAT2_GROWTH_PER_GEN
        )
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(VMAT2_FILE):
            with open(VMAT2_FILE) as f:
                return json.load(f)
        return {
            "pending_urge":        None,   # urge being held
            "urge_ticks_held":     0,
            "competing_signals":   [],     # signals that arose during buffer
            "deliberations":       [],     # log of what was considered
            "overrides":           0,      # count of times urge was overridden
            "acted_on":            0,      # count of times urge was followed
        }

    def _save(self):
        with open(VMAT2_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def submit_urge(self, urge_type, intensity, context):
        """
        An urge arrives. Hold it in the buffer.
        If buffer is full (Gen 1 = 1 tick), resolve immediately.
        """
        s = self.state

        # If no pending urge, start holding this one
        if s["pending_urge"] is None:
            s["pending_urge"]    = {"type": urge_type, "intensity": intensity, "context": context}
            s["urge_ticks_held"] = 0
            s["competing_signals"] = []
            self._save()
            return None  # not resolved yet

        # Already holding an urge — add as competing signal
        s["competing_signals"].append({
            "type":      urge_type,
            "intensity": intensity,
            "context":   context,
        })
        self._save()
        return None

    def tick(self, drives_summary, neuro_summary, consequence_memory):
        """
        Called every tick. Returns resolved urge or None.
        During buffer window, competing signals accumulate.
        At buffer end, deliberation resolves.
        """
        s = self.state

        if s["pending_urge"] is None:
            return None

        s["urge_ticks_held"] += 1

        # Not yet resolved
        if s["urge_ticks_held"] < self.buffer_size:
            self._save()
            return None

        # Buffer complete — deliberate
        result = self._deliberate(drives_summary, neuro_summary, consequence_memory)
        self._save()
        return result

    def _deliberate(self, drives_summary, neuro_summary, consequence_memory):
        """
        At end of buffer: weigh the original urge against
        competing signals and consequence memory.
        Returns what to actually do.
        """
        s      = self.state
        urge   = s["pending_urge"]
        rivals = s["competing_signals"]

        # Base: act on the urge
        act_on_urge = True
        override_reason = None

        # Check consequence memory — did this urge-type cause social pain before?
        past_pain = consequence_memory.get_pain_for_urge(urge["type"])
        if past_pain > 0.5 and self.buffer_size > 1:
            # Meaningful past pain — consider suppressing
            suppress_chance = past_pain * (self.buffer_size / VMAT2_MAX_BUFFER_TICKS)
            import random
            if random.random() < suppress_chance:
                act_on_urge = False
                override_reason = f"past_social_pain:{past_pain:.2f}"

        # High-oxytocin source recently disapproved of similar behavior
        if neuro_summary["cortisol"] > 60 and urge["type"] == "anger_expression":
            act_on_urge = False
            override_reason = "cortisol_high_anger_suppressed"

        # Log deliberation
        s["deliberations"].append({
            "urge":           urge["type"],
            "held_ticks":     s["urge_ticks_held"],
            "competing":      len(rivals),
            "acted_on_urge":  act_on_urge,
            "override_reason":override_reason,
        })
        if len(s["deliberations"]) > 20:
            s["deliberations"].pop(0)

        if act_on_urge:
            s["acted_on"] += 1
        else:
            s["overrides"] += 1

        # Reset buffer
        resolved = urge.copy()
        resolved["acted_on"]        = act_on_urge
        resolved["override_reason"] = override_reason
        resolved["competitors"]     = rivals

        s["pending_urge"]      = None
        s["urge_ticks_held"]   = 0
        s["competing_signals"] = []

        return resolved

    def summary(self):
        s = self.state
        return {
            "buffer_size":   round(self.buffer_size, 1),
            "pending_urge":  s["pending_urge"]["type"] if s["pending_urge"] else None,
            "ticks_held":    s["urge_ticks_held"],
            "total_overrides": s["overrides"],
            "total_acted":   s["acted_on"],
        }
