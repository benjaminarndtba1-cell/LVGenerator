import uuid
from datetime import date
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QMessageBox

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.views.phase_selector import PhaseSelectDialog


class ProjectController:
    def __init__(self, main_ctrl):
        self.main = main_ctrl
        self.reader = GAEBReader()
        self.writer = GAEBWriter()
        self._current_file_path: Optional[str] = None

    def new_project(self) -> None:
        dialog = PhaseSelectDialog(self.main.window)
        if dialog.exec() != PhaseSelectDialog.Accepted:
            return

        phase = dialog.get_phase()
        name = dialog.get_project_name()

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
                breakdowns=[
                    BoQBkdn(type="BoQLevel", length=2, numeric=True),
                    BoQBkdn(type="Item", length=4, numeric=True),
                ],
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
            self.main.window, "GAEB-Datei oeffnen", "", file_filter
        )
        if not file_path:
            return

        try:
            project = self.reader.read(file_path)
        except Exception as e:
            QMessageBox.critical(
                self.main.window,
                "Fehler beim Oeffnen",
                f"Die Datei konnte nicht gelesen werden:\n{e}",
            )
            return

        self._current_file_path = file_path
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

    def _do_save(self, file_path: str) -> None:
        try:
            self.writer.write(self.main.project, file_path)
            self.main.window.status_bar.showMessage(
                f"Gespeichert: {file_path}", 5000
            )
        except Exception as e:
            QMessageBox.critical(
                self.main.window,
                "Fehler beim Speichern",
                f"Die Datei konnte nicht gespeichert werden:\n{e}",
            )
