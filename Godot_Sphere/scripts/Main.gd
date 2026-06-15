# ============================================================
#  Main.gd
#
#  Root scene controller. Wires all subsystems together.
#
#  Node tree expected:
#    Node3D  (Main)  ← this script
#      DrivesBridge  (Node)
#      DayNight      (Node)
#      WorldEnvironment
#      DirectionalLight3D (Sun)
#      DirectionalLight3D (Moon)
#      MeshInstance3D (Sphere)  ← inverted sphere, white mat
#      CharacterBody3D (Kora)   ← KoraBody.gd
#        MeshInstance3D (Body)
#        MeshInstance3D (Head)
#        MeshInstance3D (EyeLeft)
#        MeshInstance3D (EyeRight)
#        OmniLight3D (StomachGlow)
#        GPUParticles3D (ZzzParticles)
#        AudioStreamPlayer3D (FootstepAudio)
#        AudioStreamPlayer3D (StomachAudio)
#        AudioStreamPlayer3D (BreathAudio)
#      Node3D (FoodBowl)   ← FoodBowl.gd
#        MeshInstance3D
#        StaticBody3D
#          CollisionShape3D
#          Area3D (click detection)
#        OmniLight3D (BowlGlow)
#        AudioStreamPlayer3D (BowlAudio)
#      MeshInstance3D (SleepSpot)  ← flat plane, soft mat
#      Node (SphereEnv)   ← SphereEnv.gd
#      CanvasLayer (HUD)
#        Control  ← HUD.gd
#      AudioStreamPlayer (AmbientDay)
#      AudioStreamPlayer (AmbientNight)
# ============================================================

extends Node3D

@export var bridge:     Node      # DrivesBridge
@export var day_night:  Node      # DayNight
@export var kora:       CharacterBody3D  # KoraBody
@export var food_bowl:  Node3D    # FoodBowl
@export var sphere_env: Node      # SphereEnv
@export var hud:        Control   # HUD


func _ready() -> void:
	# Wire DrivesBridge signals → subsystems
	if bridge:
		bridge.drives_updated.connect(_on_drives_updated)
		bridge.connected_to_kora.connect(_on_connected)
		bridge.disconnected_from_kora.connect(_on_disconnected)

	# Wire KoraBody signals
	if kora:
		kora.feed_requested.connect(_on_kora_wants_food)
		kora.state_changed.connect(_on_kora_state_changed)

	# Wire FoodBowl click → bridge feed command
	if food_bowl:
		food_bowl.bowl_clicked.connect(_on_bowl_clicked)

	print("[MAIN] Samsara Sphere ready")


func _on_drives_updated(state: Dictionary) -> void:
	if kora:      kora.on_drives_updated(state)
	if food_bowl: food_bowl.on_drives_updated(state)
	if sphere_env:sphere_env.on_drives_updated(state)
	if hud:       hud.on_drives_updated(state)


func _on_connected() -> void:
	print("[MAIN] Connected to Kora")
	if hud: hud.on_connected()


func _on_disconnected() -> void:
	print("[MAIN] Disconnected from Kora")
	if hud: hud.on_disconnected()


func _on_kora_wants_food() -> void:
	# Kora walked to food bowl and did eat animation — trigger Python feed
	if bridge: bridge.send_feed()


func _on_bowl_clicked() -> void:
	# Caretaker clicked the food bowl in the world
	if bridge: bridge.send_feed()


func _on_kora_state_changed(state_name: String) -> void:
	if hud: hud.on_state_changed(state_name)
