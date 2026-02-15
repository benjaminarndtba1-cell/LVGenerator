from pathlib import Path

from PySide6.QtCore import QSettings


MAX_RECENT_FILES = 10


class RecentFilesManager:
    """Verwaltet die Liste der zuletzt geoeffneten Dateien."""

    SETTINGS_KEY = "recent_files"

    def __init__(self):
        self._settings = QSettings()

    def get_recent_files(self) -> list[str]:
        """Gibt die Liste der zuletzt geoeffneten Dateien zurueck."""
        files = self._settings.value(self.SETTINGS_KEY, [])
        if isinstance(files, str):
            files = [files] if files else []
        return [f for f in files if Path(f).exists()][:MAX_RECENT_FILES]

    def add_file(self, file_path: str) -> None:
        """Fuegt eine Datei an erster Stelle hinzu."""
        abs_path = str(Path(file_path).resolve())
        files = self.get_recent_files()
        files = [f for f in files if f != abs_path]
        files.insert(0, abs_path)
        files = files[:MAX_RECENT_FILES]
        self._settings.setValue(self.SETTINGS_KEY, files)

    def clear(self) -> None:
        """Leert die Liste."""
        self._settings.setValue(self.SETTINGS_KEY, [])
