import pytest

import sexp
from common import GridError, g, on_grid
from sch import Schematic, SymbolLibs, lib_pins


def _sch():
    return Schematic("t", title="T", date="2026-11-23", rev="1")


def test_embeds_library_symbol_unchanged():
    s = _sch()
    s.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    embedded = s.lib_symbols["Device:R"]
    raw = SymbolLibs().raw("Device", "R")
    assert embedded[0] == "symbol" and embedded[1] == "Device:R"
    assert embedded[2:] == raw[2:]


def test_derived_symbol_is_flattened():
    sym = SymbolLibs().get("Device:Filter_EMI_C")
    assert sexp.child(sym, "extends") is None
    assert lib_pins(sym)  # pins come from the parent
    units = [u[1] for u in sexp.children(sym, "symbol")]
    assert units and all(u.startswith("Filter_EMI_C_") for u in units)
    child = SymbolLibs().raw("Device", "Filter_EMI_C")
    props = {p[1]: p for p in sexp.children(sym, "property")}
    for p in sexp.children(child, "property"):
        assert props[p[1]] == p  # the child's fields win


def test_pin_positions_follow_rotation():
    s = _sch()
    r = s.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    assert r.pin("1") == (g(10), g(7))  # library y is up, sheet y is down
    assert r.outward("1") == "up"
    r2 = s.symbol("Device:R", "R2", "1k", (g(20), g(10)), rot=90)
    assert r2.pin("1") == (g(17), g(10))
    assert r2.outward("1") == "left"
    assert r2.outward("2") == "right"


def test_label_sits_off_the_pin_and_on_grid():
    s = _sch()
    j = s.symbol("Connector_Generic:Conn_01x03", "J1", "x", (g(20), g(20)))
    s.label(j, "3", "SIG", stub=g(3))
    label = [i for i in s.items if sexp.tag(i) == "label"][0]
    at = sexp.child(label, "at")
    pin = j.pin("3")
    assert (at[1], at[2]) == (pin[0] - g(3), pin[1])
    assert at[3] == 180  # text runs left, away from the pin numbers
    assert all(on_grid(v) for v in at[1:3])


def test_off_grid_position_fails():
    s = _sch()
    with pytest.raises(GridError):
        s.symbol("Device:R", "R1", "1k", (10.0, g(10)))
    r = s.symbol("Device:R", "R2", "1k", (g(10), g(10)))
    with pytest.raises(GridError):
        s.label(r, "1", "N", stub=2.0)


def test_duplicate_reference_fails():
    s = _sch()
    s.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    with pytest.raises(ValueError, match="duplicate"):
        s.symbol("Device:R", "R1", "1k", (g(20), g(10)))


def test_output_is_deterministic():
    def build():
        s = _sch()
        r = s.symbol("Device:R", "R1", "1k", (g(10), g(10)))
        s.label(r, "1", "A")
        s.power(r, "2", "GND")
        s.power_flag("GND", (g(30), g(30)))
        return s.text_out()

    first = build()
    assert first == build()
    tree = sexp.parse(first)
    uuids = [sexp.value(n, "uuid") for n in tree if sexp.tag(n) in ("symbol", "label", "wire")]
    assert len(uuids) == len(set(uuids))


def test_title_block():
    s = Schematic("t", title="Board", date="2026-11-23", rev="2", comments=["Proposal"])
    tb = sexp.child(sexp.parse(s.text_out()), "title_block")
    assert sexp.value(tb, "title") == "Board"
    assert sexp.value(tb, "rev") == "2"
    assert tb[-1] == ["comment", "1", "Proposal"]
