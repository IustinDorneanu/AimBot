"""Reject orange effects without a level; handle drained and overlapping bars."""
import unittest
import cv2
import numpy as np
from visionaim.detection.health_bars import HealthBarDetector
from visionaim.main import parser


class HealthBarTests(unittest.TestCase):
    def frame(self):
        return np.zeros((540, 960, 3), np.uint8)

    def marker(self, frame, x, fill=60):
        cv2.rectangle(frame, (x, 200), (x+fill-1, 207), (20, 100, 225), -1)
        cv2.rectangle(frame, (x+28, 158), (x+31, 169), (20, 100, 225), -1)

    def test_full_and_drained_bar(self):
        for fill in (60, 15, 5, 3):
            frame = self.frame()
            self.marker(frame, 400, fill)
            found = HealthBarDetector().detect(frame)
            self.assertEqual(len(found), 1)
            self.assertAlmostEqual(found[0].x, 400, delta=1)

    def test_multi_digit_level_is_one_centered_marker(self):
        for glyphs in ([(424, 427), (432, 435)], [(426, 428), (431, 435)],
                       [(420, 423), (428, 431), (436, 439)]):
            frame = self.frame()
            cv2.rectangle(frame, (400, 200), (459, 207), (20, 100, 225), -1)
            for start, end in glyphs:
                cv2.rectangle(frame, (start, 158), (end, 169), (20, 100, 225), -1)
            with self.subTest(glyphs=glyphs):
                found = HealthBarDetector().detect(frame)
                self.assertEqual(len(found), 1)
                self.assertAlmostEqual(found[0].x, 400, delta=1.5)

    def test_effects_without_level_rejected(self):
        frame = self.frame()
        cv2.rectangle(frame, (400, 200), (459, 207), (20, 100, 225), -1)
        self.assertEqual(HealthBarDetector().detect(frame), [])

    def test_overlapping_bars(self):
        frame = self.frame()
        self.marker(frame, 400)
        self.marker(frame, 430)
        self.assertEqual(len(HealthBarDetector().detect(frame)), 2)

    def test_modes_are_exclusive(self):
        with self.assertRaises(SystemExit):
            parser().parse_args(['--capture-only', '--health-bars'])
