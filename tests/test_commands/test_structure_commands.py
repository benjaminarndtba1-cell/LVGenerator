import uuid

import pytest

from lvgenerator.commands.structure_commands import (
    AddCategoryCommand,
    AddItemCommand,
    DeleteCategoryCommand,
    DeleteItemCommand,
)
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription


@pytest.fixture
def category():
    return BoQCategory(
        id="cat-1",
        rno_part="01",
        label="Rohbau",
        items=[
            Item(id="item-1", rno_part="0010"),
            Item(id="item-2", rno_part="0020"),
        ],
    )


@pytest.fixture
def root_categories():
    return [
        BoQCategory(id="cat-1", rno_part="01", label="Rohbau"),
        BoQCategory(id="cat-2", rno_part="02", label="Dach"),
    ]


class TestAddCategoryCommand:
    def test_redo_appends_category(self, root_categories):
        new_cat = BoQCategory(id="cat-3", rno_part="03", label="Innenausbau")
        cmd = AddCategoryCommand(root_categories, new_cat)
        cmd.redo()
        assert len(root_categories) == 3
        assert root_categories[-1] is new_cat

    def test_undo_removes_category(self, root_categories):
        new_cat = BoQCategory(id="cat-3", rno_part="03", label="Innenausbau")
        cmd = AddCategoryCommand(root_categories, new_cat)
        cmd.redo()
        cmd.undo()
        assert len(root_categories) == 2
        assert new_cat not in root_categories

    def test_redo_at_index(self, root_categories):
        new_cat = BoQCategory(id="cat-3", rno_part="03", label="Innenausbau")
        cmd = AddCategoryCommand(root_categories, new_cat, index=1)
        cmd.redo()
        assert root_categories[1] is new_cat
        assert len(root_categories) == 3


class TestDeleteCategoryCommand:
    def test_redo_removes_category(self, root_categories):
        cat = root_categories[0]
        cmd = DeleteCategoryCommand(root_categories, cat)
        cmd.redo()
        assert len(root_categories) == 1
        assert cat not in root_categories

    def test_undo_restores_at_correct_index(self, root_categories):
        cat = root_categories[0]
        cmd = DeleteCategoryCommand(root_categories, cat)
        cmd.redo()
        cmd.undo()
        assert len(root_categories) == 2
        assert root_categories[0] is cat


class TestAddItemCommand:
    def test_redo_appends_item(self, category):
        new_item = Item(id="item-3", rno_part="0030")
        cmd = AddItemCommand(category, new_item)
        cmd.redo()
        assert len(category.items) == 3
        assert category.items[-1] is new_item

    def test_undo_removes_item(self, category):
        new_item = Item(id="item-3", rno_part="0030")
        cmd = AddItemCommand(category, new_item)
        cmd.redo()
        cmd.undo()
        assert len(category.items) == 2
        assert new_item not in category.items


class TestDeleteItemCommand:
    def test_redo_removes_item(self, category):
        item = category.items[0]
        cmd = DeleteItemCommand(category, item)
        cmd.redo()
        assert len(category.items) == 1
        assert item not in category.items

    def test_undo_restores_at_correct_index(self, category):
        item = category.items[0]
        cmd = DeleteItemCommand(category, item)
        cmd.redo()
        cmd.undo()
        assert len(category.items) == 2
        assert category.items[0] is item
