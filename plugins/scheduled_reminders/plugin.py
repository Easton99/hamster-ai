from typing import Any

from app.plugins.plugin_base import PluginBase


class Plugin(PluginBase):
    name = "scheduled_reminders"
    description = "Set time-based reminders that fire as desktop notifications."
    enabled_by_default = True

    def __init__(self) -> None:
        self._app = None

    def on_start(self, app: Any) -> None:
        self._app = app

    def on_stop(self, app: Any) -> None:
        self._app = None

    def on_event(self, event: str, data: Any) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/remind":          (self._cmd_remind,          "set a reminder (e.g. /remind me at 6pm to check the build)"),
            "/show-reminders":  (self._cmd_show_reminders,  "list pending reminders"),
            "/cancel-reminder": (self._cmd_cancel_reminder,  "cancel a reminder by id"),
        }

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_remind(self, app, args: str) -> str:
        if not app.reminder_scheduler:
            return "Reminder scheduler not available."
        if not args:
            return "Usage: /remind me at 6pm to check the build"

        from app.core.reminder_scheduler import parse_reminder_time

        content = args
        # strip "me" prefix if present
        if content.lower().startswith("me "):
            content = content[3:]

        # split on "to" to find the time vs the message
        lower = content.lower()
        to_idx = lower.find(" to ")
        if to_idx == -1:
            return "Could not find what to remind you. Try: /remind me at 6pm to check the build"

        time_part = content[:to_idx].strip()
        message = content[to_idx + 4:].strip()

        fire_at = parse_reminder_time(time_part)
        if fire_at is None:
            return (
                f"Could not parse the time '{time_part}'.\n"
                "Try: /remind me at 6pm to ... or /remind me in 30 minutes to ..."
            )

        reminder = app.reminder_scheduler.add(fire_at, message)
        return f"Reminder set (#{reminder.id}): '{message}' at {fire_at.strftime('%H:%M on %d %b')}."

    def _cmd_show_reminders(self, app, args: str) -> str:
        if not app.reminder_scheduler:
            return "Reminder scheduler not available."
        pending = app.reminder_scheduler.list_pending()
        if not pending:
            return "No pending reminders."
        lines = ["Pending reminders:"]
        for r in pending:
            lines.append(f"  #{r.id} at {r.fire_at[:16]} — {r.content}")
        return "\n".join(lines)

    def _cmd_cancel_reminder(self, app, args: str) -> str:
        if not app.reminder_scheduler:
            return "Reminder scheduler not available."
        if not args:
            return "Usage: /cancel-reminder <id>"
        try:
            rid = int(args.lstrip("#"))
        except ValueError:
            return "Usage: /cancel-reminder <id>  (must be a number)"
        ok = app.reminder_scheduler.cancel(rid)
        return f"Reminder #{rid} cancelled." if ok else f"No active reminder with id #{rid}."


