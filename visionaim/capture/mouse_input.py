"""Win32 relative motion only; no button events, hooks, or game access.

https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput
"""
import ctypes
from ctypes import wintypes


class MouseInput(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class InputUnion(ctypes.Union):
    _fields_ = [('mi', MouseInput)]


class Input(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', wintypes.DWORD), ('data', InputUnion)]


def move_relative(desktop, window, dx, dy, key=0x02):
    # Recheck immediately before each event, after capture/detection processing.
    if not (dx or dy) or not desktop.is_foreground(window) or not desktop.key_down(key) or desktop.emergency_pressed():
        return False
    event = Input(type=0, data=InputUnion(mi=MouseInput(dx, dy, 0, 1, 0, 0)))
    send = desktop.api.SendInput
    send.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    send.restype = wintypes.UINT
    if send(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
        raise RuntimeError('Windows rejected mouse input; assistance stopped')
    return True
