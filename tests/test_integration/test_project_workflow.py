import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from lvgenerator.constants import GAEBPhase
from lvgenerator.export.excel_exporter import ExcelExporter
from lvgenerator.gaeb.phase_converter import PhaseConverter
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter
from lvgenerator.models.address import Address
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.validators import ProjectValidator


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_full_project(phase=GAEBPhase.X84):
    cat = BoQCategory(id=str(uuid.uuid4()), rno_part="01", label="Rohbauarbeiten")
    cat.items.append(Item(
        id=str(uuid.uuid4()), rno_part="0010",
        qty=Decimal("100"), qu="m2", up=Decimal("25.00"), it=Decimal("2500.00"),
        description=ItemDescription(
            outline_text="Beton C25/30", detail_text="Liefern und einbauen"
        ),
    ))
    cat.items.append(Item(
        id=str(uuid.uuid4()), rno_part="0020",
        qty=Decimal("50"), qu="m3", up=Decimal("80.00"), it=Decimal("4000.00"),
        description=ItemDescription(outline_text="Bewehrungsstahl"),
    ))
    return GAEBProject(
        gaeb_info=GAEBInfo(),
        prj_info=PrjInfo(name="Integrationsprojekt", currency="EUR"),
        award_info=AwardInfo(boq_id=str(uuid.uuid4())),
        owner=Address(name1="Bauherr GmbH", city="Berlin", pcode="10115"),
        phase=phase,
        boq=BoQ(
            id=str(uuid.uuid4()),
            info=BoQInfo(name="Hauptgebaeude", breakdowns=[
                BoQBkdn(type="BoQLevel", length=2, numeric=True),
                BoQBkdn(type="Item", length=4, numeric=True),
            ]),
            categories=[cat],
        ),
    )


class TestProjectWorkflow:
    def test_save_and_reload(self, tmp_path):
        project = _make_full_project()
        writer = GAEBWriter()
        reader = GAEBReader()

        file_path = str(tmp_path / "test.x84")
        writer.write(project, file_path)
        reloaded = reader.read(file_path)

        assert reloaded.phase == GAEBPhase.X84
        assert reloaded.prj_info.name == "Integrationsprojekt"
        assert len(reloaded.boq.categories) == 1
        assert len(reloaded.boq.categories[0].items) == 2

    def test_prj_info_round_trip(self, tmp_path):
        project = _make_full_project()
        project.prj_info.label = "INT"
        project.prj_info.currency = "CHF"

        writer = GAEBWriter()
        reader = GAEBReader()
        file_path = str(tmp_path / "prjinfo.x84")
        writer.write(project, file_path)
        reloaded = reader.read(file_path)

        assert reloaded.prj_info.name == "Integrationsprojekt"
        assert reloaded.prj_info.currency == "CHF"

    def test_owner_address_round_trip(self, tmp_path):
        project = _make_full_project()
        writer = GAEBWriter()
        reader = GAEBReader()
        file_path = str(tmp_path / "owner.x84")
        writer.write(project, file_path)
        reloaded = reader.read(file_path)

        assert reloaded.owner is not None
        assert reloaded.owner.name1 == "Bauherr GmbH"
        assert reloaded.owner.city == "Berlin"

    def test_phase_convert_save_and_reload(self, tmp_path):
        project = _make_full_project(GAEBPhase.X84)
        converter = PhaseConverter()
        result = converter.convert(project, GAEBPhase.X83)
        converted = result.project

        writer = GAEBWriter()
        reader = GAEBReader()
        file_path = str(tmp_path / "converted.x83")
        writer.write(converted, file_path)
        reloaded = reader.read(file_path)

        assert reloaded.phase == GAEBPhase.X83
        for cat in reloaded.boq.categories:
            for item in cat.items:
                assert item.up is None
                assert item.it is None

    def test_validation_on_project(self):
        project = _make_full_project()
        result = ProjectValidator().validate(project)
        assert result.is_valid

    def test_excel_export_from_project(self, tmp_path):
        project = _make_full_project()
        exporter = ExcelExporter()
        file_path = str(tmp_path / "export.xlsx")
        exporter.export(project, file_path)
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) > 0

    def test_full_lifecycle_x84_to_x83_to_xlsx(self, tmp_path):
        """Full workflow: create X84, convert to X83, export to Excel."""
        project = _make_full_project(GAEBPhase.X84)

        # Convert
        converter = PhaseConverter()
        result = converter.convert(project, GAEBPhase.X83)
        x83_project = result.project
        assert x83_project.phase == GAEBPhase.X83

        # Save as X83
        writer = GAEBWriter()
        x83_path = str(tmp_path / "lifecycle.x83")
        writer.write(x83_project, x83_path)

        # Reload
        reader = GAEBReader()
        reloaded = reader.read(x83_path)
        assert reloaded.phase == GAEBPhase.X83
        assert len(reloaded.boq.categories[0].items) == 2

        # Export to Excel
        exporter = ExcelExporter()
        xlsx_path = str(tmp_path / "lifecycle.xlsx")
        exporter.export(reloaded, xlsx_path)
        assert os.path.exists(xlsx_path)

    def test_x84_fixture_round_trip_excel(self, tmp_path):
        """Read the fixture X84, export to Excel."""
        reader = GAEBReader()
        project = reader.read(str(FIXTURES / "sample_x84.xml"))
        exporter = ExcelExporter()
        xlsx_path = str(tmp_path / "fixture.xlsx")
        exporter.export(project, xlsx_path)
        assert os.path.exists(xlsx_path)
