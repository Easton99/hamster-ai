from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.db import Database


@dataclass
class NotificationEntry:
    id: int
    timestamp: str
    type: str
    content: str
    dismissed: bool


class NotificationHistory:
    def __init__(self, db: "Database") -> None:
        self._db = db

    def add(self, type: str, content: str) -> None:
        with self._db.conn() as con:
            con.execute(
                "INSERT INTO notification_history (type, content) VALUES (?, ?)",
                (type, content),
            )

    def list_recent(self, limit: int = 50) -> list[NotificationEntry]:
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM notification_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_to_entry(r) for r in rows]

    def dismiss(self, entry_id: int) -> None:
        with self._db.conn() as con:
            con.execute(
                "UPDATE notification_history SET dismissed = 1 WHERE id = ?",
                (entry_id,),
            )

    def clear(self) -> None:
        with self._db.conn() as con:
            con.execute("DELETE FROM notification_history")

    def clear_since(self, since_iso: str) -> int:
        with self._db.conn() as con:
            cur = con.execute(
                "DELETE FROM notification_history WHERE timestamp >= ?", (since_iso,)
            )
            return cur.rowcount


def _to_entry(r) -> NotificationEntry:
    return NotificationEntry(
        id=r["id"],
        timestamp=r["timestamp"],
        type=r["type"],
        content=r["content"],
        dismissed=bool(r["dismissed"]),
    )
