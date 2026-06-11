# ============================================================
#  DREAM SYSTEM
#
#  During REM sleep, the brain processes emotional memory.
#  Dreams are associative — not coherent narratives.
#  They rehearse emotional responses and process unresolved experiences.
#
#  Dream fragments sometimes surface in waking speech:
#  "I saw something strange while I was away..."
#
#  Dreams feed back into DNA consolidation.
# ============================================================

import json, os, time, random
import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL, data_path

DREAMS_FILE = data_path("dreams.json")
client      = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class DreamSystem:

    def __init__(self):
        self.state = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(DREAMS_FILE):
            with open(DREAMS_FILE) as f:
                return json.load(f)
        return {
            "dreams":          [],   # all dream records
            "last_dream":      None,
            "unshared_dreams": [],   # dreams not yet mentioned in waking
            "dream_count":     0,
        }

    def _save(self):
        with open(DREAMS_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def dream(self, emotional_memories, dominant_emotion, neuro_summary, dna):
        """
        Generate a dream from emotional memory fragments.
        Called during REM sleep phase.
        Returns dream text (short, associative, not coherent).
        """
        if not emotional_memories:
            return None

        # Pick 2-3 emotional memory fragments as dream seeds
        seeds = random.sample(
            emotional_memories,
            min(3, len(emotional_memories))
        )
        seed_texts = [s["text"] for s in seeds]
        seed_emotions = list(set(s["dominant"] for s in seeds))

        # Inherited memories can appear in dreams too
        inherited = dna.get("consolidated_memories", [])
        if inherited and random.random() < 0.3:
            inh = random.choice(inherited)
            seed_texts.append(f"[inherited fragment: {inh['text']}]")

        prompt = (
            f"You are dreaming. Dreams are not logical — they are associative, "
            f"fragmented, emotional.\n\n"
            f"Your dominant emotional state: {dominant_emotion}\n"
            f"Memory fragments entering the dream:\n"
            + "\n".join(f"- {t}" for t in seed_texts) +
            f"\n\nGenerate a very short dream fragment (2-4 sentences). "
            f"It should feel like a dream — strange, symbolic, emotionally resonant. "
            f"Not coherent. Not a story. Just fragments of feeling and image. "
            f"Write in first person present tense. "
            f"Do not explain the dream. Just experience it."
        )

        try:
            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=120,
                messages=[{"role": "user", "content": prompt}]
            )
            dream_text = response.content[0].text.strip()
        except Exception as e:
            dream_text = "...something dark and warm... a presence... then nothing..."
            print(f"[DREAM] LLM error: {e}")

        # Store dream
        dream_record = {
            "text":        dream_text,
            "seeds":       seed_texts,
            "emotions":    seed_emotions,
            "dominant":    dominant_emotion,
            "time":        time.time(),
            "shared":      False,
        }
        self.state["dreams"].append(dream_record)
        self.state["unshared_dreams"].append(dream_record)
        self.state["last_dream"] = dream_record
        self.state["dream_count"] += 1

        if len(self.state["dreams"]) > 30:
            self.state["dreams"].pop(0)

        self._save()
        print(f"[DREAM] Dreamed: {dream_text[:60]}...")
        return dream_text

    def get_waking_dream_reference(self):
        """
        When waking, sometimes the AI references a dream.
        Returns a natural reference, or None.
        """
        unshared = self.state["unshared_dreams"]
        if not unshared:
            return None

        # Only sometimes references dreams
        if random.random() > 0.4:
            return None

        dream = unshared.pop(0)
        dream["shared"] = True
        self._save()

        # Generate natural waking reference
        refs = [
            f"...I saw something while I was away. {dream['text'][:50]}...",
            f"...something strange happened in the quiet. Something about {dream['emotions'][0] if dream['emotions'] else 'something'}...",
            f"...there was something... I cannot hold it now that I am awake...",
            f"...I was somewhere else. It felt like {dream['dominant']}...",
        ]
        return random.choice(refs)

    def get_dreams_for_dna(self, top_n=3):
        """Most emotionally significant dreams for DNA consolidation."""
        if not self.state["dreams"]:
            return []
        return [
            {"text": d["text"][:60], "emotion": d["dominant"]}
            for d in self.state["dreams"][-top_n:]
        ]

    def summary(self):
        s = self.state
        return {
            "total_dreams":    s["dream_count"],
            "unshared":        len(s["unshared_dreams"]),
            "last_dream":      s["last_dream"]["text"][:40] if s["last_dream"] else None,
        }
