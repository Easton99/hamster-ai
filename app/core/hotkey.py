import threading
from typing import Callable


class GlobalHotkey:
    """Register a system-wide hotkey on Windows using ctypes."""

    def __init__(self) -> None:
        self._id = 1
        self._callback: Callable | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._registered = False

    def register(self, hotkey_str: str, callback: Callable) -> bool:
        try:
            import ctypes
            from ctypes import wintypes

            mod, vk = _parse_hotkey(hotkey_str)
            ok = ctypes.windll.user32.RegisterHotKey(None, self._id, mod, vk)
            if not ok:
                return False
            self._callback = callback
            self._registered = True
            self._running = True
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()
            return True
        except Exception:
            return False

    def unregister(self) -> None:
        self._running = False
        if self._registered:
            try:
                import ctypes
                ctypes.windll.user32.UnregisterHotKey(None, self._id)
            except Exception:
                pass
            self._registered = False

    def _listen(self) -> None:
        import ctypes
        from ctypes import wintypes

        msg = wintypes.MSG()
        while self._running:
            if ctypes.windll.user32.PeekMessageW(
                ctypes.byref(msg), None, 0x0312, 0x0312, 1
            ):
                if msg.message == 0x0312 and msg.wParam == self._id:
                    if self._callback:
                        self._callback()


_MOD_MAP = {
    "ctrl":  0x0002,
    "shift": 0x0004,
    "alt":   0x0001,
    "win":   0x0008,
}

_VK_MAP = {
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "space": 0x20, "return": 0x0D, "tab": 0x09,
}


def _parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    mod = 0
    vk = 0
    for part in parts:
        if part in _MOD_MAP:
            mod |= _MOD_MAP[part]
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
        elif len(part) == 1:
            vk = ord(part.upper())
    return mod, vk
