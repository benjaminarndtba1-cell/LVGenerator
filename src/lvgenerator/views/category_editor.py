from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.models.category import BoQCategory


class CategoryEditorWidget(QWidget):
    category_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_category: Optional[BoQCategory] = None
        self._updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        group = QGroupBox("Kategorie / Titel")
        form = QFormLayout(group)

        self.rno_edit = QLineEdit()
        self.rno_edit.setPlaceholderText("z.B. 01")
        form.addRow("OZ:", self.rno_edit)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("z.B. Rohbauarbeiten")
        form.addRow("Bezeichnung:", self.label_edit)

        layout.addWidget(group)
        layout.addStretch()

    def _connect_signals(self) -> None:
        self.rno_edit.textChanged.connect(self._on_field_changed)
        self.label_edit.textChanged.connect(self._on_field_changed)

    def set_category(self, cat: Optional[BoQCategory]) -> None:
        self._updating = True
        self._current_category = cat
        if cat is None:
            self.rno_edit.clear()
            self.label_edit.clear()
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.rno_edit.setText(cat.rno_part)
            self.label_edit.setText(cat.label)
        self._updating = False

    def _on_field_changed(self) -> None:
        if self._updating or self._current_category is None:
            return
        self._current_category.rno_part = self.rno_edit.text()
        self._current_category.label = self.label_edit.text()
        self.category_changed.emit()
