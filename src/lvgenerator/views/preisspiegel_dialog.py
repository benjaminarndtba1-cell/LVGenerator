from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from lvgenerator.export.preisspiegel_exporter import PreisSpiegelExporter
from lvgenerator.models.preisspiegel import (
    PreisSpiegel,
    PreisSpiegelCategoryRow,
    PreisSpiegelRow,
)
from lvgenerator.models.project import GAEBProject
from lvgenerator.services.preisspiegel_service import create_preisspiegel


class PreisSpiegelDialog(QDialog):
    def __init__(self, project: GAEBProject, parent=None):
        super().__init__(parent)
        self._project = project
        self._spiegel: Optional[PreisSpiegel] = None
        self._file_paths: list[str] = []

        self.setWindowTitle(
            f"Preisspiegel - {project.prj_info.name or 'Projekt'}"
        )
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Top: file list + buttons
        top_layout = QHBoxLayout()

        self._file_list = QListWidget()
        self._file_list.setMaximumHeight(120)
        top_layout.addWidget(self._file_list, stretch=1)

        btn_layout = QVBoxLayout()
        self._btn_add = QPushButton("X84 hinzufügen...")
        self._btn_add.clicked.connect(self._on_add_files)
        btn_layout.addWidget(self._btn_add)

        self._btn_remove = QPushButton("Entfernen")
        self._btn_remove.clicked.connect(self._on_remove_file)
        btn_layout.addWidget(self._btn_remove)

        self._btn_create = QPushButton("Erstellen")
        self._btn_create.setDefault(True)
        self._btn_create.clicked.connect(self._on_create)
        btn_layout.addWidget(self._btn_create)

        btn_layout.addStretch()
        top_layout.addLayout(btn_layout)
        layout.addLayout(top_layout)

        # Table
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table, stretch=1)

        # Bottom: Export + Close
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self._btn_export = QPushButton("Excel-Export...")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export)
        bottom_layout.addWidget(self._btn_export)

        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)

    def _on_add_files(self) -> None:
        file_filter = "GAEB X84-Dateien (*.x84);;Alle Dateien (*)"
        paths, _ = QFileDialog.getOpenFileNames(
            self, "X84-Dateien auswählen", "", file_filter
        )
        for path in paths:
            if path not in self._file_paths:
                self._file_paths.append(path)
                # Show just filename
                name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, path)
                item.setToolTip(path)
                self._file_list.addItem(item)

    def _on_remove_file(self) -> None:
        row = self._file_list.currentRow()
        if row >= 0:
            item = self._file_list.takeItem(row)
            path = item.data(Qt.UserRole)
            if path in self._file_paths:
                self._file_paths.remove(path)

    def _on_create(self) -> None:
        if not self._file_paths:
            QMessageBox.information(
                self, "Keine Dateien",
                "Bitte mindestens eine X84-Datei hinzufügen.",
            )
            return

        try:
            self._spiegel = create_preisspiegel(self._project, self._file_paths)
        except Exception as e:
            QMessageBox.critical(
                self, "Fehler",
                f"Preisspiegel konnte nicht erstellt werden:\n{e}",
            )
            return

        self._populate_table()
        self._btn_export.setEnabled(True)

    def _populate_table(self) -> None:
        if self._spiegel is None:
            return

        n = len(self._spiegel.bidders)

        # Headers
        headers = ["OZ", "Kurztext", "Menge", "Einheit"]
        for bidder in self._spiegel.bidders:
            headers.append(f"{bidder.name} EP")
            headers.append(f"{bidder.name} GP")
        headers.extend(["Min EP", "Max EP", "Avg EP"])

        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setRowCount(len(self._spiegel.rows) + (1 if self._spiegel.grand_totals else 0))

        cat_bg = QColor("#2a3a5c")
        cat_font = QFont()
        cat_font.setBold(True)

        min_bg = QColor("#1a4a2a")
        max_bg = QColor("#4a1a1a")

        total_font = QFont()
        total_font.setBold(True)

        for row_idx, data_row in enumerate(self._spiegel.rows):
            if isinstance(data_row, PreisSpiegelCategoryRow):
                self._set_cell(row_idx, 0, data_row.oz, font=cat_font, bg=cat_bg)
                self._set_cell(row_idx, 1, data_row.label, font=cat_font, bg=cat_bg)
                # Fill remaining columns with background
                for col in range(2, len(headers)):
                    self._set_cell(row_idx, col, "", bg=cat_bg)
                # Category GP totals
                for i, total in enumerate(data_row.totals):
                    gp_col = 4 + i * 2 + 1  # GP column for bidder i
                    if total is not None:
                        self._set_cell(
                            row_idx, gp_col,
                            str(total.quantize(Decimal("0.01"))),
                            font=cat_font, bg=cat_bg, align_right=True,
                        )
            else:
                self._set_cell(row_idx, 0, data_row.oz)
                self._set_cell(row_idx, 1, data_row.short_text)
                self._set_cell(
                    row_idx, 2,
                    str(data_row.qty.quantize(Decimal("0.001"))) if data_row.qty else "",
                    align_right=True,
                )
                self._set_cell(row_idx, 3, data_row.qu)

                # Bidder EP/GP
                for i in range(n):
                    ep_col = 4 + i * 2
                    gp_col = ep_col + 1

                    if data_row.not_offered[i]:
                        self._set_cell(row_idx, ep_col, "n.a.")
                        self._set_cell(row_idx, gp_col, "n.a.")
                    else:
                        ep_bg = None
                        if data_row.unit_prices[i] is not None and n > 1:
                            if data_row.unit_prices[i] == data_row.min_up:
                                ep_bg = min_bg
                            elif data_row.unit_prices[i] == data_row.max_up:
                                ep_bg = max_bg

                        self._set_cell(
                            row_idx, ep_col,
                            str(data_row.unit_prices[i].quantize(Decimal("0.01")))
                            if data_row.unit_prices[i] is not None else "",
                            align_right=True, bg=ep_bg,
                        )
                        self._set_cell(
                            row_idx, gp_col,
                            str(data_row.total_prices[i].quantize(Decimal("0.01")))
                            if data_row.total_prices[i] is not None else "",
                            align_right=True,
                        )

                # Statistics
                stat_base = 4 + n * 2
                self._set_cell(
                    row_idx, stat_base,
                    str(data_row.min_up.quantize(Decimal("0.01")))
                    if data_row.min_up is not None else "",
                    align_right=True,
                )
                self._set_cell(
                    row_idx, stat_base + 1,
                    str(data_row.max_up.quantize(Decimal("0.01")))
                    if data_row.max_up is not None else "",
                    align_right=True,
                )
                self._set_cell(
                    row_idx, stat_base + 2,
                    str(data_row.avg_up.quantize(Decimal("0.01")))
                    if data_row.avg_up is not None else "",
                    align_right=True,
                )

        # Grand total row
        if self._spiegel.grand_totals:
            total_row = len(self._spiegel.rows)
            self._set_cell(total_row, 0, "Gesamtsumme", font=total_font)
            for col in range(1, len(headers)):
                self._set_cell(total_row, col, "", font=total_font)
            for i, total in enumerate(self._spiegel.grand_totals):
                if total is not None:
                    gp_col = 4 + i * 2 + 1
                    self._set_cell(
                        total_row, gp_col,
                        str(total.quantize(Decimal("0.01"))),
                        font=total_font, align_right=True,
                    )

        # Resize columns
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, len(headers)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeToContents)

    def _set_cell(
        self, row: int, col: int, text: str, *,
        font: Optional[QFont] = None,
        bg: Optional[QColor] = None,
        align_right: bool = False,
    ) -> None:
        item = QTableWidgetItem(text)
        if font:
            item.setFont(font)
        if bg:
            item.setBackground(QBrush(bg))
        if align_right:
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._table.setItem(row, col, item)

    def _on_export(self) -> None:
        if self._spiegel is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Preisspiegel exportieren",
            "Preisspiegel.xlsx",
            "Excel-Dateien (*.xlsx);;Alle Dateien (*)",
        )
        if not file_path:
            return

        try:
            exporter = PreisSpiegelExporter()
            exporter.export(self._spiegel, file_path)
            QMessageBox.information(
                self, "Export erfolgreich",
                f"Preisspiegel wurde exportiert:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export-Fehler",
                f"Export fehlgeschlagen:\n{e}",
            )
