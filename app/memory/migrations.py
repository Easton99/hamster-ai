MIGRATIONS: list[str] = [
    # v0 — initial schema
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS memories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        content     TEXT    NOT NULL,
        type        TEXT    NOT NULL DEFAULT 'explicit'
    );

    CREATE TABLE IF NOT EXISTS todos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        text        TEXT    NOT NULL,
        done        INTEGER NOT NULL DEFAULT 0,
        due_date    TEXT
    );

    CREATE TABLE IF NOT EXISTS notes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        text        TEXT    NOT NULL
    );

    CREATE TABLE IF NOT EXISTS future_features (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        requested_at                TEXT    NOT NULL DEFAULT (datetime('now')),
        title                       TEXT    NOT NULL,
        description                 TEXT,
        reason_currently_unavailable TEXT,
        priority                    TEXT    NOT NULL DEFAULT 'normal',
        status                      TEXT    NOT NULL DEFAULT 'suggested'
    );
    """,

    # v1 — sessions
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at   TEXT NOT NULL DEFAULT (datetime('now')),
        ended_at     TEXT,
        session_type TEXT NOT NULL DEFAULT 'unknown',
        primary_app  TEXT NOT NULL DEFAULT '',
        summary      TEXT
    );
    """,

    # v2 — tags, notification history, reminders
    """
    ALTER TABLE memories ADD COLUMN tags TEXT NOT NULL DEFAULT '';
    ALTER TABLE todos    ADD COLUMN tags TEXT NOT NULL DEFAULT '';
    ALTER TABLE notes    ADD COLUMN tags TEXT NOT NULL DEFAULT '';

    CREATE TABLE IF NOT EXISTS notification_history (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT    NOT NULL DEFAULT (datetime('now')),
        type      TEXT    NOT NULL DEFAULT 'system',
        content   TEXT    NOT NULL,
        dismissed INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS reminders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT    NOT NULL DEFAULT (datetime('now')),
        fire_at    TEXT    NOT NULL,
        content    TEXT    NOT NULL,
        fired      INTEGER NOT NULL DEFAULT 0,
        cancelled  INTEGER NOT NULL DEFAULT 0
    );
    """,
]


def run_migrations(db) -> None:
    with db.conn() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
        )
        row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = row[0] if row[0] is not None else -1

    for i, sql in enumerate(MIGRATIONS):
        if i <= current:
            continue
        with db.conn() as con:
            con.executescript(sql)
            con.execute("INSERT OR REPLACE INTO schema_version VALUES (?)", (i,))
