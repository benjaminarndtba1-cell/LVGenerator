"""Sidecar file (.lvgmeta.json) for persisting formula metadata alongside GAEB XML files.

GAEB DA XML is a standardized format that does not support custom fields.
Formula data (formula strings, use_calculated_qty flags) is stored in a
separate JSON file next to the GAEB file.
"""
import json
from pathlib import Path
from typing import Optional

from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject


def _sidecar_path(gaeb_path: str) -> Path:
    """Get the sidecar file path for a given GAEB file."""
    p = Path(gaeb_path)
    return p.parent / (p.stem + ".lvgmeta.json")


def save_formula_metadata(project: GAEBProject, gaeb_path: str) -> None:
    """Save formula metadata to a sidecar JSON file.

    Only writes the file if at least one item has a formula.
    """
    if project.boq is None:
        return

    items_data = {}
    _collect_formulas(project.boq.categories, items_data)

    sidecar = _sidecar_path(gaeb_path)
    if not items_data:
        # No formulas — remove stale sidecar if it exists
        if sidecar.exists():
            sidecar.unlink()
        return

    data = {"version": 1, "items": items_data}
    try:
        sidecar.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def load_formula_metadata(project: GAEBProject, gaeb_path: str) -> None:
    """Restore formula metadata from a sidecar JSON file into the project."""
    sidecar = _sidecar_path(gaeb_path)
    if not sidecar.exists():
        return

    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        items_data = data.get("items", {})
    except (OSError, json.JSONDecodeError, KeyError):
        return

    if project.boq is None:
        return

    _apply_formulas(project.boq.categories, items_data)


def _collect_formulas(categories: list[BoQCategory], out: dict) -> None:
    """Recursively collect formula data from all items."""
    for cat in categories:
        for item in cat.items:
            if item.formula or item.use_calculated_qty:
                out[item.id] = {
                    "formula": item.formula,
                    "use_calculated_qty": item.use_calculated_qty,
                }
        _collect_formulas(cat.subcategories, out)


def _apply_formulas(categories: list[BoQCategory], items_data: dict) -> None:
    """Recursively apply formula data to items."""
    for cat in categories:
        for item in cat.items:
            if item.id in items_data:
                entry = items_data[item.id]
                item.formula = entry.get("formula", "")
                item.use_calculated_qty = entry.get("use_calculated_qty", False)
        _apply_formulas(cat.subcategories, items_data)
