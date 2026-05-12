from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.db import Database


@dataclass
class Memory:
    id: int
    created_at: str
    content: str
    type: str
    tags: str = ""


@dataclass
class Todo:
    id: int
    created_at: str
    updated_at: str
    text: str
    done: bool
    due_date: str | None


@dataclass
class Note:
    id: int
    created_at: str
    text: str


@dataclass
class Session:
    id: int
    started_at: str
    ended_at: str | None
    session_type: str
    primary_app: str
    summary: str | None


@dataclass
class FutureFeature:
    id: int
    requested_at: str
    title: str
    description: str | None
    reason: str | None
    priority: str
    status: str


class MemoryStore:
    def __init__(self, db: "Database") -> None:
        self._db = db

    # ── Memories ──────────────────────────────────────────────────────────────

    def add_memory(self, content: str, type: str = "explicit", tags: str = "") -> Memory:
        with self._db.conn() as con:
            cur = con.execute(
                "INSERT INTO memories (content, type, tags) VALUES (?, ?, ?)",
                (content, type, tags),
            )
            row = con.execute("SELECT * FROM memories WHERE id = ?", (cur.lastrowid,)).fetchone()
            return _to_memory(row)

    def list_memories(self, type: str | None = None, tag: str | None = None) -> list[Memory]:
        with self._db.conn() as con:
            if tag:
                pattern = f"%{tag}%"
                rows = con.execute(
                    "SELECT * FROM memories WHERE tags LIKE ? ORDER BY created_at DESC",
                    (pattern,),
                ).fetchall()
            elif type:
                rows = con.execute(
                    "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC", (type,)
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC"
                ).fetchall()
            return [_to_memory(r) for r in rows]

    def tag_memory(self, memory_id: int, tags: str) -> bool:
        with self._db.conn() as con:
            cur = con.execute(
                "UPDATE memories SET tags = ? WHERE id = ?", (tags, memory_id)
            )
            return cur.rowcount > 0

    def search_memories(self, keyword: str) -> list[Memory]:
        from app.memory.search import search_memories as _search
        rows = _search(self._db, keyword)
        return [Memory(
            id=r["id"], created_at=r["created_at"],
            content=r["content"], type=r["type"], tags=r.get("tags", ""),
        ) for r in rows]

    def delete_memory(self, memory_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cur.rowcount > 0

    def delete_all_memories(self) -> int:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM memories")
            return cur.rowcount

    # ── Todos ─────────────────────────────────────────────────────────────────

    def add_todo(self, text: str, due_date: str | None = None) -> Todo:
        with self._db.conn() as con:
            cur = con.execute(
                "INSERT INTO todos (text, due_date) VALUES (?, ?)", (text, due_date)
            )
            row = con.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
            return _to_todo(row)

    def list_todos(self, include_done: bool = False) -> list[Todo]:
        with self._db.conn() as con:
            if include_done:
                rows = con.execute("SELECT * FROM todos ORDER BY created_at DESC").fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM todos WHERE done = 0 ORDER BY created_at DESC"
                ).fetchall()
            return [_to_todo(r) for r in rows]

    def complete_todo(self, todo_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute(
                "UPDATE todos SET done = 1, updated_at = datetime('now') WHERE id = ?",
                (todo_id,),
            )
            return cur.rowcount > 0

    def delete_todo(self, todo_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            return cur.rowcount > 0

    def clear_done_todos(self) -> int:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM todos WHERE done = 1")
            return cur.rowcount

    # ── Notes ─────────────────────────────────────────────────────────────────

    def add_note(self, text: str) -> Note:
        with self._db.conn() as con:
            cur = con.execute("INSERT INTO notes (text) VALUES (?)", (text,))
            row = con.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
            return _to_note(row)

    def list_notes(self) -> list[Note]:
        with self._db.conn() as con:
            rows = con.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
            return [_to_note(r) for r in rows]

    def delete_note(self, note_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0

    # ── Future Features ───────────────────────────────────────────────────────

    def add_feature(
        self,
        title: str,
        description: str = "",
        reason: str = "",
        priority: str = "normal",
    ) -> FutureFeature:
        with self._db.conn() as con:
            cur = con.execute(
                "INSERT INTO future_features (title, description, reason_currently_unavailable, priority)"
                " VALUES (?, ?, ?, ?)",
                (title, description, reason, priority),
            )
            row = con.execute(
                "SELECT * FROM future_features WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return _to_feature(row)

    def list_features(self) -> list[FutureFeature]:
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM future_features ORDER BY requested_at DESC"
            ).fetchall()
            return [_to_feature(r) for r in rows]

    def update_feature_status(self, feature_id: int, status: str) -> bool:
        valid = {"suggested", "planned", "in_progress", "done", "rejected"}
        if status not in valid:
            return False
        with self._db.conn() as con:
            cur = con.execute(
                "UPDATE future_features SET status = ? WHERE id = ?", (status, feature_id)
            )
            return cur.rowcount > 0

    def delete_feature(self, feature_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM future_features WHERE id = ?", (feature_id,))
            return cur.rowcount > 0

    # ── Sessions ──────────────────────────────────────────────────────────────

    def start_session(self, session_type: str, primary_app: str) -> "Session":
        with self._db.conn() as con:
            con.execute(
                "UPDATE sessions SET ended_at = datetime('now') WHERE ended_at IS NULL"
            )
            cur = con.execute(
                "INSERT INTO sessions (session_type, primary_app) VALUES (?, ?)",
                (session_type, primary_app),
            )
            row = con.execute(
                "SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return _to_session(row)

    def end_active_session(self, summary: str | None = None) -> bool:
        with self._db.conn() as con:
            cur = con.execute(
                "UPDATE sessions SET ended_at = datetime('now'), summary = ?"
                " WHERE ended_at IS NULL",
                (summary,),
            )
            return cur.rowcount > 0

    def get_active_session(self) -> "Session | None":
        with self._db.conn() as con:
            row = con.execute(
                "SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return _to_session(row) if row else None

    def recent_sessions(self, limit: int = 10) -> "list[Session]":
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [_to_session(r) for r in rows]

    def sessions_in_range(self, since_iso: str, until_iso: str | None = None) -> "list[Session]":
        with self._db.conn() as con:
            if until_iso:
                rows = con.execute(
                    "SELECT * FROM sessions WHERE started_at >= ? AND started_at < ?"
                    " ORDER BY id ASC",
                    (since_iso, until_iso),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM sessions WHERE started_at >= ? ORDER BY id ASC",
                    (since_iso,),
                ).fetchall()
            return [_to_session(r) for r in rows]

    def delete_sessions_since(self, since_iso: str) -> int:
        with self._db.conn() as con:
            cur = con.execute(
                "DELETE FROM sessions WHERE started_at >= ?", (since_iso,)
            )
            return cur.rowcount

    # ── Forget Mode helpers ───────────────────────────────────────────────────

    def delete_memories_since(self, since_iso: str) -> int:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM memories WHERE created_at >= ?", (since_iso,))
            return cur.rowcount

    def delete_notes_since(self, since_iso: str) -> int:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM notes WHERE created_at >= ?", (since_iso,))
            return cur.rowcount

    def delete_todos_since(self, since_iso: str) -> int:
        with self._db.conn() as con:
            cur = con.execute("DELETE FROM todos WHERE created_at >= ?", (since_iso,))
            return cur.rowcount

    def delete_plugin_data_table(self, table: str) -> None:
        safe = table.replace('"', "")
        with self._db.conn() as con:
            con.execute(f'DELETE FROM "{safe}"')


# ── Row mappers ───────────────────────────────────────────────────────────────

def _to_memory(r) -> Memory:
    return Memory(
        id=r["id"], created_at=r["created_at"],
        content=r["content"], type=r["type"],
        tags=r["tags"] if "tags" in r.keys() else "",
    )


def _to_todo(r) -> Todo:
    return Todo(
        id=r["id"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        text=r["text"],
        done=bool(r["done"]),
        due_date=r["due_date"],
    )


def _to_note(r) -> Note:
    return Note(id=r["id"], created_at=r["created_at"], text=r["text"])


def _to_session(r) -> Session:
    return Session(
        id=r["id"],
        started_at=r["started_at"],
        ended_at=r["ended_at"],
        session_type=r["session_type"],
        primary_app=r["primary_app"],
        summary=r["summary"],
    )


def _to_feature(r) -> FutureFeature:
    return FutureFeature(
        id=r["id"],
        requested_at=r["requested_at"],
        title=r["title"],
        description=r["description"],
        reason=r["reason_currently_unavailable"],
        priority=r["priority"],
        status=r["status"],
    )
