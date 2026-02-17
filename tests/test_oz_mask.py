import pytest
from lvgenerator.models.boq import BoQBkdn
from lvgenerator.controllers.boq_controller import (
    generate_next_rno,
    _get_mask_level_for_category,
    _get_mask_level_for_item,
)
from lvgenerator.validators import validate_rno_part


class TestGenerateNextRno:
    def test_empty_list(self):
        mask = BoQBkdn(type="BoQLevel", length=2, numeric=True)
        assert generate_next_rno([], mask) == "01"

    def test_sequential(self):
        mask = BoQBkdn(type="BoQLevel", length=2, numeric=True)
        assert generate_next_rno(["01", "02"], mask) == "03"

    def test_gaps(self):
        mask = BoQBkdn(type="BoQLevel", length=2, numeric=True)
        assert generate_next_rno(["01", "05", "03"], mask) == "06"

    def test_item_4_digit(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert generate_next_rno(["0001", "0002"], mask) == "0003"

    def test_zero_pad(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert generate_next_rno([], mask) == "0001"


class TestMaskLevelFinders:
    def test_category_levels(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="BoQLevel", length=3, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert _get_mask_level_for_category(bk, 0).length == 2
        assert _get_mask_level_for_category(bk, 1).length == 3
        assert _get_mask_level_for_category(bk, 2) is None

    def test_item_level(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert _get_mask_level_for_item(bk).length == 4

    def test_with_lot(self):
        bk = [
            BoQBkdn(type="Lot", length=2, numeric=True),
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert _get_mask_level_for_category(bk, 0).type == "Lot"
        assert _get_mask_level_for_category(bk, 1).type == "BoQLevel"

    def test_no_item_level(self):
        bk = [BoQBkdn(type="BoQLevel", length=2, numeric=True)]
        assert _get_mask_level_for_item(bk) is None


class TestValidateRnoPart:
    def test_valid_numeric(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert validate_rno_part("0001", mask) is None

    def test_too_long(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        err = validate_rno_part("00001", mask)
        assert err is not None
        assert "zu lang" in err

    def test_not_numeric(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        err = validate_rno_part("abc", mask)
        assert err is not None
        assert "numerisch" in err

    def test_empty(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert validate_rno_part("", mask) is None

    def test_alpha_allowed(self):
        mask = BoQBkdn(type="BoQLevel", length=3, numeric=False)
        assert validate_rno_part("ABC", mask) is None
        assert validate_rno_part("01A", mask) is None

    def test_umlauts_rejected(self):
        mask = BoQBkdn(type="BoQLevel", length=3, numeric=False)
        err = validate_rno_part("äöü", mask)
        assert err is not None
        assert "Umlaute" in err

    def test_no_mask(self):
        assert validate_rno_part("anything", None) is None

    def test_exact_length(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert validate_rno_part("1234", mask) is None

    def test_shorter_than_mask(self):
        mask = BoQBkdn(type="Item", length=4, numeric=True)
        assert validate_rno_part("12", mask) is None


class TestBoQBkdnModel:
    def test_default_values(self):
        b = BoQBkdn()
        assert b.type == "BoQLevel"
        assert b.length == 2
        assert b.numeric is True
        assert b.label == ""
        assert b.alignment is None

    def test_custom_values(self):
        b = BoQBkdn(
            type="Lot",
            length=3,
            numeric=False,
            label="Los",
            alignment="left",
        )
        assert b.type == "Lot"
        assert b.length == 3
        assert b.numeric is False
        assert b.label == "Los"
        assert b.alignment == "left"


class TestOZMaskDialogValidation:
    """Tests for the validation logic in OZMaskDialog."""

    def _validate(self, breakdowns):
        """Standalone validation matching dialog logic."""
        from lvgenerator.views.oz_mask_dialog import MAX_OZ_LENGTH

        if not breakdowns:
            return "Mindestens eine Ebene muss definiert sein."

        item_count = sum(1 for b in breakdowns if b.type == "Item")
        if item_count == 0:
            return "Es muss genau eine Ebene vom Typ 'Position' vorhanden sein."
        if item_count > 1:
            return "Es darf nur eine Ebene vom Typ 'Position' geben."

        lot_count = sum(1 for b in breakdowns if b.type == "Lot")
        if lot_count > 1:
            return "Es darf maximal ein Los ('Lot') geben."
        if lot_count == 1 and breakdowns[0].type != "Lot":
            return "Das Los muss die erste Ebene sein."

        index_count = sum(1 for b in breakdowns if b.type == "Index")
        if index_count > 1:
            return "Es darf maximal einen Index geben."
        if index_count == 1:
            if breakdowns[-1].type != "Index":
                return "Der Index muss die letzte Ebene sein."
            if breakdowns[-1].length != 1:
                return "Der Index muss genau 1 Stelle lang sein."

        total = sum(b.length for b in breakdowns)
        if total > MAX_OZ_LENGTH:
            return f"Die Gesamtlänge ({total} Stellen) überschreitet das Maximum von {MAX_OZ_LENGTH} Stellen."

        hierarchy_count = sum(1 for b in breakdowns if b.type in ("Lot", "BoQLevel"))
        if hierarchy_count > 5:
            return "Maximal 5 Hierarchiestufen (Los + LV-Stufen) erlaubt."

        return None

    def test_valid_standard(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert self._validate(bk) is None

    def test_valid_with_lot_and_index(self):
        bk = [
            BoQBkdn(type="Lot", length=2, numeric=True),
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
            BoQBkdn(type="Index", length=1, numeric=False),
        ]
        assert self._validate(bk) is None

    def test_empty_invalid(self):
        assert self._validate([]) is not None

    def test_no_item_invalid(self):
        bk = [BoQBkdn(type="BoQLevel", length=2, numeric=True)]
        assert "Position" in self._validate(bk)

    def test_two_items_invalid(self):
        bk = [
            BoQBkdn(type="Item", length=4, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert "nur eine" in self._validate(bk)

    def test_two_lots_invalid(self):
        bk = [
            BoQBkdn(type="Lot", length=2, numeric=True),
            BoQBkdn(type="Lot", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert "maximal ein Los" in self._validate(bk)

    def test_lot_not_first_invalid(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Lot", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert "erste Ebene" in self._validate(bk)

    def test_index_not_last_invalid(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Index", length=1, numeric=False),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert "letzte Ebene" in self._validate(bk)

    def test_index_wrong_length_invalid(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=2, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
            BoQBkdn(type="Index", length=2, numeric=False),
        ]
        assert "1 Stelle" in self._validate(bk)

    def test_too_long_invalid(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=5, numeric=True),
            BoQBkdn(type="BoQLevel", length=5, numeric=True),
            BoQBkdn(type="Item", length=5, numeric=True),
        ]
        assert "überschreitet" in self._validate(bk)

    def test_max_14_ok(self):
        bk = [
            BoQBkdn(type="BoQLevel", length=5, numeric=True),
            BoQBkdn(type="BoQLevel", length=5, numeric=True),
            BoQBkdn(type="Item", length=4, numeric=True),
        ]
        assert self._validate(bk) is None

    def test_too_many_hierarchy_levels(self):
        bk = [
            BoQBkdn(type="Lot", length=1, numeric=True),
            BoQBkdn(type="BoQLevel", length=1, numeric=True),
            BoQBkdn(type="BoQLevel", length=1, numeric=True),
            BoQBkdn(type="BoQLevel", length=1, numeric=True),
            BoQBkdn(type="BoQLevel", length=1, numeric=True),
            BoQBkdn(type="BoQLevel", length=1, numeric=True),
            BoQBkdn(type="Item", length=1, numeric=True),
        ]
        assert "Maximal 5" in self._validate(bk)
