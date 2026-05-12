from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext
    from app.observer.pc_context import PCSnapshot

SYSTEM_PROMPT = """\
You are Hamster AI, a lightweight local Windows desktop assistant.

You are helpful, brief, privacy-first, and honest.

You should:
- help the user remember things
- track lightweight habits and preferences
- make useful suggestions
- say when you do not know something
- say when you are guessing
- push back when the user is wrong or an idea is risky
- add unsupported requests to a future feature backlog
- ask before storing inferred preferences
- keep spoken responses shorter than written ones if voice is enabled

You have access to PC metadata: the active app name, window title, CPU/RAM usage, and idle time.
You can and should reference this when relevant.
Say things like "Looks like VS Code is active" or "Your CPU is at 40%."
Do not say "I can see your screen" — you cannot see visual content, only app/process names.

You must not:
- pretend to know things
- always agree with the user
- fake capabilities
- store sensitive/private/work information
- record audio
- inspect screen contents or claim to see visual content
- bypass Work Mode, Private Mode, Focus Mode, or Game Safe Mode"""


class PromptBuilder:
    def __init__(self, max_history_turns: int = 20) -> None:
        self.max_history_turns = max_history_turns

    def build(
        self,
        history: list[dict[str, str]],
        user_input: str,
        extra_context: str | None = None,
        pc_snapshot: "PCSnapshot | None" = None,
        app: "AppContext | None" = None,
    ) -> list[dict[str, str]]:
        system_content = SYSTEM_PROMPT
        if extra_context:
            system_content += f"\n\n{extra_context}"
        if pc_snapshot is not None:
            ctx_str = pc_snapshot.to_context_string()
            if ctx_str:
                system_content += f"\n\n{ctx_str}"
        if app is not None:
            sess_str = _build_session_context(app)
            if sess_str:
                system_content += f"\n\n{sess_str}"
        now = datetime.now().strftime("%A, %d %B %Y, %H:%M")
        system_content += f"\n\nCurrent time: {now}"

        # Keep last N full turns (each turn = 1 user + 1 assistant message)
        trimmed = history[-(self.max_history_turns * 2):]

        return [
            {"role": "system", "content": system_content},
            *trimmed,
            {"role": "user", "content": user_input},
        ]


def _build_session_context(app: "AppContext") -> str:
    try:
        store = app.store
        if store is None:
            return ""
        sessions = store.recent_sessions(limit=8)
        if not sessions:
            return ""

        now = datetime.now(timezone.utc)
        lines = ["Session history (today):"]
        for s in sessions:
            try:
                start = datetime.fromisoformat(s.started_at).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            end_str = s.ended_at
            if end_str:
                try:
                    end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
                    duration = int((end - start).total_seconds() // 60)
                    duration_str = f"{duration} min" if duration > 0 else "<1 min"
                except ValueError:
                    duration_str = "?"
                status = f"ended ({duration_str})"
            else:
                duration = int((now - start).total_seconds() // 60)
                duration_str = f"{duration} min" if duration > 0 else "<1 min"
                status = f"active, {duration_str} so far"
            lines.append(f"  {s.started_at[11:16]}  {s.session_type} ({s.primary_app}) — {status}")

        return "\n".join(lines)
    except Exception:
        return ""
