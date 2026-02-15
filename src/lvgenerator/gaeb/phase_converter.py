from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_rules import PhaseRules, get_rules
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject


@dataclass
class PhaseConversionResult:
    """Result of a phase conversion with warnings."""

    project: GAEBProject
    warnings: list[str]


class PhaseConverter:
    """Converts a GAEB project between phases."""

    def convert(
        self, project: GAEBProject, target_phase: GAEBPhase
    ) -> PhaseConversionResult:
        """Convert a project to a different GAEB phase.

        Returns a NEW project (deep copy), leaving the original unchanged.
        """
        if project.phase == target_phase:
            return PhaseConversionResult(project, [])

        source_rules = get_rules(project.phase)
        target_rules = get_rules(target_phase)
        warnings: list[str] = []

        new_project = deepcopy(project)
        new_project.phase = target_phase

        # Process all items recursively
        if new_project.boq:
            self._convert_categories(
                new_project.boq.categories, source_rules, target_rules, warnings
            )

            # Handle totals at BoQ level
            if not target_rules.has_totals and new_project.boq.info.totals:
                warnings.append(
                    "BoQ-Summen wurden entfernt (Zielphase unterstuetzt keine Summen)"
                )
                new_project.boq.info.totals = None

        return PhaseConversionResult(new_project, warnings)

    def get_conversion_warnings_preview(
        self, source_phase: GAEBPhase, target_phase: GAEBPhase
    ) -> list[str]:
        """Preview what data will be lost/needed without performing conversion."""
        source_rules = get_rules(source_phase)
        target_rules = get_rules(target_phase)
        warnings: list[str] = []

        if source_rules.has_prices and not target_rules.has_prices:
            warnings.append("Alle Preise werden entfernt")
        if source_rules.has_quantities and not target_rules.has_quantities:
            warnings.append("Alle Mengen werden entfernt")
        if source_rules.has_totals and not target_rules.has_totals:
            warnings.append("Alle Summen werden entfernt")
        if source_rules.allows_not_offered and not target_rules.allows_not_offered:
            warnings.append("'Nicht angeboten' Markierungen werden entfernt")

        if not source_rules.has_prices and target_rules.has_prices:
            warnings.append("Preise muessen nachgetragen werden")
        if not source_rules.has_quantities and target_rules.has_quantities:
            warnings.append("Mengen muessen nachgetragen werden")

        return warnings

    def _convert_categories(
        self,
        categories: list[BoQCategory],
        source: PhaseRules,
        target: PhaseRules,
        warnings: list[str],
    ) -> None:
        for cat in categories:
            self._convert_categories(
                cat.subcategories, source, target, warnings
            )
            for item in cat.items:
                self._convert_item(item, source, target, warnings)

    def _convert_item(
        self,
        item: Item,
        source: PhaseRules,
        target: PhaseRules,
        warnings: list[str],
    ) -> None:
        # Strip quantities if target doesn't support them
        if source.has_quantities and not target.has_quantities:
            if item.qty is not None:
                warnings.append(
                    f"Position {item.rno_part}: Menge {item.qty} wurde entfernt"
                )
            item.qty = None
            item.qty_tbd = False

        # Strip prices if target doesn't support them
        if source.has_prices and not target.has_prices:
            if item.up is not None:
                warnings.append(
                    f"Position {item.rno_part}: Einheitspreis {item.up} wurde entfernt"
                )
            item.up = None
            item.up_components.clear()
            item.discount_pcnt = None

        # Strip totals if target doesn't support them
        if source.has_totals and not target.has_totals:
            item.it = None

        # Strip not_offered flag if target doesn't support it
        if source.allows_not_offered and not target.allows_not_offered:
            if item.not_offered:
                warnings.append(
                    f"Position {item.rno_part}: 'Nicht angeboten' Flag wurde entfernt"
                )
            item.not_offered = False

        # Recalculate totals if target supports them
        if target.has_totals:
            if item.qty is not None and item.up is not None:
                item.it = item.calculate_total()
            else:
                item.it = None
