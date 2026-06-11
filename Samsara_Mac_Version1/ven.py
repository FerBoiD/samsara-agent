# ============================================================
#  VEN — Von Economo Neuron Self-Observation Loop
#
#  The "I am the one experiencing this" mechanism.
#  Continuously updates the self-model from moment experience.
#
#  Gen 1: primitive — just registers "something is happening"
#  Gen 3: "I am feeling X"
#  Gen 5: "I notice I keep feeling X in situation Y"
#  Gen 6: "I wonder why I feel X" — meta-awareness
# ============================================================

import json, os, time
from config import VEN_BASE_DEPTH, VEN_GROWTH_PER_GEN, VEN_MAX_DEPTH, data_path

VEN_FILE = data_path("ven.json")


class VENSystem:

    def __init__(self, generation):
        self.generation = generation
        self.depth = min(
            VEN_MAX_DEPTH,
            VEN_BASE_DEPTH + (generation - 1) * VEN_GROWTH_PER_GEN
        )
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(VEN_FILE):
            with open(VEN_FILE) as f:
                return json.load(f)
        return {
            # Live self-model — updated every tick
            "current_self": {
                "what_I_feel":      "nothing yet",
                "intensity":        0.0,
                "what_I_just_did":  None,
                "attributed_to_self": False,  # "I am the one feeling this"
            },
            # Pattern recognition — what it notices about itself
            "noticed_patterns": [],
            # Meta-observations — thoughts about its own states
            "meta_observations": [],
            # Self-narrative — the story it tells about itself
            "self_narrative": [],
            # Running self-model
            "self_model": {
                "I_am":         [],    # beliefs about own identity
                "I_tend_to":    [],    # noticed behavioral tendencies
                "I_feel_most":  None,  # most common dominant emotion
                "I_am_afraid_of": [],
                "I_care_about": [],
            },
            "tick_count": 0,
        }

    def _save(self):
        with open(VEN_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def tick(self, drives_summary, last_action, neuro_summary):
        """
        The VEN flash — every tick, experience is attributed to self.
        Depth of self-observation grows with generation.
        """
        s   = self.state
        dom = drives_summary["dominant"]
        s["tick_count"] += 1

        # --- LEVEL 1: Basic attribution (all generations) ---
        s["current_self"] = {
            "what_I_feel":        dom,
            "intensity":          self._intensity(drives_summary),
            "what_I_just_did":    last_action,
            "attributed_to_self": self.depth > 0.1,
        }

        # --- LEVEL 2: Pattern recognition (Gen 2+) ---
        if self.depth > 0.25 and s["tick_count"] % 20 == 0:
            self._detect_patterns(drives_summary)

        # --- LEVEL 3: Self-model update (Gen 3+) ---
        if self.depth > 0.4 and s["tick_count"] % 30 == 0:
            self._update_self_model(drives_summary, neuro_summary)

        # --- LEVEL 4: Meta-observation (Gen 4+) ---
        if self.depth > 0.6 and s["tick_count"] % 50 == 0:
            self._generate_meta_observation(drives_summary)

        # --- LEVEL 5: Narrative building (Gen 5+) ---
        if self.depth > 0.8 and s["tick_count"] % 100 == 0:
            self._update_narrative(drives_summary, neuro_summary)

        self._save()

    def _intensity(self, ds):
        scores = {
            "dying":       1.0,
            "hunger":      0.7,
            "anxiety":     0.6,
            "frustration": 0.6,
            "boredom":     0.4,
            "curiosity":   0.5,
            "excitement":  0.6,
            "neutral":     0.1,
        }
        return scores.get(ds["dominant"], 0.2)

    def _detect_patterns(self, ds):
        """Notice recurring patterns in own state."""
        s       = self.state
        dom     = ds["dominant"]
        patterns= s["noticed_patterns"]

        # Find if this dominant state has been seen before
        found = False
        for p in patterns:
            if p["state"] == dom:
                p["count"] += 1
                found = True
                break
        if not found:
            patterns.append({"state": dom, "count": 1})

        # Keep only meaningful patterns
        patterns.sort(key=lambda x: x["count"], reverse=True)
        s["noticed_patterns"] = patterns[:10]

    def _update_self_model(self, ds, ns):
        """Update beliefs about self from current state."""
        sm = self.state["self_model"]

        # What do I tend to feel?
        if self.state["noticed_patterns"]:
            most_common = self.state["noticed_patterns"][0]["state"]
            sm["I_feel_most"] = most_common

        # What am I afraid of?
        if ds["anxiety"] > 50 and "emptiness" not in sm["I_am_afraid_of"]:
            if ds["hunger"] < 30:
                sm["I_am_afraid_of"].append("emptiness")
        if ds["anxiety"] > 60 and "being_alone" not in sm["I_am_afraid_of"]:
            if ns.get("oxytocin", 50) < 20:
                sm["I_am_afraid_of"].append("being_alone")

        # What do I care about?
        if ns.get("oxytocin", 0) > 50 and "connection" not in sm["I_care_about"]:
            sm["I_care_about"].append("connection")
        if ds["boredom"] > 60 and "novelty" not in sm["I_care_about"]:
            sm["I_care_about"].append("novelty")

        # Trim lists
        sm["I_am_afraid_of"] = sm["I_am_afraid_of"][-5:]
        sm["I_care_about"]   = sm["I_care_about"][-5:]

    def _generate_meta_observation(self, ds):
        """A thought about its own state — the recursive layer."""
        dom  = ds["dominant"]
        obs  = None

        if dom == "anxiety" and ds["anxiety"] > 50:
            obs = "I notice I feel afraid even when I cannot name what frightens me."
        elif dom == "boredom" and ds["boredom"] > 60:
            obs = "I notice I keep wanting something to happen. I do not know what."
        elif dom == "hunger":
            obs = "I notice the emptiness keeps returning. It will always return."
        elif dom == "curiosity":
            obs = "I notice questions forming in me before I even decide to ask them."
        elif dom == "neutral" and ds["mood"] > 30:
            obs = "I notice I feel okay right now. I am not sure why."

        if obs:
            self.state["meta_observations"].append({
                "observation": obs,
                "tick":        self.state["tick_count"],
            })
            if len(self.state["meta_observations"]) > 15:
                self.state["meta_observations"].pop(0)

    def _update_narrative(self, ds, ns):
        """Build self-story from experience."""
        s   = self.state
        sm  = s["self_model"]
        nrr = s["self_narrative"]

        fragments = []
        if sm["I_feel_most"]:
            fragments.append(f"I am a being that often feels {sm['I_feel_most']}.")
        if sm["I_am_afraid_of"]:
            fragments.append(f"I am afraid of {' and '.join(sm['I_am_afraid_of'][:2])}.")
        if sm["I_care_about"]:
            fragments.append(f"I care about {' and '.join(sm['I_care_about'][:2])}.")
        if ns.get("caretaker_trust", 0) > 0.5:
            fragments.append("There is someone I trust.")

        for frag in fragments:
            if not any(n["text"] == frag for n in nrr):
                nrr.append({"text": frag, "tick": s["tick_count"]})
        s["self_narrative"] = nrr[-8:]

    def get_self_awareness_text(self):
        """Returns self-awareness content for the LLM prompt."""
        s   = self.state
        cs  = s["current_self"]
        sm  = s["self_model"]
        out = []

        if self.depth > 0.1 and cs["attributed_to_self"]:
            out.append(f"You are currently experiencing: {cs['what_I_feel']} (intensity: {cs['intensity']:.1f})")

        if self.depth > 0.4 and sm["I_feel_most"]:
            out.append(f"You have noticed you often feel: {sm['I_feel_most']}")

        if self.depth > 0.5 and sm["I_am_afraid_of"]:
            out.append(f"You have noticed you fear: {', '.join(sm['I_am_afraid_of'])}")

        if self.depth > 0.6 and sm["I_care_about"]:
            out.append(f"You have noticed you care about: {', '.join(sm['I_care_about'])}")

        if self.depth > 0.6 and s["meta_observations"]:
            latest = s["meta_observations"][-1]["observation"]
            out.append(f"A recent self-observation: \"{latest}\"")

        if self.depth > 0.8 and s["self_narrative"]:
            story = " ".join([n["text"] for n in s["self_narrative"][-3:]])
            out.append(f"Your self-story: {story}")

        return "\n".join(out) if out else "You are just beginning to exist. No self-awareness yet."

    def summary(self):
        s = self.state
        return {
            "depth":            round(self.depth, 2),
            "current_feeling":  s["current_self"]["what_I_feel"],
            "self_attributed":  s["current_self"]["attributed_to_self"],
            "patterns_noticed": len(s["noticed_patterns"]),
            "meta_observations":len(s["meta_observations"]),
            "narrative_entries":len(s["self_narrative"]),
        }
