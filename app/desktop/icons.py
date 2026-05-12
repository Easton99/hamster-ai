from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap


def make_hamster_pixmap(size: int = 32, greyed: bool = False) -> QPixmap:
    head_color   = "#BBBBBB" if greyed else "#F5E6D3"
    cheek_color  = "#999999" if greyed else "#F2B880"
    border_color = "#888888" if greyed else "#A67C52"
    nose_color   = "#888888" if greyed else "#A67C52"

    px = QPixmap(32, 32)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QBrush(QColor(head_color)))
    p.setPen(QPen(QColor(border_color), 1.5))
    p.drawEllipse(3, 1, 10, 10)
    p.drawEllipse(19, 1, 10, 10)

    p.setBrush(QBrush(QColor(head_color)))
    p.setPen(QPen(QColor(border_color), 1.5))
    p.drawEllipse(4, 7, 24, 22)

    p.setBrush(QBrush(QColor(cheek_color)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 17, 9, 7)
    p.drawEllipse(21, 17, 9, 7)

    p.setBrush(QBrush(QColor(nose_color)))
    p.drawEllipse(13, 20, 6, 4)

    p.end()

    if size != 32:
        px = px.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return px


def make_hamster_icon(greyed: bool = False) -> QIcon:
    return QIcon(make_hamster_pixmap(32, greyed))


def make_tablet_pixmap(size: int = 26) -> QPixmap:
    body_color   = "#A67C52"
    screen_color = "#D4EAF7"
    border_color = "#3E2C1C"

    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    # body
    p.setBrush(QBrush(QColor(body_color)))
    p.setPen(QPen(QColor(border_color), 1.2))
    p.drawRoundedRect(4, 1, size - 8, size - 2, 3, 3)

    # screen
    p.setBrush(QBrush(QColor(screen_color)))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 4, size - 12, size - 12, 2, 2)

    # home button dot
    p.setBrush(QBrush(QColor(border_color)))
    cx = size // 2
    p.drawEllipse(cx - 2, size - 5, 4, 4)

    p.end()

    if size != 26:
        px = px.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return px


def make_tablet_icon(size: int = 26) -> QIcon:
    return QIcon(make_tablet_pixmap(size))


def make_plugin_pixmap(size: int = 26) -> QPixmap:
    color = "#A67C52"

    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.NoPen)

    # 2×2 grid of rounded squares
    half  = size // 2
    gap   = max(2, size // 10)
    sq    = half - gap - 1
    r     = max(2, sq // 4)
    off2  = half + gap

    p.drawRoundedRect(1,    1,    sq, sq, r, r)
    p.drawRoundedRect(off2, 1,    sq, sq, r, r)
    p.drawRoundedRect(1,    off2, sq, sq, r, r)
    p.drawRoundedRect(off2, off2, sq, sq, r, r)

    p.end()

    if size != 26:
        px = px.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return px


def make_plugin_icon(size: int = 26) -> QIcon:
    return QIcon(make_plugin_pixmap(size))
