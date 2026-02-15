from decimal import Decimal

from lvgenerator.models.item import Item


def test_calculate_total():
    item = Item(qty=Decimal("10.000"), up=Decimal("25.50"))
    assert item.calculate_total() == Decimal("255.00")


def test_calculate_total_none_qty():
    item = Item(qty=None, up=Decimal("25.50"))
    assert item.calculate_total() is None


def test_calculate_total_none_up():
    item = Item(qty=Decimal("10.000"), up=None)
    assert item.calculate_total() is None


def test_calculate_total_precision():
    item = Item(qty=Decimal("3.000"), up=Decimal("7.333"))
    total = item.calculate_total()
    assert total == Decimal("22.00")


def test_calculate_total_large():
    item = Item(qty=Decimal("1000.000"), up=Decimal("199.990"))
    total = item.calculate_total()
    assert total == Decimal("199990.00")
