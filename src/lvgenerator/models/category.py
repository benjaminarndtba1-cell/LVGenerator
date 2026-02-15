from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.models.item import Item


@dataclass
class BoQCategory:
    id: str = ""
    rno_part: str = ""
    label: str = ""
    label_html: str = ""
    subcategories: list[BoQCategory] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    def get_full_ordinal(self, parent_ordinal: str = "") -> str:
        if parent_ordinal:
            return f"{parent_ordinal}.{self.rno_part}"
        return self.rno_part
