# Project Samsara — Quickstart

## First Time Setup
1. Fill in config.py with your 2 keys:
   - GROQ_API_KEY    →  console.groq.com  (free — no credit card)
   - TELEGRAM_TOKEN  →  @BotFather on Telegram
   - TELEGRAM_CHAT_ID →  @userinfobot on Telegram

2. Install dependencies:
   pip install -r requirements.txt

   If pyaudio fails:
   brew install portaudio
   pip install pyaudio

## Run
   python main.py
   Open browser: http://localhost:5001

## Telegram Commands
/status   — full brain dashboard
/feed     — feed 40 units
/scold    — register disapproval (e.g. /scold anger without reason)
/teach    — teach a fact (e.g. /teach my_name=Maharshi)
/dna      — see DNA
/ven      — see self-model
/reset    — wipe state (keeps parent_dna.json for Gen 2)
/help     — all commands

## Files Created During Life
data/state.json          — current drives/emotions
data/memory.json         — all memories
data/dna.json            — genetics
data/telemetry.csv       — tick-by-tick CSV (open in Excel)
data/self_journal.jsonl  — inner state journal
data/session_report.json — end of session summary
decisions.json           — every decision + why
milestones.json          — developmental milestones
life_report.json         — full life analysis

## Gen 2
When Gen 1 dies, parent_dna.json is saved.
Delete all .json files EXCEPT parent_dna.json.
Run python main.py — Gen 2 starts with inherited traits.
