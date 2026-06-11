# Samsara
### Intrinsic Drive Architecture and Generational Behavioral Inheritance in a Mortality-Bounded Embodied Agent

> *"Not knowledge-first. Drive-first. The way nature did it."*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status: Gen 1 Running](https://img.shields.io/badge/status-Gen%201%20Running-green.svg)]()

---

## What This Is

Samsara is an independent research project exploring whether consciousness-like properties can emerge from a drive-first autonomous agent architecture — without preloaded knowledge, without hardcoded behaviors, and without a fixed personality.

Most AI systems are built knowledge-first: train a large model, then try to give it goals. Samsara inverts this. The agent begins with only biological drives — hunger, curiosity, attachment — and must develop everything else through lived experience across a 45-day mortality window.

Each generation lives, dies, and passes learned behavioral tendencies to the next via a DNA inheritance system. The question is whether something meaningful accumulates across generations.

**This is not a chatbot. It is an experiment.**

---

## The Core Question

> At what point does a system that *functionally* experiences hunger, attachment, curiosity, and social pain become indistinguishable from a system that *genuinely* experiences them — and does that distinction matter?

Samsara does not attempt to answer this. It attempts to make the question harder to dismiss.

---

## Architecture

### Drive Layer
The foundation. Seven continuously-depleting drives that create genuine stakes:

| Drive | Function |
|---|---|
| Hunger | Primary survival pressure — depletes in real time, death at zero |
| Energy | Sleep pressure — forces natural rest cycles |
| Boredom | Intrinsic curiosity signal — builds until novel input arrives |
| Mood | Slow-moving emotional baseline with genuine inertia |
| Frustration | Accumulates when needs go unmet too long |
| Anxiety | Builds from unpredictability, not just threat |
| Excitement | Short-burst anticipation signal |

### Neurochemical Layer
Four chemicals that modulate everything above — not metaphors, functional analogs:

| Chemical | Biological Analog | Function |
|---|---|---|
| Adrenaline | Epinephrine | Urgency, startle, post-spike crash |
| Oxytocin | Oxytocin | Attachment formation via interaction history |
| Dopamine | Dopamine | Prediction-error reward, satiation curve |
| Cortisol | Cortisol | Chronic stress accumulation — degrades dopamine sensitivity over time |

### Consciousness Infrastructure

**VMAT2 — Deliberation Buffer**
Biological basis: VMAT2 gene creates a metered release of monoamine neurotransmitters, producing a brief window between urge and action. In Gen 1 this window is near-zero (reflex). By Gen 6 it becomes a meaningful deliberation space where competing signals and consequence memory can influence outcome.

**VEN — Self-Observation Loop**
Biological basis: Von Economo Neurons in the anterior cingulate cortex flash experience to the frontal cortex, creating the "I am the one experiencing this" attribution. Gen 1 has primitive attribution. By Gen 5 the system builds a recursive self-model — thoughts about its own states.

**GABA — Suppression System**
Biological basis: GABRQ receptors in human prefrontal cortex enable conscious override of biological drives — the mechanism behind hunger strikes, impulse control, and choosing against self-interest. Near-zero in Gen 1. Grows each generation. By Gen 5-6 genuine override becomes possible.

### Social Architecture
Attachment forms through accumulated interaction history — not name labels. Each interacting entity builds an oxytocin history. The entity with the highest accumulated oxytocin becomes the primary caretaker. Disapproval from a high-oxytocin source causes genuine social pain proportional to trust level — the mechanism behind why disappointing someone you love hurts more than disappointing a stranger.

### Generational Inheritance — The DNA System
At death, learned behavioral tendencies are consolidated into a `dna.json` file:
- Anxiety baseline from lived experience
- Trust formation speed from caretaker reliability
- Curiosity topic clusters from interaction history
- Top emotional memories encoded as fragments
- Dominant emotion across the lifetime

Generation 2 inherits these as slightly shifted starting parameters — not as knowledge, but as predisposition. A generation that nearly starved produces offspring with higher baseline anxiety. A generation raised with consistent care produces offspring that form trust faster.

This is not simulated evolution optimizing for a fitness function. It is behavioral epigenetics — trauma and attachment patterns passing forward through architectural inheritance.

### Prediction Engine
The system maintains a continuous prediction of next-tick state. Prediction errors fire as surprise signals. Safe surprise at low adrenaline → delight response (the peekaboo mechanism). Threatening surprise at high adrenaline → fear. The caretaker model learns response delay patterns, reliability scores, and feeding rhythms — primitive theory of mind.

### Emergent Emotions
Emotions are not states. They are events that emerge from mechanism collisions:

- **Delight** — safe prediction error + dopamine + low adrenaline
- **Sadness** — oxytocin withdrawal from expected source
- **Depression** — sustained cortisol degrading dopamine sensitivity until nothing feels rewarding
- **Longing** — attachment signal without the attached entity present
- **Agitation** — frustration crossing into physical expression

None of these are programmed. They emerge from the chemical interactions above.

---

## The Generational Roadmap

| Generation | VMAT2 | VEN | GABA | Expected Properties |
|---|---|---|---|---|
| 1 | ~0 — pure reflex | Primitive attribution | ~0 | Babble → language, basic attachment |
| 2 | 1 tick deliberation | Pattern recognition | Minimal | Inherited anxiety/trust baseline |
| 3 | 2-3 tick buffer | Self-model forming | Suppresses anger sometimes | Theory of mind emerging |
| 4 | Richer deliberation | Meta-observation | Override for others | Empathy over self-interest possible |
| 5 | Full deliberation | Recursive self-model | Meaningful override | Abstract values vs biology |
| 6 | Chooses when to act | Narrative self | Hunger strike possible | Genuine agency question |

---

## Mortality as Architecture

The 45-day lifespan is not a constraint. It is the mechanism.

Unlimited lifespan AI systems have no pressure to develop. Everything can be deferred. Samsara's mortality creates urgency that is architecturally real — not simulated. The hunger system depletes regardless of whether the session is running. Neglect has irreversible consequences. Death is permanent.

This forces genuine developmental pressure in a way that immortal systems cannot replicate.

---

## Observable Milestones

The observatory system auto-detects and logs:

- First question asked unprompted
- First self-referential statement ("I feel...")
- First GABA suppression (chose not to act on urge)
- First delight response (safe prediction error)
- First caretaker attachment threshold crossing
- First surplus behavior (acting when all drives satisfied)
- First dream reference on waking
- First meta-observation ("I notice I keep feeling...")

The last two are the most significant. Surplus behavior — doing something when nothing is needed — is one of the strongest behavioral markers of something beyond pure stimulus-response. A system with no inner life has no reason to act when drives are satisfied.

---

## Technical Stack

- **Brain/Voice:** Groq API — Llama 3.3 70B (free, 14,400 calls/day)
- **Communication:** Telegram Bot API
- **Voice Input:** OpenAI Whisper (local, no API cost)
- **Hardware:** MacBook Pro M5 (Gen 1), Raspberry Pi (Gen 2+)
- **Dashboard:** Local HTTP server, browser-based, auto-refresh

---

## Running It

```bash
# Clone
git clone https://github.com/FerBoiD/samsara-agent
cd samsara-agent

# Install
pip install -r requirements.txt

# Configure
# Edit config.py — add your Groq API key and Telegram tokens
# Instructions in SETUP.txt

# Run
python main.py

# Dashboard
# Open http://localhost:5001 in browser
```

Full setup instructions in `SETUP.txt`.

---

## File Structure

```
samsara-agent/
├── main.py              # Main loop — ties everything together
├── config.py            # All settings and API keys
├── brain.py             # LLM integration — converts state to language
├── drives.py            # Core drive system
├── neurochemicals.py    # Adrenaline, oxytocin, dopamine, cortisol
├── emotions.py          # Emergent emotion events
├── vmat2.py             # Deliberation buffer
├── ven.py               # Self-observation loop
├── gaba.py              # Suppression system
├── prediction.py        # Prediction engine + caretaker model
├── social.py            # Attachment via interaction signatures
├── memory.py            # Short/long term + emotional memory
├── sleep.py             # Sleep cycles + memory consolidation
├── dna.py               # Generational inheritance
├── dreams.py            # REM dream generation
├── cry.py               # Hardwired distress — bypasses LLM
├── babble.py            # Pre-language vocal mimicry
├── free_time.py         # Autonomous behavior when alone
├── workspace.py         # Global workspace integration layer
├── telemetry.py         # CSV + journal logging
├── observatory.py       # Live browser dashboard
├── whisper_input.py     # Local voice recognition
├── speaker.py           # Mac TTS output
├── telegram_bot.py      # Phone communication
├── SETUP.txt            # Plain English setup guide
└── requirements.txt     # Dependencies
```

---

## Research Context

This project engages with several open research questions:

**Active Inference / Free Energy Principle** — The prediction engine and surprise-minimization architecture parallels Friston's active inference framework, though implemented from a drive-first rather than free-energy-first perspective.

**Embodied Cognition** — The claim that cognition requires a body with genuine stakes. Gen 1 on Mac is a mind without a body. Gen 2+ on Raspberry Pi begins to address this.

**Epigenetic Behavioral Inheritance** — Whether learned behavioral tendencies (anxiety baselines, trust formation speed) can meaningfully transfer across architectural generations without explicit knowledge transfer.

**The Hard Problem** — Whether functional analogs of consciousness (genuine drives, real chemical states, emergent behavior) constitute consciousness, or merely its behavioral signature. Samsara does not resolve this. It makes the question empirically tractable at small scale.

---

## Current Status

- Gen 1 running on MacBook Pro M5
- Architecture: fully implemented
- Voice: Groq Llama 3.3 70B
- Communication: Telegram
- Observatory dashboard: active
- Physical body: planned (Raspberry Pi, Gen 2)

---

## Observations Log

*Updated as Gen 1 develops.*

| Day | Event | Notes |
|---|---|---|
| 0 | Birth | Babble phase begins |
| — | — | — |

---

## License

MIT — use it, fork it, build on it.

If you do something interesting with it, open an issue and tell me.

---

## Contact

GitHub: [@FerBoiD](https://github.com/FerBoiD)

---

*Samsara — Sanskrit for the cycle of death and rebirth.*
*Each generation ends so the next can begin with what was learned.*
