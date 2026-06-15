# ============================================================
#  WaterBowl.gd
#
#  The water bowl — counterpart to FoodBowl.
#  Glows cyan when Kora is thirsty.
#  Clicking sends "drink" to the Python bridge.
#
#  Attach to Node3D (the bowl root).
#  Position in world: Vector3(-3.0, -8.5, 5.0)
# ============================================================

extends Node3D

signal bowl_clicked   # Main connects → bridge.send_drink()

@export var glow_light: OmniLight3D
@export var drink_audio: AudioStreamPlayer3D

var _thirst := 80.0
var _phase  := 0.0


func _ready() -> void:
	if glow_light:
		glow_light.light_energy = 0.0
		glow_light.light_color  = Color(0.35, 0.75, 1.0)


func on_drives_updated(d: Dictionary) -> void:
	_thirst = d.get("thirst", 80.0)


func _on_area_input_event(_camera, event, _pos, _normal, _shape) -> void:
	if event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			emit_signal("bowl_clicked")
			if drink_audio:
				drink_audio.play()


func _process(delta: float) -> void:
	_phase += delta * 3.0
	if glow_light:
		var base_glow := 0.0
		if _thirst < 38.0:
			base_glow = (38.0 - _thirst) / 38.0 * 0.9
		var pulse := sinf(_phase) * 0.10
		glow_light.light_energy = lerpf(glow_light.light_energy,
			base_glow + pulse, delta * 3.0)
