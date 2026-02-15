class ItemController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl

    def on_item_changed(self) -> None:
        if self.main.tree_model:
            index = self.main.window.tree_view.currentIndex()
            if index.isValid():
                # Notify tree model that data changed for this row
                top_left = self.main.tree_model.index(
                    index.row(), 0, index.parent()
                )
                bottom_right = self.main.tree_model.index(
                    index.row(),
                    self.main.tree_model.columnCount() - 1,
                    index.parent(),
                )
                self.main.tree_model.dataChanged.emit(top_left, bottom_right)

    def on_category_changed(self) -> None:
        self.on_item_changed()
