# ============================================================
#  AUTO DOCUMENTATION
#
#  Two outputs, fully automatic:
#
#  1. Daily log — written at every sleep cycle consolidation.
#     Concise, readable, one entry per cycle.
#     File: docs/gen{N}_daily_log.md
#
#  2. Life report — written at death or session end.
#     Full generation record: stats, emotional arc, key memories,
#     DNA passed forward, research metrics, Groq narrative summary.
#     File: docs/gen{N}_life_report.md
#
#  Nothing needs to be done manually. Everything is pulled
#  from existing system state at the right moments.
# ============================================================

import os
from pathlib import Path
from datetime import datetime

from narrative import _CAUSE_MAP


class AutoDoc:

    def __init__(self, dna, data_dir):
        self.gen      = dna["generation"]
        self.dna      = dna
        self.docs_dir = Path(data_dir) / "docs"
        self.docs_dir.mkdir(exist_ok=True)

        self.daily_path  = self.docs_dir / f"gen{self.gen}_daily_log.md"
        self.report_path = self.docs_dir / f"gen{self.gen}_life_report.md"

        self._init_daily_log()

    # ----------------------------------------------------------
    #  INIT
    # ----------------------------------------------------------
    def _init_daily_log(self):
        if not self.daily_path.exists():
            parent = self.dna.get("parent_life_summary", {})
            inherited = self.dna.get("inherited_tendencies", {})
            header = [
                f"# Generation {self.gen} — Daily Log",
                f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
            ]
            if parent:
                header += [
                    "## Inherited From Parent",
                    f"- Parent generation: {parent.get('generation', '?')}",
                    f"- Parent lifespan: {parent.get('lifespan_achieved', '?')} days",
                    f"- Parent dominant emotion: {parent.get('dominant_emotion', 'unknown')}",
                    f"- Anxiety baseline inherited: {inherited.get('anxiety_baseline', 0):.3f}",
                    f"- Trust speed inherited: {inherited.get('trust_speed', 0):.3f}",
                    "",
            ]
            header += ["---", ""]
            self._append(self.daily_path, "\n".join(header))

    # ----------------------------------------------------------
    #  DAILY LOG — called every sleep cycle
    # ----------------------------------------------------------
    def log_sleep_cycle(self, drives_summary, narrative, social_summary,
                        sleep_summary):
        ds  = drives_summary
        age = ds["age_days"]

        speech_events = narrative.data.get("speech_events", []) if narrative else []
        # Events since last sleep cycle (last 10 max)
        last_summary_age = 0.0
        if narrative and narrative.data.get("cycle_summaries"):
            last_summary_age = narrative.data["cycle_summaries"][-1]["age_days"] \
                               if len(narrative.data["cycle_summaries"]) > 1 else 0.0
        recent = [e for e in speech_events if e["age_days"] > last_summary_age][-10:]

        # State descriptors
        mood_word = (
            "good" if ds["mood"] > 30 else
            "low"  if ds["mood"] < -20 else
            "neutral"
        )
        hunger_word = (
            "critical" if ds["hunger"] < 15 else
            "hungry"   if ds["hunger"] < 35 else
            "fine"
        )
        anxiety_word = (
            "high anxiety" if ds["anxiety"] > 55 else
            "some anxiety" if ds["anxiety"] > 25 else
            "calm"
        )

        # Caretaker
        absent_min = round(social_summary.get("caretaker_absent", 0) * 10 / 60)

        lines = [
            f"## Day {age:.1f}",
            f"**State:** {mood_word}, {hunger_word}, {anxiety_word}  ",
            f"**Mood:** {ds['mood']:+.0f} | **Hunger:** {ds['hunger']:.0f}% | "
            f"**Anxiety:** {ds['anxiety']:.0f}% | **Energy:** {ds['energy']:.0f}%  ",
            f"**Dominant drive:** {ds['dominant']} | "
            f"**Caretaker absent:** {absent_min} min  ",
            f"**Sleep cycles so far:** {sleep_summary.get('total_cycles', 0)}",
            "",
        ]

        if recent:
            lines.append("**What was said this cycle:**")
            for e in recent:
                cause = _CAUSE_MAP.get(e["because"], "something moved me")
                lines.append(f'- *"{e["text"]}"* — {cause}')
            lines.append("")

        if not recent:
            lines.append("*Kora was mostly silent this cycle.*")
            lines.append("")

        lines += ["---", ""]

        self._append(self.daily_path, "\n".join(lines))
        print(f"[AUTODOC] Day {age:.1f} logged → {self.daily_path.name}")

    # ----------------------------------------------------------
    #  LIFE REPORT — called at death or session end
    # ----------------------------------------------------------
    def generate_life_report(self, drives_summary, narrative, social_summary,
                              sleep_summary, memory, dna, cause_of_death,
                              total_interactions):

        ds             = drives_summary
        speech_events  = narrative.data.get("speech_events", []) if narrative else []
        cycle_summaries= narrative.data.get("cycle_summaries", []) if narrative else []
        emotional_mems = memory.data.get("emotional_events", []) if memory else []
        inherited      = dna.get("inherited_tendencies", {})
        cons_mems      = dna.get("consolidated_memories", [])
        parent         = dna.get("parent_life_summary", {})

        # --- Compute stats ---
        emotion_counts = {}
        mood_vals, anxiety_vals, hunger_vals = [], [], []
        for e in speech_events:
            b = e.get("because", "neutral")
            emotion_counts[b] = emotion_counts.get(b, 0) + 1
            mood_vals.append(e.get("mood", 0))
            anxiety_vals.append(e.get("anxiety", 0))
            hunger_vals.append(e.get("hunger", 50))

        dominant_emotion = (max(emotion_counts, key=emotion_counts.get)
                            if emotion_counts else "unknown")
        avg_mood    = sum(mood_vals)    / len(mood_vals)    if mood_vals    else 0
        avg_anxiety = sum(anxiety_vals) / len(anxiety_vals) if anxiety_vals else 0

        top_memories = sorted(
            emotional_mems, key=lambda x: x.get("intensity", 0), reverse=True
        )[:5]

        # --- Build report ---
        lines = [
            f"# Generation {self.gen} — Life Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"End cause: **{cause_of_death}**",
            "",
            "---",
            "",
            "## Summary",
            f"- **Lifespan:** {ds['age_days']:.1f} days",
            f"- **Total caretaker interactions:** {total_interactions}",
            f"- **Total speech events:** {len(speech_events)}",
            f"- **Sleep cycles completed:** {sleep_summary.get('total_cycles', 0)}",
            f"- **Dominant emotion:** {dominant_emotion}",
            f"- **Average mood:** {avg_mood:+.1f} / 100",
            f"- **Average anxiety:** {avg_anxiety:.1f}%",
            "",
        ]

        # Emotional distribution
        lines += ["## Emotional Distribution", ""]
        total_sp = len(speech_events) or 1
        for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
            pct = count / total_sp * 100
            bar = "█" * max(1, int(pct / 4))
            lines.append(f"`{emotion:<15}` {bar} {pct:.0f}%")
        lines += ["", "---", ""]

        # Strongest memories
        lines += ["## Strongest Emotional Memories", ""]
        if top_memories:
            for m in top_memories:
                lines.append(
                    f"- **[{m.get('dominant','?')} | "
                    f"intensity {m.get('intensity', 0):.2f}]** "
                    f'*"{m.get("text","")[:80]}"*'
                )
        else:
            lines.append("*No strong emotional memories recorded.*")
        lines += ["", "---", ""]

        # Life in their own words
        lines += ["## Life In Their Own Words", "*(Sleep cycle summaries)*", ""]
        if cycle_summaries:
            for s in cycle_summaries:
                lines.append(f"**Day {s['age_days']:.1f}:** {s['text']}")
                lines.append("")
        else:
            lines.append("*No cycle summaries recorded — generation ended before first sleep.*")
        lines += ["---", ""]

        # DNA passed forward
        lines += ["## What Gets Passed to Next Generation", ""]
        lines += [
            f"- Anxiety baseline: **{inherited.get('anxiety_baseline', 0):.3f}**"
            + (f" (was {parent.get('anxiety_baseline', 0):.3f} in parent)"
               if parent.get("anxiety_baseline") is not None else ""),
            f"- Trust speed: **{inherited.get('trust_speed', 0):.3f}**",
            f"- Curiosity clusters: **{inherited.get('curiosity_clusters', 0):.3f}**",
            f"- Consolidated memory fragments: **{len(cons_mems)}**",
        ]
        if cons_mems:
            lines.append("")
            lines.append("**Top consolidated memories:**")
            for cm in cons_mems[:5]:
                lines.append(
                    f"  - [{cm.get('emotion','?')} | "
                    f"intensity {cm.get('intensity',0):.2f}] "
                    f'*"{cm.get("text","")[:60]}"*'
                )
        lines += ["", "---", ""]

        # Research metrics
        lines += ["## Research Metrics", "*(Track these across generations to measure drift)*", ""]

        # Hunger-anxiety correlation
        if len(hunger_vals) > 10:
            n      = len(hunger_vals)
            mean_h = sum(hunger_vals) / n
            mean_a = sum(anxiety_vals) / n
            cov    = sum((h - mean_h) * (a - mean_a)
                         for h, a in zip(hunger_vals, anxiety_vals)) / n
            std_h  = (sum((h - mean_h) ** 2 for h in hunger_vals) / n) ** 0.5
            std_a  = (sum((a - mean_a) ** 2 for a in anxiety_vals) / n) ** 0.5
            corr   = cov / (std_h * std_a) if std_h > 0 and std_a > 0 else 0
            lines.append(
                f"- **Hunger↔Anxiety correlation:** {corr:.3f}  "
                f"*(negative = hunger drives anxiety)*"
            )

        # Speech complexity drift
        if len(speech_events) > 20:
            early = speech_events[:10]
            late  = speech_events[-10:]
            early_avg = sum(len(e["text"].split()) for e in early) / 10
            late_avg  = sum(len(e["text"].split()) for e in late)  / 10
            delta = ((late_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0
            lines.append(
                f"- **Speech complexity drift:** {delta:+.0f}%  "
                f"*(early avg {early_avg:.1f} words → late avg {late_avg:.1f} words)*"
            )

        # Silence ratio
        silence_ticks = sleep_summary.get("total_cycles", 1) * 36
        speech_ratio  = len(speech_events) / max(1, silence_ticks + len(speech_events)) * 100
        lines.append(f"- **Speech vs silence ratio:** {speech_ratio:.1f}% of active ticks produced speech")

        lines.append(f"- **LoRA training examples available:** {len(speech_events)}")
        lines += ["", "---", ""]

        # Groq narrative summary
        narrative_text = self._groq_narrative(
            ds, dominant_emotion, avg_mood, avg_anxiety,
            total_interactions, cause_of_death, top_memories
        )
        if narrative_text:
            lines += [
                "## Narrative Summary",
                "*(Written from the data by Groq — not a human summary)*",
                "",
                narrative_text,
                "",
                "---",
                "",
            ]

        # Write
        content = "\n".join(lines)
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[AUTODOC] Life report written → {self.report_path}")
        return str(self.report_path)

    # ----------------------------------------------------------
    #  GROQ NARRATIVE — readable paragraph from raw stats
    # ----------------------------------------------------------
    def _groq_narrative(self, ds, dominant_emotion, avg_mood, avg_anxiety,
                        total_interactions, cause_of_death, top_memories):
        try:
            from groq import Groq
            from config import GROQ_API_KEY, LLM_MODEL
            client  = Groq(api_key=GROQ_API_KEY)
            mem_str = ". ".join(
                f'"{m.get("text","")[:50]}"' for m in top_memories[:3]
            )
            prompt = (
                f"Write an honest, concise paragraph (4-6 sentences) about the life "
                f"of Generation {self.gen} of an entity called Kora. "
                f"It lived {ds['age_days']:.1f} days and ended by {cause_of_death}. "
                f"Its dominant emotion was {dominant_emotion}. "
                f"Average mood: {avg_mood:+.1f}/100. Average anxiety: {avg_anxiety:.0f}%. "
                f"It had {total_interactions} interactions with its caretaker. "
                f"Its strongest memories: {mem_str}. "
                f"Write as if summarizing a real being's life. Honest, not sentimental. "
                f"No mention of AI, code, or simulation. Third person."
            )
            resp = client.chat.completions.create(
                model=LLM_MODEL, max_tokens=250, temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AUTODOC] Narrative generation failed: {e}")
            return ""

    # ----------------------------------------------------------
    #  UTIL
    # ----------------------------------------------------------
    def _append(self, path, text):
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
