"""Validated, portable per-game configuration; coordinates use capture pixels."""
import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    window_title: str = "Control"
    process_names: tuple = ("Control_DX11.exe", "Control_DX12.exe")
    capture_backend: str = "mss"
    capture_fps: int = 30
    capture_fraction: float = 0.5
    detection_resolution: tuple = (640, 360)
    confidence: float = 0.6
    aim_radius: int = 150
    target_point: str = "upper_chest"
    target_persistence_ms: int = 250
    switch_ratio: float = 0.65
    model_path: str = "models/control.pt"
    enemy_classes: tuple = ("enemy",)
    device: str = "cpu"
    half: bool = False

    def validate(self):
        for name in ("capture_fps", "aim_radius", "target_persistence_ms"):
            value = getattr(self, name)
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
        if not 1 <= self.capture_fps <= 120:
            raise ValueError("capture_fps must be between 1 and 120")
        for name in ("capture_fraction", "confidence", "switch_ratio"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0.1 <= self.capture_fraction <= 1:
            raise ValueError("capture_fraction must be between 0.1 and 1")
        if not 0 <= self.confidence <= 1 or not 0 < self.switch_ratio < 1:
            raise ValueError("confidence must be 0–1 and switch_ratio must be 0–1 exclusive")
        if self.aim_radius <= 0 or self.target_persistence_ms < 0:
            raise ValueError("aim_radius must be positive and persistence non-negative")
        if self.capture_backend not in ("mss", "dxcam"):
            raise ValueError("capture_backend must be mss or dxcam")
        if self.target_point not in ("center_mass", "upper_chest", "head"):
            raise ValueError("target_point must be center_mass, upper_chest, or head")
        if (not isinstance(self.detection_resolution, (list, tuple))
                or len(self.detection_resolution) != 2
                or any(type(n) is not int or not 32 <= n <= 4096 for n in self.detection_resolution)):
            raise ValueError("detection_resolution must contain two integers between 32 and 4096")
        if (not isinstance(self.enemy_classes, (list, tuple)) or not self.enemy_classes
                or any(not isinstance(c, str) or not c.strip() for c in self.enemy_classes)):
            raise ValueError("enemy_classes must contain non-empty class names")
        if (not isinstance(self.process_names, (list, tuple))
                or any(not isinstance(p, str) or not p.strip() for p in self.process_names)):
            raise ValueError("process_names must be a list of executable names (empty to match by title only)")
        for name in ("window_title", "model_path", "device"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.half) is not bool:
            raise ValueError("half must be true or false")
        if self.half and self.device.lower() == "cpu":
            raise ValueError("half precision requires a CUDA device, e.g. device: '0'")
        return self


def load_profile(path: Path) -> Profile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Profile must be a JSON object")
    unknown = set(raw) - {f.name for f in fields(Profile)}
    if unknown:
        raise ValueError(f"Unknown profile settings: {', '.join(sorted(unknown))}")
    return Profile(**raw).validate()


def save_profile(profile: Profile, path: Path):
    profile.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
