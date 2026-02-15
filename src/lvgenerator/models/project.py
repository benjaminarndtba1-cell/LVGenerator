from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.constants import GAEBPhase
    from lvgenerator.models.boq import BoQ
    from lvgenerator.models.address import Address


@dataclass
class GAEBInfo:
    version: str = "3.2"
    vers_date: str = "2013-10"
    date: Optional[date] = None
    time: Optional[time] = None
    prog_system: str = "LVGenerator"
    prog_name: str = "LVGenerator v0.1.0"


@dataclass
class PrjInfo:
    name: str = ""
    label: str = ""
    description: str = ""
    currency: str = "EUR"
    currency_label: str = "Euro"


@dataclass
class AwardInfo:
    boq_id: str = ""
    currency: str = "EUR"
    currency_label: str = "Euro"


@dataclass
class GAEBProject:
    gaeb_info: GAEBInfo = field(default_factory=GAEBInfo)
    prj_info: PrjInfo = field(default_factory=PrjInfo)
    award_info: AwardInfo = field(default_factory=AwardInfo)
    owner: Optional[Address] = None
    phase: Optional[GAEBPhase] = None
    boq: Optional[BoQ] = None
