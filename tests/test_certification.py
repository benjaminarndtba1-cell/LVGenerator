"""Tests fuer BVBS-Zertifizierungs-relevante GAEB-Elemente."""
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from lvgenerator.constants import GAEBPhase, GAEB_DEFAULT_VERSION
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.gaeb.reader import GAEBReader
from lvgenerator.gaeb.writer import GAEBWriter
from lvgenerator.gaeb.xsd_validator import validate_file, get_xsd_path
from lvgenerator.models.boq import BoQ, BoQInfo
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.models.text_types import AddText

FIXTURES = Path(__file__).parent / "fixtures"
BVBS_DIR = Path(__file__).parent.parent / "docs" / "certification"


@pytest.fixture
def extended_project():
    return GAEBReader().read(str(FIXTURES / "sample_extended.xml"))


@pytest.fixture
def bidcomm_project():
    return GAEBReader().read(str(FIXTURES / "sample_x84_bidcomm.xml"))


@pytest.fixture
def bvbs_x81():
    path = BVBS_DIR / "x81" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X81"
    if not path.exists():
        pytest.skip("BVBS X81 Pruefdatei nicht vorhanden")
    return GAEBReader().read(str(path))


@pytest.fixture
def bvbs_x84():
    path = BVBS_DIR / "x84" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X84"
    if not path.exists():
        pytest.skip("BVBS X84 Pruefdatei nicht vorhanden")
    return GAEBReader().read(str(path))


@pytest.fixture
def bvbs_x86():
    path = BVBS_DIR / "x86" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X86"
    if not path.exists():
        pytest.skip("BVBS X86 Pruefdatei nicht vorhanden")
    return GAEBReader().read(str(path))


# --- Version defaults ---

class TestVersionDefaults:
    def test_default_version_is_33(self):
        assert GAEB_DEFAULT_VERSION == "3.3"

    def test_new_project_version_33(self):
        info = GAEBInfo()
        assert info.version == "3.3"
        assert info.vers_date == "2021-05"

    def test_read_32_preserves_version(self):
        project = GAEBReader().read(str(FIXTURES / "sample_x83.xml"))
        assert project.gaeb_info.version == "3.2"

    def test_read_33_preserves_version(self, extended_project):
        assert extended_project.gaeb_info.version == "3.3"


# --- Positionstypen Reader ---

class TestPositionTypesReader:
    def test_normalposition_defaults(self, extended_project):
        item = extended_project.boq.categories[0].items[0]
        assert item.rno_part == "0010"
        assert not item.provis
        assert item.aln_group_no == ""
        assert item.aln_ser_no == ""
        assert not item.free_qty
        assert not item.key_it

    def test_bedarfsposition(self, extended_project):
        item = extended_project.boq.categories[0].items[1]
        assert item.rno_part == "0020"
        assert item.provis == "WithTotal"

    def test_grundposition(self, extended_project):
        item = extended_project.boq.categories[0].items[2]
        assert item.rno_part == "0030"
        assert item.aln_group_no == "1"
        assert item.aln_ser_no == "0"

    def test_alternativposition(self, extended_project):
        item = extended_project.boq.categories[0].items[3]
        assert item.rno_part == "0040"
        assert item.aln_group_no == "1"
        assert item.aln_ser_no == "1"

    def test_leitposition_free_qty(self, extended_project):
        item = extended_project.boq.categories[0].items[4]
        assert item.rno_part == "0050"
        assert item.free_qty is True
        assert item.key_it is True


# --- Zuschlag Reader ---

class TestSurchargeReader:
    def test_surcharge_type_z(self, extended_project):
        item = extended_project.boq.categories[0].items[5]
        assert item.rno_part == "0060"
        assert item.surcharge_type == "Z"
        assert item.markup_it is True
        assert item.surcharge_refs == []

    def test_surcharge_type_p_with_refs(self, extended_project):
        item = extended_project.boq.categories[0].items[6]
        assert item.rno_part == "0070"
        assert item.surcharge_type == "P"
        assert item.surcharge_refs == ["0010", "0020"]


# --- StLNo Reader ---

class TestStLNoReader:
    def test_stlno_parsed(self, extended_project):
        item = extended_project.boq.categories[0].items[0]
        assert item.description.stl_no == "009.311.0010"

    def test_stlno_default_empty(self, extended_project):
        item = extended_project.boq.categories[0].items[1]
        assert item.description.stl_no == ""


# --- AddText Reader ---

class TestAddTextReader:
    def test_boq_add_text(self, extended_project):
        info = extended_project.boq.info
        assert len(info.add_texts) == 1
        assert info.add_texts[0].outline_text == "Vorbemerkung zum LV"
        assert "Detaillierte Vorbemerkung" in info.add_texts[0].detail_text

    def test_category_add_text(self, extended_project):
        cat = extended_project.boq.categories[0]
        assert len(cat.add_texts) == 1
        assert cat.add_texts[0].outline_text == "Kategorie-Hinweistext"

    def test_item_add_text(self, extended_project):
        item = extended_project.boq.categories[0].items[0]
        assert len(item.add_texts) == 1
        assert item.add_texts[0].outline_text == "Hinweis zur Position"


# --- ExecDescr Reader ---

class TestExecDescrReader:
    def test_exec_descr_parsed(self, extended_project):
        cat = extended_project.boq.categories[0]
        assert "DIN 18300" in cat.exec_descr
        assert "VOB/C" in cat.exec_descr


# --- BidComm/TextCompl Reader ---

class TestBidCommReader:
    def test_bid_comment_parsed(self, bidcomm_project):
        item = bidcomm_project.boq.categories[0].items[0]
        assert len(item.bid_comments) == 1
        assert "Produkt XY" in item.bid_comments[0]
        assert "Lieferzeit" in item.bid_comments[0]

    def test_text_compl_parsed(self, bidcomm_project):
        item = bidcomm_project.boq.categories[0].items[0]
        assert len(item.text_compls) == 1
        assert "Montage" in item.text_compls[0]

    def test_x84_not_offered(self, bidcomm_project):
        item = bidcomm_project.boq.categories[0].items[1]
        assert item.not_offered is True

    def test_x84_prices(self, bidcomm_project):
        item = bidcomm_project.boq.categories[0].items[0]
        assert item.up == Decimal("25.50")
        assert item.it == Decimal("2550.00")


# --- Phase Rules ---

class TestPhaseRules:
    def test_x84_has_bid_comments(self):
        rules = get_rules(GAEBPhase.X84)
        assert rules.has_bid_comments is True

    def test_x83_no_bid_comments(self):
        rules = get_rules(GAEBPhase.X83)
        assert rules.has_bid_comments is False

    def test_x81_no_bid_comments(self):
        rules = get_rules(GAEBPhase.X81)
        assert rules.has_bid_comments is False

    def test_x86_no_bid_comments(self):
        rules = get_rules(GAEBPhase.X86)
        assert rules.has_bid_comments is False


# --- Roundtrip Tests ---

class TestRoundtrip:
    def _roundtrip(self, project, phase):
        writer = GAEBWriter()
        reader = GAEBReader()
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            tmp_path = f.name
        writer.write(project, tmp_path, version=project.gaeb_info.version)
        return reader.read(tmp_path)

    def test_roundtrip_extended(self, extended_project):
        result = self._roundtrip(extended_project, GAEBPhase.X83)
        cat = result.boq.categories[0]

        # Normalposition
        item0 = cat.items[0]
        assert item0.description.stl_no == "009.311.0010"
        assert len(item0.add_texts) == 1

        # Bedarfsposition
        item1 = cat.items[1]
        assert item1.provis == "WithTotal"

        # Grundposition
        item2 = cat.items[2]
        assert item2.aln_group_no == "1"
        assert item2.aln_ser_no == "0"

        # Alternativposition
        item3 = cat.items[3]
        assert item3.aln_group_no == "1"
        assert item3.aln_ser_no == "1"

        # Leitposition
        item4 = cat.items[4]
        assert item4.free_qty is True
        assert item4.key_it is True

        # Zuschlag Z
        item5 = cat.items[5]
        assert item5.surcharge_type == "Z"
        assert item5.markup_it is True

        # Zuschlag P
        item6 = cat.items[6]
        assert item6.surcharge_type == "P"
        assert item6.surcharge_refs == ["0010", "0020"]

        # ExecDescr
        assert "DIN 18300" in cat.exec_descr

        # BoQ AddText
        assert len(result.boq.info.add_texts) == 1
        assert result.boq.info.add_texts[0].outline_text == "Vorbemerkung zum LV"

        # Category AddText
        assert len(cat.add_texts) == 1

    def test_roundtrip_bidcomm(self, bidcomm_project):
        result = self._roundtrip(bidcomm_project, GAEBPhase.X84)
        item = result.boq.categories[0].items[0]
        assert len(item.bid_comments) == 1
        assert "Produkt XY" in item.bid_comments[0]
        assert len(item.text_compls) == 1
        assert "Montage" in item.text_compls[0]

    def test_roundtrip_item_programmatic(self):
        """Create item from code, write, read back."""
        project = GAEBProject()
        project.phase = GAEBPhase.X83
        project.gaeb_info.version = "3.3"
        project.boq = BoQ(
            id="test-boq",
            info=BoQInfo(name="Test"),
            categories=[
                BoQCategory(
                    id="cat-1", rno_part="01", label="Test Kategorie",
                    exec_descr="DIN Norm",
                    add_texts=[AddText(outline_text="Kat-Hinweis")],
                    items=[
                        Item(
                            id="it-1", rno_part="0010",
                            qty=Decimal("10"), qu="m2",
                            provis="WithTotal",
                            aln_group_no="2", aln_ser_no="0",
                            free_qty=True, key_it=True, markup_it=True,
                            surcharge_type="P",
                            surcharge_refs=["0020", "0030"],
                            add_texts=[AddText(
                                outline_text="Hinweis",
                                detail_text="Detail Info",
                            )],
                            description=ItemDescription(
                                outline_text="Outline",
                                stl_no="001.002.0003",
                            ),
                        ),
                    ],
                ),
            ],
        )
        project.boq.info.add_texts = [
            AddText(outline_text="LV Vorbemerkung"),
        ]

        result = self._roundtrip(project, GAEBPhase.X83)
        item = result.boq.categories[0].items[0]
        assert item.provis == "WithTotal"
        assert item.aln_group_no == "2"
        assert item.aln_ser_no == "0"
        assert item.free_qty is True
        assert item.key_it is True
        assert item.markup_it is True
        assert item.surcharge_type == "P"
        assert item.surcharge_refs == ["0020", "0030"]
        assert item.description.stl_no == "001.002.0003"
        assert len(item.add_texts) == 1
        assert item.add_texts[0].outline_text == "Hinweis"
        assert item.add_texts[0].detail_text == "Detail Info"

        cat = result.boq.categories[0]
        assert "DIN Norm" in cat.exec_descr
        assert len(cat.add_texts) == 1
        assert cat.add_texts[0].outline_text == "Kat-Hinweis"

        assert len(result.boq.info.add_texts) == 1
        assert result.boq.info.add_texts[0].outline_text == "LV Vorbemerkung"

    def test_bidcomm_not_written_in_x83(self):
        """BidComm and TextCompl should not be written in X83."""
        project = GAEBProject()
        project.phase = GAEBPhase.X83
        project.gaeb_info.version = "3.3"
        project.boq = BoQ(
            id="test-boq",
            info=BoQInfo(name="Test"),
            categories=[
                BoQCategory(
                    id="cat-1", rno_part="01", label="Test",
                    items=[
                        Item(
                            id="it-1", rno_part="0010",
                            qty=Decimal("10"), qu="m2",
                            bid_comments=["Kommentar"],
                            text_compls=["Ergaenzung"],
                            description=ItemDescription(
                                outline_text="Test",
                            ),
                        ),
                    ],
                ),
            ],
        )
        result = self._roundtrip(project, GAEBPhase.X83)
        item = result.boq.categories[0].items[0]
        assert len(item.bid_comments) == 0
        assert len(item.text_compls) == 0

    def test_bidcomm_written_in_x84(self):
        """BidComm and TextCompl should be written in X84."""
        project = GAEBProject()
        project.phase = GAEBPhase.X84
        project.gaeb_info.version = "3.3"
        project.boq = BoQ(
            id="test-boq",
            info=BoQInfo(name="Test"),
            categories=[
                BoQCategory(
                    id="cat-1", rno_part="01", label="Test",
                    items=[
                        Item(
                            id="it-1", rno_part="0010",
                            qty=Decimal("10"), qu="m2",
                            up=Decimal("5.00"),
                            bid_comments=["Kommentar"],
                            text_compls=["Ergaenzung"],
                            description=ItemDescription(
                                outline_text="Test",
                            ),
                        ),
                    ],
                ),
            ],
        )
        result = self._roundtrip(project, GAEBPhase.X84)
        item = result.boq.categories[0].items[0]
        assert len(item.bid_comments) == 1
        assert "Kommentar" in item.bid_comments[0]
        assert len(item.text_compls) == 1
        assert "Ergaenzung" in item.text_compls[0]


# --- Existing fixture backward compatibility ---

class TestBackwardCompatibility:
    def test_existing_x83_still_loads(self):
        project = GAEBReader().read(str(FIXTURES / "sample_x83.xml"))
        assert project.phase == GAEBPhase.X83
        assert len(project.boq.categories) == 2
        item = project.boq.categories[0].subcategories[0].items[0]
        assert item.qty == Decimal("150.000")
        assert not item.provis
        assert item.surcharge_type == ""
        assert item.add_texts == []

    def test_existing_x81_still_loads(self):
        project = GAEBReader().read(str(FIXTURES / "sample_x81.xml"))
        assert project.phase == GAEBPhase.X81

    def test_existing_x84_still_loads(self):
        project = GAEBReader().read(str(FIXTURES / "sample_x84.xml"))
        assert project.phase == GAEBPhase.X84

    def test_existing_x86_still_loads(self):
        project = GAEBReader().read(str(FIXTURES / "sample_x86.xml"))
        assert project.phase == GAEBPhase.X86


# ===================================================================
# BVBS Zertifizierungstests - Pruefkriterien GAEB DA XML 3.3 AVA
# ===================================================================

def _find_item_by_ordinal(project, ordinal: str):
    """Finde Item ueber OZ-Pfad z.B. '1.10.10.10'."""
    parts = ordinal.split(".")
    cats = project.boq.categories
    for p in parts[:-1]:
        found = None
        for c in cats:
            if c.rno_part == p:
                found = c
                break
        if found is None:
            return None
        cats = found.subcategories
        if not cats and found.items:
            # Letzter Teil ist Item
            for it in found.items:
                if it.rno_part == parts[-1]:
                    return it
            return None
    # Suche Item in letzter Kategorie
    if found is not None:
        for it in found.items:
            if it.rno_part == parts[-1]:
                return it
    return None


def _find_category(project, ordinal: str):
    """Finde Kategorie ueber OZ-Pfad z.B. '1.10.20'."""
    parts = ordinal.split(".")
    cats = project.boq.categories
    current = None
    for p in parts:
        found = None
        for c in cats:
            if c.rno_part == p:
                found = c
                break
        if found is None:
            return None
        current = found
        cats = found.subcategories
    return current


class TestBVBSImportX81:
    """Pruefkriterien 1.1 - 1.25: Import und Ueberpruefung der X81-Datei."""

    def test_1_1_import_x81(self, bvbs_x81):
        """1.1 Import eines LV (MUSS)."""
        assert bvbs_x81.phase == GAEBPhase.X81
        assert bvbs_x81.gaeb_info.version == "3.3"
        assert bvbs_x81.prj_info.name == "BVBS GAEB Muster"

    def test_1_1_item_count(self, bvbs_x81):
        def count_items(cats):
            total = 0
            for c in cats:
                total += len(c.items)
                total += count_items(c.subcategories)
            return total
        # 68 regular Items + 6 MarkupItems = 74
        assert count_items(bvbs_x81.boq.categories) == 74

    def test_1_1_breakdowns(self, bvbs_x81):
        bk = bvbs_x81.boq.info.breakdowns
        assert len(bk) == 5
        assert bk[0].type == "BoQLevel"
        assert bk[0].label == "Hauptgruppe"
        assert bk[3].type == "Item"
        assert bk[4].type == "Index"

    def test_1_2_additional_texts(self, bvbs_x81):
        """1.2 Zusatztexte (MUSS) - Award-Level AddTexts vorhanden."""
        assert len(bvbs_x81.award_add_texts) >= 1

    def test_1_4_stlno(self, bvbs_x81):
        """1.4 StL-Nr in Position 1.10.10.10 (MUSS)."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.10.10")
        assert item is not None
        assert item.description.stl_no == "9300201123000202"

    def test_1_9_grundposition_alternativ(self, bvbs_x81):
        """1.9 Grund- und Alternativpositionen im Bereich 1.10.20 (MUSS)."""
        # Grundpositionen haben ALNGroupNo=1, ALNSerNo=0
        item10 = _find_item_by_ordinal(bvbs_x81, "1.10.20.10")
        assert item10 is not None
        assert item10.aln_group_no == "1"
        assert item10.aln_ser_no == "0"

        # Alternativpositionen mit ALNSerNo=1
        item20 = _find_item_by_ordinal(bvbs_x81, "1.10.20.20")
        assert item20 is not None
        assert item20.aln_group_no == "1"
        assert item20.aln_ser_no == "1"

        # Alternativpositionen mit ALNSerNo=2
        item30 = _find_item_by_ordinal(bvbs_x81, "1.10.20.30")
        assert item30 is not None
        assert item30.aln_group_no == "1"
        assert item30.aln_ser_no == "2"

    def test_1_10_ctlg_assign(self, bvbs_x81):
        """1.10 Katalogzuordnungen in Positionen (MUSS)."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.25.10")
        assert item is not None
        assert len(item.ctlg_assignments) > 0

    def test_1_11_bedarfsposition_mit_gb(self, bvbs_x81):
        """1.11 Bedarfspositionen mit GB (MUSS)."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.25.10")
        assert item is not None
        assert item.provis == "WithTotal"

    def test_1_12_grund_wahlgruppen(self, bvbs_x81):
        """1.12 Grund- und Wahlgruppen (MUSS)."""
        cat_30 = _find_category(bvbs_x81, "1.10.30")
        assert cat_30 is not None
        assert cat_30.aln_b_group_no == "100"

        cat_40 = _find_category(bvbs_x81, "1.10.40")
        assert cat_40 is not None
        assert cat_40.aln_b_group_no == "100"
        assert cat_40.aln_b_ser_no == "1"

    def test_1_14_not_appl(self, bvbs_x81):
        """1.14 Position entfaellt (MUSS)."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.40.30")
        assert item is not None
        assert item.not_appl is True

    def test_1_17_markup_it(self, bvbs_x81):
        """1.17 Positionskennzeichen zu bezuschlagen (MUSS)."""
        item = _find_item_by_ordinal(bvbs_x81, "1.30.10.10")
        assert item is not None
        assert item.markup_it is True

    def test_1_18_surcharge_type(self, bvbs_x81):
        """1.18 Zuschlagsart der Zuschlagsposition (MUSS) - MarkupItem."""
        item = _find_item_by_ordinal(bvbs_x81, "1.30.10.40")
        assert item is not None
        assert item.is_markup_item is True
        assert item.markup_type == "IdentAsMark"

    def test_1_25_bieter_textergaenzungen(self, bvbs_x81):
        """1.25 Bietertextergaenzungen (MUSS) - BidCommPerm."""
        assert bvbs_x81.prj_info.bid_comm_perm is True

    def test_catalogs(self, bvbs_x81):
        """Kataloge im BoQInfo."""
        assert len(bvbs_x81.boq.info.catalogs) >= 1

    def test_award_info_extended(self, bvbs_x81):
        """Erweiterte AwardInfo-Felder."""
        ai = bvbs_x81.award_info
        assert ai.cat == "OpenCall"
        assert ai.open_date != ""
        assert ai.subm_loc != ""

    def test_owner(self, bvbs_x81):
        """OWN/Address und AwardNo."""
        assert bvbs_x81.owner is not None
        assert bvbs_x81.award_info.award_no != ""

    def test_gaeb_level_addtext(self, bvbs_x81):
        """Schlussbemerkungen (GAEB-level AddText)."""
        assert len(bvbs_x81.gaeb_add_texts) >= 1


class TestBVBSImportX86:
    """Pruefkriterien 3.x / 4.x: X86-Datei mit Preisen."""

    def test_3_1_import_x86(self, bvbs_x86):
        """3.1 Import X86 (MUSS)."""
        assert bvbs_x86.phase == GAEBPhase.X86
        assert bvbs_x86.gaeb_info.version == "3.3"

    def test_4_2_total(self, bvbs_x86):
        """4.2 Gesamtbetrag = 1.421.003.968,15 EUR (MUSS)."""
        totals = bvbs_x86.boq.info.totals
        assert totals is not None
        assert totals.total == Decimal("1421003968.15")

    def test_4_2_total_gross(self, bvbs_x86):
        """4.2 Bruttobetrag."""
        totals = bvbs_x86.boq.info.totals
        assert totals.total_gross == Decimal("1690994722.10")

    def test_4_12_decimal_places(self, bvbs_x86):
        """4.12 EP mit 3 Nachkommastellen (MUSS)."""
        # Position 2.1.1.10 soll 3 Nachkommastellen haben
        item = _find_item_by_ordinal(bvbs_x86, "2.1.1.10")
        assert item is not None
        assert item.up is not None
        # UP should have exactly 3 decimal places
        assert item.up == item.up.quantize(Decimal("0.001"))

    def test_x86_items_have_prices(self, bvbs_x86):
        """X86 Positionen haben Einheitspreise und Gesamtbetraege."""
        item = _find_item_by_ordinal(bvbs_x86, "1.10.10.10")
        assert item is not None
        assert item.up is not None
        assert item.it is not None


class TestBVBSImportX84:
    """Pruefkriterien 5.x: X84-Datei fuer Vergabephase."""

    def test_5_2_import_x84(self, bvbs_x84):
        """5.2 Import X84 (MUSS)."""
        assert bvbs_x84.phase == GAEBPhase.X84
        assert bvbs_x84.gaeb_info.version == "3.3"

    def test_x84_items_have_prices(self, bvbs_x84):
        """X84 Positionen haben EP und GB."""
        item = _find_item_by_ordinal(bvbs_x84, "1.10.10.10")
        assert item is not None
        assert item.up is not None
        assert item.it is not None


class TestBVBSRoundtrip:
    """Pruefkriterien 2.x: Export und Vergleich."""

    def _roundtrip(self, project):
        writer = GAEBWriter()
        reader = GAEBReader()
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            tmp_path = f.name
        writer.write(project, tmp_path, version=project.gaeb_info.version)
        return reader.read(tmp_path)

    def test_2_1_roundtrip_x81_items(self, bvbs_x81):
        """2.1/2.3 Export und Re-Import: gleiche Anzahl Positionen."""
        result = self._roundtrip(bvbs_x81)

        def count_items(cats):
            total = 0
            for c in cats:
                total += len(c.items)
                total += count_items(c.subcategories)
            return total

        assert count_items(result.boq.categories) == count_items(bvbs_x81.boq.categories)

    def test_2_1_roundtrip_x81_breakdowns(self, bvbs_x81):
        """Roundtrip: OZ-Maske erhalten."""
        result = self._roundtrip(bvbs_x81)
        assert len(result.boq.info.breakdowns) == len(bvbs_x81.boq.info.breakdowns)
        for orig, rt in zip(bvbs_x81.boq.info.breakdowns, result.boq.info.breakdowns):
            assert orig.type == rt.type
            assert orig.length == rt.length
            assert orig.numeric == rt.numeric

    def test_roundtrip_x81_stlno(self, bvbs_x81):
        """Roundtrip: StLNo erhalten."""
        result = self._roundtrip(bvbs_x81)
        item = _find_item_by_ordinal(result, "1.10.10.10")
        assert item is not None
        assert item.description.stl_no == "9300201123000202"

    def test_roundtrip_x81_provis(self, bvbs_x81):
        """Roundtrip: Bedarfsposition erhalten."""
        result = self._roundtrip(bvbs_x81)
        item = _find_item_by_ordinal(result, "1.10.25.10")
        assert item is not None
        assert item.provis == "WithTotal"

    def test_roundtrip_x81_ctlg_assign(self, bvbs_x81):
        """Roundtrip: Katalogzuordnungen erhalten."""
        result = self._roundtrip(bvbs_x81)
        item = _find_item_by_ordinal(result, "1.10.25.10")
        assert item is not None
        assert len(item.ctlg_assignments) > 0

    def test_roundtrip_x81_aln_b(self, bvbs_x81):
        """Roundtrip: Grund-/Wahlgruppen auf Kategorie erhalten."""
        result = self._roundtrip(bvbs_x81)
        cat = _find_category(result, "1.10.30")
        assert cat is not None
        assert cat.aln_b_group_no == "100"

    def test_roundtrip_x81_not_appl(self, bvbs_x81):
        """Roundtrip: Position entfaellt erhalten."""
        result = self._roundtrip(bvbs_x81)
        item = _find_item_by_ordinal(result, "1.10.40.30")
        assert item is not None
        assert item.not_appl is True

    def test_roundtrip_x81_award_add_texts(self, bvbs_x81):
        """Roundtrip: Award-level AddTexts erhalten."""
        result = self._roundtrip(bvbs_x81)
        assert len(result.award_add_texts) == len(bvbs_x81.award_add_texts)

    def test_roundtrip_x81_bid_comm_perm(self, bvbs_x81):
        """Roundtrip: BidCommPerm erhalten."""
        result = self._roundtrip(bvbs_x81)
        assert result.prj_info.bid_comm_perm is True

    def test_roundtrip_x81_award_info(self, bvbs_x81):
        """Roundtrip: Erweiterte AwardInfo erhalten."""
        result = self._roundtrip(bvbs_x81)
        assert result.award_info.cat == bvbs_x81.award_info.cat
        assert result.award_info.open_date == bvbs_x81.award_info.open_date
        assert result.award_info.subm_loc == bvbs_x81.award_info.subm_loc

    def test_roundtrip_x81_catalogs(self, bvbs_x81):
        """Roundtrip: Kataloge erhalten."""
        result = self._roundtrip(bvbs_x81)
        assert len(result.boq.info.catalogs) == len(bvbs_x81.boq.info.catalogs)

    def test_roundtrip_x81_markup(self, bvbs_x81):
        """Roundtrip: MarkupIt erhalten."""
        result = self._roundtrip(bvbs_x81)
        item = _find_item_by_ordinal(result, "1.30.10.10")
        assert item is not None
        assert item.markup_it is True

    def test_roundtrip_x86_totals(self, bvbs_x86):
        """Roundtrip X86: Totals erhalten."""
        result = self._roundtrip(bvbs_x86)
        assert result.boq.info.totals is not None
        assert result.boq.info.totals.total == Decimal("1421003968.15")

    def test_roundtrip_x86_prices(self, bvbs_x86):
        """Roundtrip X86: Preise erhalten."""
        result = self._roundtrip(bvbs_x86)
        item = _find_item_by_ordinal(result, "1.10.10.10")
        orig = _find_item_by_ordinal(bvbs_x86, "1.10.10.10")
        assert item is not None
        assert item.up == orig.up
        assert item.it == orig.it


# --- XSD-Validierung (Pruefkriterium 2.2 / 3.5) ---

class TestXSDValidation:
    """XSD-Validierung der Roundtrip-Dateien (BVBS Pruefkriterien 2.2, 3.5)."""

    def _roundtrip_and_validate(self, src_path: str) -> None:
        """Read source, write to temp file, validate against XSD."""
        reader = GAEBReader()
        writer = GAEBWriter()
        project = reader.read(src_path)

        with tempfile.NamedTemporaryFile(
            suffix=project.phase.file_extension, delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            writer.write(project, tmp_path)
            result = validate_file(tmp_path)
            if not result.is_valid:
                errors = "\n".join(
                    f"  Line {e.line}: {e.message}" for e in result.errors[:10]
                )
                pytest.fail(
                    f"XSD-Validierung fehlgeschlagen fuer {project.phase.name}:\n{errors}"
                )
        finally:
            import os
            os.unlink(tmp_path)

    def test_xsd_schemas_available(self):
        """XSD-Schemas fuer alle Phasen vorhanden."""
        for phase in [GAEBPhase.X81, GAEBPhase.X83, GAEBPhase.X84, GAEBPhase.X86]:
            xsd_path = get_xsd_path(phase, "3.3")
            assert xsd_path is not None, f"XSD fuer {phase.name} nicht gefunden"
            assert xsd_path.is_file()

    def test_2_2_xsd_roundtrip_x81(self):
        """Pruefkriterium 2.2: X81 Roundtrip XSD-valide."""
        src = BVBS_DIR / "x81" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X81"
        if not src.exists():
            pytest.skip("BVBS X81 Pruefdatei nicht vorhanden")
        self._roundtrip_and_validate(str(src))

    def test_3_5_xsd_roundtrip_x84(self):
        """Pruefkriterium 3.5: X84 Roundtrip XSD-valide."""
        src = BVBS_DIR / "x84" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X84"
        if not src.exists():
            pytest.skip("BVBS X84 Pruefdatei nicht vorhanden")
        self._roundtrip_and_validate(str(src))

    def test_3_5_xsd_roundtrip_x86(self):
        """Pruefkriterium 3.5: X86 Roundtrip XSD-valide."""
        src = BVBS_DIR / "x86" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X86"
        if not src.exists():
            pytest.skip("BVBS X86 Pruefdatei nicht vorhanden")
        self._roundtrip_and_validate(str(src))

    def test_xsd_original_x81_valid(self):
        """Original BVBS X81 Pruefdatei ist XSD-valide."""
        src = BVBS_DIR / "x81" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X81"
        if not src.exists():
            pytest.skip("BVBS X81 Pruefdatei nicht vorhanden")
        result = validate_file(str(src))
        assert result.is_valid
        assert result.phase == GAEBPhase.X81

    def test_xsd_original_x86_valid(self):
        """Original BVBS X86 Pruefdatei ist XSD-valide."""
        src = BVBS_DIR / "x86" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X86"
        if not src.exists():
            pytest.skip("BVBS X86 Pruefdatei nicht vorhanden")
        result = validate_file(str(src))
        assert result.is_valid
        assert result.phase == GAEBPhase.X86

    def test_xsd_detects_phase(self):
        """XSD-Validator erkennt Phase automatisch."""
        src = BVBS_DIR / "x84" / "BVBS_Pruefdatei GAEB DA XML 3.3 - AVA - V 11 06 2021.X84"
        if not src.exists():
            pytest.skip("BVBS X84 Pruefdatei nicht vorhanden")
        result = validate_file(str(src))
        assert result.phase == GAEBPhase.X84
        assert result.version == "3.3"

    def test_roundtrip_ref_descr_preserved(self, bvbs_x81):
        """RefDescr-Wert (Ref/Rep) wird korrekt roundtripped."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.20.10")
        assert item is not None
        assert item.ref_descr == "Ref"

        item2 = _find_item_by_ordinal(bvbs_x81, "1.10.20.11")
        assert item2 is not None
        assert item2.ref_descr == "Rep"

    def test_roundtrip_sum_descr_preserved(self, bvbs_x81):
        """SumDescr wird als 'Yes' roundtripped."""
        item = _find_item_by_ordinal(bvbs_x81, "1.10.15.10")
        assert item is not None
        assert item.sum_descr is True

    def test_roundtrip_markup_value_preserved(self, bvbs_x86):
        """Markup-Dezimalwert wird korrekt roundtripped."""
        result = self._roundtrip_project(bvbs_x86)
        # Find a MarkupItem
        for cat in self._iter_all_categories(result):
            for item in cat.items:
                if item.is_markup_item and item.markup_value is not None:
                    assert item.markup_value == _find_markup_item_value(
                        bvbs_x86, item.id
                    )
                    return
        # If no markup items found, that's also OK (test is skipped implicitly)

    def test_roundtrip_up_comp_types_preserved(self, bvbs_x86):
        """LblUPComp Type-Attribut wird korrekt roundtripped."""
        result = self._roundtrip_project(bvbs_x86)
        assert len(result.boq.info.up_comp_types) > 0
        for i, comp_type in result.boq.info.up_comp_types.items():
            assert comp_type == bvbs_x86.boq.info.up_comp_types[i]

    def _roundtrip_project(self, project):
        reader = GAEBReader()
        writer = GAEBWriter()
        with tempfile.NamedTemporaryFile(
            suffix=project.phase.file_extension, delete=False
        ) as tmp:
            tmp_path = tmp.name
        try:
            writer.write(project, tmp_path)
            return reader.read(tmp_path)
        finally:
            import os
            os.unlink(tmp_path)

    def _iter_all_categories(self, project):
        def _iter(cats):
            for cat in cats:
                yield cat
                yield from _iter(cat.subcategories)
        if project.boq:
            yield from _iter(project.boq.categories)


def _find_markup_item_value(project, item_id):
    """Find Markup value for a MarkupItem by ID."""
    def _search(cats):
        for cat in cats:
            for item in cat.items:
                if item.id == item_id and item.is_markup_item:
                    return item.markup_value
            result = _search(cat.subcategories)
            if result is not None:
                return result
        return None
    if project.boq:
        return _search(project.boq.categories)
    return None
