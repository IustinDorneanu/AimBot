from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

    def point(self, mode="upper_chest"):
        fraction = {"center_mass": 0.5, "upper_chest": 0.35, "head": 0.15}[mode]
        return self.x + self.width / 2, self.y + self.height * fraction


class YoloDetector:
    def __init__(self, profile, model_path: Path):
        if not model_path.is_file():
            raise FileNotFoundError(f"Local model not found: {model_path}. Use --capture-only to collect training images.")
        from ultralytics import YOLO
        self.profile = profile
        self.model = YOLO(str(model_path), task="detect")
        self.classes = [idx for idx, name in self.model.names.items() if name in profile.enemy_classes]
        if not self.classes:
            raise ValueError(f"Model classes {self.model.names} do not include {profile.enemy_classes}. Use a trained enemy model.")

    def detect(self, frame):
        import cv2
        w, h = self.profile.detection_resolution
        resized = cv2.resize(frame, (w, h))
        result = self.model.predict(resized, imgsz=max(w, h), conf=self.profile.confidence,
                                    classes=self.classes, device=self.profile.device,
                                    half=self.profile.half, verbose=False)[0]
        sx, sy = frame.shape[1] / w, frame.shape[0] / h
        detections = []
        if result.boxes is not None:
            for x1, y1, x2, y2, conf, cls in result.boxes.data.cpu().numpy():
                detections.append(Detection(self.model.names[int(cls)], float(conf),
                                            float(x1 * sx), float(y1 * sy),
                                            float((x2 - x1) * sx), float((y2 - y1) * sy)))
        return detections
