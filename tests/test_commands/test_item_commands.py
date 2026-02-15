from decimal import Decimal

import pytest

from lvgenerator.commands.item_commands import (
    EditItemDescriptionCommand,
    EditItemPropertyCommand,
)
from lvgenerator.models.item import Item, ItemDescription


@pytest.fixture
def item():
    return Item(
        id="test-1",
        rno_part="0010",
        qty=Decimal("100.000"),
        qu="m2",
        up=Decimal("25.00"),
        description=ItemDescription(
            outline_text="Kurztext",
            detail_text="Langtext",
        ),
    )


class TestEditItemPropertyCommand:
    def test_redo_sets_new_value(self, item):
        cmd = EditItemPropertyCommand(item, "rno_part", "0010", "0020")
        cmd.redo()
        assert item.rno_part == "0020"

    def test_undo_restores_old_value(self, item):
        cmd = EditItemPropertyCommand(item, "rno_part", "0010", "0020")
        cmd.redo()
        cmd.undo()
        assert item.rno_part == "0010"

    def test_redo_decimal_field(self, item):
        cmd = EditItemPropertyCommand(
            item, "qty", Decimal("100.000"), Decimal("200.000")
        )
        cmd.redo()
        assert item.qty == Decimal("200.000")

    def test_undo_decimal_field(self, item):
        cmd = EditItemPropertyCommand(
            item, "up", Decimal("25.00"), Decimal("30.00")
        )
        cmd.redo()
        cmd.undo()
        assert item.up == Decimal("25.00")

    def test_merge_same_property(self, item):
        cmd1 = EditItemPropertyCommand(item, "rno_part", "0010", "001")
        cmd2 = EditItemPropertyCommand(item, "rno_part", "001", "0015")
        assert cmd1.mergeWith(cmd2) is True
        # After merge, cmd1 should have cmd2's new value
        cmd1.redo()
        assert item.rno_part == "0015"
        # Undo should restore original value
        cmd1.undo()
        assert item.rno_part == "0010"

    def test_no_merge_different_property(self, item):
        cmd1 = EditItemPropertyCommand(item, "rno_part", "0010", "0020")
        cmd2 = EditItemPropertyCommand(item, "qu", "m2", "m3")
        assert cmd1.mergeWith(cmd2) is False

    def test_no_merge_different_item(self):
        item1 = Item(id="1", rno_part="0010")
        item2 = Item(id="2", rno_part="0020")
        cmd1 = EditItemPropertyCommand(item1, "rno_part", "0010", "0011")
        cmd2 = EditItemPropertyCommand(item2, "rno_part", "0020", "0021")
        assert cmd1.mergeWith(cmd2) is False


class TestEditItemDescriptionCommand:
    def test_redo_sets_new_text(self, item):
        cmd = EditItemDescriptionCommand(
            item.description, "outline_text", "Kurztext", "Neuer Kurztext"
        )
        cmd.redo()
        assert item.description.outline_text == "Neuer Kurztext"

    def test_undo_restores_old_text(self, item):
        cmd = EditItemDescriptionCommand(
            item.description, "detail_text", "Langtext", "Neuer Langtext"
        )
        cmd.redo()
        cmd.undo()
        assert item.description.detail_text == "Langtext"

    def test_merge_same_field(self, item):
        cmd1 = EditItemDescriptionCommand(
            item.description, "outline_text", "Kurztext", "Kurz"
        )
        cmd2 = EditItemDescriptionCommand(
            item.description, "outline_text", "Kurz", "Kurztext Neu"
        )
        assert cmd1.mergeWith(cmd2) is True
        cmd1.redo()
        assert item.description.outline_text == "Kurztext Neu"
        cmd1.undo()
        assert item.description.outline_text == "Kurztext"

    def test_no_merge_different_field(self, item):
        cmd1 = EditItemDescriptionCommand(
            item.description, "outline_text", "a", "b"
        )
        cmd2 = EditItemDescriptionCommand(
            item.description, "detail_text", "c", "d"
        )
        assert cmd1.mergeWith(cmd2) is False
