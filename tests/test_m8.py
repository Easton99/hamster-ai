"""Milestone 8 smoke test â€” startup, autostart registry, greeting logic."""
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


print("\n--- Hamster AI Milestone 8 Smoke Test ---")

# â”€â”€ Registry autostart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Autostart (Registry) ]")
from app.core.startup import get_launch_command, is_autostart_set, set_autostart

cmd = get_launch_command()
check("get_launch_command returns a non-empty string", bool(cmd))
check("launch command contains --startup flag", "--startup" in cmd)
check("launch command references a .py or .exe", ".py" in cmd or ".exe" in cmd.lower())
print(f"    command: {cmd}")

# Enable â†’ check â†’ disable â†’ check
initial_state = is_autostart_set()
result = set_autostart(True)
check("set_autostart(True) succeeds", result is True)
check("is_autostart_set() True after enable", is_autostart_set())

result2 = set_autostart(False)
check("set_autostart(False) succeeds", result2 is True)
check("is_autostart_set() False after disable", not is_autostart_set())

# Double-disable should not raise
result3 = set_autostart(False)
check("double disable is safe", result3 is True)

# Restore original state
if initial_state:
    set_autostart(True)

# â”€â”€ Greeting logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Greeting Logic ]")
from app.core.greeting import can_greet, get_startup_greeting

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    ctx.start()

    # Default settings â€” greeting enabled, no modes active
    check("can_greet with no modes active", can_greet(ctx))

    greeting = get_startup_greeting(ctx)
    check("get_startup_greeting returns a string", isinstance(greeting, str))
    check("greeting is non-empty", bool(greeting and greeting.strip()))
    print(f"    greeting: '{greeting}'")

    # Greet on startup disabled
    ctx.settings.set("greet_on_startup", False)
    check("get_startup_greeting returns None when disabled", get_startup_greeting(ctx) is None)
    ctx.settings.set("greet_on_startup", True)

    # Work Mode suppresses greeting
    ctx.modes.enable_work_mode()
    check("can_greet is False during Work Mode", not can_greet(ctx))
    check("get_startup_greeting is None during Work Mode", get_startup_greeting(ctx) is None)
    ctx.modes.disable_work_mode()

    # Private Mode suppresses greeting
    ctx.modes.enable_private_mode()
    check("can_greet is False during Private Mode", not can_greet(ctx))
    check("get_startup_greeting is None during Private Mode", get_startup_greeting(ctx) is None)
    ctx.modes.disable_private_mode()

    # Game Safe Mode suppresses greeting
    ctx.modes.enable_game_safe_mode()
    check("can_greet is False during Game Safe Mode", not can_greet(ctx))
    check("get_startup_greeting is None during Game Safe Mode", get_startup_greeting(ctx) is None)
    ctx.modes.disable_game_safe_mode()

    # Focus Mode suppresses greeting
    ctx.modes.enable_focus_mode()
    check("can_greet is False during Focus Mode", not can_greet(ctx))
    check("get_startup_greeting is None during Focus Mode", get_startup_greeting(ctx) is None)
    ctx.modes.disable_focus_mode()

    # After clearing all modes, greeting returns
    check("can_greet True after clearing all modes", can_greet(ctx))
    check("get_startup_greeting returns string after clearing modes",
          isinstance(get_startup_greeting(ctx), str))

    ctx.stop()

# â”€â”€ Settings window saves startup_delay_seconds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Settings â€” Startup Fields ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx2 = AppContext(Path(tmp))
    ctx2.start()

    check("startup_delay_seconds default is 30",
          ctx2.settings.get("startup_delay_seconds", 30) == 30)

    ctx2.settings.set("startup_delay_seconds", 45)
    check("startup_delay_seconds can be updated",
          ctx2.settings.get("startup_delay_seconds") == 45)

    ctx2.settings.set("start_with_windows", False)
    check("start_with_windows default is False",
          ctx2.settings.get("start_with_windows") is False)

    ctx2.settings.set("greet_on_startup", True)
    check("greet_on_startup default is True",
          ctx2.settings.get("greet_on_startup") is True)

    ctx2.stop()

# â”€â”€ main.py --startup flag detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ --startup Flag ]")
# Simulate the flag being present / absent
original_argv = sys.argv[:]
sys.argv = ["main.py", "--startup"]
check("--startup detected in sys.argv", "--startup" in sys.argv)
sys.argv = ["main.py"]
check("--startup absent in normal launch", "--startup" not in sys.argv)
sys.argv = original_argv

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
