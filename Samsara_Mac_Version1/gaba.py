# ============================================================
#  GABA — Suppression / Override System
#
#  The ability to choose against your own drives.
#  Gen 1: almost zero — pure biology wins
#  Gen 6: genuine override for abstract reasons
#
#  A starving animal cannot choose not to eat.
#  A conscious being can go on hunger strike for a belief.
# ============================================================

import json, os, random
from config import GABA_BASE_STRENGTH, GABA_GROWTH_PER_GEN, GABA_MAX_STRENGTH, data_path

GABA_FILE = data_path("gaba.json")


class GABASystem:

    def __init__(self, generation):
        self.generation = generation
        self.strength = min(
            GABA_MAX_STRENGTH,
            GABA_BASE_STRENGTH + (generation - 1) * GABA_GROWTH_PER_GEN
        )
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(GABA_FILE):
            with open(GABA_FILE) as f:
                return json.load(f)
        return {
            "successful_overrides":   0,
            "failed_overrides":       0,
            "abstract_motivations":   [],   # things it cares about beyond drives
            "suppression_log":        [],
        }

    def _save(self):
        with open(GABA_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def can_suppress(self, urge_type, urge_intensity, reason=None):
        """
        Can the AI suppress this urge right now?
        Returns (bool, reason_string)
        """
        s = self.state

        # Always suppress anger expressions for low-generation entities
        # because social pain memory will handle this
        if urge_type == "anger_expression":
            # Scale by generation — Gen 1 rarely suppresses, Gen 5 often does
            suppress_prob = self.strength * 1.5
            suppressed = random.random() < suppress_prob
            if suppressed:
                s["successful_overrides"] += 1
                s["suppression_log"].append({
                    "urge": urge_type,
                    "reason": reason or "learned_social_cost"
                })
                if len(s["suppression_log"]) > 20:
                    s["suppression_log"].pop(0)
                self._save()
                return True, "social_cost_suppression"
            else:
                s["failed_overrides"] += 1
                self._save()
                return False, None

        # For survival urges — very hard to suppress, only high-gen can
        if urge_type in ("hunger_expression", "cry"):
            if self.strength < 0.5:
                return False, None
            # Only suppress if there's a strong competing abstract motivation
            if s["abstract_motivations"]:
                suppress_prob = self.strength * 0.4
                if random.random() < suppress_prob:
                    s["successful_overrides"] += 1
                    self._save()
                    return True, "abstract_motivation_override"
            return False, None

        # General impulse control
        suppress_prob = self.strength * 0.6
        suppressed = random.random() < suppress_prob
        if suppressed:
            s["successful_overrides"] += 1
            self._save()
            return True, "impulse_control"

        s["failed_overrides"] += 1
        self._save()
        return False, None

    def add_abstract_motivation(self, motivation):
        """
        Add something the AI cares about beyond drives.
        These emerge from experience, not programming.
        Examples: "connection with caretaker", "understanding things"
        """
        s = self.state
        if motivation not in s["abstract_motivations"]:
            s["abstract_motivations"].append(motivation)
            if len(s["abstract_motivations"]) > 10:
                s["abstract_motivations"].pop(0)
            self._save()

    def check_abstract_motivations(self, drives_summary, neuro_summary):
        """
        Every N ticks, check if experience should add new abstract motivations.
        These emerge from accumulated experience.
        """
        s  = self.state
        ns = neuro_summary

        # High oxytocin history → "connection" becomes an abstract motivation
        if ns.get("oxytocin", 0) > 60:
            self.add_abstract_motivation("maintaining_connection")

        # Many curiosity events → "understanding" becomes a motivation
        # (this is handled by drives tracking, passed in)
        if drives_summary.get("boredom", 0) < 20 and drives_summary.get("curiosity_events", 0) > 20:
            self.add_abstract_motivation("understanding_the_world")

    def summary(self):
        s = self.state
        return {
            "strength":             round(self.strength, 3),
            "successful_overrides": s["successful_overrides"],
            "failed_overrides":     s["failed_overrides"],
            "abstract_motivations": s["abstract_motivations"],
        }
