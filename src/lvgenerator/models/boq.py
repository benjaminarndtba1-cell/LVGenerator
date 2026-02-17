from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.models.category import BoQCategory
    from lvgenerator.models.text_types import AddText


@dataclass
class BoQBkdn:
    type: str = "BoQLevel"  # "Lot", "BoQLevel", "Item", "Index"
    length: int = 2
    numeric: bool = True
    label: str = ""
    alignment: Optional[str] = None  # "left", "right", or None


@dataclass
class Totals:
    total: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_pcnt: Optional[Decimal] = None
    discount_amt: Optional[Decimal] = None
    total_net: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    total_gross: Optional[Decimal] = None


@dataclass
class Catalog:
    """Katalogdefinition (Ctlg) in BoQInfo."""
    ctlg_id: str = ""
    ctlg_name: str = ""


@dataclass
class BoQInfo:
    name: str = ""
    label: str = ""
    date: Optional[date] = None
    outline_complete: str = "AllTxt"
    breakdowns: list[BoQBkdn] = field(default_factory=list)
    catalogs: list[Catalog] = field(default_factory=list)
    no_up_comps: int = 0
    up_comp_labels: dict[int, str] = field(default_factory=dict)
    totals: Optional[Totals] = None
    add_texts: list[AddText] = field(default_factory=list)


@dataclass
class BoQ:
    id: str = ""
    info: BoQInfo = field(default_factory=BoQInfo)
    categories: list[BoQCategory] = field(default_factory=list)
