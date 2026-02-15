"""Umfassende Tests fuer den GAEBWriter."""
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter
from lvgenerator.models.address import Address
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo, Totals
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo


def _make_project(phase=GAEBPhase.X84, items=None, categories=None):
    if categories is None:
        cat = BoQCategory(id="cat-1", rno_part="01", label="Test")
        if items:
            cat.items = items
        categories = [cat]
    return GAEBProject(
        gaeb_info=GAEBInfo(),
        prj_info=PrjInfo(name="WriterTest"),
        award_info=AwardInfo(boq_id="award-1"),
        phase=phase,
        boq=BoQ(
            id="boq-1", info=BoQInfo(name="LV Test",
                breakdowns=[BoQBkdn(type="BoQLevel", length=2, numeric=True)]),
            categories=categories,
        ),
    )


class TestWriterOwnerAddress:
    def test_write_full_address(self, tmp_path):
        project = _make_project()
        project.owner = Address(
            name1="Firma AG", name2="Abteilung Bau", name3="z.Hd. Herr Meier",
            street="Musterstrasse 1", pcode="10115", city="Berlin",
        )
        path = str(tmp_path / "addr.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.owner.name1 == "Firma AG"
        assert reloaded.owner.name2 == "Abteilung Bau"
        assert reloaded.owner.name3 == "z.Hd. Herr Meier"
        assert reloaded.owner.street == "Musterstrasse 1"
        assert reloaded.owner.pcode == "10115"
        assert reloaded.owner.city == "Berlin"

    def test_write_no_owner(self, tmp_path):
        project = _make_project()
        project.owner = None
        path = str(tmp_path / "no_owner.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.owner is None

    def test_write_partial_address(self, tmp_path):
        project = _make_project()
        project.owner = Address(name1="Nur Name", city="Hamburg")
        path = str(tmp_path / "partial.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.owner.name1 == "Nur Name"
        assert reloaded.owner.city == "Hamburg"
        assert reloaded.owner.street == ""


class TestWriterPhases:
    def test_write_x81_no_quantities_no_prices(self, tmp_path):
        items = [Item(id="1", rno_part="0010", qty=Decimal("10"),
                       qu="m2", up=Decimal("5.00"), it=Decimal("50.00"))]
        project = _make_project(GAEBPhase.X81, items=items)
        path = str(tmp_path / "test.x81")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        item = reloaded.boq.categories[0].items[0]
        assert item.qty is None  # X81 has no quantities
        assert item.up is None
        assert item.it is None

    def test_write_x83_quantities_no_prices(self, tmp_path):
        items = [Item(id="1", rno_part="0010", qty=Decimal("10"),
                       qu="m2", up=Decimal("5.00"), it=Decimal("50.00"))]
        project = _make_project(GAEBPhase.X83, items=items)
        path = str(tmp_path / "test.x83")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        item = reloaded.boq.categories[0].items[0]
        assert item.qty == Decimal("10")
        assert item.up is None  # X83 has no prices
        assert item.it is None

    def test_write_x84_all_fields(self, tmp_path):
        items = [Item(id="1", rno_part="0010", qty=Decimal("10"),
                       qu="m2", up=Decimal("5.00"), it=Decimal("50.00"))]
        project = _make_project(GAEBPhase.X84, items=items)
        path = str(tmp_path / "test.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        item = reloaded.boq.categories[0].items[0]
        assert item.qty == Decimal("10")
        assert item.up == Decimal("5.00")
        assert item.it == Decimal("50.00")

    def test_write_x84_not_offered(self, tmp_path):
        items = [Item(id="1", rno_part="0010", not_offered=True)]
        project = _make_project(GAEBPhase.X84, items=items)
        path = str(tmp_path / "offered.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].items[0].not_offered is True

    def test_write_x86_no_not_offered(self, tmp_path):
        items = [Item(id="1", rno_part="0010", not_offered=True)]
        project = _make_project(GAEBPhase.X86, items=items)
        path = str(tmp_path / "test.x86")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        # X86 doesn't allow not_offered
        assert reloaded.boq.categories[0].items[0].not_offered is False


class TestWriterEdgeCases:
    def test_empty_boq(self, tmp_path):
        project = _make_project(categories=[])
        path = str(tmp_path / "empty.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert len(reloaded.boq.categories) == 0

    def test_deeply_nested_categories(self, tmp_path):
        inner = BoQCategory(id="c3", rno_part="01", label="Inner", items=[
            Item(id="i1", rno_part="0010",
                 description=ItemDescription(outline_text="Innermost")),
        ])
        mid = BoQCategory(id="c2", rno_part="01", label="Mid",
                          subcategories=[inner])
        outer = BoQCategory(id="c1", rno_part="01", label="Outer",
                            subcategories=[mid])
        project = _make_project(categories=[outer])
        path = str(tmp_path / "nested.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].label == "Outer"
        assert reloaded.boq.categories[0].subcategories[0].label == "Mid"
        assert reloaded.boq.categories[0].subcategories[0].subcategories[0].label == "Inner"

    def test_special_characters_in_text(self, tmp_path):
        items = [Item(
            id="1", rno_part="0010",
            description=ItemDescription(
                outline_text='Beton <C25/30> & "Sondermischung"',
                detail_text="Liefern & einbauen: <100m2>",
            ),
        )]
        project = _make_project(items=items)
        path = str(tmp_path / "special.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        item = reloaded.boq.categories[0].items[0]
        assert "<C25/30>" in item.description.outline_text
        assert "&" in item.description.detail_text

    def test_multiline_description(self, tmp_path):
        items = [Item(
            id="1", rno_part="0010",
            description=ItemDescription(
                outline_text="Zeile 1\nZeile 2",
                detail_text="Detail 1\nDetail 2\nDetail 3",
            ),
        )]
        project = _make_project(items=items)
        path = str(tmp_path / "multi.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        item = reloaded.boq.categories[0].items[0]
        assert "Zeile 1" in item.description.outline_text
        assert "Detail 1" in item.description.detail_text

    def test_item_with_vat(self, tmp_path):
        items = [Item(id="1", rno_part="0010", vat=Decimal("19.00"))]
        project = _make_project(items=items)
        path = str(tmp_path / "vat.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].items[0].vat == Decimal("19.00")

    def test_item_with_discount(self, tmp_path):
        items = [Item(id="1", rno_part="0010",
                       up=Decimal("100.00"), it=Decimal("100.00"),
                       discount_pcnt=Decimal("10.00"))]
        project = _make_project(GAEBPhase.X84, items=items)
        path = str(tmp_path / "discount.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].items[0].discount_pcnt == Decimal("10.00")

    def test_qty_tbd_flag(self, tmp_path):
        items = [Item(id="1", rno_part="0010", qty_tbd=True)]
        project = _make_project(GAEBPhase.X83, items=items)
        path = str(tmp_path / "tbd.x83")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].items[0].qty_tbd is True

    def test_hour_it_flag(self, tmp_path):
        items = [Item(id="1", rno_part="0010", hour_it=True)]
        project = _make_project(items=items)
        path = str(tmp_path / "hour.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.categories[0].items[0].hour_it is True


class TestWriterPrjInfo:
    def test_prj_info_round_trip(self, tmp_path):
        project = _make_project()
        project.prj_info.name = "Testprojekt Gross"
        project.prj_info.label = "TPG"
        project.prj_info.currency = "CHF"
        project.prj_info.currency_label = "Schweizer Franken"
        path = str(tmp_path / "prj.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.prj_info.name == "Testprojekt Gross"
        assert reloaded.prj_info.currency == "CHF"
        assert reloaded.prj_info.currency_label == "Schweizer Franken"

    def test_prj_info_empty_name(self, tmp_path):
        project = _make_project()
        project.prj_info.name = ""
        project.prj_info.label = ""
        path = str(tmp_path / "empty_prj.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.prj_info.name == ""

    def test_boq_info_round_trip(self, tmp_path):
        project = _make_project()
        project.boq.info.name = "Hauptgebaeude"
        project.boq.info.label = "HG"
        path = str(tmp_path / "boq_info.x84")
        GAEBWriter().write(project, path)
        reloaded = GAEBReader().read(path)
        assert reloaded.boq.info.name == "Hauptgebaeude"
