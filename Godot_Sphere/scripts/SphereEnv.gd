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
	var mood:      float  = d.get("mood",      0.0)
	var anxiety:   float  = d.get("anxiety",  10.0)
	var hunger:    float  = d.get("hunger",   80.0)
	var excitement:float  = d.get("excitement", 5.0)
	var dominant:  String = d.get("dominant", "neutral")
	var sleeping:  bool   = d.get("sleeping", false)

	# --- Target wall color ---
	if dominant == "dying":
		_target_color = Color(0.42, 0.08, 0.08)   # dark blood red
	elif sleeping:
		_target_color = Color(0.08, 0.1, 0.2)     # deep navy
	elif hunger < 20.0:
		# Dim red when in pain
		var intensity := 1.0 - hunger / 20.0
		_target_color = Color.WHITE.lerp(Color(0.6, 0.15, 0.1), intensity * 0.5)
	else:
		# Mood → colour temperature
		# mood: -100 (sad cold blue) to +100 (happy warm cream)
		var mood_norm := (mood + 100.0) / 200.0   # 0..1
		var warm := Color(0.99, 0.97, 0.93)        # happy warm white
		var cold := Color(0.88, 0.92, 1.00)        # sad cool white
		_target_color = cold.lerp(warm, mood_norm)

	# --- Particle effects ---
	if anxiety_particles:
		anxiety_particles.emitting = anxiety > 55.0

	if sparkle_particles:
		sparkle_particles.emitting = excitement > 65.0


func _process(delta: float) -> void:
	if _sphere_mat:
		_current_color = _current_color.lerp(_target_color, delta * 0.6)
		_sphere_mat.albedo_color = _current_color
