"""Exercise live-loop gating and cleanup without Windows or a game."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from visionaim.config import Profile
from visionaim.geometry import Rect
from visionaim.main import parser, run


class PipelineTests(unittest.TestCase):
    def test_assistance_runs_only_for_held_key_and_visible_markers(self):
        from unittest.mock import Mock
        from visionaim.capture.window_detection import GameWindow
        from visionaim.detection.detector import Detection
        window = GameWindow(123, 'Control', Rect(0, 0, 1920, 1080))
        desktop = SimpleNamespace(emergency_pressed=lambda: False, key_down=lambda key: key == 0x02,
                                  find=lambda title: window, is_foreground=lambda _: True)
        capture = Mock()
        capture.grab.return_value = np.zeros((540, 960, 3), dtype=np.uint8)
        detector = Mock()
        detector.detect.side_effect = [[Detection('health-bar + level', 1, x, 140, 60, 50)]
                                       for x in (450, 480)] + [[]]
        args = parser().parse_args(['--health-bars', '--assist', '--headless', '--frames', '3'])
        with patch('visionaim.capture.window_detection.WindowsDesktop', return_value=desktop), \
                patch('visionaim.capture.screen_capture.ScreenCapture', return_value=capture), \
                patch('visionaim.detection.health_bars.HealthBarDetector', return_value=detector), \
                patch('visionaim.capture.mouse_input.move_relative') as move:
            self.assertEqual(run(args, Profile()), 0)
        self.assertEqual(move.call_count, 2)
        self.assertEqual(move.call_args.args[2:], (6, -8))
        capture.close.assert_called_once()

    def test_capture_waits_for_foreground(self):
        from visionaim.capture.window_detection import GameWindow
        window = GameWindow(123, "Control", Rect(100, 100, 1280, 720))
        focus = iter((False, True))
        desktop = SimpleNamespace(emergency_pressed=lambda: False, key_down=lambda key: False,
                                  find=lambda title: window, is_foreground=lambda _: next(focus))
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        from unittest.mock import Mock
        capture = Mock()
        capture.grab.return_value = frame
        args = parser().parse_args(["--capture-only", "--headless", "--frames", "1"])
        with patch("visionaim.capture.window_detection.WindowsDesktop", return_value=desktop), \
                patch("visionaim.capture.screen_capture.ScreenCapture", return_value=capture):
            self.assertEqual(run(args, Profile()), 0)
        # No capture while the game is in the background, and resources are closed.
        capture.grab.assert_called_once_with(Rect(420, 280, 640, 360))
        capture.close.assert_called_once()

    def test_emergency_stop_exits_before_capture(self):
        from unittest.mock import Mock
        desktop = SimpleNamespace(emergency_pressed=lambda: True)
        capture = Mock()
        args = parser().parse_args(["--capture-only", "--headless"])
        with patch("visionaim.capture.window_detection.WindowsDesktop", return_value=desktop), \
                patch("visionaim.capture.screen_capture.ScreenCapture", return_value=capture):
            self.assertEqual(run(args, Profile()), 0)
        capture.grab.assert_not_called()
        capture.close.assert_called_once()

    def test_capture_error_still_releases_resources(self):
        from unittest.mock import Mock
        from visionaim.capture.window_detection import GameWindow
        window = GameWindow(123, "Control", Rect(0, 0, 1280, 720))
        desktop = SimpleNamespace(emergency_pressed=lambda: False, key_down=lambda key: False,
                                  find=lambda title: window, is_foreground=lambda _: True)
        capture = Mock()
        capture.grab.side_effect = RuntimeError("capture failed")
        args = parser().parse_args(["--capture-only", "--headless"])
        with patch("visionaim.capture.window_detection.WindowsDesktop", return_value=desktop), \
                patch("visionaim.capture.screen_capture.ScreenCapture", return_value=capture):
            with self.assertRaisesRegex(RuntimeError, "capture failed"):
                run(args, Profile())
        capture.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
