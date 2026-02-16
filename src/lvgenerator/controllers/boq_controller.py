import uuid
from typing import Optional

from PySide6.QtWidgets import QMessageBox

from lvgenerator.commands.copy_commands import (
    DuplicateCategoryCommand,
    DuplicateItemCommand,
)
from lvgenerator.commands.move_commands import MoveNodeCommand
from lvgenerator.commands.structure_commands import (
    AddCategoryCommand,
    AddItemCommand,
    DeleteCategoryCommand,
    DeleteItemCommand,
)
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.viewmodels.boq_tree_model import BoQTreeNode


class BoQController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl

    def add_category(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        node = self._get_selected_node()

        new_cat = BoQCategory(
            id=str(uuid.uuid4()),
            rno_part="",
            label="Neue Kategorie",
        )

        if node is not None and node.node_type == "category":
            parent_list = node.data.subcategories
        else:
            parent_list = self.main.project.boq.categories

        cmd = AddCategoryCommand(parent_list, new_cat)
        self.main.execute_command(cmd)

    def add_item(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        node = self._get_selected_node()

        new_item = Item(
            id=str(uuid.uuid4()),
            rno_part="",
            description=ItemDescription(outline_text="Neue Position"),
        )

        if node is not None and node.node_type == "category":
            parent_cat: BoQCategory = node.data
            cmd = AddItemCommand(parent_cat, new_item)
            self.main.execute_command(cmd)
        elif node is not None and node.node_type == "item":
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                parent_cat = parent_node.data
                cmd = AddItemCommand(parent_cat, new_item)
                self.main.execute_command(cmd)
            else:
                QMessageBox.warning(
                    self.main.window,
                    "Keine Kategorie",
                    "Bitte wählen Sie eine Kategorie aus.",
                )
        else:
            QMessageBox.warning(
                self.main.window,
                "Keine Kategorie",
                "Bitte wählen Sie zuerst eine Kategorie aus.",
            )

    def delete_selected(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        node = self._get_selected_node()
        if node is None:
            return

        reply = QMessageBox.question(
            self.main.window,
            "Löschen bestätigen",
            "Soll das ausgewählte Element gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if node.node_type == "category":
            parent_list = self._get_parent_list(node)
            if parent_list is not None:
                cmd = DeleteCategoryCommand(parent_list, node.data)
                self.main.execute_command(cmd)
        elif node.node_type == "item":
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                cmd = DeleteItemCommand(parent_node.data, node.data)
                self.main.execute_command(cmd)

    def move_up(self) -> None:
        node = self._get_selected_node()
        if node is None:
            return
        parent_list = self._get_parent_list(node)
        if parent_list is None:
            return
        idx = parent_list.index(node.data)
        if idx <= 0:
            return
        cmd = MoveNodeCommand(
            parent_list, node.data, -1, "Element nach oben verschieben"
        )
        self.main.execute_command(cmd)

    def move_down(self) -> None:
        node = self._get_selected_node()
        if node is None:
            return
        parent_list = self._get_parent_list(node)
        if parent_list is None:
            return
        idx = parent_list.index(node.data)
        if idx >= len(parent_list) - 1:
            return
        cmd = MoveNodeCommand(
            parent_list, node.data, +1, "Element nach unten verschieben"
        )
        self.main.execute_command(cmd)

    def duplicate_selected(self) -> None:
        node = self._get_selected_node()
        if node is None:
            return

        if node.node_type == "item":
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                cmd = DuplicateItemCommand(parent_node.data, node.data)
                self.main.execute_command(cmd)
        elif node.node_type == "category":
            parent_list = self._get_parent_list(node)
            if parent_list is not None:
                cmd = DuplicateCategoryCommand(parent_list, node.data)
                self.main.execute_command(cmd)

    def _get_selected_node(self) -> Optional[BoQTreeNode]:
        if self.main.tree_model is None:
            return None
        index = self.main.window.tree_view.currentIndex()
        if not index.isValid():
            return None
        source_index = self.main._get_source_index(index)
        return self.main.tree_model.get_node(source_index)

    def _get_parent_list(self, node: BoQTreeNode) -> Optional[list]:
        """Returns the list that contains node.data."""
        parent = node.parent_node
        if node.node_type == "item":
            if parent and parent.node_type == "category":
                return parent.data.items
        elif node.node_type == "category":
            if parent and parent.node_type == "category":
                return parent.data.subcategories
            else:
                return self.main.project.boq.categories
        return None
