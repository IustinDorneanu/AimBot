"""Experimental Control HUD marker detection; does not infer enemy bodies."""
from .detector import Detection


class HealthBarDetector:
    def detect(self, frame):
        import cv2
        import numpy as np
        scale = frame.shape[1] / 960
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # The supplied captures use an orange-red HUD, distinct from red effects.
        mask = cv2.inRange(hsv, np.array((7, 170, 140)), np.array((16, 255, 255)))
        kernel = np.ones((1, max(2, round(3 * scale))), np.uint8)
        horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        markers = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if not (3 * scale <= w <= 126 * scale and 3 * scale <= h <= 11 * scale):
                continue
            if w / h < .3 or cv2.countNonZero(mask[y:y+h, x:x+w]) / (w*h) < .85:
                continue
            # Health drains from the right. Locate the numeral above the full
            # 60px HUD bar, rather than above the center of its remaining fill.
            left, right = max(0, x), min(frame.shape[1], round(x+w+30*scale))
            top, bottom = max(0, round(y-52*scale)), max(0, round(y-22*scale))
            if bottom <= top or right <= left:
                continue
            _, _, stats, _ = cv2.connectedComponentsWithStats(mask[top:bottom, left:right])
            glyphs = sorted((left + sx, left + sx + sw) for sx, sy, sw, sh, area in stats[1:]
                            if 2*scale <= sw <= 16*scale and 7*scale <= sh <= 18*scale
                            and area >= 10*scale*scale)
            # Multi-digit levels are separate components; merge adjacent
            # glyphs so each numeral is centered once over its bar.
            numerals = []
            for start, end in glyphs:
                if numerals and start - numerals[-1][1] <= 5*scale:
                    numerals[-1][1] = max(numerals[-1][1], end)
                else:
                    numerals.append([start, end])
            for start, end in numerals:
                center = (start + end) / 2
                bar_left = center - 30*scale
                if not (x-4*scale <= bar_left <= x+w-2*scale):
                    continue
                marker_left = max(0, bar_left)
                markers.append(Detection('health-bar + level', 1.0, marker_left, top,
                                         min(60*scale, frame.shape[1]-marker_left), y+h-top))
        return sorted(markers, key=lambda d: (d.y, d.x))
