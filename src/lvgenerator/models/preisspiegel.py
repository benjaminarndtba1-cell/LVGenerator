from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class BidderInfo:
    name: str
    file_path: str


@dataclass
class PreisSpiegelRow:
    oz: str
    short_text: str
    qty: Optional[Decimal]
    qu: str
    unit_prices: list[Optional[Decimal]]
    total_prices: list[Optional[Decimal]]
    not_offered: list[bool]
    min_up: Optional[Decimal] = None
    max_up: Optional[Decimal] = None
    avg_up: Optional[Decimal] = None


@dataclass
class PreisSpiegelCategoryRow:
    oz: str
    label: str
    totals: list[Optional[Decimal]] = field(default_factory=list)


@dataclass
class PreisSpiegel:
    project_name: str
    bidders: list[BidderInfo]
    rows: list[PreisSpiegelRow | PreisSpiegelCategoryRow] = field(default_factory=list)
    grand_totals: list[Optional[Decimal]] = field(default_factory=list)
