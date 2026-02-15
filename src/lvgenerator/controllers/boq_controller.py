import uuid

from PySide6.QtWidgets import QMessageBox

from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription


class BoQController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl

    def add_category(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        index = self.main.window.tree_view.currentIndex()
        node = self.main.tree_model.get_node(index) if index.isValid() else None

        new_cat = BoQCategory(
            id=str(uuid.uuid4()),
            rno_part="",
            label="Neue Kategorie",
        )

        if node is not None and node.node_type == "category":
            # Add as subcategory
            parent_cat: BoQCategory = node.data
            parent_cat.subcategories.append(new_cat)
        else:
            # Add at root level
            self.main.project.boq.categories.append(new_cat)

        self.main.refresh_tree()

    def add_item(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        index = self.main.window.tree_view.currentIndex()
        node = self.main.tree_model.get_node(index) if index.isValid() else None

        new_item = Item(
            id=str(uuid.uuid4()),
            rno_part="",
            description=ItemDescription(outline_text="Neue Position"),
        )

        if node is not None and node.node_type == "category":
            parent_cat: BoQCategory = node.data
            parent_cat.items.append(new_item)
        elif node is not None and node.node_type == "item":
            # Find parent category
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                parent_cat: BoQCategory = parent_node.data
                parent_cat.items.append(new_item)
            else:
                QMessageBox.warning(
                    self.main.window,
                    "Keine Kategorie",
                    "Bitte waehlen Sie eine Kategorie aus.",
                )
                return
        else:
            QMessageBox.warning(
                self.main.window,
                "Keine Kategorie",
                "Bitte waehlen Sie zuerst eine Kategorie aus.",
            )
            return

        self.main.refresh_tree()

    def delete_selected(self) -> None:
        if self.main.project is None or self.main.project.boq is None:
            return

        index = self.main.window.tree_view.currentIndex()
        node = self.main.tree_model.get_node(index) if index.isValid() else None

        if node is None:
            return

        reply = QMessageBox.question(
            self.main.window,
            "Loeschen bestaetigen",
            "Soll das ausgewaehlte Element geloescht werden?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if node.node_type == "category":
            self._remove_category(node.data, self.main.project.boq.categories)
        elif node.node_type == "item":
            parent_node = node.parent_node
            if parent_node and parent_node.node_type == "category":
                parent_cat: BoQCategory = parent_node.data
                if node.data in parent_cat.items:
                    parent_cat.items.remove(node.data)

        self.main.refresh_tree()

    def _remove_category(self, cat: BoQCategory, categories: list) -> bool:
        if cat in categories:
            categories.remove(cat)
            return True
        for c in categories:
            if self._remove_category(cat, c.subcategories):
                return True
        return False
