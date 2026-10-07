from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self):
        return self.width / 2, self.height / 2

    @property
    def bounds(self):
        return self.left, self.top, self.left + self.width, self.top + self.height

    def contains(self, other):
        a, b, c, d = self.bounds
        e, f, g, h = other.bounds
        return a <= e and b <= f and c >= g and d >= h


def central_region(window: Rect, fraction: float) -> Rect:
    if window.width <= 0 or window.height <= 0 or not 0 < fraction <= 1:
        raise ValueError("Window dimensions and crop fraction must be positive")
    width, height = max(1, int(window.width * fraction)), max(1, int(window.height * fraction))
    return Rect(window.left + (window.width - width) // 2,
                window.top + (window.height - height) // 2, width, height)
