import logging

_log = logging.getLogger("hamster_ai.fullscreen")


def is_fullscreen() -> bool:
    """Return True if the foreground window covers the entire monitor."""
    try:
        import win32api
        import win32con
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        monitor_rect = win32api.GetMonitorInfo(monitor)["Monitor"]
        win_rect = win32gui.GetWindowRect(hwnd)
        return tuple(win_rect) == tuple(monitor_rect)
    except Exception as exc:
        _log.debug(f"fullscreen check error: {exc}")
        return False
