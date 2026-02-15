from decimal import Decimal

import pytest

from lvgenerator.commands.drag_drop_commands import DragDropMoveCommand
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item


class TestDragDropMoveCommand:
    def test_move_item_within_same_list(self):
        items = [
            Item(id="1", rno_part="0010"),
            Item(id="2", rno_part="0020"),
            Item(id="3", rno_part="0030"),
        ]
        # Move item 0 to position 2
        cmd = DragDropMoveCommand(items, items[0], 0, items, 2)
        cmd.redo()
        assert items[0].id == "2"
        assert items[1].id == "1"
        assert items[2].id == "3"

    def test_undo_restores_position(self):
        items = [
            Item(id="1", rno_part="0010"),
            Item(id="2", rno_part="0020"),
            Item(id="3", rno_part="0030"),
        ]
        item = items[0]
        cmd = DragDropMoveCommand(items, item, 0, items, 2)
        cmd.redo()
        cmd.undo()
        assert items[0].id == "1"
        assert items[1].id == "2"
        assert items[2].id == "3"

    def test_move_item_to_different_list(self):
        source = [Item(id="1", rno_part="0010"), Item(id="2", rno_part="0020")]
        target = [Item(id="3", rno_part="0030")]
        item = source[0]
        cmd = DragDropMoveCommand(source, item, 0, target, 1)
        cmd.redo()
        assert len(source) == 1
        assert source[0].id == "2"
        assert len(target) == 2
        assert target[1].id == "1"

    def test_undo_cross_list_move(self):
        source = [Item(id="1", rno_part="0010"), Item(id="2", rno_part="0020")]
        target = [Item(id="3", rno_part="0030")]
        item = source[0]
        cmd = DragDropMoveCommand(source, item, 0, target, 1)
        cmd.redo()
        cmd.undo()
        assert len(source) == 2
        assert source[0].id == "1"
        assert len(target) == 1

    def test_move_category_within_list(self):
        cats = [
            BoQCategory(id="c1", rno_part="01", label="A"),
            BoQCategory(id="c2", rno_part="02", label="B"),
        ]
        cmd = DragDropMoveCommand(cats, cats[1], 1, cats, 0)
        cmd.redo()
        assert cats[0].id == "c2"
        assert cats[1].id == "c1"

    def test_move_to_beginning(self):
        items = [
            Item(id="1", rno_part="0010"),
            Item(id="2", rno_part="0020"),
            Item(id="3", rno_part="0030"),
        ]
        item = items[2]
        cmd = DragDropMoveCommand(items, item, 2, items, 0)
        cmd.redo()
        assert items[0].id == "3"
        assert items[1].id == "1"
        assert items[2].id == "2"

    def test_move_to_end(self):
        items = [
            Item(id="1", rno_part="0010"),
            Item(id="2", rno_part="0020"),
        ]
        item = items[0]
        cmd = DragDropMoveCommand(items, item, 0, items, 2)
        cmd.redo()
        assert items[0].id == "2"
        assert items[1].id == "1"

    def test_cross_list_insert_at_start(self):
        source = [Item(id="1", rno_part="0010")]
        target = [Item(id="2", rno_part="0020")]
        item = source[0]
        cmd = DragDropMoveCommand(source, item, 0, target, 0)
        cmd.redo()
        assert len(source) == 0
        assert len(target) == 2
        assert target[0].id == "1"
