# ============================================================
#  GODOT BRIDGE — Python side
#
#  TCP server on port 9999.
#  Streams Kora's full state (drives + body) to Godot every 500ms.
#  Receives commands from Godot:
#    "feed"       — feed Kora
#    "drink"      — give water
#    "msg:<text>" — caretaker typed something in Godot chat
#    "ping"       — keepalive
#
#  Usage in main.py:
#    from godot_bridge import start_bridge, get_next_godot_message
#    start_bridge(get_state_fn, on_feed=..., on_drink=...)
#    # in main loop: godot_text = get_next_godot_message()
# ============================================================

import json
import socket
import threading
import time

BRIDGE_PORT    = 9999
BROADCAST_HZ   = 0.5

_server_socket = None
_get_state_fn  = None
_on_feed_fn    = None
_on_drink_fn   = None
_running       = False

# Queue for Godot → Python chat messages
_msg_queue: list = []
_msg_lock        = threading.Lock()


# ----------------------------------------------------------
#  PUBLIC API
# ----------------------------------------------------------
def start_bridge(get_state_fn, on_feed=None, on_drink=None):
    """
    get_state_fn : callable() → dict (drives + body merged)
    on_feed      : callable() — caretaker fed Kora from Godot
    on_drink     : callable() — caretaker gave water from Godot
    """
    global _server_socket, _get_state_fn, _on_feed_fn, _on_drink_fn, _running
    _get_state_fn = get_state_fn
    _on_feed_fn   = on_feed
    _on_drink_fn  = on_drink
    _running      = True

    try:
        _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_socket.bind(("127.0.0.1", BRIDGE_PORT))
        _server_socket.listen(5)
        _server_socket.setblocking(False)
    except OSError as e:
        print(f"[GODOT BRIDGE] Could not bind port {BRIDGE_PORT}: {e}")
        return

    t = threading.Thread(target=_accept_loop, daemon=True)
    t.start()
    print(f"[GODOT BRIDGE] Listening on port {BRIDGE_PORT}")


def stop_bridge():
    global _running
    _running = False
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass


def get_next_godot_message() -> str | None:
    """
    Called from main loop every tick.
    Returns the next chat message typed in Godot, or None.
    """
    with _msg_lock:
        return _msg_queue.pop(0) if _msg_queue else None


# ----------------------------------------------------------
#  INTERNAL
# ----------------------------------------------------------
def _accept_loop():
    while _running:
        try:
            conn, _ = _server_socket.accept()
            t = threading.Thread(
                target=_client_handler, args=(conn,), daemon=True
            )
            t.start()
        except BlockingIOError:
            time.sleep(0.1)
        except Exception:
            time.sleep(1)


def _client_handler(conn: socket.socket):
    conn.setblocking(False)
    print("[GODOT BRIDGE] Godot connected")
    try:
        while _running:
            # --- Push state ---
            if _get_state_fn:
                raw     = _get_state_fn()
                payload = _build_payload(raw)
                try:
                    conn.sendall((json.dumps(payload) + "\n").encode())
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break

            # --- Read commands ---
            try:
                data = conn.recv(512).decode().strip()
                if data:
                    for line in data.split("\n"):
                        line = line.strip()
                        if line:
                            _handle_command(line)
            except BlockingIOError:
                pass
            except (ConnectionResetError, OSError):
                break

            time.sleep(BROADCAST_HZ)

    finally:
        conn.close()
        print("[GODOT BRIDGE] Godot disconnected")


def _build_payload(raw: dict) -> dict:
    """Whitelist fields sent to Godot — drives + body merged."""
    return {
        # Drive state
        "hunger":            round(raw.get("hunger",       80.0), 1),
        "energy":            round(raw.get("energy",       90.0), 1),
        "mood":              round(raw.get("mood",          0.0), 1),
        "anxiety":           round(raw.get("anxiety",      10.0), 1),
        "frustration":       round(raw.get("frustration",  10.0), 1),
        "boredom":           round(raw.get("boredom",      20.0), 1),
        "excitement":        round(raw.get("excitement",    5.0), 1),
        "dominant":          raw.get("dominant",    "neutral"),
        "age_days":          round(raw.get("age_days",      0.0), 2),
        "sleeping":          raw.get("cog_state", "active") == "sleeping",
        "cog_state":         raw.get("cog_state",  "active"),
        "aging_phase":       raw.get("aging_phase","healthy"),
        # Body sensations
        "thirst":            round(raw.get("thirst",           80.0), 1),
        "body_temp":         round(raw.get("body_temp",        37.0), 2),
        "muscle_fatigue":    round(raw.get("muscle_fatigue",    0.0), 1),
        "blood_sugar_crash": round(raw.get("blood_sugar_crash", 0.0), 1),
        "nausea":            round(raw.get("nausea",            0.0), 1),
        "immune":            round(raw.get("immune",          100.0), 1),
        "sickness":          round(raw.get("sickness",          0.0), 1),
        "restlessness":      round(raw.get("restlessness",      0.0), 1),
        "jet_lag_score":     round(raw.get("jet_lag_score",     0.0), 1),
    }


def _handle_command(cmd: str):
    if cmd == "feed" and _on_feed_fn:
        print("[GODOT BRIDGE] Feed command")
        _on_feed_fn()
    elif cmd == "drink" and _on_drink_fn:
        print("[GODOT BRIDGE] Drink command")
        _on_drink_fn()
    elif cmd.startswith("msg:"):
        text = cmd[4:].strip()
        if text:
            with _msg_lock:
                _msg_queue.append(text)
            print(f"[GODOT BRIDGE] Message: {text[:50]}")
    elif cmd == "ping":
        pass
