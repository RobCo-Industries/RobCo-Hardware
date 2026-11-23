import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.join(ROOT, "tools"))



def real_board_support():
    """RobCo-Core BOARD_SUPPORT.md, found as tools/build.sh finds it."""
    env = os.environ.get("ROBCO_BOARD_SUPPORT")
    if env:
        return env
    tail = os.path.join("RobCo-Core", "docs", "spec", "BOARD_SUPPORT.md")
    for up in ("..", os.path.join("..", "..")):
        path = os.path.join(ROOT, up, tail)
        if os.path.exists(path):
            return path
    return os.path.join(ROOT, "..", tail)


STOCK_SYMBOLS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"


@pytest.fixture(autouse=True)
def fixture_libs(monkeypatch):
    """Point the tools at the trimmed stock libraries in tests/fixtures."""
    monkeypatch.setenv("KICAD10_SYMBOL_DIR", os.path.join(FIXTURES, "symbols"))
