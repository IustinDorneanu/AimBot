"""Detector integration using synthetic model output; never downloads weights."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from visionaim.config import Profile
from visionaim.detection.detector import YoloDetector
from visionaim.main import save_screenshot


class DetectorTests(unittest.TestCase):
    def test_resized_coordinates_return_to_capture_space_and_filter_classes(self):
        output = np.array([[100, 50, 200, 150, 0.91, 0]], dtype=float)
        boxes = SimpleNamespace(data=SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: output)))
        model = SimpleNamespace(names={0: "enemy", 1: "player"})
        calls = []

        def predict(frame, **kwargs):
            calls.append((frame.shape, kwargs))
            return [SimpleNamespace(boxes=boxes)]

        model.predict = predict
        with tempfile.TemporaryDirectory() as folder:
            weights = Path(folder) / "control.pt"
            weights.touch()
            with patch.dict("sys.modules", {"ultralytics": SimpleNamespace(YOLO=lambda *args, **kwargs: model)}):
                detector = YoloDetector(Profile(), weights)
                detections = detector.detect(np.zeros((720, 1280, 3), dtype=np.uint8))
        self.assertEqual(calls[0][0], (360, 640, 3))
        self.assertEqual(calls[0][1]["classes"], [0])
        detection = detections[0]
        self.assertEqual((detection.x, detection.y, detection.width, detection.height), (200, 100, 200, 200))

    def test_missing_weights_fail_before_import_or_download(self):
        with self.assertRaises(FileNotFoundError):
            YoloDetector(Profile(), Path("/nonexistent/visionaim-model.pt"))

    def test_non_enemy_weights_rejected(self):
        model = SimpleNamespace(names={0: "person"})
        with tempfile.TemporaryDirectory() as folder:
            weights = Path(folder) / "model.pt"
            weights.touch()
            with patch.dict("sys.modules", {"ultralytics": SimpleNamespace(YOLO=lambda *args, **kwargs: model)}):
                with self.assertRaises(ValueError):
                    YoloDetector(Profile(), weights)

    def test_raw_screenshot_is_unchanged(self):
        import cv2
        frame = np.full((20, 30, 3), (13, 27, 42), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as folder:
            save_screenshot(frame, Path(folder), Profile(), None)
            files = list(Path(folder).glob("*.png"))
            self.assertEqual(len(files), 1)
            np.testing.assert_array_equal(cv2.imread(str(files[0])), frame)
            self.assertTrue(files[0].with_suffix(".json").exists())


if __name__ == "__main__":
    unittest.main()
