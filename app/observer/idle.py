import ctypes
import ctypes.wintypes
import logging

_log = logging.getLogger("hamster_ai.idle")


def get_idle_seconds() -> int:
    """Return seconds since the last keyboard or mouse input."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.UINT),
                ("dwTime", ctypes.wintypes.DWORD),
            ]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        tick_now = ctypes.windll.kernel32.GetTickCount()
        # GetTickCount wraps at ~49 days; handle negative result safely
        elapsed_ms = (tick_now - lii.dwTime) & 0xFFFFFFFF
        return elapsed_ms // 1000
    except Exception as exc:
        _log.debug(f"idle_seconds error: {exc}")
        return 0
