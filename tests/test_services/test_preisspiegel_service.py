from decimal import Decimal

import pytest

from lvgenerator.models.boq import BoQ, BoQInfo
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.preisspiegel import (
    PreisSpiegelCategoryRow,
    PreisSpiegelRow,
)
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.services.preisspiegel_service import (
    _build_item_map,
    _build_item_row,
    create_preisspiegel,
)


def _item(rno, qty=None, qu="", up=None, it=None, text="Pos", not_offered=False):
    return Item(
        id=f"id-{rno}",
        rno_part=rno,
        qty=qty,
        qu=qu,
        up=up,
        it=it,
        not_offered=not_offered,
        description=ItemDescription(outline_text=text),
    )


def _project(name="Testprojekt", categories=None, phase=None):
    from lvgenerator.constants import GAEBPhase
    return GAEBProject(
        gaeb_info=GAEBInfo(),
        prj_info=PrjInfo(name=name),
        award_info=AwardInfo(),
        phase=phase or GAEBPhase.X83,
        boq=BoQ(
            id="boq-1",
            info=BoQInfo(name=name),
            categories=categories or [],
        ),
    )


class TestBuildItemMap:
    def test_flat_structure(self):
        cat = BoQCategory(id="c1", rno_part="01", label="Rohbau", items=[
            _item("0010", qty=Decimal("10")),
            _item("0020", qty=Decimal("20")),
        ])
        project = _project(categories=[cat])
        result = _build_item_map(project)
        assert "01.0010" in result
        assert "01.0020" in result
        assert result["01.0010"].qty == Decimal("10")

    def test_nested_structure(self):
        sub = BoQCategory(id="s1", rno_part="01", label="Sub", items=[
            _item("0010"),
        ])
        cat = BoQCategory(id="c1", rno_part="01", label="Parent",
                          subcategories=[sub])
        project = _project(categories=[cat])
        result = _build_item_map(project)
        assert "01.01.0010" in result

    def test_empty_project(self):
        project = _project()
        result = _build_item_map(project)
        assert result == {}


class TestBuildItemRow:
    def test_all_bidders_have_prices(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        maps = [
            {"01.0010": _item("0010", up=Decimal("5.00"))},
            {"01.0010": _item("0010", up=Decimal("8.00"))},
        ]
        row = _build_item_row("01.0010", ref, maps)
        assert row.oz == "01.0010"
        assert row.unit_prices == [Decimal("5.00"), Decimal("8.00")]
        assert row.total_prices == [Decimal("50.00"), Decimal("80.00")]
        assert row.min_up == Decimal("5.00")
        assert row.max_up == Decimal("8.00")
        assert row.avg_up == Decimal("6.50")
        assert row.not_offered == [False, False]

    def test_bidder_not_offered(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        maps = [
            {"01.0010": _item("0010", up=Decimal("5.00"))},
            {"01.0010": _item("0010", not_offered=True)},
        ]
        row = _build_item_row("01.0010", ref, maps)
        assert row.unit_prices == [Decimal("5.00"), None]
        assert row.not_offered == [False, True]
        assert row.min_up == Decimal("5.00")
        assert row.max_up == Decimal("5.00")

    def test_bidder_missing_position(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        maps = [
            {"01.0010": _item("0010", up=Decimal("5.00"))},
            {},  # Bidder doesn't have this position
        ]
        row = _build_item_row("01.0010", ref, maps)
        assert row.unit_prices == [Decimal("5.00"), None]
        assert row.total_prices[1] is None
        assert row.not_offered == [False, False]

    def test_bidder_with_it_total(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        maps = [
            {"01.0010": _item("0010", up=Decimal("5.00"), it=Decimal("55.00"))},
        ]
        row = _build_item_row("01.0010", ref, maps)
        # it takes precedence over qty*up
        assert row.total_prices == [Decimal("55.00")]

    def test_no_bidders(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        row = _build_item_row("01.0010", ref, [])
        assert row.unit_prices == []
        assert row.min_up is None
        assert row.avg_up is None

    def test_statistics_single_bidder(self):
        ref = _item("0010", qty=Decimal("10"), qu="m2")
        maps = [
            {"01.0010": _item("0010", up=Decimal("7.50"))},
        ]
        row = _build_item_row("01.0010", ref, maps)
        assert row.min_up == Decimal("7.50")
        assert row.max_up == Decimal("7.50")
        assert row.avg_up == Decimal("7.50")


class TestCreatePreisspiegelIntegration:
    """Integration tests using in-memory projects (no file I/O)."""

    def test_basic_structure(self):
        ref_cat = BoQCategory(id="c1", rno_part="01", label="Rohbau", items=[
            _item("0010", qty=Decimal("10"), qu="m2", text="Beton"),
            _item("0020", qty=Decimal("5"), qu="Stk", text="Schalung"),
        ])
        reference = _project(name="Testprojekt", categories=[ref_cat])

        # Build bidder projects manually - since we can't use file I/O,
        # test the internal functions instead
        bidder_maps = [
            {
                "01.0010": _item("0010", up=Decimal("100.00")),
                "01.0020": _item("0020", up=Decimal("50.00")),
            },
            {
                "01.0010": _item("0010", up=Decimal("120.00")),
                "01.0020": _item("0020", up=Decimal("45.00")),
            },
        ]

        from lvgenerator.services.preisspiegel_service import _traverse_structure
        rows = []
        bidder_totals = [Decimal("0.00"), Decimal("0.00")]
        _traverse_structure(
            reference.boq.categories, "", bidder_maps, rows, bidder_totals,
        )

        # Should have 1 category + 2 item rows
        assert len(rows) == 3
        assert isinstance(rows[0], PreisSpiegelCategoryRow)
        assert rows[0].oz == "01"
        assert rows[0].label == "Rohbau"
        assert isinstance(rows[1], PreisSpiegelRow)
        assert rows[1].oz == "01.0010"
        assert isinstance(rows[2], PreisSpiegelRow)
        assert rows[2].oz == "01.0020"

        # Bidder totals
        # Bidder A: 10*100 + 5*50 = 1250
        # Bidder B: 10*120 + 5*45 = 1425
        assert bidder_totals[0] == Decimal("1250.00")
        assert bidder_totals[1] == Decimal("1425.00")

    def test_category_totals(self):
        ref_cat = BoQCategory(id="c1", rno_part="01", label="Rohbau", items=[
            _item("0010", qty=Decimal("10"), qu="m2"),
        ])
        reference = _project(categories=[ref_cat])

        bidder_maps = [
            {"01.0010": _item("0010", up=Decimal("100.00"))},
        ]

        from lvgenerator.services.preisspiegel_service import _traverse_structure
        rows = []
        bidder_totals = [Decimal("0.00")]
        _traverse_structure(
            reference.boq.categories, "", bidder_maps, rows, bidder_totals,
        )

        cat_row = rows[0]
        assert isinstance(cat_row, PreisSpiegelCategoryRow)
        assert cat_row.totals == [Decimal("1000.00")]

    def test_nested_categories(self):
        sub = BoQCategory(id="s1", rno_part="01", label="Untergruppe", items=[
            _item("0010", qty=Decimal("5"), qu="m2"),
        ])
        cat = BoQCategory(id="c1", rno_part="01", label="Hauptgruppe",
                          subcategories=[sub])
        reference = _project(categories=[cat])

        bidder_maps = [
            {"01.01.0010": _item("0010", up=Decimal("20.00"))},
        ]

        from lvgenerator.services.preisspiegel_service import _traverse_structure
        rows = []
        bidder_totals = [Decimal("0.00")]
        _traverse_structure(
            reference.boq.categories, "", bidder_maps, rows, bidder_totals,
        )

        assert len(rows) == 3  # 2 categories + 1 item
        assert rows[0].oz == "01"
        assert rows[0].label == "Hauptgruppe"
        assert rows[1].oz == "01.01"
        assert rows[1].label == "Untergruppe"
        assert rows[2].oz == "01.01.0010"

        # Parent category total should include sub-category items
        assert rows[0].totals == [Decimal("100.00")]
        assert rows[1].totals == [Decimal("100.00")]

    def test_empty_reference(self):
        reference = _project()
        from lvgenerator.services.preisspiegel_service import _traverse_structure
        rows = []
        _traverse_structure(reference.boq.categories, "", [], rows, [])
        assert rows == []
