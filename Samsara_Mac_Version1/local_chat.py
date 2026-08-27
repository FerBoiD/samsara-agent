# ============================================================
#  LOCAL CHAT UI
#
#  Serves a minimal browser chat at http://localhost:5002
#  so you can talk to Kora without Telegram or Godot.
#
#  main.py calls:
#    start_chat_ui()          — start the server (once at boot)
#    get_next_chat_message()  — pull user messages each tick
#    push_chat_response(text) — push Kora's words to the UI
# ============================================================

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import queue
import time
import urllib.parse

CHAT_PORT = 5002

_incoming = queue.Queue()     # user → Kora ({"type": "message", "text": ...})
_messages = []                # all messages shown in UI
_msg_id   = 0
_lock     = threading.Lock()


def push_chat_response(text: str) -> None:
    global _msg_id
    text = text.strip()
    if not text:
        return
    with _lock:
        _msg_id += 1
        _messages.append({"id": _msg_id, "sender": "kora", "text": text})
        if len(_messages) > 600:
            _messages.pop(0)


def get_next_chat_message():
    try:
        return _incoming.get_nowait()
    except queue.Empty:
        return None


# ----------------------------------------------------------
#  HTTP HANDLER
# ----------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence access logs

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/poll":
            self._serve_poll()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path == "/send":
            self._handle_send()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_html(self):
        body = _HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_poll(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        since  = int(params.get("since", ["0"])[0])
        with _lock:
            new_msgs = [m for m in _messages if m["id"] > since]
        body = json.dumps(new_msgs).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_send(self):
        global _msg_id
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)
        try:
            data = json.loads(raw)
            text = data.get("text", "").strip()
        except Exception:
            text = ""
        if text:
            with _lock:
                _msg_id += 1
                _messages.append({"id": _msg_id, "sender": "you", "text": text})
            _incoming.put({"type": "message", "text": text})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


# ----------------------------------------------------------
#  START
# ----------------------------------------------------------
def start_chat_ui():
    server = HTTPServer(("", CHAT_PORT), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[CHAT] Local chat UI → http://localhost:{CHAT_PORT}")


# ----------------------------------------------------------
#  UI HTML (self-contained, no CDN)
# ----------------------------------------------------------
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kora</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;background:#0b0b10;color:#d8d8e8;font-family:'Segoe UI',system-ui,sans-serif}
body{display:flex;flex-direction:column;height:100vh}

.header{
  padding:14px 20px;
  background:#111118;
  border-bottom:1px solid #1c1c2a;
  display:flex;align-items:center;gap:12px;
  flex-shrink:0;
}
.dot{width:9px;height:9px;border-radius:50%;background:#e74c3c;transition:background .4s}
.dot.on{background:#2ecc71}
.hname{font-size:15px;font-weight:600;color:#c0c0dc;letter-spacing:.04em}
.hsub{font-size:11px;color:#44445a;margin-top:1px}

#msgs{
  flex:1;overflow-y:auto;
  padding:18px 16px;
  display:flex;flex-direction:column;gap:10px;
}
.bubble{
  max-width:74%;padding:10px 14px;border-radius:14px;
  font-size:14px;line-height:1.55;
  animation:fadeIn .2s ease;
}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.bubble.kora{
  align-self:flex-start;
  background:#161622;color:#cccce0;
  border-bottom-left-radius:4px;
}
.bubble.you{
  align-self:flex-end;
  background:#221e4a;color:#e0e0f8;
  border-bottom-right-radius:4px;
}
.label{
  font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  margin-bottom:5px;opacity:.45;
}

.bar{
  padding:12px 16px;
  background:#111118;border-top:1px solid #1c1c2a;
  display:flex;gap:10px;flex-shrink:0;
}
#inp{
  flex:1;background:#191926;border:1px solid #26263a;border-radius:10px;
  color:#e0e0f0;font-size:14px;padding:10px 14px;outline:none;
  transition:border-color .2s;
}
#inp:focus{border-color:#4040aa}
#inp::placeholder{color:#33334a}
#btn{
  background:#2c2c9a;color:#d0d0ff;border:none;border-radius:10px;
  padding:10px 20px;font-size:14px;cursor:pointer;
  transition:background .15s;white-space:nowrap;
}
#btn:hover{background:#3a3ab8}
#btn:active{background:#22228a}

#msgs::-webkit-scrollbar{width:4px}
#msgs::-webkit-scrollbar-track{background:transparent}
#msgs::-webkit-scrollbar-thumb{background:#252535;border-radius:4px}
</style>
</head>
<body>
<div class="header">
  <div class="dot" id="dot"></div>
  <div>
    <div class="hname">Kora</div>
    <div class="hsub" id="sub">connecting&hellip;</div>
  </div>
</div>
<div id="msgs"></div>
<div class="bar">
  <input id="inp" type="text" placeholder="say something&hellip;" autocomplete="off">
  <button id="btn">Send</button>
</div>
<script>
let lastId = 0;
const msgs = document.getElementById('msgs');
const inp  = document.getElementById('inp');
const dot  = document.getElementById('dot');
const sub  = document.getElementById('sub');

function addBubble(sender, text){
  const wrap = document.createElement('div');
  wrap.className = 'bubble ' + sender;
  const lbl = document.createElement('div');
  lbl.className = 'label';
  lbl.textContent = sender === 'kora' ? 'KORA' : 'YOU';
  wrap.appendChild(lbl);
  const t = document.createElement('div');
  t.textContent = text;
  wrap.appendChild(t);
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
}

async function poll(){
  try{
    const r = await fetch('/poll?since=' + lastId);
    const data = await r.json();
    data.forEach(m => {
      addBubble(m.sender, m.text);
      if(m.id > lastId) lastId = m.id;
    });
    dot.className = 'dot on';
    sub.textContent = 'connected';
  }catch(e){
    dot.className = 'dot';
    sub.textContent = 'waiting for Kora…';
  }
}

async function send(){
  const text = inp.value.trim();
  if(!text) return;
  inp.value = '';
  try{
    await fetch('/send',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text})
    });
  }catch(e){}
}

document.getElementById('btn').addEventListener('click', send);
inp.addEventListener('keydown', e => { if(e.key === 'Enter') send(); });

setInterval(poll, 1000);
poll();
</script>
</body>
</html>"""
