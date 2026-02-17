"""Programmatische Monochrom-Icons für eine einheitliche, moderne UI."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

_SIZE = 24
_COLOR = QColor("#cccccc")
_STROKE = 1.8


def _begin(size: int = _SIZE) -> tuple[QPixmap, QPainter]:
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(_COLOR, _STROKE, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    return px, p


def _finish(px: QPixmap, p: QPainter) -> QIcon:
    p.end()
    return QIcon(px)


def icon_new() -> QIcon:
    """Blank document with folded corner."""
    px, p = _begin()
    # Document body
    p.drawLine(QPointF(7, 3), QPointF(7, 21))
    p.drawLine(QPointF(7, 21), QPointF(17, 21))
    p.drawLine(QPointF(17, 21), QPointF(17, 8))
    p.drawLine(QPointF(17, 8), QPointF(12, 3))
    p.drawLine(QPointF(12, 3), QPointF(7, 3))
    # Fold
    p.drawLine(QPointF(12, 3), QPointF(12, 8))
    p.drawLine(QPointF(12, 8), QPointF(17, 8))
    return _finish(px, p)


def icon_open() -> QIcon:
    """Open folder."""
    px, p = _begin()
    # Folder back
    p.drawLine(QPointF(3, 8), QPointF(3, 19))
    p.drawLine(QPointF(3, 19), QPointF(18, 19))
    # Folder tab
    p.drawLine(QPointF(3, 8), QPointF(8, 8))
    p.drawLine(QPointF(8, 8), QPointF(10, 6))
    p.drawLine(QPointF(10, 6), QPointF(18, 6))
    p.drawLine(QPointF(18, 6), QPointF(18, 19))
    # Front flap (open)
    p.drawLine(QPointF(3, 11), QPointF(6, 11))
    p.drawLine(QPointF(6, 11), QPointF(21, 8))
    p.drawLine(QPointF(21, 8), QPointF(21, 16))
    p.drawLine(QPointF(21, 16), QPointF(18, 19))
    return _finish(px, p)


def icon_save() -> QIcon:
    """Floppy disk."""
    px, p = _begin()
    # Outer frame
    p.drawRect(QRectF(4, 3, 16, 18))
    # Inner label area
    p.drawRect(QRectF(7, 3, 10, 7))
    # Disk slot in label
    p.drawLine(QPointF(14, 5), QPointF(14, 8))
    # Bottom storage area
    p.drawRect(QRectF(7, 14, 10, 7))
    return _finish(px, p)


def icon_undo() -> QIcon:
    """Curved arrow left."""
    px, p = _begin()
    path = QPainterPath()
    path.moveTo(18, 9)
    path.cubicTo(18, 4, 6, 4, 6, 11)
    path.lineTo(6, 16)
    p.drawPath(path)
    # Arrow head
    p.drawLine(QPointF(6, 16), QPointF(10, 13))
    p.drawLine(QPointF(6, 16), QPointF(3, 12))
    return _finish(px, p)


def icon_redo() -> QIcon:
    """Curved arrow right."""
    px, p = _begin()
    path = QPainterPath()
    path.moveTo(6, 9)
    path.cubicTo(6, 4, 18, 4, 18, 11)
    path.lineTo(18, 16)
    p.drawPath(path)
    p.drawLine(QPointF(18, 16), QPointF(14, 13))
    p.drawLine(QPointF(18, 16), QPointF(21, 12))
    return _finish(px, p)


def icon_add_category() -> QIcon:
    """Folder with plus sign."""
    px, p = _begin()
    # Folder
    p.drawLine(QPointF(3, 8), QPointF(3, 19))
    p.drawLine(QPointF(3, 19), QPointF(19, 19))
    p.drawLine(QPointF(19, 19), QPointF(19, 8))
    p.drawLine(QPointF(3, 8), QPointF(8, 8))
    p.drawLine(QPointF(8, 8), QPointF(10, 6))
    p.drawLine(QPointF(10, 6), QPointF(19, 6))
    # Plus
    p.drawLine(QPointF(11, 11), QPointF(11, 17))
    p.drawLine(QPointF(8, 14), QPointF(14, 14))
    return _finish(px, p)


def icon_add_item() -> QIcon:
    """Document with plus sign."""
    px, p = _begin()
    # Document
    p.drawLine(QPointF(6, 3), QPointF(6, 21))
    p.drawLine(QPointF(6, 21), QPointF(16, 21))
    p.drawLine(QPointF(16, 21), QPointF(16, 8))
    p.drawLine(QPointF(16, 8), QPointF(11, 3))
    p.drawLine(QPointF(11, 3), QPointF(6, 3))
    p.drawLine(QPointF(11, 3), QPointF(11, 8))
    p.drawLine(QPointF(11, 8), QPointF(16, 8))
    # Plus
    p.drawLine(QPointF(18, 14), QPointF(18, 20))
    p.drawLine(QPointF(15, 17), QPointF(21, 17))
    return _finish(px, p)


def icon_delete() -> QIcon:
    """Trash can."""
    px, p = _begin()
    # Lid
    p.drawLine(QPointF(5, 7), QPointF(19, 7))
    p.drawLine(QPointF(9, 7), QPointF(9, 5))
    p.drawLine(QPointF(9, 5), QPointF(15, 5))
    p.drawLine(QPointF(15, 5), QPointF(15, 7))
    # Body
    p.drawLine(QPointF(7, 7), QPointF(8, 20))
    p.drawLine(QPointF(8, 20), QPointF(16, 20))
    p.drawLine(QPointF(16, 20), QPointF(17, 7))
    # Lines
    p.drawLine(QPointF(10, 10), QPointF(10, 17))
    p.drawLine(QPointF(12, 10), QPointF(12, 17))
    p.drawLine(QPointF(14, 10), QPointF(14, 17))
    return _finish(px, p)


def icon_move_up() -> QIcon:
    """Arrow pointing up."""
    px, p = _begin()
    p.drawLine(QPointF(12, 4), QPointF(12, 20))
    p.drawLine(QPointF(12, 4), QPointF(6, 10))
    p.drawLine(QPointF(12, 4), QPointF(18, 10))
    return _finish(px, p)


def icon_move_down() -> QIcon:
    """Arrow pointing down."""
    px, p = _begin()
    p.drawLine(QPointF(12, 20), QPointF(12, 4))
    p.drawLine(QPointF(12, 20), QPointF(6, 14))
    p.drawLine(QPointF(12, 20), QPointF(18, 14))
    return _finish(px, p)


def icon_duplicate() -> QIcon:
    """Two overlapping documents."""
    px, p = _begin()
    # Back document
    p.drawRect(QRectF(7, 3, 12, 14))
    # Front document
    p.setPen(QPen(_COLOR, _STROKE, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QBrush(QColor("#2d2d2d")))
    p.drawRect(QRectF(4, 7, 12, 14))
    p.setBrush(Qt.NoBrush)
    # Lines on front document
    p.drawLine(QPointF(7, 12), QPointF(13, 12))
    p.drawLine(QPointF(7, 15), QPointF(13, 15))
    p.drawLine(QPointF(7, 18), QPointF(11, 18))
    return _finish(px, p)
