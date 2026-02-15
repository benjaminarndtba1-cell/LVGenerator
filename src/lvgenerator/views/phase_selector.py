from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from lvgenerator.constants import GAEBPhase


class PhaseSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Leistungsverzeichnis")
        self.setMinimumWidth(400)

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_phase(self) -> GAEBPhase:
        return self.phase_combo.currentData()

    def get_project_name(self) -> str:
        return self.name_edit.text()
