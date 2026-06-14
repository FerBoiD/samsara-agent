# ============================================================
#  TELEGRAM BOT — phone communication
#  AI → sends notifications to your phone
#  You → reply to talk to it, or use commands
# ============================================================

import asyncio
import threading
import time
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# Support multiple caretakers — TELEGRAM_CHAT_ID can be a single ID
# or a comma-separated list: "111111,222222,333333"
_ALLOWED_CHAT_IDS = {
    str(cid).strip()
    for cid in str(TELEGRAM_CHAT_ID).split(",")
    if cid.strip()
}

# Thread-safe queue for incoming messages from your phone
_incoming = []

# Persistent event loop for all send operations
# This fixes the "Event loop is closed" RuntimeError on Mac
_send_loop = None
_send_loop_lock = threading.Lock()


def _get_send_loop():
    """Get or create a persistent event loop for sending messages."""
    global _send_loop
    with _send_loop_lock:
        if _send_loop is None or _send_loop.is_closed():
            _send_loop = asyncio.new_event_loop()
            # Run loop in background thread so it stays alive
            t = threading.Thread(
                target=_send_loop.run_forever,
                daemon=True
            )
            t.start()
        return _send_loop


async def _async_send(text):
    bot = Bot(token=TELEGRAM_TOKEN)
    # Broadcast to all allowed caretakers
    for chat_id in _ALLOWED_CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=str(text))
        except Exception as e:
            print(f"[TELEGRAM ERROR] Failed to send to {chat_id}: {e}")
    await bot.close()


def send(text):
    """Send a message to your phone. Thread-safe, no event loop errors."""
    print(f"[TELEGRAM →] {text}")
    try:
        loop = _get_send_loop()
        future = asyncio.run_coroutine_threadsafe(_async_send(text), loop)
        future.result(timeout=10)  # wait max 10 seconds
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


def send_status(s):
    """Send a formatted status update."""
    cog = s['cog_state'].upper()
    bar = lambda v: "█" * int(v / 10) + "░" * (10 - int(v / 10))

    msg = (
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 STATUS  Day {s['age_days']}/45  ({s['days_left']}d left)\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🍽 Hunger     {bar(s['hunger'])} {s['hunger']}%\n"
        f"⚡ Energy     {bar(s['energy'])} {s['energy']}%\n"
        f"😴 Boredom    {bar(s['boredom'])} {s['boredom']}%\n"
        f"😤 Frustration {bar(s['frustration'])} {s['frustration']}%\n"
        f"😰 Anxiety    {bar(s['anxiety'])} {s['anxiety']}%\n"
        f"😆 Excitement {bar(s['excitement'])} {s['excitement']}%\n"
        f"🧠 Mood       {s['mood']:+.0f}/100\n"
        f"🐌 Lethargy   {s['lethargy']}%\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🎯 Feels: {s['dominant'].upper()}\n"
        f"🧩 State: {cog}"
    )
    send(msg)


def send_birth_notice(personality):
    p = dict(personality.get("traits", personality))
    p["generation"] = personality.get("generation", p.get("generation", 1))
    msg = (
        f"🌱 A new entity has been born.\n\n"
        f"Generation {p['generation']} — Day 0 of 45\n\n"
        f"Personality seed:\n"
        f"  Curiosity:   {'HIGH' if p['curiosity_rate'] > 1.0 else 'moderate'}\n"
        f"  Social need: {'HIGH' if p['social_drive'] > 0.8 else 'moderate'}\n"
        f"  Talkativeness: {'HIGH' if p['talkativeness'] > 0.7 else 'low'}\n"
        f"  Resilience:  {'HIGH' if p['resilience'] > 0.6 else 'low'}\n\n"
        f"Commands: /status /feed /teach /reset\n"
        f"Or just type to talk to it."
    )
    send(msg)


# ----------------------------------------------------------
#  RECEIVE (Phone → AI)
# ----------------------------------------------------------
async def _handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = str(update.message.chat_id)
    if sender_id not in _ALLOWED_CHAT_IDS:
        return  # ignore messages from unknown chats

    text = update.message.text.strip()
    print(f"[TELEGRAM ←] {sender_id}: {text}")

    # --- Commands ---
    if text.lower() == "/status":
        _incoming.append({"type": "cmd", "cmd": "status"})
        return
    if text.lower() == "/feed":
        _incoming.append({"type": "cmd", "cmd": "feed"})
        return
    if text.lower() == "/reset":
        _incoming.append({"type": "cmd", "cmd": "reset"})
        return
    if text.lower().startswith("/teach "):
        # Format: /teach key=value
        rest = text[7:].strip()
        if "=" in rest:
            key, val = rest.split("=", 1)
            _incoming.append({"type": "cmd", "cmd": "teach", "key": key.strip(), "value": val.strip()})
        return
    if text.lower() == "/help":
        send(
            "Commands:\n"
            "/status — see all drive levels\n"
            "/feed — give it energy (40 units)\n"
            "/teach key=value — teach it a fact\n"
            "  e.g. /teach name=Claude\n"
            "  e.g. /teach caretaker=you\n"
            "/reset — delete state and restart life\n"
            "\nOr just type anything to talk to it."
        )
        return

    # Regular message — goes to AI (sender_id included for social tracking)
    _incoming.append({"type": "message", "text": text, "sender_id": sender_id})


def get_incoming():
    """Pop and return the next incoming item, or None."""
    if _incoming:
        return _incoming.pop(0)
    return None


def start_listener():
    """Start Telegram polling in a background daemon thread."""
    def run():
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT, _handle_message))
        print("[TELEGRAM] Listening...")
        app.run_polling(allowed_updates=["message"],stop_signals=None)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
