"""Milestone 16 smoke test â€” UI/UX upgrades (theme, hotkey, notification history, widgets)."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

passed = failed = 0


def check(label: str, ok: bool) -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")


print("\n--- Hamster AI Milestone 16 Smoke Test ---\n")

# â”€â”€ Theme system â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Theme System ]")
from app.desktop import theme as _theme_mod

# Verify the three themes exist
check("soft_hamster_minimal theme defined", "soft_hamster_minimal" in _theme_mod._THEMES)
check("dark_hamster theme defined", "dark_hamster" in _theme_mod._THEMES)
check("high_contrast theme defined", "high_contrast" in _theme_mod._THEMES)

# Default is light
_theme_mod._reload()
light_bg = _theme_mod.BG
check("default BG is light", light_bg == "#FAF7F2")
check("default ACCENT is brown", _theme_mod.ACCENT == "#A67C52")

# Switch to dark
_theme_mod.set_theme("dark_hamster")
check("dark theme changes BG", _theme_mod.BG == "#1E1A17")
check("dark theme keeps ACCENT", _theme_mod.ACCENT == "#A67C52")
check("STYLESHEET updated after theme switch", _theme_mod.BG in _theme_mod.STYLESHEET)

# Switch to high contrast
_theme_mod.set_theme("high_contrast")
check("high_contrast BG is black", _theme_mod.BG == "#000000")
check("high_contrast ACCENT is yellow", _theme_mod.ACCENT == "#FFCC00")

# Back to light
_theme_mod.set_theme("soft_hamster_minimal")
check("can switch back to light theme", _theme_mod.BG == "#FAF7F2")

# Unknown theme is ignored safely
_theme_mod.set_theme("no_such_theme")
check("unknown theme is ignored", _theme_mod.BG == "#FAF7F2")

# â”€â”€ Hotkey parser â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Global Hotkey Parser ]")
from app.core.hotkey import GlobalHotkey, _parse_hotkey

mod, vk = _parse_hotkey("Ctrl+Shift+H")
check("Ctrl+Shift+H parses mod = Ctrl|Shift (0x0006)", mod == 0x0006)
check("Ctrl+Shift+H parses vk = H (0x48)", vk == 0x48)

mod2, vk2 = _parse_hotkey("Alt+F12")
check("Alt+F12 parses mod = Alt (0x0001)", mod2 == 0x0001)
check("Alt+F12 parses vk = F12 (0x7B)", vk2 == 0x7B)

mod3, vk3 = _parse_hotkey("Ctrl+Shift+Z")
check("Ctrl+Shift+Z parses correctly", mod3 == 0x0006 and vk3 == ord("Z"))

hk = GlobalHotkey()
check("GlobalHotkey instantiates", hk is not None)
check("GlobalHotkey.unregister() safe when not registered", (hk.unregister() or True))

# â”€â”€ Notification History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Notification History ]")
with tempfile.TemporaryDirectory() as tmp:
    from app.memory.db import Database
    from app.core.notification_history import NotificationHistory

    db = Database(Path(tmp) / "test.db")
    nh = NotificationHistory(db)

    nh.add("greeting", "Hamster online.")
    nh.add("reminder", "Check email")
    nh.add("insight", "You coded 3 hours today.")

    entries = nh.list_recent(10)
    check("list_recent returns 3 entries", len(entries) == 3)
    check("entries have correct fields", all(
        hasattr(e, "id") and hasattr(e, "timestamp") and
        hasattr(e, "type") and hasattr(e, "content") and hasattr(e, "dismissed")
        for e in entries
    ))
    check("entries ordered most recent first", entries[0].content == "You coded 3 hours today.")

    nh.dismiss(entries[2].id)
    after_dismiss = nh.list_recent(10)
    dismissed = [e for e in after_dismiss if e.dismissed]
    check("dismiss marks entry as dismissed", len(dismissed) == 1)

    nh.clear()
    check("clear() removes all entries", len(nh.list_recent(10)) == 0)

    import time as _time
    nh.add("system", "First")
    nh.add("system", "Second")
    _time.sleep(1.1)
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    nh.add("system", "Third")
    n = nh.clear_since(cutoff)
    check("clear_since removes entries since cutoff", n == 1)
    check("older entries remain", len(nh.list_recent(10)) == 2)

# â”€â”€ New UI files importable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ UI Modules Importable ]")
try:
    from app.desktop.mini_widget import MiniWidget
    check("mini_widget.py imports cleanly", True)
except ImportError as e:
    check(f"mini_widget.py imports cleanly ({e})", False)

try:
    from app.desktop.mini_overlay import MiniOverlay
    check("mini_overlay.py imports cleanly", True)
except ImportError as e:
    check(f"mini_overlay.py imports cleanly ({e})", False)

try:
    from app.desktop.notification_history_window import NotificationHistoryWindow
    check("notification_history_window.py imports cleanly", True)
except ImportError as e:
    check(f"notification_history_window.py imports cleanly ({e})", False)

# â”€â”€ Settings keys present â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Settings Keys ]")
from app.core.settings import Settings

with tempfile.TemporaryDirectory() as tmp:
    s = Settings(Path(tmp) / "settings.json")
    # Set and read back all new appearance keys
    for key, val in [
        ("theme", "dark_hamster"),
        ("global_hotkey_enabled", True),
        ("global_hotkey", "Ctrl+Shift+H"),
        ("mini_widget_enabled", False),
        ("mini_overlay_enabled", False),
        ("mini_overlay_position", "top-right"),
        ("mini_overlay_auto_hide_seconds", 8),
    ]:
        s.set(key, val)
        check(f"settings key '{key}' round-trips", s.get(key) == val)

# â”€â”€ AppContext wires notification_history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ AppContext Integration ]")
ctx_tmp = tempfile.mkdtemp()
from app.core.app_context import AppContext
ctx = AppContext(Path(ctx_tmp))
ctx.start()
check("ctx.notification_history is set after start()", ctx.notification_history is not None)
check("ctx.reminder_scheduler is set after start()", ctx.reminder_scheduler is not None)
ctx.stop()

import shutil
shutil.rmtree(ctx_tmp, ignore_errors=True)

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
