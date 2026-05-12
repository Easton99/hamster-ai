"""Milestone 11 smoke test â€” Insights Plugin."""
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
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


print("\n--- Hamster AI Milestone 11 Smoke Test ---")

# â”€â”€ store.sessions_in_range â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ sessions_in_range ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext

    ctx = AppContext(Path(tmp))
    ctx.start()
    store = ctx.store

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    store.start_session("coding",   "code.exe")
    store.start_session("browsing", "chrome.exe")

    all_today = store.sessions_in_range(today)
    check("sessions_in_range(today) returns sessions", len(all_today) >= 2)

    bounded = store.sessions_in_range(today, tomorrow)
    check("sessions_in_range with upper bound works", len(bounded) >= 2)

    none_yesterday = store.sessions_in_range(yesterday, today)
    check("sessions before today excluded by upper bound", len(none_yesterday) == 0)

    ctx.stop()

# â”€â”€ Analysis helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Analysis Helpers ]")
import importlib.util

insights_src = ROOT / "plugins" / "insights"
check("insights plugin folder exists", insights_src.exists())
check("insights plugin.py exists", (insights_src / "plugin.py").exists())

spec = importlib.util.spec_from_file_location("insights_plugin", insights_src / "plugin.py")
ins_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ins_mod)

_analyse     = ins_mod._analyse
_fmt_minutes = ins_mod._fmt_minutes
_peak_hours  = ins_mod._peak_hours


class _FakeSession:
    def __init__(self, stype, started_at, ended_at=None, primary_app="app.exe"):
        self.session_type = stype
        self.started_at   = started_at
        self.ended_at     = ended_at
        self.primary_app  = primary_app


check("_fmt_minutes(0) = '0m'",    _fmt_minutes(0)  == "0m")
check("_fmt_minutes(45) = '45m'",  _fmt_minutes(45) == "45m")
check("_fmt_minutes(60) = '1h'",   _fmt_minutes(60) == "1h")
check("_fmt_minutes(90) = '1h 30m'", _fmt_minutes(90) == "1h 30m")

sessions = [
    _FakeSession("coding",   "2026-05-01 10:00:00", "2026-05-01 10:30:00"),
    _FakeSession("browsing", "2026-05-01 11:00:00", "2026-05-01 11:15:00"),
    _FakeSession("idle",     "2026-05-01 12:00:00", "2026-05-01 12:05:00"),
]
a = _analyse(sessions)
check("total = 50 min", a["total"] == 50)
check("coding = 30 min", a["by_type"].get("coding") == 30)
check("browsing = 15 min", a["by_type"].get("browsing") == 15)
check("by_hour has hour 10", 10 in a["by_hour"])
check("avg_len is 16 or 17 min", a["avg_len"] in (16, 17))

check("_peak_hours returns string", isinstance(_peak_hours({10: 30, 11: 15}), str))

# â”€â”€ Plugin loads and commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"

    shutil.copytree(ROOT / "plugins" / "insights",          plugins_dir / "insights")
    shutil.copytree(ROOT / "plugins" / "session_awareness", plugins_dir / "session_awareness")

    ctx.start()
    pm = ctx.plugin_manager

    check("insights loaded",           "insights" in [p["name"] for p in pm.list_plugins()])
    check("insights enabled by default",
          any(p["name"] == "insights" and p["enabled"] for p in pm.list_plugins()))

    # Seed sessions so commands have real data
    today = date.today().isoformat()
    ctx.store.start_session("coding",   "code.exe")
    ctx.store.start_session("browsing", "vivaldi.exe")

    result = ctx.commands.dispatch("/summary", ctx)
    check("/summary returns data",   "activity" in result.lower() or "total" in result.lower() or "today" in result.lower())

    result2 = ctx.commands.dispatch("/week", ctx)
    check("/week returns data",      any(w in result2.lower() for w in ["day", "week", "total", "past"]))

    result3 = ctx.commands.dispatch("/patterns", ctx)
    check("/patterns returns string", len(result3) > 0)

    result4 = ctx.commands.dispatch("/energy", ctx)
    check("/energy returns data",    any(w in result4.lower() for w in ["active", "energy", "session", "no activity"]))

    ctx.stop()

# â”€â”€ NOTIFY event wired â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ NOTIFY event ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    ctx.start()

    received = []
    ctx.event_bus.subscribe("notify", lambda e, d: received.append(d))
    ctx.event_bus.emit("notify", {"title": "Test", "body": "hello"})
    check("NOTIFY event fires and is received", len(received) == 1)
    check("NOTIFY data has title and body", received[0].get("title") == "Test")

    ctx.stop()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
