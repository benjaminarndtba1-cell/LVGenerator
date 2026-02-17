from copy import deepcopy

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from lvgenerator.constants import GAEBPhase
from lvgenerator.models.boq import BoQBkdn
from lvgenerator.views.oz_mask_dialog import OZMaskDialog, TEMPLATES


# Standard OZ-Maske: 22PPPP
DEFAULT_BREAKDOWNS = [
    BoQBkdn(type="BoQLevel", length=2, numeric=True),
    BoQBkdn(type="Item", length=4, numeric=True),
]


class PhaseSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Leistungsverzeichnis")
        self.setMinimumWidth(450)
        self._breakdowns = deepcopy(DEFAULT_BREAKDOWNS)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Projektname eingeben")
        form.addRow("Projektname:", self.name_edit)

        self.phase_combo = QComboBox()
        for phase in GAEBPhase:
            self.phase_combo.addItem(
                f"{phase.name} - {phase.label_de}", phase
            )
        self.phase_combo.setCurrentIndex(2)  # X83 as default
        form.addRow("Phase:", self.phase_combo)

        layout.addLayout(form)

        # OZ-Maske Abschnitt
        oz_group = QGroupBox("OZ-Maske")
        oz_layout = QVBoxLayout(oz_group)

        self.oz_preview_label = QLabel()
        self._update_oz_preview()
        oz_layout.addWidget(self.oz_preview_label)

        self.oz_template_combo = QComboBox()
        self.oz_template_combo.addItem("22PPPP — Standard")
        for label, _ in TEMPLATES:
            if label != "22PPPP — Standard":
                self.oz_template_combo.addItem(label)
        self.oz_template_combo.currentIndexChanged.connect(
            self._on_oz_template_changed
        )
        oz_layout.addWidget(self.oz_template_combo)

        btn_configure = QPushButton("OZ-Maske anpassen...")
        btn_configure.clicked.connect(self._on_configure_oz)
        oz_layout.addWidget(btn_configure)

        layout.addWidget(oz_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_oz_preview(self) -> None:
        parts = []
        for bkdn in self._breakdowns:
            if bkdn.type == "Index":
                parts.append("A" if not bkdn.numeric else "1")
            elif bkdn.numeric:
                sample = str(1).zfill(bkdn.length)
                parts.append(sample)
            else:
                parts.append("A" * bkdn.length)

        total = sum(b.length for b in self._breakdowns)
        types = " → ".join(
            {"Lot": "Los", "BoQLevel": "LV-Stufe", "Item": "Position",
             "Index": "Index"}.get(b.type, b.type)
            for b in self._breakdowns
        )
        preview = ".".join(parts)
        self.oz_preview_label.setText(
            f"Schema: {preview} ({total} Stellen)\n{types}"
        )

    def _on_oz_template_changed(self, index: int) -> None:
        # Finde die passende Vorlage
        label = self.oz_template_combo.currentText()
        for tmpl_label, tmpl_breakdowns in TEMPLATES:
            if tmpl_label == label:
                self._breakdowns = deepcopy(tmpl_breakdowns)
                self._update_oz_preview()
                return
        # Fallback auf Standard
        self._breakdowns = deepcopy(DEFAULT_BREAKDOWNS)
        self._update_oz_preview()

    def _on_configure_oz(self) -> None:
        dialog = OZMaskDialog(self._breakdowns, self)
        if dialog.exec() == OZMaskDialog.DialogCode.Accepted:
            self._breakdowns = dialog.get_breakdowns()
            self._update_oz_preview()

    def get_phase(self) -> GAEBPhase:
        return self.phase_combo.currentData()

    def get_project_name(self) -> str:
        return self.name_edit.text()

    def get_breakdowns(self) -> list[BoQBkdn]:
        return deepcopy(self._breakdowns)
