# PRD — Computer Vision Aim Assist for Single-Player Games

## Product Name

**VisionAim**

## 1. Overview

VisionAim is a local desktop application that provides configurable aim assistance for single-player PC games using computer vision.

The application captures a portion of the game screen, detects visible enemies, selects an appropriate target near the player's crosshair, and applies smooth mouse movement toward the selected target.

The initial target game for development and testing is **Control**.

The project is intended for:

- experimentation
- computer-vision learning
- accessibility experimentation
- offline/single-player gameplay
- AI/ML development practice

The application must not depend on reading or modifying game memory.

## 2. Goals

The primary goal is to create a responsive aim-assist system that feels similar to controller aim assist rather than a traditional instant-snap aimbot.

The system should:

- detect enemies visible on screen
- determine their approximate position
- identify targets near the player's crosshair
- smoothly move the crosshair toward the selected target
- allow configurable aim strength
- operate with minimal effect on game performance
- work without injecting code into the game
- run entirely locally

Target experience:

> Hold the aim-assist button and the crosshair gently gravitates toward a nearby visible enemy.

## 3. Non-Goals

The initial version will not:

- read game memory
- modify game memory
- inject DLLs
- hook game rendering APIs
- provide wallhacks
- detect enemies through walls
- perform automatic firing
- bypass anti-cheat systems
- target multiplayer or competitive games
- attempt to conceal itself from anti-cheat software

The intended environment is offline or single-player gameplay.

## 4. Target Platform

Initial platform:

**Windows 10 (64-bit)**

Windows 11 may also be supported, but initial development and validation must target Windows 10.

Primary GPU target:

- NVIDIA RTX-class GPUs

Recommended development environment:

- Python 3.12+
- CUDA
- PyTorch
- OpenCV
- YOLO-compatible object detection
- Windows desktop capture API

A future implementation may move performance-critical components to C++.

## 5. High-Level Architecture

```text
Game
 ↓
Screen Capture
 ↓
Image Preprocessing
 ↓
Enemy Detection AI
 ↓
Target Selection
 ↓
Aim Controller
 ↓
Mouse Input Output
```

## 6. Core Components

### 6.1 Screen Capture

The system continuously captures a configurable portion of the game window.

Capturing the entire display should be avoided where possible.

Default detection region:

```text
40–60% of screen width
40–60% of screen height
centered around crosshair
```

Example:

Game resolution:

```text
2560 × 1440
```

Detection region:

```text
1280 × 720
```

Detector input:

```text
640 × 360
```

The reduced detection resolution lowers GPU usage and inference latency.

Target capture rate:

**30 FPS**

Optional settings:

```text
15 FPS
20 FPS
30 FPS
45 FPS
60 FPS
```

## 7. Enemy Detection

The application should use an object-detection model.

Initial recommendation:

**YOLO small/nano model**

Potential models:

- YOLO11n
- YOLO11s
- equivalent lightweight detector

The detector should return:

```text
class
confidence
x
y
width
height
```

Example:

```json
{
  "class": "enemy",
  "confidence": 0.91,
  "x": 830,
  "y": 340,
  "width": 120,
  "height": 280
}
```

## 8. Training Dataset

Because *Control* has unique enemy designs, a custom dataset will likely be required.

Screenshots should be collected during normal gameplay.

Initial dataset target:

```text
500–1,000 images
```

Better dataset:

```text
2,000–5,000 images
```

Images should contain:

- close enemies
- distant enemies
- flying enemies
- partially obstructed enemies
- enemies under red Hiss lighting
- enemies during explosions
- enemies behind environmental effects
- multiple enemies simultaneously
- empty scenes

Bounding boxes should be manually labeled.

Initial classes:

```text
enemy
```

Future classes:

```text
enemy_head
enemy_body
flying_enemy
heavy_enemy
boss
```

## 9. Target Point Calculation

Once an enemy bounding box is identified, the system needs to determine where to aim.

Default target:

**upper torso**

For bounding box:

```text
x
y
width
height
```

Target X:

```text
targetX = x + width / 2
```

Target Y:

```text
targetY = y + height * 0.35
```

User-selectable target modes:

```text
Center Mass
Upper Chest
Head
Adaptive
```

## 10. Crosshair Position

Default crosshair position:

```text
screenWidth / 2
screenHeight / 2
```

The system calculates:

```text
deltaX = targetX - crosshairX
deltaY = targetY - crosshairY
```

## 11. Target Selection

Multiple enemies may be visible simultaneously.

Each detected enemy receives a target score.

Initial scoring algorithm:

```text
distanceToCrosshair
```

Future scoring could include:

```text
distance
confidence
enemy size
target type
previous target
screen position
```

## 12. Aim FOV

Aim assist should only activate when an enemy is sufficiently close to the player's crosshair.

Configurable FOV:

```text
50 px
100 px
150 px
200 px
300 px
```

Recommended default:

```text
150 px
```

## 13. Aim Smoothing

The system should never instantly teleport the crosshair.

Instead:

```text
movementX = deltaX * aimStrength
movementY = deltaY * aimStrength
```

Recommended range:

```text
0.02 – 0.40
```

Default:

```text
0.10
```

## 14. Advanced Smoothing

Linear smoothing can look robotic.

A better system should support gradual acceleration and deceleration.

Potential interpolation:

```text
lerp
smoothstep
ease-in-out
Bezier curve
```

## 15. Target Locking

Target switching can create jitter.

Once a target is selected, the system should temporarily prefer that target.

Example:

```text
Target persistence = 250 ms
```

The application should change targets only when:

- current target disappears
- current target leaves aim FOV
- another target is substantially closer
- target confidence becomes too low

## 16. Activation

Default aim-assist activation:

```text
Hold Right Mouse Button
```

Alternative:

```text
Mouse Button 4
Mouse Button 5
Left Alt
Left Shift
custom keyboard key
```

Modes:

- Hold
- Toggle

## 17. Slow-Motion Integration

An optional future module could integrate slow motion.

Example behaviour:

```text
Hold Mouse 4
 ↓
Slow motion ON
 ↓
Aim assistance ON
 ↓
Release
 ↓
Normal speed
```

Potential configuration:

```text
Normal speed:       1.0
Slow motion:        0.4
Aim strength:       0.12
Slow-mo strength:   0.22
```

Slow-motion support must remain independent of the computer-vision detector.

Game-specific implementations may be required.

## 18. Performance Requirements

The system must minimize performance impact.

Primary target:

```text
Game FPS loss < 5%
```

Ideal:

```text
< 2%
```

Detection latency target:

```text
< 25 ms
```

Total pipeline target:

```text
capture + processing + inference + target selection < 35 ms
```

Example:

```text
Game:       144 FPS
Capture:     30 FPS
Detection:   30 FPS
Aim update: 144 Hz interpolation
```

## 19. GPU Management

Recommended techniques:

- small AI models
- FP16 inference
- reduced input resolution
- cropped capture region
- asynchronous inference
- configurable inference FPS
- GPU utilization limit where practical

Potential architecture:

```text
Thread 1: Screen capture
Thread 2: AI inference
Thread 3: Target selection
Thread 4: Mouse interpolation
```

## 20. Detection Interpolation

Because detection may only happen at 20–30 FPS, aim movement should interpolate between detections.

## 21. User Interface

The application should provide a small control panel with:

- enable/disable status
- activation key
- detection FPS
- aim strength
- aim radius
- aim point
- detection confidence
- target persistence
- debug overlay toggle
- FPS display

## 22. Debug Overlay

Development mode should display:

- enemy bounding boxes
- detection confidence
- selected target
- crosshair center
- aim FOV
- inference FPS
- capture FPS
- latency

## 23. Configuration Profiles

Settings should be saved per game.

Example:

```text
profiles/
  control.json
  wolfenstein.json
  generic.json
```

Example configuration:

```json
{
  "capture_fps": 30,
  "detection_resolution": [640, 360],
  "confidence": 0.6,
  "aim_strength": 0.12,
  "aim_radius": 150,
  "target_point": "upper_chest",
  "target_persistence_ms": 250
}
```

## 24. Safety Controls

The application should include a master emergency hotkey.

Example:

```text
CTRL + SHIFT + F12
```

Behaviour:

Immediately disable:

- aim assist
- automated mouse movement
- overlay

The application should never prevent normal mouse control.

## 25. Development Phases

### Phase 1 — Screen Capture

Goal:

Capture the game window efficiently.

Success criteria:

```text
30+ FPS capture
minimal game FPS loss
```

### Phase 2 — Object Detection

Goal:

Detect enemies in screenshots.

Requirements:

- collect screenshots
- label enemies
- train detector
- display bounding boxes

Success criteria:

```text
>85% useful enemy detection
```

### Phase 3 — Target Selection

Goal:

Choose the enemy closest to the crosshair.

No mouse movement yet.

### Phase 4 — Aim Controller

Goal:

Move the mouse smoothly toward selected targets.

Requirements:

- configurable strength
- activation hotkey
- aim radius
- smooth movement
- target persistence

### Phase 5 — Optimization

Optimize:

- inference resolution
- capture pipeline
- GPU inference
- threading
- memory allocation
- model size

Target:

```text
< 5% game FPS impact
```

### Phase 6 — Advanced Aim Behaviour

Add:

- acceleration
- deceleration
- target prediction
- target locking
- adaptive smoothing
- head/chest targeting
- dynamic aim radius

### Phase 7 — Game Profiles

Allow individual configuration for:

```text
Control
Wolfenstein
other single-player games
```

## 26. Suggested Project Structure

```text
visionaim/

├── app/
│   ├── main.py
│   └── config.py
├── capture/
│   ├── screen_capture.py
│   └── window_detection.py
├── detection/
│   ├── detector.py
│   ├── model_loader.py
│   └── inference.py
├── targeting/
│   ├── target_selector.py
│   ├── target_tracker.py
│   └── prediction.py
├── aim/
│   ├── controller.py
│   ├── smoothing.py
│   └── input.py
├── overlay/
│   ├── overlay.py
│   └── debug_renderer.py
├── ui/
│   └── settings_window.py
├── models/
├── datasets/
├── profiles/
│   └── control.json
└── tests/
```

## 27. Recommended Technology Stack

### Prototype

Language:

```text
Python
```

Libraries:

```text
PyTorch
Ultralytics YOLO
OpenCV
NumPy
DXCam
PySide6
```

Potential screen capture:

```text
DXCam
Windows Graphics Capture
Desktop Duplication API
```

Input handling:

```text
Windows SendInput
```

## 28. Future C++ Version

Potential stack:

```text
C++20
DirectX 11/12 Desktop Duplication
ONNX Runtime
TensorRT
CUDA
Win32 SendInput
```

Potential total processing latency:

```text
5–15 ms
```

on suitable hardware.

## 29. MVP Definition

The MVP is considered complete when the application can:

1. Detect the *Control* game window.
2. Capture the central portion of the screen.
3. Detect visible Hiss enemies.
4. Display enemy bounding boxes.
5. Select the enemy closest to the crosshair.
6. Highlight the selected enemy.
7. Activate aim assistance while a configurable button is held.
8. Smoothly move the crosshair toward the target.
9. Allow adjustment of aim strength.
10. Allow adjustment of aim radius.
11. Maintain acceptable game performance.

MVP target performance:

```text
Detector:      ≥ 25 FPS
Latency:       ≤ 40 ms
Game FPS loss: ≤ 5%
```

## 30. Recommended First Prototype

The first prototype should deliberately avoid mouse control.

Build:

```text
Game
 ↓
Screen capture
 ↓
YOLO detector
 ↓
Enemy bounding boxes
 ↓
Choose closest enemy
 ↓
Draw line:
Crosshair ─────────► Target
```

Once that works reliably, add mouse assistance.

## 31. Long-Term Vision

VisionAim could eventually become a generic experimental computer-vision framework for single-player games.

Possible modules:

```text
Enemy detection
Aim assistance
Object recognition
Loot detection
NPC recognition
Accessibility enhancements
Visual alerts
Slow-motion integration
Gameplay analytics
```

The architecture should therefore keep capture, detection, targeting, input, and UI as independent modules rather than building everything specifically around *Control*.
