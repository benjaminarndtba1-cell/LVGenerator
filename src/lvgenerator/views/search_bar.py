from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class SearchBarWidget(QWidget):
    """Suchleiste für das Leistungsverzeichnis."""
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Suchen... (OZ, Kurztext, Langtext)"
        )
        self.search_edit.setClearButtonEnabled(True)
        layout.addWidget(self.search_edit)

        self.search_edit.textChanged.connect(self.search_changed.emit)

    def focus_search(self) -> None:
        """Fokussiert das Suchfeld."""
        self.search_edit.setFocus()
        self.search_edit.selectAll()
