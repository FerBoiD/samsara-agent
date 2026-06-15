# ============================================================
#  KoraBody.gd  — v2
#
#  State machine for Kora's physical presence.
#  Drive + body state → movement, posture, visuals.
#
#  States:
#    IDLE          — standing, occasional look-around
#    WANDER        — slow walk (boredom / restlessness)
#    WALK_TO_FOOD  — hunger seeking
#    EAT           — at food bowl, eating animation
#    WALK_TO_WATER — thirst seeking
#    DRINK_WATER   — at water bowl, drinking animation
#    SLEEPING      — at sleep spot, ZZZ particles
#    WAKING        — stretch after sleep
#    STOMACH_ACHE  — hunger < 20, hunched, glow
#    NAUSEOUS      — stomach turning, sways, blocks food
#    ANXIOUS       — rapid small steps, head shake
#    EXCITED       — fast bouncing
#    SHIVERING     — cold body temp, huddle pulse
#    SICK          — slow, hunched, very dim eyes
#    FATIGUED      — sits still, resists wander
#
#  Attach to CharacterBody3D (Kora root node).
# ============================================================

extends CharacterBody3D

signal feed_requested
signal drink_requested
signal state_changed(s: String)

# --- Exported scene refs ---
@export var body_mesh:       MeshInstance3D
@export var head_mesh:       MeshInstance3D
@export var eye_left:        MeshInstance3D
@export var eye_right:       MeshInstance3D
@export var stomach_glow:    OmniLight3D
@export var zzz_particles:   GPUParticles3D
@export var footstep_audio:  AudioStreamPlayer3D
@export var stomp_audio:     AudioStreamPlayer3D
@export var breath_audio:    AudioStreamPlayer3D

# --- World positions ---
const FLOOR_Y       := -8.5
const HOME_POS      := Vector3( 0.0, FLOOR_Y,  3.0)
const FOOD_POS      := Vector3( 5.5, FLOOR_Y,  0.0)
const WATER_POS     := Vector3(-3.0, FLOOR_Y,  5.0)
const SLEEP_POS     := Vector3(-5.0, FLOOR_Y, -2.5)
const WANDER_RADIUS := 6.0
const ARRIVE_DIST   := 0.4

enum State {
	IDLE, WANDER,
	WALK_TO_FOOD, EAT,
	WALK_TO_WATER, DRINK_WATER,
	SLEEPING, WAKING,
	STOMACH_ACHE, NAUSEOUS,
	ANXIOUS, EXCITED,
	SHIVERING, SICK, FATIGUED
}

var current_state   := State.IDLE
var drives          := {}
var body_state      := {}

var target_pos      := HOME_POS
var base_speed      := 2.2
var current_speed   := 2.2

var state_timer         := 0.0
var idle_look_timer     := 0.0
var eat_timer           := 0.0
var drink_timer         := 0.0
var wander_pause        := 0.0
var footstep_timer      := 0.0

var eye_mat:    StandardMaterial3D
var body_mat:   StandardMaterial3D

var _stomach_phase  := 0.0
var _shiver_phase   := 0.0
var _last_sleeping  := false


func _ready() -> void:
	position   = HOME_POS
	target_pos = HOME_POS

	# Eye emissive material
	eye_mat = StandardMaterial3D.new()
	eye_mat.emission_enabled           = true
	eye_mat.emission                   = Color.WHITE
	eye_mat.emission_energy_multiplier = 2.0
	if eye_left:  eye_left.set_surface_override_material(0, eye_mat)
	if eye_right: eye_right.set_surface_override_material(0, eye_mat)

	# Body colour material
	if body_mesh:
		body_mat = StandardMaterial3D.new()
		body_mat.albedo_color = Color(0.88, 0.86, 0.94)
		body_mat.roughness    = 0.8
		body_mesh.set_surface_override_material(0, body_mat)

	if stomach_glow:
		stomach_glow.light_energy = 0.0

	if zzz_particles:
		zzz_particles.emitting = false

	_set_state(State.IDLE)


# Called from Main.gd on drives_updated signal
# drives dict now includes body fields too (thirst, body_temp, etc.)
func on_drives_updated(d: Dictionary) -> void:
	drives     = d
	body_state = {
		"thirst":            d.get("thirst",            80.0),
		"body_temp":         d.get("body_temp",         37.0),
		"muscle_fatigue":    d.get("muscle_fatigue",     0.0),
		"blood_sugar_crash": d.get("blood_sugar_crash",  0.0),
		"nausea":            d.get("nausea",             0.0),
		"immune":            d.get("immune",           100.0),
		"sickness":          d.get("sickness",           0.0),
		"restlessness":      d.get("restlessness",       0.0),
	}

	var now_sleeping: bool = d.get("sleeping", false)
	if now_sleeping and not _last_sleeping:
		_set_state(State.SLEEPING)
	elif not now_sleeping and _last_sleeping:
		_set_state(State.WAKING)
	_last_sleeping = now_sleeping


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
	var sleeping:    bool  = drives.get("sleeping",  false)

	var thirst:      float = body_state.get("thirst",         80.0)
	var body_temp:   float = body_state.get("body_temp",      37.0)
	var nausea:      float = body_state.get("nausea",          0.0)
	var sickness:    float = body_state.get("sickness",        0.0)
	var fatigue:     float = body_state.get("muscle_fatigue",  0.0)
	var restless:    float = body_state.get("restlessness",    0.0)

	match current_state:

		State.IDLE:
			idle_look_timer += delta
			if idle_look_timer > randf_range(3.5, 8.0):
				idle_look_timer = 0.0
				_look_random()

			if sleeping:                              _set_state(State.SLEEPING); return
			if sickness > 45.0:                       _set_state(State.SICK); return
			if body_temp < 36.0 and state_timer > 2.0:_set_state(State.SHIVERING); return
			if nausea > 55.0:                         _set_state(State.NAUSEOUS); return
			if hunger < 18.0:                         _set_state(State.STOMACH_ACHE); return
			if fatigue > 78.0:                        _set_state(State.FATIGUED); return
			if anxiety > 65.0:                        _set_state(State.ANXIOUS); return
			if excitement > 72.0:                     _set_state(State.EXCITED); return
			if thirst < 32.0 and state_timer > 3.0:  _set_state(State.WALK_TO_WATER); return
			if hunger < 55.0 and state_timer > 4.0:  _set_state(State.WALK_TO_FOOD); return
			if (boredom > 45.0 or restless > 68.0) and state_timer > 8.0:
				_set_state(State.WANDER); return

		State.WANDER:
			if sleeping:            _set_state(State.SLEEPING); return
			if sickness > 45.0:     _set_state(State.SICK); return
			if hunger < 18.0:       _set_state(State.STOMACH_ACHE); return
			if nausea > 55.0:       _set_state(State.NAUSEOUS); return
			if hunger < 50.0:       _set_state(State.WALK_TO_FOOD); return
			if thirst < 30.0:       _set_state(State.WALK_TO_WATER); return
			if position.distance_to(target_pos) < ARRIVE_DIST:
				wander_pause += delta
				if wander_pause > randf_range(1.5, 4.0):
					wander_pause = 0.0
					_set_state(State.IDLE)

		State.WALK_TO_FOOD:
			if sleeping:            _set_state(State.SLEEPING); return
			if nausea > 60.0:       _set_state(State.NAUSEOUS); return
			if hunger < 18.0:       _set_state(State.STOMACH_ACHE); return
			if hunger > 82.0:       _set_state(State.IDLE); return
			if position.distance_to(FOOD_POS) < ARRIVE_DIST + 0.3:
				_set_state(State.EAT)

		State.EAT:
			eat_timer += delta
			var bob := sinf(eat_timer * 5.0) * 0.12
			if body_mesh: body_mesh.position.y = bob
			if eat_timer > 3.0:
				eat_timer = 0.0
				emit_signal("feed_requested")
				_set_state(State.IDLE)

		State.WALK_TO_WATER:
			if sleeping:        _set_state(State.SLEEPING); return
			if hunger < 18.0:   _set_state(State.STOMACH_ACHE); return
			if thirst > 85.0:   _set_state(State.IDLE); return
			if position.distance_to(WATER_POS) < ARRIVE_DIST + 0.3:
				_set_state(State.DRINK_WATER)

		State.DRINK_WATER:
			drink_timer += delta
			var bob := sinf(drink_timer * 4.0) * 0.08
			if body_mesh: body_mesh.position.y = bob
			if drink_timer > 2.5:
				drink_timer = 0.0
				emit_signal("drink_requested")
				_set_state(State.IDLE)

		State.SLEEPING:
			if zzz_particles: zzz_particles.emitting = true
			var breath_scale := 1.0 + sinf(state_timer * 0.55) * 0.025
			if body_mesh: body_mesh.scale = Vector3(1.0, breath_scale, 1.0)
			if not drives.get("sleeping", false): _set_state(State.WAKING)

		State.WAKING:
			if zzz_particles: zzz_particles.emitting = false
			var stretch := 1.0 + sinf(clampf(state_timer / 2.0, 0.0, PI)) * 0.18
			if body_mesh: body_mesh.scale = Vector3(1.0, stretch, 1.0)
			if state_timer > 2.5: _set_state(State.IDLE)

		State.STOMACH_ACHE:
			if body_mesh:
				body_mesh.rotation_degrees.x = lerpf(
					body_mesh.rotation_degrees.x, 28.0, 0.05)
			if hunger > 26.0:       _set_state(State.IDLE)
			elif state_timer > 3.5: _set_state(State.WALK_TO_FOOD)

		State.NAUSEOUS:
			# Sway side to side
			var sway := sinf(state_timer * 1.8) * 3.0
			if body_mesh: body_mesh.rotation_degrees.z = sway
			if nausea < 35.0:
				if body_mesh: body_mesh.rotation_degrees.z = 0.0
				_set_state(State.IDLE)

		State.ANXIOUS:
			if state_timer > randf_range(0.5, 1.4):
				state_timer = 0.0
				var jitter := Vector3(randf_range(-1.8, 1.8), 0.0, randf_range(-1.8, 1.8))
				target_pos = position + jitter
				target_pos.y = FLOOR_Y
			if anxiety < 40.0: _set_state(State.IDLE)

		State.EXCITED:
			var bounce := absf(sinf(state_timer * 5.5)) * 0.24
			if body_mesh: body_mesh.position.y = bounce
			if excitement < 38.0:
				if body_mesh: body_mesh.position.y = 0.0
				_set_state(State.IDLE)

		State.SHIVERING:
			_shiver_phase += delta * 18.0
			var shiver := sinf(_shiver_phase) * 0.04
			if body_mesh: body_mesh.scale = Vector3(1.0 + shiver, 1.0 - shiver, 1.0)
			if body_temp >= 36.3: _set_state(State.IDLE)

		State.SICK:
			if body_mesh:
				body_mesh.rotation_degrees.x = lerpf(
					body_mesh.rotation_degrees.x, 18.0, 0.03)
			if sickness < 25.0:
				if body_mesh: body_mesh.rotation_degrees.x = 0.0
				_set_state(State.IDLE)

		State.FATIGUED:
			# Crouch/shrink body to simulate sitting
			if body_mesh:
				body_mesh.scale = Vector3(1.0, lerpf(body_mesh.scale.y, 0.65, 0.04), 1.0)
			if fatigue < 50.0:
				if body_mesh: body_mesh.scale = Vector3.ONE
				_set_state(State.IDLE)


func _set_state(s: State) -> void:
	var prev := current_state
	current_state = s
	state_timer   = 0.0

	match s:
		State.IDLE:
			target_pos    = HOME_POS
			current_speed = base_speed
			if body_mesh:
				body_mesh.rotation_degrees = Vector3.ZERO
				body_mesh.scale            = Vector3.ONE
				body_mesh.position.y       = 0.0

		State.WANDER:
			current_speed = base_speed * 0.62
			target_pos    = _random_floor_point()

		State.WALK_TO_FOOD:
			current_speed = base_speed * 0.85
			target_pos    = FOOD_POS

		State.EAT:
			target_pos    = position
			current_speed = 0.0

		State.WALK_TO_WATER:
			current_speed = base_speed * 0.80
			target_pos    = WATER_POS

		State.DRINK_WATER:
			target_pos    = position
			current_speed = 0.0

		State.SLEEPING:
			current_speed = base_speed
			target_pos    = SLEEP_POS
			if breath_audio: breath_audio.play()

		State.WAKING:
			current_speed = 0.0
			if breath_audio: breath_audio.stop()

		State.STOMACH_ACHE:
			current_speed = base_speed * 0.28

		State.NAUSEOUS:
			current_speed = 0.0
			target_pos    = position

		State.ANXIOUS:
			current_speed = base_speed * 1.35

		State.EXCITED:
			current_speed = base_speed * 1.55
			target_pos    = HOME_POS

		State.SHIVERING:
			current_speed = base_speed * 0.35
			# Huddle toward centre
			target_pos = HOME_POS

		State.SICK:
			current_speed = base_speed * 0.22

		State.FATIGUED:
			current_speed = 0.0
			target_pos    = position

	if s != prev:
		emit_signal("state_changed", _state_name(s))


# ===========================================================
#  DRIVE VISUALS
# ===========================================================
func _apply_drive_visuals(delta: float) -> void:
	if drives.is_empty():
		return

	var dominant: String = drives.get("dominant", "neutral")
	var hunger:   float  = drives.get("hunger",   80.0)
	var mood:     float  = drives.get("mood",      0.0)
	var anxiety:  float  = drives.get("anxiety",  10.0)
	var energy:   float  = drives.get("energy",   90.0)

	var thirst:   float  = body_state.get("thirst",         80.0)
	var sickness: float  = body_state.get("sickness",        0.0)
	var crash:    float  = body_state.get("blood_sugar_crash", 0.0)

	# --- Movement speed from energy + sickness ---
	var speed_mult := clampf(energy / 80.0, 0.25, 1.4)
	if sickness > 30.0:
		speed_mult *= lerpf(1.0, 0.3, sickness / 100.0)
	current_speed = base_speed * speed_mult

	# --- Eye colour ---
	if eye_mat:
		var target_eye := _emotion_eye_color(dominant, hunger, thirst, sickness)
		eye_mat.emission = eye_mat.emission.lerp(target_eye, delta * 2.0)
		# Sick = dim eyes
		var energy_mult := lerpf(0.6, 2.5, energy / 100.0)
		if sickness > 40.0:
			energy_mult *= lerpf(1.0, 0.3, sickness / 100.0)
		eye_mat.emission_energy_multiplier = energy_mult + sinf(state_timer * 1.8) * 0.3

	# --- Stomach glow (hunger + nausea) ---
	_stomach_phase += delta * 3.5
	var nausea := body_state.get("nausea", 0.0)
	if stomach_glow:
		if hunger < 22.0 or nausea > 50.0:
			var pulse := (sinf(_stomach_phase) + 1.0) * 0.5
			stomach_glow.light_energy = lerpf(
				stomach_glow.light_energy, 0.7 + pulse * 1.2, delta * 4.0)
			stomach_glow.light_color = (
				Color(1.0, 0.4, 0.05) if hunger < 22.0   # orange-red hunger
				else Color(0.5, 1.0, 0.4)                 # green nausea
			)
			if stomp_audio and not stomp_audio.playing:
				stomp_audio.play()
		elif hunger < 42.0:
			stomach_glow.light_energy = lerpf(
				stomach_glow.light_energy, 0.18, delta * 2.0)
			stomach_glow.light_color = Color(1.0, 0.55, 0.1)
			if stomp_audio and stomp_audio.playing:
				stomp_audio.stop()
		else:
			stomach_glow.light_energy = lerpf(
				stomach_glow.light_energy, 0.0, delta * 3.0)
			if stomp_audio and stomp_audio.playing:
				stomp_audio.stop()

	# --- Body tint (mood + sickness) ---
	if body_mat:
		var mood_norm := (mood + 100.0) / 200.0
		var base_col  := Color(
			lerpf(0.50, 0.90, mood_norm),
			lerpf(0.50, 0.90, mood_norm),
			lerpf(0.62, 0.95, mood_norm)
		)
		if sickness > 20.0:
			var sick_tint := Color(0.78, 0.88, 0.75)  # pale greenish when sick
			base_col = base_col.lerp(sick_tint, sickness / 100.0)
		body_mat.albedo_color = body_mat.albedo_color.lerp(base_col, delta * 1.5)

	# --- Anxiety head shake ---
	if head_mesh and anxiety > 52.0:
		var shake := sinf(state_timer * 14.0) * ((anxiety - 52.0) / 48.0) * 3.5
		head_mesh.rotation_degrees.z = shake

	# --- Blood sugar crash: dizzy head sway ---
	if head_mesh and crash > 20.0:
		var dizzy := sinf(state_timer * 2.5) * (crash / 100.0) * 4.0
		head_mesh.rotation_degrees.x = dizzy


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
	else:
		velocity = dir.normalized() * current_speed
		var face := Vector3(velocity.x, 0.0, velocity.z)
		if face.length() > 0.01:
			var target_rot := atan2(-face.x, -face.z)
			rotation.y = lerpf(rotation.y, target_rot, delta * 6.0)

	velocity.y = -9.8 * delta
	move_and_slide()
	position.y = FLOOR_Y


func _tick_footsteps(delta: float) -> void:
	footstep_timer += delta
	var step_interval := 0.45 / maxf(current_speed / base_speed, 0.1)
	if velocity.length() > 0.3 and footstep_timer > step_interval:
		footstep_timer = 0.0
		if footstep_audio and not footstep_audio.playing:
			footstep_audio.pitch_scale = randf_range(0.88, 1.12)
			footstep_audio.play()


# ===========================================================
#  UTILITY
# ===========================================================
func _random_floor_point() -> Vector3:
	var angle  := randf() * TAU
	var radius := randf_range(1.0, WANDER_RADIUS)
	return Vector3(cos(angle) * radius, FLOOR_Y, sin(angle) * radius)


func _look_random() -> void:
	if head_mesh:
		head_mesh.rotation_degrees.y = randf_range(-65.0, 65.0)


func _emotion_eye_color(dominant: String, hunger: float,
						thirst: float, sickness: float) -> Color:
	if sickness > 45.0:
		return Color(0.6, 0.7, 0.55)   # pale grey-green when sick
	if thirst < 20.0:
		return Color(0.7, 0.7, 1.0)    # pale dry blue
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
			var h_norm := hunger / 100.0
			return Color(1.0, 0.8 + h_norm * 0.2, 0.7 + h_norm * 0.3)


func _state_name(s: State) -> String:
	match s:
		State.IDLE:          return "idle"
		State.WANDER:        return "wander"
		State.WALK_TO_FOOD:  return "walk to food"
		State.EAT:           return "eating"
		State.WALK_TO_WATER: return "walk to water"
		State.DRINK_WATER:   return "drinking"
		State.SLEEPING:      return "sleeping"
		State.WAKING:        return "waking"
		State.STOMACH_ACHE:  return "stomach ache"
		State.NAUSEOUS:      return "nauseous"
		State.ANXIOUS:       return "anxious"
		State.EXCITED:       return "excited"
		State.SHIVERING:     return "shivering"
		State.SICK:          return "sick"
		State.FATIGUED:      return "fatigued"
		_:                   return "unknown"
