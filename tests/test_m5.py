"""Milestone 5 smoke test â€” modes, process monitor, forget commands."""
import sys
import time
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"
results: list[tuple[str, str]] = []


def check(label: str, condition: bool) -> None:
    tag = PASS if condition else FAIL
    results.append((tag, label))
    print(f"  {tag} {label}")


print("\n--- Hamster AI Milestone 5 Smoke Test ---\n")

from app.core.app_context import AppContext

ctx = AppContext(ROOT)
ctx.start()

# â”€â”€ ModeManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ ModeManager ]")
modes = ctx.modes
check("ModeManager created", modes is not None)
check("No modes active initially", modes.active_modes() == [])
check("is_fully_paused() is False", not modes.is_fully_paused())

# Work Mode
modes.enable_work_mode()
check("Work Mode enabled", modes.work_mode)
check("is_fully_paused() True in Work Mode", modes.is_fully_paused())
check("active_modes() contains 'Work'", "Work" in modes.active_modes())
modes.enable_work_mode()  # idempotent
check("enable_work_mode is idempotent", modes.work_mode)
modes.disable_work_mode()
check("Work Mode disabled", not modes.work_mode)
check("is_fully_paused() False after disable", not modes.is_fully_paused())

# Private Mode
modes.enable_private_mode()
check("Private Mode enabled", modes.private_mode)
check("is_fully_paused() True in Private Mode", modes.is_fully_paused())
modes.disable_private_mode()
check("Private Mode disabled", not modes.private_mode)

# Game Safe Mode
modes.enable_game_safe_mode()
check("Game Safe Mode enabled", modes.game_safe_mode)
modes.disable_game_safe_mode()
check("Game Safe Mode disabled", not modes.game_safe_mode)

# Focus Mode with timer
print("\n[ Focus Mode Timer ]")
events_seen: list[str] = []
from app.core.event_bus import FOCUS_MODE_ENABLED, FOCUS_MODE_DISABLED
ctx.event_bus.subscribe(FOCUS_MODE_ENABLED, lambda e, d: events_seen.append("enabled"))
ctx.event_bus.subscribe(FOCUS_MODE_DISABLED, lambda e, d: events_seen.append("disabled"))

modes.enable_focus_mode(minutes=0.02)  # 1.2 seconds
check("Focus Mode active after enable", modes.focus_mode)
check("FOCUS_MODE_ENABLED event fired", "enabled" in events_seen)
time.sleep(2.0)
check("Focus Mode expired automatically", not modes.focus_mode)
check("FOCUS_MODE_DISABLED event fired on expiry", "disabled" in events_seen)

# Focus Mode manual disable
modes.enable_focus_mode(minutes=None)
check("Focus Mode with no timer", modes.focus_mode)
modes.disable_focus_mode()
check("Manual disable works", not modes.focus_mode)

# Multiple modes
modes.enable_work_mode()
modes.enable_focus_mode(minutes=None)
check("Multiple modes tracked", len(modes.active_modes()) == 2)
modes.disable_work_mode()
modes.disable_focus_mode()
check("All modes cleared", modes.active_modes() == [])

# â”€â”€ Event bus integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Mode Events on Event Bus ]")
from app.core.event_bus import WORK_MODE_ENABLED, WORK_MODE_DISABLED
work_events: list[str] = []
ctx.event_bus.subscribe(WORK_MODE_ENABLED, lambda e, d: work_events.append("on"))
ctx.event_bus.subscribe(WORK_MODE_DISABLED, lambda e, d: work_events.append("off"))
modes.enable_work_mode()
modes.disable_work_mode()
check("Work mode events fired in order", work_events == ["on", "off"])

# â”€â”€ Forget Mode commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Forget Mode Commands ]")
d = ctx.commands

ctx.store.add_memory("test memory")
ctx.store.add_note("test note")
ctx.store.add_todo("test todo")

resp = d.dispatch("/forget-today", ctx)
check("/forget-today runs without error", "Cleared" in resp)
check("/forget-today clears today's data",
      len(ctx.store.list_memories()) == 0 and len(ctx.store.list_notes()) == 0)

resp = d.dispatch("/forget-last-hour", ctx)
check("/forget-last-hour runs without error", "Cleared" in resp)

resp = d.dispatch("/forget-session", ctx)
check("/forget-session returns confirmation", "cleared" in resp.lower() or "session" in resp.lower())

resp = d.dispatch("/clear-activity", ctx)
check("/clear-activity returns confirmation", "cleared" in resp.lower() or "activity" in resp.lower())

# â”€â”€ Mode commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Mode Commands ]")

resp = d.dispatch("/focus 25", ctx)
check("/focus 25 enables Focus Mode", modes.focus_mode)
check("/focus response mentions duration", "25" in resp or "Focus" in resp)
modes.disable_focus_mode()

resp = d.dispatch("/focus 1h", ctx)
check("/focus 1h enables Focus Mode", modes.focus_mode)
modes.disable_focus_mode()

resp = d.dispatch("/quiet", ctx)
check("/quiet enables Focus Mode", modes.focus_mode)

resp = d.dispatch("/resume", ctx)
check("/resume disables Focus Mode", not modes.focus_mode)

resp = d.dispatch("/resume", ctx)
check("/resume when not active gives feedback", "not active" in resp.lower() or "Focus" in resp)

resp = d.dispatch("/private", ctx)
check("/private enables Private Mode", modes.private_mode)

resp = d.dispatch("/private-off", ctx)
check("/private-off disables Private Mode", not modes.private_mode)

# /status shows modes
modes.enable_focus_mode(minutes=None)
resp = d.dispatch("/status", ctx)
check("/status includes mode info", "Focus" in resp or "Modes" in resp)
modes.disable_focus_mode()

# â”€â”€ Process Monitor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Process Monitor ]")
check("ProcessMonitor created", ctx.process_monitor is not None)
try:
    import psutil
    check("psutil available", True)
except ImportError:
    check("psutil available", False)

ctx.stop()

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
