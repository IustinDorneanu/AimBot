# VisionAim

Prototype for **Windows 10, 64-bit** and offline single-player games. It captures the center of a foreground game window and displays a separate debug preview. Capture, demo, and YOLO modes do not move the mouse. Experimental Control HUD assistance is explicitly enabled with `--health-bars --assist`; it is not the completed aim-assist MVP.

## Run on Windows 10

Install 64-bit Python 3.12. Open PowerShell in this project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m visionaim --demo
```

No virtual-environment activation or PowerShell execution-policy changes are needed. The demo uses synthetic rectangles and targets, so it needs no game, GPU, or model. Confirm that a nearby rectangle is highlighted and connected to the crosshair.

To test actual capture:

```powershell
.\.venv\Scripts\python.exe -m visionaim --list-windows
.\.venv\Scripts\python.exe -m visionaim --capture-only
```

Run Control in borderless or windowed mode, then focus the game. A window must match both the title substring and one of the profile's `process_names` (`Control_DX11.exe` or `Control_DX12.exe` by default), so windows like Control Panel are ignored. `--list-windows` shows each window's executable; override with `--window-title "Control"` and `--process Control_DX12.exe` if necessary. Capture pauses when the game is minimized or loses foreground focus. The crop is 50% of the client width and height; window borders and title bars are excluded. Other applications covering the capture region will appear in the capture. Keep the preview outside the game area, preferably on a second monitor. If capture is black, use borderless mode before experimenting with the optional DXCam backend.

## Controls

While the game is focused, these global keys work:

| Key | Action |
| --- | --- |
| F8 | Pause/resume capture and detection |
| F9 | Save the next raw, unannotated captured frame |
| Ctrl+Shift+F12 | Exit and close the preview |

In the preview, Q/Esc quits, P pauses, and S saves a screenshot. Ctrl+C also stops the console process. Global shortcuts are polled, not registered or consumed, so a game may react to them too. Emergency shutdown is checked between frames; a blocking inference call must return first. Mouse assistance is opt-in as described below.

Screenshots go to `datasets/control/images/raw/` with JSON crop metadata. Save a representative mix of Hiss enemies, lighting, partial occlusion, and empty scenes. The images are capture pixels, not debug drawings.

## Experimental Control marker lock

The supplied 960 × 540 captures show an orange-red health bar with a level numeral above it. The heuristic checks both shapes without reading the numeral's value. It handles partial health and overlapping bars, but its color and size thresholds are specific to these captures. HUD scaling changes can require tuning. Markers may only appear when aiming at an enemy; this does not detect all visible enemies.

Using the Windows environment created during setup:

```powershell
.\.venv-win\Scripts\python.exe tools\test_health_bars.py
.\.venv-win\Scripts\python.exe -m visionaim --health-bars
.\.venv-win\Scripts\python.exe -m visionaim --health-bars --assist
```

The offline check writes annotated copies, a contact sheet, and JSON timings to `datasets/control/health-bar-test/`. Raw screenshots remain available for training.

With `--assist`, aim at the enemy first, then **hold right mouse button**. One marker near the crosshair acquires a lock. The lock centers horizontally on the marker and aims 40 capture pixels below the bar at 960px capture width, scaled with capture width. This estimates an upper-body point from the supplied screenshots; it does not detect body boundaries or heads, so distance and animation can affect accuracy. Relative mouse corrections use a gain of 0.25, a two-pixel dead zone, and a maximum of ten motion units per processed frame. Game sensitivity affects the result and may need tuning in `visionaim/targeting/marker_lock.py`. The input uses [Win32 relative mouse movement](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput).

Release right mouse button to stop. Marker shifts up to 100 capture pixels (scaled with capture width) can remain associated during manual mouse movement. Missing or ambiguous markers pause movement. A single nearby marker returning within 350 ms resumes the lock; after longer loss, acquisition rearms automatically while right-click remains held and waits for one marker near the crosshair. This can acquire another enemy after the original is lost. Pause, window/crop changes, and loss of foreground focus cancel it and require releasing the button to rearm. Focus, button state, and emergency shutdown are checked again immediately before sending movement. No firing or mouse button events are sent. No mouse movement is sent while the marker is missing. Live game behavior and sensitivity still need user testing; screenshot detection is not a game accuracy benchmark.

## Use a detector

**Trained Control enemy weights are not included.** A generic person detector cannot distinguish Hiss enemies, the player, and friendly characters. Collect and label the PRD dataset, train a YOLO detection model with an `enemy` class, and place its weights at `models/control.pt`.

Install detection support and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[detection]"
.\.venv\Scripts\python.exe -m visionaim --model models\control.pt
```

The application requires an existing local model file and rejects models without a configured enemy class. It does not download default pretrained weights. Detection boxes are mapped from the resized input back to capture coordinates before target selection.

CPU inference is the portable default. For an NVIDIA GPU, install the CUDA-enabled PyTorch build appropriate to your driver using the [official PyTorch installer](https://pytorch.org/get-started/locally/), then use `--device 0`. Enable `half` in the profile only with a supported CUDA device. No CUDA performance claims have been validated yet.

## Configuration

Edit `profiles/control.json`; settings are validated at launch:

- `window_title`: case-insensitive visible window title substring.
- `process_names`: accepted game executable names (case-insensitive). An empty list matches by title only.
- `capture_backend`: `mss` by default; works with multiple monitors and negative desktop coordinates.
- `capture_fps`: requested capture/pipeline rate; inference may reduce the actual rate.
- `capture_fraction`: centered fraction of the game client area.
- `detection_resolution`: width and height before YOLO inference (default 640 × 360).
- `confidence`, `enemy_classes`: accepted enemy detections.
- `aim_radius`: radius in original capture pixels, centered on the crosshair.
- `target_point`: `upper_chest` (35% box height), `center_mass` (50%), or `head` (15%, an estimate rather than a head detector).
- `target_persistence_ms`: how long spatially matched boxes are preferred; disappeared targets are dropped immediately.
- `switch_ratio`: a substantially closer candidate can break persistence (default 0.65).
- `model_path`: resolved relative to the project root for `profiles/control.json`; for another profile, relative to its parent directory's parent. `--model` resolves relative to the working directory.
- `device`, `half`: inference device and optional half precision.

Create another game profile with `--profile profiles/generic.json --write-default-profile`. Load it with `--profile profiles/generic.json`.

Optional DXCam Desktop Duplication capture:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dxcam]"
```

Set `capture_backend` to `dxcam`. This initial adapter requires a single-monitor setup using DXGI device 0/output 0 at desktop origin (0,0). Use MSS for multiple monitors. DXCam may return no frame when the desktop has not changed; the program keeps polling rather than blocking while waiting for a frame.

## Validation and status

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m visionaim --demo --headless --frames 60
```

The headless command prints JSON metrics. Preview metrics include capture, inference, and total processing latency; processing latency excludes rendering and rate-limit waiting. FPS is the average processed frame rate since launch, including any foreground/pause waiting. A synthetic demo does not measure game detection accuracy or GPU inference performance.

Implemented: profiles, Win32 discovery/DPI handling, crop capture, local detection adapter, coordinate mapping, target selection and persistence, debug preview, screenshot collection, demo, emergency exit.

Still needed: labeled Control dataset and trained weights, live validation of experimental marker assistance, capture/detection benchmarks, a settings panel, a transparent overlay, calibrated assistance and smoothing, asynchronous pipeline optimization, and advanced targeting. Adaptive targeting and slow-motion integration are deferred. The ≥25 FPS, ≤40 ms and ≤5% game FPS loss targets have not been verified.

Capture and detector integrations follow the [MSS examples](https://python-mss.readthedocs.io/v10.2.0/examples.html), [DXCam API](https://ra1nty.github.io/DXcam/dxcam.html), and [Ultralytics prediction API](https://docs.ultralytics.com/modes/predict/). Review dependency licenses before distributing the application, especially Ultralytics.
