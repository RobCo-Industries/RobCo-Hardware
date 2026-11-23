import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.join(ROOT, "tools"))

STOCK_SYMBOLS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"


@pytest.fixture(autouse=True)
def fixture_libs(monkeypatch):
    """Point the tools at the trimmed stock libraries in tests/fixtures."""
    monkeypatch.setenv("KICAD10_SYMBOL_DIR", os.path.join(FIXTURES, "symbols"))
