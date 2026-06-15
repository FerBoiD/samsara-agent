# ============================================================
#  HUD.gd
#
#  Minimal observational overlay.
#  Toggle with Tab. Hidden by default — observatory mode.
#
#  Shows:
#    - Drive bars (hunger, energy, mood, anxiety, boredom)
#    - Age in days
#    - Current state (sleeping, stomach ache, etc.)
#    - Day/night indicator
#    - Bridge connection status
#
#  Attach to CanvasLayer > Control.
# ============================================================

extends Control

@export var day_night_ref: Node   # DayNight node for time info
@export var kora_body_ref: Node   # KoraBody node for state

# Bar nodes — assign in editor or auto-find by name
var _bars := {}
var _state_label: Label
var _age_label:   Label
var _time_label:  Label
var _conn_label:  Label

var _drives  := {}
var _visible := false
var _conn    := false


func _ready() -> void:
	visible = false
	_create_ui()


func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		if event.pressed and event.keycode == KEY_TAB:
			_visible = not _visible
			visible  = _visible


func on_drives_updated(d: Dictionary) -> void:
	_drives = d
	_update_bars()


func on_state_changed(s: String) -> void:
	if _state_label:
		_state_label.text = "state: " + s


func on_connected() -> void:
	_conn = true
	if _conn_label:
		_conn_label.text = "● connected"
		_conn_label.modulate = Color(0.2, 1.0, 0.4)


func on_disconnected() -> void:
	_conn = false
	if _conn_label:
		_conn_label.text = "○ not connected"
		_conn_label.modulate = Color(1.0, 0.3, 0.3)


func _process(_delta: float) -> void:
	if not _visible:
		return
	_update_time()
	if _age_label and not _drives.is_empty():
		_age_label.text = "day %.1f / 45" % _drives.get("age_days", 0.0)


# ----------------------------------------------------------
#  UI CREATION (procedural — no scene needed)
# ----------------------------------------------------------
func _create_ui() -> void:
	var panel := PanelContainer.new()
	panel.position = Vector2(16, 16)
	panel.custom_minimum_size = Vector2(230, 0)

	var style := StyleBoxFlat.new()
	style.bg_color         = Color(0.04, 0.04, 0.07, 0.78)
	style.border_width_left  = 1
	style.border_color     = Color(0.3, 0.3, 0.45, 0.6)
	style.corner_radius_top_left     = 6
	style.corner_radius_top_right    = 6
	style.corner_radius_bottom_left  = 6
	style.corner_radius_bottom_right = 6
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 5)
	panel.add_child(vbox)

	# Title
	var title := Label.new()
	title.text      = "KORA — OBSERVER"
	title.modulate  = Color(0.6, 0.6, 0.9)
	title.add_theme_font_size_override("font_size", 11)
	vbox.add_child(title)

	_add_separator(vbox)

	# Drive bars
	var drive_defs := [
		["hunger",        Color(1.0,  0.6,  0.1)],
		["thirst",        Color(0.3,  0.75, 1.0)],
		["energy",        Color(0.2,  0.9,  0.4)],
		["mood",          Color(0.5,  0.7,  1.0)],
		["anxiety",       Color(0.9,  0.9,  0.2)],
		["boredom",       Color(0.5,  0.5,  0.6)],
		["nausea",        Color(0.5,  0.85, 0.4)],
		["muscle_fatigue",Color(0.8,  0.5,  0.3)],
		["sickness",      Color(0.65, 0.75, 0.55)],
	]
	for dd in drive_defs:
		_create_bar_row(vbox, dd[0], dd[1])

	_add_separator(vbox)

	# Labels
	_age_label   = _make_label(vbox, "day 0 / 45")
	_time_label  = _make_label(vbox, "time: --:--")
	_state_label = _make_label(vbox, "state: idle")
	_conn_label  = _make_label(vbox, "○ not connected")
	_conn_label.modulate = Color(1.0, 0.3, 0.3)

	_add_separator(vbox)

	var hint := Label.new()
	hint.text     = "[Tab] toggle"
	hint.modulate = Color(0.35, 0.35, 0.4)
	hint.add_theme_font_size_override("font_size", 9)
	vbox.add_child(hint)


func _create_bar_row(parent: VBoxContainer, name: String, color: Color) -> void:
	var hbox := HBoxContainer.new()
	parent.add_child(hbox)

	var lbl := Label.new()
	lbl.text      = name.substr(0, 6).lpad(6)
	lbl.modulate  = Color(0.7, 0.7, 0.8)
	lbl.add_theme_font_size_override("font_size", 10)
	lbl.custom_minimum_size = Vector2(52, 0)
	hbox.add_child(lbl)

	var bar := ProgressBar.new()
	bar.min_value = 0.0
	bar.max_value = 100.0
	bar.value     = 50.0
	bar.custom_minimum_size = Vector2(130, 12)
	bar.show_percentage = false

	var bar_style := StyleBoxFlat.new()
	bar_style.bg_color = color
	bar_style.corner_radius_top_left     = 3
	bar_style.corner_radius_top_right    = 3
	bar_style.corner_radius_bottom_left  = 3
	bar_style.corner_radius_bottom_right = 3
	bar.add_theme_stylebox_override("fill", bar_style)

	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = Color(0.12, 0.12, 0.16)
	bar.add_theme_stylebox_override("background", bg_style)

	hbox.add_child(bar)
	_bars[name] = bar


func _update_bars() -> void:
	for key in _bars:
		var bar: ProgressBar = _bars[key]
		var val: float = _drives.get(key, 50.0)
		# Mood is -100 to +100 — remap
		if key == "mood":
			val = (val + 100.0) / 2.0
		bar.value = lerpf(bar.value, val, 0.15)


func _update_time() -> void:
	if _time_label:
		var t := Time.get_time_dict_from_system()
		_time_label.text = "time: %02d:%02d" % [t["hour"], t["minute"]]


func _add_separator(parent: VBoxContainer) -> void:
	var sep := HSeparator.new()
	sep.modulate = Color(0.25, 0.25, 0.35, 0.6)
	parent.add_child(sep)


func _make_label(parent: VBoxContainer, text: String) -> Label:
	var l := Label.new()
	l.text     = text
	l.modulate = Color(0.65, 0.65, 0.75)
	l.add_theme_font_size_override("font_size", 10)
	parent.add_child(l)
	return l
