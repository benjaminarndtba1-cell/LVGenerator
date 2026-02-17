from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lvgenerator.models.text_types import AddText


@dataclass
class SubDescription:
    """Unterbeschreibung (SubDescr) fuer Leit-/Unterbeschreibungen."""
    sub_d_no: str = ""
    qty: Optional[Decimal] = None
    qty_spec: str = ""
    qu: str = ""
    description: Optional[ItemDescription] = None


@dataclass
class CtlgAssignment:
    """Katalogzuordnung (CtlgAssign)."""
    ctlg_id: str = ""
    ctlg_code: str = ""


@dataclass
class ItemDescription:
    outline_text: str = ""
    detail_text: str = ""
    detail_html: str = ""
    outline_html: str = ""
    stl_no: str = ""
    compl_tsa: str = ""
    compl_tsb: str = ""
    stlb_bau_raw: Optional[object] = None  # Raw XML element preserved for roundtrip
    text_complements_raw: list = field(default_factory=list)  # Raw TextComplement XML
    detail_txt_raw: Optional[object] = None  # Raw DetailTxt XML for roundtrip (interleaved Text/TextComplement)
    perf_descr_raw: Optional[object] = None  # Raw PerfDescr XML element


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
    lump_sum_item: bool = False
    pred_qty: Optional[Decimal] = None
    description: ItemDescription = field(default_factory=ItemDescription)
    formula: str = ""
    use_calculated_qty: bool = False

    # Positionstypen (Provis: "", "WithTotal", "WithoutTotal" oder "Yes" fuer 3.2)
    provis: str = ""
    aln_group_no: str = ""
    aln_ser_no: str = ""
    free_qty: bool = False
    key_it: bool = False
    markup_it: bool = False

    # Zuschlag (AddPlIT style)
    surcharge_type: str = ""
    surcharge_refs: list[str] = field(default_factory=list)

    # MarkupItem (Zuschlagsposition)
    is_markup_item: bool = False
    markup_type: str = ""  # "IdentAsMark", "AllInCat", "ListInSubQty"
    markup_sub_qty_refs: list[str] = field(default_factory=list)  # IDRef values
    it_markup: Optional[Decimal] = None
    has_markup: bool = False  # Empty <Markup/> element

    # Bezugspositionen
    ref_descr: bool = False
    ref_rno: str = ""
    ref_rno_idref: str = ""
    ref_perf_no: str = ""
    ref_perf_no_idref: str = ""
    sum_descr: bool = False

    # Unterbeschreibungen (Leitbeschreibung)
    sub_descriptions: list[SubDescription] = field(default_factory=list)

    # Katalogzuordnungen
    ctlg_assignments: list[CtlgAssignment] = field(default_factory=list)

    # UP Breakdown
    up_bkdn: bool = False  # Empty <UPBkdn/> element

    # Mengensplit
    qty_splits: list[dict] = field(default_factory=list)

    # Zusatztexte
    add_texts: list[AddText] = field(default_factory=list)
    bid_comments: list[str] = field(default_factory=list)
    text_compls: list[str] = field(default_factory=list)

    def calculate_total(self) -> Optional[Decimal]:
        effective_qty = self.get_effective_qty()
        if effective_qty is not None and self.up is not None:
            return (effective_qty * self.up).quantize(Decimal("0.01"))
        return None

    def get_effective_qty(self) -> Optional[Decimal]:
        """Get the effective quantity: calculated if use_calculated_qty is True, else manual qty."""
        if self.use_calculated_qty:
            from lvgenerator.models.formula_evaluator import evaluate_formula
            result, _error = evaluate_formula(self.formula)
            return result
        return self.qty
