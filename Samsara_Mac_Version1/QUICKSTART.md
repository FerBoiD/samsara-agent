# Project Samsara — Quickstart

## What You Need to Download (one-time)

| Thing | Size | Where | Cost |
|---|---|---|---|
| Python 3.9+ | ~30MB | python.org | Free |
| Godot 4.3+ | ~100MB | godotengine.org | Free |
| Groq API key | — | console.groq.com | Free (no card) |
| Telegram bot token | — | @BotFather on Telegram | Free |

No new pip packages needed for body.py, godot_bridge.py — standard library only.
Optional: free audio files from freesound.org (ambient sounds, stomach growl, footsteps).

---

## First Time Setup — Windows

1. Install Python 3.9+ from python.org — tick **"Add Python to PATH"** during install.

2. Fill in `config.py` with your keys:
   - GROQ_API_KEY    →  console.groq.com  (free — no credit card)
   - TELEGRAM_TOKEN  →  @BotFather on Telegram
   - TELEGRAM_CHAT_ID →  @userinfobot on Telegram

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. If pyaudio fails (voice input, optional):
   ```
   pip install pipwin
   pipwin install pyaudio
   ```
   Voice input is optional — Kora runs fine on Telegram + Godot chat without it.

5. TTS (Kora's voice) uses Windows built-in SAPI5 — no extra install needed.
   To pick a different Windows voice: open Settings → Time & Language → Speech → Manage voices.

---

## First Time Setup — Mac

1. Fill in `config.py` with your keys.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   If pyaudio fails: `brew install portaudio && pip install pyaudio`

---

## Run (Python only — text/Telegram mode)

```
python main.py
Open browser: http://localhost:5001
```

---

## Run with Godot Sphere

```
# Terminal 1 — start Kora first (opens TCP bridge on port 9999)
python main.py

# Terminal 2 (or just use Godot UI)
# Open Godot, import Godot_Sphere/project.godot, press Play
```

The sphere connects automatically. Green dot = connected. Red dot = waiting.

### Godot controls
- **Tab** — toggle stats overlay (drives, body bars)
- **Type in bottom bar + Enter** — talk to Kora directly (no Telegram needed)
- **Feed button** — click to feed
- **Drink button** — click to give water
- **Click food bowl in world** — also feeds
- **Click water bowl in world** — also gives water
- **Arrow keys** — rotate camera (if using the orbit camera script)

---

## Running on Lenovo (24/7 Ubuntu) + watching on Mac

```
# On Lenovo — runs Kora 24/7
python main.py

# On Mac — watch the sphere
# In Godot_Sphere/scripts/DrivesBridge.gd, change:
#   const HOST := "127.0.0.1"
# to:
#   const HOST := "192.168.x.x"   ← your Lenovo's LAN IP
# Then press Play in Godot on Mac
# The sphere will connect to Kora on Lenovo over WiFi
```

To export Godot as a standalone Linux app (no Godot installation on Lenovo):
- Godot → Project → Export → Linux x86_64
- Download Linux export template (one-time, ~200MB)
- Copy the exported .pck + executable to Lenovo

---

## Telegram Commands

```
/status   — full brain dashboard
/feed     — feed 40 hunger units
/drink    — give water (thirst)
/scold    — register disapproval
/teach    — teach a fact (e.g. /teach my_name=Maharshi)
/dna      — see DNA and inherited traits
/ven      — see self-model
/reset    — wipe state (keeps parent_dna.json for Gen 2)
/help     — all commands
```

---

## Files Created During Life

```
data/state.json                — current drives/emotions
data/memory.json               — all memories
data/dna.json                  — genetics + inheritance
data/body.json                 — body sensations (thirst, temp, nausea, etc.)
data/narrative.json            — speech events + sleep cycle stories
data/telemetry.csv             — tick-by-tick CSV (open in Excel)
data/self_journal.jsonl        — inner state journal
data/session_report.json       — end of session summary
data/docs/gen1_daily_log.md    — readable daily log (auto every sleep cycle)
data/docs/gen1_life_report.md  — full generation report (at death)
decisions.json                 — every decision + why
milestones.json                — developmental milestones
life_report.json               — observatory life analysis
```

---

## Auto Documentation

Two markdown files write themselves — nothing to do:

`data/docs/gen1_daily_log.md`
  One entry per sleep cycle. Drives + body state, recent speech with
  causal context, caretaker absence. Open in VS Code while Kora runs.

`data/docs/gen1_life_report.md`
  Written at death or Ctrl+C. Full generation record: stats,
  emotional distribution, strongest memories, sleep cycle stories
  in Kora's words, DNA passed forward, research metrics,
  Groq-written narrative paragraph.

Files named by generation — gen2_* for Gen 2. Never overwrite.

---

## Gen 2

When Gen 1 dies, `parent_dna.json` is saved automatically.
Delete all `.json` files in `data/` EXCEPT `parent_dna.json`.
Run `python main.py` — Gen 2 starts with Gen 1's inherited traits.

---

## What Kora Does Physically (Godot)

| Condition | Behavior |
|---|---|
| Bored / restless | Wanders to random spots |
| Hunger < 55% | Walks to food bowl, eating animation |
| Thirst < 32% | Walks to water bowl, drinking animation |
| Hunger < 20% | Hunches, stomach glows orange-red, sound |
| Nausea > 55% | Sways side to side, green glow, blocks food |
| Body temp < 36°C (cold night) | Shivers, huddles toward centre |
| Muscle fatigue > 78% | Crouches/sits, resists wandering |
| Sick | Slow, pale green tint, dim eyes |
| Anxious | Rapid erratic steps, head shakes |
| Excited | Fast bouncy movement, cyan eyes |
| Sleeping | Walks to sleep spot, ZZZ particles |
| Waking | Stretches upward, ZZZ stops |
| Dying | Sphere walls pulse dark red |
