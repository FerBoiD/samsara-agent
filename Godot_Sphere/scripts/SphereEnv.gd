# ============================================================
#  SphereEnv.gd
#
#  The sphere interior reacts subtly to Kora's emotional state.
#
#  Effects:
#    - Sphere wall tint shifts with mood (warm=happy, cool=sad)
#    - Anxiety causes a faint heat-shimmer particle effect
#    - Excitement adds a faint sparkle layer
#    - Hunger critical: dim red bleed on the walls
#    - Sleep: walls deepen to dark navy
#    - Dying: walls slowly pulse deep red
#
#  Attach to Node3D child of Main.
# ============================================================

extends Node

@export var sphere_mesh:       MeshInstance3D
@export var anxiety_particles: GPUParticles3D
@export var sparkle_particles: GPUParticles3D

var _sphere_mat: StandardMaterial3D
var _target_color := Color.WHITE
var _current_color := Color.WHITE


func _ready() -> void:
	if sphere_mesh:
		# Clone the material so we can modify it per-instance
		_sphere_mat = sphere_mesh.get_active_material(0).duplicate() as StandardMaterial3D
		if _sphere_mat:
			sphere_mesh.set_surface_override_material(0, _sphere_mat)

	if anxiety_particles:
		anxiety_particles.emitting = false
	if sparkle_particles:
		sparkle_particles.emitting = false


func on_drives_updated(d: Dictionary) -> void:
	var mood:      float  = d.get("mood",       0.0)
	var anxiety:   float  = d.get("anxiety",   10.0)
	var hunger:    float  = d.get("hunger",    80.0)
	var excitement:float  = d.get("excitement", 5.0)
	var dominant:  String = d.get("dominant",  "neutral")
	var sleeping:  bool   = d.get("sleeping",  false)
	var sickness:  float  = d.get("sickness",   0.0)
	var body_temp: float  = d.get("body_temp", 37.0)

	# --- Target wall color ---
	if dominant == "dying":
		_target_color = Color(0.42, 0.08, 0.08)     # dark blood red
	elif sleeping:
		_target_color = Color(0.08, 0.10, 0.20)     # deep navy
	elif sickness > 35.0:
		# Pale sickly green tint when ill
		var t := sickness / 100.0
		_target_color = Color.WHITE.lerp(Color(0.82, 0.92, 0.80), t * 0.4)
	elif body_temp < 36.1:
		# Cold blue tint when shivering
		_target_color = Color.WHITE.lerp(Color(0.85, 0.90, 1.00), 0.35)
	elif hunger < 20.0:
		var intensity := 1.0 - hunger / 20.0
		_target_color = Color.WHITE.lerp(Color(0.60, 0.15, 0.10), intensity * 0.5)
	else:
		# Mood → colour temperature
		var mood_norm := (mood + 100.0) / 200.0
		var warm := Color(0.99, 0.97, 0.93)  # happy warm white
		var cold := Color(0.88, 0.92, 1.00)  # sad cool white
		_target_color = cold.lerp(warm, mood_norm)

	# --- Particles ---
	if anxiety_particles:
		anxiety_particles.emitting = anxiety > 55.0
	if sparkle_particles:
		sparkle_particles.emitting = excitement > 65.0


func _process(delta: float) -> void:
	if _sphere_mat:
		_current_color = _current_color.lerp(_target_color, delta * 0.6)
		_sphere_mat.albedo_color = _current_color
