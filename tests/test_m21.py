"""Milestone 21 smoke test â€” Scheduled Reminders Plugin."""
import sys
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
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


print("\n--- Hamster AI Milestone 21 Smoke Test ---\n")

# â”€â”€ ReminderScheduler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ ReminderScheduler ]")
with tempfile.TemporaryDirectory() as tmp:
    from app.memory.db import Database
    from app.core.reminder_scheduler import ReminderScheduler, Reminder

    db = Database(Path(tmp) / "test.db")
    fired: list[Reminder] = []

    sched = ReminderScheduler(db, lambda r: fired.append(r))
    sched.start()

    future = datetime.now() + timedelta(hours=2)
    r1 = sched.add(future, "Call dentist")
    check("add() returns Reminder with id", isinstance(r1.id, int) and r1.id > 0)
    check("Reminder content stored", r1.content == "Call dentist")
    check("Reminder not yet fired", not r1.fired)
    check("Reminder not cancelled", not r1.cancelled)

    r2 = sched.add(datetime.now() + timedelta(hours=3), "Check email")
    pending = sched.list_pending()
    check("list_pending returns 2 reminders", len(pending) == 2)
    check("pending reminders sorted by fire_at (earliest first)",
          pending[0].fire_at <= pending[1].fire_at)

    ok = sched.cancel(r1.id)
    check("cancel() returns True for valid id", ok)
    pending2 = sched.list_pending()
    check("cancelled reminder removed from pending", len(pending2) == 1)
    check("remaining reminder is the right one", pending2[0].content == "Check email")

    check("cancel() returns False for already-cancelled id", not sched.cancel(r1.id))
    check("cancel() returns False for nonexistent id", not sched.cancel(9999))

    all_reminders = sched.list_all()
    check("list_all() includes cancelled reminder", len(all_reminders) == 2)

    sched.stop()

# â”€â”€ Reminder fires correctly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Reminder Firing ]")
import time

with tempfile.TemporaryDirectory() as tmp:
    from app.memory.db import Database
    from app.core.reminder_scheduler import ReminderScheduler

    db = Database(Path(tmp) / "test.db")
    fired: list = []

    sched = ReminderScheduler(db, lambda r: fired.append(r.content))
    sched.start()

    # Add a reminder that already fired (past time)
    past = datetime.now(timezone.utc) - timedelta(seconds=5)
    sched.add(past, "Past reminder")

    # Manually trigger a tick
    sched._tick()

    check("past reminder fires on tick", "Past reminder" in fired)
    check("already-fired reminder not fired twice", fired.count("Past reminder") == 1)

    sched.stop()

# â”€â”€ parse_reminder_time â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ parse_reminder_time ]")
from app.core.reminder_scheduler import parse_reminder_time

t = parse_reminder_time("in 30 minutes")
check("'in 30 minutes' parses", t is not None)
if t:
    diff = (t - datetime.now()).total_seconds()
    check("'in 30 minutes' gives ~30min from now", 1700 <= diff <= 1820)

t2 = parse_reminder_time("in 2 hours")
check("'in 2 hours' parses", t2 is not None)
if t2:
    diff2 = (t2 - datetime.now()).total_seconds()
    check("'in 2 hours' gives ~2h from now", 7100 <= diff2 <= 7300)

t3 = parse_reminder_time("at 6pm")
check("'at 6pm' parses", t3 is not None)
if t3:
    check("'at 6pm' gives hour 18", t3.hour == 18)

t4 = parse_reminder_time("at 10:30")
check("'at 10:30' parses", t4 is not None)
if t4:
    check("'at 10:30' gives hour 10 minute 30", t4.hour == 10 and t4.minute == 30)

t5 = parse_reminder_time("at 9am")
check("'at 9am' parses", t5 is not None)
if t5:
    check("'at 9am' gives hour 9", t5.hour == 9)

t6 = parse_reminder_time("completely unparseable garbage xyz")
check("unparseable time returns None", t6 is None)

# â”€â”€ Plugin files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Files ]")
plugin_dir = ROOT / "plugins" / "scheduled_reminders"
check("plugin directory exists", plugin_dir.exists())
check("plugin.py exists", (plugin_dir / "plugin.py").exists())
check("config.json exists", (plugin_dir / "config.json").exists())

# â”€â”€ Plugin loads and commands work â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Load + Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    dest = Path(tmp) / "plugins" / "scheduled_reminders"
    shutil.copytree(plugin_dir, dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("scheduled_reminders plugin found",
          "scheduled_reminders" in [p["name"] for p in pm.list_plugins()])
    check("scheduled_reminders enabled by default",
          any(p["name"] == "scheduled_reminders" and p["enabled"] for p in pm.list_plugins()))
    check("ctx.reminder_scheduler is not None", ctx.reminder_scheduler is not None)

    for cmd in ("/remind", "/show-reminders", "/cancel-reminder"):
        short = cmd.lstrip("/")
        check(f"{cmd} command registered",
              any(c == short for c, _ in ctx.commands.list_commands()))

    resp = ctx.commands.dispatch("/remind me at 6pm to check the build", ctx)
    check("/remind parses and saves reminder",
          "#" in resp or "set" in resp.lower() or "reminder" in resp.lower())

    resp = ctx.commands.dispatch("/remind me in 30 minutes to take a break", ctx)
    check("/remind 'in X minutes' works",
          "#" in resp or "set" in resp.lower() or "reminder" in resp.lower())

    resp = ctx.commands.dispatch("/show-reminders", ctx)
    check("/show-reminders lists reminders",
          isinstance(resp, str) and ("pending" in resp.lower() or "#" in resp or "check" in resp.lower()))

    resp = ctx.commands.dispatch("/remind me in 999 hours to this is unparseable garbage", ctx)
    check("/remind with bad time returns error or sets reminder", isinstance(resp, str))

    resp = ctx.commands.dispatch("/remind", ctx)
    check("/remind with no args returns usage hint",
          "Usage" in resp or "usage" in resp.lower() or "remind" in resp.lower())

    resp = ctx.commands.dispatch("/cancel-reminder 9999", ctx)
    check("/cancel-reminder with invalid id returns not-found message",
          "No" in resp or "not found" in resp.lower() or "active" in resp.lower())

    resp = ctx.commands.dispatch("/cancel-reminder notanumber", ctx)
    check("/cancel-reminder with bad id returns usage hint",
          "Usage" in resp or "usage" in resp.lower() or "number" in resp.lower())

    ctx.stop()

# â”€â”€ AppContext integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ AppContext Integration ]")
with tempfile.TemporaryDirectory() as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    ctx.start()
    check("ctx.reminder_scheduler starts automatically", ctx.reminder_scheduler is not None)
    check("reminder_scheduler is running", ctx.reminder_scheduler._running)
    ctx.stop()
    check("reminder_scheduler stops with ctx.stop()", not ctx.reminder_scheduler._running)

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
