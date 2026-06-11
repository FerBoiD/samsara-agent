# ============================================================
#  MEMORY SYSTEM
#  Short term, long term, emotional events, learned facts,
#  associative links (trigger → outcome)
# ============================================================

import json, os, time
from config import SHORT_TERM_MAX, LONG_TERM_MAX, EMOTIONAL_MAX, data_path


MEMORY_FILE = data_path("memory.json")


class Memory:

    def __init__(self):
        self.data = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE) as f:
                return json.load(f)
        return {
            "short_term":    [],   # raw recent interactions
            "long_term":     [],   # compressed older memories
            "learned_facts": {},   # key→value things taught by human
            "emotional_events": [], # high-intensity moments
        }

    def _save(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    # ----------------------------------------------------------
    #  ADD
    # ----------------------------------------------------------
    def add(self, speaker, text, drive_snapshot, emotional_intensity=0.0):
        """
        speaker: "ai" | "human"
        drive_snapshot: summary dict from drives.summary()
        emotional_intensity: 0.0–1.0, triggers emotional memory storage
        """
        entry = {
            "t":       time.time(),
            "speaker": speaker,
            "text":    text,
            "mood":    drive_snapshot.get("mood", 0),
            "dominant":drive_snapshot.get("dominant", "neutral"),
        }
        self.data["short_term"].append(entry)

        # Overflow to long term
        if len(self.data["short_term"]) > SHORT_TERM_MAX:
            old = self.data["short_term"].pop(0)
            self._compress_to_long_term(old)

        # Store emotional memory if intense enough
        if emotional_intensity > 0.5:
            self.data["emotional_events"].append({
                "t":          time.time(),
                "text":       text[:120],
                "dominant":   drive_snapshot.get("dominant", "neutral"),
                "mood":       drive_snapshot.get("mood", 0),
                "intensity":  emotional_intensity,
            })
            if len(self.data["emotional_events"]) > EMOTIONAL_MAX:
                self.data["emotional_events"].pop(0)

        self._save()

    def learn_fact(self, key, value):
        self.data["learned_facts"][key] = {
            "value":  value,
            "time":   time.time(),
        }
        self._save()

    def _compress_to_long_term(self, entry):
        compressed = {
            "t":       entry["t"],
            "speaker": entry["speaker"],
            "summary": entry["text"][:80],
            "mood":    entry.get("mood", 0),
        }
        self.data["long_term"].append(compressed)
        if len(self.data["long_term"]) > LONG_TERM_MAX:
            self.data["long_term"].pop(0)

    # ----------------------------------------------------------
    #  RETRIEVE
    # ----------------------------------------------------------
    def recent_for_llm(self, n=12):
        """Returns last n turns formatted as LLM messages list."""
        recent = self.data["short_term"][-n:]
        messages = []
        for e in recent:
            role = "assistant" if e["speaker"] == "ai" else "user"
            messages.append({"role": role, "content": e["text"]})
        return messages

    def facts_as_text(self):
        if not self.data["learned_facts"]:
            return "Nothing taught yet."
        lines = [f"- {k}: {v['value']}" for k, v in self.data["learned_facts"].items()]
        return "\n".join(lines)

    def emotional_history_as_text(self):
        recent = self.data["emotional_events"][-6:]
        if not recent:
            return "No strong emotional memories yet."
        lines = [f"- [{e['dominant']}] {e['text']}" for e in recent]
        return "\n".join(lines)

    def long_term_summary(self):
        """Brief summary of long term memory for context."""
        if not self.data["long_term"]:
            return "No long term memories yet."
        # Just show last 5
        recent = self.data["long_term"][-5:]
        lines = [f"- {e['speaker']}: {e['summary']}" for e in recent]
        return "\n".join(lines)
