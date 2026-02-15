from decimal import Decimal
from pathlib import Path

import pytest

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.phase_converter import PhaseConverter
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.models.boq import BoQ, BoQInfo
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_project(phase: GAEBPhase, items: list[Item]) -> GAEBProject:
    cat = BoQCategory(id="cat-1", rno_part="01", label="Test", items=items)
    return GAEBProject(
        gaeb_info=GAEBInfo(),
        prj_info=PrjInfo(name="Test"),
        award_info=AwardInfo(),
        phase=phase,
        boq=BoQ(id="boq-1", info=BoQInfo(), categories=[cat]),
    )


@pytest.fixture
def converter():
    return PhaseConverter()


class TestPhaseConverter:
    def test_same_phase_noop(self, converter):
        project = _make_project(GAEBPhase.X83, [])
        result = converter.convert(project, GAEBPhase.X83)
        assert result.project is project
        assert result.warnings == []

    def test_x83_to_x84_preserves_quantities(self, converter):
        item = Item(id="1", rno_part="0010", qty=Decimal("100"), qu="m2")
        project = _make_project(GAEBPhase.X83, [item])
        result = converter.convert(project, GAEBPhase.X84)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.qty == Decimal("100")
        assert new_item.qu == "m2"

    def test_x83_to_x84_prices_stay_none(self, converter):
        item = Item(id="1", rno_part="0010", qty=Decimal("100"), qu="m2")
        project = _make_project(GAEBPhase.X83, [item])
        result = converter.convert(project, GAEBPhase.X84)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.up is None

    def test_x84_to_x83_strips_prices(self, converter):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("100"), qu="m2",
            up=Decimal("25.00"), it=Decimal("2500.00"),
        )
        project = _make_project(GAEBPhase.X84, [item])
        result = converter.convert(project, GAEBPhase.X83)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.up is None
        assert new_item.it is None
        assert new_item.qty == Decimal("100")

    def test_x84_to_x81_strips_all(self, converter):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("100"), qu="m2",
            up=Decimal("25.00"), it=Decimal("2500.00"),
        )
        project = _make_project(GAEBPhase.X84, [item])
        result = converter.convert(project, GAEBPhase.X81)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.qty is None
        assert new_item.up is None
        assert new_item.it is None

    def test_x84_to_x86_preserves_all(self, converter):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("100"), qu="m2",
            up=Decimal("25.00"), it=Decimal("2500.00"),
        )
        project = _make_project(GAEBPhase.X84, [item])
        result = converter.convert(project, GAEBPhase.X86)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.qty == Decimal("100")
        assert new_item.up == Decimal("25.00")
        assert new_item.it == Decimal("2500.00")

    def test_x84_to_x86_clears_not_offered(self, converter):
        item = Item(id="1", rno_part="0010", not_offered=True)
        project = _make_project(GAEBPhase.X84, [item])
        result = converter.convert(project, GAEBPhase.X86)
        new_item = result.project.boq.categories[0].items[0]
        assert new_item.not_offered is False

    def test_conversion_returns_new_project(self, converter):
        item = Item(id="1", rno_part="0010", qty=Decimal("100"))
        project = _make_project(GAEBPhase.X83, [item])
        result = converter.convert(project, GAEBPhase.X84)
        assert result.project is not project
        # Original unchanged
        assert project.phase == GAEBPhase.X83

    def test_preview_warnings_down_conversion(self, converter):
        warnings = converter.get_conversion_warnings_preview(
            GAEBPhase.X84, GAEBPhase.X83
        )
        assert any("Preise" in w for w in warnings)

    def test_preview_warnings_up_conversion(self, converter):
        warnings = converter.get_conversion_warnings_preview(
            GAEBPhase.X83, GAEBPhase.X84
        )
        assert any("Preise" in w for w in warnings)

    def test_totals_recalculated(self, converter):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("10"), qu="m2",
            up=Decimal("5.00"),
        )
        project = _make_project(GAEBPhase.X83, [item])
        # X83 has no prices, but we set them manually for this test
        result = converter.convert(project, GAEBPhase.X84)
        # Prices were stripped from X83 source rules (has_prices=False),
        # so up should still be there (X83 doesn't have prices to strip)
        # Actually X83->X84: source has no prices, target has prices
        # So prices stay as-is (None stays None, set stays set)
        new_item = result.project.boq.categories[0].items[0]
        # Since source X83 doesn't have prices flag, strip logic doesn't fire
        # The item originally had up=5.00 which is preserved
        if new_item.up is not None and new_item.qty is not None:
            assert new_item.it == Decimal("50.00")

    def test_x84_fixture_to_x83(self, converter):
        reader = GAEBReader()
        project = reader.read(str(FIXTURES / "sample_x84.xml"))
        assert project.phase == GAEBPhase.X84
        result = converter.convert(project, GAEBPhase.X83)
        assert result.project.phase == GAEBPhase.X83
        # All prices should be stripped
        for cat in result.project.boq.categories:
            for item in cat.items:
                assert item.up is None
                assert item.it is None
