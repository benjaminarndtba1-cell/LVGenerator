import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Dict, Tuple

from PySide6.QtCore import QStandardPaths


# Type: name -> (value, description)
ConstantsDict = Dict[str, Tuple[Decimal, str]]


def _default_constants() -> ConstantsDict:
    """Built-in constants for construction calculations."""
    return {
        "PI": (Decimal(str(math.pi)), "Kreiszahl"),
        "E": (Decimal(str(math.e)), "Eulersche Zahl"),
        "DICHTE_BETON": (Decimal("2.4"), "Dichte Beton [t/m3]"),
        "DICHTE_STAHLBETON": (Decimal("2.5"), "Dichte Stahlbeton [t/m3]"),
        "DICHTE_STAHL": (Decimal("7.85"), "Dichte Stahl [t/m3]"),
        "DICHTE_HOLZ": (Decimal("0.5"), "Dichte Holz (Nadelholz) [t/m3]"),
        "DICHTE_WASSER": (Decimal("1.0"), "Dichte Wasser [t/m3]"),
        "DICHTE_MAUERWERK": (Decimal("1.8"), "Dichte Mauerwerk [t/m3]"),
        "DICHTE_GLAS": (Decimal("2.5"), "Dichte Glas [t/m3]"),
        "DICHTE_ALUMINIUM": (Decimal("2.7"), "Dichte Aluminium [t/m3]"),
        "DICHTE_KUPFER": (Decimal("8.92"), "Dichte Kupfer [t/m3]"),
        "DICHTE_ERDE": (Decimal("1.8"), "Dichte Erde (gewachsen) [t/m3]"),
        "DICHTE_KIES": (Decimal("1.8"), "Dichte Kies [t/m3]"),
        "DICHTE_SAND": (Decimal("1.6"), "Dichte Sand [t/m3]"),
        "DICHTE_ASPHALT": (Decimal("2.4"), "Dichte Asphalt [t/m3]"),
    }


class GlobalConstants:
    """Manages global constants for formula calculations.

    Constants are stored as (value, description) tuples, keyed by uppercase name.
    Persistence uses a JSON file in the application data directory.
    """

    def __init__(self):
        self._constants: ConstantsDict = _default_constants()
        self._settings_path: Path = self._get_settings_path()
        self.load()

    @staticmethod
    def _get_settings_path() -> Path:
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        path = Path(app_data) / "LVGenerator"
        path.mkdir(parents=True, exist_ok=True)
        return path / "global_constants.json"

    def get_constant(self, name: str) -> Tuple[Decimal, str]:
        """Get a constant (value, description) by name."""
        return self._constants.get(name.upper(), (Decimal(0), ""))

    def get_value(self, name: str) -> Decimal:
        """Get just the value of a constant."""
        return self._constants.get(name.upper(), (Decimal(0), ""))[0]

    def set_constant(self, name: str, value: Decimal, description: str = "") -> None:
        """Set a constant with value and description."""
        self._constants[name.upper()] = (value, description)

    def remove_constant(self, name: str) -> None:
        """Remove a constant."""
        self._constants.pop(name.upper(), None)

    def get_all_constants(self) -> ConstantsDict:
        """Get all constants as a copy."""
        return self._constants.copy()

    def reset_defaults(self) -> None:
        """Reset to built-in default constants."""
        self._constants = _default_constants()

    def save(self) -> None:
        """Persist constants to JSON file."""
        data = {}
        for name, (value, desc) in self._constants.items():
            data[name] = {"value": str(value), "description": desc}
        try:
            self._settings_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def load(self) -> None:
        """Load constants from JSON file, falling back to defaults."""
        if not self._settings_path.exists():
            return
        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
            self._constants = {}
            for name, entry in data.items():
                value = Decimal(entry["value"])
                desc = entry.get("description", "")
                self._constants[name.upper()] = (value, desc)
        except (OSError, json.JSONDecodeError, KeyError, Exception):
            self._constants = _default_constants()


# Global singleton instance
global_constants = GlobalConstants()
