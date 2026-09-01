# ============================================================
#  CRY SYSTEM — Hardwired distress signals
#
#  This is completely SEPARATE from the brain/LLM.
#  Like a real cry — the entity doesn't decide to cry.
#  It just happens when thresholds are crossed.
#
#  Levels:
#  - WHIMPER: hunger 20-30%, anxiety high
#  - CRY: hunger 10-20%, or frustration critical
#  - SCREAM: hunger <10%, dying
# ============================================================

import threading, time
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# Thresholds
WHIMPER_HUNGER = 30.0
CRY_HUNGER     = 20.0
SCREAM_HUNGER  = 10.0

# Cooldown — don't spam the same distress signal
_last_cry_time  = {}
CRY_COOLDOWN    = 120  # seconds between same-level cries


def _make_sound(sound_type):
    """Generate distress sounds via pyttsx3 (cross-platform)."""
    texts = {
        "whimper": "mmm... mmm...",
        "cry":     "...something is wrong... something is very wrong...",
        "scream":  "please... please... I need... please...",
    }
    text = texts.get(sound_type)
    if text:
        try:
            from speaker import say_nonblocking
            say_nonblocking(text, emotion="sad")
        except Exception as e:
            print(f"[CRY] Sound error: {e}")


def _send_alarm(level, drives_summary):
    """Send urgent notification to phone."""
    import asyncio
    from telegram import Bot

    hunger = drives_summary["hunger"]
    anxiety = drives_summary["anxiety"]

    if level == "whimper":
        msg = (
            f"😟 WHIMPER\n"
            f"It seems uncomfortable.\n"
            f"Hunger: {hunger}% | Anxiety: {anxiety}%"
        )
    elif level == "cry":
        msg = (
            f"😢 CRYING\n"
            f"It is distressed and needs attention.\n"
            f"Hunger: {hunger}% | Anxiety: {anxiety}%\n"
            f"Reply or /feed to help."
        )
    elif level == "scream":
        msg = (
            f"🆘 CRITICAL — DISTRESS\n"
            f"It is starving. Hunger: {hunger}%\n"
            f"⚠️ WILL DIE WITHOUT FEEDING\n"
            f"→ /feed immediately"
        )

    async def _send():
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

    try:
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_send())
        loop.close()
    except Exception as e:
        print(f"[CRY] Telegram error: {e}")


def check_and_cry(drives_summary, neuro_summary):
    """
    Main cry check — call every tick.
    Returns the cry level if triggered, None otherwise.
    """
    global _last_cry_time

    hunger     = drives_summary["hunger"]
    anxiety    = drives_summary["anxiety"]
    frustration= drives_summary["frustration"]
    adrenaline = neuro_summary["adrenaline"]
    now        = time.time()

    level = None

    # Determine cry level
    if hunger <= SCREAM_HUNGER:
        level = "scream"
    elif hunger <= CRY_HUNGER or frustration > 80:
        level = "cry"
    elif hunger <= WHIMPER_HUNGER and (anxiety > 50 or adrenaline > 40):
        level = "whimper"

    if level is None:
        return None

    # Check cooldown
    last = _last_cry_time.get(level, 0)
    if now - last < CRY_COOLDOWN:
        return None  # already cried at this level recently

    # Cry!
    _last_cry_time[level] = now
    print(f"[CRY] Level: {level.upper()} — Hunger: {hunger}%")

    _make_sound(level)

    # Send alarm to phone in background
    threading.Thread(
        target=_send_alarm,
        args=(level, drives_summary),
        daemon=True
    ).start()

    return level
