from copy import deepcopy
from typing import Optional

from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QKeySequence, QShortcut, QUndoCommand, QUndoStack
from PySide6.QtWidgets import QMenu, QMessageBox

from lvgenerator.commands.drag_drop_commands import DragDropMoveCommand
from lvgenerator.commands.phase_commands import PhaseConvertCommand
from lvgenerator.constants import GAEBPhase
from lvgenerator.controllers.boq_controller import BoQController
from lvgenerator.controllers.item_controller import ItemController
from lvgenerator.controllers.project_controller import ProjectController
from lvgenerator.gaeb.phase_converter import PhaseConverter
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.project import GAEBProject
from lvgenerator.viewmodels.boq_tree_model import (
    BoQFilterProxyModel, BoQTreeModel, BoQTreeNode,
)
from lvgenerator.views.global_constants_dialog import GlobalConstantsDialog
from lvgenerator.views.main_window import MainWindow
from lvgenerator.views.oz_mask_dialog import OZMaskDialog
from lvgenerator.views.phase_convert_dialog import PhaseConvertDialog


class MainController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.project: Optional[GAEBProject] = None
        self.tree_model: Optional[BoQTreeModel] = None
        self.proxy_model: Optional[BoQFilterProxyModel] = None
        self.undo_stack = QUndoStack(self.window)

        self.project_ctrl = ProjectController(self)
        self.boq_ctrl = BoQController(self)
        self.item_ctrl = ItemController(self)

        self._connect_signals()

    def _connect_signals(self) -> None:
        # File menu
        self.window.action_new.triggered.connect(self.project_ctrl.new_project)
        self.window.action_open.triggered.connect(self.project_ctrl.open_project)
        self.window.action_save.triggered.connect(self.project_ctrl.save_project)
        self.window.action_save_as.triggered.connect(self.project_ctrl.save_project_as)
        self.window.action_export_excel.triggered.connect(
            self.project_ctrl.export_excel
        )

        # Undo/Redo
        self.window.action_undo.triggered.connect(self._do_undo)
        self.window.action_redo.triggered.connect(self._do_redo)
        self.undo_stack.canUndoChanged.connect(self.window.action_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.window.action_redo.setEnabled)
        self.undo_stack.undoTextChanged.connect(
            lambda t: self.window.action_undo.setText(
                f"Rückgängig: {t}" if t else "Rückgängig"
            )
        )
        self.undo_stack.redoTextChanged.connect(
            lambda t: self.window.action_redo.setText(
                f"Wiederholen: {t}" if t else "Wiederholen"
            )
        )

        # Edit menu
        self.window.action_add_category.triggered.connect(self.boq_ctrl.add_category)
        self.window.action_add_item.triggered.connect(self.boq_ctrl.add_item)
        self.window.action_delete.triggered.connect(self.boq_ctrl.delete_selected)
        self.window.action_move_up.triggered.connect(self.boq_ctrl.move_up)
        self.window.action_move_down.triggered.connect(self.boq_ctrl.move_down)
        self.window.action_duplicate.triggered.connect(self.boq_ctrl.duplicate_selected)
        self.window.action_convert_phase.triggered.connect(self._on_convert_phase)
        self.window.action_project_info.triggered.connect(self._on_show_project_info)

        # Extras
        self.window.action_global_constants.triggered.connect(
            self._on_global_constants
        )
        self.window.action_oz_mask.triggered.connect(self._on_oz_mask)
        self.window.action_preisspiegel.triggered.connect(self._on_preisspiegel)

        # About
        self.window.action_about.triggered.connect(self._show_about)

        # Tree selection (clicked for mouse)
        self.window.tree_view.clicked.connect(self._on_tree_selection)

        # Context menu
        self.window.tree_view.customContextMenuRequested.connect(
            self._on_context_menu
        )

        # Editor signals
        self.window.item_editor.item_changed.connect(self.item_ctrl.on_item_changed)
        self.window.category_editor.category_changed.connect(
            self.item_ctrl.on_category_changed
        )
        self.window.project_info_editor.project_changed.connect(
            self._on_project_info_changed
        )

        # Search
        self.window.search_bar.search_changed.connect(self._on_search_changed)

        # Ctrl+F shortcut
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self.window)
        search_shortcut.activated.connect(self.window.search_bar.focus_search)

    def execute_command(self, command: QUndoCommand) -> None:
        """Push a command onto the undo stack and refresh the tree."""
        self.undo_stack.push(command)
        self.refresh_tree()

    def set_project(self, project: GAEBProject) -> None:
        self.project = project
        self.undo_stack.clear()

        self.tree_model = BoQTreeModel()
        self.tree_model.set_project(project)

        # Filter proxy
        self.proxy_model = BoQFilterProxyModel()
        self.proxy_model.setSourceModel(self.tree_model)
        self.window.tree_view.setModel(self.proxy_model)

        # Keyboard navigation (reconnect because selectionModel changes with model)
        self.window.tree_view.selectionModel().currentChanged.connect(
            self._on_tree_selection
        )

        # Drag-and-drop signal
        self.tree_model.drop_requested.connect(self._on_drop_requested)

        # Pass undo stack to editors
        self.window.item_editor.set_undo_stack(self.undo_stack)
        self.window.category_editor.set_undo_stack(self.undo_stack)
        self.window.project_info_editor.set_undo_stack(self.undo_stack)
        self.window.project_info_editor.set_project(project)

        # Configure UI for phase
        if project.phase:
            rules = get_rules(project.phase)
            self.window.set_phase_label(
                f"{project.phase.name} - {project.phase.label_de}"
            )
            self.window.item_editor.set_phase(project.phase)
            self.window.item_editor.set_price_visible(rules.has_prices)

            if not rules.has_prices:
                self.window.tree_view.setColumnHidden(4, True)
                self.window.tree_view.setColumnHidden(5, True)
            else:
                self.window.tree_view.setColumnHidden(4, False)
                self.window.tree_view.setColumnHidden(5, False)

        # Expand all categories
        self.window.tree_view.expandAll()

        # Resize columns with minimum widths
        from PySide6.QtWidgets import QHeaderView
        header = self.window.tree_view.header()
        header.setStretchLastSection(False)
        # All columns: resize to contents first
        for i in range(self.tree_model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        # Beschreibung column stretches to fill remaining space
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        # Set minimum widths for numeric columns
        header.setMinimumSectionSize(50)
        for i in range(self.tree_model.columnCount()):
            self.window.tree_view.resizeColumnToContents(i)

        # Clear search
        self.window.search_bar.search_edit.clear()

        self.window.show_empty_editor()
        self._update_title()
        self._update_status_counts()

    def refresh_tree(self) -> None:
        if self.project and self.tree_model:
            self.tree_model.set_project(self.project)
            self.window.tree_view.expandAll()
            self._update_status_counts()

    def _get_source_index(self, proxy_index: QModelIndex) -> QModelIndex:
        """Map proxy index to source model index."""
        if self.proxy_model and proxy_index.isValid():
            return self.proxy_model.mapToSource(proxy_index)
        return proxy_index

    def _do_undo(self) -> None:
        self.undo_stack.undo()
        self._on_after_undo_redo()

    def _do_redo(self) -> None:
        self.undo_stack.redo()
        self._on_after_undo_redo()

    def _on_after_undo_redo(self) -> None:
        self.refresh_tree()
        index = self.window.tree_view.currentIndex()
        self._on_tree_selection(index)

    def _on_tree_selection(self, index: QModelIndex) -> None:
        if not index.isValid() or self.tree_model is None:
            self.window.show_empty_editor()
            self.window.update_selection_info("")
            return

        # Map through proxy if needed
        source_index = self._get_source_index(index)
        node = self.tree_model.get_node(source_index)
        if node is None:
            self.window.show_empty_editor()
            self.window.update_selection_info("")
            return

        if node.node_type == "item":
            self.window.item_editor.set_item(node.data)
            self.window.show_item_editor()
            total = node.data.calculate_total()
            info = f"Position {node.data.rno_part}"
            if total is not None:
                info += f" | GP: {total}"
            self.window.update_selection_info(info)
        elif node.node_type == "category":
            self.window.category_editor.set_category(node.data)
            self.window.show_category_editor()
            total = node.data.calculate_total()
            info = f"Kategorie {node.data.rno_part} - {node.data.label}"
            if total is not None:
                info += f" | Summe: {total}"
            self.window.update_selection_info(info)
        else:
            self.window.show_empty_editor()
            self.window.update_selection_info("")

    def _on_convert_phase(self) -> None:
        if self.project is None or self.project.phase is None:
            return

        converter = PhaseConverter()
        dialog = PhaseConvertDialog(
            self.project.phase, converter, self.window
        )
        if dialog.exec() != PhaseConvertDialog.DialogCode.Accepted:
            return

        target = dialog.get_target_phase()
        if target is None or target == self.project.phase:
            return

        result = converter.convert(self.project, target)

        if result.warnings:
            QMessageBox.information(
                self.window,
                "Konvertierung abgeschlossen",
                "\n".join(result.warnings),
            )

        old_project = deepcopy(self.project)
        cmd = PhaseConvertCommand(self, old_project, result.project)
        self.undo_stack.push(cmd)

    def _on_show_project_info(self) -> None:
        if self.project is None:
            return
        self.window.project_info_editor.set_project(self.project)
        self.window.show_project_info_editor()

    def _on_project_info_changed(self) -> None:
        self._update_title()

    def _on_search_changed(self, text: str) -> None:
        if self.proxy_model:
            self.proxy_model.setFilterFixedString(text)
            if not text:
                self.window.tree_view.expandAll()

    def _on_drop_requested(self, source_node: BoQTreeNode,
                           target_parent: Optional[BoQTreeNode],
                           target_row: int) -> None:
        if self.project is None or self.project.boq is None:
            return

        source_data = source_node.data

        # Find source list and index
        if source_node.node_type == "item":
            source_list = self._find_item_parent_list(source_data)
        else:
            source_list = self._find_category_parent_list(source_data)

        if source_list is None:
            return

        source_index = source_list.index(source_data)

        # Find target list
        if target_parent is None:
            # Drop at root level — only for categories
            if source_node.node_type == "item":
                return
            target_list = self.project.boq.categories
        else:
            target_cat: BoQCategory = target_parent.data
            if source_node.node_type == "item":
                target_list = target_cat.items
            else:
                target_list = target_cat.subcategories

        cmd = DragDropMoveCommand(
            source_list, source_data, source_index,
            target_list, target_row,
        )
        self.execute_command(cmd)

    def _find_item_parent_list(self, item) -> Optional[list]:
        if self.project is None or self.project.boq is None:
            return None
        return self._search_item_in_categories(
            self.project.boq.categories, item
        )

    def _search_item_in_categories(self, categories, item) -> Optional[list]:
        for cat in categories:
            if item in cat.items:
                return cat.items
            result = self._search_item_in_categories(
                cat.subcategories, item
            )
            if result is not None:
                return result
        return None

    def _find_category_parent_list(self, cat) -> Optional[list]:
        if self.project is None or self.project.boq is None:
            return None
        if cat in self.project.boq.categories:
            return self.project.boq.categories
        return self._search_cat_in_categories(
            self.project.boq.categories, cat
        )

    def _search_cat_in_categories(self, categories, target) -> Optional[list]:
        for cat in categories:
            if target in cat.subcategories:
                return cat.subcategories
            result = self._search_cat_in_categories(
                cat.subcategories, target
            )
            if result is not None:
                return result
        return None

    def _on_context_menu(self, pos) -> None:
        index = self.window.tree_view.indexAt(pos)
        menu = QMenu(self.window)

        if index.isValid() and self.tree_model:
            source_index = self._get_source_index(index)
            node = self.tree_model.get_node(source_index)
            if node and node.node_type == "category":
                menu.addAction(self.window.action_add_category)
                menu.addAction(self.window.action_add_item)
                menu.addSeparator()
            menu.addAction(self.window.action_duplicate)
            menu.addSeparator()
            menu.addAction(self.window.action_move_up)
            menu.addAction(self.window.action_move_down)
            menu.addSeparator()
            menu.addAction(self.window.action_delete)
        else:
            menu.addAction(self.window.action_add_category)

        menu.exec(self.window.tree_view.viewport().mapToGlobal(pos))

    def _update_title(self) -> None:
        if self.project and self.project.prj_info.name:
            self.window.setWindowTitle(
                f"LVGenerator - {self.project.prj_info.name}"
            )
        else:
            self.window.setWindowTitle("LVGenerator")

    def _update_status_counts(self) -> None:
        if self.project is None or self.project.boq is None:
            self.window.update_counts(0, 0)
            return
        cat_count, item_count = self._count_recursive(
            self.project.boq.categories
        )
        self.window.update_counts(cat_count, item_count)

    def _count_recursive(self, categories: list) -> tuple[int, int]:
        cats = len(categories)
        items = 0
        for cat in categories:
            items += len(cat.items)
            sub_cats, sub_items = self._count_recursive(cat.subcategories)
            cats += sub_cats
            items += sub_items
        return cats, items

    def _on_global_constants(self) -> None:
        dialog = GlobalConstantsDialog(self.window)
        if dialog.exec() == GlobalConstantsDialog.DialogCode.Accepted:
            # Refresh formula results in the item editor
            self.window.item_editor.refresh_formula()

    def _on_oz_mask(self) -> None:
        if self.project is None or self.project.boq is None:
            QMessageBox.information(
                self.window,
                "Kein Projekt",
                "Bitte öffnen oder erstellen Sie zuerst ein Projekt.",
            )
            return

        from copy import deepcopy
        from lvgenerator.commands.base import BaseCommand

        old_breakdowns = deepcopy(self.project.boq.info.breakdowns)
        dialog = OZMaskDialog(old_breakdowns, self.window)
        if dialog.exec() != OZMaskDialog.DialogCode.Accepted:
            return

        new_breakdowns = dialog.get_breakdowns()

        class ChangeOZMaskCommand(BaseCommand):
            def __init__(cmd_self, project, old_bk, new_bk):
                super().__init__("OZ-Maske ändern")
                cmd_self._project = project
                cmd_self._old = old_bk
                cmd_self._new = new_bk

            def redo(cmd_self) -> None:
                cmd_self._project.boq.info.breakdowns = deepcopy(cmd_self._new)

            def undo(cmd_self) -> None:
                cmd_self._project.boq.info.breakdowns = deepcopy(cmd_self._old)

        cmd = ChangeOZMaskCommand(self.project, old_breakdowns, new_breakdowns)
        self.execute_command(cmd)

    def _on_preisspiegel(self) -> None:
        if self.project is None or self.project.boq is None:
            QMessageBox.information(
                self.window,
                "Kein Projekt",
                "Bitte zuerst ein Projekt oeffnen.",
            )
            return
        from lvgenerator.views.preisspiegel_dialog import PreisSpiegelDialog
        dialog = PreisSpiegelDialog(self.project, self.window)
        dialog.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self.window,
            "Über LVGenerator",
            "LVGenerator v0.1.0\n\n"
            "Desktop-Anwendung zum Lesen und Schreiben\n"
            "von GAEB DA XML Dateien.\n\n"
            "Unterstützte Phasen: X81 - X86",
        )
