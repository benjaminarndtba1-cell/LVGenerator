import json
from typing import Optional

from PySide6.QtCore import (
    QAbstractItemModel, QMimeData, QModelIndex,
    QSortFilterProxyModel, Qt, Signal,
)

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.models.boq import BoQ
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject


class BoQTreeNode:
    def __init__(self, data, parent: Optional["BoQTreeNode"] = None,
                 node_type: str = "category"):
        self.data = data
        self.parent_node = parent
        self.node_type = node_type
        self.children: list[BoQTreeNode] = []

    def row(self) -> int:
        if self.parent_node:
            return self.parent_node.children.index(self)
        return 0


COLUMNS = ["OZ", "Beschreibung", "Menge", "Einheit", "EP", "GP"]
MIME_TYPE = "application/x-lvgenerator-node"


class BoQTreeModel(QAbstractItemModel):
    drop_requested = Signal(object, object, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_nodes: list[BoQTreeNode] = []
        self._phase: Optional[GAEBPhase] = None

    def set_project(self, project: GAEBProject) -> None:
        self.beginResetModel()
        self._root_nodes = []
        self._phase = project.phase
        if project.boq:
            self._root_nodes = self._build_tree(project.boq)
        self.endResetModel()

    def _build_tree(self, boq: BoQ) -> list[BoQTreeNode]:
        nodes = []
        for cat in boq.categories:
            node = self._build_category_node(cat, None)
            nodes.append(node)
        return nodes

    def _build_category_node(self, cat: BoQCategory,
                             parent: Optional[BoQTreeNode]) -> BoQTreeNode:
        node = BoQTreeNode(cat, parent, "category")
        for subcat in cat.subcategories:
            child = self._build_category_node(subcat, node)
            node.children.append(child)
        for item in cat.items:
            child = BoQTreeNode(item, node, "item")
            node.children.append(child)
        return node

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._root_nodes)
        node: BoQTreeNode = parent.internalPointer()
        return len(node.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        node: BoQTreeNode = index.internalPointer()
        col = index.column()

        if node.node_type == "category":
            cat: BoQCategory = node.data
            if col == 0:
                return cat.rno_part
            if col == 1:
                return cat.label
            if col == 5:
                total = cat.calculate_total()
                return str(total) if total is not None else ""
            return None

        if node.node_type == "item":
            item: Item = node.data
            if col == 0:
                return item.rno_part
            if col == 1:
                return item.description.outline_text
            if col == 2:
                return str(item.qty) if item.qty is not None else ""
            if col == 3:
                return item.qu
            if col == 4:
                return str(item.up) if item.up is not None else ""
            if col == 5:
                if item.it is not None:
                    return str(item.it)
                total = item.calculate_total()
                return str(total) if total is not None else ""
            return None

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(COLUMNS):
                return COLUMNS[section]
        return None

    def index(self, row: int, column: int,
              parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            if row < len(self._root_nodes):
                return self.createIndex(row, column, self._root_nodes[row])
            return QModelIndex()

        parent_node: BoQTreeNode = parent.internalPointer()
        if row < len(parent_node.children):
            return self.createIndex(row, column, parent_node.children[row])
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        node: BoQTreeNode = index.internalPointer()
        parent_node = node.parent_node

        if parent_node is None:
            return QModelIndex()

        return self.createIndex(parent_node.row(), 0, parent_node)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        default = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if not index.isValid():
            return default | Qt.ItemIsDropEnabled
        node: BoQTreeNode = index.internalPointer()
        flags = default | Qt.ItemIsDragEnabled
        if node.node_type == "category":
            flags |= Qt.ItemIsDropEnabled
        return flags

    def supportedDropActions(self) -> Qt.DropActions:
        return Qt.MoveAction

    def mimeTypes(self) -> list[str]:
        return [MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime = QMimeData()
        if indexes:
            node: BoQTreeNode = indexes[0].internalPointer()
            data = {
                "node_type": node.node_type,
                "id": node.data.id,
            }
            mime.setData(MIME_TYPE, json.dumps(data).encode())
        return mime

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction,
                        row: int, column: int,
                        parent: QModelIndex) -> bool:
        if not data.hasFormat(MIME_TYPE):
            return False
        try:
            info = json.loads(bytes(data.data(MIME_TYPE)).decode())
        except (ValueError, UnicodeDecodeError):
            return False
        if info["node_type"] == "item" and not parent.isValid():
            return False
        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction,
                     row: int, column: int,
                     parent: QModelIndex) -> bool:
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        try:
            info = json.loads(bytes(data.data(MIME_TYPE)).decode())
        except (ValueError, UnicodeDecodeError):
            return False

        source_node = self._find_node_by_id(info["id"], info["node_type"])
        if source_node is None:
            return False

        target_parent = None
        if parent.isValid():
            target_parent = parent.internalPointer()

        target_row = row if row >= 0 else 0
        self.drop_requested.emit(source_node, target_parent, target_row)
        return False

    def _find_node_by_id(self, node_id: str,
                         node_type: str) -> Optional[BoQTreeNode]:
        for root in self._root_nodes:
            found = self._search_node(root, node_id, node_type)
            if found:
                return found
        return None

    def _search_node(self, node: BoQTreeNode, node_id: str,
                     node_type: str) -> Optional[BoQTreeNode]:
        if node.node_type == node_type and node.data.id == node_id:
            return node
        for child in node.children:
            found = self._search_node(child, node_id, node_type)
            if found:
                return found
        return None

    def get_node(self, index: QModelIndex) -> Optional[BoQTreeNode]:
        if index.isValid():
            return index.internalPointer()
        return None

    def is_price_visible(self) -> bool:
        if self._phase is None:
            return True
        return get_rules(self._phase).has_prices


class BoQFilterProxyModel(QSortFilterProxyModel):
    """Filtert den BoQ-Baum nach Suchbegriff."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def filterAcceptsRow(self, source_row: int,
                         source_parent: QModelIndex) -> bool:
        pattern = self.filterRegularExpression().pattern()
        if not pattern:
            return True

        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        node = model.get_node(index)
        if node is None:
            return False

        search = pattern.lower()

        if node.node_type == "category":
            cat = node.data
            return (search in cat.rno_part.lower()
                    or search in cat.label.lower())

        if node.node_type == "item":
            item = node.data
            return (search in item.rno_part.lower()
                    or search in item.description.outline_text.lower()
                    or search in item.description.detail_text.lower()
                    or search in item.qu.lower())

        return True
