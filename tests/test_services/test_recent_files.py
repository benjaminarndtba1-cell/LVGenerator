import os
import tempfile

import pytest

from lvgenerator.services.recent_files import MAX_RECENT_FILES, RecentFilesManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """Create a RecentFilesManager with isolated QSettings."""
    # Use a unique org/app name to avoid polluting real settings
    from PySide6.QtCore import QCoreApplication
    # Ensure QCoreApplication exists
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    app.setOrganizationName("LVGenerator-Test")
    app.setApplicationName("test-recent-files")

    mgr = RecentFilesManager()
    mgr.clear()
    return mgr


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary files for testing."""
    files = []
    for i in range(12):
        f = tmp_path / f"test_{i}.x83"
        f.write_text(f"content {i}")
        files.append(str(f))
    return files


class TestRecentFilesManager:
    def test_initial_empty(self, manager):
        assert manager.get_recent_files() == []

    def test_add_file(self, manager, temp_files):
        manager.add_file(temp_files[0])
        files = manager.get_recent_files()
        assert len(files) == 1

    def test_most_recent_first(self, manager, temp_files):
        manager.add_file(temp_files[0])
        manager.add_file(temp_files[1])
        files = manager.get_recent_files()
        assert os.path.basename(files[0]) == "test_1.x83"
        assert os.path.basename(files[1]) == "test_0.x83"

    def test_duplicate_moves_to_top(self, manager, temp_files):
        manager.add_file(temp_files[0])
        manager.add_file(temp_files[1])
        manager.add_file(temp_files[0])
        files = manager.get_recent_files()
        assert len(files) == 2
        assert os.path.basename(files[0]) == "test_0.x83"

    def test_max_files(self, manager, temp_files):
        for f in temp_files:
            manager.add_file(f)
        files = manager.get_recent_files()
        assert len(files) <= MAX_RECENT_FILES

    def test_nonexistent_filtered(self, manager, tmp_path):
        fake_path = str(tmp_path / "nonexistent.x83")
        manager.add_file(fake_path)
        # File doesn't exist, should be filtered out
        files = manager.get_recent_files()
        assert len(files) == 0

    def test_clear(self, manager, temp_files):
        manager.add_file(temp_files[0])
        manager.clear()
        assert manager.get_recent_files() == []
