# ============================================================
#  ChatOverlay.gd
#
#  Always-visible chat bar at the bottom of the sphere window.
#  Tab toggles the stats HUD — this stays on regardless.
#
#  Contains:
#    - Connection indicator dot
#    - Text input ("talk to Kora...")
#    - Send button (also triggered by Enter)
#    - Feed button  → bridge.send_feed()
#    - Drink button → bridge.send_drink()
#
#  Attach to a CanvasLayer node (separate from HUD's CanvasLayer).
#  Main.gd connects message_sent to bridge and buttons.
# ============================================================

extends CanvasLayer

signal message_sent(text: String)
signal feed_pressed
signal drink_pressed

var _input: LineEdit
var _conn_dot: Label


func _ready() -> void:
	layer = 10   # render above HUD

	# --- Panel backing ---
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	panel.offset_bottom = 0
	panel.offset_top    = -46

	var style := StyleBoxFlat.new()
	style.bg_color              = Color(0.03, 0.03, 0.07, 0.88)
	style.border_width_top      = 1
	style.border_color          = Color(0.18, 0.18, 0.35, 0.9)
	style.content_margin_left   = 8
	style.content_margin_right  = 8
	style.content_margin_top    = 5
	style.content_margin_bottom = 5
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	# --- Row ---
	var hbox := HBoxContainer.new()
	hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	hbox.add_theme_constant_override("separation", 7)
	panel.add_child(hbox)

	# Connection dot
	_conn_dot = Label.new()
	_conn_dot.text    = "○"
	_conn_dot.modulate = Color(1.0, 0.3, 0.3)
	_conn_dot.add_theme_font_size_override("font_size", 16)
	_conn_dot.custom_minimum_size = Vector2(18, 0)
	hbox.add_child(_conn_dot)

	# Text input
	_input = LineEdit.new()
	_input.placeholder_text = "talk to Kora..."
	_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_input.return_pressed.connect(_on_send)
	_input.add_theme_font_size_override("font_size", 13)
	hbox.add_child(_input)

	# Send button
	var send_btn := Button.new()
	send_btn.text = "send"
	send_btn.pressed.connect(_on_send)
	hbox.add_child(send_btn)

	# Feed button
	var feed_btn := Button.new()
	feed_btn.text    = "🍽 feed"
	feed_btn.modulate = Color(1.0, 0.80, 0.35)
	feed_btn.pressed.connect(_on_feed)
	hbox.add_child(feed_btn)

	# Drink button
	var drink_btn := Button.new()
	drink_btn.text    = "💧 drink"
	drink_btn.modulate = Color(0.45, 0.85, 1.0)
	drink_btn.pressed.connect(_on_drink)
	hbox.add_child(drink_btn)


func on_connected() -> void:
	if _conn_dot:
		_conn_dot.text    = "●"
		_conn_dot.modulate = Color(0.25, 1.0, 0.45)


func on_disconnected() -> void:
	if _conn_dot:
		_conn_dot.text    = "○"
		_conn_dot.modulate = Color(1.0, 0.3, 0.3)


# ----------------------------------------------------------
func _on_send() -> void:
	var text := _input.text.strip_edges()
	if text.length() > 0:
		emit_signal("message_sent", text)
		_input.text = ""


func _on_feed() -> void:
	emit_signal("feed_pressed")


func _on_drink() -> void:
	emit_signal("drink_pressed")
