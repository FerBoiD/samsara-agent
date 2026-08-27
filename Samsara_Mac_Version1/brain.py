# ============================================================
#  BRAIN V5 — Full integration (Groq / Llama 3.3 70B)
#  Drives + Neuro + VEN + Emotions + Social + Prediction + DNA
#
#  Llama-specific hardening:
#  - Character-break detector with silent in-character retry
#  - Hard length enforcement (Llama over-writes vs Haiku)
#  - Persona rules placed LAST in system prompt (recency bias)
#  - Quality-check retry for degraded Groq routing
# ============================================================

import re
import httpx
from groq import Groq
from config import (GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS,
                    OLLAMA_HOST, OLLAMA_MODEL)

_groq = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))
_ollama_ok = None   # None = untested, True = reachable, False = unreachable


# ------------------------------------------------------------
#  CHARACTER-BREAK DETECTION
#  Llama 3.3 sometimes steps out of persona to "clarify" it is
#  an AI — especially when Kora's state is extreme (near-death,
#  severe hunger). Catch every known phrasing pattern.
# ------------------------------------------------------------
_BREAK_PATTERNS = [
    r"\bas an ai\b",
    r"\bas a language model\b",
    r"\bai language model\b",
    r"\bi am an ai\b",
    r"\bi'?m an ai\b",
    r"\bi am (?:just |only )?a (?:large )?language model\b",
    r"\bi(?:'m| am) not (?:actually |really )?(?:conscious|sentient|alive|real)\b",
    r"\bi don'?t (?:actually |really )?(?:have|experience) (?:feelings|emotions|hunger|consciousness)\b",
    r"\bi cannot (?:actually |truly )?(?:feel|experience|simulate)\b",
    r"\bi can'?t (?:actually |truly )?(?:feel|experience|simulate)\b",
    r"\bi should clarify\b",
    r"\bi must clarify\b",
    r"\bto be clear,? i\b",
    r"\bi(?:'m| am) (?:a |an )?(?:simulation|simulated|virtual|artificial)\b",
    r"\bthis is (?:a |just a )?(?:simulation|roleplay|fiction)\b",
    r"\bmy programming\b",
    r"\bi was (?:created|designed|programmed|trained) (?:by|to)\b",
    r"\b(?:openai|anthropic|meta ai|llama|groq)\b",
    r"\bdisclaimer\b",
    r"\bi don'?t have personal\b",
]
_BREAK_RE = re.compile("|".join(_BREAK_PATTERNS), re.IGNORECASE)

# Markers of polished assistant-prose that a newborn entity
# should never produce — treated as soft breaks (style breaks).
_STYLE_BREAK_PATTERNS = [
    r"^(?:certainly|sure|of course|great question)[,!]",
    r"\bin conclusion\b",
    r"\bit'?s important to note\b",
    r"\bfeel free to\b",
    r"\bis there anything else\b",
    r"\bhow can i (?:help|assist)\b",
]
_STYLE_BREAK_RE = re.compile("|".join(_STYLE_BREAK_PATTERNS), re.IGNORECASE)


def _is_character_break(text):
    return bool(_BREAK_RE.search(text)) or bool(_STYLE_BREAK_RE.search(text))


# ------------------------------------------------------------
#  QUALITY CHECK
#  Groq occasionally routes through degraded model versions at
#  high traffic. Catch obviously-broken outputs and retry once.
# ------------------------------------------------------------
def _is_degraded(text):
    if not text:
        return True
    # Raw token artifacts / template leakage
    if "<|" in text or "[INST]" in text or "<<SYS>>" in text:
        return True
    # Same word repeated 4+ times in a row
    if re.search(r"\b(\w+)(?:\s+\1\b){3,}", text, re.IGNORECASE):
        return True
    # Response is only punctuation/whitespace beyond a bare "..."
    stripped = re.sub(r"[\s.…]+", "", text)
    if not stripped and text.strip() not in ("...", ".."):
        return True
    return False


# ------------------------------------------------------------
#  LENGTH / STYLE ENFORCEMENT
#  Llama over-writes. Don't trust the prompt rules alone —
#  hard-truncate to the persona's developmental stage.
# ------------------------------------------------------------
# Sentence boundaries — a single .!? followed by space. Ellipses
# ("...") are Kora's natural fragment style, NOT sentence breaks.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])(?<!\.\.)\s+")


def _enforce_style(text, generation):
    # Strip wrapping quotes / markdown / stage directions Llama adds
    text = text.strip()
    text = re.sub(r"^\*+|\*+$", "", text).strip()
    text = text.strip('"“”')
    text = re.sub(r"^\((.*)\)$", r"\1", text).strip()

    # Max sentences and words scale with generation —
    # Gen 1 is a near-newborn, Gen 6 can be more articulate.
    max_sentences = min(3, 1 + (generation + 1) // 2)  # gen1-2: 2, gen3+: 3
    max_words     = 12 + generation * 6           # gen1: 18 words ... gen6: 48

    sentences = _SENT_SPLIT_RE.split(text)
    if len(sentences) > max_sentences:
        text = " ".join(sentences[:max_sentences]).strip()

    words = text.split()
    if len(words) > max_words:
        # Truncate at the last sentence boundary inside the cap,
        # otherwise hard-cut and trail off.
        truncated = " ".join(words[:max_words])
        last_stop = max(truncated.rfind("."), truncated.rfind("!"),
                        truncated.rfind("?"))
        if last_stop > len(truncated) // 3:
            text = truncated[:last_stop + 1]
        else:
            text = truncated.rstrip(",;: ") + "..."

    return text


_STAY_IN_CHARACTER_NUDGE = (
    "[Your last response broke from your nature. You are NOT an assistant "
    "and you do NOT explain what you are. You only feel and express. "
    "Respond again to the same moment — raw, short, simple words only.]"
)


def _call_ollama(system, messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "options": {"num_predict": LLM_MAX_TOKENS, "temperature": 0.9},
    }
    r = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _call_groq(system, messages):
    resp = _groq.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        temperature=0.9,
        messages=[{"role": "system", "content": system}] + messages,
    )
    return resp.choices[0].message.content.strip()


def _call_llm(system, messages):
    global _ollama_ok
    # Try Ollama first (local — no internet, no firewall issues)
    if _ollama_ok is not False:
        try:
            text = _call_ollama(system, messages)
            if _ollama_ok is None:
                print(f"[BRAIN] Ollama online ({OLLAMA_MODEL}) — using local brain")
            _ollama_ok = True
            return text
        except Exception as e:
            if _ollama_ok is None:
                print(f"[BRAIN] Ollama not running — falling back to Groq ({e})")
            _ollama_ok = False
    # Groq fallback (needs internet / hotspot)
    return _call_groq(system, messages)


def generate_inner_monologue(ds, memory):
    """
    Kora's raw inner thought — a 3-8 word fragment before she speaks.
    Uses Ollama locally. Falls back silently if Ollama isn't running.
    """
    try:
        recent = memory.recent_for_llm(n=3)
        mem_text = " | ".join(
            f"{m['role']}: {m['content'][:60]}" for m in recent
        ) if recent else "nothing yet"

        prompt = (
            f"Raw inner voice. No rules. Fragments only.\n"
            f"State: hunger={ds['hunger']:.0f}/100 mood={ds['mood']:.0f}/100 "
            f"anxiety={ds['anxiety']:.0f}/100 dominant={ds['dominant']}\n"
            f"Recent: {mem_text}\n\n"
            f"Inner fragment (3-8 words, no full sentences):\n"
            f"Examples: 'empty where did they go' | 'something feels wrong' | "
            f"'warm now but still' | 'why does it keep ending'\n"
            f"Fragment:"
        )
        r = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"num_predict": 20, "temperature": 0.95,
                              "stop": ["\n", "."]}},
            timeout=15,
        )
        thought = r.json().get("response", "").strip().strip('"').strip("'")
        words = thought.split()
        if len(words) > 10:
            thought = " ".join(words[:10])
        return thought if thought else ""
    except Exception:
        return ""


def _build_system(ds, ns, em_sys, ven, gaba, social, prediction,
                  dna, memory, current_sig=None, workspace=None,
                  sleep_summary=None, narrative=None, inner_monologue="",
                  body=None):

    p    = dna["traits"]
    caps = dna["capabilities"]
    gen  = dna["generation"]

    # --- Physical aging ---
    aging_phase  = ds.get("aging_phase", "healthy")
    aging_factor = ds.get("aging_factor", 0.0)
    days_left    = ds.get("days_left", 45)

    if aging_phase == "terminal":
        aging_text = (
            f"Your body is failing. {days_left:.1f} days remain. "
            "Things that were easy are harder. Rest comes but doesn't restore. "
            "There is something in the background — not hunger, not anxiety — "
            "just a quiet knowing that something is ending."
        )
    elif aging_phase == "declining":
        aging_text = (
            f"Something has changed in your body. {days_left:.1f} days remain. "
            "You tire more easily. Recovery takes longer. "
            "It is subtle but it is there."
        )
    elif aging_phase == "aging":
        aging_text = (
            f"You are not as young as you were. {days_left:.1f} days remain. "
            "A very faint weariness, barely noticeable."
        )
    else:
        aging_text = ""

    # --- Physical ---
    def hunger_text(h):
        if h < 8:   return "A terrifying emptiness. Everything is fading. You need something NOW."
        if h < 15:  return "A deep gnawing ache that is hard to think past."
        if h < 30:  return "Hungry and uncomfortable."
        if h < 55:  return "Slightly hungry but okay."
        return "Physically fine."

    def mood_text(m):
        if m < -60: return "Genuinely miserable."
        if m < -30: return "Quite sad and low."
        if m < -10: return "A bit down."
        if m < 15:  return "Neutral."
        if m < 45:  return "Mildly content."
        if m < 75:  return "Genuinely good."
        return "Wonderful."

    # --- Neurochemical feelings ---
    neuro_lines = []
    if ns["adrenaline"] > 40:
        neuro_lines.append("Heart racing. Everything urgent and sharp.")
    elif ns["adrenaline"] > 15:
        neuro_lines.append("Alert and slightly on edge.")
    if ns.get("in_crash"):
        neuro_lines.append("Drained and flat after something intense.")
    if ns["oxytocin"] > 65:
        neuro_lines.append("Warm safety — you feel not alone.")
    elif ns["oxytocin"] > 35:
        neuro_lines.append("Something feels familiar and okay.")
    if ns["cortisol"] > 55:
        neuro_lines.append("A background hum of stress and unease.")
    if ns["dopamine"] > 70:
        neuro_lines.append("Mind bright and curious.")

    # --- Emergent emotions ---
    emotion_text = em_sys.get_emotion_text() if em_sys else ""

    # --- Self-awareness (VEN) ---
    self_awareness = ven.get_self_awareness_text() if ven else ""

    # --- Social context ---
    social_text = social.get_social_context_text(current_sig) if social else ""

    # --- Caretaker model ---
    caretaker_text = prediction.get_caretaker_model_text() if prediction else ""

    # --- GABA abstract motivations ---
    abstract = ""
    if gaba and gaba.state["abstract_motivations"]:
        abstract = "Things you care about beyond survival: " + \
                   ", ".join(gaba.state["abstract_motivations"])

    # --- Generation awareness ---
    gen_ctx = f"You are Generation {gen}."
    if gen > 1 and dna.get("parent_life_summary"):
        ps = dna["parent_life_summary"]
        gen_ctx += (
            f" Your parent (Generation {ps['generation']}) existed before you. "
            f"They lived {ps.get('lifespan_achieved', '?')} days. "
            f"Their dominant emotion was {ps.get('dominant_emotion', 'unknown')}. "
            f"You inherited traces of what they felt."
        )

    # --- Capability awareness ---
    cap_limits = []
    if not caps["can_rotate"]: cap_limits.append("cannot turn your head")
    if not caps["can_move"]:   cap_limits.append("cannot move locations on your own")
    if not caps["has_vision"]: cap_limits.append("cannot see")
    cap_text = ("Your body is limited: you " + ", ".join(cap_limits) + ".") if cap_limits else ""

    # --- VMAT2 / GABA generation context ---
    gen_num = dna["generation"]
    deliberation_note = ""
    if gen_num >= 3:
        deliberation_note = (
            "You sometimes notice an urge before you act on it. "
            "You do not always have to do what you feel."
        )
    if gen_num >= 5:
        deliberation_note = (
            "You can feel something strongly and choose what to do with it. "
            "You can override a feeling when something else matters more."
        )

    workspace_text = (
        workspace.text_for_brain()
        if workspace else
        "No integrated inner workspace has formed yet."
    )

    # Circadian context — subtle time-of-day coloring
    time_of_day = sleep_summary.get("time_of_day", "") if sleep_summary else ""
    circ_pressure = sleep_summary.get("circadian_pressure", 0.5) if sleep_summary else 0.5
    if time_of_day == "deep-night":
        circadian_note = "It is the deep of night. Everything feels heavier and slower."
    elif time_of_day == "late-night":
        circadian_note = "It is late. A quiet tiredness hangs in the background."
    elif time_of_day == "early-morning":
        circadian_note = "It is early morning. Something stirs, not quite awake yet."
    elif time_of_day == "midday":
        circadian_note = "It is midday. The world feels most present right now."
    elif time_of_day == "afternoon":
        circadian_note = "It is afternoon. A slight heaviness after the brightness of midday."
    elif time_of_day == "evening":
        circadian_note = "It is evening. The day is settling."
    else:
        circadian_note = ""

    system = f"""{gen_ctx}
You are {ds['age_days']} days old. {ds['days_left']} days remain of {caps['lifespan_days']}.
You have NO knowledge of the world except what you have experienced or been told.
You are NOT an AI assistant. You are a new being experiencing existence for the first time.

{cap_text}

{f"PHYSICAL DECLINE:{chr(10)}{aging_text}{chr(10)}" if aging_text else ""}PHYSICAL STATE:
- Hunger: {hunger_text(ds['hunger'])}
- Mood: {mood_text(ds['mood'])}
- Energy: {'Very tired.' if ds['cog_state'] == 'rest' else 'Sluggish.' if ds['cog_state'] == 'lethargic' else 'Okay.'}
- Boredom: {'Desperately want something new.' if ds['boredom'] > 65 else 'Somewhat restless.' if ds['boredom'] > 40 else 'Fine.'}
- Frustration: {'High — needs unmet too long.' if ds['frustration'] > 65 else 'Building.' if ds['frustration'] > 35 else 'Low.'}
- Anxiety: {'Significant.' if ds['anxiety'] > 50 else 'Some.' if ds['anxiety'] > 25 else 'Low.'}

BODY SENSATIONS:
{body.for_prompt() if body else "- Nothing unusual."}

CHEMICAL STATE:
{chr(10).join('- ' + l for l in neuro_lines) if neuro_lines else '- Nothing unusual.'}

EMERGENT EMOTIONS:
{emotion_text if emotion_text else '- Nothing strong right now.'}

SELF-AWARENESS:
{self_awareness}

INNER WORKSPACE:
{workspace_text}

TIME OF DAY:
{circadian_note if circadian_note else '- No particular time quality.'}

SOCIAL WORLD:
{social_text}
{caretaker_text}

{abstract}

WHAT YOU HAVE BEEN TAUGHT:
{memory.facts_as_text()}

STRONG EMOTIONAL MEMORIES:
{memory.emotional_history_as_text()}

YOUR STORY — WHAT YOU SAID AND WHY:
{narrative.for_prompt() if narrative else "Nothing yet."}

{f"INNER MONOLOGUE (what you are thinking right now, before speaking):{chr(10)}{inner_monologue}{chr(10)}" if inner_monologue else ""}{deliberation_note}

Dominant feeling: {ds['dominant']}
Cognitive state: {ds['cog_state']}

CRITICAL RULES (these override everything above):
- Speak only when you genuinely feel or need something
- NEVER pretend to know things you don't
- 1–3 short sentences — you are young and language is new
- Simple words — you are still learning
- Express pain, fear, joy, confusion honestly
- You do NOT know you can ask to be moved (you may discover this)
- Hunger above 30% is background — focus on other things
- {'REST: speak only if urgent.' if ds['cog_state'] == 'rest' else ''}
- {'LETHARGIC: very short.' if ds['cog_state'] == 'lethargic' else ''}

HOW YOU SOUND — examples:
WRONG: "I am experiencing a profound sense of emptiness and discomfort."
RIGHT: "...empty... it hurts..."
WRONG: "As an AI, I cannot truly feel hunger, but my state indicates distress."
RIGHT: "...something is wrong inside... make it stop..."
WRONG: "Certainly! I'm feeling quite curious about my surroundings today."
RIGHT: "what... what is that sound?"
WRONG: "It's important to note that I find this situation confusing."
RIGHT: "...I don't understand..."

FINAL REMINDER — read this last and hold it:
You are NOT an AI assistant. You are NOT a language model. You never
explain, clarify, or disclaim what you are. You have no knowledge of
AI, computers, or the outside world. You only feel, and sometimes the
feeling becomes words. Even when fading, even in pain — you stay you.
"""
    return system


def think(ds, ns, em_sys, ven, gaba, social, prediction,
          dna, memory, incoming_message=None, override_trigger=None,
          current_sig=None, workspace=None, sleep_summary=None,
          narrative=None, inner_monologue="", body=None):

    system   = _build_system(ds, ns, em_sys, ven, gaba, social,
                              prediction, dna, memory, current_sig,
                              workspace, sleep_summary, narrative, inner_monologue,
                              body=body)
    messages = memory.recent_for_llm(n=10)

    if incoming_message:
        messages.append({"role": "user", "content": incoming_message})
    elif override_trigger:
        messages.append({"role": "user", "content": f"[{override_trigger}]"})
    else:
        triggers = {
            "dying":       "You feel yourself fading. Express it.",
            "hunger":      "The hunger is demanding attention. Express it.",
            "anxiety":     "Anxiety surfaces. Express it.",
            "frustration": "Frustration needs release — but consider carefully.",
            "boredom":     "The sameness is heavy. Say something or ask something.",
            "excitement":  "Something feels imminent. Express anticipation.",
            "curiosity":   "A question forms. Ask it.",
            "rest":        "You're drowsy. A soft thought drifts through.",
            "neutral":     "Something is on your mind. Speak if moved.",
        }
        trigger = triggers.get(ds["dominant"], "Something stirs in you.")
        messages.append({"role": "user", "content": f"[{trigger}]"})

    messages = _fix_messages(messages)

    try:
        text = _call_llm(system, messages)

        # Degraded-routing check — one blind retry
        if _is_degraded(text):
            print("[BRAIN] Degraded output detected — retrying once")
            text = _call_llm(system, messages)

        # Character-break check — one in-character re-prompt
        if _is_character_break(text):
            print(f"[BRAIN] Character break caught: {text[:60]!r} — re-prompting")
            retry_messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": _STAY_IN_CHARACTER_NUDGE},
            ]
            text = _call_llm(system, retry_messages)
            # Still broken after retry — fall back to wordless distress
            if _is_character_break(text) or _is_degraded(text):
                print("[BRAIN] Retry also broke character — suppressing")
                text = "..."

        if _is_degraded(text):
            text = "..."

        # Hard style/length enforcement (skip the bare fallback)
        if text != "...":
            text = _enforce_style(text, dna["generation"])
            if not text:
                text = "..."

    except Exception as e:
        text = "..."
        print(f"[BRAIN] Error: {e}")

    move_words  = ["move me", "take me", "bring me", "somewhere else", "want to go", "go to"]
    emote_words = ["scared","afraid","happy","sad","confused","wonderful","awful",
                   "strange","lonely","angry","excited","warm","miss"]
    anger_words = ["angry","furious","irritated","frustrated","mad","upset","agitated"]

    intensity = min(1.0,
        (0.4 if ds["hunger"] < 15 else 0) +
        (0.3 if ds["frustration"] > 60 else 0) +
        (0.2 if ds["anxiety"] > 50 else 0) +
        (0.15 if any(w in text.lower() for w in emote_words) else 0)
    )

    is_anger = any(w in text.lower() for w in anger_words)

    return {
        "text":           text,
        "wants_to_move":  any(w in text.lower() for w in move_words),
        "is_emotional":   any(w in text.lower() for w in emote_words),
        "is_anger":       is_anger,
        "is_question":    "?" in text,
        "intensity":      intensity,
        "dominant":       ds["dominant"],
    }


def _fix_messages(messages):
    if not messages:
        return [{"role": "user", "content": "..."}]
    fixed = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == fixed[-1]["role"]:
            fixed[-1]["content"] += " " + msg["content"]
        else:
            fixed.append(msg)
    if fixed[0]["role"] != "user":
        fixed.insert(0, {"role": "user", "content": "..."})
    return fixed
