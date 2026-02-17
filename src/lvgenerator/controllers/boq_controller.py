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
from lvgenerator.models.boq import BoQBkdn
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.viewmodels.boq_tree_model import BoQTreeNode


def generate_next_rno(existing_parts: list[str], mask_level: BoQBkdn) -> str:
    """Erzeugt die nächste freie Ordnungszahl basierend auf der OZ-Maske."""
    if mask_level.numeric:
        # Höchste existierende Nummer finden
        max_num = 0
        for part in existing_parts:
            try:
                num = int(part)
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        next_num = max_num + 1
        return str(next_num).zfill(mask_level.length)
    else:
        # Alphanumerisch: einfach durchnummerieren
        max_num = 0
        for part in existing_parts:
            try:
                num = int(part)
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        next_num = max_num + 1
        return str(next_num).zfill(mask_level.length)


def _get_mask_level_for_category(
    breakdowns: list[BoQBkdn], depth: int
) -> Optional[BoQBkdn]:
    """Findet die passende BoQBkdn-Ebene für eine Kategorie in gegebener Tiefe."""
    boq_levels = [b for b in breakdowns if b.type in ("Lot", "BoQLevel")]
    if depth < len(boq_levels):
        return boq_levels[depth]
    return None


def _get_mask_level_for_item(breakdowns: list[BoQBkdn]) -> Optional[BoQBkdn]:
    """Findet die BoQBkdn-Ebene für Positionen."""
    for b in breakdowns:
        if b.type == "Item":
            return b
    return None


class BoQController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl

    def _get_breakdowns(self) -> list[BoQBkdn]:
        if (self.main.project and self.main.project.boq
                and self.main.project.boq.info.breakdowns):
            return self.main.project.boq.info.breakdowns
        return []

    def _get_category_depth(self, node: Optional[BoQTreeNode]) -> int:
        """Berechnet die Verschachtelungstiefe für eine neue Kategorie."""
        if node is None or node.node_type != "category":
            return 0  # Root-Ebene
        # Tiefe des Parent-Knotens + 1 (für Unterkategorie)
        depth = 0
        current = node
        while current and current.node_type == "category":
            depth += 1
            current = current.parent_node
        return depth

    def add_category(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        node = self._get_selected_node()

        if node is not None and node.node_type == "category":
            parent_list = node.data.subcategories
            depth = self._get_category_depth(node)
        else:
            parent_list = self.main.project.boq.categories
            depth = 0

        # Auto-Nummerierung
        rno_part = ""
        breakdowns = self._get_breakdowns()
        mask_level = _get_mask_level_for_category(breakdowns, depth)
        if mask_level:
            existing = [c.rno_part for c in parent_list]
            rno_part = generate_next_rno(existing, mask_level)

        new_cat = BoQCategory(
            id=str(uuid.uuid4()),
            rno_part=rno_part,
            label="Neue Kategorie",
        )

        cmd = AddCategoryCommand(parent_list, new_cat)
        self.main.execute_command(cmd)

    def add_item(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        node = self._get_selected_node()

        # Auto-Nummerierung
        rno_part = ""
        breakdowns = self._get_breakdowns()
        mask_level = _get_mask_level_for_item(breakdowns)

        if node is not None and node.node_type == "category":
            parent_cat: BoQCategory = node.data
            if mask_level:
                existing = [i.rno_part for i in parent_cat.items]
                rno_part = generate_next_rno(existing, mask_level)
            new_item = Item(
                id=str(uuid.uuid4()),
                rno_part=rno_part,
                description=ItemDescription(outline_text="Neue Position"),
            )
            cmd = AddItemCommand(parent_cat, new_item)
            self.main.execute_command(cmd)
        elif node is not None and node.node_type == "item":
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                parent_cat = parent_node.data
                if mask_level:
                    existing = [i.rno_part for i in parent_cat.items]
                    rno_part = generate_next_rno(existing, mask_level)
                new_item = Item(
                    id=str(uuid.uuid4()),
                    rno_part=rno_part,
                    description=ItemDescription(outline_text="Neue Position"),
                )
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
