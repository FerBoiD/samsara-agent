import json
import math
import os
import time

from config import data_path


WORKSPACE_FILE = data_path("workspace.json")


class GlobalWorkspace:
    """
    A small local integration layer.

    It does not decide sentences or scripted behaviors. It exposes the current
    competition between bodily need, uncertainty, attachment, and rest pressure
    so the interpreter has an organism-state to translate.
    """

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(WORKSPACE_FILE):
            with open(WORKSPACE_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {
            "last": {},
            "history": [],
            "epistemic_need": 0.0,
            "conflict_memory": 0.0,
        }

    def _save(self):
        with open(WORKSPACE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def update(self, drives, neuro, memory, prediction, social, sleep):
        body_need = max(0.0, (100.0 - drives["hunger"]) / 100.0)
        fatigue = max(0.0, (100.0 - drives["energy"]) / 100.0)
        stress = (drives["anxiety"] + drives["frustration"] + neuro["cortisol"]) / 300.0
        attachment_gap = max(0.0, 0.6 - neuro.get("caretaker_trust", 0.0))

        recent_terms = set()
        for item in memory.data.get("short_term", [])[-8:]:
            for token in item.get("text", "").lower().split():
                if len(token) > 3:
                    recent_terms.add(token.strip(".,!?;:"))
        novelty_gap = max(0.0, 1.0 - min(1.0, len(recent_terms) / 28.0))
        boredom_pressure = drives["boredom"] / 100.0
        prediction_pressure = min(1.0, prediction.summary()["total_surprises"] / 20.0)

        epistemic = (
            0.45 * boredom_pressure +
            0.35 * novelty_gap +
            0.20 * prediction_pressure
        ) * drives["personality"].get("curiosity_rate", 1.0)
        epistemic = max(0.0, min(1.0, epistemic))
        self.state["epistemic_need"] = (
            self.state.get("epistemic_need", 0.0) * 0.85 + epistemic * 0.15
        )

        channels = {
            "body": body_need,
            "rest": fatigue,
            "uncertainty": self.state["epistemic_need"],
            "attachment": attachment_gap,
            "stress": stress,
        }
        ranked = sorted(channels.items(), key=lambda x: x[1], reverse=True)
        focus, pressure = ranked[0]
        conflict = max(0.0, ranked[0][1] - ranked[1][1])
        conflict = round(1.0 - conflict, 3)
        self.state["conflict_memory"] = (
            self.state.get("conflict_memory", 0.0) * 0.9 + conflict * 0.1
        )

        snapshot = {
            "time": time.time(),
            "focus": focus,
            "pressure": round(pressure, 3),
            "conflict": round(self.state["conflict_memory"], 3),
            "uncertainty": round(self.state["epistemic_need"], 3),
            "channels": {k: round(v, 3) for k, v in channels.items()},
            "sleeping": sleep.get("sleeping", False),
        }
        self.state["last"] = snapshot
        self.state["history"].append(snapshot)
        self.state["history"] = self.state["history"][-80:]
        self._save()
        return snapshot

    def text_for_brain(self):
        last = self.state.get("last") or {}
        if not last:
            return "No integrated inner workspace has formed yet."
        channels = last.get("channels", {})
        channel_text = ", ".join(
            f"{name}:{value:.2f}" for name, value in sorted(channels.items())
        )
        return (
            f"Current inner focus: {last.get('focus')} "
            f"(pressure {last.get('pressure')}, conflict {last.get('conflict')}, "
            f"uncertainty {last.get('uncertainty')}). "
            f"Competing channels: {channel_text}."
        )

    def summary(self):
        return self.state.get("last", {})
