from decimal import Decimal

import pytest

from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item


class TestCalculateTotal:
    def test_items_with_totals(self):
        cat = BoQCategory(
            id="cat-1",
            rno_part="01",
            label="Test",
            items=[
                Item(id="1", rno_part="0010", it=Decimal("100.00")),
                Item(id="2", rno_part="0020", it=Decimal("200.00")),
            ],
        )
        assert cat.calculate_total() == Decimal("300.00")

    def test_items_calculated_from_qty_and_up(self):
        cat = BoQCategory(
            id="cat-1",
            rno_part="01",
            label="Test",
            items=[
                Item(
                    id="1", rno_part="0010",
                    qty=Decimal("10"), up=Decimal("5.00"),
                ),
                Item(
                    id="2", rno_part="0020",
                    qty=Decimal("20"), up=Decimal("3.00"),
                ),
            ],
        )
        assert cat.calculate_total() == Decimal("110.00")

    def test_recursive_subcategories(self):
        sub = BoQCategory(
            id="sub-1",
            rno_part="01",
            label="Sub",
            items=[Item(id="1", rno_part="0010", it=Decimal("50.00"))],
        )
        cat = BoQCategory(
            id="cat-1",
            rno_part="01",
            label="Parent",
            subcategories=[sub],
            items=[Item(id="2", rno_part="0010", it=Decimal("100.00"))],
        )
        assert cat.calculate_total() == Decimal("150.00")

    def test_empty_category_returns_none(self):
        cat = BoQCategory(id="cat-1", rno_part="01", label="Empty")
        assert cat.calculate_total() is None

    def test_items_without_values_returns_none(self):
        cat = BoQCategory(
            id="cat-1",
            rno_part="01",
            label="Test",
            items=[Item(id="1", rno_part="0010")],
        )
        assert cat.calculate_total() is None
