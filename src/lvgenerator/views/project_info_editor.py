from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from lvgenerator.commands.project_commands import EditProjectPropertyCommand
from lvgenerator.models.address import Address
from lvgenerator.models.project import GAEBProject


class ProjectInfoEditorWidget(QWidget):
    """Editor fuer Projektinformationen (PrjInfo, Auftraggeber, LV-Info)."""
    project_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: Optional[GAEBProject] = None
        self._updating = False
        self._undo_stack: Optional[QUndoStack] = None
        self._setup_ui()
        self._connect_signals()

    def set_undo_stack(self, stack: QUndoStack) -> None:
        self._undo_stack = stack

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # PrjInfo
        prj_group = QGroupBox("Projektinformationen")
        prj_form = QFormLayout(prj_group)
        self.prj_name_edit = QLineEdit()
        self.prj_label_edit = QLineEdit()
        self.prj_description_edit = QPlainTextEdit()
        self.prj_description_edit.setMaximumHeight(80)
        self.currency_edit = QLineEdit()
        self.currency_edit.setMaximumWidth(80)
        self.currency_label_edit = QLineEdit()
        prj_form.addRow("Projektname:", self.prj_name_edit)
        prj_form.addRow("Projektkuerzel:", self.prj_label_edit)
        prj_form.addRow("Beschreibung:", self.prj_description_edit)
        prj_form.addRow("Waehrung:", self.currency_edit)
        prj_form.addRow("Waehrungsbezeichnung:", self.currency_label_edit)
        layout.addWidget(prj_group)

        # Auftraggeber
        owner_group = QGroupBox("Auftraggeber")
        owner_form = QFormLayout(owner_group)
        self.owner_name1_edit = QLineEdit()
        self.owner_name2_edit = QLineEdit()
        self.owner_name3_edit = QLineEdit()
        self.owner_street_edit = QLineEdit()
        self.owner_pcode_edit = QLineEdit()
        self.owner_pcode_edit.setMaximumWidth(100)
        self.owner_city_edit = QLineEdit()
        owner_form.addRow("Name 1:", self.owner_name1_edit)
        owner_form.addRow("Name 2:", self.owner_name2_edit)
        owner_form.addRow("Name 3:", self.owner_name3_edit)
        owner_form.addRow("Strasse:", self.owner_street_edit)
        owner_form.addRow("PLZ:", self.owner_pcode_edit)
        owner_form.addRow("Ort:", self.owner_city_edit)
        layout.addWidget(owner_group)

        # BoQ-Info
        boq_group = QGroupBox("Leistungsverzeichnis")
        boq_form = QFormLayout(boq_group)
        self.boq_name_edit = QLineEdit()
        self.boq_label_edit = QLineEdit()
        boq_form.addRow("LV-Bezeichnung:", self.boq_name_edit)
        boq_form.addRow("LV-Kuerzel:", self.boq_label_edit)
        layout.addWidget(boq_group)

        layout.addStretch()

    def _connect_signals(self) -> None:
        self.prj_name_edit.textChanged.connect(self._on_field_changed)
        self.prj_label_edit.textChanged.connect(self._on_field_changed)
        self.prj_description_edit.textChanged.connect(self._on_field_changed)
        self.currency_edit.textChanged.connect(self._on_field_changed)
        self.currency_label_edit.textChanged.connect(self._on_field_changed)
        self.owner_name1_edit.textChanged.connect(self._on_field_changed)
        self.owner_name2_edit.textChanged.connect(self._on_field_changed)
        self.owner_name3_edit.textChanged.connect(self._on_field_changed)
        self.owner_street_edit.textChanged.connect(self._on_field_changed)
        self.owner_pcode_edit.textChanged.connect(self._on_field_changed)
        self.owner_city_edit.textChanged.connect(self._on_field_changed)
        self.boq_name_edit.textChanged.connect(self._on_field_changed)
        self.boq_label_edit.textChanged.connect(self._on_field_changed)

    def set_project(self, project: Optional[GAEBProject]) -> None:
        self._updating = True
        self._project = project
        if project is None:
            self._clear_fields()
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.prj_name_edit.setText(project.prj_info.name)
            self.prj_label_edit.setText(project.prj_info.label)
            self.prj_description_edit.setPlainText(project.prj_info.description)
            self.currency_edit.setText(project.prj_info.currency)
            self.currency_label_edit.setText(project.prj_info.currency_label)

            if project.owner:
                self.owner_name1_edit.setText(project.owner.name1)
                self.owner_name2_edit.setText(project.owner.name2)
                self.owner_name3_edit.setText(project.owner.name3)
                self.owner_street_edit.setText(project.owner.street)
                self.owner_pcode_edit.setText(project.owner.pcode)
                self.owner_city_edit.setText(project.owner.city)
            else:
                self.owner_name1_edit.clear()
                self.owner_name2_edit.clear()
                self.owner_name3_edit.clear()
                self.owner_street_edit.clear()
                self.owner_pcode_edit.clear()
                self.owner_city_edit.clear()

            if project.boq:
                self.boq_name_edit.setText(project.boq.info.name)
                self.boq_label_edit.setText(project.boq.info.label)
            else:
                self.boq_name_edit.clear()
                self.boq_label_edit.clear()
        self._updating = False

    def _clear_fields(self) -> None:
        for edit in [
            self.prj_name_edit, self.prj_label_edit,
            self.currency_edit, self.currency_label_edit,
            self.owner_name1_edit, self.owner_name2_edit, self.owner_name3_edit,
            self.owner_street_edit, self.owner_pcode_edit, self.owner_city_edit,
            self.boq_name_edit, self.boq_label_edit,
        ]:
            edit.clear()
        self.prj_description_edit.clear()

    def _push_command(self, obj, prop: str, old_val, new_val) -> None:
        if self._undo_stack is None:
            setattr(obj, prop, new_val)
        else:
            cmd = EditProjectPropertyCommand(obj, prop, old_val, new_val)
            self._updating = True
            self._undo_stack.push(cmd)
            self._updating = False

    def _on_field_changed(self) -> None:
        if self._updating or self._project is None:
            return
        prj = self._project

        # PrjInfo
        self._check_field(prj.prj_info, "name", self.prj_name_edit.text())
        self._check_field(prj.prj_info, "label", self.prj_label_edit.text())
        self._check_field(
            prj.prj_info, "description",
            self.prj_description_edit.toPlainText()
        )
        self._check_field(prj.prj_info, "currency", self.currency_edit.text())
        self._check_field(
            prj.prj_info, "currency_label", self.currency_label_edit.text()
        )

        # Owner (create Address if needed)
        owner_fields = {
            "name1": self.owner_name1_edit.text(),
            "name2": self.owner_name2_edit.text(),
            "name3": self.owner_name3_edit.text(),
            "street": self.owner_street_edit.text(),
            "pcode": self.owner_pcode_edit.text(),
            "city": self.owner_city_edit.text(),
        }
        if prj.owner is None:
            if any(v.strip() for v in owner_fields.values()):
                prj.owner = Address()
        if prj.owner is not None:
            for attr, new_val in owner_fields.items():
                self._check_field(prj.owner, attr, new_val)

        # BoQ info
        if prj.boq:
            self._check_field(prj.boq.info, "name", self.boq_name_edit.text())
            self._check_field(prj.boq.info, "label", self.boq_label_edit.text())

        self.project_changed.emit()

    def _check_field(self, obj, prop: str, new_val) -> None:
        old_val = getattr(obj, prop)
        if new_val != old_val:
            self._push_command(obj, prop, old_val, new_val)
