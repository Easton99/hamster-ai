"""
App name substrings and window title keywords that trigger Private Mode
auto-detection. Checked case-insensitively.
"""

PROTECTED_APP_PATTERNS: frozenset[str] = frozenset([
    "1password",
    "keepass",
    "bitwarden",
    "lastpass",
    "dashlane",
])

PROTECTED_TITLE_KEYWORDS: frozenset[str] = frozenset([
    "incognito",
    "private browsing",
    "inprivate",
    "online banking",
    "paypal",
    "stripe dashboard",
])


def is_protected(process_name: str, window_title: str) -> bool:
    """Return True if the active app or title suggests private activity."""
    name_l = process_name.lower()
    title_l = window_title.lower()
    if any(p in name_l for p in PROTECTED_APP_PATTERNS):
        return True
    if any(k in title_l for k in PROTECTED_TITLE_KEYWORDS):
        return True
    return False
