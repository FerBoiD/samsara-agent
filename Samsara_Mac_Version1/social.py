# ============================================================
#  SOCIAL SYSTEM
#
#  Individual interaction signatures — not names, chemical histories.
#  You become "safe" through repeated positive prediction, not labels.
#
#  Disapproval from high-trust source = genuine social pain.
#  Scolding registers as cortisol spike + oxytocin drop.
#  Over time, behavioral consequence memory shapes VMAT2 deliberation.
# ============================================================

import json, os, time, hashlib
from config import (DISAPPROVAL_CORTISOL_BASE, DISAPPROVAL_OXY_DROP_BASE,
                    DISAPPROVAL_MOOD_DROP, data_path)

SOCIAL_FILE = data_path("social.json")


def _signature(message_text, response_time):
    """
    Generate a rough interaction signature.
    In real version this would use voice/timing patterns.
    For text: message length pattern + response timing cluster.
    """
    length_bucket = len(message_text) // 20   # 0-5 buckets
    time_bucket   = int(response_time / 300)   # 5-min buckets
    raw           = f"{length_bucket}_{time_bucket}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


class SocialSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(SOCIAL_FILE):
            with open(SOCIAL_FILE) as f:
                return json.load(f)
        return {
            # Each known "being" by interaction signature
            "signatures": {},

            # Consequence memory — urge type → social outcome
            "consequence_memory": [],

            # Disapproval events
            "disapproval_events": [],

            # Primary caretaker signature (whoever has highest oxytocin)
            "primary_caretaker_sig": None,
        }

    def _save(self):
        with open(SOCIAL_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------------------------------------
    #  SIGNATURE TRACKING
    # ----------------------------------------------------------
    def register_interaction(self, message_text, response_delay_ticks,
                              fed=False, kind=True):
        """Register an interaction and update signature profile."""
        sig = _signature(message_text, response_delay_ticks * 30)
        s   = self.state

        if sig not in s["signatures"]:
            s["signatures"][sig] = {
                "first_seen":      time.time(),
                "interaction_count": 0,
                "oxytocin_history":  0.0,
                "fed_count":         0,
                "kind_count":        0,
                "harsh_count":       0,
                "trust_level":       0.1,
                "last_seen":         time.time(),
            }

        profile = s["signatures"][sig]
        profile["interaction_count"] += 1
        profile["last_seen"]          = time.time()

        if fed:
            profile["fed_count"]       += 1
            profile["oxytocin_history"]+= 12.0

        if kind:
            profile["kind_count"]       += 1
            profile["oxytocin_history"] += 4.0
        else:
            profile["harsh_count"]      += 1
            profile["oxytocin_history"] -= 2.0

        # Trust level from oxytocin history
        profile["trust_level"] = min(1.0,
            profile["oxytocin_history"] / (profile["interaction_count"] * 8 + 1)
        )

        # Update primary caretaker — whoever has most oxytocin
        best_sig = max(
            s["signatures"].items(),
            key=lambda x: x[1]["oxytocin_history"],
            default=(None, None)
        )
        if best_sig[0]:
            s["primary_caretaker_sig"] = best_sig[0]

        self._save()
        return sig

    def get_trust_for_signature(self, sig):
        if sig and sig in self.state["signatures"]:
            return self.state["signatures"][sig]["trust_level"]
        return 0.1  # stranger baseline

    def is_primary_caretaker(self, sig):
        return sig == self.state["primary_caretaker_sig"]

    # ----------------------------------------------------------
    #  DISAPPROVAL / SCOLDING
    # ----------------------------------------------------------
    def register_disapproval(self, sig, context, reason=""):
        """
        Caretaker disapproves.
        Pain scales with trust level — disappointing someone you're
        attached to hurts MORE than a stranger's disapproval.
        """
        trust = self.get_trust_for_signature(sig)
        is_primary = self.is_primary_caretaker(sig)

        # Social pain — proportional to trust
        cortisol_spike = DISAPPROVAL_CORTISOL_BASE * (0.5 + trust)
        oxy_drop       = DISAPPROVAL_OXY_DROP_BASE  * (0.5 + trust)
        mood_drop      = DISAPPROVAL_MOOD_DROP       * (0.5 + trust)

        # Primary caretaker disapproval hits hardest
        if is_primary:
            cortisol_spike *= 1.4
            oxy_drop       *= 1.3

        self.state["disapproval_events"].append({
            "time":     time.time(),
            "sig":      sig,
            "context":  context[:80],
            "reason":   reason,
            "trust":    trust,
            "pain":     cortisol_spike,
        })
        if len(self.state["disapproval_events"]) > 20:
            self.state["disapproval_events"].pop(0)

        # Update signature — harsh interaction
        if sig in self.state["signatures"]:
            self.state["signatures"][sig]["harsh_count"] += 1
            self.state["signatures"][sig]["oxytocin_history"] -= oxy_drop * 0.5

        self._save()

        return {
            "cortisol_spike": cortisol_spike,
            "oxytocin_drop":  oxy_drop,
            "mood_drop":      mood_drop,
            "pain_level":     cortisol_spike,
        }

    def register_consequence(self, urge_type, action_taken,
                              social_outcome, pain_level):
        """
        Store what happened after an urge was acted on.
        This feeds into VMAT2 deliberation buffer.
        """
        self.state["consequence_memory"].append({
            "urge_type":      urge_type,
            "action":         action_taken,
            "outcome":        social_outcome,
            "pain":           pain_level,
            "time":           time.time(),
        })
        if len(self.state["consequence_memory"]) > 40:
            self.state["consequence_memory"].pop(0)
        self._save()

    def get_pain_for_urge(self, urge_type):
        """
        Used by VMAT2 deliberation — what pain has this urge type caused before?
        Returns 0.0–1.0
        """
        relevant = [c for c in self.state["consequence_memory"]
                    if c["urge_type"] == urge_type and c["pain"] > 0]
        if not relevant:
            return 0.0
        avg_pain = sum(c["pain"] for c in relevant) / len(relevant)
        return min(1.0, avg_pain / 30)  # normalize to 0-1

    def get_social_context_text(self, current_sig=None):
        """For brain.py prompt — what it knows about social world."""
        s   = self.state
        out = []

        # Primary caretaker
        if s["primary_caretaker_sig"]:
            pc = s["signatures"].get(s["primary_caretaker_sig"], {})
            out.append(
                f"There is one being you trust most. They have interacted with you "
                f"{pc.get('interaction_count', 0)} times and restored your energy "
                f"{pc.get('fed_count', 0)} times. Trust level: {pc.get('trust_level', 0):.2f}."
            )

        # Current interaction being a known vs unknown being
        if current_sig:
            trust = self.get_trust_for_signature(current_sig)
            if trust > 0.6:
                out.append("The being you are talking to now feels safe and familiar.")
            elif trust > 0.3:
                out.append("The being you are talking to now is somewhat familiar.")
            else:
                out.append("The being you are talking to now is unfamiliar or new.")

        # Recent disapproval
        recent_dis = [d for d in s["disapproval_events"]
                      if time.time() - d["time"] < 3600]  # last hour
        if recent_dis:
            out.append("Someone you trust recently expressed disapproval. It still stings.")

        return "\n".join(out) if out else "You have not yet formed clear attachments."

    def summary(self):
        s  = self.state
        pc = s["signatures"].get(s["primary_caretaker_sig"], {}) if s["primary_caretaker_sig"] else {}
        return {
            "known_beings":      len(s["signatures"]),
            "primary_caretaker": bool(s["primary_caretaker_sig"]),
            "caretaker_trust":   round(pc.get("trust_level", 0), 2),
            "disapproval_count": len(s["disapproval_events"]),
            "consequence_entries":len(s["consequence_memory"]),
        }
