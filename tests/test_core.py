import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from visionaim.config import Profile, load_profile, save_profile
from visionaim.geometry import Rect, central_region
from visionaim.detection.detector import Detection
from visionaim.targeting.target_selector import TargetSelector


def enemy(x, y=65, confidence=0.9, label="enemy"):
    return Detection(label, confidence, x - 10, y - 35, 20, 100)


class ConfigurationTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "control.json"
            save_profile(Profile(), path)
            profile = load_profile(path)
            self.assertEqual(profile.capture_fps, 30)
            self.assertEqual(tuple(profile.detection_resolution), (640, 360))

    def test_invalid_settings(self):
        for change in ({"capture_fps": 0}, {"confidence": 1.1}, {"capture_fraction": 0},
                       {"half": True}, {"detection_resolution": [640, -1]},
                       {"capture_fps": True}, {"target_point": "adaptive"},
                       {"confidence": float("nan")}, {"enemy_classes": "enemy"},
                       {"aim_radius": 0}, {"half": "false"},
                       {"process_names": "Control.exe"}, {"process_names": [""]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(Profile(), **change).validate()

    def test_unknown_setting_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            path.write_text(json.dumps({"aim_raduis": 150}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profile(path)


class GeometryTests(unittest.TestCase):
    def test_crop_preserves_crosshair_with_negative_monitor_coordinates(self):
        region = central_region(Rect(-2560, 0, 2560, 1440), 0.5)
        self.assertEqual(region, Rect(-1920, 360, 1280, 720))
        self.assertEqual(region.center, (640, 360))

    def test_target_modes(self):
        detection = Detection("enemy", 0.9, 10, 20, 100, 200)
        self.assertEqual(detection.point(), (60, 90))
        self.assertEqual(detection.point("center_mass"), (60, 120))
        self.assertEqual(detection.point("head"), (60, 50))


class TargetTests(unittest.TestCase):
    def setUp(self):
        self.selector = TargetSelector(Profile())
        self.crosshair = (100, 65)

    def test_nearest_valid_enemy(self):
        nearest = enemy(110)
        selected = self.selector.select([enemy(102, confidence=0.1), enemy(101, label="player"),
                                         enemy(290), enemy(140), nearest], self.crosshair, 1)
        self.assertIs(selected, nearest)

    def test_persistence_follows_current_box_without_stale_coordinates(self):
        self.selector.select([enemy(140)], self.crosshair, 1)
        moved = enemy(142)
        self.assertIs(self.selector.select([moved, enemy(130)], self.crosshair, 1.1), moved)

    def test_substantially_closer_target_breaks_lock(self):
        self.selector.select([enemy(140)], self.crosshair, 1)
        closer = enemy(105)
        self.assertIs(self.selector.select([enemy(140), closer], self.crosshair, 1.1), closer)

    def test_expired_lock_chooses_nearest(self):
        self.selector.select([enemy(140)], self.crosshair, 1)
        closer = enemy(130)
        self.assertIs(self.selector.select([enemy(140), closer], self.crosshair, 1.3), closer)

    def test_disappearance_and_fov_exit_clear_lock(self):
        self.selector.select([enemy(140)], self.crosshair, 1)
        self.assertIsNone(self.selector.select([], self.crosshair, 1.05))
        self.assertIsNone(self.selector.previous)
        self.selector.select([enemy(140)], self.crosshair, 2)
        self.assertIsNone(self.selector.select([enemy(290)], self.crosshair, 2.05))

    def test_radius_boundary_is_inclusive(self):
        boundary = enemy(250)
        self.assertIs(self.selector.select([boundary], self.crosshair, 1), boundary)


if __name__ == "__main__":
    unittest.main()
