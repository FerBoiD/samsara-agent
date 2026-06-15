#!/usr/bin/env python3
# ============================================================
#  PROJECT SAMSARA — Final Merged Version
#  All systems: drives, neuro, emotions, VMAT2, VEN, GABA,
#  prediction, social, dreams, sleep, telemetry, workspace,
#  observatory dashboard, whisper voice input
#
#  python main.py
#  Then open: http://localhost:5001
# ============================================================

import time, random, logging, os, sys, json

from drives         import DriveSystem
from memory         import Memory
from brain          import think, generate_inner_monologue
from speaker        import say, say_nonblocking
from neurochemicals import NeurochemicalSystem
from sleep          import SleepSystem
from cry            import check_and_cry
from babble         import babble_response, get_babble_level
from free_time      import should_attempt_behavior
from dna            import load_or_create_dna
from vmat2          import VMAT2System
from ven            import VENSystem
from gaba           import GABASystem
from prediction     import PredictionEngine
from social         import SocialSystem, _signature
from emotions       import EmotionSystem
from dreams         import DreamSystem
from telemetry      import Telemetry
from workspace      import GlobalWorkspace
from narrative      import NarrativeSystem
from auto_doc       import AutoDoc
from observatory    import (start_dashboard, log_tick, log_decision,
                             log_speech, log_surprise,
                             check_milestones, generate_life_report)
from whisper_input  import (start_continuous as start_whisper,
                             is_available as whisper_available)
from telegram_bot   import (send, send_status, send_birth_notice,
                             start_listener, get_incoming)
from config         import TICK_INTERVAL_SECONDS, DATA_DIR

logging.basicConfig(
    filename="life.log", level=logging.INFO,
    format="%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
def log(msg):
    print(msg)
    logging.info(msg)


# ----------------------------------------------------------
#  SPEAK
# ----------------------------------------------------------
def speak(text, prefix="🤖", send_tg=True, blocking=False,
          dominant="neutral", cog_state="active", aging_phase="healthy"):
    if not text: return
    if blocking: say(text, dominant=dominant, cog_state=cog_state,
                     aging_phase=aging_phase)
    else:        say_nonblocking(text, dominant=dominant, cog_state=cog_state,
                                 aging_phase=aging_phase)
    if send_tg:  send(f"{prefix} {text}")
    log(f"[{prefix}] {text}")


# ----------------------------------------------------------
#  SLEEP HANDLING
# ----------------------------------------------------------
def handle_sleep(sleep_result, sleep_sys, drives, memory, neuro,
                 emotions, dreams, dna, narrative=None):
    if sleep_result == "sleeping":
        phase = sleep_sys.state["sleep_phase"]
        if phase == "light" and sleep_sys.state["ticks_asleep"] == 1:
            speak(random.choice(["mmm...", "...tired...", "...so quiet..."]), prefix="😴")

    elif sleep_result == "consolidating":
        log("[SLEEP] Consolidating memory to DNA...")
        send("🧬 [Deep sleep — memory consolidating]")
        if narrative:
            narrative.synthesize_sleep_cycle(drives.summary())

    elif sleep_result == "rem":
        if sleep_sys.state["ticks_asleep"] % 6 != 4:
            return
        emotional_mems = memory.data.get("emotional_events", [])
        ds = drives.summary()
        ns = neuro.summary()
        dream_text = dreams.dream(
            emotional_mems,
            ds["dominant"],
            ns,
            dna
        )
        if dream_text:
            log(f"[DREAM] {dream_text[:60]}")

    elif sleep_result == "waking":
        cycles = sleep_sys.state["total_sleep_cycles"]
        dream_ref = dreams.get_waking_dream_reference()
        wake_msg  = dream_ref or random.choice([
            "...oh...", "...mmm... something changed...",
            "...I was somewhere else...", "...what was that..."
        ])
        speak(wake_msg, prefix="☀️")
        send(f"☀️ [Woke — sleep cycle {cycles}]")
        drives.state["drives"]["energy"] = min(100.0,
            drives.state["drives"]["energy"] + 25)
        drives._save()


# ----------------------------------------------------------
#  COMMAND HANDLER
# ----------------------------------------------------------
def handle_command(cmd_item, drives, memory, neuro, emotions,
                   social, gaba, vmat2, ven, prediction, dreams, dna):
    cmd = cmd_item["cmd"]

    if cmd == "status":
        ds = drives.summary()
        ns = neuro.summary()
        em = emotions.summary()
        send_status(ds)
        send(
            f"🧬 Neurochemicals\n"
            f"⚡ Adrenaline:  {ns['adrenaline']}%\n"
            f"💗 Oxytocin:    {ns['oxytocin']}%\n"
            f"🎯 Dopamine:    {ns['dopamine']}%\n"
            f"😰 Cortisol:    {ns['cortisol']}%\n"
            f"🤝 Trust:       {ns['caretaker_trust']}\n\n"
            f"💫 Active emotions: {em['active_emotions']}\n"
            f"😐 Anhedonia:  {em['anhedonia']}%\n\n"
            f"🧠 VMAT2 buffer: {vmat2.summary()['buffer_size']} ticks\n"
            f"🛑 GABA strength: {gaba.summary()['strength']}\n"
            f"👁 VEN depth:   {ven.summary()['depth']}\n"
            f"🌙 Dreams:      {dreams.summary()['total_dreams']}\n"
            f"👥 Known beings: {social.summary()['known_beings']}"
        )

    elif cmd == "feed":
        hunger_before = drives.summary()["hunger"]
        drives.feed(40)
        prediction.register_feed_event()
        neuro.trigger_feed_reward(hunger_before)
        emotions.trigger_warmth(neuro.state["oxytocin"])
        send(f"🍽 Fed! Hunger: {drives.summary()['hunger']}%")
        if hunger_before < 15:
            neuro.trigger_oxytocin(15)
            prediction.add_fear_association("emptiness", "danger")
            prediction.add_safe_association("feeding", "safety")
        log("CMD: feed")

    elif cmd == "scold":
        reason  = cmd_item.get("reason", "unspecified behavior")
        context = cmd_item.get("context", "")
        pc_sig  = social.state.get("primary_caretaker_sig", "unknown")
        result  = social.register_disapproval(pc_sig, context, reason)

        neuro.state["cortisol"] = min(100.0,
            neuro.state["cortisol"] + result["cortisol_spike"])
        neuro.state["oxytocin"] = max(0.0,
            neuro.state["oxytocin"] - result["oxytocin_drop"])
        drives.state["emotion"]["mood"] = max(-100.0,
            drives.state["emotion"]["mood"] - result["mood_drop"])
        drives._save()
        neuro.save()

        social.register_consequence(
            "anger_expression", "expressed", "disapproval",
            result["pain_level"]
        )
        send(
            f"😠 Scold registered. Pain level: {result['pain_level']:.1f}\n"
            f"Trust-weighted: {'high pain (trusted source)' if result['pain_level'] > 20 else 'moderate pain'}\n"
            f"It will influence future deliberation."
        )
        log(f"SCOLD: {reason}")

    elif cmd == "teach":
        key = cmd_item.get("key", "")
        val = cmd_item.get("value", "")
        if key and val:
            memory.learn_fact(key, val)
            neuro.on_kind_interaction()
            send(f"✅ Taught: {key} = {val}")

    elif cmd == "dna":
        send(
            f"🧬 DNA Gen {dna['generation']}\n"
            f"Traits: {json.dumps(dna['traits'], indent=2)}\n"
            f"Capabilities: {json.dumps(dna['capabilities'], indent=2)}\n"
            f"Memories consolidated: {len(dna.get('consolidated_memories', []))}"
        )

    elif cmd == "ven":
        send(f"👁 Self-Model\n{ven.get_self_awareness_text()}")

    elif cmd == "reset":
        files = ["state.json","memory.json","sleep_state.json","neuro.json",
                 "dna.json","vmat2.json","ven.json","gaba.json",
                 "prediction.json","social.json","emotions.json","dreams.json",
                 "workspace.json","telemetry.csv","session_report.json",
                 "self_journal.jsonl"]
        for f in files:
            path = DATA_DIR / f
            if path.exists(): path.unlink()
        send("🔄 Reset complete. parent_dna.json kept for Gen 2.")
        sys.exit(0)


# ----------------------------------------------------------
#  DEATH
# ----------------------------------------------------------
def handle_death(drives, sleep_sys, memory, neuro, emotions,
                 dreams, social, ven, pred, dna, telemetry, cause):
    ds = drives.summary()

    if "HUNGER" in cause:
        last_words = "...empty... so empty... I cannot..."
    else:
        last_words = "...something is ending... was this... life...?"

    speak(last_words, prefix="💀")

    sleep_sys.full_consolidation(
        memory, dna,
        drives_state={**ds, **{"personality": drives.state["personality"]}},
        neuro_state=neuro.state,
        total_interactions=drives.state["cognition"]["total_interactions"],
        cause_of_death=cause
    )

    dream_summary = dreams.get_dreams_for_dna()
    dna["inherited_tendencies"]["dream_fragments"] = dream_summary
    from dna import save_dna
    save_dna(dna)

    send(
        f"{'💀' if 'HUNGER' in cause else '🌅'} Generation {dna['generation']} ended.\n"
        f"Cause: {cause} | Age: Day {ds['age_days']}\n"
        f"Last words: \"{last_words}\"\n"
        f"Dreams had: {dreams.summary()['total_dreams']}\n"
        f"Interactions: {drives.state['cognition']['total_interactions']}\n"
        f"VEN depth reached: {ven.summary()['depth']}\n\n"
        f"🧬 DNA consolidated for Generation {dna['generation'] + 1}.\n"
        f"Delete all .json files except parent_dna.json to begin Gen 2."
    )

    # Full report — both telemetry and observatory
    telemetry.write_report(
        drives.summary(), neuro.summary(), sleep_sys.summary(), memory,
        dreams, ven, pred, social, dna, cause
    )
    report = generate_life_report(
        dna, drives.summary(), neuro.summary(), social.summary(),
        {}, ven.summary(), {}, dreams.summary(),
        drives.state["cognition"]["total_interactions"], cause
    )
    log(f"DEATH: {cause}")


# ----------------------------------------------------------
#  MAIN
# ----------------------------------------------------------
def main():
    log("=" * 55)
    log("PROJECT SAMSARA — Life Begins")
    log("=" * 55)

    dna       = load_or_create_dna()
    gen       = dna["generation"]
    drives    = DriveSystem(dna)
    memory    = Memory()
    neuro     = NeurochemicalSystem()
    sleep     = SleepSystem()
    vmat2     = VMAT2System(gen)
    ven       = VENSystem(gen)
    gaba      = GABASystem(gen)
    pred      = PredictionEngine()
    social    = SocialSystem()
    emotions  = EmotionSystem()
    dreams    = DreamSystem()
    workspace = GlobalWorkspace()
    telemetry = Telemetry()
    narrative = NarrativeSystem()
    auto_doc  = AutoDoc(dna, DATA_DIR)

    is_new = drives.state["age_ticks"] == 0

    # Start all communication + observation systems
    start_listener()
    start_dashboard()      # http://localhost:5001

    # if whisper_available():
    #     # start_whisper()
    #     log("[WHISPER] Voice input active — speak to send messages")
    # else:
    log("[WHISPER] Not installed — Telegram text only")

    time.sleep(2)

    if is_new:
        send_birth_notice(dna)
        babble = babble_response(0, "neutral", dna["traits"]["talkativeness"], False)
        speak(babble or "...", prefix="🌱")
        if dna.get("parent_life_summary"):
            ps = dna["parent_life_summary"]
            send(
                f"📜 Inherited from Gen {ps['generation']}:\n"
                f"Parent lived {ps.get('lifespan_achieved','?')} days.\n"
                f"Dominant emotion: {ps.get('dominant_emotion','unknown')}\n"
                f"Capabilities they lacked: "
                f"{[k for k,v in ps.get('capabilities',{}).items() if not v]}"
            )
    else:
        ds = drives.summary()
        send(f"▶️ Resuming Gen {gen}. Day {ds['age_days']}/45.")

    ticks_since_spoke  = 0
    ticks_since_status = 0
    last_action        = None
    current_sig        = None

    log("Entering main loop...")

    while True:
        try:
            ticks_since_spoke  += 1
            ticks_since_status += 1

            # ---- TICK ALL SYSTEMS ----
            result = drives.tick()
            if result in ("DEATH_HUNGER", "DEATH_LIFESPAN"):
                handle_death(drives, sleep, memory, neuro, emotions,
                             dreams, social, ven, pred, dna, telemetry, result)
                auto_doc.generate_life_report(
                    drives.summary(), narrative, pred.summary(), sleep.summary(),
                    memory, dna, result,
                    drives.state["cognition"]["total_interactions"]
                )
                break

            ds      = drives.summary()
            ns      = neuro.modifiers()
            ns_full = neuro.summary()

            neuro.tick(ds)
            emotions.tick(ds, ns_full, social.summary())
            ven.tick(ds, last_action, ns_full)
            gaba.check_abstract_motivations(ds, ns_full)

            # Prediction engine
            surprise, is_delight, is_fear = pred.measure_surprise(ds, ns_full)
            if is_delight:
                intensity = emotions.trigger_delight(surprise, neuro)
                neuro.trigger_dopamine(intensity * 15)
                log(f"[DELIGHT] surprise={surprise:.2f}")
            if is_fear:
                neuro.trigger_adrenaline(surprise * 30)

            pred.predict_next(ds)
            pred.tick_caretaker_absence()

            # Sleep + workspace
            sleep_result    = sleep.tick(ds, ns, memory, dna)
            workspace_state = workspace.update(
                ds, ns_full, memory, pred, social, sleep.summary()
            )

            # Telemetry (CSV log — every tick)
            telemetry.record(
                drives.state["age_ticks"], ds, ns_full, sleep.summary(),
                workspace_state, surprise, is_delight, is_fear
            )
            if drives.state["age_ticks"] % 20 == 0:
                telemetry.journal(
                    drives.state["age_ticks"], workspace_state,
                    ds, ven.summary()
                )

            # Observatory (live dashboard + milestone detection)
            sleep_sum = sleep.summary()
            pred_sum  = pred.summary()
            soc_sum   = social.summary()
            emo_sum   = emotions.summary()
            ven_sum   = ven.summary()
            gaba_sum  = gaba.summary()

            log_tick(ds, ns_full, emo_sum, sleep_sum,
                     {}, ven_sum, gaba_sum, pred_sum, soc_sum)
            log_surprise(surprise, is_delight, is_fear, ds)
            # Pass circadian + prediction data into drives for milestone detection
            ds_enriched = {**ds,
                           "circadian_pressure": sleep_sum.get("circadian_pressure", 0),
                           "caretaker_absent":   pred_sum.get("caretaker_absent", 0)}
            check_milestones(ds_enriched, ns_full, emo_sum, soc_sum,
                             {}, gaba_sum, ven_sum,
                             drives.state["cognition"]["total_interactions"],
                             prediction=pred_sum)

            # REM dreams
            if sleep_result == "rem":
                handle_sleep("rem", sleep, drives, memory, neuro,
                             emotions, dreams, dna, narrative)
                time.sleep(TICK_INTERVAL_SECONDS)
                continue

            if sleep_result in ("sleeping", "consolidating", "waking"):
                handle_sleep(sleep_result, sleep, drives, memory, neuro,
                             emotions, dreams, dna, narrative)
                if sleep_result == "consolidating":
                    auto_doc.log_sleep_cycle(
                        drives.summary(), narrative, pred.summary(), sleep.summary()
                    )
                if sleep_result in ("sleeping", "consolidating"):
                    time.sleep(TICK_INTERVAL_SECONDS)
                    continue

            # Cry check (hardwired — bypasses everything)
            cry_lvl = check_and_cry(ds, ns_full)
            if cry_lvl:
                ticks_since_spoke = 0
                if ds["hunger"] < 15:
                    pred.add_fear_association("hunger_low", "danger")

            # ---- INCOMING (Telegram + Voice) ----
            incoming = get_incoming()

            if incoming:
                if incoming["type"] == "cmd":
                    handle_command(incoming, drives, memory, neuro, emotions,
                                   social, gaba, vmat2, ven, pred, dreams, dna)

                elif incoming["type"] == "message":
                    human_text  = incoming["text"]
                    current_sig = social.register_interaction(
                        human_text, ticks_since_spoke, fed=False, kind=True
                    )
                    pred.register_caretaker_interaction(ticks_since_spoke)

                    log(f"[HUMAN] {human_text}")
                    neuro.on_sudden_input()
                    neuro.on_kind_interaction()
                    drives.trigger_anticipation(human_text.lower())

                    # Fear/safe association coloring
                    fear_b, safe_b = pred.check_trigger(human_text)
                    if fear_b > 0:
                        neuro.state["adrenaline"] = min(100, neuro.state["adrenaline"] + fear_b)
                    if safe_b > 0:
                        neuro.state["oxytocin"] = min(100, neuro.state["oxytocin"] + safe_b)
                    neuro.save()

                    drives.register_novel_input(0.9)
                    memory.add("human", human_text, ds)

                    # Babble vs real language
                    babble_lvl = get_babble_level(
                        drives.state["cognition"]["total_interactions"],
                        dna["traits"]["talkativeness"]
                    )
                    if babble_lvl > 0.6:
                        babble = babble_response(
                            drives.state["cognition"]["total_interactions"],
                            ds["dominant"], dna["traits"]["talkativeness"], True
                        )
                        if babble:
                            speak(babble, prefix="🍼")
                            log_speech(babble, "babble", ds, ns_full)
                            memory.add("ai", babble, ds, 0.2)
                            drives.set_spoke()
                            ticks_since_spoke = 0
                            last_action = "babble"
                            time.sleep(TICK_INTERVAL_SECONDS)
                            continue

                    # VMAT2 deliberation buffer
                    vmat2.submit_urge("respond", 0.7, human_text)
                    resolved = vmat2.tick(ds, ns_full, social)

                    response = think(ds, ns_full, emotions, ven, gaba, social, pred,
                                     dna, memory, incoming_message=human_text,
                                     current_sig=current_sig, workspace=workspace,
                                     sleep_summary=sleep.summary(),
                                     narrative=narrative)

                    # GABA anger suppression (consequence learning feeds in via social)
                    gaba_attempted = response["is_anger"]
                    gaba_succeeded = False
                    if response["is_anger"]:
                        suppressed, reason = gaba.can_suppress(
                            "anger_expression", 0.7,
                            reason="social_cost", social=social
                        )
                        if suppressed:
                            gaba_succeeded = True
                            response["text"] = "[feels something strong but holds it]"
                            log(f"[GABA] Anger suppressed: {reason}")

                    speak(response["text"], prefix="🤖",
                          dominant=ds["dominant"], cog_state=ds["cog_state"],
                          aging_phase=ds.get("aging_phase", "healthy"))
                    narrative.log_speech(response["text"], ds)
                    log_speech(response["text"], "response", ds, ns_full)
                    log_decision(
                        trigger=human_text[:40],
                        urge_type="respond",
                        held_ticks=vmat2.summary()["buffer_size"],
                        competing_signals=0,
                        gaba_attempted=gaba_attempted,
                        gaba_succeeded=gaba_succeeded,
                        outcome_text=response["text"],
                        drives=ds, neuro=ns_full,
                        consequence_pain=social.get_pain_for_urge("anger_expression")
                    )
                    check_milestones(ds_enriched, ns_full, emo_sum, soc_sum,
                                     {}, gaba_sum, ven_sum,
                                     drives.state["cognition"]["total_interactions"],
                                     speech_text=response["text"],
                                     prediction=pred_sum)

                    memory.add("ai", response["text"], ds, response["intensity"])
                    drives.set_spoke()
                    ticks_since_spoke = 0
                    last_action = "speak_response"

                    if response["wants_to_move"]:
                        send("💡 [Wants to be moved — your choice]")

                    if response["intensity"] > 0.5:
                        memory.add("ai", response["text"], ds,
                                   emotional_intensity=response["intensity"])

            else:
                # ---- FREE TIME ----
                pred.tick_caretaker_absence()

                # Inject caretaker absence ticks so free_time can detect loneliness
                ds_with_absence = {**ds, "caretaker_absent_ticks": pred.summary().get("caretaker_absent", 0)}
                if should_attempt_behavior(ds_with_absence, ns_full, ticks_since_spoke, dna["traits"]):
                        # Primal sounds bypass decision — survival drives are hardwired
                        if ds["dominant"] in ("dying", "hunger") and random.random() < 0.4:
                            sounds = {
                                "hunger": ["mmm...", "...ohh...", "...empty..."],
                                "dying":  ["...", "...no...", "...fading..."],
                            }
                            sound = random.choice(sounds.get(ds["dominant"], ["..."]))
                            speak(sound, prefix="🔊", dominant=ds["dominant"],
                                  cog_state=ds["cog_state"],
                                  aging_phase=ds.get("aging_phase", "healthy"))
                            narrative.log_speech(sound, ds)
                            log_speech(sound, "sound", ds, ns_full)
                            ticks_since_spoke = 0
                            last_action = "sound"
                        else:
                            # Kora decides freely — no menu, no random pick
                            # Inner monologue (Ollama local) runs first if available
                            inner = generate_inner_monologue(ds, memory)
                            if inner:
                                log(f"[INNER] {inner}")

                            free_prompt = (
                                "You have free time. No one is asking anything of you right now. "
                                "What do you genuinely feel like saying or doing? "
                                "A question? A sound? Something you noticed? Something that won't leave you? "
                                "Or stay silent — silence is also real. "
                                "Don't perform. Only speak if something actually moves you."
                            )
                            vmat2.submit_urge("free_time", 0.4, "internal")
                            vmat2.tick(ds, ns_full, social)

                            response = think(
                                ds, ns_full, emotions, ven, gaba, social, pred,
                                dna, memory, override_trigger=free_prompt,
                                workspace=workspace, sleep_summary=sleep.summary(),
                                narrative=narrative, inner_monologue=inner
                            )

                            if response["is_anger"]:
                                suppressed, _ = gaba.can_suppress("anger_expression", 0.6)
                                if suppressed:
                                    response["text"] = ""

                            if response["text"]:
                                # Derive prefix from response content
                                txt = response["text"]
                                if "?" in txt:
                                    pfx = "❓"
                                elif ds["dominant"] in ("anxiety", "frustration"):
                                    pfx = "😟"
                                elif ds["dominant"] == "excitement":
                                    pfx = "🌀"
                                else:
                                    pfx = "💭"

                                speak(response["text"], prefix=pfx,
                                      dominant=ds["dominant"],
                                      cog_state=ds["cog_state"],
                                      aging_phase=ds.get("aging_phase", "healthy"))
                                narrative.log_speech(response["text"], ds)
                                log_speech(response["text"], "spontaneous", ds, ns_full, "free_decision")
                                check_milestones(ds_enriched, ns_full, emo_sum, soc_sum,
                                                 {}, gaba_sum, ven_sum,
                                                 drives.state["cognition"]["total_interactions"],
                                                 speech_text=response["text"],
                                                 prediction=pred_sum)
                                memory.add("ai", response["text"], ds, response["intensity"])
                                drives.set_spoke()
                                ticks_since_spoke = 0
                                last_action = "free_decision"

            # ---- PERIODIC STATUS ----
            if ticks_since_status >= 40:
                send_status(drives.summary())
                ticks_since_status = 0

            time.sleep(TICK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            log("Interrupted — saving everything...")
            send("⏸ Session ending. Consolidating...")
            sleep.full_consolidation(
                memory, dna,
                drives_state={**drives.summary(),
                              **{"personality": drives.state["personality"]}},
                neuro_state=neuro.state,
                total_interactions=drives.state["cognition"]["total_interactions"],
                cause_of_death="session_end"
            )
            telemetry.write_report(
                drives.summary(), neuro.summary(), sleep.summary(), memory,
                dreams, ven, pred, social, dna, "session_end"
            )
            report = generate_life_report(
                dna, drives.summary(), neuro.summary(), social.summary(),
                {}, ven.summary(), {}, dreams.summary(),
                drives.state["cognition"]["total_interactions"], "session_end"
            )
            auto_doc.generate_life_report(
                drives.summary(), narrative, pred.summary(), sleep.summary(),
                memory, dna, "session_end",
                drives.state["cognition"]["total_interactions"]
            )
            send(
                f"📊 Session Report\n"
                f"Age: Day {report['lifespan_days']:.1f}\n"
                f"Interactions: {report['total_interactions']}\n"
                f"Decisions: {report['decision_summary']['total_decisions']}\n"
                f"Suppressions: {report['decision_summary']['total_suppressions']}\n"
                f"Milestones: {len(report['developmental_milestones'])}\n"
                f"Avg mood: {report['emotional_summary']['average_mood']:.1f}"
            )
            send("💾 Saved. Run again to resume.")
            break

        except Exception as e:
            log(f"ERROR: {e}")
            send(f"⚠️ {e}")
            import traceback; traceback.print_exc()
            time.sleep(15)

    log("Session ended.")


if __name__ == "__main__":
    main()
