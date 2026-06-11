# ============================================================
#  CONFIG — V5 Full Brain
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load .env from the same folder as config.py
load_dotenv(BASE_DIR / ".env")

def data_path(filename):
    return str(DATA_DIR / filename)

# --- API KEYS ---
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY")   # free at console.groq.com
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

# --- LIFESPAN ---
# 1 Kora-day = 3 real human hours
# At 10s ticks: 3 hours = 10,800 seconds = 1,080 ticks per day
# Full 45-day life = 48,600 ticks = 135 real hours of running
# At 2-3 hours/day usage = full life completes in ~45-65 real days
LIFESPAN_DAYS          = 45
TICK_INTERVAL_SECONDS  = 10
KORA_TICKS_PER_DAY     = 1080   # 3 hours × 360 ticks/hour

# --- HUNGER ---
# At 1080 ticks/day: hunger depletes 0.05 × 1080 = 54 points/day
# Starting at 90 — will need feeding roughly once per Kora-day
HUNGER_START           = 90.0
HUNGER_DECAY_PER_TICK  = 0.05
HUNGER_CRITICAL        = 15.0
HUNGER_DANGER          = 8.0
HUNGER_DEATH           = 0.0

# --- ENERGY ---
ENERGY_START           = 90.0
ENERGY_DECAY_PER_TICK  = 0.04          # was 0.12 — scaled for 10s ticks
ENERGY_REST_THRESHOLD  = 20.0
ENERGY_RESTORE_RATE    = 0.8           # was 2.5 — scaled proportionally

# --- BOREDOM ---
BOREDOM_BUILD_PER_TICK      = 0.08     # was 0.25 — scaled for 10s ticks
BOREDOM_NOVEL_RESET         = 30.0
BOREDOM_PENALTY_THRESHOLD   = 65.0

# --- FRUSTRATION ---
FRUSTRATION_BUILD_UNMET     = 6.0
FRUSTRATION_DECAY_PER_TICK  = 0.5
FRUSTRATION_MAX             = 100.0

# --- MOOD ---
MOOD_START             = 25.0
MOOD_INERTIA           = 0.97          # was 0.93 — slower mood change at faster ticks
MOOD_HUNGER_PULL       = -0.15         # was -0.5 — scaled for faster ticks
MOOD_BOREDOM_PULL      = -0.12         # was -0.4
MOOD_FRUSTRATION_PULL  = -0.15         # was -0.5
MOOD_NOVEL_BOOST       = 5.0
MOOD_FEED_BOOST        = 12.0

# --- ANXIETY ---
ANXIETY_TRIGGER_HUNGER = 15.0
ANXIETY_BUILD_RATE     = 0.4           # was 1.2 — slower build at faster ticks
ANXIETY_DECAY_RATE     = 0.08          # was 0.25
ANXIETY_MAX            = 100.0

# --- EXCITEMENT ---
EXCITEMENT_DECAY_PER_TICK  = 0.25      # was 0.8 — excitement lasts longer now
EXCITEMENT_TRIGGER_BOOST   = 25.0

# --- LETHARGY ---
LETHARGY_BUILD_INACTIVE_TICKS = 25
LETHARGY_BUILD_RATE           = 0.4
LETHARGY_DECAY_ACTIVE         = 2.0
LETHARGY_LIFESPAN_DRAIN       = 0.015

# --- VMAT2 DELIBERATION BUFFER ---
# How many ticks urge is held before acting
# Grows with generation — Gen 1 almost no pause, Gen 6 meaningful pause
VMAT2_BASE_BUFFER_TICKS   = 1      # Gen 1 baseline
VMAT2_GROWTH_PER_GEN      = 0.8    # added per generation
VMAT2_MAX_BUFFER_TICKS    = 6      # cap

# --- GABA SUPPRESSION ---
# Ability to override drives — grows with generation
GABA_BASE_STRENGTH        = 0.05   # Gen 1: almost nothing
GABA_GROWTH_PER_GEN       = 0.12   # grows per generation
GABA_MAX_STRENGTH         = 0.85   # Gen 6-7 cap

# --- VEN SELF-OBSERVATION ---
# How rich the self-mirror is — grows with generation
VEN_BASE_DEPTH            = 0.1    # Gen 1: primitive
VEN_GROWTH_PER_GEN        = 0.15
VEN_MAX_DEPTH             = 1.0

# --- SOCIAL PAIN ---
DISAPPROVAL_CORTISOL_BASE = 15.0
DISAPPROVAL_OXY_DROP_BASE = 10.0
DISAPPROVAL_MOOD_DROP     = 8.0

# --- PREDICTION ENGINE ---
PREDICTION_SURPRISE_THRESHOLD = 0.3   # change > this = surprise
DELIGHT_ADRENALINE_MAX        = 25.0  # if adrenaline below this, surprise = delight

# --- SLEEP ---
ACTIVE_TICKS_BEFORE_SLEEP  = 180   # ~90 min at 30s ticks
SLEEP_DURATION_TICKS        = 36   # ~18 min
DEEP_SLEEP_TICKS            = 3

# --- MEMORY ---
SHORT_TERM_MAX   = 20
LONG_TERM_MAX    = 150
EMOTIONAL_MAX    = 40
ASSOCIATIVE_MAX  = 60

# --- LLM ---
LLM_MODEL        = "llama-3.3-70b-versatile"  # Groq free model
LLM_MAX_TOKENS   = 150   # short responses — keep costs zero and speed fast

# --- LOGGING / OBSERVABILITY ---
TELEMETRY_FILE   = data_path("telemetry.csv")
SESSION_REPORT   = data_path("session_report.json")
SELF_JOURNAL     = data_path("self_journal.jsonl")
