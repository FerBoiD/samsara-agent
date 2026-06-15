# ============================================================
#  DrivesBridge.gd
#
#  TCP client connecting to the Python godot_bridge.py server.
#  Polls drive state every 500ms and emits drives_updated signal.
#  Auto-reconnects on disconnect.
#
#  Attach to an autoload Node or to Main.
# ============================================================

extends Node

signal drives_updated(state: Dictionary)
signal connected_to_kora
signal disconnected_from_kora

const HOST := "127.0.0.1"
const PORT := 9999
const POLL_INTERVAL := 0.5

var state: Dictionary = {
	"hunger":      80.0,
	"energy":      90.0,
	"mood":         0.0,
	"anxiety":     10.0,
	"frustration":  5.0,
	"boredom":     20.0,
	"excitement":   5.0,
	"dominant":    "neutral",
	"age_days":     0.0,
	"sleeping":    false,
	"cog_state":   "active",
	"aging_phase": "healthy",
}

var _socket   := StreamPeerTCP.new()
var _connected := false
var _timer     := 0.0
var _buf       := ""
var _reconnect_timer := 0.0
const RECONNECT_INTERVAL := 3.0


func _ready() -> void:
	_try_connect()


func _process(delta: float) -> void:
	_reconnect_timer += delta

	if not _connected:
		if _reconnect_timer >= RECONNECT_INTERVAL:
			_reconnect_timer = 0.0
			_try_connect()
		return

	_socket.poll()
	var status := _socket.get_status()

	if status == StreamPeerTCP.STATUS_NONE or status == StreamPeerTCP.STATUS_ERROR:
		_on_disconnect()
		return

	if status != StreamPeerTCP.STATUS_CONNECTED:
		return

	# Read available bytes
	var available := _socket.get_available_bytes()
	if available > 0:
		_buf += _socket.get_utf8_string(available)
		_parse_buffer()

	_timer += delta
	if _timer >= POLL_INTERVAL:
		_timer = 0.0


func send_command(cmd: String) -> void:
	if not _connected:
		return
	_socket.put_utf8_string(cmd + "\n")


func send_feed() -> void:
	send_command("feed")


# ----------------------------------------------------------
#  INTERNAL
# ----------------------------------------------------------
func _try_connect() -> void:
	_socket = StreamPeerTCP.new()
	var err := _socket.connect_to_host(HOST, PORT)
	if err == OK:
		_connected = true
		_buf = ""
		emit_signal("connected_to_kora")
		print("[BRIDGE] Connected to Kora on port ", PORT)
	else:
		_connected = false


func _on_disconnect() -> void:
	_connected = false
	_socket.disconnect_from_host()
	emit_signal("disconnected_from_kora")
	print("[BRIDGE] Disconnected — will retry in ", RECONNECT_INTERVAL, "s")


func _parse_buffer() -> void:
	while "\n" in _buf:
		var idx   := _buf.find("\n")
		var line  := _buf.substr(0, idx).strip_edges()
		_buf = _buf.substr(idx + 1)
		if line.is_empty():
			continue
		var parsed := JSON.parse_string(line)
		if parsed is Dictionary:
			state = parsed
			emit_signal("drives_updated", state)
