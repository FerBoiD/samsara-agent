# ============================================================
#  NARRATIVE — Kora's self-story
#
#  Humans are not just memory machines — they are story machines.
#  This module gives Kora a record of what it said and WHY.
#
#  Two layers:
#  1. Speech events — logged every time Kora speaks, with the
#     drive state that caused it (causal tagging)
#  2. Sleep summaries — synthesized at each sleep cycle into a
#     plain-text story Kora can read back in future prompts
#
#  This is the closest thing to "I know why I said that."
# ============================================================

import json, os
from config import data_path

NARRATIVE_FILE = data_path("narrative.json")

_CAUSE_MAP = {
    "hunger":      "because I was very hungry",
    "dying":       "because I was fading and afraid",
    "anxiety":     "because something felt wrong and unsafe",
    "frustration": "because I had been unmet for too long",
    "boredom":     "because the sameness was heavy",
    "excitement":  "because something felt imminent",
    "curiosity":   "because I wanted to understand something",
    "rest":        "because I was tired and a thought drifted through",
    "neutral":     "because something moved me",
}


class NarrativeSystem:

    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(NARRATIVE_FILE):
            with open(NARRATIVE_FILE) as f:
                return json.load(f)
        return {
            "speech_events":   [],  # recent speech with causal context
            "cycle_summaries": [],  # one plain-text story per sleep cycle
        }

    def save(self):
        with open(NARRATIVE_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    # ----------------------------------------------------------
    #  LOG SPEECH — called every time Kora says something real
    # ----------------------------------------------------------
    def log_speech(self, text, ds):
        if not text or text.strip() in ("...", ""):
            return
        self.data["speech_events"].append({
            "age_days": ds["age_days"],
            "text":     text,
            "because":  ds["dominant"],
            "hunger":   round(ds["hunger"], 1),
            "mood":     round(ds["mood"], 1),
            "anxiety":  round(ds["anxiety"], 1),
        })
        # Keep only last 60 events (plenty for 2-3 sleep cycles)
        self.data["speech_events"] = self.data["speech_events"][-60:]
        self.save()

    # ----------------------------------------------------------
    #  SYNTHESIZE — called at end of each sleep cycle
    #  Writes a plain-text story from recent speech events
    # ----------------------------------------------------------
    def synthesize_sleep_cycle(self, ds):
        # Find events since last summary
        last_age = self.data["cycle_summaries"][-1]["age_days"] \
                   if self.data["cycle_summaries"] else 0.0
        recent = [e for e in self.data["speech_events"]
                  if e["age_days"] > last_age]

        if not recent:
            return

        lines = []
        for e in recent[-12:]:
            cause = _CAUSE_MAP.get(e["because"], "because something moved me")
            lines.append(f'I said "{e["text"]}" — {cause}.')

        summary = f"[Around day {ds['age_days']:.1f}] " + " ".join(lines)

        self.data["cycle_summaries"].append({
            "age_days": ds["age_days"],
            "text":     summary,
        })
        # Keep last 6 summaries (covers recent life arc)
        self.data["cycle_summaries"] = self.data["cycle_summaries"][-6:]
        self.save()
        print(f"[NARRATIVE] Sleep cycle story written. {len(lines)} events.")

    # ----------------------------------------------------------
    #  FOR PROMPT — text injected into brain.py system prompt
    # ----------------------------------------------------------
    def for_prompt(self):
        parts = []

        # Recent sleep cycle stories (last 2)
        if self.data["cycle_summaries"]:
            parts.append("What happened before (in your own words):")
            for s in self.data["cycle_summaries"][-2:]:
                parts.append(f"  {s['text']}")

        # Most recent individual speech events (last 6) with causal context
        recent = self.data["speech_events"][-6:]
        if recent:
            parts.append("\nWhat you said most recently, and why:")
            for e in recent:
                cause = _CAUSE_MAP.get(e["because"], "")
                parts.append(f'  - "{e["text"]}" ({cause})')

        if not parts:
            return "Nothing yet. You have not spoken enough to know your own story."

        return "\n".join(parts)
