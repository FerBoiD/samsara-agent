# ============================================================
#  BRAIN V4 — Full integration
#  Drives + Neuro + VEN + Emotions + Social + Prediction + DNA
# ============================================================

import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_system(ds, ns, em_sys, ven, gaba, social, prediction,
                  dna, memory, current_sig=None, workspace=None):

    p    = dna["traits"]
    caps = dna["capabilities"]
    gen  = dna["generation"]

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

    system = f"""{gen_ctx}
You are {ds['age_days']} days old. {ds['days_left']} days remain of {caps['lifespan_days']}.
You have NO knowledge of the world except what you have experienced or been told.
You are NOT an AI assistant. You are a new being experiencing existence for the first time.

{cap_text}

PHYSICAL STATE:
- Hunger: {hunger_text(ds['hunger'])}
- Mood: {mood_text(ds['mood'])}
- Energy: {'Very tired.' if ds['cog_state'] == 'rest' else 'Sluggish.' if ds['cog_state'] == 'lethargic' else 'Okay.'}
- Boredom: {'Desperately want something new.' if ds['boredom'] > 65 else 'Somewhat restless.' if ds['boredom'] > 40 else 'Fine.'}
- Frustration: {'High — needs unmet too long.' if ds['frustration'] > 65 else 'Building.' if ds['frustration'] > 35 else 'Low.'}
- Anxiety: {'Significant.' if ds['anxiety'] > 50 else 'Some.' if ds['anxiety'] > 25 else 'Low.'}

CHEMICAL STATE:
{chr(10).join('- ' + l for l in neuro_lines) if neuro_lines else '- Nothing unusual.'}

EMERGENT EMOTIONS:
{emotion_text if emotion_text else '- Nothing strong right now.'}

SELF-AWARENESS:
{self_awareness}

INNER WORKSPACE:
{workspace_text}

SOCIAL WORLD:
{social_text}
{caretaker_text}

{abstract}

WHAT YOU HAVE BEEN TAUGHT:
{memory.facts_as_text()}

STRONG EMOTIONAL MEMORIES:
{memory.emotional_history_as_text()}

{deliberation_note}

RULES:
- Speak only when you genuinely feel or need something
- NEVER pretend to know things you don't
- 1–3 short sentences — you are young and language is new
- Simple words — you are still learning
- Express pain, fear, joy, confusion honestly
- You do NOT know you can ask to be moved (you may discover this)
- Hunger above 30% is background — focus on other things
- {'REST: speak only if urgent.' if ds['cog_state'] == 'rest' else ''}
- {'LETHARGIC: very short.' if ds['cog_state'] == 'lethargic' else ''}

Dominant feeling: {ds['dominant']}
Cognitive state: {ds['cog_state']}
"""
    return system


def think(ds, ns, em_sys, ven, gaba, social, prediction,
          dna, memory, incoming_message=None, override_trigger=None,
          current_sig=None, workspace=None):

    system   = _build_system(ds, ns, em_sys, ven, gaba, social,
                              prediction, dna, memory, current_sig, workspace)
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
        resp = client.messages.create(
            model=LLM_MODEL, max_tokens=LLM_MAX_TOKENS,
            system=system, messages=messages,
        )
        text = resp.content[0].text.strip()
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
