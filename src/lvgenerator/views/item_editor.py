from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.models.item import Item


class ItemEditorWidget(QWidget):
    item_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_item: Optional[Item] = None
        self._updating = False
        self._setup_ui()
        self._connect_signals()

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

        # Quantities
        qty_group = QGroupBox("Mengen & Preise")
        qty_layout = QFormLayout(qty_group)

        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("0.000")
        qty_layout.addRow("Menge:", self.qty_edit)

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
            self._update_total()
        self._updating = False

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

    def _clear_fields(self) -> None:
        self.rno_edit.clear()
        self.outline_edit.clear()
        self.detail_edit.clear()
        self.qty_edit.clear()
        self.qu_edit.clear()
        self.up_edit.clear()
        self.total_label.setText("--")
        self.qty_tbd_check.setChecked(False)

    def _on_field_changed(self) -> None:
        if self._updating or self._current_item is None:
            return
        item = self._current_item
        item.rno_part = self.rno_edit.text()
        item.description.outline_text = self.outline_edit.toPlainText()
        item.description.detail_text = self.detail_edit.toPlainText()
        item.qu = self.qu_edit.text()
        item.qty_tbd = self.qty_tbd_check.isChecked()

        try:
            item.qty = Decimal(self.qty_edit.text()) if self.qty_edit.text() else None
        except InvalidOperation:
            item.qty = None

        try:
            item.up = Decimal(self.up_edit.text()) if self.up_edit.text() else None
        except InvalidOperation:
            item.up = None

        self._update_total()
        self.item_changed.emit()

    def _update_total(self) -> None:
        if self._current_item:
            total = self._current_item.calculate_total()
            self.total_label.setText(str(total) if total is not None else "--")
        else:
            self.total_label.setText("--")
