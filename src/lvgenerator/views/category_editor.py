from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.commands.category_commands import EditCategoryPropertyCommand
from lvgenerator.models.category import BoQCategory
from lvgenerator.validators import CategoryValidator


class CategoryEditorWidget(QWidget):
    category_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_category: Optional[BoQCategory] = None
        self._updating = False
        self._undo_stack: Optional[QUndoStack] = None
        self._validator = CategoryValidator()
        self._setup_ui()
        self._connect_signals()

    def set_undo_stack(self, stack: QUndoStack) -> None:
        self._undo_stack = stack

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

        self.total_label = QLabel("--")
        form.addRow("Summe:", self.total_label)

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
            self.total_label.setText("--")
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.rno_edit.setText(cat.rno_part)
            self.label_edit.setText(cat.label)
            total = cat.calculate_total()
            self.total_label.setText(str(total) if total is not None else "--")
        self._updating = False

    def _push_command(self, prop: str, old_val, new_val) -> None:
        if self._undo_stack is None:
            setattr(self._current_category, prop, new_val)
        else:
            cmd = EditCategoryPropertyCommand(
                self._current_category, prop, old_val, new_val
            )
            self._updating = True
            self._undo_stack.push(cmd)
            self._updating = False

    def _on_field_changed(self) -> None:
        if self._updating or self._current_category is None:
            return
        cat = self._current_category

        new_rno = self.rno_edit.text()
        if new_rno != cat.rno_part:
            self._push_command("rno_part", cat.rno_part, new_rno)

        new_label = self.label_edit.text()
        if new_label != cat.label:
            self._push_command("label", cat.label, new_label)

        self._validate()
        self.category_changed.emit()

    def _validate(self) -> None:
        if self._current_category is None:
            return
        result = self._validator.validate(self._current_category)
        field_map = {"rno_part": self.rno_edit, "label": self.label_edit}
        for field_name, widget in field_map.items():
            errors = result.get_field_errors(field_name)
            if not errors:
                widget.setStyleSheet("")
                widget.setToolTip("")
            elif errors[0].severity == "error":
                widget.setStyleSheet("border: 2px solid red;")
                widget.setToolTip(errors[0].message)
            else:
                widget.setStyleSheet("border: 2px solid orange;")
                widget.setToolTip(errors[0].message)
