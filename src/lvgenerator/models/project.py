from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.constants import GAEBPhase
    from lvgenerator.models.boq import BoQ
    from lvgenerator.models.address import Address, Contractor
    from lvgenerator.models.text_types import AddText


@dataclass
class GAEBInfo:
    version: str = "3.3"
    vers_date: str = "2021-05"
    date: Optional[date] = None
    time: Optional[time] = None
    prog_system: str = "LVGenerator"
    prog_name: str = "LVGenerator v0.1.0"


@dataclass
class PrjInfo:
    name: str = ""
    label: str = ""
    description: str = ""
    currency: str = ""
    currency_label: str = ""
    bid_comm_perm: bool = False


@dataclass
class AwardInfo:
    boq_id: str = ""
    currency: str = "EUR"
    currency_label: str = "Euro"
    cat: str = ""
    open_date: str = ""
    open_time: str = ""
    eval_end: str = ""
    subm_loc: str = ""
    cnst_start: str = ""
    cnst_end: str = ""
    contr_no: str = ""
    contr_date: str = ""
    accept_type: str = ""
    warr_dur: str = ""
    warr_unit: str = ""
    award_no: str = ""


@dataclass
class GAEBProject:
    gaeb_info: GAEBInfo = field(default_factory=GAEBInfo)
    prj_info: PrjInfo = field(default_factory=PrjInfo)
    award_info: AwardInfo = field(default_factory=AwardInfo)
    owner: Optional[Address] = None
    contractor: Optional[Contractor] = None
    phase: Optional[GAEBPhase] = None
    boq: Optional[BoQ] = None
    award_add_texts: list[AddText] = field(default_factory=list)
    gaeb_add_texts: list[AddText] = field(default_factory=list)
