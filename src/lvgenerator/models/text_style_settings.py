import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass
class TextStyleSettings:
    font_family: str = "Arial"
    font_size_pt: int = 10


class TextStyleSettingsManager:
    """Manages global text style defaults. Singleton with JSON persistence."""

    def __init__(self):
        self._settings = TextStyleSettings()
        self._settings_path = self._get_settings_path()
        self.load()

    @staticmethod
    def _get_settings_path() -> Path:
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        path = Path(app_data) / "LVGenerator"
        path.mkdir(parents=True, exist_ok=True)
        return path / "text_style.json"

    def get_settings(self) -> TextStyleSettings:
        return self._settings

    def update_settings(self, font_family: str, font_size_pt: int) -> None:
        self._settings.font_family = font_family
        self._settings.font_size_pt = font_size_pt
        self.save()

    def get_default_body_style(self) -> str:
        """Return CSS for QTextEdit body element."""
        return (
            f"font-family:'{self._settings.font_family}'; "
            f"font-size:{self._settings.font_size_pt}pt"
        )

    def save(self) -> None:
        data = {
            "font_family": self._settings.font_family,
            "font_size_pt": self._settings.font_size_pt,
        }
        try:
            self._settings_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def load(self) -> None:
        if not self._settings_path.exists():
            return
        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            self._settings.font_family = data.get("font_family", "Arial")
            self._settings.font_size_pt = data.get("font_size_pt", 10)
        except (OSError, json.JSONDecodeError):
            self._settings = TextStyleSettings()


# Global singleton
text_style_settings = TextStyleSettingsManager()
