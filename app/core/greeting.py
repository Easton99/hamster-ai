"""Startup greeting selection and gating logic."""
from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_MORNING   = ["Morning. Need anything?", "Good morning. I'm up.", "Morning. Try not to break anything."]
_AFTERNOON = ["Afternoon. Need a hand?", "Still grinding?", "Hey. What do you need?"]
_EVENING   = ["Evening. Late one?", "Still at it?", "Evening. Need anything?"]
_NIGHT     = ["Hamster online.", "Late night? I'm here.", "Still up? What do you need?"]


def _time_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return random.choice(_MORNING)
    elif 12 <= hour < 17:
        return random.choice(_AFTERNOON)
    elif 17 <= hour < 21:
        return random.choice(_EVENING)
    else:
        return random.choice(_NIGHT)


def can_greet(app: "AppContext") -> bool:
    """Return True if no active mode suppresses greetings.

    Work, Private, and Game Safe fully pause the app.
    Focus Mode pauses greetings specifically (spec section 16).
    """
    modes = app.modes
    if modes is None:
        return False
    return not modes.is_fully_paused() and not modes.focus_mode


def get_startup_greeting(app: "AppContext") -> str | None:
    """Return a greeting string, or None if greeting should be suppressed."""
    if not app.settings.get("greet_on_startup", True):
        return None
    if not can_greet(app):
        return None
    return _time_greeting()
