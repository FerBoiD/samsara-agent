# ============================================================
#  WHISPER INPUT — Local Speech Recognition
#
#  Listens to your microphone, converts speech to text.
#  Runs entirely on your Mac — no API cost, no internet needed.
#
#  Install:
#    pip install openai-whisper pyaudio numpy
#    brew install portaudio   (if pyaudio fails)
#
#  Two modes:
#  1. Push-to-talk: call listen_once() when you want to speak
#  2. Continuous:   runs in background, pushes to queue
# ============================================================

import threading
import queue
import time
import os
import tempfile

# Try imports — graceful fallback if not installed
try:
    import whisper
    import pyaudio
    import numpy as np
    import wave
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[WHISPER] Not available — install with: pip install openai-whisper pyaudio numpy")
    print("[WHISPER] Falling back to Telegram text input only")

# Audio settings
SAMPLE_RATE    = 16000
CHANNELS       = 1
CHUNK          = 1024
SILENCE_THRESH = 500      # RMS below this = silence
SILENCE_SECS   = 1.5      # seconds of silence before stopping recording
MAX_RECORD_SECS= 15       # max recording length

# Whisper model — "tiny" is fastest, "base" is more accurate
# tiny: ~40MB, base: ~150MB, small: ~500MB
WHISPER_MODEL  = "base"

_model         = None
_speech_queue  = queue.Queue()
_listening     = False
_listen_thread = None


def _load_model():
    global _model
    if _model is None and WHISPER_AVAILABLE:
        print(f"[WHISPER] Loading {WHISPER_MODEL} model...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("[WHISPER] Model ready.")
    return _model


def _rms(data):
    """Calculate RMS volume of audio chunk."""
    if not WHISPER_AVAILABLE:
        return 0
    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(arr ** 2)))


def _record_until_silence():
    """
    Record from microphone until silence detected.
    Returns: audio data as bytes, or None if nothing captured.
    """
    if not WHISPER_AVAILABLE:
        return None

    p      = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames        = []
    silent_chunks = 0
    speaking      = False
    max_chunks    = int(SAMPLE_RATE / CHUNK * MAX_RECORD_SECS)
    silence_limit = int(SAMPLE_RATE / CHUNK * SILENCE_SECS)

    for _ in range(max_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        rms = _rms(data)

        if rms > SILENCE_THRESH:
            speaking = True
            silent_chunks = 0
        elif speaking:
            silent_chunks += 1
            if silent_chunks > silence_limit:
                break  # enough silence after speech

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not speaking or len(frames) < 5:
        return None

    return b"".join(frames)


def _transcribe(audio_bytes):
    """Transcribe audio bytes using Whisper."""
    if not WHISPER_AVAILABLE or not audio_bytes:
        return None

    model = _load_model()
    if model is None:
        return None

    # Write to temp wav file (Whisper needs a file)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write WAV file
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)

        # Transcribe
        result = model.transcribe(tmp_path, language="en", fp16=False)
        text   = result["text"].strip()
        return text if text else None

    except Exception as e:
        print(f"[WHISPER] Transcription error: {e}")
        return None
    finally:
        try: os.unlink(tmp_path)
        except: pass


def listen_once(timeout=10):
    """
    Listen for one utterance and return the text.
    Blocking call — waits for speech then silence.
    Returns: transcribed text or None
    """
    if not WHISPER_AVAILABLE:
        return None

    print("[WHISPER] Listening... (speak now)")
    audio = _record_until_silence()
    if audio is None:
        print("[WHISPER] No speech detected")
        return None

    text = _transcribe(audio)
    if text:
        print(f"[WHISPER] Heard: {text}")
    return text


def _continuous_listen_loop():
    """Background thread — continuously listens and pushes to queue."""
    global _listening
    _load_model()

    print("[WHISPER] Continuous listening started. Speak to send messages.")
    while _listening:
        try:
            audio = _record_until_silence()
            if audio:
                text = _transcribe(audio)
                if text and len(text) > 2:
                    print(f"[WHISPER] → {text}")
                    _speech_queue.put({"type": "message", "text": text})
        except Exception as e:
            print(f"[WHISPER] Listen error: {e}")
            time.sleep(1)


def start_continuous():
    """
    Start background listening thread.
    Transcribed speech appears in get_speech_input().
    """
    global _listening, _listen_thread

    if not WHISPER_AVAILABLE:
        print("[WHISPER] Not available — voice input disabled")
        return False

    _listening    = True
    _listen_thread= threading.Thread(target=_continuous_listen_loop, daemon=True)
    _listen_thread.start()
    return True


def stop_continuous():
    global _listening
    _listening = False


def get_speech_input():
    """
    Returns next transcribed speech from queue, or None.
    Same interface as telegram_bot.get_incoming() —
    main.py checks both and merges them.
    """
    try:
        return _speech_queue.get_nowait()
    except queue.Empty:
        return None


def is_available():
    return WHISPER_AVAILABLE


# ============================================================
#  VOICE ANALYSIS — for babble mimicry
# ============================================================

def analyze_voice_for_babble(audio_bytes=None):
    """
    Analyze recent speech for pitch and rhythm.
    Used by babble.py for vocal mimicry.
    Returns dict with pitch and rhythm values.
    """
    if not WHISPER_AVAILABLE or not audio_bytes:
        return {"pitch": 150, "rhythm": 0.4}

    try:
        arr = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

        # Zero-crossing rate → pitch estimate
        zero_crossings = np.where(np.diff(np.sign(arr)))[0]
        if len(zero_crossings) > 1:
            avg_period = np.mean(np.diff(zero_crossings))
            pitch = SAMPLE_RATE / (2 * avg_period) if avg_period > 0 else 150
            pitch = max(80, min(500, pitch))
        else:
            pitch = 150

        # Volume variance → rhythm estimate
        segment_size = 512
        segments = np.abs(arr).reshape(-1, segment_size).mean(axis=1) \
                   if len(arr) >= segment_size else np.array([1.0])
        mean_vol = segments.mean()
        rhythm   = float(segments.std() / (mean_vol + 1e-5))
        rhythm   = max(0.1, min(1.0, rhythm))

        return {"pitch": float(pitch), "rhythm": rhythm}

    except Exception as e:
        print(f"[WHISPER] Voice analysis error: {e}")
        return {"pitch": 150, "rhythm": 0.4}
