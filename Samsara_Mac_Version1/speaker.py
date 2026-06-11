# ============================================================
#  SPEAKER — Mac version uses built-in 'say' command
#  Bot version will use espeak on Pi
# ============================================================

import subprocess
import threading

# Mac voices that sound decent — change to your preference
# Run: say -v '?' to list all available voices
MAC_VOICE = "Samantha"   # alternatives: Alex, Karen, Moira, Tessa
SPEECH_RATE = 160        # words per minute (default ~175)


def say(text, blocking=True):
    """
    Speak text aloud using Mac's built-in TTS.
    blocking=False lets main loop continue while it speaks.
    """
    text = text.strip()
    if not text:
        return

    cmd = ["say", "-v", MAC_VOICE, "-r", str(SPEECH_RATE), text]

    if blocking:
        subprocess.run(cmd, capture_output=True)
    else:
        threading.Thread(target=lambda: subprocess.run(cmd, capture_output=True), daemon=True).start()


def say_nonblocking(text):
    say(text, blocking=False)
