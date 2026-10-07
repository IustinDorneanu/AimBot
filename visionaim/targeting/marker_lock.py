"""Hold-to-lock markers with a brief, motion-free recovery window."""
from math import hypot
from time import monotonic


class MarkerLock:
    def __init__(self, gain=.25, max_step=10, recovery_seconds=.35):
        self.gain, self.max_step = gain, max_step
        self.recovery_seconds = recovery_seconds
        self.release()

    def release(self):
        self.anchor = self.offset = self.point = None
        self.last_seen = None
        self.blocked = False
        self.status = 'Aim, then hold right mouse button'

    def cancel(self):
        self.anchor = self.offset = self.point = None
        self.last_seen = None
        self.blocked = True
        self.status = 'Lock lost: release right mouse button to rearm'

    @staticmethod
    def position(marker):
        return marker.x + marker.width/2, marker.y + marker.height

    def update(self, markers, center, held, scale=1, now=None):
        now = monotonic() if now is None else now
        if not held:
            self.release()
            return None
        if self.blocked:
            return None
        if self.anchor is not None and now - self.last_seen > self.recovery_seconds:
            # Detection loss rearms acquisition while the button remains held.
            # Focus/pause cancellation still requires an explicit release.
            self.anchor = self.offset = self.point = None
            self.last_seen = None
        if self.anchor is None:
            candidates = [m for m in markers
                          if abs(self.position(m)[0]-center[0]) <= 90*scale
                          and 10*scale <= center[1]-self.position(m)[1] <= 180*scale]
            if len(candidates) != 1:
                self.status = 'Need one marker near crosshair'
                return None
            self.anchor = self.position(candidates[0])
            # In the supplied Control captures, an upper-body point lies about
            # 40 pixels below the HUD bar at 960px capture width. This is a HUD
            # heuristic, not a detected body/head or the initial crosshair.
            self.offset = (0, 40*scale)
        else:
            candidates = [m for m in markers
                          if hypot(self.position(m)[0]-self.anchor[0],
                                   self.position(m)[1]-self.anchor[1]) <= 100*scale]
            if not candidates:
                # Muzzle flash, recoil, and health changes can interrupt HUD
                # detection. Keep identity briefly, but never move to stale pixels.
                self.point = None
                self.status = 'Marker briefly hidden: waiting to resume lock'
                return None
            if len(candidates) != 1:
                self.point = None
                self.status = 'Multiple markers: waiting for a clear target'
                return None
            self.anchor = self.position(candidates[0])
        self.last_seen = now
        self.point = (self.anchor[0]+self.offset[0], self.anchor[1]+self.offset[1])
        self.status = 'LOCKED | release right mouse button to unlock'
        error = (self.point[0]-center[0], self.point[1]-center[1])
        if hypot(*error) > 150*scale:
            self.cancel()
            return None
        dx, dy = [0 if abs(v) < 2*scale else v*self.gain for v in error]
        length = hypot(dx, dy)
        if length > self.max_step:
            dx, dy = dx*self.max_step/length, dy*self.max_step/length
        return round(dx), round(dy)
