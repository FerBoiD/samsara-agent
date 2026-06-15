# ============================================================
#  KoraBody.gd
#
#  Kora's physical presence inside the sphere.
#  State machine driven entirely by live drive data from DrivesBridge.
#
#  States:
#    IDLE          — standing, occasional look-around
#    WANDER        — slow walk to random point (boredom)
#    WALK_TO_FOOD  — hunger seeking, walks to food bowl area
#    EAT           — at bowl, eating animation
#    SLEEPING      — at sleep spot, curled up breathing
#    WAKING        — slow stretch after sleep
#    STOMACH_ACHE  — hunger < 20, hunched over, moaning
#    ANXIOUS       — rapid head turns, small erratic steps
#    EXCITED       — fast bouncing movement
#
#  Attach to CharacterBody3D (Kora root node).
# ============================================================

extends CharacterBody3D

signal feed_requested        # Kora clicked food → tell bridge to feed
signal state_changed(s: String)

# --- Exported scene refs ---
@export var body_mesh:       MeshInstance3D
@export var head_mesh:       MeshInstance3D
@export var eye_left:        MeshInstance3D
@export var eye_right:       MeshInstance3D
@export var stomach_glow:    OmniLight3D
@export var zzz_particles:   GPUParticles3D
@export var footstep_audio:  AudioStreamPlayer3D
@export var stomp_audio:     AudioStreamPlayer3D  # stomach growl / pain sound
@export var breath_audio:    AudioStreamPlayer3D

# --- World positions (on the sphere floor, y = -8.5) ---
const FLOOR_Y      := -8.5
const HOME_POS     := Vector3( 0.0, -8.5,  3.0)
const FOOD_POS     := Vector3( 5.5, -8.5,  0.0)
const SLEEP_POS    := Vector3(-5.0, -8.5, -2.5)
const WANDER_RADIUS := 6.0

const ARRIVE_DIST  := 0.35

# --- State machine ---
enum State {
	IDLE, WANDER, WALK_TO_FOOD, EAT,
	SLEEPING, WAKING,
	STOMACH_ACHE, ANXIOUS, EXCITED
}

var current_state   := State.IDLE
var drives          := {}

# Movement
var target_pos      := HOME_POS
var base_speed      := 2.2
var current_speed   := 2.2

# Timers
var state_timer         := 0.0
var idle_look_timer     := 0.0
var eat_timer           := 0.0
var wander_pause        := 0.0
var stomach_hold_timer  := 0.0
var footstep_timer      := 0.0

# Eye material (StandardMaterial3D, set on ready)
var eye_mat: StandardMaterial3D

# Stomach ache oscillator
var _stomach_phase := 0.0

# Last known drives for delta-detection
var _last_sleeping := false
var _last_hunger   := 80.0


func _ready() -> void:
	position = HOME_POS
	target_pos = HOME_POS

	# Create eye emissive material
	eye_mat = StandardMaterial3D.new()
	eye_mat.emission_enabled = true
	eye_mat.emission = Color.WHITE
	eye_mat.emission_energy_multiplier = 2.0
	if eye_left:  eye_left.set_surface_override_material(0, eye_mat)
	if eye_right: eye_right.set_surface_override_material(0, eye_mat)

	if stomach_glow:
		stomach_glow.light_energy = 0.0

	if zzz_particles:
		zzz_particles.emitting = false

	_set_state(State.IDLE)


func on_drives_updated(d: Dictionary) -> void:
	drives = d

	# Detect sleep start/end
	var now_sleeping: bool = d.get("sleeping", false)
	if now_sleeping and not _last_sleeping:
		_set_state(State.SLEEPING)
	elif not now_sleeping and _last_sleeping:
		_set_state(State.WAKING)
	_last_sleeping = now_sleeping

	_last_hunger = d.get("hunger", 80.0)


func _physics_process(delta: float) -> void:
	if drives.is_empty():
		return

	state_timer += delta
	_tick_state(delta)
	_apply_drive_visuals(delta)
	_move_toward_target(delta)
	_tick_footsteps(delta)


# ===========================================================
#  STATE MACHINE
# ===========================================================
func _tick_state(delta: float) -> void:
	var hunger:      float = drives.get("hunger",      80.0)
	var energy:      float = drives.get("energy",      90.0)
	var anxiety:     float = drives.get("anxiety",     10.0)
	var boredom:     float = drives.get("boredom",     20.0)
	var excitement:  float = drives.get("excitement",   5.0)
	var sleeping:    bool  = drives.get("sleeping",   false)

	match current_state:

		State.IDLE:
			# Gaze around occasionally
			idle_look_timer += delta
			if idle_look_timer > randf_range(3.0, 7.0):
				idle_look_timer = 0.0
				_look_random()

			# Transitions
			if sleeping:
				_set_state(State.SLEEPING); return
			if hunger < 18.0:
				_set_state(State.STOMACH_ACHE); return
			if hunger < 55.0 and state_timer > 4.0:
				_set_state(State.WALK_TO_FOOD); return
			if anxiety > 65.0:
				_set_state(State.ANXIOUS); return
			if excitement > 72.0:
				_set_state(State.EXCITED); return
			if boredom > 45.0 and state_timer > 8.0:
				_set_state(State.WANDER); return

		State.WANDER:
			if sleeping:
				_set_state(State.SLEEPING); return
			if hunger < 18.0:
				_set_state(State.STOMACH_ACHE); return
			if hunger < 50.0:
				_set_state(State.WALK_TO_FOOD); return
			# Arrived at wander target → pause then idle
			if position.distance_to(target_pos) < ARRIVE_DIST:
				wander_pause += delta
				if wander_pause > randf_range(1.5, 4.0):
					wander_pause = 0.0
					_set_state(State.IDLE)

		State.WALK_TO_FOOD:
			if sleeping:
				_set_state(State.SLEEPING); return
			if hunger < 18.0:
				_set_state(State.STOMACH_ACHE); return
			if hunger > 80.0:
				_set_state(State.IDLE); return
			# Arrived at bowl
			if position.distance_to(FOOD_POS) < ARRIVE_DIST + 0.3:
				_set_state(State.EAT); return

		State.EAT:
			eat_timer += delta
			# Bob down-up eating animation
			var bob := sinf(eat_timer * 5.0) * 0.12
			if body_mesh:
				body_mesh.position.y = bob
			# After 3 seconds, send feed request and go idle
			if eat_timer > 3.0:
				eat_timer = 0.0
				emit_signal("feed_requested")
				_set_state(State.IDLE)

		State.SLEEPING:
			# Zzz particles
			if zzz_particles:
				zzz_particles.emitting = true
			# Slow breathing scale on body
			var breath := 1.0 + sinf(state_timer * 0.6) * 0.025
			if body_mesh:
				body_mesh.scale = Vector3(1.0, breath, 1.0)
			if not drives.get("sleeping", false):
				_set_state(State.WAKING)

		State.WAKING:
			if zzz_particles:
				zzz_particles.emitting = false
			# Stretch: scale Y up then back
			var stretch := 1.0 + sinf(clampf(state_timer / 2.0, 0.0, PI)) * 0.18
			if body_mesh:
				body_mesh.scale = Vector3(1.0, stretch, 1.0)
			if state_timer > 2.5:
				_set_state(State.IDLE)

		State.STOMACH_ACHE:
			# Hunch: lean forward (tilt body_mesh), glow pulses in _apply_drive_visuals
			if body_mesh:
				body_mesh.rotation_degrees.x = lerpf(body_mesh.rotation_degrees.x, 25.0, 0.05)
			stomach_hold_timer += delta
			if hunger > 25.0:
				stomach_hold_timer = 0.0
				_set_state(State.IDLE)
			elif stomach_hold_timer > 3.0:
				stomach_hold_timer = 0.0
				_set_state(State.WALK_TO_FOOD)

		State.ANXIOUS:
			# Rapid small random steps
			if state_timer > randf_range(0.4, 1.2):
				state_timer = 0.0
				var jitter := Vector3(randf_range(-1.5, 1.5), 0.0, randf_range(-1.5, 1.5))
				target_pos = position + jitter
				target_pos.y = FLOOR_Y
			if drives.get("anxiety", 10.0) < 45.0:
				_set_state(State.IDLE)

		State.EXCITED:
			# Bounce: vertical offset oscillation (handled via body_mesh.position.y)
			var bounce := absf(sinf(state_timer * 5.5)) * 0.22
			if body_mesh:
				body_mesh.position.y = bounce
			if drives.get("excitement", 5.0) < 40.0:
				if body_mesh:
					body_mesh.position.y = 0.0
				_set_state(State.IDLE)


func _set_state(s: State) -> void:
	var prev := current_state
	current_state = s
	state_timer   = 0.0

	match s:
		State.IDLE:
			target_pos = HOME_POS
			current_speed = base_speed
			if body_mesh:
				body_mesh.rotation_degrees.x = 0.0
				body_mesh.scale = Vector3.ONE

		State.WANDER:
			current_speed = base_speed * 0.65
			target_pos = _random_floor_point()

		State.WALK_TO_FOOD:
			current_speed = base_speed * 0.85
			target_pos = FOOD_POS

		State.EAT:
			target_pos = position  # stop
			current_speed = 0.0

		State.SLEEPING:
			current_speed = base_speed
			target_pos = SLEEP_POS
			if breath_audio:
				breath_audio.play()

		State.WAKING:
			current_speed = 0.0
			target_pos = SLEEP_POS
			if breath_audio:
				breath_audio.stop()

		State.STOMACH_ACHE:
			current_speed = base_speed * 0.3

		State.ANXIOUS:
			current_speed = base_speed * 1.3

		State.EXCITED:
			current_speed = base_speed * 1.5
			target_pos = HOME_POS

	if s != prev:
		emit_signal("state_changed", _state_name(s))


# ===========================================================
#  DRIVE VISUALS
# ===========================================================
func _apply_drive_visuals(delta: float) -> void:
	if drives.is_empty():
		return

	var hunger:     float = drives.get("hunger",     80.0)
	var mood:       float = drives.get("mood",        0.0)
	var anxiety:    float = drives.get("anxiety",    10.0)
	var dominant:   String = drives.get("dominant", "neutral")

	# --- Movement speed modulated by energy ---
	var energy := drives.get("energy", 90.0)
	current_speed = base_speed * clampf(energy / 80.0, 0.3, 1.4)

	# --- Eye colour by dominant emotion ---
	if eye_mat:
		var target_eye := _emotion_eye_color(dominant, hunger)
		eye_mat.emission = eye_mat.emission.lerp(target_eye, delta * 2.0)
		eye_mat.emission_energy_multiplier = 2.0 + sinf(state_timer * 2.0) * 0.4

	# --- Stomach glow (hunger pain) ---
	_stomach_phase += delta * 3.5
	if stomach_glow:
		if hunger < 22.0:
			var pulse := (sinf(_stomach_phase) + 1.0) * 0.5
			stomach_glow.light_energy = lerpf(stomach_glow.light_energy,
				0.6 + pulse * 1.2, delta * 4.0)
			stomach_glow.light_color = Color(1.0, 0.3, 0.05)
			# Play growl sound
			if stomp_audio and not stomp_audio.playing:
				stomp_audio.play()
		elif hunger < 40.0:
			stomach_glow.light_energy = lerpf(stomach_glow.light_energy,
				0.15, delta * 2.0)
			stomach_glow.light_color = Color(1.0, 0.55, 0.1)
			if stomp_audio and stomp_audio.playing:
				stomp_audio.stop()
		else:
			stomach_glow.light_energy = lerpf(stomach_glow.light_energy,
				0.0, delta * 3.0)
			if stomp_audio and stomp_audio.playing:
				stomp_audio.stop()

	# --- Mood: slight body tint ---
	if body_mesh and body_mesh.get_surface_override_material(0):
		var mat := body_mesh.get_surface_override_material(0) as StandardMaterial3D
		if mat:
			var mood_norm := (mood + 100.0) / 200.0  # 0..1
			mat.albedo_color = Color(
				lerpf(0.55, 0.88, mood_norm),
				lerpf(0.55, 0.88, mood_norm),
				lerpf(0.65, 0.92, mood_norm)
			)

	# --- Anxiety: slight head shake ---
	if head_mesh and anxiety > 50.0:
		var shake := sinf(state_timer * 15.0) * ((anxiety - 50.0) / 50.0) * 2.5
		head_mesh.rotation_degrees.z = shake


# ===========================================================
#  MOVEMENT
# ===========================================================
func _move_toward_target(delta: float) -> void:
	if current_speed <= 0.0:
		velocity = Vector3.ZERO
		move_and_slide()
		return

	var dir := target_pos - position
	dir.y = 0.0
	if dir.length() < ARRIVE_DIST:
		velocity = Vector3.ZERO
		# Face target anyway
	else:
		velocity = dir.normalized() * current_speed
		# Rotate body toward movement direction
		var face := Vector3(velocity.x, 0.0, velocity.z)
		if face.length() > 0.01:
			var target_rot := atan2(-face.x, -face.z)
			rotation.y = lerpf(rotation.y, target_rot, delta * 6.0)

	velocity.y = -9.8 * delta  # gravity keeps on floor
	move_and_slide()
	# Snap to floor Y
	position.y = FLOOR_Y


func _tick_footsteps(delta: float) -> void:
	footstep_timer += delta
	var step_interval := 0.45 / maxf(current_speed / base_speed, 0.1)
	if velocity.length() > 0.3 and footstep_timer > step_interval:
		footstep_timer = 0.0
		if footstep_audio and not footstep_audio.playing:
			footstep_audio.pitch_scale = randf_range(0.9, 1.1)
			footstep_audio.play()


# ===========================================================
#  UTILITY
# ===========================================================
func _random_floor_point() -> Vector3:
	var angle  := randf() * TAU
	var radius := randf_range(1.0, WANDER_RADIUS)
	return Vector3(cos(angle) * radius, FLOOR_Y, sin(angle) * radius)


func _look_random() -> void:
	# Just rotate head to a random yaw
	if head_mesh:
		head_mesh.rotation_degrees.y = randf_range(-60.0, 60.0)


func _emotion_eye_color(dominant: String, hunger: float) -> Color:
	match dominant:
		"hunger":      return Color(1.0,  0.45, 0.05)
		"anxiety":     return Color(0.9,  0.9,  0.1)
		"frustration": return Color(1.0,  0.3,  0.1)
		"excitement":  return Color(0.1,  0.9,  1.0)
		"boredom":     return Color(0.5,  0.5,  0.55)
		"dying":       return Color(1.0,  0.05, 0.05)
		"curiosity":   return Color(0.3,  0.7,  1.0)
		"rest":        return Color(0.4,  0.4,  0.8)
		_:
			# neutral — warm white shifted by hunger
			var h_norm := hunger / 100.0
			return Color(1.0, 0.8 + h_norm * 0.2, 0.7 + h_norm * 0.3)


func _state_name(s: State) -> String:
	match s:
		State.IDLE:         return "idle"
		State.WANDER:       return "wander"
		State.WALK_TO_FOOD: return "walk_to_food"
		State.EAT:          return "eat"
		State.SLEEPING:     return "sleeping"
		State.WAKING:       return "waking"
		State.STOMACH_ACHE: return "stomach_ache"
		State.ANXIOUS:      return "anxious"
		State.EXCITED:      return "excited"
		_:                  return "unknown"
