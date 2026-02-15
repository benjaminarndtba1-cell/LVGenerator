import os
import tempfile
from decimal import Decimal

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter


class TestGAEBWriter:

    def test_round_trip_x83(self, sample_x83):
        reader = GAEBReader()
        writer = GAEBWriter()

        original = reader.read(sample_x83)

        with tempfile.NamedTemporaryFile(suffix=".x83", delete=False) as f:
            tmp_path = f.name

        try:
            writer.write(original, tmp_path)
            reloaded = reader.read(tmp_path)

            assert reloaded.phase == GAEBPhase.X83
            assert reloaded.prj_info.name == original.prj_info.name
            assert reloaded.prj_info.currency == original.prj_info.currency
            assert reloaded.boq is not None
            assert len(reloaded.boq.categories) == len(original.boq.categories)
        finally:
            os.unlink(tmp_path)

    def test_round_trip_items_preserved(self, sample_x83):
        reader = GAEBReader()
        writer = GAEBWriter()

        original = reader.read(sample_x83)

        with tempfile.NamedTemporaryFile(suffix=".x83", delete=False) as f:
            tmp_path = f.name

        try:
            writer.write(original, tmp_path)
            reloaded = reader.read(tmp_path)

            orig_items = original.boq.categories[0].subcategories[0].items
            reload_items = reloaded.boq.categories[0].subcategories[0].items

            assert len(reload_items) == len(orig_items)
            for orig, reloaded_item in zip(orig_items, reload_items):
                assert reloaded_item.qty == orig.qty
                assert reloaded_item.qu == orig.qu
                assert reloaded_item.description.outline_text == orig.description.outline_text
        finally:
            os.unlink(tmp_path)

    def test_x83_omits_prices(self, sample_x83):
        reader = GAEBReader()
        writer = GAEBWriter()

        project = reader.read(sample_x83)
        # Manually set a price (should be omitted in X83 output)
        project.boq.categories[0].subcategories[0].items[0].up = Decimal("99.99")

        with tempfile.NamedTemporaryFile(suffix=".x83", delete=False) as f:
            tmp_path = f.name

        try:
            writer.write(project, tmp_path)
            reloaded = reader.read(tmp_path)
            # X83 writer should omit UP
            item = reloaded.boq.categories[0].subcategories[0].items[0]
            assert item.up is None
        finally:
            os.unlink(tmp_path)

    def test_write_x84_includes_prices(self, sample_x83):
        reader = GAEBReader()
        writer = GAEBWriter()

        project = reader.read(sample_x83)
        project.phase = GAEBPhase.X84
        # Set prices
        for cat in project.boq.categories:
            for subcat in cat.subcategories:
                for item in subcat.items:
                    item.up = Decimal("50.00")
                    item.it = item.calculate_total() if item.qty else None
            for item in cat.items:
                item.up = Decimal("50.00")
                item.it = item.calculate_total() if item.qty else None

        with tempfile.NamedTemporaryFile(suffix=".x84", delete=False) as f:
            tmp_path = f.name

        try:
            writer.write(project, tmp_path)
            reloaded = reader.read(tmp_path)
            assert reloaded.phase == GAEBPhase.X84
            item = reloaded.boq.categories[0].subcategories[0].items[0]
            assert item.up == Decimal("50.00")
        finally:
            os.unlink(tmp_path)
