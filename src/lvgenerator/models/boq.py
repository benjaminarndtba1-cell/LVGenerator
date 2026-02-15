from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.models.category import BoQCategory


@dataclass
class BoQBkdn:
    type: str = "BoQLevel"
    length: int = 2
    numeric: bool = True


@dataclass
class Totals:
    total: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_pcnt: Optional[Decimal] = None
    discount_amt: Optional[Decimal] = None
    total_net: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    total_gross: Optional[Decimal] = None


@dataclass
class BoQInfo:
    name: str = ""
    label: str = ""
    date: Optional[date] = None
    outline_complete: str = "AllTxt"
    breakdowns: list[BoQBkdn] = field(default_factory=list)
    no_up_comps: int = 0
    up_comp_labels: dict[int, str] = field(default_factory=dict)
    totals: Optional[Totals] = None


@dataclass
class BoQ:
    id: str = ""
    info: BoQInfo = field(default_factory=BoQInfo)
    categories: list[BoQCategory] = field(default_factory=list)
