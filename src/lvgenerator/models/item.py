from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class ItemDescription:
    outline_text: str = ""
    detail_text: str = ""
    detail_html: str = ""
    outline_html: str = ""


@dataclass
class Item:
    id: str = ""
    rno_part: str = ""
    qty: Optional[Decimal] = None
    qty_tbd: bool = False
    qu: str = ""
    up: Optional[Decimal] = None
    up_components: dict[int, Decimal] = field(default_factory=dict)
    discount_pcnt: Optional[Decimal] = None
    it: Optional[Decimal] = None
    vat: Optional[Decimal] = None
    not_appl: bool = False
    not_offered: bool = False
    hour_it: bool = False
    description: ItemDescription = field(default_factory=ItemDescription)

    def calculate_total(self) -> Optional[Decimal]:
        if self.qty is not None and self.up is not None:
            return (self.qty * self.up).quantize(Decimal("0.01"))
        return None
