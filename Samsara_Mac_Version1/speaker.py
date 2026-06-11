# ============================================================
#  SPEAKER — Mac version uses built-in 'say' command
#  Bot version will use espeak on Pi
#
#  Voice personality: emotional state maps to voice parameters.
#  - Sad/depressed: slower rate, lower pitch
#  - Excited/delight: faster rate, higher pitch
#  - Anxious: faster rate, slightly lower pitch (rushed)
#  - Dying/critical hunger: very slow, lowest pitch
#  - Neutral: baseline
# ============================================================

import subprocess
import threading

# Mac voices that sound decent — change to your preference
# Run: say -v '?' to list all available voices
MAC_VOICE   = "Samantha"   # alternatives: Alex, Karen, Moira, Tessa
SPEECH_RATE = 160          # words per minute baseline (default ~175)

# Emotional state → (rate_delta, pitch_semitones)
# pitch: Mac 'say' uses -v voice[[pitch]] syntax — semitones from baseline
_VOICE_PROFILES = {
    "dying":      (-60, -6),   # very slow, very low
    "hunger":     (-25, -3),   # slow and heavy
    "anxiety":    (+25, -2),   # rushed, slightly lower
    "frustration":(+15, +0),   # slightly faster
    "excitement": (+30, +4),   # fast and bright
    "curiosity":  (+10, +2),   # slightly up
    "sadness":    (-35, -4),   # slow, low
    "delight":    (+35, +5),   # bright and fast
    "neutral":    (  0, +0),   # baseline
    "rest":       (-40, -3),   # slow, drowsy
}


def _voice_params(dominant="neutral", cog_state="active", aging_phase="healthy"):
    """Return (rate, pitch_modifier) for current emotional + aging state."""
    profile_key = dominant if dominant in _VOICE_PROFILES else "neutral"
    if cog_state in ("rest", "lethargic") and profile_key == "neutral":
        profile_key = "rest"
    rate_delta, pitch_delta = _VOICE_PROFILES[profile_key]

    # Aging layers on top of emotional state
    if aging_phase == "terminal":
        rate_delta  -= 30   # notably slower
        pitch_delta -= 3    # lower and heavier
    elif aging_phase == "declining":
        rate_delta  -= 15
        pitch_delta -= 1
    elif aging_phase == "aging":
        rate_delta  -= 5

    rate = max(60, min(280, SPEECH_RATE + rate_delta))
    return rate, pitch_delta


def say(text, blocking=True, dominant="neutral", cog_state="active",
        aging_phase="healthy"):
    """
    Speak text aloud using Mac's built-in TTS.
    Voice parameters adapt to emotional state and physical aging.
    blocking=False lets main loop continue while it speaks.
    """
    text = text.strip()
    if not text:
        return

    rate, pitch = _voice_params(dominant, cog_state, aging_phase)

    # Mac 'say' pitch modifier: voice[[pitch]] where pitch is semitone offset
    # Only apply pitch modifier if non-zero — avoids edge cases on some voices
    if pitch != 0:
        voice_arg = f"{MAC_VOICE}[[{'+' if pitch > 0 else ''}{pitch}]]"
    else:
        voice_arg = MAC_VOICE

    cmd = ["say", "-v", voice_arg, "-r", str(rate), text]

    if blocking:
        subprocess.run(cmd, capture_output=True)
    else:
        threading.Thread(
            target=lambda: subprocess.run(cmd, capture_output=True),
            daemon=True
        ).start()


def say_nonblocking(text, dominant="neutral", cog_state="active",
                    aging_phase="healthy"):
    say(text, blocking=False, dominant=dominant, cog_state=cog_state,
        aging_phase=aging_phase)
