from PySide6.QtGui import QUndoCommand

from lvgenerator.commands.base import BaseCommand


class EditProjectPropertyCommand(BaseCommand):
    """Undoable Änderung an Projekteigenschaften."""

    def __init__(self, obj, property_name: str, old_value, new_value,
                 description: str = ""):
        super().__init__(
            description or f"Projekteigenschaft '{property_name}' ändern"
        )
        self.obj = obj
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        self._id = hash(
            ("prj_prop", id(self.obj), self.property_name)
        ) % (2**31)

    def redo(self) -> None:
        setattr(self.obj, self.property_name, self.new_value)

    def undo(self) -> None:
        setattr(self.obj, self.property_name, self.old_value)

    def id(self) -> int:
        return self._id

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditProjectPropertyCommand):
            return False
        if other.obj is not self.obj:
            return False
        if other.property_name != self.property_name:
            return False
        self.new_value = other.new_value
        return True
