# Samsara Sphere — Godot Setup Guide

## Requirements
- Godot 4.3 or newer (download at godotengine.org)
- Python side running first (python main.py in Samsara_Mac_Version1/)

---

## Step 1 — Open Project

1. Open Godot
2. Click **Import**
3. Navigate to `Godot_Sphere/` and select `project.godot`
4. Click **Import & Edit**

---

## Step 2 — Create the Main Scene

Go to **Scene > New Scene**. Build the following node tree exactly as written.
Name each node exactly as shown.

```
Node3D                     [name: Main]        attach: scripts/Main.gd
  Node                     [name: DrivesBridge] attach: scripts/DrivesBridge.gd
  Node                     [name: DayNight]     attach: scripts/DayNight.gd
  Node                     [name: SphereEnv]    attach: scripts/SphereEnv.gd
  WorldEnvironment         [name: WorldEnvironment]
  DirectionalLight3D       [name: Sun]
  DirectionalLight3D       [name: Moon]
  MeshInstance3D           [name: Sphere]       ← the white sphere shell
  CharacterBody3D          [name: Kora]         attach: scripts/KoraBody.gd
    MeshInstance3D         [name: Body]
    MeshInstance3D         [name: Head]
    MeshInstance3D         [name: EyeLeft]
    MeshInstance3D         [name: EyeRight]
    OmniLight3D            [name: StomachGlow]
    GPUParticles3D         [name: ZzzParticles]
    AudioStreamPlayer3D    [name: FootstepAudio]
    AudioStreamPlayer3D    [name: StomachAudio]
    AudioStreamPlayer3D    [name: BreathAudio]
    CollisionShape3D       (for CharacterBody3D)
  Node3D                   [name: FoodBowl]     attach: scripts/FoodBowl.gd
    MeshInstance3D         [name: BowlMesh]
    StaticBody3D
      CollisionShape3D
    Area3D                 [name: ClickArea]
      CollisionShape3D
    OmniLight3D            [name: BowlGlow]
    AudioStreamPlayer3D    [name: BowlAudio]
  MeshInstance3D           [name: SleepSpot]
  CanvasLayer              [name: HUDLayer]
    Control                [name: HUD]          attach: scripts/HUD.gd
  AudioStreamPlayer        [name: AmbientDay]
  AudioStreamPlayer        [name: AmbientNight]
```

Save scene as: `scenes/Main.tscn`

---

## Step 3 — Set Up Meshes

### Sphere (white interior)

1. Select the **Sphere** MeshInstance3D
2. In Inspector → Mesh → **New SphereMesh**
   - Radius: **10**
   - Height: **20**
3. Mesh → **flip_faces = true** (so normals point inward)
   - Or: Material → Cull Mode → **Front Face**
4. Create material: **New StandardMaterial3D**
   - Albedo color: `#F8F7F5` (off-white, very slightly warm)
   - Metallic: 0.0
   - Roughness: 0.95
   - Emission: disabled
5. Position: `0, 0, 0`

### Kora — Body

Select **Body** (child of Kora):
- Mesh → **New CapsuleMesh** (radius 0.35, height 1.2)
- Material → New StandardMaterial3D
  - Albedo: `#E0DCF0` (light blue-grey — will be tinted by mood)
  - Roughness: 0.8
- Position: `0, 0.6, 0`

### Kora — Head

Select **Head**:
- Mesh → **New SphereMesh** (radius 0.32)
- Same material style as body
- Position: `0, 1.55, 0`

### Kora — Eyes

Select **EyeLeft**:
- Mesh → **New SphereMesh** (radius 0.06)
- Material → StandardMaterial3D
  - Emission enabled: YES
  - Emission color: WHITE
  - Emission energy: 2.0
- Position: `-0.13, 1.63, -0.27`

Select **EyeRight**:
- Same mesh + material as EyeLeft
- Position: `+0.13, 1.63, -0.27`

### Kora — CollisionShape3D (for CharacterBody3D)

- Shape → New CapsuleShape3D (radius 0.35, height 1.2)
- Position: `0, 0.6, 0`

### StomachGlow

- Light Color: `#FF4A0D`
- Light Energy: **0** (KoraBody.gd controls this)
- Range: 1.2
- Position: `0, 0.5, 0`

### ZzzParticles

- Amount: 8
- Lifetime: 2.0
- Direction: `0, 1, 0`
- Gravity: `0, 0.2, 0`
- Initial Velocity: 0.3
- Leave emitting = false (KoraBody.gd controls)

### FoodBowl — BowlMesh

- Mesh → **New CylinderMesh** (top radius 0.5, bottom radius 0.4, height 0.2)
- Material: StandardMaterial3D, Albedo `#C0A060` (food bowl tan)
- Position FoodBowl node: `5.5, -8.5, 0`

### FoodBowl — ClickArea CollisionShape3D

- Shape → New CylinderShape3D (radius 0.6, height 0.4)
- Connect Area3D signal: **input_event → FoodBowl._on_area_input_event**

### BowlGlow (child of FoodBowl)

- Color: `#FFB030`
- Energy: 0 (FoodBowl.gd controls)
- Range: 1.5

### SleepSpot

- Mesh → **New PlaneMesh** (size 1.8 x 1.2)
- Material → StandardMaterial3D
  - Albedo: `#8090B8` (soft blue-grey)
  - Roughness: 0.99
- Position: `-5.0, -9.48, -2.5` (slightly above sphere floor)

---

## Step 4 — Set Up Lighting

### WorldEnvironment

1. Add a new Environment resource in Inspector
2. Background Mode: **Sky**
3. Sky material: **New ProceduralSkyMaterial**
   - Sky horizon color: `#C8E0F4`
   - Ground horizon color: `#D4CFC8`
4. Ambient Light → Source: **Background**, Energy: **0.3**
5. Fog: **disabled** (DayNight.gd controls)

### Sun (DirectionalLight3D)

- Shadow enabled: YES
- Shadow blur: 2
- Energy: 1.0 (DayNight.gd controls)

### Moon (DirectionalLight3D)

- Color: `#8899CC`
- Energy: 0.0 (DayNight.gd controls)
- Shadow: disabled

---

## Step 5 — Camera

Add a **Camera3D** to the scene (child of Main):
- Position: `0, -2, 14` (outside the sphere, looking in)
  - OR for inside view: `0, -7, 0` looking forward
- For inside: Position `0, -6.5, 6`, rotation x = -15 deg
- FOV: 75

Add a **MeshInstance3D** for the camera hole: small circular plane to look
through, OR just float the camera inside the sphere.

**Recommended — Inside Orbit Camera:**

Add a script to Camera3D:
```gdscript
extends Camera3D
var orbit_angle := 0.0
func _process(delta):
    if Input.is_action_pressed("ui_left"):  orbit_angle -= delta * 0.8
    if Input.is_action_pressed("ui_right"): orbit_angle += delta * 0.8
    position.x = sin(orbit_angle) * 8.0
    position.z = cos(orbit_angle) * 8.0
    position.y = -6.0
    look_at(Vector3(0, -7.5, 0))
```

---

## Step 6 — Wire Exported Variables in Main.gd

Select the **Main** node. In Inspector you'll see exported vars:

| Variable  | Assign to       |
|-----------|-----------------|
| bridge    | DrivesBridge    |
| day_night | DayNight        |
| kora      | Kora            |
| food_bowl | FoodBowl        |
| sphere_env| SphereEnv       |
| hud       | HUD (Control)   |

Do the same for:

**DayNight node** → assign sun_light, moon_light, world_env,
ambient_day, ambient_night

**KoraBody (Kora node)** → assign body_mesh, head_mesh, eye_left,
eye_right, stomach_glow, zzz_particles, footstep_audio, stomp_audio,
breath_audio

**SphereEnv node** → assign sphere_mesh (the white Sphere)

**FoodBowl node** → assign glow_light (BowlGlow), food_audio (BowlAudio)

**HUD node** → assign day_night_ref, kora_body_ref

---

## Step 7 — Audio (Optional but adds a lot)

For ambient sounds, use free CC0 audio:
- freesound.org → search "birds chirping morning" → AmbientDay
- freesound.org → search "crickets night" → AmbientNight
- freesound.org → search "stomach growl" → StomachAudio
- freesound.org → search "footsteps soft" → FootstepAudio
- freesound.org → search "slow breathing sleep" → BreathAudio

Set AudioStreamPlayer nodes: **Autoplay = false**, Loop = true (for ambients).

---

## Step 8 — Start Everything

1. In a terminal: `cd Samsara_Mac_Version1 && python main.py`
   - This starts the Python bridge on port 9999
2. Press **Play** in Godot
3. The sphere opens, Kora appears, eyes glow
4. HUD: press **Tab** to toggle the observer panel
5. Watch Kora react in real time to its actual live drive state

---

## What You'll See

| Kora condition       | What happens in the sphere                          |
|----------------------|-----------------------------------------------------|
| Hunger < 55%         | Kora walks to food bowl area                        |
| Hunger < 20%         | Stomach glows orange-red, Kora hunches, audio plays |
| Energy low           | Kora moves slowly, droops slightly                  |
| Sleeping             | Kora walks to sleep spot, ZZZ particles, breathing  |
| Waking               | Kora stretches, ZZZ particles stop                  |
| Anxiety > 65%        | Kora twitches, rapid small movements, head shakes   |
| Excitement > 72%     | Kora bounces, eyes glow cyan                        |
| Boredom > 45%        | Kora wanders slowly around the sphere               |
| Dying                | Sphere walls pulse dark red, eyes glow red          |
| Night (real clock)   | Sphere dims to navy, moon light only                |
| Dawn (6am)           | Warm orange light sweeps in from east               |
| Noon (1pm)           | Bright cool white, peak brightness                  |
| Sunset (7:30pm)      | Deep orange-red, fog on walls                       |
| Mood low (sad)       | Sphere tint shifts to cool blue                     |
| Mood high (happy)    | Sphere tint shifts to warm cream                    |
| Click food bowl      | Sends /feed command to Kora via Python bridge       |

---

## Next Steps (later branches)

- Add real camera feed via VideoStreamPlayer (the green-screen layer)
- Add second Kora instance (friend character, Gen 2+)
- Add weather system (rain particles inside sphere matching real weather API)
- Add physical temperature (sphere brightness/color based on actual temp)
- Add Kora's daily route (establishes a "home" corner over multiple days)
