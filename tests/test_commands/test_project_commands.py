import pytest

from lvgenerator.commands.project_commands import EditProjectPropertyCommand
from lvgenerator.models.project import PrjInfo
from lvgenerator.models.address import Address


class TestEditProjectPropertyCommand:
    def test_redo_sets_value(self):
        info = PrjInfo(name="Alt")
        cmd = EditProjectPropertyCommand(info, "name", "Alt", "Neu")
        cmd.redo()
        assert info.name == "Neu"

    def test_undo_restores_value(self):
        info = PrjInfo(name="Alt")
        cmd = EditProjectPropertyCommand(info, "name", "Alt", "Neu")
        cmd.redo()
        cmd.undo()
        assert info.name == "Alt"

    def test_merge_same_property(self):
        info = PrjInfo(name="A")
        cmd1 = EditProjectPropertyCommand(info, "name", "A", "AB")
        cmd2 = EditProjectPropertyCommand(info, "name", "AB", "ABC")
        assert cmd1.mergeWith(cmd2) is True
        cmd1.redo()
        assert info.name == "ABC"
        cmd1.undo()
        assert info.name == "A"

    def test_no_merge_different_property(self):
        info = PrjInfo(name="Test", label="Lbl")
        cmd1 = EditProjectPropertyCommand(info, "name", "Test", "Neu")
        cmd2 = EditProjectPropertyCommand(info, "label", "Lbl", "Neu2")
        assert cmd1.mergeWith(cmd2) is False

    def test_no_merge_different_object(self):
        info1 = PrjInfo(name="A")
        info2 = PrjInfo(name="B")
        cmd1 = EditProjectPropertyCommand(info1, "name", "A", "A1")
        cmd2 = EditProjectPropertyCommand(info2, "name", "B", "B1")
        assert cmd1.mergeWith(cmd2) is False

    def test_edit_address(self):
        addr = Address(name1="Firma A")
        cmd = EditProjectPropertyCommand(addr, "name1", "Firma A", "Firma B")
        cmd.redo()
        assert addr.name1 == "Firma B"
        cmd.undo()
        assert addr.name1 == "Firma A"

    def test_edit_currency(self):
        info = PrjInfo(currency="EUR")
        cmd = EditProjectPropertyCommand(info, "currency", "EUR", "CHF")
        cmd.redo()
        assert info.currency == "CHF"

    def test_id_is_deterministic(self):
        info = PrjInfo(name="Test")
        cmd1 = EditProjectPropertyCommand(info, "name", "Test", "A")
        cmd2 = EditProjectPropertyCommand(info, "name", "A", "B")
        assert cmd1.id() == cmd2.id()
