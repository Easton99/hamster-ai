import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.memory.db import Database


@dataclass
class Reminder:
    id: int
    created_at: str
    fire_at: str
    content: str
    fired: bool
    cancelled: bool


class ReminderScheduler:
    def __init__(self, db: "Database", on_fire: Callable[[Reminder], None]) -> None:
        self._db = db
        self._on_fire = on_fire
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._schedule_tick()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()

    def add(self, fire_at: datetime, content: str) -> Reminder:
        fire_iso = fire_at.strftime("%Y-%m-%d %H:%M:%S")
        with self._db.conn() as con:
            cur = con.execute(
                "INSERT INTO reminders (fire_at, content) VALUES (?, ?)",
                (fire_iso, content),
            )
            row = con.execute(
                "SELECT * FROM reminders WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return _to_reminder(row)

    def cancel(self, reminder_id: int) -> bool:
        with self._db.conn() as con:
            cur = con.execute(
                "UPDATE reminders SET cancelled = 1"
                " WHERE id = ? AND fired = 0 AND cancelled = 0",
                (reminder_id,),
            )
        return cur.rowcount > 0

    def list_pending(self) -> list[Reminder]:
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM reminders WHERE fired = 0 AND cancelled = 0"
                " ORDER BY fire_at ASC"
            ).fetchall()
        return [_to_reminder(r) for r in rows]

    def list_all(self) -> list[Reminder]:
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM reminders ORDER BY fire_at DESC LIMIT 20"
            ).fetchall()
        return [_to_reminder(r) for r in rows]

    def _schedule_tick(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(60.0, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        if not self._running:
            return
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self._db.conn() as con:
            rows = con.execute(
                "SELECT * FROM reminders WHERE fired = 0 AND cancelled = 0"
                " AND fire_at <= ?",
                (now,),
            ).fetchall()
            for row in rows:
                con.execute(
                    "UPDATE reminders SET fired = 1 WHERE id = ?", (row["id"],)
                )
                reminder = _to_reminder(row)
                try:
                    self._on_fire(reminder)
                except Exception:
                    pass
        self._schedule_tick()


def parse_reminder_time(text: str) -> datetime | None:
    """Best-effort natural language time parser. Returns None if unparseable."""
    import re
    from datetime import timedelta

    text = text.lower().strip()
    now = datetime.now()

    # "in X minutes/hours"
    m = re.search(r'in\s+(\d+)\s+(minute|min|hour|hr)s?', text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit in ("minute", "min"):
            return now + timedelta(minutes=n)
        else:
            return now + timedelta(hours=n)

    # "at HH:MM" or "at H:MM am/pm"
    m = re.search(r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?', text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        ampm = m.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target.replace(day=target.day + 1)
        return target

    # "at Xpm" or "at Xam"
    m = re.search(r'at\s+(\d{1,2})\s*(am|pm)', text)
    if m:
        hour = int(m.group(1))
        ampm = m.group(2)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target = target.replace(day=target.day + 1)
        return target

    return None


def _to_reminder(r) -> Reminder:
    return Reminder(
        id=r["id"],
        created_at=r["created_at"],
        fire_at=r["fire_at"],
        content=r["content"],
        fired=bool(r["fired"]),
        cancelled=bool(r["cancelled"]),
    )
