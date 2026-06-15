# ============================================================
#  GODOT BRIDGE — Python side
#
#  TCP server on port 9999.
#  Streams Kora's drive state to the Godot sphere every 500ms.
#  Receives commands from Godot (feed, status, etc.)
#
#  Usage in main.py:
#    from godot_bridge import start_bridge
#    start_bridge(lambda: drives.summary(), on_feed=lambda: drives.feed(40))
# ============================================================

import json
import socket
import threading
import time

_server_socket  = None
_get_state_fn   = None
_on_feed_fn     = None
_running        = False

BRIDGE_PORT     = 9999
BROADCAST_HZ    = 0.5    # seconds between state pushes


def start_bridge(get_state_fn, on_feed=None):
    """
    get_state_fn : callable() -> dict of current drive state
    on_feed      : callable() triggered when Godot food bowl is clicked
    """
    global _server_socket, _get_state_fn, _on_feed_fn, _running
    _get_state_fn = get_state_fn
    _on_feed_fn   = on_feed
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
                raw = _get_state_fn()
                # Add Godot-specific fields
                payload = {
                    "hunger":      round(raw.get("hunger",      80.0), 1),
                    "energy":      round(raw.get("energy",      90.0), 1),
                    "mood":        round(raw.get("mood",         0.0), 1),
                    "anxiety":     round(raw.get("anxiety",     10.0), 1),
                    "frustration": round(raw.get("frustration", 10.0), 1),
                    "boredom":     round(raw.get("boredom",     20.0), 1),
                    "excitement":  round(raw.get("excitement",   5.0), 1),
                    "dominant":    raw.get("dominant",  "neutral"),
                    "age_days":    round(raw.get("age_days",     0.0), 2),
                    "sleeping":    raw.get("cog_state", "active") == "sleeping",
                    "cog_state":   raw.get("cog_state", "active"),
                    "aging_phase": raw.get("aging_phase", "healthy"),
                }
                try:
                    conn.sendall((json.dumps(payload) + "\n").encode())
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break

            # --- Read commands ---
            try:
                data = conn.recv(256).decode().strip()
                if data:
                    _handle_command(data)
            except BlockingIOError:
                pass
            except (ConnectionResetError, OSError):
                break

            time.sleep(BROADCAST_HZ)

    finally:
        conn.close()
        print("[GODOT BRIDGE] Godot disconnected")


def _handle_command(cmd: str):
    if cmd == "feed" and _on_feed_fn:
        print("[GODOT BRIDGE] Feed command from Godot")
        _on_feed_fn()
    elif cmd == "ping":
        pass  # keepalive
