"""Milestone 15 smoke test â€” Memory Search + Tagging."""
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


print("\n--- Hamster AI Milestone 15 Smoke Test ---\n")

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)

    from app.memory.db import Database
    from app.memory.store import MemoryStore

    db = Database(tmp_path / "test.db")
    store = MemoryStore(db)

    # â”€â”€ Schema: tags columns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[ Schema â€” tags columns ]")
    with db.conn() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(memories)").fetchall()}
    check("memories table has tags column", "tags" in cols)

    with db.conn() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(todos)").fetchall()}
    check("todos table has tags column", "tags" in cols)

    with db.conn() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(notes)").fetchall()}
    check("notes table has tags column", "tags" in cols)

    # â”€â”€ Schema: notification_history + reminders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    with db.conn() as con:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    check("notification_history table exists", "notification_history" in tables)
    check("reminders table exists", "reminders" in tables)

    # â”€â”€ Memory tags â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Memory Tags ]")
    m1 = store.add_memory("I prefer dark mode", tags="preferences")
    check("add_memory with tags stores tags", m1.tags == "preferences")

    m2 = store.add_memory("Use venvs for Python", tags="dev")
    m3 = store.add_memory("Call dentist next week")

    all_mem = store.list_memories()
    check("list_memories returns all 3", len(all_mem) == 3)

    pref = store.list_memories(tag="preferences")
    check("list_memories(tag=) filters correctly", len(pref) == 1 and pref[0].content == "I prefer dark mode")

    dev = store.list_memories(tag="dev")
    check("list_memories filters by different tag", len(dev) == 1)

    no_tag = store.list_memories(tag="nonexistent")
    check("list_memories with unknown tag returns empty", len(no_tag) == 0)

    # tag_memory
    ok = store.tag_memory(m3.id, "personal")
    check("tag_memory returns True", ok)
    updated = store.list_memories(tag="personal")
    check("tagged memory appears in filtered list", len(updated) == 1)

    check("tag_memory on nonexistent id returns False", not store.tag_memory(9999, "foo"))

    # â”€â”€ Memory search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Memory Search ]")
    results = store.search_memories("dark")
    check("search_memories finds by content", len(results) >= 1)
    check("search result has correct content", any("dark" in m.content for m in results))

    results2 = store.search_memories("venv")
    check("search_memories finds 'venv'", len(results2) >= 1)

    results3 = store.search_memories("zzznomatch")
    check("search_memories returns empty for no match", len(results3) == 0)

    # search by tag
    results4 = store.search_memories("preferences")
    check("search_memories can find by tag", len(results4) >= 1)

    # â”€â”€ search_notes / search_todos functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ search_notes / search_todos ]")
    from app.memory.search import search_notes, search_todos

    store.add_note("Hotel checkout at 11am")
    store.add_note("Python refactor notes")
    store.add_todo("Buy batteries")
    store.add_todo("Check Python version")

    notes = search_notes(db, "Python")
    check("search_notes finds by keyword", len(notes) >= 1)
    check("search_notes returns dicts", isinstance(notes[0], dict))

    todos = search_todos(db, "batteries")
    check("search_todos finds by keyword", len(todos) >= 1)

    empty = search_notes(db, "zzznomatch")
    check("search_notes returns empty for no match", len(empty) == 0)

    # â”€â”€ Commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Commands ]")
    from app.core.app_context import AppContext

    ctx = AppContext(ROOT)
    ctx.start()

    # /remember with tag
    resp = ctx.commands.dispatch("/remember I use Windows 11", ctx)
    check("/remember works", "memory" in resp.lower() or "#" in resp)

    # /search-memory
    resp = ctx.commands.dispatch("/search-memory Windows", ctx)
    check("/search-memory finds saved memory", "Windows" in resp)

    resp = ctx.commands.dispatch("/search-memory", ctx)
    check("/search-memory with no args returns usage", "Usage" in resp or "usage" in resp.lower())

    resp = ctx.commands.dispatch("/search-memory zzznomatch", ctx)
    check("/search-memory returns 'no results' message", "No" in resp or "no" in resp.lower())

    # /tag-memory
    mems = ctx.store.list_memories()
    if mems:
        resp = ctx.commands.dispatch(f"/tag-memory {mems[0].id} work", ctx)
        check("/tag-memory works", "tagged" in resp.lower() or "work" in resp.lower())

    resp = ctx.commands.dispatch("/tag-memory notanumber foo", ctx)
    check("/tag-memory with bad id returns usage hint", "Usage" in resp or "usage" in resp.lower())

    # /show-memories with tag filter
    resp = ctx.commands.dispatch("/show-memories", ctx)
    check("/show-memories lists all memories", isinstance(resp, str) and len(resp) > 0)

    # /search-notes
    resp = ctx.commands.dispatch("/search-notes hotel", ctx)
    check("/search-notes command registered", isinstance(resp, str))

    # /search-todos
    resp = ctx.commands.dispatch("/search-todos batteries", ctx)
    check("/search-todos command registered", isinstance(resp, str))

    ctx.stop()

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
