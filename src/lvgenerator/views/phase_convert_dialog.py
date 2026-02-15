from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_converter import PhaseConverter


class PhaseConvertDialog(QDialog):
    """Dialog for converting between GAEB phases."""

    def __init__(
        self,
        current_phase: GAEBPhase,
        converter: PhaseConverter,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Phase konvertieren")
        self.setMinimumWidth(400)
        self._current_phase = current_phase
        self._converter = converter
        self._target_phase: Optional[GAEBPhase] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        current_label = QLabel(
            f"{self._current_phase.name} - {self._current_phase.label_de}"
        )
        form.addRow("Aktuelle Phase:", current_label)

        self._phase_combo = QComboBox()
        for phase in GAEBPhase:
            if phase != self._current_phase:
                self._phase_combo.addItem(
                    f"{phase.name} - {phase.label_de}", phase
                )
        form.addRow("Zielphase:", self._phase_combo)

        layout.addLayout(form)

        # Warnings area
        self._warnings_label = QLabel("Hinweise zur Konvertierung:")
        layout.addWidget(self._warnings_label)

        self._warnings_text = QTextEdit()
        self._warnings_text.setReadOnly(True)
        self._warnings_text.setMaximumHeight(120)
        layout.addWidget(self._warnings_text)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        # Connect combo change to update warnings
        self._phase_combo.currentIndexChanged.connect(self._update_warnings)
        self._update_warnings()

    def _update_warnings(self) -> None:
        target = self._phase_combo.currentData()
        if target is None:
            self._warnings_text.clear()
            return

        warnings = self._converter.get_conversion_warnings_preview(
            self._current_phase, target
        )
        if warnings:
            self._warnings_text.setPlainText("\n".join(f"• {w}" for w in warnings))
        else:
            self._warnings_text.setPlainText("Keine Datenverluste erwartet.")

    def get_target_phase(self) -> Optional[GAEBPhase]:
        return self._phase_combo.currentData()
