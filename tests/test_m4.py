"""Milestone 4 smoke test â€” SQLite memory, store CRUD, command dispatcher."""
import sys
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


print("\n--- Hamster AI Milestone 4 Smoke Test ---\n")

# Use a temp DB so tests don't pollute the real one
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)

    from app.memory.db import Database
    from app.memory.store import MemoryStore

    db = Database(tmp_path / "test.db")
    store = MemoryStore(db)

    # â”€â”€ Schema / migrations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[ Database & Migrations ]")
    check("DB file created", (tmp_path / "test.db").exists())
    with db.conn() as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for tbl in ("memories", "todos", "notes", "future_features", "schema_version"):
        check(f"Table '{tbl}' exists", tbl in tables)

    # â”€â”€ Memories â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Memories ]")
    m1 = store.add_memory("I prefer dark mode")
    check("add_memory returns Memory", m1.id > 0 and m1.content == "I prefer dark mode")
    m2 = store.add_memory("Likes short answers", type="preference")

    all_mem = store.list_memories()
    check("list_memories returns both", len(all_mem) == 2)

    pref = store.list_memories(type="preference")
    check("list_memories filtered by type", len(pref) == 1 and pref[0].type == "preference")

    deleted = store.delete_memory(m1.id)
    check("delete_memory returns True", deleted)
    check("memory removed from list", len(store.list_memories()) == 1)

    check("delete non-existent returns False", not store.delete_memory(9999))

    # â”€â”€ Todos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Todos ]")
    t1 = store.add_todo("Buy batteries")
    t2 = store.add_todo("Call dentist", due_date="2026-05-01")
    check("add_todo returns Todo", t1.id > 0 and not t1.done)
    check("due_date stored", t2.due_date == "2026-05-01")

    open_todos = store.list_todos()
    check("list_todos (open) returns 2", len(open_todos) == 2)

    ok = store.complete_todo(t1.id)
    check("complete_todo returns True", ok)
    check("completed todo excluded from open list", len(store.list_todos()) == 1)
    check("completed todo included when include_done=True", len(store.list_todos(include_done=True)) == 2)

    # â”€â”€ Notes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Notes ]")
    n1 = store.add_note("Hotel checkout is 11am")
    n2 = store.add_note("Meeting at 3pm")
    check("add_note returns Note", n1.id > 0)
    check("list_notes returns 2", len(store.list_notes()) == 2)
    check("delete_note works", store.delete_note(n1.id))
    check("note removed", len(store.list_notes()) == 1)

    # â”€â”€ Future Features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Future Features ]")
    f1 = store.add_feature("Voice input", description="STT support", reason="No Whisper yet")
    check("add_feature returns FutureFeature", f1.id > 0 and f1.status == "suggested")
    check("feature title stored", f1.title == "Voice input")

    check("update_feature_status to planned", store.update_feature_status(f1.id, "planned"))
    feats = store.list_features()
    check("status updated in DB", feats[0].status == "planned")
    check("invalid status rejected", not store.update_feature_status(f1.id, "bogus_status"))
    check("delete_feature works", store.delete_feature(f1.id))
    check("feature removed", len(store.list_features()) == 0)

    # â”€â”€ Command Dispatcher â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Command Dispatcher ]")
    from app.core.commands import build_dispatcher
    from app.core.app_context import AppContext

    ctx = AppContext(ROOT)
    ctx.start()

    d = ctx.commands
    check("is_command('/todo buy milk')", d.is_command("/todo buy milk"))
    check("is_command('hello') is False", not d.is_command("hello"))

    resp = d.dispatch("/todo buy milk", ctx)
    check("/todo returns confirmation", "Added" in resp or "todo" in resp.lower())

    resp = d.dispatch("/show-todos", ctx)
    check("/show-todos returns todos", "buy milk" in resp)

    resp = d.dispatch("/remember I use Windows 11", ctx)
    check("/remember saves memory", "Saved" in resp or "memory" in resp.lower())

    resp = d.dispatch("/show-memories", ctx)
    check("/show-memories lists memories", "Windows 11" in resp)

    resp = d.dispatch("/note hotel checkout 11am", ctx)
    check("/note saves note", "saved" in resp.lower() or "note" in resp.lower())

    resp = d.dispatch("/show-notes", ctx)
    check("/show-notes lists notes", "hotel" in resp.lower())

    resp = d.dispatch("/add-feature Calendar integration", ctx)
    check("/add-feature works", "Calendar" in resp)

    resp = d.dispatch("/show-features", ctx)
    check("/show-features lists features", "Calendar" in resp)

    resp = d.dispatch("/unknown-cmd", ctx)
    check("unknown command returns helpful message", "Unknown" in resp or "unknown" in resp)

    resp = d.dispatch("/help", ctx)
    check("/help lists commands", "/todo" in resp and "/remember" in resp)

    resp = d.dispatch("/status", ctx)
    check("/status shows model info", "Model" in resp)

    ctx.stop()

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
