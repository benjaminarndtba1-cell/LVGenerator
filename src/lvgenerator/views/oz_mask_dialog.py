from copy import deepcopy
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
)

from lvgenerator.models.boq import BoQBkdn
from lvgenerator.resources import theme


# Vordefinierte Vorlagen
TEMPLATES: list[tuple[str, list[BoQBkdn]]] = [
    ("22PPPP — Standard", [
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
    ]),
    ("22PPPPI — Standard mit Index", [
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
        BoQBkdn(type="Index", length=1, numeric=False),
    ]),
    ("1122PPPP — Zwei Kategorieebenen", [
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
    ]),
    ("1122PPPPI — Zwei Kategorieebenen mit Index", [
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
        BoQBkdn(type="Index", length=1, numeric=False),
    ]),
    ("LL1122PPPP — Mit Los", [
        BoQBkdn(type="Lot", length=2, numeric=True, label="Los"),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
    ]),
    ("112233PPPP — Drei Kategorieebenen", [
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="BoQLevel", length=2, numeric=True),
        BoQBkdn(type="Item", length=4, numeric=True),
    ]),
]

TYPE_LABELS = {
    "Lot": "Los",
    "BoQLevel": "LV-Stufe",
    "Item": "Position",
    "Index": "Index",
}
TYPE_VALUES = list(TYPE_LABELS.keys())

ALIGNMENT_LABELS = {
    "": "—",
    "left": "Links",
    "right": "Rechts",
}
ALIGNMENT_VALUES = list(ALIGNMENT_LABELS.keys())

MAX_OZ_LENGTH = 14


class OZMaskDialog(QDialog):
    """Dialog zur Konfiguration der Ordnungsziffernmaske (OZ-Maske)."""

    def __init__(self, breakdowns: list[BoQBkdn], parent=None):
        super().__init__(parent)
        self.setWindowTitle("OZ-Maske konfigurieren")
        self.setMinimumSize(750, 500)
        self._breakdowns = deepcopy(breakdowns)
        self._setup_ui()
        self._load_breakdowns()
        self._update_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Vorlagen
        tmpl_layout = QHBoxLayout()
        tmpl_layout.addWidget(QLabel("Vorlage:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("— Vorlage wählen —")
        for label, _ in TEMPLATES:
            self.template_combo.addItem(label)
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        tmpl_layout.addWidget(self.template_combo, 1)
        layout.addLayout(tmpl_layout)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Typ", "Bezeichnung", "Länge", "Numerisch", "Ausrichtung"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("Ebene hinzufügen")
        self.btn_add.clicked.connect(self._on_add)
        btn_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("Ebene entfernen")
        self.btn_remove.clicked.connect(self._on_remove)
        btn_layout.addWidget(self.btn_remove)

        self.btn_up = QPushButton("Nach oben")
        self.btn_up.clicked.connect(self._on_move_up)
        btn_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("Nach unten")
        self.btn_down.clicked.connect(self._on_move_down)
        btn_layout.addWidget(self.btn_down)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Vorschau + Stellenzähler
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Vorschau:"))
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #d4d4d4;")
        preview_layout.addWidget(self.preview_label, 1)

        self.length_label = QLabel("")
        preview_layout.addWidget(self.length_label)
        layout.addLayout(preview_layout)

        # OK / Abbrechen
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_breakdowns(self) -> None:
        self.table.setRowCount(0)
        for bkdn in self._breakdowns:
            self._add_row(bkdn)

    def _add_row(self, bkdn: BoQBkdn) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Typ ComboBox
        type_combo = QComboBox()
        for val in TYPE_VALUES:
            type_combo.addItem(TYPE_LABELS[val], val)
        idx = TYPE_VALUES.index(bkdn.type) if bkdn.type in TYPE_VALUES else 1
        type_combo.setCurrentIndex(idx)
        type_combo.currentIndexChanged.connect(self._update_preview)
        self.table.setCellWidget(row, 0, type_combo)

        # Bezeichnung
        from PySide6.QtWidgets import QLineEdit
        label_edit = QLineEdit(bkdn.label)
        label_edit.setPlaceholderText("z.B. Titel, Abschnitt...")
        self.table.setCellWidget(row, 1, label_edit)

        # Länge SpinBox
        length_spin = QSpinBox()
        length_spin.setMinimum(1)
        length_spin.setMaximum(14)
        length_spin.setValue(bkdn.length)
        length_spin.valueChanged.connect(self._update_preview)
        self.table.setCellWidget(row, 2, length_spin)

        # Numerisch CheckBox
        num_check = QCheckBox()
        num_check.setChecked(bkdn.numeric)
        # Zentrieren
        from PySide6.QtWidgets import QWidget
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.addWidget(num_check)
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 3, container)

        # Ausrichtung ComboBox
        align_combo = QComboBox()
        for val in ALIGNMENT_VALUES:
            align_combo.addItem(ALIGNMENT_LABELS[val], val)
        if bkdn.alignment and bkdn.alignment in ALIGNMENT_VALUES:
            align_combo.setCurrentIndex(ALIGNMENT_VALUES.index(bkdn.alignment))
        else:
            align_combo.setCurrentIndex(0)
        self.table.setCellWidget(row, 4, align_combo)

    def _read_rows(self) -> list[BoQBkdn]:
        result = []
        for row in range(self.table.rowCount()):
            type_combo: QComboBox = self.table.cellWidget(row, 0)
            label_edit = self.table.cellWidget(row, 1)
            length_spin: QSpinBox = self.table.cellWidget(row, 2)
            num_container = self.table.cellWidget(row, 3)
            num_check: QCheckBox = num_container.findChild(QCheckBox)
            align_combo: QComboBox = self.table.cellWidget(row, 4)

            bkdn = BoQBkdn(
                type=type_combo.currentData(),
                length=length_spin.value(),
                numeric=num_check.isChecked(),
                label=label_edit.text().strip(),
                alignment=align_combo.currentData() or None,
            )
            result.append(bkdn)
        return result

    def _on_template_selected(self, index: int) -> None:
        if index <= 0:
            return
        _, breakdowns = TEMPLATES[index - 1]
        self._breakdowns = deepcopy(breakdowns)
        self._load_breakdowns()
        self._update_preview()
        self.template_combo.setCurrentIndex(0)

    def _on_add(self) -> None:
        new_bkdn = BoQBkdn(type="BoQLevel", length=2, numeric=True)
        self._add_row(new_bkdn)
        self._update_preview()

    def _on_remove(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        self._update_preview()

    def _on_move_up(self) -> None:
        row = self.table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self.table.selectRow(row - 1)
        self._update_preview()

    def _on_move_down(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self.table.selectRow(row + 1)
        self._update_preview()

    def _swap_rows(self, row_a: int, row_b: int) -> None:
        breakdowns = self._read_rows()
        breakdowns[row_a], breakdowns[row_b] = breakdowns[row_b], breakdowns[row_a]
        self._breakdowns = breakdowns
        self._load_breakdowns()

    def _update_preview(self) -> None:
        breakdowns = self._read_rows()
        total_length = sum(b.length for b in breakdowns)

        # Vorschau erzeugen
        parts = []
        for bkdn in breakdowns:
            if bkdn.type == "Lot":
                sample = "01" if bkdn.numeric else "A" * min(bkdn.length, 2)
                parts.append(sample.zfill(bkdn.length) if bkdn.numeric else sample.ljust(bkdn.length, "x"))
            elif bkdn.type == "BoQLevel":
                sample = str(1).zfill(bkdn.length) if bkdn.numeric else "A" * bkdn.length
                parts.append(sample)
            elif bkdn.type == "Item":
                sample = str(10).zfill(bkdn.length) if bkdn.numeric else "a" * bkdn.length
                parts.append(sample)
            elif bkdn.type == "Index":
                parts.append("A" if not bkdn.numeric else "1")

        preview = ".".join(parts) if parts else "—"
        self.preview_label.setText(preview)

        color = theme.HTML_SUCCESS if total_length <= MAX_OZ_LENGTH else theme.HTML_ERROR
        self.length_label.setText(
            f'<span style="color:{color};">{total_length} / {MAX_OZ_LENGTH} Stellen</span>'
        )

    def _validate(self) -> Optional[str]:
        breakdowns = self._read_rows()

        if not breakdowns:
            return "Mindestens eine Ebene muss definiert sein."

        # Item genau einmal
        item_count = sum(1 for b in breakdowns if b.type == "Item")
        if item_count == 0:
            return "Es muss genau eine Ebene vom Typ 'Position' vorhanden sein."
        if item_count > 1:
            return "Es darf nur eine Ebene vom Typ 'Position' geben."

        # Lot Regeln
        lot_count = sum(1 for b in breakdowns if b.type == "Lot")
        if lot_count > 1:
            return "Es darf maximal ein Los ('Lot') geben."
        if lot_count == 1 and breakdowns[0].type != "Lot":
            return "Das Los muss die erste Ebene sein."

        # Index Regeln
        index_count = sum(1 for b in breakdowns if b.type == "Index")
        if index_count > 1:
            return "Es darf maximal einen Index geben."
        if index_count == 1:
            if breakdowns[-1].type != "Index":
                return "Der Index muss die letzte Ebene sein."
            if breakdowns[-1].length != 1:
                return "Der Index muss genau 1 Stelle lang sein."

        # Reihenfolge prüfen: Lot → BoQLevel(s) → Item → Index
        order = {"Lot": 0, "BoQLevel": 1, "Item": 2, "Index": 3}
        last_order = -1
        for b in breakdowns:
            current = order.get(b.type, 1)
            # BoQLevel darf mehrfach vorkommen
            if b.type == "BoQLevel":
                if current < last_order and last_order > 1:
                    return "LV-Stufen müssen vor der Position stehen."
            else:
                if current < last_order:
                    return (
                        "Die Reihenfolge muss sein: "
                        "Los → LV-Stufe(n) → Position → Index"
                    )
                last_order = current

        # Gesamtlänge
        total = sum(b.length for b in breakdowns)
        if total > MAX_OZ_LENGTH:
            return (
                f"Die Gesamtlänge ({total} Stellen) überschreitet "
                f"das Maximum von {MAX_OZ_LENGTH} Stellen."
            )

        # Max 5 Hierarchiestufen (Lot + BoQLevel)
        hierarchy_count = sum(
            1 for b in breakdowns if b.type in ("Lot", "BoQLevel")
        )
        if hierarchy_count > 5:
            return "Maximal 5 Hierarchiestufen (Los + LV-Stufen) erlaubt."

        return None

    def _on_accept(self) -> None:
        error = self._validate()
        if error:
            QMessageBox.warning(self, "Ungültige OZ-Maske", error)
            return
        self._breakdowns = self._read_rows()
        self.accept()

    def get_breakdowns(self) -> list[BoQBkdn]:
        return deepcopy(self._breakdowns)
