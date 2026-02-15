import uuid
from copy import deepcopy

import pytest

from lvgenerator.commands.copy_commands import (
    DuplicateCategoryCommand,
    DuplicateItemCommand,
)
from lvgenerator.commands.move_commands import MoveNodeCommand
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription


@pytest.fixture
def items():
    return [
        Item(id="a", rno_part="0010", description=ItemDescription(outline_text="A")),
        Item(id="b", rno_part="0020", description=ItemDescription(outline_text="B")),
        Item(id="c", rno_part="0030", description=ItemDescription(outline_text="C")),
    ]


@pytest.fixture
def category_with_items(items):
    return BoQCategory(id="cat-1", rno_part="01", label="Test", items=items)


class TestMoveNodeCommand:
    def test_move_down(self, items):
        cmd = MoveNodeCommand(items, items[0], +1)
        cmd.redo()
        assert items[0].id == "b"
        assert items[1].id == "a"
        assert items[2].id == "c"

    def test_move_up(self, items):
        cmd = MoveNodeCommand(items, items[2], -1)
        cmd.redo()
        assert items[0].id == "a"
        assert items[1].id == "c"
        assert items[2].id == "b"

    def test_undo_move(self, items):
        cmd = MoveNodeCommand(items, items[0], +1)
        cmd.redo()
        cmd.undo()
        assert items[0].id == "a"
        assert items[1].id == "b"
        assert items[2].id == "c"

    def test_move_first_up_noop(self, items):
        """Moving first element up should be a no-op."""
        cmd = MoveNodeCommand(items, items[0], -1)
        cmd.redo()
        assert items[0].id == "a"

    def test_move_last_down_noop(self, items):
        """Moving last element down should be a no-op."""
        cmd = MoveNodeCommand(items, items[2], +1)
        cmd.redo()
        assert items[2].id == "c"


class TestDuplicateItemCommand:
    def test_duplicate_creates_copy(self, category_with_items):
        source = category_with_items.items[0]
        cmd = DuplicateItemCommand(category_with_items, source)
        cmd.redo()
        assert len(category_with_items.items) == 4
        dup = category_with_items.items[1]
        assert dup is not source
        assert dup.rno_part == source.rno_part
        assert dup.id != source.id

    def test_undo_removes_duplicate(self, category_with_items):
        source = category_with_items.items[0]
        cmd = DuplicateItemCommand(category_with_items, source)
        cmd.redo()
        cmd.undo()
        assert len(category_with_items.items) == 3

    def test_duplicate_preserves_description(self, category_with_items):
        source = category_with_items.items[0]
        cmd = DuplicateItemCommand(category_with_items, source)
        cmd.redo()
        dup = category_with_items.items[1]
        assert dup.description.outline_text == source.description.outline_text


class TestDuplicateCategoryCommand:
    def test_duplicate_category_with_items(self):
        cat = BoQCategory(
            id="cat-1",
            rno_part="01",
            label="Rohbau",
            items=[Item(id="item-1", rno_part="0010")],
        )
        parent_list = [cat]
        cmd = DuplicateCategoryCommand(parent_list, cat)
        cmd.redo()
        assert len(parent_list) == 2
        dup = parent_list[1]
        assert dup.id != cat.id
        assert dup.label == cat.label
        assert dup.items[0].id != cat.items[0].id

    def test_undo_removes_duplicate_category(self):
        cat = BoQCategory(id="cat-1", rno_part="01", label="Rohbau")
        parent_list = [cat]
        cmd = DuplicateCategoryCommand(parent_list, cat)
        cmd.redo()
        cmd.undo()
        assert len(parent_list) == 1
