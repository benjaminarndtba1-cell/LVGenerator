from PySide6.QtGui import QUndoCommand

from lvgenerator.commands.base import BaseCommand
from lvgenerator.models.item import Item, ItemDescription


class EditItemPropertyCommand(BaseCommand):
    """Undoable command for changing a single property on an Item."""

    _merge_id_counter = 100

    def __init__(self, item: Item, property_name: str,
                 old_value, new_value, description: str = ""):
        super().__init__(description or f"Eigenschaft '{property_name}' aendern")
        self.item = item
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        self._id = hash(("item_prop", id(self.item), self.property_name)) % (2**31)

    def redo(self) -> None:
        setattr(self.item, self.property_name, self.new_value)

    def undo(self) -> None:
        setattr(self.item, self.property_name, self.old_value)

    def id(self) -> int:
        return self._id

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditItemPropertyCommand):
            return False
        if other.item is not self.item:
            return False
        if other.property_name != self.property_name:
            return False
        self.new_value = other.new_value
        return True


class EditItemDescriptionCommand(BaseCommand):
    """Undoable command for changing a field on ItemDescription."""

    def __init__(self, description: ItemDescription, field_name: str,
                 old_value: str, new_value: str):
        super().__init__(f"Beschreibung '{field_name}' aendern")
        self.description = description
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value
        self._id = hash(("item_desc", id(self.description), self.field_name)) % (2**31)

    def redo(self) -> None:
        setattr(self.description, self.field_name, self.new_value)

    def undo(self) -> None:
        setattr(self.description, self.field_name, self.old_value)

    def id(self) -> int:
        return self._id

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditItemDescriptionCommand):
            return False
        if other.description is not self.description:
            return False
        if other.field_name != self.field_name:
            return False
        self.new_value = other.new_value
        return True
