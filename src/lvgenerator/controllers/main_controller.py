from copy import deepcopy
from typing import Optional

from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QUndoCommand, QUndoStack
from PySide6.QtWidgets import QMenu, QMessageBox

from lvgenerator.commands.phase_commands import PhaseConvertCommand
from lvgenerator.constants import GAEBPhase
from lvgenerator.controllers.boq_controller import BoQController
from lvgenerator.controllers.item_controller import ItemController
from lvgenerator.controllers.project_controller import ProjectController
from lvgenerator.gaeb.phase_converter import PhaseConverter
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.models.project import GAEBProject
from lvgenerator.viewmodels.boq_tree_model import BoQTreeModel
from lvgenerator.views.main_window import MainWindow
from lvgenerator.views.phase_convert_dialog import PhaseConvertDialog


class MainController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.project: Optional[GAEBProject] = None
        self.tree_model: Optional[BoQTreeModel] = None
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

        # Undo/Redo
        self.window.action_undo.triggered.connect(self.undo_stack.undo)
        self.window.action_redo.triggered.connect(self.undo_stack.redo)
        self.undo_stack.canUndoChanged.connect(self.window.action_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.window.action_redo.setEnabled)
        self.undo_stack.undoTextChanged.connect(
            lambda t: self.window.action_undo.setText(
                f"Rueckgaengig: {t}" if t else "Rueckgaengig"
            )
        )
        self.undo_stack.redoTextChanged.connect(
            lambda t: self.window.action_redo.setText(
                f"Wiederholen: {t}" if t else "Wiederholen"
            )
        )
        self.undo_stack.indexChanged.connect(self._on_undo_redo)

        # Edit menu
        self.window.action_add_category.triggered.connect(self.boq_ctrl.add_category)
        self.window.action_add_item.triggered.connect(self.boq_ctrl.add_item)
        self.window.action_delete.triggered.connect(self.boq_ctrl.delete_selected)
        self.window.action_move_up.triggered.connect(self.boq_ctrl.move_up)
        self.window.action_move_down.triggered.connect(self.boq_ctrl.move_down)
        self.window.action_duplicate.triggered.connect(self.boq_ctrl.duplicate_selected)
        self.window.action_convert_phase.triggered.connect(self._on_convert_phase)

        # About
        self.window.action_about.triggered.connect(self._show_about)

        # Tree selection
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

    def execute_command(self, command: QUndoCommand) -> None:
        """Push a command onto the undo stack and refresh the tree."""
        self.undo_stack.push(command)
        self.refresh_tree()

    def set_project(self, project: GAEBProject) -> None:
        self.project = project
        self.undo_stack.clear()

        self.tree_model = BoQTreeModel()
        self.tree_model.set_project(project)
        self.window.tree_view.setModel(self.tree_model)

        # Pass undo stack to editors
        self.window.item_editor.set_undo_stack(self.undo_stack)
        self.window.category_editor.set_undo_stack(self.undo_stack)

        # Configure UI for phase
        if project.phase:
            rules = get_rules(project.phase)
            self.window.set_phase_label(
                f"{project.phase.name} - {project.phase.label_de}"
            )
            self.window.item_editor.set_price_visible(rules.has_prices)

            # Hide price columns if not applicable
            if not rules.has_prices:
                self.window.tree_view.setColumnHidden(4, True)  # EP
                self.window.tree_view.setColumnHidden(5, True)  # GP
            else:
                self.window.tree_view.setColumnHidden(4, False)
                self.window.tree_view.setColumnHidden(5, False)

        # Expand all categories
        self.window.tree_view.expandAll()

        # Resize columns
        for i in range(self.tree_model.columnCount()):
            self.window.tree_view.resizeColumnToContents(i)

        self.window.show_empty_editor()
        self._update_title()

    def refresh_tree(self) -> None:
        if self.project and self.tree_model:
            self.tree_model.set_project(self.project)
            self.window.tree_view.expandAll()

    def _on_undo_redo(self, _idx: int) -> None:
        """Called after any undo/redo operation."""
        self.refresh_tree()
        index = self.window.tree_view.currentIndex()
        self._on_tree_selection(index)

    def _on_tree_selection(self, index: QModelIndex) -> None:
        if not index.isValid() or self.tree_model is None:
            self.window.show_empty_editor()
            return

        node = self.tree_model.get_node(index)
        if node is None:
            self.window.show_empty_editor()
            return

        if node.node_type == "item":
            self.window.item_editor.set_item(node.data)
            self.window.show_item_editor()
        elif node.node_type == "category":
            self.window.category_editor.set_category(node.data)
            self.window.show_category_editor()
        else:
            self.window.show_empty_editor()

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

    def _on_context_menu(self, pos) -> None:
        index = self.window.tree_view.indexAt(pos)
        menu = QMenu(self.window)

        if index.isValid() and self.tree_model:
            node = self.tree_model.get_node(index)
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

    def _show_about(self) -> None:
        QMessageBox.about(
            self.window,
            "Ueber LVGenerator",
            "LVGenerator v0.1.0\n\n"
            "Desktop-Anwendung zum Lesen und Schreiben\n"
            "von GAEB DA XML Dateien.\n\n"
            "Unterstuetzte Phasen: X81 - X86",
        )
