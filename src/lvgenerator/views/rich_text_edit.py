from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextListFormat
from PySide6.QtWidgets import (
    QHBoxLayout,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.gaeb.html_converter import gaeb_html_to_qt_html, qt_html_to_gaeb_html
from lvgenerator.models.text_style_settings import text_style_settings


class RichTextEditWidget(QWidget):
    """Rich text editor with formatting toolbar for GAEB text fields."""

    editing_finished = Signal(str, str)  # (gaeb_html, plain_text)
    content_changed = Signal()

    def __init__(self, max_height: int = 200, parent=None):
        super().__init__(parent)
        self._max_height = max_height
        self._gaeb_parent_tag = "Text"
        self._gaeb_ns = ""
        self._snapshot_html = ""
        self._snapshot_text = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Formatting toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)

        self._btn_bold = self._make_toggle_button("F", "Fett (Ctrl+B)")
        font = self._btn_bold.font()
        font.setBold(True)
        self._btn_bold.setFont(font)
        toolbar.addWidget(self._btn_bold)

        self._btn_italic = self._make_toggle_button("K", "Kursiv (Ctrl+I)")
        font = self._btn_italic.font()
        font.setItalic(True)
        self._btn_italic.setFont(font)
        toolbar.addWidget(self._btn_italic)

        self._btn_underline = self._make_toggle_button("U", "Unterstrichen (Ctrl+U)")
        font = self._btn_underline.font()
        font.setUnderline(True)
        self._btn_underline.setFont(font)
        toolbar.addWidget(self._btn_underline)

        self._btn_bullet = self._make_toggle_button("\u2022", "Aufzaehlung")
        toolbar.addWidget(self._btn_bullet)

        self._btn_indent = self._make_button("\u2192", "Einruecken")
        toolbar.addWidget(self._btn_indent)

        self._btn_outdent = self._make_button("\u2190", "Ausruecken")
        toolbar.addWidget(self._btn_outdent)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Text editor
        self._text_edit = QTextEdit()
        self._text_edit.setMaximumHeight(self._max_height)
        self._text_edit.setTabChangesFocus(True)
        layout.addWidget(self._text_edit)

    def _make_button(self, text: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet("QToolButton { padding: 2px; }")
        return btn

    def _make_toggle_button(self, text: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(
            "QToolButton { padding: 2px; }"
            "QToolButton:checked { background-color: #3d3d3d; border: 1px solid #666; }"
        )
        return btn

    def _connect_signals(self) -> None:
        self._btn_bold.clicked.connect(self._on_bold)
        self._btn_italic.clicked.connect(self._on_italic)
        self._btn_underline.clicked.connect(self._on_underline)
        self._btn_bullet.clicked.connect(self._on_bullet_list)
        self._btn_indent.clicked.connect(self._on_indent)
        self._btn_outdent.clicked.connect(self._on_outdent)
        self._text_edit.cursorPositionChanged.connect(self._update_toolbar_state)
        self._text_edit.textChanged.connect(self.content_changed.emit)

    def set_gaeb_html(self, gaeb_html: str, parent_tag: str = "Text", ns: str = "") -> None:
        """Load GAEB HTML into the editor."""
        self._gaeb_parent_tag = parent_tag
        self._gaeb_ns = ns

        settings = text_style_settings.get_settings()
        qt_html = gaeb_html_to_qt_html(
            gaeb_html,
            default_font_family=settings.font_family,
            default_font_size_pt=settings.font_size_pt,
        )
        self._text_edit.blockSignals(True)
        if qt_html:
            self._text_edit.setHtml(qt_html)
        else:
            self._text_edit.clear()
        self._text_edit.blockSignals(False)
        self._take_snapshot()

    def set_plain_text(self, text: str) -> None:
        """Load plain text (fallback when no HTML available)."""
        settings = text_style_settings.get_settings()
        self._text_edit.blockSignals(True)
        self._text_edit.clear()
        self._text_edit.setFont(
            QFont(settings.font_family, settings.font_size_pt)
        )
        self._text_edit.setPlainText(text)
        self._text_edit.blockSignals(False)
        self._take_snapshot()

    def get_gaeb_html(self) -> str:
        """Get current content as GAEB HTML."""
        if not self._gaeb_ns:
            return ""
        qt_html = self._text_edit.toHtml()
        return qt_html_to_gaeb_html(qt_html, self._gaeb_parent_tag, self._gaeb_ns)

    def get_plain_text(self) -> str:
        """Get current content as plain text."""
        return self._text_edit.toPlainText()

    def clear(self) -> None:
        self._text_edit.blockSignals(True)
        self._text_edit.clear()
        self._text_edit.blockSignals(False)
        self._snapshot_html = ""
        self._snapshot_text = ""

    def setPlaceholderText(self, text: str) -> None:
        self._text_edit.setPlaceholderText(text)

    def setMaximumHeight(self, h: int) -> None:
        self._text_edit.setMaximumHeight(h)

    def setStyleSheet(self, style: str) -> None:
        self._text_edit.setStyleSheet(style)

    def setToolTip(self, tip: str) -> None:
        self._text_edit.setToolTip(tip)

    def _take_snapshot(self) -> None:
        """Snapshot current state for change detection on focus-out."""
        self._snapshot_html = self._text_edit.toHtml()
        self._snapshot_text = self._text_edit.toPlainText()

    def commit_if_changed(self) -> None:
        """Check if content changed since last snapshot and emit editing_finished."""
        current_text = self._text_edit.toPlainText()
        if current_text != self._snapshot_text:
            gaeb_html = self.get_gaeb_html()
            plain_text = current_text
            self._snapshot_html = self._text_edit.toHtml()
            self._snapshot_text = current_text
            self.editing_finished.emit(gaeb_html, plain_text)

    def focusOutEvent(self, event) -> None:
        self.commit_if_changed()
        super().focusOutEvent(event)

    def _on_bold(self) -> None:
        fmt = QTextCharFormat()
        if self._btn_bold.isChecked():
            fmt.setFontWeight(QFont.Weight.Bold)
        else:
            fmt.setFontWeight(QFont.Weight.Normal)
        self._merge_format(fmt)

    def _on_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(self._btn_italic.isChecked())
        self._merge_format(fmt)

    def _on_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self._btn_underline.isChecked())
        self._merge_format(fmt)

    def _on_bullet_list(self) -> None:
        cursor = self._text_edit.textCursor()
        if self._btn_bullet.isChecked():
            cursor.createList(QTextListFormat.Style.ListDisc)
        else:
            # Remove list
            lst = cursor.currentList()
            if lst:
                block = cursor.block()
                lst.remove(block)
                # Reset indent
                fmt = block.blockFormat()
                fmt.setIndent(0)
                cursor.setBlockFormat(fmt)

    def _merge_format(self, fmt: QTextCharFormat) -> None:
        cursor = self._text_edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self._text_edit.mergeCurrentCharFormat(fmt)

    def _on_indent(self) -> None:
        cursor = self._text_edit.textCursor()
        fmt = cursor.blockFormat()
        fmt.setIndent(fmt.indent() + 1)
        cursor.setBlockFormat(fmt)

    def _on_outdent(self) -> None:
        cursor = self._text_edit.textCursor()
        fmt = cursor.blockFormat()
        if fmt.indent() > 0:
            fmt.setIndent(fmt.indent() - 1)
            cursor.setBlockFormat(fmt)

    def _update_toolbar_state(self) -> None:
        fmt = self._text_edit.currentCharFormat()
        self._btn_bold.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self._btn_italic.setChecked(fmt.fontItalic())
        self._btn_underline.setChecked(fmt.fontUnderline())

        lst = self._text_edit.textCursor().currentList()
        self._btn_bullet.setChecked(lst is not None)
