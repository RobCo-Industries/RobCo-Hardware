"""The pin table in a spec equals the one generated from its pins.yaml."""

import os

import pytest

import check_pins as cp
import gen_pin_table as gpt
from conftest import ROOT, real_board_support

TC = os.path.join(ROOT, "terminal-controller", "spec")
PINS = os.path.join(TC, "pins.yaml")
DOC = os.path.join(TC, "SPEC.md")
PB = os.path.join(ROOT, "pipboy-hat", "spec")
PB_PINS = os.path.join(PB, "pins.yaml")
PB_DOC = os.path.join(PB, "SPEC.md")
REAL_SPEC = real_board_support()


def test_spec_table_matches_pins_yaml():
    assert gpt.main(["--check", PINS, DOC]) == 0


def test_changed_pin_fails_the_check(tmp_path):
    text = open(PINS, encoding="utf-8").read().replace("net: BTN_UP", "net: BTN_DOWN", 1)
    bad = tmp_path / "pins.yaml"
    bad.write_text(text, encoding="utf-8")
    assert gpt.main(["--check", str(bad), DOC]) == 1


def test_write_then_check(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# x\n\n<!-- pin-table:start -->\nold\n<!-- pin-table:end -->\n\ntail\n", encoding="utf-8")
    assert gpt.main(["--check", PINS, str(doc)]) == 1
    assert gpt.main([PINS, str(doc)]) == 0
    text = doc.read_text(encoding="utf-8")
    assert "old" not in text and text.endswith("<!-- pin-table:end -->\n\ntail\n")
    assert "| 40 | GPIO 21 | `GPIO21` |" in text
    assert gpt.main(["--check", PINS, str(doc)]) == 0


def test_missing_markers_fail(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# no markers\n", encoding="utf-8")
    assert gpt.main(["--check", PINS, str(doc)]) == 2


def test_not_connected_and_pipe_cells():
    body = gpt.table("pins:\n  - pin: 19\n    net: NC\n    use: a|b\n    source: s\n")
    assert body.splitlines()[2] == "| 19 |  | not connected | a\\|b (s) |  |  |"


def test_terminal_controller_map_is_complete():
    pm = cp.load_pins(PINS)
    assert pm.header == "pi40" and sorted(e.pin for e in pm.pins) == list(range(1, 41))
    assert cp.check_software(pm, {}) == []  # every name matches the Pi pin


def test_terminal_controller_against_real_board_support():
    if not os.path.exists(REAL_SPEC):
        if os.environ.get("ROBCO_REQUIRE_BOARD_SUPPORT") == "1":
            pytest.fail("BOARD_SUPPORT.md not found at " + REAL_SPEC)
        pytest.skip("set ROBCO_BOARD_SUPPORT or check out RobCo-Core next to this repository")
    assert cp.run(PINS, None, REAL_SPEC) == (cp.OK, [])


def test_pipboy_table_matches_pins_yaml():
    assert gpt.main(["--check", PB_PINS, PB_DOC]) == 0


def test_pipboy_changed_pin_fails_the_check(tmp_path):
    text = open(PB_PINS, encoding="utf-8").read().replace("net: TFT_DC", "net: TFT_RESET", 1)
    bad = tmp_path / "pins.yaml"
    bad.write_text(text, encoding="utf-8")
    assert gpt.main(["--check", str(bad), PB_DOC]) == 1


def test_pipboy_map_is_complete_and_ignores_nothing():
    pm = cp.load_pins(PB_PINS)
    assert pm.header == "pi40" and sorted(e.pin for e in pm.pins) == list(range(1, 41))
    assert pm.ignore == []
    assert cp.check_software(pm, {}) == []


def test_pipboy_against_real_board_support():
    if not os.path.exists(REAL_SPEC):
        if os.environ.get("ROBCO_REQUIRE_BOARD_SUPPORT") == "1":
            pytest.fail("BOARD_SUPPORT.md not found at " + REAL_SPEC)
        pytest.skip("set ROBCO_BOARD_SUPPORT or check out RobCo-Core next to this repository")
    assert cp.run(PB_PINS, None, REAL_SPEC) == (cp.OK, [])
    uses = cp.parse_board_support(open(REAL_SPEC, encoding="utf-8").read())
    by_gpio = {e.gpio: e for e in cp.load_pins(PB_PINS).pins if e.gpio is not None}
    # The display defaults reach the panel socket.
    assert ("TFT D/C", "SPI display") in uses[25] and by_gpio[25].net == "TFT_DC"
    assert ("TFT RESET", "SPI display") in uses[4] and by_gpio[4].net == "TFT_RESET"
