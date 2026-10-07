"""Capture adapters with nonblocking acquisition; frames are BGR arrays."""
from ..geometry import Rect


class ScreenCapture:
    def __init__(self, backend="mss"):
        import mss
        self.desktop = mss.mss()
        self.camera = None
        self.backend = backend
        if backend == "dxcam":
            try:
                if len(self.desktop.monitors) != 2:
                    raise RuntimeError("The prototype DXCam adapter supports one monitor only; use mss for multiple monitors.")
                import dxcam
                self.camera = dxcam.create(device_idx=0, output_idx=0, output_color="BGR")
            except Exception:
                self.desktop.close()
                raise

    def grab(self, region: Rect):
        import numpy as np
        if self.camera is not None:
            # This optional adapter is explicitly limited to DXGI device 0/output 0.
            info = self.camera.width, self.camera.height
            if not Rect(0, 0, *info).contains(region):
                raise RuntimeError("DXCam requires the game on device 0/output 0 at origin (0,0); use mss for other monitors.")
            return self.camera.grab(region=region.bounds)
        monitors = [Rect(m["left"], m["top"], m["width"], m["height"]) for m in self.desktop.monitors[1:]]
        if not any(m.contains(region) for m in monitors):
            raise RuntimeError("Move the game fully onto one monitor before capturing.")
        shot = self.desktop.grab({"left": region.left, "top": region.top,
                                  "width": region.width, "height": region.height})
        return np.asarray(shot)[:, :, :3].copy()

    def close(self):
        try:
            if self.camera is not None:
                self.camera.release()
        finally:
            self.desktop.close()
