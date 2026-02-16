from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QTreeView,
    QWidget,
    QVBoxLayout,
    QLabel,
)

from lvgenerator.views.category_editor import CategoryEditorWidget
from lvgenerator.views.item_editor import ItemEditorWidget
from lvgenerator.views.project_info_editor import ProjectInfoEditorWidget
from lvgenerator.views.search_bar import SearchBarWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LVGenerator")
        self.setMinimumSize(1200, 800)

        self._setup_actions()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_actions(self) -> None:
        self.action_new = QAction("&Neu", self)
        self.action_new.setShortcut(QKeySequence.New)

        self.action_open = QAction("&Oeffnen...", self)
        self.action_open.setShortcut(QKeySequence.Open)

        self.action_save = QAction("&Speichern", self)
        self.action_save.setShortcut(QKeySequence.Save)

        self.action_save_as = QAction("Speichern &unter...", self)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.action_export_excel = QAction("Excel-Export...", self)

        self.action_exit = QAction("&Beenden", self)
        self.action_exit.setShortcut(QKeySequence.Quit)
        self.action_exit.triggered.connect(self.close)

        self.action_undo = QAction("Rueckgaengig", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.setEnabled(False)

        self.action_redo = QAction("Wiederholen", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        self.action_redo.setEnabled(False)

        self.action_add_category = QAction("Kategorie hinzufuegen", self)
        self.action_add_item = QAction("Position hinzufuegen", self)
        self.action_delete = QAction("Loeschen", self)
        self.action_delete.setShortcut(QKeySequence.Delete)

        self.action_move_up = QAction("Nach oben", self)
        self.action_move_up.setShortcut(QKeySequence("Alt+Up"))

        self.action_move_down = QAction("Nach unten", self)
        self.action_move_down.setShortcut(QKeySequence("Alt+Down"))

        self.action_duplicate = QAction("Duplizieren", self)
        self.action_duplicate.setShortcut(QKeySequence("Ctrl+D"))

        self.action_convert_phase = QAction("Phase konvertieren...", self)

        self.action_project_info = QAction("Projektinformationen...", self)

        self.action_about = QAction("Ueber LVGenerator", self)

        self.action_global_constants = QAction("Globale Konstanten...", self)

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&Datei")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        self.recent_files_menu = file_menu.addMenu("Zuletzt geoeffnet")
        self.recent_files_menu.setEnabled(False)
        file_menu.addSeparator()
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_export_excel)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        edit_menu = menu_bar.addMenu("&Bearbeiten")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_add_category)
        edit_menu.addAction(self.action_add_item)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_move_up)
        edit_menu.addAction(self.action_move_down)
        edit_menu.addAction(self.action_duplicate)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_convert_phase)
        edit_menu.addAction(self.action_project_info)

        extras_menu = menu_bar.addMenu("E&xtras")
        extras_menu.addAction(self.action_global_constants)

        help_menu = menu_bar.addMenu("&Hilfe")
        help_menu.addAction(self.action_about)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Hauptwerkzeugleiste")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_add_category)
        toolbar.addAction(self.action_add_item)
        toolbar.addAction(self.action_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.action_move_up)
        toolbar.addAction(self.action_move_down)
        toolbar.addAction(self.action_duplicate)

    def _setup_central_widget(self) -> None:
        splitter = QSplitter()

        # Left panel: search bar + tree view
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.search_bar = SearchBarWidget()
        left_layout.addWidget(self.search_bar)

        self.tree_view = QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionBehavior(QTreeView.SelectRows)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setExpandsOnDoubleClick(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDragDropMode(QTreeView.InternalMove)
        self.tree_view.setDefaultDropAction(Qt.MoveAction)
        left_layout.addWidget(self.tree_view)

        # Right: Editor panel (stacked widget)
        self.editor_stack = QStackedWidget()

        # Empty placeholder
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_label = QLabel("Waehlen Sie ein Element im Baum aus.")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_label)

        self.item_editor = ItemEditorWidget()
        self.category_editor = CategoryEditorWidget()
        self.project_info_editor = ProjectInfoEditorWidget()

        self.editor_stack.addWidget(empty_widget)               # index 0
        self.editor_stack.addWidget(self.item_editor)            # index 1
        self.editor_stack.addWidget(self.category_editor)        # index 2
        self.editor_stack.addWidget(self.project_info_editor)    # index 3

        splitter.addWidget(left_panel)
        splitter.addWidget(self.editor_stack)
        splitter.setSizes([650, 450])

        self.setCentralWidget(splitter)

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.item_count_label = QLabel("")
        self.status_bar.addWidget(self.item_count_label)

        self.selection_info_label = QLabel("")
        self.status_bar.addWidget(self.selection_info_label)

        self.phase_label = QLabel("")
        self.status_bar.addPermanentWidget(self.phase_label)

    def show_item_editor(self) -> None:
        self.editor_stack.setCurrentIndex(1)

    def show_category_editor(self) -> None:
        self.editor_stack.setCurrentIndex(2)

    def show_project_info_editor(self) -> None:
        self.editor_stack.setCurrentIndex(3)

    def show_empty_editor(self) -> None:
        self.editor_stack.setCurrentIndex(0)

    def set_phase_label(self, text: str) -> None:
        self.phase_label.setText(text)

    def update_counts(self, categories: int, items: int) -> None:
        self.item_count_label.setText(
            f"{categories} Kategorien, {items} Positionen"
        )

    def update_selection_info(self, text: str) -> None:
        self.selection_info_label.setText(text)

    def update_recent_files_menu(self, files: list[str], callback) -> None:
        """Aktualisiert das Untermenue mit den zuletzt geoeffneten Dateien."""
        self.recent_files_menu.clear()
        for file_path in files:
            name = Path(file_path).name
            action = self.recent_files_menu.addAction(name)
            action.setData(file_path)
            action.setToolTip(file_path)
            action.triggered.connect(
                lambda checked, p=file_path: callback(p)
            )
        self.recent_files_menu.setEnabled(bool(files))
