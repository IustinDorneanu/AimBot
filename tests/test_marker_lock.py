import unittest
from unittest.mock import Mock
from visionaim.detection.detector import Detection
from visionaim.targeting.marker_lock import MarkerLock
from visionaim.capture.mouse_input import Input, move_relative
import ctypes


def marker(x=450, y=140):
    return Detection('health-bar + level', 1, x, y, 60, 50)


class MarkerLockTests(unittest.TestCase):
    def test_off_center_acquisition_corrects_both_sides(self):
        for x, expected_dx in [(430, -5), (470, 5)]:
            lock = MarkerLock()
            self.assertEqual(lock.update([marker(x)], (480, 230), True), (expected_dx, 0))
            self.assertEqual(lock.point, (x+30, 230))
            lock.update([marker(x+10)], (480, 230), True)
            self.assertEqual(lock.point, (x+40, 230))

    def test_acquisition_moves_vertically_into_estimated_body(self):
        lock = MarkerLock()
        self.assertEqual(lock.update([marker()], (480, 270), True), (0, -10))
        self.assertEqual(lock.point, (480, 230))

    def test_acquire_tracks_body_point_and_caps_movement(self):
        lock = MarkerLock()
        self.assertEqual(lock.update([marker()], (480, 230), True), (0, 0))
        self.assertEqual(lock.update([marker(480)], (480, 230), True), (8, 0))
        self.assertEqual(lock.point, (510, 230))
        self.assertEqual(lock.update([marker(520)], (480, 230), True), (10, 0))

    def test_brief_missing_marker_pauses_motion_and_recovers(self):
        lock = MarkerLock()
        lock.update([marker()], (480, 270), True, now=1)
        self.assertIsNone(lock.update([], (480, 270), True, now=1.1))
        self.assertIsNone(lock.point)
        self.assertFalse(lock.blocked)
        self.assertEqual(lock.update([marker()], (480, 270), True, now=1.2), (0, -10))
        self.assertIsNone(lock.update([marker()], (480, 270), False))
        self.assertEqual(lock.update([marker()], (480, 270), True), (0, -10))

    def test_extended_marker_loss_reacquires_while_held(self):
        lock = MarkerLock()
        lock.update([marker()], (480, 270), True, now=1)
        self.assertIsNone(lock.update([], (480, 270), True, now=1.36))
        self.assertFalse(lock.blocked)
        self.assertEqual(lock.update([marker()], (480, 270), True, now=1.4), (0, -10))
        lock.update([], (480, 270), False, now=1.5)
        self.assertEqual(lock.update([marker()], (480, 270), True, now=1.6), (0, -10))

    def test_missing_marker_cannot_recover_to_distant_enemy(self):
        lock = MarkerLock()
        lock.update([marker()], (480, 270), True, now=1)
        self.assertIsNone(lock.update([marker(600)], (480, 270), True, now=1.1))
        self.assertIsNone(lock.point)
        self.assertEqual(lock.anchor, (480, 190))

    def test_ambiguous_targets_pause_until_unique(self):
        lock = MarkerLock()
        self.assertIsNone(lock.update([marker(), marker(460)], (480, 270), True))
        lock.update([marker()], (480, 270), True)
        self.assertIsNone(lock.update([marker(), marker(460)], (480, 270), True))
        self.assertFalse(lock.blocked)
        self.assertEqual(lock.update([marker()], (480, 270), True), (0, -10))

    def test_mouse_movement_can_shift_marker_without_losing_lock(self):
        lock = MarkerLock()
        lock.update([marker()], (480, 270), True, now=1)
        self.assertIsNotNone(lock.update([marker(530)], (480, 270), True, now=1.03))
        self.assertEqual(lock.point, (560, 230))

    def test_cancel_requires_release_before_reacquisition(self):
        lock = MarkerLock()
        lock.cancel()
        self.assertIsNone(lock.update([marker()], (480, 270), True))
        lock.update([], (480, 270), False)
        self.assertEqual(lock.update([marker()], (480, 270), True), (0, -10))

    def test_recheck_focus_key_and_emergency_before_input(self):
        for focus, held, emergency in [(False, True, False), (True, False, False), (True, True, True)]:
            desktop = Mock()
            desktop.is_foreground.return_value = focus
            desktop.key_down.return_value = held
            desktop.emergency_pressed.return_value = emergency
            self.assertFalse(move_relative(desktop, object(), 5, -5))
            desktop.api.SendInput.assert_not_called()

    def test_input_layout_and_motion_without_clicks(self):
        self.assertEqual(ctypes.sizeof(Input), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        desktop = Mock()
        desktop.is_foreground.return_value = True
        desktop.key_down.return_value = True
        desktop.emergency_pressed.return_value = False
        def send(count, pointer, size):
            event = ctypes.cast(pointer, ctypes.POINTER(Input)).contents
            self.assertEqual((event.type, event.mi.dx, event.mi.dy, event.mi.dwFlags), (0, 5, -5, 1))
            return 1
        desktop.api.SendInput.side_effect = send
        self.assertTrue(move_relative(desktop, object(), 5, -5))
        desktop.key_down.assert_called_once_with(0x02)
