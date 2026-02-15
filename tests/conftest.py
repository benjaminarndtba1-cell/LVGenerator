from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_x83(fixtures_dir):
    return str(fixtures_dir / "sample_x83.xml")
