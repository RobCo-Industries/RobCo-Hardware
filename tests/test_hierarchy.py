"""Hierarchy, global labels, junctions, frames, mirroring and repeated channels."""

import pytest

import sexp
from common import g
from sch import PROPOSAL, Hierarchy, Schematic


def _sch(**kw):
    return Schematic("t", title="T", date="2026-11-23", rev="1", **kw)


def _items(s, tag):
    return [i for i in s.items if sexp.tag(i) == tag]


def _hier():
    h = Hierarchy("h", board="Board", date="2026-11-23", rev="1")
    a = h.sheet("Power", "power.kicad_sch", (g(20), g(20)))
    b = h.sheet("Outputs", "outputs.kicad_sch", (g(60), g(20)), notes="Eight channels")
    return h, a, b


def test_sheet_symbols_pages_and_instance_paths():
    h, a, b = _hier()
    a.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    b.symbol("Device:R", "R2", "1k", (g(10), g(10)))
    files = h.files()
    assert sorted(files) == ["h.kicad_sch", "outputs.kicad_sch", "power.kicad_sch"]
    root = sexp.parse(files["h.kicad_sch"])
    sheets = sexp.children(root, "sheet")
    assert [s[2] for s in (sexp.children(x, "property")[1] for x in sheets)] == ["power.kicad_sch", "outputs.kicad_sch"]
    pages = [sexp.child(sexp.child(sexp.child(x, "instances"), "project"), "path") for x in sheets]
    assert [p[1] for p in pages] == [f"/{h.root.root}"] * 2
    assert [sexp.value(p, "page") for p in pages] == ["2", "3"]
    sheet_uuid = sexp.value(sheets[0], "uuid")
    child = sexp.parse(files["power.kicad_sch"])
    assert sexp.child(child, "sheet_instances") is None
    assert sexp.child(root, "sheet_instances") is not None
    sym = sexp.child(child, "symbol")
    path = sexp.child(sexp.child(sexp.child(sym, "instances"), "project"), "path")
    assert path[1] == f"/{h.root.root}/{sheet_uuid}"
    assert sexp.value(path, "reference") == "R1"


def test_each_sheet_has_its_title_block():
    h, a, _ = _hier()
    tb = sexp.child(sexp.parse(h.files()["power.kicad_sch"]), "title_block")
    assert sexp.value(tb, "title") == "Power"
    comments = [c[2] for c in sexp.children(tb, "comment")]
    assert comments[:2] == ["Board", PROPOSAL]
    root_tb = sexp.child(sexp.parse(h.files()["h.kicad_sch"]), "title_block")
    assert sexp.value(root_tb, "title") == "Board"


def test_references_and_power_numbers_are_unique_across_sheets():
    h, a, b = _hier()
    a.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    with pytest.raises(ValueError, match="duplicate"):
        b.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    a.power_symbol("GND", (g(20), g(20)))
    b.power_symbol("GND", (g(20), g(20)))
    refs = [p.ref for s in (a, b) for p in s.refs.values() if p.ref.startswith("#PWR")]
    assert refs == ["#PWR01", "#PWR02"]


def test_duplicate_sheet_fails():
    h, _, _ = _hier()
    with pytest.raises(ValueError, match="duplicate sheet name"):
        h.sheet("Power", "other.kicad_sch", (g(100), g(20)))
    with pytest.raises(ValueError, match="duplicate sheet file"):
        h.sheet("Other", "power.kicad_sch", (g(100), g(20)))


def test_uuids_differ_between_sheets_and_are_stable():
    h1, a1, b1 = _hier()
    h2, a2, b2 = _hier()
    assert a1.root != b1.root
    assert h1.files() == h2.files()


def test_global_label_shape_and_side():
    s = _sch()
    j = s.symbol("Connector_Generic:Conn_01x03", "J1", "x", (g(20), g(20)))
    s.global_label(j, "3", "X0.1", shape="output", stub=g(2))
    lab = _items(s, "global_label")[0]
    assert lab[1] == "X0.1"
    assert sexp.value(lab, "shape") == "output"
    at = sexp.child(lab, "at")
    assert (at[1], at[2], at[3]) == (j.pin("3")[0] - g(2), j.pin("3")[1], 180)
    assert sexp.child(lab, "property")[1] == "Intersheetrefs"
    with pytest.raises(ValueError, match="shape"):
        s.global_label_at("N", (g(1), g(1)), shape="round")


def test_no_connect_sits_on_the_pin():
    s = _sch()
    r = s.symbol("Device:R", "R1", "1k", (g(10), g(10)))
    s.no_connect(r, "2")
    at = sexp.child(_items(s, "no_connect")[0], "at")
    assert (at[1], at[2]) == r.pin("2")


def test_t_connection_without_junction_fails():
    s = _sch()
    s.wire((g(0), g(0)), (g(10), g(0)))
    s.wire((g(5), g(0)), (g(5), g(5)))
    assert s.missing_junctions() == [(g(5), g(0))]
    with pytest.raises(ValueError, match="without a junction"):
        s.text_out()
    s.junction((g(5), g(0)))
    assert s.missing_junctions() == []
    assert len(_items(s, "junction")) == 1


def test_three_wire_ends_need_a_junction_and_a_corner_does_not():
    s = _sch()
    s.wire((g(0), g(0)), (g(5), g(0)), (g(5), g(5)))
    assert s.missing_junctions() == []
    s.wire((g(5), g(0)), (g(10), g(0)))
    assert s.missing_junctions() == [(g(5), g(0))]


def test_frame_and_bold_title():
    s = _sch()
    s.frame("Outputs", (g(10), g(10)), (g(50), g(40)))
    rect = _items(s, "rectangle")[0]
    assert sexp.child(rect, "stroke")[2][1] == "dash"
    text = _items(s, "text")[0]
    assert text[1] == "Outputs"
    assert ["bold", "yes"] in sexp.child(sexp.child(text, "effects"), "font")


def test_repeat_places_channels_with_index():
    s = _sch()
    seen = []

    def ch(i, at):
        seen.append((i, at))
        s.symbol("Device:R", f"R1{i}", "1k", at)

    s.repeat(3, (g(10), g(10)), (0, g(8)), ch)
    assert seen == [(0, (g(10), g(10))), (1, (g(10), g(18))), (2, (g(10), g(26)))]
    with pytest.raises(Exception):
        s.repeat(2, (g(10), g(10)), (1.0, 0), ch)


@pytest.mark.parametrize("mirror,rot,want,out", [
    ("", 90, (g(17), g(10)), "left"),
    ("y", 90, (g(23), g(10)), "right"),
    ("", 0, (g(20), g(7)), "up"),
    ("x", 0, (g(20), g(13)), "down"),
    ("y", 0, (g(20), g(7)), "up"),
])
def test_mirror_moves_pins(mirror, rot, want, out):
    s = _sch()
    r = s.symbol("Device:R", "R1", "1k", (g(20), g(10)), rot=rot, mirror=mirror)
    assert r.pin("1") == want
    assert r.outward("1") == out
    assert sexp.value(s.symbols[0], "mirror") == (mirror or None)


def test_bad_mirror_fails():
    with pytest.raises(ValueError, match="mirror"):
        _sch().symbol("Device:R", "R1", "1k", (g(10), g(10)), mirror="z")


def test_units_of_a_part_are_placed_once_each():
    s = _sch()
    u1 = s.symbol("Isolator:LTV-847", "U5", "LTV-847", (g(10), g(10)), unit=1)
    u2 = s.symbol("Isolator:LTV-847", "U5", "LTV-847", (g(30), g(10)), unit=2)
    assert sorted(u1._pins) == sorted(["1", "2", "15", "16"])
    assert sorted(u2._pins) == sorted(["3", "4", "13", "14"])
    with pytest.raises(ValueError, match="duplicate reference U5 unit 2"):
        s.symbol("Isolator:LTV-847", "U5", "LTV-847", (g(50), g(10)), unit=2)
    with pytest.raises(ValueError, match="has no unit 5"):
        s.symbol("Isolator:LTV-847", "U6", "LTV-847", (g(50), g(10)), unit=5)
    tree = sexp.parse(s.text_out())
    syms = sexp.children(tree, "symbol")
    assert [str(sexp.value(x, "unit")) for x in syms] == ["1", "2"]
    paths = [sexp.child(sexp.child(sexp.child(x, "instances"), "project"), "path") for x in syms]
    assert [str(sexp.value(p, "unit")) for p in paths] == ["1", "2"]
    assert sexp.value(syms[0], "uuid") != sexp.value(syms[1], "uuid")


def test_dnp_flag():
    s = _sch()
    s.symbol("Device:R", "R1", "4k7", (g(10), g(10)), dnp=True)
    s.symbol("Device:R", "R2", "4k7", (g(20), g(10)))
    syms = sexp.children(sexp.parse(s.text_out()), "symbol")
    assert [str(sexp.value(x, "dnp")) for x in syms] == ["yes", "no"]


def test_label_at_and_own_power_library():
    s = _sch(power_libs={"V_SW": "RobCo"})
    s.label_at("ARM_G", (g(10), g(10)), "left")
    s.power_symbol("V_SW", (g(20), g(20)))
    s.power_symbol("GND", (g(30), g(20)))
    labels = _items(s, "label")
    assert labels[0][1] == "ARM_G" and sexp.child(labels[0], "at")[3] == 180
    assert sorted(s.lib_symbols) == ["RobCo:V_SW", "power:GND"]


def test_power_symbol_value_position():
    s = _sch()
    p = s.power_symbol("GND", (g(10), g(10)), rot=270, value_at=(g(3), 0))
    node = next(n for n in s.symbols if sexp.value(n, "lib_id") == "power:GND")
    val = next(x for x in sexp.children(node, "property") if x[1] == "Value")
    assert [float(v) for v in sexp.child(val, "at")[1:3]] == [g(13), g(10)]
    assert p.ref.startswith("#PWR")
