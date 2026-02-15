from decimal import Decimal

import pytest

from lvgenerator.constants import GAEBPhase
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import GAEBProject, PrjInfo
from lvgenerator.models.boq import BoQ, BoQInfo
from lvgenerator.validators import (
    CategoryValidator,
    ItemValidator,
    ProjectValidator,
    validate_decimal_input,
)


class TestItemValidator:
    def test_valid_item(self):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("10"), qu="m2",
            up=Decimal("5.00"),
            description=ItemDescription(outline_text="Beton C25"),
        )
        result = ItemValidator().validate(item, GAEBPhase.X84)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_rno_part_is_error(self):
        item = Item(id="1", rno_part="", qty=Decimal("10"), qu="m2")
        result = ItemValidator().validate(item, GAEBPhase.X83)
        assert not result.is_valid
        errors = result.get_field_errors("rno_part")
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_missing_outline_text_is_warning(self):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("10"), qu="m2",
            description=ItemDescription(outline_text=""),
        )
        result = ItemValidator().validate(item, GAEBPhase.X83)
        assert result.is_valid  # Warning, not error
        errors = result.get_field_errors("outline_text")
        assert len(errors) == 1
        assert errors[0].severity == "warning"

    def test_negative_qty_is_error(self):
        item = Item(id="1", rno_part="0010", qty=Decimal("-5"))
        result = ItemValidator().validate(item, GAEBPhase.X83)
        assert not result.is_valid
        errors = result.get_field_errors("qty")
        assert any(e.severity == "error" for e in errors)

    def test_no_qty_and_no_tbd_is_warning(self):
        item = Item(id="1", rno_part="0010", qty=None, qty_tbd=False)
        result = ItemValidator().validate(item, GAEBPhase.X83)
        errors = result.get_field_errors("qty")
        assert any(e.severity == "warning" for e in errors)

    def test_qty_tbd_suppresses_missing_qty_warning(self):
        item = Item(id="1", rno_part="0010", qty=None, qty_tbd=True)
        result = ItemValidator().validate(item, GAEBPhase.X83)
        qty_errors = result.get_field_errors("qty")
        assert len(qty_errors) == 0

    def test_missing_unit_is_warning(self):
        item = Item(id="1", rno_part="0010", qty=Decimal("10"), qu="")
        result = ItemValidator().validate(item, GAEBPhase.X83)
        errors = result.get_field_errors("qu")
        assert len(errors) == 1
        assert errors[0].severity == "warning"

    def test_negative_up_is_error(self):
        item = Item(
            id="1", rno_part="0010", qty=Decimal("10"), qu="m2",
            up=Decimal("-1.00"),
        )
        result = ItemValidator().validate(item, GAEBPhase.X84)
        errors = result.get_field_errors("up")
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_x81_no_qty_warnings(self):
        """X81 has no quantities, so missing qty should not warn."""
        item = Item(id="1", rno_part="0010", qty=None)
        result = ItemValidator().validate(item, GAEBPhase.X81)
        qty_errors = result.get_field_errors("qty")
        assert len(qty_errors) == 0

    def test_zero_qty_is_valid(self):
        item = Item(id="1", rno_part="0010", qty=Decimal("0"), qu="m2")
        result = ItemValidator().validate(item, GAEBPhase.X83)
        qty_errors = result.get_field_errors("qty")
        assert all(e.severity != "error" for e in qty_errors)


class TestCategoryValidator:
    def test_valid_category(self):
        cat = BoQCategory(id="1", rno_part="01", label="Rohbau")
        result = CategoryValidator().validate(cat)
        assert result.is_valid

    def test_missing_rno_part(self):
        cat = BoQCategory(id="1", rno_part="", label="Rohbau")
        result = CategoryValidator().validate(cat)
        assert not result.is_valid

    def test_missing_label_is_warning(self):
        cat = BoQCategory(id="1", rno_part="01", label="")
        result = CategoryValidator().validate(cat)
        assert result.is_valid  # Warning only
        errors = result.get_field_errors("label")
        assert len(errors) == 1
        assert errors[0].severity == "warning"


class TestProjectValidator:
    def test_empty_project_name_is_warning(self):
        project = GAEBProject(
            prj_info=PrjInfo(name=""),
            phase=GAEBPhase.X83,
            boq=BoQ(id="1", info=BoQInfo()),
        )
        result = ProjectValidator().validate(project)
        assert result.is_valid  # Warning only
        errors = result.get_field_errors("prj_name")
        assert len(errors) == 1

    def test_valid_project(self):
        cat = BoQCategory(id="c1", rno_part="01", label="Test")
        cat.items.append(
            Item(id="i1", rno_part="0010", qty=Decimal("10"), qu="m2",
                 description=ItemDescription(outline_text="Test"))
        )
        project = GAEBProject(
            prj_info=PrjInfo(name="Testprojekt"),
            phase=GAEBPhase.X83,
            boq=BoQ(id="1", info=BoQInfo(), categories=[cat]),
        )
        result = ProjectValidator().validate(project)
        assert result.is_valid


class TestValidateDecimalInput:
    def test_valid_number(self):
        val, err = validate_decimal_input("123.45")
        assert val == Decimal("123.45")
        assert err is None

    def test_empty_string(self):
        val, err = validate_decimal_input("")
        assert val is None
        assert err is None

    def test_invalid_string(self):
        val, err = validate_decimal_input("abc")
        assert val is None
        assert err is not None

    def test_whitespace_only(self):
        val, err = validate_decimal_input("   ")
        assert val is None
        assert err is None
