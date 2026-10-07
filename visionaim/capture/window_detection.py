"""Win32 client-area discovery. No memory access, injection, or rendering hooks."""
import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from ..geometry import Rect


@dataclass(frozen=True)
class GameWindow:
    handle: int
    title: str
    client: Rect


class WindowsDesktop:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Live game capture requires Windows 10 or later. Use --demo here.")
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        signatures = {
            "EnumWindows": ([self.callback_type, wintypes.LPARAM], wintypes.BOOL),
            "IsWindowVisible": ([wintypes.HWND], wintypes.BOOL),
            "IsIconic": ([wintypes.HWND], wintypes.BOOL),
            "GetWindowTextLengthW": ([wintypes.HWND], ctypes.c_int),
            "GetWindowTextW": ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetClientRect": ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            "ClientToScreen": ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            "GetForegroundWindow": ([], wintypes.HWND),
            "GetAsyncKeyState": ([ctypes.c_int], ctypes.c_short),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        # Windows 10 physical pixel coordinates, including displays at 125/150% scaling.
        try:
            fn = self.api.SetProcessDpiAwarenessContext
            fn.argtypes, fn.restype = [ctypes.c_void_p], wintypes.BOOL
            fn(ctypes.c_void_p(-4))
        except AttributeError:
            shcore = ctypes.WinDLL("shcore")
            shcore.SetProcessDpiAwareness(2)

    def windows(self):
        found = []

        @self.callback_type
        def visit(hwnd, _):
            if self.api.IsWindowVisible(hwnd) and not self.api.IsIconic(hwnd):
                size = self.api.GetWindowTextLengthW(hwnd)
                if size:
                    buf = ctypes.create_unicode_buffer(size + 1)
                    self.api.GetWindowTextW(hwnd, buf, size + 1)
                    rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
                    if self.api.GetClientRect(hwnd, ctypes.byref(rect)) and self.api.ClientToScreen(hwnd, ctypes.byref(origin)):
                        if rect.right > 0 and rect.bottom > 0:
                            found.append(GameWindow(hwnd, buf.value, Rect(origin.x, origin.y, rect.right, rect.bottom)))
            return True

        if not self.api.EnumWindows(visit, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return found

    def find(self, title):
        matches = [w for w in self.windows() if title.casefold() in w.title.casefold()]
        if not matches:
            return None
        foreground = self.api.GetForegroundWindow()
        return next((w for w in matches if w.handle == foreground), matches[0])

    def is_foreground(self, window):
        return self.api.GetForegroundWindow() == window.handle

    def emergency_pressed(self):
        return all(self.api.GetAsyncKeyState(key) & 0x8000 for key in (0x11, 0x10, 0x7B))

    def key_down(self, key):
        return bool(self.api.GetAsyncKeyState(key) & 0x8000)
