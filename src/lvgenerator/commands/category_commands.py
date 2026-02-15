from PySide6.QtGui import QUndoCommand

from lvgenerator.commands.base import BaseCommand
from lvgenerator.models.category import BoQCategory


class EditCategoryPropertyCommand(BaseCommand):
    """Undoable command for changing a property on a BoQCategory."""

    def __init__(self, category: BoQCategory, property_name: str,
                 old_value, new_value):
        super().__init__(f"Kategorie-Eigenschaft '{property_name}' aendern")
        self.category = category
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        self._id = hash(("cat_prop", id(self.category), self.property_name)) % (2**31)

    def redo(self) -> None:
        setattr(self.category, self.property_name, self.new_value)

    def undo(self) -> None:
        setattr(self.category, self.property_name, self.old_value)

    def id(self) -> int:
        return self._id

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditCategoryPropertyCommand):
            return False
        if other.category is not self.category:
            return False
        if other.property_name != self.property_name:
            return False
        self.new_value = other.new_value
        return True
