# ============================================================
#  BABBLE ENGINE — Vocal mimicry
#
#  Early life behavior — before real language develops.
#  When you speak, it tries to match your pitch/rhythm.
#  Not words. Just tonal response.
#
#  After enough interactions, babbling fades and real
#  language takes over. Just like a baby.
#
#  Requires: pyaudio, numpy (install separately)
#  Falls back to simple sounds if not available.
# ============================================================

import subprocess
import threading
import random
import time

# Try to import audio libraries
try:
    import pyaudio
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("[BABBLE] pyaudio/numpy not available — using simple babble sounds")


# Babble fades as the AI has more interactions
# Below this = mostly babble, above = mostly words
BABBLE_INTERACTION_THRESHOLD = 30
BABBLE_FULL_FADE_THRESHOLD   = 80


def get_babble_level(total_interactions, talkativeness):
    """
    Returns 0.0 (no babble) to 1.0 (full babble)
    based on how many interactions it's had.
    """
    if total_interactions < BABBLE_INTERACTION_THRESHOLD:
        return 1.0
    elif total_interactions < BABBLE_FULL_FADE_THRESHOLD:
        progress = (total_interactions - BABBLE_INTERACTION_THRESHOLD) / (
            BABBLE_FULL_FADE_THRESHOLD - BABBLE_INTERACTION_THRESHOLD
        )
        return round(1.0 - progress, 2)
    return 0.0


def _analyze_voice_simple():
    """
    Simple voice analysis without pyaudio.
    Returns approximate pitch and rhythm values.
    """
    if not AUDIO_AVAILABLE:
        return {"pitch": random.uniform(100, 300), "rhythm": random.uniform(0.3, 0.8)}

    p      = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1,
                    rate=16000, input=True, frames_per_buffer=1024)

    frames = []
    for _ in range(20):  # ~1.25 seconds of audio
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(np.frombuffer(data, dtype=np.int16))

    stream.stop_stream()
    stream.close()
    p.terminate()

    audio = np.concatenate(frames).astype(np.float32)

    # Estimate dominant frequency via zero crossings
    zero_crossings = np.where(np.diff(np.sign(audio)))[0]
    if len(zero_crossings) > 1:
        avg_period = np.mean(np.diff(zero_crossings))
        pitch = 16000 / (2 * avg_period) if avg_period > 0 else 150
        pitch = max(80, min(500, pitch))
    else:
        pitch = 150

    # Rhythm: variance in loudness segments
    segments = np.abs(audio).reshape(-1, 512).mean(axis=1)
    rhythm = float(np.std(segments) / (np.mean(segments) + 1e-5))
    rhythm = max(0.1, min(1.0, rhythm))

    return {"pitch": pitch, "rhythm": rhythm}


def _generate_babble_sound(pitch, rhythm, duration_ms=800, emotion="neutral"):
    """
    Generate babble text for TTS that mimics the given pitch/rhythm.
    This is the 'robot equivalent of baby babbling'.
    """
    # Map pitch to vowel sounds (higher pitch = brighter vowels)
    if pitch > 250:
        vowels = ["eee", "iii", "aaa"]
    elif pitch > 150:
        vowels = ["aah", "ooh", "mmm"]
    else:
        vowels = ["ohh", "umm", "mmm"]

    # Map rhythm to repetition pattern
    if rhythm > 0.6:
        pattern = lambda v: f"{v}-{v}-{v}"   # staccato
    elif rhythm > 0.3:
        pattern = lambda v: f"{v}... {v}"    # moderate
    else:
        pattern = lambda v: f"{v}..."         # slow/drawn out

    # Emotion colors the babble
    if emotion == "hunger":
        base = random.choice(["mmm", "uhh", "ohh"])
    elif emotion == "curiosity":
        base = random.choice(["ooh", "aah", "hmm"])
    elif emotion == "excitement":
        base = random.choice(vowels)
    elif emotion == "anxiety":
        base = random.choice(["uhh", "mmm", "ohh"])
    else:
        base = random.choice(vowels)

    return pattern(base)


def babble_response(total_interactions, dominant_emotion, talkativeness, voice_input=False):
    """
    Main babble function.
    Call this instead of LLM think() during early life.

    voice_input: True if human just spoke (triggers mimicry)
    Returns: babble text to speak, or None if should use real language
    """
    babble_level = get_babble_level(total_interactions, talkativeness)

    if babble_level < 0.1:
        return None  # past babbling stage, use real language

    # Decide: babble or try real language
    if random.random() > babble_level:
        return None  # this moment, using real language

    if voice_input and AUDIO_AVAILABLE:
        # Try to mimic the voice we just heard
        try:
            voice = _analyze_voice_simple()
            text  = _generate_babble_sound(
                pitch=voice["pitch"],
                rhythm=voice["rhythm"],
                emotion=dominant_emotion
            )
        except Exception:
            text = _generate_babble_sound(150, 0.4, emotion=dominant_emotion)
    else:
        # Spontaneous babble
        text = _generate_babble_sound(
            pitch=random.uniform(100, 300),
            rhythm=random.uniform(0.2, 0.7),
            emotion=dominant_emotion
        )

    return text


def install_instructions():
    return (
        "To enable vocal mimicry, install:\n"
        "  pip install pyaudio numpy\n"
        "On Mac you may also need:\n"
        "  brew install portaudio\n"
        "  pip install pyaudio"
    )
