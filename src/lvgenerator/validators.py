from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.formula_evaluator import evaluate_formula
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject


@dataclass
class ValidationError:
    """Einzelner Validierungsfehler."""
    field_name: str
    message: str
    severity: str = "error"  # "error" oder "warning"


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung."""
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(e.severity == "error" for e in self.errors)

    def get_field_errors(self, field_name: str) -> list[ValidationError]:
        return [e for e in self.errors if e.field_name == field_name]


class ItemValidator:
    """Validiert eine Position gemaess Phasenregeln."""

    def validate(self, item: Item, phase: GAEBPhase) -> ValidationResult:
        errors: list[ValidationError] = []
        rules = get_rules(phase)

        if not item.rno_part.strip():
            errors.append(ValidationError(
                "rno_part", "Ordnungszahl ist Pflichtfeld"
            ))

        if not item.description.outline_text.strip():
            errors.append(ValidationError(
                "outline_text", "Kurztext ist Pflichtfeld", "warning"
            ))

        if rules.has_quantities:
            if item.qty is not None and item.qty < 0:
                errors.append(ValidationError(
                    "qty", "Menge darf nicht negativ sein"
                ))
            if item.qty is None and not item.qty_tbd:
                errors.append(ValidationError(
                    "qty", "Menge oder 'Menge noch offen' erforderlich", "warning"
                ))

        if item.qty is not None and not item.qu.strip():
            errors.append(ValidationError(
                "qu", "Einheit fehlt bei vorhandener Menge", "warning"
            ))

        if rules.has_prices and item.up is not None and item.up < 0:
            errors.append(ValidationError(
                "up", "Einheitspreis darf nicht negativ sein"
            ))

        # Formula validation
        if item.use_calculated_qty:
            if not item.formula.strip():
                errors.append(ValidationError(
                    "formula", "Formelberechnung aktiv, aber keine Formel eingegeben",
                    "warning"
                ))
            else:
                _result, error = evaluate_formula(item.formula)
                if error:
                    errors.append(ValidationError(
                        "formula", f"Ungueltige Formel: {error}"
                    ))

        return ValidationResult(errors)


class CategoryValidator:
    """Validiert eine Kategorie."""

    def validate(self, cat: BoQCategory) -> ValidationResult:
        errors: list[ValidationError] = []

        if not cat.rno_part.strip():
            errors.append(ValidationError(
                "rno_part", "Ordnungszahl ist Pflichtfeld"
            ))

        if not cat.label.strip():
            errors.append(ValidationError(
                "label", "Bezeichnung ist Pflichtfeld", "warning"
            ))

        return ValidationResult(errors)


class ProjectValidator:
    """Validiert das gesamte Projekt."""

    def validate(self, project: GAEBProject) -> ValidationResult:
        errors: list[ValidationError] = []

        if not project.prj_info.name.strip():
            errors.append(ValidationError(
                "prj_name", "Projektname ist Pflichtfeld", "warning"
            ))

        if project.boq:
            item_val = ItemValidator()
            cat_val = CategoryValidator()
            self._validate_categories(
                project.boq.categories, project.phase, item_val, cat_val, errors
            )

        return ValidationResult(errors)

    def _validate_categories(
        self, categories: list[BoQCategory], phase: GAEBPhase,
        item_val: ItemValidator, cat_val: CategoryValidator,
        errors: list[ValidationError],
    ) -> None:
        for cat in categories:
            result = cat_val.validate(cat)
            errors.extend(result.errors)
            for item in cat.items:
                result = item_val.validate(item, phase)
                errors.extend(result.errors)
            self._validate_categories(
                cat.subcategories, phase, item_val, cat_val, errors
            )


def validate_decimal_input(text: str) -> tuple[Optional[Decimal], Optional[str]]:
    """Validiert eine Dezimaleingabe. Gibt (Wert, Fehlermeldung) zurueck."""
    if not text.strip():
        return None, None
    try:
        val = Decimal(text)
        return val, None
    except InvalidOperation:
        return None, "Ungueltiger Zahlenwert"
