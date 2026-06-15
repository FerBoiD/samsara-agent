# ============================================================
#  DayNight.gd
#
#  Real-clock-based day/night cycle inside the sphere.
#
#  Timeline:
#    06:00 → sunrise  (warm orange light from east)
#    10:00 → morning  (bright warm)
#    13:00 → noon     (cool white, peak brightness)
#    17:00 → late afternoon (golden hour begins)
#    19:30 → sunset   (deep orange-red)
#    20:30 → dusk     (purple-blue, light fading)
#    22:00 → night    (dim blue, moon light)
#    04:00 → pre-dawn (slight blue brightening)
#    06:00 → repeat
#
#  Attach to a Node3D child of Main.
#  Exported vars point to scene nodes.
# ============================================================

extends Node

@export var sun_light:     DirectionalLight3D
@export var moon_light:    DirectionalLight3D
@export var world_env:     WorldEnvironment
@export var ambient_day:   AudioStreamPlayer
@export var ambient_night: AudioStreamPlayer

# Colour keyframes: [hour, Color]
const SUN_COLORS := [
	[6.0,  Color(1.0, 0.55, 0.2,  1.0)],   # sunrise orange
	[10.0, Color(1.0, 0.88, 0.72, 1.0)],   # warm morning
	[13.0, Color(1.0, 0.97, 0.92, 1.0)],   # cool noon
	[17.0, Color(1.0, 0.88, 0.62, 1.0)],   # golden afternoon
	[19.5, Color(1.0, 0.45, 0.15, 1.0)],   # deep sunset
	[20.5, Color(0.55, 0.3,  0.6,  1.0)],  # dusk purple
	[22.0, Color(0.2,  0.3,  0.7,  1.0)],  # night blue
]

const SUN_ENERGY := [
	[6.0,  0.3],
	[9.0,  1.0],
	[13.0, 1.4],
	[17.0, 1.1],
	[19.5, 0.7],
	[20.5, 0.2],
	[22.0, 0.0],
]

var _last_is_day := true
var _day_fraction := 0.0   # 0.0 = midnight, 1.0 = noon


func _ready() -> void:
	if moon_light:
		moon_light.light_color = Color(0.5, 0.55, 0.9, 1.0)
		moon_light.light_energy = 0.0
	_update(0.0)


func _process(delta: float) -> void:
	_update(delta)


func get_day_fraction() -> float:
	return _day_fraction


func is_daytime() -> bool:
	return _last_is_day


# ----------------------------------------------------------
#  INTERNAL
# ----------------------------------------------------------
func _update(_delta: float) -> void:
	var t    := Time.get_time_dict_from_system()
	var hour := float(t["hour"]) + float(t["minute"]) / 60.0 + float(t["second"]) / 3600.0

	# _day_fraction: 0 at midnight, peaks 1.0 at 13:00
	# Use a smooth bell curve centred on 13:00
	var dist_from_noon := absf(hour - 13.0)
	_day_fraction = clampf(1.0 - dist_from_noon / 13.0, 0.0, 1.0)

	var is_day := hour >= 6.0 and hour < 20.5

	# Sun light
	if sun_light:
		sun_light.visible = is_day
		if is_day:
			sun_light.light_color  = _sample_color(SUN_COLORS, hour)
			sun_light.light_energy = _sample_float(SUN_ENERGY, hour)
			# Rotate sun: rises east (rotation_degrees.z = -90 at 6am),
			# arcs to overhead at noon, sets west (+90 at ~20:30)
			var sun_angle := (hour - 6.0) / 14.5 * 180.0 - 90.0
			sun_light.rotation_degrees = Vector3(-60.0, 0.0, sun_angle)

	# Moon light
	if moon_light:
		moon_light.visible = not is_day
		if not is_day:
			# Night: simple overhead, low energy
			var night_progress := 0.0
			if hour >= 20.5:
				night_progress = (hour - 20.5) / 9.5  # 20:30 → 6:00
			else:
				night_progress = (hour + 3.5) / 9.5
			moon_light.light_energy = 0.18 + sinf(night_progress * PI) * 0.12
			moon_light.rotation_degrees = Vector3(-45.0, night_progress * 180.0, 0.0)

	# Ambient audio crossfade
	if is_day != _last_is_day:
		_last_is_day = is_day
		if ambient_day and ambient_night:
			if is_day:
				ambient_night.stop()
				ambient_day.play()
			else:
				ambient_day.stop()
				ambient_night.play()

	# WorldEnvironment sky tint
	if world_env and world_env.environment:
		var env := world_env.environment
		if is_day:
			var sky_col := _sample_color(SUN_COLORS, hour)
			env.ambient_light_color  = sky_col
			env.ambient_light_energy = _day_fraction * 0.4
			env.fog_enabled          = hour < 8.0 or hour > 18.5  # morning/evening haze
			env.fog_density          = 0.01 if env.fog_enabled else 0.0
			env.fog_light_color      = sky_col
		else:
			env.ambient_light_color  = Color(0.1, 0.12, 0.25)
			env.ambient_light_energy = 0.08
			env.fog_enabled          = false


func _sample_color(keyframes: Array, hour: float) -> Color:
	if keyframes.is_empty():
		return Color.WHITE
	if hour <= keyframes[0][0]:
		return keyframes[0][1]
	if hour >= keyframes[-1][0]:
		return keyframes[-1][1]
	for i in range(keyframes.size() - 1):
		var h0: float = keyframes[i][0]
		var h1: float = keyframes[i + 1][0]
		if hour >= h0 and hour < h1:
			var t := (hour - h0) / (h1 - h0)
			return keyframes[i][1].lerp(keyframes[i + 1][1], t)
	return Color.WHITE


func _sample_float(keyframes: Array, hour: float) -> float:
	if keyframes.is_empty():
		return 1.0
	if hour <= keyframes[0][0]:
		return keyframes[0][1]
	if hour >= keyframes[-1][0]:
		return keyframes[-1][1]
	for i in range(keyframes.size() - 1):
		var h0: float = keyframes[i][0]
		var h1: float = keyframes[i + 1][0]
		if hour >= h0 and hour < h1:
			var t := (hour - h0) / (h1 - h0)
			return lerpf(keyframes[i][1], keyframes[i + 1][1], t)
	return 1.0
