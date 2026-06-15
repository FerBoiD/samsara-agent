# ============================================================
#  Main.gd — v2
#
#  Root scene controller. Wires all subsystems.
#
#  Node tree expected:
#    Node3D (Main) ← this script
#      Node          (DrivesBridge)
#      Node          (DayNight)
#      Node          (SphereEnv)
#      WorldEnvironment
#      DirectionalLight3D (Sun)
#      DirectionalLight3D (Moon)
#      MeshInstance3D     (Sphere)
#      CharacterBody3D    (Kora)          KoraBody.gd
#        ...
#      Node3D             (FoodBowl)      FoodBowl.gd
#      Node3D             (WaterBowl)     WaterBowl.gd
#      MeshInstance3D     (SleepSpot)
#      CanvasLayer        (HUDLayer)
#        Control          (HUD)           HUD.gd
#      CanvasLayer        (ChatLayer)     ChatOverlay.gd
#      AudioStreamPlayer  (AmbientDay)
#      AudioStreamPlayer  (AmbientNight)
# ============================================================

extends Node3D

@export var bridge:      Node
@export var day_night:   Node
@export var kora:        CharacterBody3D
@export var food_bowl:   Node3D
@export var water_bowl:  Node3D
@export var sphere_env:  Node
@export var hud:         Control
@export var chat_overlay:CanvasLayer


func _ready() -> void:
	if bridge:
		bridge.drives_updated.connect(_on_drives_updated)
		bridge.connected_to_kora.connect(_on_connected)
		bridge.disconnected_from_kora.connect(_on_disconnected)

	if kora:
		kora.feed_requested.connect(_on_kora_wants_food)
		kora.drink_requested.connect(_on_kora_wants_drink)
		kora.state_changed.connect(_on_kora_state_changed)

	if food_bowl:
		food_bowl.bowl_clicked.connect(_on_bowl_clicked_feed)

	if water_bowl:
		water_bowl.bowl_clicked.connect(_on_bowl_clicked_drink)

	if chat_overlay:
		chat_overlay.message_sent.connect(_on_chat_message)
		chat_overlay.feed_pressed.connect(_on_bowl_clicked_feed)
		chat_overlay.drink_pressed.connect(_on_bowl_clicked_drink)

	print("[MAIN] Samsara Sphere v2 ready — Tab = stats, type below to talk")


# ----------------------------------------------------------
#  DRIVE UPDATES
# ----------------------------------------------------------
func _on_drives_updated(state: Dictionary) -> void:
	if kora:        kora.on_drives_updated(state)
	if food_bowl:   food_bowl.on_drives_updated(state)
	if water_bowl:  water_bowl.on_drives_updated(state)
	if sphere_env:  sphere_env.on_drives_updated(state)
	if hud:         hud.on_drives_updated(state)


# ----------------------------------------------------------
#  CONNECTION
# ----------------------------------------------------------
func _on_connected() -> void:
	print("[MAIN] Connected to Kora")
	if hud:          hud.on_connected()
	if chat_overlay: chat_overlay.on_connected()


func _on_disconnected() -> void:
	print("[MAIN] Disconnected from Kora")
	if hud:          hud.on_disconnected()
	if chat_overlay: chat_overlay.on_disconnected()


# ----------------------------------------------------------
#  KORA ACTIONS
# ----------------------------------------------------------
func _on_kora_wants_food() -> void:
	if bridge: bridge.send_feed()


func _on_kora_wants_drink() -> void:
	if bridge: bridge.send_drink()


func _on_kora_state_changed(state_name: String) -> void:
	if hud: hud.on_state_changed(state_name)


# ----------------------------------------------------------
#  CARETAKER ACTIONS
# ----------------------------------------------------------
func _on_bowl_clicked_feed() -> void:
	if bridge: bridge.send_feed()


func _on_bowl_clicked_drink() -> void:
	if bridge: bridge.send_drink()


func _on_chat_message(text: String) -> void:
	if bridge: bridge.send_message(text)
