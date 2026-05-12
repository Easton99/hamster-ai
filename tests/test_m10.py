"""Milestone 10 smoke test â€” Session Awareness Plugin."""
import sys
import tempfile
import time
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


print("\n--- Hamster AI Milestone 10 Smoke Test ---")

# â”€â”€ DB migration â€” sessions table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ DB Migration ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext

    ctx = AppContext(Path(tmp))
    ctx.start()

    with ctx.db.conn() as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check("sessions table created by migration", "sessions" in tables)

    with ctx.db.conn() as con:
        row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
    check("schema_version records v1", row[0] == 1)

    ctx.stop()

# â”€â”€ Session CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Session Store CRUD ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    ctx.start()
    store = ctx.store

    check("no active session initially", store.get_active_session() is None)

    s1 = store.start_session("coding", "code.exe")
    check("start_session returns session", s1 is not None)
    check("session type correct", s1.session_type == "coding")
    check("session primary_app correct", s1.primary_app == "code.exe")
    check("session ended_at is None", s1.ended_at is None)

    active = store.get_active_session()
    check("get_active_session returns session", active is not None)
    check("active session matches started", active.id == s1.id)

    # Starting new session auto-ends the previous one
    s2 = store.start_session("gaming", "valorant.exe")
    check("new session started", s2.session_type == "gaming")

    active2 = store.get_active_session()
    check("active session updated to new", active2 is not None and active2.id == s2.id)

    recent = store.recent_sessions(limit=5)
    check("recent_sessions has 2 entries", len(recent) == 2)
    check("most recent is gaming", recent[0].session_type == "gaming")
    check("older one is coding", recent[1].session_type == "coding")
    check("older session has ended_at", recent[1].ended_at is not None)

    check("end_active_session returns True", store.end_active_session(summary="done"))
    check("no active session after end", store.get_active_session() is None)

    ctx.stop()

# â”€â”€ delete_sessions_since â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ delete_sessions_since ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    ctx.start()
    store = ctx.store

    store.start_session("browsing", "chrome.exe")
    store.start_session("coding", "code.exe")

    before = store.recent_sessions()
    check("2 sessions before delete", len(before) == 2)

    n = store.delete_sessions_since("1970-01-01 00:00:00")
    check("delete_sessions_since removes all", n == 2)
    check("no sessions after delete", len(store.recent_sessions()) == 0)

    ctx.stop()

# â”€â”€ Session classifier â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Session Classifier ]")
import shutil

sa_src = ROOT / "plugins" / "session_awareness"
check("session_awareness plugin folder exists", sa_src.exists())
check("session_awareness plugin.py exists", (sa_src / "plugin.py").exists())

# Import the classifier directly
import importlib.util

spec = importlib.util.spec_from_file_location("sa_plugin", sa_src / "plugin.py")
sa_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa_mod)
_classify = sa_mod._classify

check("idle classified as idle", _classify("", "", 600, False) == "idle")
check("code.exe -> coding", _classify("code.exe", "index.py - VS Code", 0, False) == "coding")
check("chrome.exe -> browsing", _classify("chrome.exe", "Google", 0, False) == "browsing")
check("valorant.exe -> gaming", _classify("valorant.exe", "", 0, False) == "gaming")
check("vlc.exe -> media", _classify("vlc.exe", "movie.mp4", 0, False) == "media")
check("dbeaver.exe -> database", _classify("dbeaver.exe", "DBeaver", 0, False) == "database")
check("unknown process -> unknown", _classify("randomapp.exe", "Random", 0, False) == "unknown")
check("youtube title -> media", _classify("chrome.exe", "youtube - chrome", 0, True) == "media")

# â”€â”€ Plugin loads and /session / /sessions commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    dest = plugins_dir / "session_awareness"
    shutil.copytree(sa_src, dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("session_awareness loaded", "session_awareness" in [p["name"] for p in pm.list_plugins()])
    check("session_awareness enabled by default",
          any(p["name"] == "session_awareness" and p["enabled"] for p in pm.list_plugins()))

    # Seed a session so commands have something to show
    ctx.store.start_session("coding", "code.exe")

    result = ctx.commands.dispatch("/session", ctx)
    check("/session returns session info", "coding" in result.lower() or "session" in result.lower())

    result2 = ctx.commands.dispatch("/sessions", ctx)
    check("/sessions returns list", "session" in result2.lower() or "coding" in result2.lower())

    ctx.stop()

# â”€â”€ forget commands include sessions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Forget Commands Include Sessions ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    ctx.start()
    ctx.store.start_session("browsing", "firefox.exe")

    result = ctx.commands.dispatch("/forget-today", ctx)
    check("/forget-today mentions sessions", "session" in result.lower())

    ctx.stop()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
