from lvgenerator.commands.base import BaseCommand
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item


class AddCategoryCommand(BaseCommand):
    """Undoable command for adding a category to a list."""

    def __init__(self, parent_list: list, category: BoQCategory,
                 index: int = -1):
        super().__init__(f"Kategorie '{category.label}' hinzufuegen")
        self.parent_list = parent_list
        self.category = category
        self.index = index

    def redo(self) -> None:
        if self.index == -1 or self.index >= len(self.parent_list):
            self.parent_list.append(self.category)
            self.index = len(self.parent_list) - 1
        else:
            self.parent_list.insert(self.index, self.category)

    def undo(self) -> None:
        self.parent_list.remove(self.category)


class DeleteCategoryCommand(BaseCommand):
    """Undoable command for removing a category from a list."""

    def __init__(self, parent_list: list, category: BoQCategory):
        super().__init__(f"Kategorie '{category.label}' loeschen")
        self.parent_list = parent_list
        self.category = category
        self.index = -1

    def redo(self) -> None:
        self.index = self.parent_list.index(self.category)
        self.parent_list.remove(self.category)

    def undo(self) -> None:
        self.parent_list.insert(self.index, self.category)


class AddItemCommand(BaseCommand):
    """Undoable command for adding an item to a category."""

    def __init__(self, parent_category: BoQCategory, item: Item,
                 index: int = -1):
        super().__init__(f"Position '{item.rno_part or 'neu'}' hinzufuegen")
        self.parent_category = parent_category
        self.item = item
        self.index = index

    def redo(self) -> None:
        if self.index == -1 or self.index >= len(self.parent_category.items):
            self.parent_category.items.append(self.item)
            self.index = len(self.parent_category.items) - 1
        else:
            self.parent_category.items.insert(self.index, self.item)

    def undo(self) -> None:
        self.parent_category.items.remove(self.item)


class DeleteItemCommand(BaseCommand):
    """Undoable command for removing an item from a category."""

    def __init__(self, parent_category: BoQCategory, item: Item):
        super().__init__(f"Position '{item.rno_part}' loeschen")
        self.parent_category = parent_category
        self.item = item
        self.index = -1

    def redo(self) -> None:
        self.index = self.parent_category.items.index(self.item)
        self.parent_category.items.remove(self.item)

    def undo(self) -> None:
        self.parent_category.items.insert(self.index, self.item)
