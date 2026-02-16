import re
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from lvgenerator.models.global_constants import global_constants


class GlobalConstantsDialog(QDialog):
    """Dialog to manage global constants for formula calculations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Globale Konstanten")
        self.setMinimumSize(600, 450)
        self._setup_ui()
        self._load_constants()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Wert", "Beschreibung"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("Hinzufuegen")
        self.btn_add.clicked.connect(self._on_add)
        btn_layout.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Loeschen")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.btn_delete)

        self.btn_reset = QPushButton("Standardwerte")
        self.btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # OK / Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_constants(self) -> None:
        """Populate the table from global_constants."""
        constants = global_constants.get_all_constants()
        self.table.setRowCount(len(constants))
        for row, (name, (value, desc)) in enumerate(sorted(constants.items())):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            value_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 1, value_item)

            desc_item = QTableWidgetItem(desc)
            self.table.setItem(row, 2, desc_item)

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Neue Konstante", "Name (nur Buchstaben, Ziffern, Unterstrich):"
        )
        if not ok or not name.strip():
            return

        name = name.strip().upper()
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', name):
            QMessageBox.warning(
                self, "Ungueltiger Name",
                "Der Name darf nur Grossbuchstaben, Ziffern und "
                "Unterstriche enthalten und muss mit einem Buchstaben "
                "oder Unterstrich beginnen."
            )
            return

        # Check for duplicate
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == name:
                QMessageBox.warning(
                    self, "Name existiert bereits",
                    f"Die Konstante '{name}' existiert bereits."
                )
                return

        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, QTableWidgetItem("0"))
        self.table.setItem(row, 2, QTableWidgetItem(""))

        self.table.selectRow(row)
        self.table.editItem(self.table.item(row, 1))

    def _on_delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Konstante loeschen",
            f"Konstante '{name}' wirklich loeschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.table.removeRow(row)

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self, "Standardwerte wiederherstellen",
            "Alle Konstanten auf die Standardwerte zuruecksetzen?\n"
            "Eigene Konstanten gehen verloren.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            global_constants.reset_defaults()
            self._load_constants()

    def _on_accept(self) -> None:
        """Validate and save all constants."""
        # Validate values
        for row in range(self.table.rowCount()):
            value_text = self.table.item(row, 1).text().strip()
            name = self.table.item(row, 0).text()
            try:
                Decimal(value_text)
            except (InvalidOperation, ValueError):
                QMessageBox.warning(
                    self, "Ungueltiger Wert",
                    f"Der Wert fuer '{name}' ist keine gueltige Zahl: '{value_text}'"
                )
                self.table.selectRow(row)
                return

        # Clear and rebuild constants
        new_constants = {}
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            value = Decimal(self.table.item(row, 1).text().strip())
            desc = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else ""
            new_constants[name] = (value, desc)

        # Apply to global singleton
        global_constants._constants = new_constants
        global_constants.save()

        self.accept()
