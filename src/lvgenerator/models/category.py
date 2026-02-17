from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from lvgenerator.models.boq import Totals
    from lvgenerator.models.item import Item
    from lvgenerator.models.text_types import AddText


@dataclass
class BoQCategory:
    id: str = ""
    rno_part: str = ""
    label: str = ""
    label_html: str = ""
    subcategories: list[BoQCategory] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    add_texts: list[AddText] = field(default_factory=list)
    exec_descr: str = ""
    exec_descr_html: str = ""
    aln_b_group_no: str = ""
    aln_b_ser_no: str = ""
    remarks_raw: list = field(default_factory=list)  # Raw XML Remark elements in BoQBody
    itemlist_remarks_raw: list = field(default_factory=list)  # Raw XML Remark elements in Itemlist
    perf_descrs_raw: list = field(default_factory=list)  # Raw XML PerfDescr elements in Itemlist
    totals: Optional[Totals] = None

    def get_full_ordinal(self, parent_ordinal: str = "") -> str:
        if parent_ordinal:
            return f"{parent_ordinal}.{self.rno_part}"
        return self.rno_part

    def calculate_total(self) -> Optional[Decimal]:
        """Sum of all item totals in this category (recursive)."""
        total = Decimal("0.00")
        has_any = False
        for item in self.items:
            item_total = item.it if item.it is not None else item.calculate_total()
            if item_total is not None:
                total += item_total
                has_any = True
        for sub in self.subcategories:
            sub_total = sub.calculate_total()
            if sub_total is not None:
                total += sub_total
                has_any = True
        return total if has_any else None
