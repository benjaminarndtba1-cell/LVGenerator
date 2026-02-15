from lvgenerator.commands.base import BaseCommand
from lvgenerator.models.project import GAEBProject


class PhaseConvertCommand(BaseCommand):
    """Undoable command for converting between GAEB phases."""

    def __init__(self, main_ctrl, old_project: GAEBProject,
                 new_project: GAEBProject):
        super().__init__(
            f"Phase konvertiert: {old_project.phase.name} -> {new_project.phase.name}"
        )
        self.main_ctrl = main_ctrl
        self.old_project = old_project
        self.new_project = new_project

    def redo(self) -> None:
        self.main_ctrl.project = self.new_project
        self.main_ctrl.set_project(self.new_project)

    def undo(self) -> None:
        self.main_ctrl.project = self.old_project
        self.main_ctrl.set_project(self.old_project)
