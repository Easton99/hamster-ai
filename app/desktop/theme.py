_THEMES: dict[str, dict] = {
    "soft_hamster_minimal": {
        "BG":       "#FAF7F2",
        "PRIMARY":  "#F5E6D3",
        "ACCENT":   "#A67C52",
        "SECONDARY":"#F2B880",
        "TEXT":     "#3E2C1C",
        "TEXT_MUTED":"#8B6A4A",
        "SURFACE":  "#F5EDE3",
        "BORDER":   "#D4C0A8",
        "INPUT_BG": "white",
    },
    "dark_hamster": {
        "BG":       "#1E1A17",
        "PRIMARY":  "#2A2420",
        "ACCENT":   "#A67C52",
        "SECONDARY":"#6B4E35",
        "TEXT":     "#F5E6D3",
        "TEXT_MUTED":"#8A7060",
        "SURFACE":  "#2E2520",
        "BORDER":   "#4A3828",
        "INPUT_BG": "#2E2520",
    },
    "high_contrast": {
        "BG":       "#000000",
        "PRIMARY":  "#111111",
        "ACCENT":   "#FFCC00",
        "SECONDARY":"#888888",
        "TEXT":     "#FFFFFF",
        "TEXT_MUTED":"#BBBBBB",
        "SURFACE":  "#1A1A1A",
        "BORDER":   "#FFCC00",
        "INPUT_BG": "#111111",
    },
}

_current_theme: str = "soft_hamster_minimal"


def set_theme(name: str) -> None:
    global _current_theme, BG, PRIMARY, ACCENT, SECONDARY, TEXT, TEXT_MUTED, STYLESHEET
    if name in _THEMES:
        _current_theme = name
    _reload()


def _reload() -> None:
    global BG, PRIMARY, ACCENT, SECONDARY, TEXT, TEXT_MUTED, STYLESHEET
    t = _THEMES[_current_theme]
    BG        = t["BG"]
    PRIMARY   = t["PRIMARY"]
    ACCENT    = t["ACCENT"]
    SECONDARY = t["SECONDARY"]
    TEXT      = t["TEXT"]
    TEXT_MUTED= t["TEXT_MUTED"]
    STYLESHEET = _make_stylesheet(t)


def _make_stylesheet(t: dict) -> str:
    return f"""
QWidget {{
    background-color: {t['BG']};
    color: {t['TEXT']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

QTextEdit {{
    background-color: {t['PRIMARY']};
    border: 1px solid {t['SECONDARY']};
    border-radius: 8px;
    padding: 8px;
    color: {t['TEXT']};
    selection-background-color: {t['SECONDARY']};
}}

QLineEdit {{
    background-color: {t['INPUT_BG']};
    border: 1.5px solid {t['SECONDARY']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {t['TEXT']};
}}

QLineEdit:focus {{
    border-color: {t['ACCENT']};
}}

QPushButton {{
    background-color: {t['ACCENT']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: #8B6A42;
}}

QPushButton:pressed {{
    background-color: #7A5A38;
}}

QPushButton:disabled {{
    background-color: #C4A882;
    color: #F0E4D4;
}}

QCheckBox {{
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {t['ACCENT']};
    background: {t['INPUT_BG']};
}}

QCheckBox::indicator:checked {{
    background-color: {t['ACCENT']};
    image: none;
}}

QComboBox {{
    background-color: {t['INPUT_BG']};
    border: 1.5px solid {t['SECONDARY']};
    border-radius: 6px;
    padding: 5px 10px;
    color: {t['TEXT']};
}}

QComboBox:focus {{
    border-color: {t['ACCENT']};
}}

QComboBox QAbstractItemView {{
    background-color: {t['INPUT_BG']};
    selection-background-color: {t['PRIMARY']};
    color: {t['TEXT']};
    border: 1px solid {t['SECONDARY']};
}}

QLabel {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: {t['PRIMARY']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {t['SECONDARY']};
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QMenu {{
    background-color: {t['BG']};
    border: 1px solid {t['SECONDARY']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {t['PRIMARY']};
    color: {t['TEXT']};
}}

QMenu::separator {{
    height: 1px;
    background: {t['SECONDARY']};
    margin: 4px 8px;
}}

QFrame#PluginCard {{
    background: {t['SURFACE']};
    border: 1px solid {t['BORDER']};
    border-radius: 10px;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {t['INPUT_BG']};
    border: 1.5px solid {t['SECONDARY']};
    border-radius: 6px;
    padding: 4px 8px;
    color: {t['TEXT']};
}}

QTabWidget::pane {{
    border: 1px solid {t['BORDER']};
    background: {t['BG']};
}}

QTabBar::tab {{
    background: {t['PRIMARY']};
    color: {t['TEXT_MUTED']};
    padding: 6px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background: {t['BG']};
    color: {t['ACCENT']};
    font-weight: bold;
}}
"""


# Initialise defaults
BG         = _THEMES["soft_hamster_minimal"]["BG"]
PRIMARY    = _THEMES["soft_hamster_minimal"]["PRIMARY"]
ACCENT     = _THEMES["soft_hamster_minimal"]["ACCENT"]
SECONDARY  = _THEMES["soft_hamster_minimal"]["SECONDARY"]
TEXT       = _THEMES["soft_hamster_minimal"]["TEXT"]
TEXT_MUTED = _THEMES["soft_hamster_minimal"]["TEXT_MUTED"]
STYLESHEET = _make_stylesheet(_THEMES["soft_hamster_minimal"])
