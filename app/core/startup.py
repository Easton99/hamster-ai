"""Windows autostart management via the registry Run key."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_log = logging.getLogger("hamster_ai.startup")
_REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME  = "HamsterAI"


def get_launch_command() -> str:
    """Return the command stored in the registry Run key.

    When frozen (PyInstaller), points at the .exe.
    When running from source, uses pythonw.exe (no console) + app/main.py --startup.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --startup'

    python   = Path(sys.executable)
    pythonw  = python.parent / "pythonw.exe"
    main_py  = Path(__file__).resolve().parent.parent / "main.py"
    exe      = pythonw if pythonw.exists() else python
    return f'"{exe}" "{main_py}" --startup'


def set_autostart(enabled: bool) -> bool:
    """Write or remove the HKCU Run key. Returns True on success."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, get_launch_command())
                _log.info("Autostart enabled.")
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                    _log.info("Autostart disabled.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as exc:
        _log.warning(f"set_autostart failed: {exc}")
        return False


def is_autostart_set() -> bool:
    """Return True if the registry Run key exists for this app."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
