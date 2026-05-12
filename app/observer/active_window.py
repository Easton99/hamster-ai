import logging
import re

_log = logging.getLogger("hamster_ai.active_window")

# Strip control characters and Braille block (U+2800-U+28FF) which terminal
# UIs like Claude Code use for progress spinners in the window title.
_CLEAN_RE = re.compile(r"[\x00-\x1f\x7f⠀-⣿]+")


def get_active_window() -> tuple[str, str]:
    """Return (process_name, window_title) for the current foreground window.
    Returns ('', '') if pywin32/psutil are unavailable or the call fails."""
    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ("", "")

        raw_title = win32gui.GetWindowText(hwnd) or ""
        title = _CLEAN_RE.sub("", raw_title).strip()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            name = psutil.Process(pid).name()
        except Exception:
            name = ""

        return (name, title)
    except Exception as exc:
        _log.debug(f"active_window error: {exc}")
        return ("", "")
