from decimal import Decimal
from typing import Optional

from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.preisspiegel import (
    BidderInfo,
    PreisSpiegel,
    PreisSpiegelCategoryRow,
    PreisSpiegelRow,
)
from lvgenerator.models.project import GAEBProject


def _build_item_map(project: GAEBProject) -> dict[str, Item]:
    """Build a flat dict mapping full OZ -> Item from a project."""
    result: dict[str, Item] = {}
    if project.boq:
        for cat in project.boq.categories:
            _collect_items(cat, "", result)
    return result


def _collect_items(cat: BoQCategory, parent_oz: str, result: dict[str, Item]) -> None:
    oz = f"{parent_oz}.{cat.rno_part}" if parent_oz else cat.rno_part
    for sub in cat.subcategories:
        _collect_items(sub, oz, result)
    for item in cat.items:
        full_oz = f"{oz}.{item.rno_part}" if oz else item.rno_part
        result[full_oz] = item


def _traverse_structure(
    categories: list[BoQCategory],
    parent_oz: str,
    bidder_maps: list[dict[str, Item]],
    rows: list,
    bidder_totals: list[Decimal],
) -> None:
    """Recursively traverse reference structure and build rows."""
    for cat in categories:
        oz = f"{parent_oz}.{cat.rno_part}" if parent_oz else cat.rno_part
        cat_row = PreisSpiegelCategoryRow(oz=oz, label=cat.label)
        rows.append(cat_row)

        # Recurse into subcategories
        _traverse_structure(cat.subcategories, oz, bidder_maps, rows, bidder_totals)

        # Process items
        for item in cat.items:
            full_oz = f"{oz}.{item.rno_part}" if oz else item.rno_part
            row = _build_item_row(full_oz, item, bidder_maps)
            rows.append(row)

            # Accumulate bidder totals
            for i, tp in enumerate(row.total_prices):
                if tp is not None:
                    bidder_totals[i] += tp

        # Set category totals (sum of item totals per bidder)
        cat_totals = _compute_category_totals(cat, oz, bidder_maps)
        cat_row.totals = cat_totals


def _build_item_row(
    full_oz: str,
    ref_item: Item,
    bidder_maps: list[dict[str, Item]],
) -> PreisSpiegelRow:
    """Build a PreisSpiegelRow for one position across all bidders."""
    n = len(bidder_maps)
    unit_prices: list[Optional[Decimal]] = []
    total_prices: list[Optional[Decimal]] = []
    not_offered: list[bool] = []

    ref_qty = ref_item.qty

    for bmap in bidder_maps:
        bidder_item = bmap.get(full_oz)
        if bidder_item is None:
            unit_prices.append(None)
            total_prices.append(None)
            not_offered.append(False)
        elif bidder_item.not_offered:
            unit_prices.append(None)
            total_prices.append(None)
            not_offered.append(True)
        else:
            up = bidder_item.up
            unit_prices.append(up)
            if bidder_item.it is not None:
                total_prices.append(bidder_item.it)
            elif up is not None and ref_qty is not None:
                total_prices.append((ref_qty * up).quantize(Decimal("0.01")))
            else:
                total_prices.append(None)
            not_offered.append(False)

    # Statistics over valid unit prices
    valid_ups = [up for up in unit_prices if up is not None]
    min_up = min(valid_ups) if valid_ups else None
    max_up = max(valid_ups) if valid_ups else None
    avg_up = (
        (sum(valid_ups) / len(valid_ups)).quantize(Decimal("0.01"))
        if valid_ups
        else None
    )

    return PreisSpiegelRow(
        oz=full_oz,
        short_text=ref_item.description.outline_text,
        qty=ref_qty,
        qu=ref_item.qu,
        unit_prices=unit_prices,
        total_prices=total_prices,
        not_offered=not_offered,
        min_up=min_up,
        max_up=max_up,
        avg_up=avg_up,
    )


def _compute_category_totals(
    cat: BoQCategory,
    oz: str,
    bidder_maps: list[dict[str, Item]],
) -> list[Optional[Decimal]]:
    """Compute sum of all item GPs in a category for each bidder (recursive)."""
    n = len(bidder_maps)
    totals: list[Decimal] = [Decimal("0.00")] * n
    has_any: list[bool] = [False] * n

    for item in cat.items:
        full_oz = f"{oz}.{item.rno_part}" if oz else item.rno_part
        ref_qty = item.qty
        for i, bmap in enumerate(bidder_maps):
            bidder_item = bmap.get(full_oz)
            if bidder_item is None or bidder_item.not_offered:
                continue
            if bidder_item.it is not None:
                totals[i] += bidder_item.it
                has_any[i] = True
            elif bidder_item.up is not None and ref_qty is not None:
                totals[i] += (ref_qty * bidder_item.up).quantize(Decimal("0.01"))
                has_any[i] = True

    for sub in cat.subcategories:
        sub_oz = f"{oz}.{sub.rno_part}" if oz else sub.rno_part
        sub_totals = _compute_category_totals(sub, sub_oz, bidder_maps)
        for i, st in enumerate(sub_totals):
            if st is not None:
                totals[i] += st
                has_any[i] = True

    return [totals[i] if has_any[i] else None for i in range(n)]


def create_preisspiegel(
    reference: GAEBProject,
    bidder_files: list[str],
) -> PreisSpiegel:
    """Create a Preisspiegel from a reference project and bidder X84 files."""
    reader = GAEBReader()
    bidders: list[BidderInfo] = []
    bidder_maps: list[dict[str, Item]] = []

    for fp in bidder_files:
        project = reader.read(fp)
        name = ""
        if project.contractor and project.contractor.address:
            name = project.contractor.address.name1
        if not name:
            # Use filename as fallback
            name = fp.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        bidders.append(BidderInfo(name=name, file_path=fp))
        bidder_maps.append(_build_item_map(project))

    rows: list = []
    n = len(bidder_files)
    bidder_totals = [Decimal("0.00")] * n

    if reference.boq:
        _traverse_structure(
            reference.boq.categories, "", bidder_maps, rows, bidder_totals
        )

    grand_totals: list[Optional[Decimal]] = [
        t if t != Decimal("0.00") else None for t in bidder_totals
    ]

    return PreisSpiegel(
        project_name=reference.prj_info.name,
        bidders=bidders,
        rows=rows,
        grand_totals=grand_totals,
    )
