"""Milestone 11 — Insights Plugin

Four features in one plugin:
  1. End-of-day summary  — tray notification at 6 PM with today's activity
  2. /summary            — today's session breakdown
  3. /week               — last 7 days breakdown
  4. /patterns           — recurring habits detected from session history
  5. /energy             — hourly activity profile
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_EOD_HOUR = 18          # 6 PM
_POLL_INTERVAL = 1800   # check every 30 minutes


# ── Session analysis helpers ──────────────────────────────────────────────────

def _duration_minutes(started_at: str, ended_at: str | None) -> int:
    try:
        start = datetime.fromisoformat(started_at).replace(tzinfo=timezone.utc)
        if ended_at:
            end = datetime.fromisoformat(ended_at).replace(tzinfo=timezone.utc)
        else:
            end = datetime.now(timezone.utc)
        return max(0, int((end - start).total_seconds() // 60))
    except Exception:
        return 0


def _fmt_minutes(mins: int) -> str:
    if mins < 60:
        return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h {m}m" if m else f"{h}h"


def _analyse(sessions) -> dict:
    """Return totals-by-type, minutes-by-hour, average session length."""
    by_type: dict[str, int] = defaultdict(int)
    by_hour: dict[int, int] = defaultdict(int)
    lengths: list[int] = []

    for s in sessions:
        mins = _duration_minutes(s.started_at, s.ended_at)
        if mins == 0:
            continue
        by_type[s.session_type] += mins
        lengths.append(mins)
        try:
            hour = datetime.fromisoformat(s.started_at).hour
            by_hour[hour] += mins
        except Exception:
            pass

    total = sum(by_type.values())
    avg_len = sum(lengths) // len(lengths) if lengths else 0
    return {"total": total, "by_type": dict(by_type), "by_hour": dict(by_hour), "avg_len": avg_len}


def _format_by_type(by_type: dict, total: int) -> list[str]:
    lines = []
    for stype, mins in sorted(by_type.items(), key=lambda x: -x[1]):
        pct = int(mins * 100 / total) if total else 0
        lines.append(f"  {stype}: {_fmt_minutes(mins)}  ({pct}%)")
    return lines


def _peak_hours(by_hour: dict) -> str:
    if not by_hour:
        return "none"
    top = sorted(by_hour.items(), key=lambda x: -x[1])[:3]
    spans = sorted(h for h, _ in top)
    return ", ".join(f"{h:02d}:00" for h in spans)


# ── Plugin ────────────────────────────────────────────────────────────────────

class Plugin(PluginBase):
    name = "insights"
    description = "Daily/weekly activity summaries, pattern detection, energy profile"
    enabled_by_default = True
    dependencies = []
    permissions_required = []

    def on_start(self, app: "AppContext") -> None:
        self._app = app
        self._stop = threading.Event()
        self._last_eod_date: date | None = None
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="Insights"
        )
        self._thread.start()

    def on_stop(self, app: "AppContext") -> None:
        self._stop.set()

    def on_event(self, event: str, data) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/summary":  self._cmd_summary,
            "/week":     self._cmd_week,
            "/patterns": self._cmd_patterns,
            "/energy":   self._cmd_energy,
        }

    # ── End-of-day background trigger ────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop.wait(_POLL_INTERVAL):
            try:
                self._check_eod()
            except Exception:
                pass

    def _check_eod(self) -> None:
        now = datetime.now()
        today = now.date()
        if now.hour < _EOD_HOUR:
            return
        if self._last_eod_date == today:
            return

        self._last_eod_date = today
        summary = self._build_today_summary()
        self._app.event_bus.emit("day_ended", {"date": str(today)})
        self._app.event_bus.emit("notify", {
            "title": "Hamster AI — End of day",
            "body": summary,
        })

    # ── /summary ─────────────────────────────────────────────────────────────

    def _cmd_summary(self, app: "AppContext", args: str) -> str:
        return self._build_today_summary()

    def _build_today_summary(self) -> str:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        sessions = self._app.store.sessions_in_range(today, tomorrow)

        if not sessions:
            return "No activity recorded today."

        a = _analyse(sessions)
        lines = [f"Today's activity  ({_fmt_minutes(a['total'])} total):"]
        lines += _format_by_type(a["by_type"], a["total"])
        if a["by_hour"]:
            lines.append(f"Peak hours: {_peak_hours(a['by_hour'])}")
        if a["avg_len"]:
            lines.append(f"Avg session length: {_fmt_minutes(a['avg_len'])}")
        return "\n".join(lines)

    # ── /week ─────────────────────────────────────────────────────────────────

    def _cmd_week(self, app: "AppContext", args: str) -> str:
        since = (date.today() - timedelta(days=6)).isoformat()
        sessions = app.store.sessions_in_range(since)

        if not sessions:
            return "No activity in the past 7 days."

        # Group by calendar date
        by_day: dict[str, list] = defaultdict(list)
        for s in sessions:
            day = s.started_at[:10]
            by_day[day].append(s)

        lines = ["Past 7 days:"]
        grand_total = 0
        all_types: dict[str, int] = defaultdict(int)

        for day in sorted(by_day.keys()):
            a = _analyse(by_day[day])
            grand_total += a["total"]
            for t, m in a["by_type"].items():
                all_types[t] += m
            top = max(a["by_type"], key=a["by_type"].get) if a["by_type"] else "—"
            weekday = datetime.fromisoformat(day).strftime("%a %d %b")
            lines.append(f"  {weekday}: {_fmt_minutes(a['total'])}  (mostly {top})")

        lines.append(f"Total: {_fmt_minutes(grand_total)}")
        if all_types:
            fav = max(all_types, key=all_types.__getitem__)
            fav_pct = int(all_types[fav] * 100 / grand_total) if grand_total else 0
            lines.append(f"Most time spent: {fav} ({fav_pct}%)")
        return "\n".join(lines)

    # ── /patterns ────────────────────────────────────────────────────────────

    def _cmd_patterns(self, app: "AppContext", args: str) -> str:
        since = (date.today() - timedelta(days=13)).isoformat()
        sessions = app.store.sessions_in_range(since)

        if len(sessions) < 5:
            return "Not enough data yet — check back after a few days of activity."

        # Average start hour per session type
        hours_by_type: dict[str, list[int]] = defaultdict(list)
        dow_by_type: dict[str, list[int]] = defaultdict(list)  # 0=Mon
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s.started_at)
                hours_by_type[s.session_type].append(dt.hour)
                dow_by_type[s.session_type].append(dt.weekday())
            except Exception:
                pass

        _DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        lines = ["Patterns detected:"]

        for stype, hours in sorted(hours_by_type.items()):
            if len(hours) < 2:
                continue
            avg_hour = int(sum(hours) / len(hours))
            lines.append(f"  {stype.capitalize()} sessions typically start around {avg_hour:02d}:00")

        for stype, days in sorted(dow_by_type.items()):
            if len(days) < 3:
                continue
            most_common_day = max(set(days), key=days.count)
            count = days.count(most_common_day)
            if count >= 2:
                lines.append(f"  {stype.capitalize()} happens most on {_DOW[most_common_day]}s")

        if len(lines) == 1:
            lines.append("  No strong patterns yet — keep using the app!")
        return "\n".join(lines)

    # ── /energy ──────────────────────────────────────────────────────────────

    def _cmd_energy(self, app: "AppContext", args: str) -> str:
        since = (date.today() - timedelta(days=6)).isoformat()
        sessions = app.store.sessions_in_range(since)

        if not sessions:
            return "No activity data yet."

        a = _analyse(sessions)

        if not a["by_hour"]:
            return "Not enough data to build an energy profile."

        # Top 3 hours = peak, bottom 3 (with any activity) = low
        sorted_hours = sorted(a["by_hour"].items(), key=lambda x: -x[1])
        peak = [f"{h:02d}:00" for h, _ in sorted_hours[:3]]
        low  = [f"{h:02d}:00" for h, _ in sorted_hours[-3:] if _ > 0]

        lines = ["Energy profile (past 7 days):"]
        lines.append(f"  Most active:   {', '.join(peak)}")
        if low:
            lines.append(f"  Least active:  {', '.join(low)}")
        if a["avg_len"]:
            lines.append(f"  Avg session:   {_fmt_minutes(a['avg_len'])}")
        if a["total"]:
            lines.append(f"  Total tracked: {_fmt_minutes(a['total'])}")
        return "\n".join(lines)
