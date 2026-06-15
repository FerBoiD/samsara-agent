# ============================================================
#  FoodBowl.gd
#
#  The food bowl in Kora's world.
#  Clicking it sends a feed command to the Python bridge.
#  Glows when Kora is nearby / hungry.
#  Plays a ripple animation when food is added.
#
#  Attach to MeshInstance3D (the bowl mesh).
#  Requires a CollisionShape3D sibling (StaticBody3D or Area3D).
# ============================================================

extends Node3D

signal bowl_clicked     # Main connects this to DrivesBridge.send_feed()

@export var glow_light: OmniLight3D
@export var food_audio: AudioStreamPlayer3D

var _hunger     := 80.0
var _kora_near  := false
var _phase      := 0.0
var _just_fed   := false
var _fed_timer  := 0.0


func _ready() -> void:
	if glow_light:
		glow_light.light_energy = 0.0
		glow_light.light_color  = Color(1.0, 0.75, 0.2)


func on_drives_updated(d: Dictionary) -> void:
	_hunger = d.get("hunger", 80.0)


func on_kora_near(near: bool) -> void:
	_kora_near = near


# Called when caretaker clicks the bowl in Godot (Area3D input_event)
func _on_area_input_event(_camera, event, _pos, _normal, _shape) -> void:
	if event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			emit_signal("bowl_clicked")
			_play_feed_animation()


func _play_feed_animation() -> void:
	_just_fed  = true
	_fed_timer = 0.0
	if food_audio:
		food_audio.play()


func _process(delta: float) -> void:
	_phase += delta * 2.5
	_fed_timer += delta

	if _just_fed and _fed_timer > 1.5:
		_just_fed = false

	if glow_light:
		# Glow intensity: hungry + Kora nearby = brightest
		var base_glow := 0.0
		if _hunger < 55.0:
			base_glow = (55.0 - _hunger) / 55.0 * 0.8
		if _kora_near:
			base_glow = maxf(base_glow, 0.5)
		if _just_fed:
			base_glow = 1.5

		var pulse := sinf(_phase) * 0.12
		glow_light.light_energy = lerpf(glow_light.light_energy,
			base_glow + pulse, delta * 3.0)
