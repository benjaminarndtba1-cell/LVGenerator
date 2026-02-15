from dataclasses import dataclass

from lvgenerator.constants import GAEBPhase


@dataclass(frozen=True)
class PhaseRules:
    has_quantities: bool
    has_prices: bool
    has_totals: bool
    allows_not_offered: bool
    dp_label_de: str
    dp_label_en: str


PHASE_RULES: dict[GAEBPhase, PhaseRules] = {
    GAEBPhase.X81: PhaseRules(
        False, False, False, False,
        "Leistungsbeschreibung", "Service Description",
    ),
    GAEBPhase.X82: PhaseRules(
        True, True, True, False,
        "Kostenansatz", "Cost Estimate",
    ),
    GAEBPhase.X83: PhaseRules(
        True, False, False, False,
        "Angebotsaufforderung", "Tender Request",
    ),
    GAEBPhase.X84: PhaseRules(
        True, True, True, True,
        "Angebotsabgabe", "Bid Submission",
    ),
    GAEBPhase.X85: PhaseRules(
        True, True, True, False,
        "Nebenangebot", "Alternative Bid",
    ),
    GAEBPhase.X86: PhaseRules(
        True, True, True, False,
        "Auftragserteilung", "Contract Award",
    ),
}


def get_rules(phase: GAEBPhase) -> PhaseRules:
    return PHASE_RULES[phase]
