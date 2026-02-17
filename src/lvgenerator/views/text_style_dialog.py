from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from lvgenerator.models.text_style_settings import text_style_settings


class TextStyleDialog(QDialog):
    """Dialog fuer globale Textstil-Einstellungen (Schriftart, Groesse)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Textstil-Einstellungen")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.font_combo = QFontComboBox()
        form.addRow("Schriftart:", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 72)
        self.size_spin.setSuffix(" pt")
        form.addRow("Schriftgroesse:", self.size_spin)

        layout.addLayout(form)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setMinimumHeight(60)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "border: 1px solid #555; padding: 8px; background: #1e1e1e;"
        )
        layout.addWidget(self.preview_label)

        # Connect for live preview
        self.font_combo.currentFontChanged.connect(self._update_preview)
        self.size_spin.valueChanged.connect(self._update_preview)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self) -> None:
        settings = text_style_settings.get_settings()
        self.font_combo.setCurrentFont(QFont(settings.font_family))
        self.size_spin.setValue(settings.font_size_pt)
        self._update_preview()

    def _update_preview(self) -> None:
        family = self.font_combo.currentFont().family()
        size = self.size_spin.value()
        self.preview_label.setFont(QFont(family, size))
        self.preview_label.setText(
            f"Vorschau: {family}, {size}pt\n"
            f"Boden loesen und seitlich lagern. Bodenklasse 3-5."
        )

    def _on_accept(self) -> None:
        family = self.font_combo.currentFont().family()
        size = self.size_spin.value()
        text_style_settings.update_settings(family, size)
        self.accept()
