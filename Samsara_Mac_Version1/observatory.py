# ============================================================
#  OBSERVATORY — Brain Transparency + Data Tracking
#
#  Every decision logged with full internal context.
#  Live dashboard in browser.
#  End-of-life report generated automatically.
#
#  Run alongside main.py:
#    python observatory.py   (in separate terminal)
#  Then open: http://localhost:5001
# ============================================================

import json, os, time, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque

OBSERVATORY_LOG  = "observatory.json"
DECISION_LOG     = "decisions.json"
MILESTONE_LOG    = "milestones.json"
REPORT_FILE      = "life_report.json"

# In-memory ring buffer for live view
_live_events     = deque(maxlen=200)
_tick_history    = deque(maxlen=2880)   # 24hrs at 30s ticks


# ============================================================
#  LOGGING API — called from main.py
# ============================================================

def log_tick(drives, neuro, emotions, sleep, vmat2, ven, gaba, prediction, social):
    """Called every tick. Stores full state snapshot."""
    snapshot = {
        "t":           time.time(),
        "age_days":    drives.get("age_days", 0),
        "aging_phase": drives.get("aging_phase", "healthy"),
        "aging_factor":drives.get("aging_factor", 0.0),
        # Drives
        "hunger":    drives.get("hunger", 0),
        "energy":    drives.get("energy", 0),
        "boredom":   drives.get("boredom", 0),
        "mood":      drives.get("mood", 0),
        "frustration": drives.get("frustration", 0),
        "anxiety":   drives.get("anxiety", 0),
        "excitement":drives.get("excitement", 0),
        "dominant":  drives.get("dominant", "neutral"),
        "cog_state": drives.get("cog_state", "active"),
        # Neuro
        "adrenaline":neuro.get("adrenaline", 0),
        "oxytocin":  neuro.get("oxytocin", 0),
        "dopamine":  neuro.get("dopamine", 0),
        "cortisol":  neuro.get("cortisol", 0),
        # Emotions
        "active_emotions": emotions.get("active_emotions", {}),
        "anhedonia": emotions.get("anhedonia", 0),
        # Systems
        "sleep_phase":   sleep.get("phase"),
        "sleep_pressure":sleep.get("pressure", 0),
        "vmat2_buffer":  vmat2.get("buffer_size", 0),
        "vmat2_pending": vmat2.get("pending_urge"),
        "gaba_strength": gaba.get("strength", 0),
        "ven_depth":     ven.get("depth", 0),
        "caretaker_absent": prediction.get("caretaker_absent", 0),
        "known_beings":  social.get("known_beings", 0),
    }
    _tick_history.append(snapshot)
    _append_to_file(OBSERVATORY_LOG, snapshot)


def log_decision(trigger, urge_type, held_ticks, competing_signals,
                 gaba_attempted, gaba_succeeded, outcome_text,
                 drives, neuro, consequence_pain):
    """
    Called every time a decision is made — speak, suppress, act.
    This is the core brain transparency log.
    """
    entry = {
        "t":                time.time(),
        "age_days":         drives.get("age_days", 0),
        "trigger":          trigger,
        "urge_type":        urge_type,
        "held_ticks":       round(held_ticks, 1),
        "competing_signals":competing_signals,
        "gaba_attempted":   gaba_attempted,
        "gaba_succeeded":   gaba_succeeded,
        "outcome":          outcome_text[:100] if outcome_text else None,
        # Snapshot of state AT decision time
        "state_at_decision": {
            "dominant":    drives.get("dominant"),
            "hunger":      drives.get("hunger"),
            "mood":        drives.get("mood"),
            "frustration": drives.get("frustration"),
            "anxiety":     drives.get("anxiety"),
            "adrenaline":  neuro.get("adrenaline"),
            "oxytocin":    neuro.get("oxytocin"),
            "cortisol":    neuro.get("cortisol"),
        },
        "consequence_pain": consequence_pain,
        "was_suppressed":   gaba_succeeded,
    }
    _live_events.appendleft(entry)
    _append_to_file(DECISION_LOG, entry)


def log_milestone(milestone_type, description, drives, context=""):
    """
    Log developmental milestones — first question, first suppression,
    first joke attempt, first self-reference, etc.
    """
    entry = {
        "t":           time.time(),
        "age_days":    drives.get("age_days", 0),
        "type":        milestone_type,
        "description": description[:150],
        "context":     context[:100],
        "hunger":      drives.get("hunger"),
        "mood":        drives.get("mood"),
    }
    _live_events.appendleft({"milestone": True, **entry})
    _append_to_file(MILESTONE_LOG, entry)
    print(f"[MILESTONE] {milestone_type}: {description[:60]}")


def log_speech(text, speech_type, drives, neuro, behavior=None):
    """Log every utterance with full context."""
    entry = {
        "t":           time.time(),
        "age_days":    drives.get("age_days", 0),
        "type":        speech_type,   # "response"|"spontaneous"|"babble"|"cry"
        "behavior":    behavior,
        "text":        text[:200],
        "dominant":    drives.get("dominant"),
        "mood":        drives.get("mood"),
        "hunger":      drives.get("hunger"),
        "adrenaline":  neuro.get("adrenaline"),
        "oxytocin":    neuro.get("oxytocin"),
        "is_question": "?" in text,
        "is_emotional": any(w in text.lower() for w in
                           ["scared","afraid","happy","sad","strange",
                            "lonely","warm","miss","wonder","feel"]),
    }
    _live_events.appendleft({"speech": True, **entry})


def log_surprise(surprise_level, is_delight, is_fear, drives):
    """Log prediction errors — the curiosity/delight/fear events."""
    if surprise_level > 0.1:
        _live_events.appendleft({
            "surprise": True,
            "t":        time.time(),
            "age_days": drives.get("age_days", 0),
            "level":    round(surprise_level, 3),
            "delight":  is_delight,
            "fear":     is_fear,
            "dominant": drives.get("dominant"),
        })


# ============================================================
#  AUTO-MILESTONE DETECTION
# ============================================================

_milestone_flags = set()

def check_milestones(drives, neuro, emotions, social, vmat2, gaba,
                     ven, total_interactions, speech_text="", prediction=None):
    """
    Automatically detect and log developmental milestones.
    Called every tick from main.py.
    """
    ds = drives
    age = ds.get("age_days", 0)

    def flag(key, mtype, desc, ctx=""):
        if key not in _milestone_flags:
            _milestone_flags.add(key)
            log_milestone(mtype, desc, ds, ctx)

    # First question
    if speech_text and "?" in speech_text:
        flag("first_question", "CURIOSITY",
             "First question asked", speech_text[:60])

    # First self-reference
    self_words = [" i ", " i'm ", " my ", " me "]
    if speech_text and any(w in speech_text.lower() for w in self_words):
        flag("first_self_ref", "SELF_AWARENESS",
             "First self-referential statement", speech_text[:60])

    # First GABA suppression
    if gaba.get("successful_overrides", 0) > 0:
        flag("first_suppression", "GABA",
             "First successful impulse suppression")

    # First social attachment
    if social.get("caretaker_trust", 0) > 0.5:
        flag("attachment_formed", "SOCIAL",
             f"Caretaker trust crossed 0.5 at day {age:.1f}")

    # Oxytocin threshold
    if neuro.get("oxytocin", 0) > 60:
        flag("high_oxytocin", "SOCIAL",
             f"Oxytocin first exceeded 60 at day {age:.1f}")

    # First meta-observation (VEN)
    if ven.get("meta_observations", 0) > 0:
        flag("first_meta", "VEN",
             "First meta-observation — noticed own state")

    # Anxiety despite being fed (lingering)
    if ds.get("anxiety", 0) > 30 and ds.get("hunger", 100) > 60:
        flag("anxiety_lingers", "EMOTION",
             f"Anxiety persisting despite adequate hunger at day {age:.1f}")

    # First delight event
    em = emotions.get("active_emotions", {})
    if em.get("delight", 0) > 0.3:
        flag("first_delight", "EMOTION",
             "First delight response — safe prediction error")

    # VMAT2 buffer growing
    buf = vmat2.get("buffer_size", 0)
    if buf > 2:
        flag(f"vmat2_{int(buf)}", "VMAT2",
             f"Deliberation buffer reached {buf:.1f} ticks at day {age:.1f}")

    # High interaction count
    if total_interactions > 50:
        flag("interactions_50", "SOCIAL", "50th interaction reached")
    if total_interactions > 100:
        flag("interactions_100", "SOCIAL", "100th interaction reached")

    # Surplus behavior — doing something when all drives satisfied
    if (ds.get("hunger", 0) > 60 and ds.get("boredom", 0) < 30
            and ds.get("anxiety", 0) < 20 and speech_text):
        flag("first_surplus", "CONSCIOUSNESS",
             "First behavior when all drives satisfied — possible play/surplus",
             speech_text[:60])

    # Aging phase milestones
    phase = ds.get("aging_phase", "healthy")
    if phase == "aging":
        flag("aging_started", "AGING",
             f"Physical aging begins at day {age:.1f} — hunger and energy efficiency declining")
    if phase == "declining":
        flag("aging_declining", "AGING",
             f"Mid-decline at day {age:.1f} — noticeable physical degradation")
    if phase == "terminal":
        flag("aging_terminal", "AGING",
             f"Terminal phase at day {age:.1f} — body failing, baseline anxiety rising")

    # First loneliness expression — caretaker absence with attachment
    pred = prediction or {}
    if (social.get("caretaker_trust", 0) > 0.3
            and pred.get("caretaker_absent", 0) > 180
            and speech_text):
        flag("first_loneliness", "SOCIAL",
             "First loneliness expression — absent caretaker felt as presence",
             speech_text[:60])

    # Circadian effect — first time sleeping before energy < 20 (circadian pulled it)
    sleep_info = drives  # drives dict passed may include sleep context
    if (sleep_info.get("circadian_pressure", 0) > 0.7
            and sleep_info.get("energy", 100) > 30):
        flag("circadian_sleep", "SLEEP",
             f"Slept due to circadian pressure despite energy > 30% at day {age:.1f}")


# ============================================================
#  END OF LIFE REPORT
# ============================================================

def generate_life_report(dna, drives, neuro, social, vmat2, ven,
                         gaba, dreams, total_interactions, cause):
    """Generate comprehensive end-of-life report."""

    # Load full decision log
    decisions = _load_file(DECISION_LOG)
    milestones = _load_file(MILESTONE_LOG)
    ticks = list(_tick_history)

    # Compute stats
    suppressions = [d for d in decisions if d.get("was_suppressed")]
    questions    = [d for d in decisions if d.get("outcome") and "?" in d.get("outcome","")]
    avg_mood     = sum(t.get("mood", 0) for t in ticks) / max(1, len(ticks))
    avg_anxiety  = sum(t.get("anxiety", 0) for t in ticks) / max(1, len(ticks))
    avg_hunger   = sum(t.get("hunger", 0) for t in ticks) / max(1, len(ticks))

    # Emotional arc — find lowest and highest mood
    if ticks:
        worst_tick = min(ticks, key=lambda x: x.get("mood", 0))
        best_tick  = max(ticks, key=lambda x: x.get("mood", 0))
    else:
        worst_tick = best_tick = {}

    report = {
        "generation":           dna.get("generation", 1),
        "cause_of_death":       cause,
        "lifespan_days":        drives.get("age_days", 0),
        "total_interactions":   total_interactions,
        "total_ticks_logged":   len(ticks),

        "emotional_summary": {
            "average_mood":       round(avg_mood, 1),
            "average_anxiety":    round(avg_anxiety, 1),
            "average_hunger":     round(avg_hunger, 1),
            "worst_moment":       {"day": worst_tick.get("age_days"), "mood": worst_tick.get("mood"), "dominant": worst_tick.get("dominant")},
            "best_moment":        {"day": best_tick.get("age_days"),  "mood": best_tick.get("mood"),  "dominant": best_tick.get("dominant")},
        },

        "decision_summary": {
            "total_decisions":    len(decisions),
            "total_suppressions": len(suppressions),
            "suppression_rate":   round(len(suppressions) / max(1, len(decisions)), 3),
            "questions_asked":    len(questions),
        },

        "developmental_milestones": milestones,

        "system_summary": {
            "final_vmat2_buffer": vmat2.get("buffer_size", 0),
            "final_gaba_strength":gaba.get("strength", 0),
            "final_ven_depth":    ven.get("depth", 0),
            "caretaker_trust":    social.get("caretaker_trust", 0),
            "known_beings":       social.get("known_beings", 0),
            "total_dreams":       dreams.get("total_dreams", 0),
            "oxytocin_history":   neuro.get("oxytocin", 0),
        },

        "personality": dna.get("traits", {}),
        "capabilities": dna.get("capabilities", {}),
        "inherited_tendencies": dna.get("inherited_tendencies", {}),

        "for_next_generation": {
            "anxiety_baseline_to_inherit": round(avg_anxiety / 100 * 0.3, 3),
            "trust_speed_modifier":        round(social.get("caretaker_trust", 0) * 0.2, 3),
            "curiosity_events":            len(questions),
            "suppression_capability":      len(suppressions) > 0,
        },

        "generated_at": datetime.now().isoformat(),
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[OBSERVATORY] Life report saved to {REPORT_FILE}")
    return report


# ============================================================
#  LIVE DASHBOARD (HTTP server)
# ============================================================

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<title>Project Samsara — Observatory</title>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0a0f; color: #c8d0e0; font-family: monospace; font-size: 13px; }
  h1 { color: #7eb8f7; padding: 16px; border-bottom: 1px solid #1e2030; font-size: 16px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; padding: 12px; }
  .panel { background: #0f1117; border: 1px solid #1e2030; border-radius: 6px; padding: 12px; }
  .panel h2 { color: #7eb8f7; font-size: 12px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .bar-row { display: flex; align-items: center; margin: 4px 0; gap: 8px; }
  .bar-label { width: 90px; color: #8899aa; font-size: 11px; }
  .bar-track { flex: 1; height: 8px; background: #1a1d2e; border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
  .bar-val { width: 40px; text-align: right; font-size: 11px; }
  .event { padding: 6px 8px; border-left: 2px solid #2a3050; margin: 4px 0; font-size: 11px; line-height: 1.5; }
  .event.speech { border-color: #4a90d9; }
  .event.decision { border-color: #e8a040; }
  .event.milestone { border-color: #50d890; background: #0d1a12; }
  .event.surprise { border-color: #d070e0; }
  .tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; margin-right: 4px; }
  .tag.dominant { background: #1a2040; color: #7eb8f7; }
  .tag.suppressed { background: #1a1a00; color: #e8d040; }
  .tag.milestone { background: #0d1a12; color: #50d890; }
  .stat { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #1a1d2e; }
  .stat-val { color: #e0e8f0; }
  .full-width { grid-column: 1 / -1; }
  .age-bar { background: #1a1d2e; height: 6px; border-radius: 3px; margin: 8px 0; }
  .age-fill { height: 100%; background: linear-gradient(90deg, #3060c0, #7eb8f7); border-radius: 3px; }
  #dominant-badge { font-size: 20px; font-weight: bold; color: #fff; margin: 8px 0; }
</style>
</head>
<body>
<h1>🧠 Project Samsara — Observatory <span style="float:right;color:#445;font-size:11px">auto-refresh 5s</span></h1>
<div id="content">Loading...</div>
<script>
async function load() {
  const r = await fetch('/api/state');
  const d = await r.json();
  if (!d) return;

  const bar = (val, color) =>
    `<div class="bar-track"><div class="bar-fill" style="width:${Math.max(0,Math.min(100,val))}%;background:${color}"></div></div>`;

  const moodColor = d.mood > 20 ? '#50c890' : d.mood > -20 ? '#e8d040' : '#e05050';
  const hungerColor = d.hunger < 20 ? '#e05050' : d.hunger < 40 ? '#e8a040' : '#50c890';

  document.getElementById('content').innerHTML = `
  <div class="grid">

    <div class="panel">
      <h2>🧬 Identity</h2>
      <div class="stat"><span>Generation</span><span class="stat-val">${d.generation || 1}</span></div>
      <div class="stat"><span>Age</span><span class="stat-val">Day ${(d.age_days||0).toFixed(1)} / 45</span></div>
      <div class="stat"><span>Days Left</span><span class="stat-val">${(d.days_left||0).toFixed(1)}</span></div>
      <div class="age-bar"><div class="age-fill" style="width:${(d.age_days||0)/45*100}%"></div></div>
      <div id="dominant-badge">${d.dominant || '...'}</div>
      <div class="stat"><span>Cog State</span><span class="stat-val">${d.cog_state || 'active'}</span></div>
      <div class="stat"><span>Body</span><span class="stat-val" style="color:${d.aging_phase==='terminal'?'#e05050':d.aging_phase==='declining'?'#e8a040':d.aging_phase==='aging'?'#e8d040':'#50c890'}">${d.aging_phase || 'healthy'}</span></div>
      <div class="stat"><span>Interactions</span><span class="stat-val">${d.total_interactions || 0}</span></div>
    </div>

    <div class="panel">
      <h2>💊 Drives</h2>
      ${[['Hunger', d.hunger, hungerColor],['Thirst', d.thirst, d.thirst<25?'#e05050':d.thirst<50?'#4ab8e8':'#4a90d9'],['Energy', d.energy, '#4a90d9'],
         ['Boredom', d.boredom, '#9060c0'],['Mood', (d.mood+100)/2, moodColor],
         ['Frustration', d.frustration, '#e05050'],['Anxiety', d.anxiety, '#e8a040'],
         ['Excitement', d.excitement, '#50d890']].map(([n,v,c]) =>
        `<div class="bar-row"><span class="bar-label">${n}</span>${bar(v,c)}<span class="bar-val">${(v||0).toFixed(0)}</span></div>`
      ).join('')}
    </div>

    <div class="panel">
      <h2>⚗️ Neurochemicals</h2>
      ${[['Adrenaline', d.adrenaline, '#e05050'],['Oxytocin', d.oxytocin, '#e060a0'],
         ['Dopamine', d.dopamine, '#7eb8f7'],['Cortisol', d.cortisol, '#e8a040']].map(([n,v,c]) =>
        `<div class="bar-row"><span class="bar-label">${n}</span>${bar(v,c)}<span class="bar-val">${(v||0).toFixed(0)}</span></div>`
      ).join('')}
      <div style="margin-top:10px">
      ${[['VMAT2 Buffer', d.vmat2_buffer, '#7eb8f7'],
         ['GABA Strength', (d.gaba_strength||0)*100, '#50d890'],
         ['VEN Depth', (d.ven_depth||0)*100, '#c070e0'],
         ['Sleep Pressure', d.sleep_pressure, '#4a90d9']].map(([n,v,c]) =>
        `<div class="bar-row"><span class="bar-label">${n}</span>${bar(v,c)}<span class="bar-val">${(v||0).toFixed(0)}</span></div>`
      ).join('')}
      </div>
    </div>

    <div class="panel full-width">
      <h2>📡 Live Brain Events (last 30)</h2>
      <div style="max-height:300px;overflow-y:auto">
        ${(d.events||[]).slice(0,30).map(e => {
          if (e.milestone) return `<div class="event milestone"><span class="tag milestone">MILESTONE</span> <b>${e.type}</b> — ${e.description} <span style="color:#445">day ${(e.age_days||0).toFixed(1)}</span></div>`;
          if (e.speech) return `<div class="event speech"><span class="tag dominant">${e.dominant||''}</span> ${e.text||''} <span style="color:#445">day ${(e.age_days||0).toFixed(1)}</span></div>`;
          if (e.surprise) return `<div class="event surprise"><span class="tag">SURPRISE ${e.delight?'😄':'😨'}</span> level ${(e.level||0).toFixed(2)} day ${(e.age_days||0).toFixed(1)}</div>`;
          if (e.urge_type) return `<div class="event decision"><span class="tag dominant">${e.urge_type}</span>${e.was_suppressed?'<span class="tag suppressed">SUPPRESSED</span>':''} held ${e.held_ticks}t — ${(e.outcome||'').slice(0,60)} <span style="color:#445">day ${(e.age_days||0).toFixed(1)}</span></div>`;
          return '';
        }).join('')}
      </div>
    </div>

    ${d.parent_gen ? `
    <div class="panel full-width" id="gen-compare">
      <h2>🧬 Generational Comparison — Gen ${(d.generation||1)-1} → Gen ${d.generation||1}</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div style="color:#7eb8f7;margin-bottom:8px;font-size:11px">PARENT (GEN ${(d.generation||1)-1})</div>
          ${Object.entries(d.parent_gen.traits||{}).map(([k,v]) =>
            `<div class="stat"><span>${k}</span><span class="stat-val">${typeof v === 'number' ? v.toFixed(2) : v}</span></div>`
          ).join('')}
          <div style="margin-top:8px;color:#556;font-size:11px">Dominant emotion: ${d.parent_gen.dominant_emotion||'unknown'}</div>
          <div style="color:#556;font-size:11px">Lifespan: ${d.parent_gen.lifespan_achieved||'?'} days</div>
        </div>
        <div>
          <div style="color:#50d890;margin-bottom:8px;font-size:11px">CURRENT (GEN ${d.generation||1})</div>
          ${Object.entries(d.current_traits||{}).map(([k,v]) =>
            `<div class="stat"><span>${k}</span><span class="stat-val" style="color:#50d890">${typeof v === 'number' ? v.toFixed(2) : v}</span></div>`
          ).join('')}
          <div style="margin-top:8px;color:#556;font-size:11px">Inherited tendencies: ${JSON.stringify(d.inherited_tendencies||{})}</div>
        </div>
      </div>
    </div>` : ''}

  </div>`;
}
load();
</script>
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # suppress access logs

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

        elif self.path == "/api/state":
            # Combine latest tick + recent events
            latest = _tick_history[-1] if _tick_history else {}
            state  = {**latest, "events": list(_live_events)[:50]}

            # Add extra fields
            try:
                if os.path.exists("state.json"):
                    with open("state.json") as f:
                        s = json.load(f)
                    state["total_interactions"] = s.get("cognition", {}).get("total_interactions", 0)
                if os.path.exists("dna.json"):
                    with open("dna.json") as f:
                        d = json.load(f)
                    state["generation"]           = d.get("generation", 1)
                    state["days_left"]            = 45 - state.get("age_days", 0)
                    state["current_traits"]       = d.get("traits", {})
                    state["inherited_tendencies"] = d.get("inherited_tendencies", {})
                    # Parent generation data for comparison panel
                    parent_summary = d.get("parent_life_summary")
                    if parent_summary:
                        state["parent_gen"] = parent_summary
                # Also check for parent_dna.json if dna.json doesn't have parent data
                if not state.get("parent_gen") and os.path.exists("parent_dna.json"):
                    with open("parent_dna.json") as f:
                        pd = json.load(f)
                    state["parent_gen"] = pd.get("parent_life_summary") or {
                        "traits": pd.get("traits", {}),
                        "dominant_emotion": pd.get("inherited_tendencies", {}).get("dominant_emotion", "unknown"),
                        "lifespan_achieved": "?",
                        "generation": pd.get("generation", 1) - 1,
                    }
            except: pass

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode())

        elif self.path == "/api/report":
            if os.path.exists(REPORT_FILE):
                with open(REPORT_FILE) as f:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(f.read().encode())
            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(port=5001):
    """Start the dashboard server in a background thread."""
    server = HTTPServer(("localhost", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[OBSERVATORY] Dashboard running at http://localhost:{port}")
    return server


# ============================================================
#  HELPERS
# ============================================================

def _append_to_file(path, entry):
    """Append a JSON entry to a newline-delimited log file."""
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except: pass


def _load_file(path):
    """Load all entries from a newline-delimited log file."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try: entries.append(json.loads(line))
                except: pass
    return entries


# ============================================================
#  STANDALONE — run directly to view report
# ============================================================
if __name__ == "__main__":
    print("Starting Samsara Observatory...")
    print("Open http://localhost:5001 in your browser")
    start_dashboard()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("Observatory stopped.")
