from lvgenerator.commands.base import BaseCommand


class MoveNodeCommand(BaseCommand):
    """Undoable command for moving an item or category up/down."""

    def __init__(self, parent_list: list, item, direction: int,
                 description: str = ""):
        super().__init__(description or "Element verschieben")
        self.parent_list = parent_list
        self.item = item
        self.direction = direction  # -1 for up, +1 for down

    def redo(self) -> None:
        idx = self.parent_list.index(self.item)
        new_idx = idx + self.direction
        if 0 <= new_idx < len(self.parent_list):
            self.parent_list[idx], self.parent_list[new_idx] = (
                self.parent_list[new_idx],
                self.parent_list[idx],
            )

    def undo(self) -> None:
        idx = self.parent_list.index(self.item)
        new_idx = idx - self.direction
        if 0 <= new_idx < len(self.parent_list):
            self.parent_list[idx], self.parent_list[new_idx] = (
                self.parent_list[new_idx],
                self.parent_list[idx],
            )
