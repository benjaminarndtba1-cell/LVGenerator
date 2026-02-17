from enum import Enum


GAEB_VERSION_32 = "3.2"
GAEB_VERSION_33 = "3.3"
GAEB_DEFAULT_VERSION = GAEB_VERSION_33


class GAEBPhase(Enum):
    X81 = (81, "Leistungsbeschreibung", "Service Description")
    X82 = (82, "Kostenansatz", "Cost Estimate")
    X83 = (83, "Angebotsaufforderung", "Tender Request")
    X84 = (84, "Angebotsabgabe", "Bid Submission")
    X85 = (85, "Nebenangebot", "Alternative Bid")
    X86 = (86, "Auftragserteilung", "Contract Award")

    def __init__(self, dp_value: int, label_de: str, label_en: str):
        self.dp_value = dp_value
        self.label_de = label_de
        self.label_en = label_en

    @classmethod
    def from_dp(cls, dp_value: int) -> "GAEBPhase":
        for phase in cls:
            if phase.dp_value == dp_value:
                return phase
        raise ValueError(f"Unknown GAEB phase: {dp_value}")

    @property
    def file_extension(self) -> str:
        return f".x{self.dp_value}"
