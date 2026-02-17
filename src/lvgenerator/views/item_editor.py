from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.commands.item_commands import (
    EditItemDescriptionCommand,
    EditItemPropertyCommand,
)
from lvgenerator.constants import GAEBPhase
from lvgenerator.models.formula_evaluator import evaluate_formula
from lvgenerator.models.item import Item
from lvgenerator.resources import theme
from lvgenerator.validators import ItemValidator


class ItemEditorWidget(QWidget):
    item_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_item: Optional[Item] = None
        self._updating = False
        self._undo_stack: Optional[QUndoStack] = None
        self._phase: Optional[GAEBPhase] = None
        self._validator = ItemValidator()
        self._setup_ui()
        self._connect_signals()

    def set_undo_stack(self, stack: QUndoStack) -> None:
        self._undo_stack = stack

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Position info
        pos_group = QGroupBox("Position")
        pos_layout = QFormLayout(pos_group)

        self.rno_edit = QLineEdit()
        self.rno_edit.setPlaceholderText("z.B. 0010")
        pos_layout.addRow("OZ:", self.rno_edit)

        self.outline_edit = QPlainTextEdit()
        self.outline_edit.setMaximumHeight(80)
        self.outline_edit.setPlaceholderText("Kurztext der Position")
        pos_layout.addRow("Kurztext:", self.outline_edit)

        self.detail_edit = QPlainTextEdit()
        self.detail_edit.setMaximumHeight(200)
        self.detail_edit.setPlaceholderText("Detaillierter Langtext")
        pos_layout.addRow("Langtext:", self.detail_edit)

        layout.addWidget(pos_group)

        # Quantities & formula
        qty_group = QGroupBox("Mengen & Preise")
        qty_layout = QFormLayout(qty_group)

        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("0.000")
        qty_layout.addRow("Menge:", self.qty_edit)

        # Formula row with result preview
        formula_container = QWidget()
        formula_h_layout = QHBoxLayout(formula_container)
        formula_h_layout.setContentsMargins(0, 0, 0, 0)

        self.formula_edit = QLineEdit()
        self.formula_edit.setPlaceholderText(
            "z.B. 2 * PI * 5 + AUFRUNDEN(3.14, 1)"
        )
        formula_h_layout.addWidget(self.formula_edit, stretch=3)

        self.formula_result_label = QLabel("")
        self.formula_result_label.setMinimumWidth(120)
        formula_h_layout.addWidget(self.formula_result_label, stretch=1)

        qty_layout.addRow("Formel:", formula_container)

        self.use_calculated_check = QCheckBox("Menge aus Formel berechnen")
        qty_layout.addRow("", self.use_calculated_check)

        self.qu_edit = QLineEdit()
        self.qu_edit.setPlaceholderText("z.B. m2, Stk, psch")
        self.qu_edit.setMaximumWidth(100)
        qty_layout.addRow("Einheit:", self.qu_edit)

        self.up_edit = QLineEdit()
        self.up_edit.setPlaceholderText("0.00")
        qty_layout.addRow("Einheitspreis:", self.up_edit)

        self.total_label = QLabel("--")
        qty_layout.addRow("Gesamtbetrag:", self.total_label)

        self.qty_tbd_check = QCheckBox("Menge noch offen")
        qty_layout.addRow("", self.qty_tbd_check)

        layout.addWidget(qty_group)
        layout.addStretch()

    def _connect_signals(self) -> None:
        self.rno_edit.textChanged.connect(self._on_field_changed)
        self.outline_edit.textChanged.connect(self._on_field_changed)
        self.detail_edit.textChanged.connect(self._on_field_changed)
        self.qty_edit.textChanged.connect(self._on_field_changed)
        self.qu_edit.textChanged.connect(self._on_field_changed)
        self.up_edit.textChanged.connect(self._on_field_changed)
        self.qty_tbd_check.toggled.connect(self._on_field_changed)
        self.formula_edit.textChanged.connect(self._on_formula_changed)
        self.use_calculated_check.toggled.connect(self._on_calculation_mode_changed)

    def set_item(self, item: Optional[Item]) -> None:
        self._updating = True
        self._current_item = item
        if item is None:
            self._clear_fields()
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.rno_edit.setText(item.rno_part)
            self.outline_edit.setPlainText(item.description.outline_text)
            self.detail_edit.setPlainText(item.description.detail_text)
            self.qty_edit.setText(str(item.qty) if item.qty is not None else "")
            self.qu_edit.setText(item.qu)
            self.up_edit.setText(str(item.up) if item.up is not None else "")
            self.qty_tbd_check.setChecked(item.qty_tbd)
            self.formula_edit.setText(item.formula)
            self.use_calculated_check.setChecked(item.use_calculated_qty)
            self._update_calculation_mode()
            self._update_formula_result()
            self._update_total()
        self._updating = False

    def set_phase(self, phase: GAEBPhase) -> None:
        self._phase = phase

    def set_price_visible(self, visible: bool) -> None:
        self.up_edit.setVisible(visible)
        self.total_label.setVisible(visible)
        # Find the labels in the form layout and hide them too
        parent_layout = self.up_edit.parentWidget().layout()
        if isinstance(parent_layout, QFormLayout):
            for i in range(parent_layout.rowCount()):
                item = parent_layout.itemAt(i, QFormLayout.FieldRole)
                label = parent_layout.itemAt(i, QFormLayout.LabelRole)
                if item and item.widget() in (self.up_edit, self.total_label):
                    if label and label.widget():
                        label.widget().setVisible(visible)

    def refresh_formula(self) -> None:
        """Refresh formula result, e.g. after global constants changed."""
        self._update_formula_result()
        self._update_total()

    def _clear_fields(self) -> None:
        self.rno_edit.clear()
        self.outline_edit.clear()
        self.detail_edit.clear()
        self.qty_edit.clear()
        self.qu_edit.clear()
        self.up_edit.clear()
        self.total_label.setText("--")
        self.qty_tbd_check.setChecked(False)
        self.formula_edit.clear()
        self.use_calculated_check.setChecked(False)
        self.formula_result_label.setText("")
        self.formula_result_label.setStyleSheet(theme.CLEAR_STYLE)
        self._update_calculation_mode()

    def _push_item_command(self, prop: str, old_val, new_val) -> None:
        if self._undo_stack is None:
            setattr(self._current_item, prop, new_val)
        else:
            cmd = EditItemPropertyCommand(
                self._current_item, prop, old_val, new_val
            )
            self._updating = True
            self._undo_stack.push(cmd)
            self._updating = False

    def _push_desc_command(self, field: str, old_val: str, new_val: str) -> None:
        if self._undo_stack is None:
            setattr(self._current_item.description, field, new_val)
        else:
            cmd = EditItemDescriptionCommand(
                self._current_item.description, field, old_val, new_val
            )
            self._updating = True
            self._undo_stack.push(cmd)
            self._updating = False

    def _on_field_changed(self) -> None:
        if self._updating or self._current_item is None:
            return
        item = self._current_item

        # String properties
        new_rno = self.rno_edit.text()
        if new_rno != item.rno_part:
            self._push_item_command("rno_part", item.rno_part, new_rno)

        new_qu = self.qu_edit.text()
        if new_qu != item.qu:
            self._push_item_command("qu", item.qu, new_qu)

        new_qty_tbd = self.qty_tbd_check.isChecked()
        if new_qty_tbd != item.qty_tbd:
            self._push_item_command("qty_tbd", item.qty_tbd, new_qty_tbd)

        # Description fields
        new_outline = self.outline_edit.toPlainText()
        if new_outline != item.description.outline_text:
            self._push_desc_command(
                "outline_text", item.description.outline_text, new_outline
            )

        new_detail = self.detail_edit.toPlainText()
        if new_detail != item.description.detail_text:
            self._push_desc_command(
                "detail_text", item.description.detail_text, new_detail
            )

        # Decimal properties
        try:
            new_qty = Decimal(self.qty_edit.text()) if self.qty_edit.text() else None
        except InvalidOperation:
            new_qty = None
        if new_qty != item.qty:
            self._push_item_command("qty", item.qty, new_qty)

        try:
            new_up = Decimal(self.up_edit.text()) if self.up_edit.text() else None
        except InvalidOperation:
            new_up = None
        if new_up != item.up:
            self._push_item_command("up", item.up, new_up)

        self._update_total()
        self._validate()
        self.item_changed.emit()

    def _on_formula_changed(self) -> None:
        """Handle formula text changes: update model and result preview."""
        if self._updating or self._current_item is None:
            return

        new_formula = self.formula_edit.text()
        if new_formula != self._current_item.formula:
            self._push_item_command("formula", self._current_item.formula, new_formula)

        self._update_formula_result()
        self._update_total()
        self._validate()
        self.item_changed.emit()

    def _update_formula_result(self) -> None:
        """Evaluate the current formula and show result/error."""
        formula_text = self.formula_edit.text().strip()
        if not formula_text:
            self.formula_result_label.setText("")
            self.formula_result_label.setStyleSheet(theme.CLEAR_STYLE)
            self.formula_result_label.setToolTip("")
            self.formula_edit.setStyleSheet(theme.CLEAR_STYLE)
            return

        result, error = evaluate_formula(formula_text)
        if error:
            self.formula_result_label.setText("Fehler")
            self.formula_result_label.setStyleSheet(theme.ERROR_TEXT)
            self.formula_result_label.setToolTip(error)
            self.formula_edit.setStyleSheet(theme.ERROR_BORDER)
        elif result is not None:
            display = str(result.quantize(Decimal("0.001")))
            self.formula_result_label.setText(f"= {display}")
            self.formula_result_label.setStyleSheet(theme.SUCCESS_TEXT)
            self.formula_result_label.setToolTip("Berechnetes Ergebnis")
            self.formula_edit.setStyleSheet(theme.SUCCESS_BORDER)

            # If formula mode active, update the qty display
            if self.use_calculated_check.isChecked():
                self._updating = True
                self.qty_edit.setText(display)
                self._updating = False
        else:
            self.formula_result_label.setText("")
            self.formula_result_label.setStyleSheet(theme.CLEAR_STYLE)
            self.formula_result_label.setToolTip("")
            self.formula_edit.setStyleSheet(theme.CLEAR_STYLE)

    def _validate(self) -> None:
        if self._current_item is None or self._phase is None:
            return
        result = self._validator.validate(self._current_item, self._phase)
        field_map = {
            "rno_part": self.rno_edit,
            "qty": self.qty_edit,
            "qu": self.qu_edit,
            "up": self.up_edit,
        }
        for field_name, widget in field_map.items():
            errors = result.get_field_errors(field_name)
            if not errors:
                widget.setStyleSheet(theme.CLEAR_STYLE)
                widget.setToolTip("")
            elif errors[0].severity == "error":
                widget.setStyleSheet(theme.ERROR_BORDER)
                widget.setToolTip(errors[0].message)
            else:
                widget.setStyleSheet(theme.WARNING_BORDER)
                widget.setToolTip(errors[0].message)

        # Formula field validation
        formula_errors = result.get_field_errors("formula")
        if formula_errors:
            err = formula_errors[0]
            if err.severity == "error":
                self.formula_edit.setStyleSheet(theme.ERROR_BORDER)
            else:
                self.formula_edit.setStyleSheet(theme.WARNING_BORDER)
            self.formula_edit.setToolTip(err.message)

    def _update_total(self) -> None:
        if self._current_item:
            effective_qty = self._current_item.get_effective_qty()
            if effective_qty is not None and self._current_item.up is not None:
                total = (effective_qty * self._current_item.up).quantize(Decimal("0.01"))
                self.total_label.setText(str(total))
            else:
                self.total_label.setText("--")
        else:
            self.total_label.setText("--")

    def _update_calculation_mode(self) -> None:
        """Update UI based on calculation mode."""
        use_calculated = self.use_calculated_check.isChecked()
        self.qty_edit.setReadOnly(use_calculated)
        self.formula_edit.setEnabled(True)

        if use_calculated:
            self.qty_edit.setStyleSheet(theme.READONLY_BG)
            self._update_formula_result()
        else:
            self.qty_edit.setStyleSheet(theme.CLEAR_STYLE)

    def _on_calculation_mode_changed(self) -> None:
        """Handle change in calculation mode."""
        if self._updating or self._current_item is None:
            return

        new_use_calculated = self.use_calculated_check.isChecked()
        if new_use_calculated != self._current_item.use_calculated_qty:
            self._push_item_command(
                "use_calculated_qty",
                self._current_item.use_calculated_qty,
                new_use_calculated,
            )

        self._update_calculation_mode()
        self._update_total()
        self._validate()
        self.item_changed.emit()
