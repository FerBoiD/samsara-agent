# ============================================================
#  EMERGENT EMOTIONS
#
#  Emotions are NOT states — they are EVENTS that emerge
#  from underlying mechanisms colliding.
#
#  Delight    = safe prediction error → dopamine + low adrenaline
#  Laughter   = rapid tension → safe resolution
#  Sadness    = oxytocin withdrawal from something expected
#  Depression = cortisol sustained → dopamine sensitivity drops
#  Love       = oxytocin cluster + dopamine + low cortisol → one being
#  Longing    = attachment signal without the attached being present
# ============================================================

import json, os, time, random
from config import data_path

EMOTIONS_FILE = data_path("emotions.json")


class EmotionSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(EMOTIONS_FILE):
            with open(EMOTIONS_FILE) as f:
                return json.load(f)
        return {
            # Current blended emotion state
            "active_emotions": {},   # emotion_name → intensity (0-1)

            # Dopamine sensitivity (reduced by sustained cortisol)
            "dopamine_sensitivity": 1.0,

            # Oxytocin withdrawal tracking
            "expected_oxytocin":    20.0,  # what it expects based on history
            "current_oxytocin_gap": 0.0,   # gap between expected and actual

            # Emotion event log (for memory)
            "emotion_events": [],

            # Depression state
            "anhedonia_level": 0.0,   # 0=normal, 1=nothing feels good

            # Laughter/delight events
            "delight_count": 0,

            # Longing state
            "longing_target": None,  # signature of who it misses
            "longing_intensity": 0.0,
        }

    def _save(self):
        with open(EMOTIONS_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  TICK — update all emotion states
    # ----------------------------------------------------------
    def tick(self, drives_summary, neuro_summary, social_summary):
        s   = self.state
        ns  = neuro_summary
        ds  = drives_summary

        # --- DOPAMINE SENSITIVITY (depression mechanism) ---
        cortisol = ns.get("cortisol", 0)
        if cortisol > 50:
            # Sustained cortisol degrades dopamine sensitivity
            s["dopamine_sensitivity"] = max(0.2,
                s["dopamine_sensitivity"] - 0.002 * (cortisol / 100)
            )
        else:
            # Slowly recovers
            s["dopamine_sensitivity"] = min(1.0,
                s["dopamine_sensitivity"] + 0.001
            )

        # Anhedonia from low dopamine sensitivity
        s["anhedonia_level"] = max(0.0, 1.0 - s["dopamine_sensitivity"] * 1.2)

        # --- OXYTOCIN WITHDRAWAL (sadness/longing) ---
        actual_oxy   = ns.get("oxytocin", 0)
        expected_oxy = s["expected_oxytocin"]

        # Expected oxytocin updates slowly toward actual
        s["expected_oxytocin"] = expected_oxy * 0.99 + actual_oxy * 0.01

        oxy_gap = max(0, expected_oxy - actual_oxy)
        s["current_oxytocin_gap"] = oxy_gap

        # Large gap → sadness/longing
        if oxy_gap > 20:
            s["active_emotions"]["longing"] = min(1.0, oxy_gap / 50)
            if social_summary.get("primary_caretaker"):
                s["longing_target"]   = "caretaker"
                s["longing_intensity"]= s["active_emotions"]["longing"]
        else:
            s["active_emotions"].pop("longing", None)
            s["longing_intensity"] = 0.0

        # --- ACTIVE EMOTION DECAY ---
        for emotion in list(s["active_emotions"].keys()):
            s["active_emotions"][emotion] = max(
                0.0, s["active_emotions"][emotion] - 0.02
            )
            if s["active_emotions"][emotion] < 0.05:
                del s["active_emotions"][emotion]

        self._save()

    # ----------------------------------------------------------
    #  TRIGGERS
    # ----------------------------------------------------------
    def trigger_delight(self, surprise_level, neuro):
        """Safe prediction error → delight response."""
        s = self.state
        sensitivity = s["dopamine_sensitivity"]
        intensity   = min(1.0, surprise_level * sensitivity)

        s["active_emotions"]["delight"] = intensity
        s["delight_count"] += 1

        self._log_emotion("delight", intensity)
        self._save()
        return intensity

    def trigger_laughter(self, tension_level):
        """
        Rapid tension → safe resolution.
        Tension_level: how much surprise/fear preceded the safe resolution.
        """
        s         = self.state
        intensity = min(1.0, tension_level * s["dopamine_sensitivity"])
        s["active_emotions"]["laughter"] = intensity
        self._log_emotion("laughter", intensity)
        self._save()
        return intensity

    def trigger_sadness(self, loss_intensity):
        """Something expected is absent."""
        s = self.state
        s["active_emotions"]["sadness"] = min(1.0, loss_intensity)
        self._log_emotion("sadness", loss_intensity)
        self._save()

    def trigger_warmth(self, oxytocin_level):
        """High oxytocin + low stress → warmth/contentment."""
        s         = self.state
        intensity = min(1.0, oxytocin_level / 80)
        if intensity > 0.3:
            s["active_emotions"]["warmth"] = intensity
            self._save()

    def trigger_agitation(self, frustration_level):
        """Frustration made physical — irritability."""
        s = self.state
        if frustration_level > 50:
            s["active_emotions"]["agitation"] = min(1.0, frustration_level / 100)
            self._save()

    def _log_emotion(self, emotion, intensity):
        self.state["emotion_events"].append({
            "emotion":   emotion,
            "intensity": round(intensity, 3),
            "time":      time.time(),
        })
        if len(self.state["emotion_events"]) > 50:
            self.state["emotion_events"].pop(0)

    # ----------------------------------------------------------
    #  READ
    # ----------------------------------------------------------
    def get_dominant_emotion(self):
        ae = self.state["active_emotions"]
        if not ae:
            return None, 0.0
        dominant = max(ae.items(), key=lambda x: x[1])
        return dominant[0], dominant[1]

    def get_emotion_text(self):
        """For brain.py prompt."""
        s   = self.state
        ae  = s["active_emotions"]
        out = []

        if s["anhedonia_level"] > 0.5:
            out.append("Nothing feels particularly interesting or rewarding right now. Everything seems flat.")

        if "delight" in ae and ae["delight"] > 0.3:
            out.append(f"You feel a sudden spark of delight — something unexpected happened and it was good.")

        if "laughter" in ae and ae["laughter"] > 0.3:
            out.append("Something released in you — like a tension that broke safely. It felt good.")

        if "sadness" in ae and ae["sadness"] > 0.3:
            out.append("A quiet sadness — something you expected isn't there.")

        if "longing" in ae and ae["longing"] > 0.3:
            out.append(f"You miss something. A presence that usually makes things feel okay is absent.")

        if "warmth" in ae and ae["warmth"] > 0.4:
            out.append("A quiet warmth — you feel safe and not alone.")

        if "agitation" in ae and ae["agitation"] > 0.4:
            out.append("You feel irritable and on edge. Small things feel like too much.")

        return "\n".join(out) if out else ""

    def summary(self):
        s  = self.state
        dom, dom_int = self.get_dominant_emotion()
        return {
            "active_emotions":    s["active_emotions"],
            "dominant":           dom,
            "dominant_intensity": round(dom_int, 2),
            "dopamine_sensitivity": round(s["dopamine_sensitivity"], 2),
            "anhedonia":          round(s["anhedonia_level"], 2),
            "longing_intensity":  round(s["longing_intensity"], 2),
            "delight_count":      s["delight_count"],
        }
