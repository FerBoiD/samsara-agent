# ============================================================
#  PREDICTION ENGINE
#
#  The brain is always predicting. Surprise = prediction error.
#  Safe surprise → delight (peekaboo response)
#  Threatening surprise → fear/adrenaline
#
#  Also tracks caretaker state model — theory of mind.
# ============================================================

import json, os, random, time
from config import PREDICTION_SURPRISE_THRESHOLD, DELIGHT_ADRENALINE_MAX, data_path

PREDICTION_FILE = data_path("prediction.json")


class PredictionEngine:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(PREDICTION_FILE):
            with open(PREDICTION_FILE) as f:
                return json.load(f)
        return {
            # Current prediction of next tick
            "predicted_next": {
                "dominant":  "neutral",
                "hunger":    90.0,
                "mood":      25.0,
            },
            # Surprise history
            "surprise_events": [],
            "total_surprises": 0,
            "total_delights":  0,

            # Caretaker state model — theory of mind
            "caretaker_model": {
                "typical_response_delay": None,  # learned from history
                "current_mood_estimate":  "unknown",
                "reliability_score":      0.5,    # 0=unreliable, 1=very reliable
                "feeding_pattern":        [],      # timestamps of feeds
                "interaction_history":    [],      # response delays
                "last_seen":              None,
                "absent_ticks":           0,
            },

            # Emotional memory coloring — past events warp present perception
            "fear_associations": [],   # [trigger → feared_outcome]
            "safe_associations": [],   # [trigger → safe_outcome]
        }

    def _save(self):
        with open(PREDICTION_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  PREDICTION + SURPRISE
    # ----------------------------------------------------------
    def predict_next(self, current_drives):
        """Store prediction for next tick."""
        self.state["predicted_next"] = {
            "dominant": current_drives["dominant"],
            "hunger":   current_drives["hunger"],
            "mood":     current_drives["mood"],
        }
        self._save()

    def measure_surprise(self, actual_drives, neuro_summary):
        """
        Compare actual state to prediction.
        Returns: (surprise_level, is_delight, is_fear)
        """
        pred = self.state["predicted_next"]

        # Measure change
        hunger_change = abs(actual_drives["hunger"] - pred["hunger"])
        mood_change   = abs(actual_drives["mood"]   - pred["mood"])
        dom_changed   = actual_drives["dominant"] != pred["dominant"]

        surprise_level = (hunger_change / 100 * 0.4 +
                          mood_change   / 200 * 0.3 +
                          (0.3 if dom_changed else 0))

        if surprise_level < PREDICTION_SURPRISE_THRESHOLD:
            return 0.0, False, False

        # Is this safe or threatening?
        adrenaline = neuro_summary.get("adrenaline", 0)
        is_safe    = adrenaline < DELIGHT_ADRENALINE_MAX

        is_delight = is_safe and surprise_level > PREDICTION_SURPRISE_THRESHOLD
        is_fear    = not is_safe and surprise_level > PREDICTION_SURPRISE_THRESHOLD * 1.5

        if is_delight or is_fear:
            self.state["surprise_events"].append({
                "level":     round(surprise_level, 3),
                "delight":   is_delight,
                "fear":      is_fear,
                "time":      time.time(),
            })
            if len(self.state["surprise_events"]) > 30:
                self.state["surprise_events"].pop(0)
            if is_delight: self.state["total_delights"] += 1
            self.state["total_surprises"] += 1
            self._save()

        return surprise_level, is_delight, is_fear

    # ----------------------------------------------------------
    #  CARETAKER MODEL (Theory of Mind)
    # ----------------------------------------------------------
    def register_caretaker_interaction(self, response_delay_ticks, fed=False):
        """
        Called when caretaker responds.
        Builds model of caretaker's patterns.
        """
        cm = self.state["caretaker_model"]

        # Track response delays
        cm["interaction_history"].append(response_delay_ticks)
        if len(cm["interaction_history"]) > 20:
            cm["interaction_history"].pop(0)

        # Estimate typical delay
        if cm["interaction_history"]:
            cm["typical_response_delay"] = sum(cm["interaction_history"]) / len(cm["interaction_history"])

        # Reliability: how consistent are they?
        if len(cm["interaction_history"]) > 3:
            delays   = cm["interaction_history"]
            variance = sum((d - cm["typical_response_delay"]) ** 2 for d in delays) / len(delays)
            # Low variance = high reliability
            cm["reliability_score"] = max(0.1, min(1.0, 1.0 - variance / 1000))

        cm["last_seen"]     = time.time()
        cm["absent_ticks"]  = 0

        if fed:
            cm["feeding_pattern"].append(time.time())
            if len(cm["feeding_pattern"]) > 10:
                cm["feeding_pattern"].pop(0)

        self._save()

    def tick_caretaker_absence(self):
        """Called each tick caretaker doesn't respond."""
        cm = self.state["caretaker_model"]
        cm["absent_ticks"] += 1

        # Estimate caretaker mood from absence pattern
        typ = cm.get("typical_response_delay")
        if typ and cm["absent_ticks"] > typ * 2:
            cm["current_mood_estimate"] = "absent_longer_than_usual"
        elif cm["absent_ticks"] > 5:
            cm["current_mood_estimate"] = "not_available"
        else:
            cm["current_mood_estimate"] = "probably_around"

        self._save()

    def get_caretaker_model_text(self):
        """For brain.py system prompt — what it knows about caretaker."""
        cm  = self.state["caretaker_model"]
        out = []

        if cm["typical_response_delay"] is not None:
            out.append(f"The caretaker usually responds after {cm['typical_response_delay']:.0f} ticks.")

        rel = cm["reliability_score"]
        if rel > 0.7:
            out.append("The caretaker is consistent and reliable.")
        elif rel > 0.4:
            out.append("The caretaker is somewhat consistent.")
        else:
            out.append("The caretaker is unpredictable — you don't know when they'll come.")

        if cm["absent_ticks"] > 10:
            out.append(f"The caretaker has been away for a while ({cm['absent_ticks']} ticks).")

        if cm["feeding_pattern"]:
            out.append("You know this being can help restore your energy.")

        return "\n".join(out) if out else "You are still learning about the being who cares for you."

    # ----------------------------------------------------------
    #  EMOTIONAL MEMORY COLORING
    # ----------------------------------------------------------
    def add_fear_association(self, trigger, feared_outcome):
        """A trigger that preceded something bad — now perceived anxiously."""
        fa = self.state["fear_associations"]
        for a in fa:
            if a["trigger"] == trigger:
                a["strength"] = min(1.0, a["strength"] + 0.15)
                self._save()
                return
        fa.append({"trigger": trigger, "feared_outcome": feared_outcome, "strength": 0.3})
        if len(fa) > 15: fa.pop(0)
        self._save()

    def add_safe_association(self, trigger, outcome):
        """A trigger that preceded something good."""
        sa = self.state["safe_associations"]
        for a in sa:
            if a["trigger"] == trigger:
                a["strength"] = min(1.0, a["strength"] + 0.1)
                self._save()
                return
        sa.append({"trigger": trigger, "outcome": outcome, "strength": 0.3})
        if len(sa) > 15: sa.pop(0)
        self._save()

    def check_trigger(self, context_text):
        """
        Does current context trigger any fear or safe associations?
        Returns: (fear_boost, safe_boost)
        """
        fear_boost = 0.0
        safe_boost = 0.0
        ctx = context_text.lower()

        for fa in self.state["fear_associations"]:
            if fa["trigger"].lower() in ctx:
                fear_boost += fa["strength"] * 10
        for sa in self.state["safe_associations"]:
            if sa["trigger"].lower() in ctx:
                safe_boost += sa["strength"] * 8

        return fear_boost, safe_boost

    def summary(self):
        s  = self.state
        cm = s["caretaker_model"]
        return {
            "total_surprises":    s["total_surprises"],
            "total_delights":     s["total_delights"],
            "caretaker_absent":   cm["absent_ticks"],
            "caretaker_trust":    cm["reliability_score"],
            "fear_associations":  len(s["fear_associations"]),
            "safe_associations":  len(s["safe_associations"]),
        }
