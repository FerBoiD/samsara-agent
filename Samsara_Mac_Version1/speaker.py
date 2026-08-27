# ============================================================
#  SPEAKER — cross-platform version
#
#  Mac:     built-in NSSpeech (via pyttsx3)
#  Windows: SAPI5 (via pyttsx3)
#  Linux:   espeak (via pyttsx3)
#
#  Voice personality: emotional state maps to rate + volume.
#  Pitch is not reliably exposed on all engines, so emotional
#  colour comes from rate and volume variation instead.
# ============================================================

import threading
import sys

try:
    import pyttsx3
    _engine = pyttsx3.init()
    TTS_AVAILABLE = True
except Exception as e:
    print(f"[SPEAKER] TTS not available: {e}")
    TTS_AVAILABLE = False
    _engine = None

_lock = threading.Lock()

# Words-per-minute baseline
SPEECH_RATE = 165

# Emotional state → (rate_delta, volume_0to1)
_VOICE_PROFILES = {
    "dying":       (-65, 0.55),   # very slow, quiet
    "hunger":      (-28, 0.70),   # slow and heavy
    "anxiety":     (+28, 0.90),   # rushed
    "frustration": (+18, 0.85),   # faster
    "excitement":  (+32, 1.00),   # fast and bright
    "curiosity":   (+12, 0.88),   # slightly up
    "sadness":     (-38, 0.65),   # slow, quiet
    "delight":     (+38, 1.00),   # bright and fast
    "neutral":     (  0, 0.80),   # baseline
    "rest":        (-42, 0.60),   # slow, drowsy
}


def _voice_params(dominant="neutral", cog_state="active", aging_phase="healthy"):
    key = dominant if dominant in _VOICE_PROFILES else "neutral"
    if cog_state in ("rest", "lethargic") and key == "neutral":
        key = "rest"
    rate_delta, volume = _VOICE_PROFILES[key]

    if aging_phase == "terminal":
        rate_delta -= 30
        volume = max(0.4, volume - 0.15)
    elif aging_phase == "declining":
        rate_delta -= 15
        volume = max(0.5, volume - 0.08)
    elif aging_phase == "aging":
        rate_delta -= 5

    rate = max(60, min(280, SPEECH_RATE + rate_delta))
    return rate, volume


def _pick_voice():
    """Pick first available non-default voice — Windows prefers Zira/David."""
    if not TTS_AVAILABLE:
        return
    voices = _engine.getProperty("voices")
    if not voices:
        return
    # On Windows, prefer Microsoft Zira (female) or David; fall back to index 0
    preferred = [v for v in voices if any(
        n in v.name for n in ("Zira", "David", "Hazel", "George", "Samantha")
    )]
    chosen = preferred[0] if preferred else voices[0]
    _engine.setProperty("voice", chosen.id)


_pick_voice()


def say(text, blocking=True, dominant="neutral", cog_state="active",
        aging_phase="healthy"):
    """
    Speak text aloud using the system TTS engine.
    blocking=False lets the main loop continue while Kora speaks.
    """
    if not TTS_AVAILABLE:
        return
    text = text.strip()
    if not text:
        return

    rate, volume = _voice_params(dominant, cog_state, aging_phase)

    def _speak():
        with _lock:
            _engine.setProperty("rate",   rate)
            _engine.setProperty("volume", volume)
            _engine.say(text)
            _engine.runAndWait()

    if blocking:
        _speak()
    else:
        threading.Thread(target=_speak, daemon=True).start()


def say_nonblocking(text, dominant="neutral", cog_state="active",
                    aging_phase="healthy"):
    say(text, blocking=False, dominant=dominant, cog_state=cog_state,
        aging_phase=aging_phase)
