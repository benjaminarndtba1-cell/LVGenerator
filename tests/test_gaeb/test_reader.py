from decimal import Decimal

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.reader import GAEBReader


class TestGAEBReader:

    def test_read_x83_phase(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        assert project.phase == GAEBPhase.X83

    def test_read_x83_project_info(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        assert project.prj_info.name == "Testprojekt Neubau"
        assert project.prj_info.label == "TP-2024"
        assert project.prj_info.currency == "EUR"

    def test_read_x83_gaeb_info(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        assert project.gaeb_info.version == "3.2"
        assert project.gaeb_info.prog_name == "LVGenerator Test"

    def test_read_x83_award_info(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        assert project.award_info.boq_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert project.award_info.currency == "EUR"

    def test_read_x83_boq(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        assert project.boq is not None
        assert project.boq.id == "boq-001"
        assert project.boq.info.name == "Neubau Buerogebaeude"

    def test_read_x83_breakdowns(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        bkdns = project.boq.info.breakdowns
        assert len(bkdns) == 2
        assert bkdns[0].type == "BoQLevel"
        assert bkdns[0].length == 2
        assert bkdns[1].type == "Item"

    def test_read_x83_categories(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        cats = project.boq.categories
        assert len(cats) == 2
        assert cats[0].rno_part == "01"
        assert cats[0].label == "Rohbauarbeiten"
        assert cats[1].rno_part == "02"
        assert cats[1].label == "Dacharbeiten"

    def test_read_x83_subcategories(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        subcats = project.boq.categories[0].subcategories
        assert len(subcats) == 2
        assert subcats[0].label == "Erdarbeiten"
        assert subcats[1].label == "Betonarbeiten"

    def test_read_x83_items(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        # Erdarbeiten items
        items = project.boq.categories[0].subcategories[0].items
        assert len(items) == 2
        assert items[0].rno_part == "0010"
        assert items[0].qty == Decimal("150.000")
        assert items[0].qu == "m3"
        assert items[0].description.outline_text == "Boden loesen und lagern"

    def test_read_x83_no_prices(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        items = project.boq.categories[0].subcategories[0].items
        for item in items:
            assert item.up is None
            assert item.it is None

    def test_read_x83_detail_text(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        item = project.boq.categories[0].subcategories[0].items[0]
        assert "Boden loesen" in item.description.detail_text
        assert "Bodenklasse 3-5" in item.description.detail_text

    def test_read_x83_total_items(self, sample_x83):
        reader = GAEBReader()
        project = reader.read(sample_x83)
        # Count all items across all categories
        total = 0
        for cat in project.boq.categories:
            for subcat in cat.subcategories:
                total += len(subcat.items)
            total += len(cat.items)
        assert total == 4
