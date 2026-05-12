from typing import Any

from app.plugins.plugin_base import PluginBase


class Plugin(PluginBase):
    name = "process_awareness"
    description = "Running processes, internet-using apps, and Windows startup programs."
    enabled_by_default = False

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
            "/processes":       (self._cmd_processes,     "list top running processes"),
            "/internet-apps":   (self._cmd_internet,      "list processes using the internet"),
            "/startup-programs":(self._cmd_startup,       "list Windows startup entries"),
            "/kill":            (self._cmd_kill,           "terminate a process by name (with confirmation)"),
        }

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_processes(self, app, args: str) -> str:
        if self._is_protected(app):
            return "Process list is not available in the current mode."
        from app.observer.process_list import get_top_processes
        procs = get_top_processes(10)
        if not procs:
            return "Could not retrieve process list."
        lines = ["Top processes by CPU:"]
        for p in procs:
            lines.append(
                f"  {p.name:<32} CPU: {p.cpu_percent:>5.1f}%  RAM: {p.ram_mb:.0f} MB"
            )
        return "\n".join(lines)

    def _cmd_internet(self, app, args: str) -> str:
        if self._is_protected(app):
            return "Not available in the current mode."
        from app.observer.process_list import get_internet_processes
        procs = get_internet_processes()
        if not procs:
            return "No processes with active internet connections found."
        lines = ["Processes with active network connections:"]
        for p in procs:
            lines.append(f"  {p.name} (PID {p.pid})")
        return "\n".join(lines)

    def _cmd_startup(self, app, args: str) -> str:
        from app.observer.startup_programs import get_startup_programs
        entries = get_startup_programs()
        if not entries:
            return "No startup programs found (or access denied)."
        lines = ["Windows startup programs:"]
        for e in entries:
            lines.append(f"  [{e.source}] {e.name}")
        return "\n".join(lines)

    def _cmd_kill(self, app, args: str) -> str:
        if not args:
            return "Usage: /kill <process name>"
        return (
            f"To kill '{args}', type: /kill-confirm {args}\n"
            f"This will terminate all processes matching that name."
        )

    def _is_protected(self, app) -> bool:
        if app.modes and (app.modes.work_mode or app.modes.private_mode):
            return True
        return False


