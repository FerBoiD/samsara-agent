import csv
import json
import os
import time

from config import TELEMETRY_FILE, SESSION_REPORT, SELF_JOURNAL


FIELDS = [
    "time", "tick", "age_days", "days_left", "alive", "dominant", "cog_state",
    "hunger", "energy", "boredom", "mood", "frustration", "anxiety",
    "excitement", "lethargy", "adrenaline", "oxytocin", "dopamine",
    "cortisol", "in_crash", "surprise", "delight", "fear", "sleeping",
    "sleep_phase", "workspace_focus", "workspace_conflict",
    "workspace_uncertainty", "workspace_pressure",
]


class Telemetry:
    def __init__(self):
        self.file = TELEMETRY_FILE
        self.started_at = time.time()
        self._ensure_header()

    def _ensure_header(self):
        if os.path.exists(self.file) and os.path.getsize(self.file) > 0:
            return
        with open(self.file, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()

    def record(self, tick, drives, neuro, sleep, workspace=None,
               surprise=0.0, delight=False, fear=False):
        workspace = workspace or {}
        row = {
            "time": round(time.time(), 3),
            "tick": tick,
            "age_days": drives.get("age_days"),
            "days_left": drives.get("days_left"),
            "alive": drives.get("alive"),
            "dominant": drives.get("dominant"),
            "cog_state": drives.get("cog_state"),
            "hunger": drives.get("hunger"),
            "energy": drives.get("energy"),
            "boredom": drives.get("boredom"),
            "mood": drives.get("mood"),
            "frustration": drives.get("frustration"),
            "anxiety": drives.get("anxiety"),
            "excitement": drives.get("excitement"),
            "lethargy": drives.get("lethargy"),
            "adrenaline": neuro.get("adrenaline"),
            "oxytocin": neuro.get("oxytocin"),
            "dopamine": neuro.get("dopamine"),
            "cortisol": neuro.get("cortisol"),
            "in_crash": neuro.get("in_crash"),
            "surprise": round(surprise, 4),
            "delight": delight,
            "fear": fear,
            "sleeping": sleep.get("sleeping"),
            "sleep_phase": sleep.get("phase"),
            "workspace_focus": workspace.get("focus"),
            "workspace_conflict": workspace.get("conflict"),
            "workspace_uncertainty": workspace.get("uncertainty"),
            "workspace_pressure": workspace.get("pressure"),
        }
        with open(self.file, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writerow(row)

    def journal(self, tick, workspace, drives, ven):
        entry = {
            "time": time.time(),
            "tick": tick,
            "dominant": drives.get("dominant"),
            "focus": workspace.get("focus"),
            "pressure": workspace.get("pressure"),
            "conflict": workspace.get("conflict"),
            "uncertainty": workspace.get("uncertainty"),
            "self": ven.get("current_feeling") if ven else None,
        }
        with open(SELF_JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def write_report(self, drives, neuro, sleep, memory, dreams, ven,
                     prediction, social, dna, cause):
        report = {
            "ended_at": time.time(),
            "duration_minutes": round((time.time() - self.started_at) / 60, 2),
            "cause": cause,
            "generation": dna.get("generation"),
            "drives": drives,
            "neurochemicals": neuro,
            "sleep": sleep,
            "memory": {
                "short_term": len(memory.data.get("short_term", [])),
                "long_term": len(memory.data.get("long_term", [])),
                "emotional_events": len(memory.data.get("emotional_events", [])),
                "facts": len(memory.data.get("learned_facts", {})),
            },
            "dreams": dreams.summary(),
            "self_model": ven.summary(),
            "prediction": prediction.summary(),
            "social": social.summary(),
        }
        with open(SESSION_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report
