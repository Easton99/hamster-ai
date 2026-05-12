"""Milestone 1 smoke test â€” no external deps, no interactive input."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.app_context import AppContext
from app.core.event_bus import APP_STARTED, APP_EXITING, USER_MESSAGE

PASS = "[PASS]"
FAIL = "[FAIL]"
results: list[tuple[str, str]] = []


def check(label: str, condition: bool) -> None:
    tag = PASS if condition else FAIL
    results.append((tag, label))
    print(f"  {tag} {label}")


# â”€â”€ Boot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n--- Hamster AI Milestone 1 Smoke Test ---\n")

ctx = AppContext(ROOT)

# Settings
check("Settings loads with defaults", ctx.settings.get("model") == "llama3.2:3b")
check("Settings get/set round-trip", (ctx.settings.set("_test", 42) or True) and ctx.settings.get("_test") == 42)
check("settings.json written to disk", (ROOT / "data" / "config" / "settings.json").exists())

# Logging
import logging
logger = logging.getLogger("hamster_ai")
check("Logger initialised", logger is not None)
check("Log file created", (ROOT / "data" / "logs" / "hamster_ai.log").exists())

# Event bus
events_seen: list[str] = []
ctx.event_bus.subscribe(APP_STARTED, lambda e, d: events_seen.append(e))
ctx.event_bus.subscribe(USER_MESSAGE, lambda e, d: events_seen.append(f"{e}:{d['text']}"))

# Start (fires APP_STARTED)
ctx.start()
check("APP_STARTED fired", APP_STARTED in events_seen)
check("Plugin manager created", ctx.plugin_manager is not None)
check("Plugin manager list_plugins() callable", isinstance(ctx.plugin_manager.list_plugins(), list))

# Event emission
ctx.event_bus.emit(USER_MESSAGE, {"text": "hello"})
check("USER_MESSAGE received by subscriber", f"{USER_MESSAGE}:hello" in events_seen)

# Bad handler isolation
ctx.event_bus.subscribe("test_event", lambda e, d: 1 / 0)
try:
    ctx.event_bus.emit("test_event")
    check("Crashing handler does not propagate", True)
except ZeroDivisionError:
    check("Crashing handler does not propagate", False)

# Graceful shutdown
exit_events: list[str] = []
ctx.event_bus.subscribe(APP_EXITING, lambda e, d: exit_events.append(e))
ctx.stop()
check("APP_EXITING fired on stop", APP_EXITING in exit_events)

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
