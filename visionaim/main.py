"""Capture/detection preview with optional hold-to-assist Control HUD locking."""
import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from .config import Profile, load_profile, save_profile
from .geometry import central_region
from .targeting.target_selector import TargetSelector

PREVIEW = "VisionAim preview | Q: quit  P: pause  S: screenshot"


def parser():
    result = argparse.ArgumentParser(description="VisionAim: Windows capture and optional HUD marker assistance")
    result.add_argument("--profile", type=Path, default=Path("profiles/control.json"))
    result.add_argument("--write-default-profile", action="store_true")
    result.add_argument("--list-windows", action="store_true")
    modes = result.add_mutually_exclusive_group()
    modes.add_argument("--capture-only", action="store_true", help="Capture without loading a detector")
    modes.add_argument("--health-bars", action="store_true", help="Experimental Control health-bar and level marker preview")
    modes.add_argument("--demo", action="store_true", help="Synthetic targets; works without Windows or model weights")
    result.add_argument("--model", type=Path, help="Local YOLO .pt model; no automatic model downloads")
    result.add_argument("--window-title", help="Case-insensitive game window title substring")
    result.add_argument("--process", action="append", metavar="EXE",
                        help="Game executable name (repeatable); replaces the profile's process_names")
    result.add_argument("--device", help="cpu, 0, or another Ultralytics device")
    result.add_argument("--frames", type=int, default=0, help="Stop after N frames; 0 runs until stopped")
    result.add_argument("--headless", action="store_true", help="Print metrics without displaying the preview")
    result.add_argument("--screenshots", type=Path, default=Path("datasets/control/images/raw"))
    result.add_argument("--assist", action="store_true", help="With --health-bars: hold right mouse button to aim at an estimated upper-body point below the marker")
    return result


def demo_frame(t):
    import numpy as np
    import cv2
    from math import sin
    from .detection.detector import Detection
    frame = np.full((720, 1280, 3), (24, 28, 30), dtype=np.uint8)
    detections = [Detection("enemy", 0.92, 580 + sin(t) * 100, 240, 95, 220),
                  Detection("enemy", 0.81, 820 + sin(t * 0.5) * 40, 275, 75, 170)]
    for d in detections:
        cv2.rectangle(frame, (int(d.x), int(d.y)), (int(d.x + d.width), int(d.y + d.height)), (55, 55, 110), -1)
    return frame, detections


def save_screenshot(frame, folder, profile, region):
    import cv2
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".png")
    if not cv2.imwrite(str(path), frame):
        raise OSError(f"Could not save screenshot: {path}")
    metadata = {"source": "raw capture (unannotated)", "window_title": profile.window_title,
                "region": list(region.bounds) if region else None}
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {path}")


def run(args, profile):
    if args.assist and not args.health_bars:
        raise ValueError('--assist requires --health-bars')
    from .targeting.marker_lock import MarkerLock
    lock = MarkerLock() if args.assist else None
    # DPI awareness must be configured before creating capture or preview surfaces.
    desktop = None
    if not args.demo:
        from .capture.window_detection import WindowsDesktop
        desktop = WindowsDesktop()
    import cv2
    from .overlay.debug_renderer import render
    detector = None
    if args.health_bars:
        from .detection.health_bars import HealthBarDetector
        detector = HealthBarDetector()
    elif not args.demo and not args.capture_only:
        from .detection.detector import YoloDetector
        # Profile model paths resolve relative to the profile's parent directory's parent.
        model_path = args.model or (args.profile.resolve().parent.parent / profile.model_path)
        detector = YoloDetector(profile, model_path)
    capture = None
    selector = TargetSelector(profile)
    count, paused = 0, False
    started = time.perf_counter()
    deadline = started
    last_report = started
    context = None
    warning = None
    hotkeys = {0x77: False, 0x78: False}  # F8 pause, F9 screenshot (edge triggered).
    screenshot_pending = False
    try:
        if desktop:
            from .capture.screen_capture import ScreenCapture
            capture = ScreenCapture(profile.capture_backend)
        if not args.headless:
            cv2.namedWindow(PREVIEW, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(PREVIEW, 480 if args.health_bars else 960, 200 if args.health_bars else 540)
            if args.health_bars:
                # Keep the preview outside the central crop on the tested
                # 1920x1080 desktop, so it cannot capture its own annotations.
                cv2.moveWindow(PREVIEW, 0, 0)
        processes = f" ({', '.join(profile.process_names)})" if profile.process_names else ""
        print("Demo: synthetic targets" if args.demo else f"Waiting for foreground game window: {profile.window_title}{processes}")
        print("Hold right mouse button: marker lock assistance." if lock else "Preview only: no mouse movement.")
        print("F8: pause, F9: screenshot, Ctrl+Shift+F12: exit globally.")
        while not args.frames or count < args.frames:
            if desktop and desktop.emergency_pressed():
                print("Emergency stop.")
                break
            key = -1 if args.headless else cv2.waitKey(1) & 0xFF
            pressed = set()
            if desktop:
                for virtual_key in hotkeys:
                    down = desktop.key_down(virtual_key)
                    if down and not hotkeys[virtual_key]:
                        pressed.add(virtual_key)
                    hotkeys[virtual_key] = down
            if key in (ord("q"), 27):
                break
            if not args.headless and cv2.getWindowProperty(PREVIEW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord("p") or 0x77 in pressed:
                paused = not paused
                selector.reset()
            if key == ord("s") or 0x78 in pressed:
                screenshot_pending = True
            window = desktop.find(profile.window_title, profile.process_names) if desktop else None
            status = None
            if paused:
                status = "Paused"
            elif desktop and (window is None or not desktop.is_foreground(window)):
                status = "Waiting: game must be visible and foreground"
            if status:
                selector.reset()
                if lock:
                    lock.cancel()
                    if not desktop.key_down(0x02):
                        lock.release()
                screenshot_pending = False
                # Replace the last result to avoid leaving stale targets on screen.
                if not args.headless:
                    import numpy as np
                    blank = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(blank, status, (15, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    cv2.imshow(PREVIEW, blank)
                if warning != status:
                    print(status)
                    warning = status
                time.sleep(0.03)
                deadline = time.perf_counter()
                continue
            warning = None
            now = time.perf_counter()
            if now < deadline:
                time.sleep(min(deadline - now, 0.01))
                continue
            tick = time.perf_counter()
            region = central_region(window.client, profile.capture_fraction) if window else None
            new_context = (window.handle, region) if window else None
            if new_context != context:
                selector.reset()
                if lock and context is not None:
                    lock.cancel()
                context = new_context
            if args.demo:
                frame, detections = demo_frame(tick - started)
            else:
                frame = capture.grab(region)
                detections = []
            captured = time.perf_counter()
            deadline = max(deadline + 1 / profile.capture_fps, captured)
            if frame is None:
                continue  # DXCam only returns a frame when the desktop changes.
            if detector is not None:
                detections = detector.detect(frame)
            inferred = time.perf_counter()
            selected = None if args.health_bars else selector.select(detections, (frame.shape[1] / 2, frame.shape[0] / 2), inferred)
            if lock:
                delta = lock.update(detections, (frame.shape[1]/2, frame.shape[0]/2),
                                    desktop.key_down(0x02), frame.shape[1]/960)
                if delta is not None:
                    from .capture.mouse_input import move_relative
                    move_relative(desktop, window, *delta)
            finished = time.perf_counter()
            count += 1
            metrics = {"frames": count, "pipeline_fps": round(count / max(finished - started, 0.001), 1),
                       "capture_ms": round((captured - tick) * 1000, 2),
                       "inference_ms": round((inferred - captured) * 1000, 2),
                       "pipeline_ms": round((finished - tick) * 1000, 2),
                       "detections": len(detections), "target_selected": selected is not None}
            if screenshot_pending:
                save_screenshot(frame, args.screenshots, profile, region)
                screenshot_pending = False
            if args.headless:
                if finished - last_report >= 1 or (args.frames and count == args.frames):
                    print(json.dumps(metrics))
                    last_report = finished
            else:
                label = "SYNTHETIC DEMO" if args.demo else "CAPTURE ONLY" if args.capture_only else "HUD MARKERS (EXPERIMENTAL)" if args.health_bars else "LOCAL YOLO"
                lines = [f"{label} | {'HOLD RIGHT MOUSE: ASSIST' if lock else 'preview only'}", f"Pipeline {metrics['pipeline_fps']} FPS | {metrics['pipeline_ms']} ms",
                         f"Capture {metrics['capture_ms']} ms | Inference {metrics['inference_ms']} ms",
                         f"{'Markers' if args.health_bars else 'Targets'} {len(detections)} | radius {profile.aim_radius} px"]
                if lock:
                    lines.append(lock.status)
                canvas = render(frame, detections, selected, profile, lines)
                if lock and lock.point is not None:
                    point = tuple(round(v) for v in lock.point)
                    cv2.drawMarker(canvas, point, (50, 230, 120), cv2.MARKER_CROSS, 22, 2)
                    cv2.line(canvas, (frame.shape[1]//2, frame.shape[0]//2), point, (50, 230, 120), 1)
                cv2.imshow(PREVIEW, canvas)
    finally:
        try:
            if capture is not None:
                capture.close()
        finally:
            if not args.headless:
                cv2.destroyAllWindows()
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.frames < 0:
            raise ValueError("--frames must be non-negative")
        if args.write_default_profile:
            save_profile(Profile(), args.profile)
            print(f"Wrote {args.profile}")
            return 0
        if args.list_windows:
            from .capture.window_detection import WindowsDesktop
            desktop = WindowsDesktop()
            for window in desktop.windows():
                print(f"{window.title} | {desktop.process_name(window.handle) or '?'} | {window.client.width}x{window.client.height} at {window.client.left},{window.client.top}")
            return 0
        profile = load_profile(args.profile) if args.profile.exists() else Profile().validate()
        if not args.profile.exists() and not args.demo:
            raise FileNotFoundError(f"Profile not found: {args.profile}. Run --write-default-profile first.")
        overrides = {key: value for key, value in {"window_title": args.window_title, "device": args.device,
                                                  "process_names": tuple(args.process) if args.process else None}.items() if value is not None}
        profile = replace(profile, **overrides).validate()
        return run(args, profile)
    except KeyboardInterrupt:
        print("Stopped.")
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"VisionAim: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
