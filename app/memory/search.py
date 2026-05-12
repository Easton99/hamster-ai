from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.db import Database


def search_memories(db: "Database", keyword: str) -> list[dict]:
    pattern = f"%{keyword}%"
    with db.conn() as con:
        rows = con.execute(
            "SELECT id, created_at, content, type, tags FROM memories"
            " WHERE content LIKE ? OR tags LIKE ?"
            " ORDER BY created_at DESC LIMIT 50",
            (pattern, pattern),
        ).fetchall()
    return [dict(r) for r in rows]


def search_notes(db: "Database", keyword: str) -> list[dict]:
    pattern = f"%{keyword}%"
    with db.conn() as con:
        rows = con.execute(
            "SELECT id, created_at, text, tags FROM notes"
            " WHERE text LIKE ? OR tags LIKE ?"
            " ORDER BY created_at DESC LIMIT 50",
            (pattern, pattern),
        ).fetchall()
    return [dict(r) for r in rows]


def search_todos(db: "Database", keyword: str) -> list[dict]:
    pattern = f"%{keyword}%"
    with db.conn() as con:
        rows = con.execute(
            "SELECT id, created_at, text, done, tags FROM todos"
            " WHERE text LIKE ? OR tags LIKE ?"
            " ORDER BY created_at DESC LIMIT 50",
            (pattern, pattern),
        ).fetchall()
    return [dict(r) for r in rows]
