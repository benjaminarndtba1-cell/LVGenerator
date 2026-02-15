import uuid
from copy import deepcopy

from lvgenerator.commands.base import BaseCommand
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item


class DuplicateItemCommand(BaseCommand):
    """Undoable command for duplicating an item."""

    def __init__(self, parent_category: BoQCategory, source_item: Item):
        super().__init__(f"Position '{source_item.rno_part}' duplizieren")
        self.parent_category = parent_category
        self.source_item = source_item
        self.new_item = None

    def redo(self) -> None:
        if self.new_item is None:
            self.new_item = deepcopy(self.source_item)
            self.new_item.id = str(uuid.uuid4())
        idx = self.parent_category.items.index(self.source_item) + 1
        self.parent_category.items.insert(idx, self.new_item)

    def undo(self) -> None:
        self.parent_category.items.remove(self.new_item)


class DuplicateCategoryCommand(BaseCommand):
    """Undoable command for duplicating a category with all children."""

    def __init__(self, parent_list: list, source_category: BoQCategory):
        super().__init__(f"Kategorie '{source_category.label}' duplizieren")
        self.parent_list = parent_list
        self.source_category = source_category
        self.new_category = None

    def redo(self) -> None:
        if self.new_category is None:
            self.new_category = deepcopy(self.source_category)
            self._assign_new_ids(self.new_category)
        idx = self.parent_list.index(self.source_category) + 1
        self.parent_list.insert(idx, self.new_category)

    def undo(self) -> None:
        self.parent_list.remove(self.new_category)

    def _assign_new_ids(self, cat: BoQCategory) -> None:
        cat.id = str(uuid.uuid4())
        for sub in cat.subcategories:
            self._assign_new_ids(sub)
        for item in cat.items:
            item.id = str(uuid.uuid4())
