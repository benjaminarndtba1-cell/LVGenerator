import uuid
from datetime import date
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QMessageBox

from lvgenerator.constants import GAEBPhase
from lvgenerator.export.excel_exporter import ExcelExporter
from lvgenerator.gaeb.formula_persistence import load_formula_metadata, save_formula_metadata
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.services.recent_files import RecentFilesManager
from lvgenerator.views.phase_selector import PhaseSelectDialog


class ProjectController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl
        self.reader = GAEBReader()
        self.writer = GAEBWriter()
        self._current_file_path: Optional[str] = None
        self._recent_files = RecentFilesManager()
        self._update_recent_menu()

    def new_project(self) -> None:
        dialog = PhaseSelectDialog(self.main.window)
        if dialog.exec() != PhaseSelectDialog.Accepted:
            return

        phase = dialog.get_phase()
        name = dialog.get_project_name()
        breakdowns = dialog.get_breakdowns()

        project = GAEBProject()
        project.phase = phase
        project.gaeb_info = GAEBInfo(date=date.today())
        project.prj_info = PrjInfo(name=name)
        project.award_info = AwardInfo(boq_id=str(uuid.uuid4()))
        project.boq = BoQ(
            id=str(uuid.uuid4()),
            info=BoQInfo(
                name=name,
                date=date.today(),
                breakdowns=breakdowns,
            ),
        )

        self._current_file_path = None
        self.main.set_project(project)

    def open_project(self) -> None:
        file_filter = (
            "GAEB-Dateien (*.x81 *.x82 *.x83 *.x84 *.x85 *.x86);;"
            "Alle Dateien (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self.main.window, "GAEB-Datei öffnen", "", file_filter
        )
        if not file_path:
            return

        self._open_file(file_path)

    def open_recent_file(self, file_path: str) -> None:
        self._open_file(file_path)

    def _open_file(self, file_path: str) -> None:
        try:
            project = self.reader.read(file_path)
        except Exception as e:
            QMessageBox.critical(
                self.main.window,
                "Fehler beim Öffnen",
                f"Die Datei konnte nicht gelesen werden:\n{e}",
            )
            return

        # Restore formula metadata from sidecar file
        load_formula_metadata(project, file_path)

        self._current_file_path = file_path
        self._recent_files.add_file(file_path)
        self._update_recent_menu()
        self.main.set_project(project)

    def save_project(self) -> None:
        if self.main.project is None:
            return
        if self._current_file_path:
            self._do_save(self._current_file_path)
        else:
            self.save_project_as()

    def save_project_as(self) -> None:
        if self.main.project is None:
            return

        phase = self.main.project.phase
        ext = phase.file_extension if phase else ".x83"
        default_name = f"Leistungsverzeichnis{ext}"

        file_filter = f"GAEB XML (*{ext});;Alle Dateien (*)"
        file_path, _ = QFileDialog.getSaveFileName(
            self.main.window, "GAEB-Datei speichern", default_name, file_filter
        )
        if not file_path:
            return

        self._do_save(file_path)
        self._current_file_path = file_path
        self._recent_files.add_file(file_path)
        self._update_recent_menu()

    def _do_save(self, file_path: str) -> None:
        try:
            self.writer.write(self.main.project, file_path)
            # Save formula metadata to sidecar file
            save_formula_metadata(self.main.project, file_path)
            self.main.window.status_bar.showMessage(
                f"Gespeichert: {file_path}", 5000
            )
        except Exception as e:
            QMessageBox.critical(
                self.main.window,
                "Fehler beim Speichern",
                f"Die Datei konnte nicht gespeichert werden:\n{e}",
            )

    def export_excel(self) -> None:
        if self.main.project is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.main.window, "Als Excel exportieren",
            "Leistungsverzeichnis.xlsx",
            "Excel-Dateien (*.xlsx);;Alle Dateien (*)",
        )
        if not file_path:
            return

        try:
            exporter = ExcelExporter()
            exporter.export(self.main.project, file_path)
            self.main.window.status_bar.showMessage(
                f"Excel-Export erfolgreich: {file_path}", 5000
            )
        except Exception as e:
            QMessageBox.critical(
                self.main.window,
                "Export-Fehler",
                f"Excel-Export fehlgeschlagen:\n{e}",
            )

    def _update_recent_menu(self) -> None:
        files = self._recent_files.get_recent_files()
        self.main.window.update_recent_files_menu(
            files, self.open_recent_file
        )
