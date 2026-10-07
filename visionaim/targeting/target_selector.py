"""Nearest target with spatial matching and bounded persistence. No input output."""
from math import hypot


def overlap(a, b):
    left, top = max(a.x, b.x), max(a.y, b.y)
    right = min(a.x + a.width, b.x + b.width)
    bottom = min(a.y + a.height, b.y + b.height)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = a.width * a.height + b.width * b.height - intersection
    return intersection / union if union > 0 else 0


class TargetSelector:
    def __init__(self, profile):
        self.profile = profile
        self.reset()

    def reset(self):
        self.previous = None
        self.locked_at = 0

    def select(self, detections, crosshair, now):
        def distance(detection):
            x, y = detection.point(self.profile.target_point)
            return hypot(x - crosshair[0], y - crosshair[1])

        valid = [d for d in detections if d.label in self.profile.enemy_classes
                 and d.confidence >= self.profile.confidence
                 and d.width > 0 and d.height > 0 and distance(d) <= self.profile.aim_radius]
        if not valid:
            self.reset()
            return None
        nearest = min(valid, key=distance)
        matched = None
        if self.previous is not None:
            candidate = max(valid, key=lambda d: overlap(self.previous, d))
            if overlap(self.previous, candidate) >= 0.2:
                matched = candidate
        active_lock = now - self.locked_at < self.profile.target_persistence_ms / 1000
        chosen = nearest
        if matched is not None and active_lock and distance(nearest) >= distance(matched) * self.profile.switch_ratio:
            chosen = matched
        if matched is None or chosen is not matched:
            self.locked_at = now
        self.previous = chosen
        return chosen
