from lvgenerator.commands.base import BaseCommand


class DragDropMoveCommand(BaseCommand):
    """Undoable Verschiebung per Drag-and-Drop."""

    def __init__(self, source_list: list, source_item,
                 source_index: int, target_list: list,
                 target_index: int, description: str = ""):
        super().__init__(description or "Element per Drag-and-Drop verschoben")
        self.source_list = source_list
        self.source_item = source_item
        self.source_index = source_index
        self.target_list = target_list
        self.target_index = target_index

    def redo(self) -> None:
        self.source_list.remove(self.source_item)
        idx = self.target_index
        if self.source_list is self.target_list and self.source_index < idx:
            idx -= 1
        self.target_list.insert(idx, self.source_item)

    def undo(self) -> None:
        self.target_list.remove(self.source_item)
        self.source_list.insert(self.source_index, self.source_item)
