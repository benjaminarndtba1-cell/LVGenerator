from typing import Optional

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QMessageBox

from lvgenerator.constants import GAEBPhase
from lvgenerator.controllers.boq_controller import BoQController
from lvgenerator.controllers.item_controller import ItemController
from lvgenerator.controllers.project_controller import ProjectController
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.models.project import GAEBProject
from lvgenerator.viewmodels.boq_tree_model import BoQTreeModel
from lvgenerator.views.main_window import MainWindow


class MainController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.project: Optional[GAEBProject] = None
        self.tree_model: Optional[BoQTreeModel] = None

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

        # Edit menu
        self.window.action_add_category.triggered.connect(self.boq_ctrl.add_category)
        self.window.action_add_item.triggered.connect(self.boq_ctrl.add_item)
        self.window.action_delete.triggered.connect(self.boq_ctrl.delete_selected)

        # About
        self.window.action_about.triggered.connect(self._show_about)

        # Tree selection
        self.window.tree_view.clicked.connect(self._on_tree_selection)

        # Editor signals
        self.window.item_editor.item_changed.connect(self.item_ctrl.on_item_changed)
        self.window.category_editor.category_changed.connect(
            self.item_ctrl.on_category_changed
        )

    def set_project(self, project: GAEBProject) -> None:
        self.project = project

        self.tree_model = BoQTreeModel()
        self.tree_model.set_project(project)
        self.window.tree_view.setModel(self.tree_model)

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
