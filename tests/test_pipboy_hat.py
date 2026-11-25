"""Netlist checks of the Pip-Boy HAT that ERC cannot make.

The tests read the netlist that `kicad-cli sch export netlist` writes from the
committed schematic, and compare it with pipboy-hat/spec/SPEC.md: the BOM,
every signal net that reaches the Pi, the 5 V input path, the rails, the
backlight switch, the clock's battery jumper, the unfitted pull-ups, the
display socket's pin order and the serial header.

Parts that stay off the board, the display module DS1 and the speaker LS1,
are not in the netlist. The tests read them from the schematic files.

The netlist comes from ROBCO_NETLIST when set (tools/build.sh check sets it),
else from kicad-cli when one is found. Without either the tests are skipped.

Runs under pytest, or alone with any Python 3.9 (KiCad's has no pytest):
    python3 tests/test_pipboy_hat.py
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import netlist  # noqa: E402
import sexp  # noqa: E402

BOARD = os.path.join(ROOT, "pipboy-hat")
SPEC = os.path.join(BOARD, "spec", "SPEC.md")
SCH = os.path.join(BOARD, "kicad", "pipboy-hat.kicad_sch")

# Values are compared for these designator prefixes. Connectors, switches,
# jumpers, test points and holes carry a function name as value.
VALUE_PREFIXES = ("R", "RV", "C", "U", "Q", "D", "DS", "F", "Y", "BT", "M", "LS")
OFF_BOARD = {"DS1", "LS1"}

# (Pi-side net, J1 pin, series resistor, capacitor, switch and its pin, J5 pin), spec section 4.4.
INPUTS = [
    ("BTN_UP", "29", "R40", "C40", ("SW1", "1"), "2"),
    ("BTN_DOWN", "31", "R41", "C41", ("SW2", "1"), "3"),
    ("BTN_LEFT", "11", "R42", "C42", ("SW3", "1"), "4"),
    ("BTN_RIGHT", "15", "R43", "C43", ("SW4", "1"), "5"),
    ("BTN_SELECT", "37", "R44", "C44", ("SW5", "1"), "6"),
    ("BTN_BACK", "13", "R45", "C45", ("SW6", "1"), "7"),
    ("DIAL_A", "16", "R46", "C47", ("SW7", "A"), "8"),
    ("DIAL_B", "18", "R47", "C48", ("SW7", "B"), "9"),
    ("DIAL_PUSH", "36", "R48", "C46", ("SW7", "S1"), "10"),
]

# Every other net that reaches a Pi signal pin, with its exact pin set.
PI_NETS = {
    "TFT_CS": {("J1", "24"), ("J2", "3")},
    "TFT_RESET": {("J1", "7"), ("J2", "4")},
    "TFT_DC": {("J1", "22"), ("J2", "5")},
    "SPI_MOSI": {("J1", "19"), ("J2", "6")},
    "SPI_MISO": {("J1", "21"), ("J2", "9")},
    "SPI_SCLK": {("J1", "23"), ("R24", "1")},
    "TFT_BL": {("J1", "35"), ("R20", "2"), ("R21", "1")},
    "AUDIO_PWM": {("J1", "12"), ("R30", "1")},
    "UART_TX": {("J1", "8"), ("J4", "5")},
    "UART_RX": {("J1", "10"), ("J4", "4")},
    "I2C_SDA": {("J1", "3"), ("U1", "5"), ("R10", "2"), ("TP4", "1")},
    "I2C_SCL": {("J1", "5"), ("U1", "6"), ("R11", "2"), ("TP5", "1")},
    "ID_SD": {("J1", "27"), ("U2", "5"), ("R12", "2")},
    "ID_SC": {("J1", "28"), ("U2", "6"), ("R13", "2")},
}
PI_OPEN = ("26", "32", "33", "38", "40")


class Skip(Exception):
    pass


_NL = None
_LIBPARTS = None


def _kicad_cli() -> str:
    for path in (os.environ.get("KICAD_CLI", ""), "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                 shutil.which("kicad-cli") or ""):
        if path and os.path.exists(path):
            return path
    return ""


def _netlist_text() -> str:
    path = os.environ.get("ROBCO_NETLIST", "")
    if path:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    cli = _kicad_cli()
    if not cli:
        raise Skip("no netlist: set ROBCO_NETLIST or install kicad-cli")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "pb.net")
        subprocess.run([cli, "sch", "export", "netlist", "-o", out, SCH], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(out, encoding="utf-8") as fh:
            return fh.read()


def nl() -> netlist.Netlist:
    global _NL, _LIBPARTS
    if _NL is None:
        text = _netlist_text()
        _NL = netlist.parse(text)
        _LIBPARTS = {}
        for lp in sexp.children(sexp.child(sexp.parse(text), "libparts") or [], "libpart"):
            key = f"{sexp.value(lp, 'lib')}:{sexp.value(lp, 'part')}"
            pins = sexp.child(lp, "pins") or []
            _LIBPARTS[key] = {sexp.value(p, "num"): sexp.value(p, "name") for p in sexp.children(pins, "pin")}
    return _NL


def pin_names(ref: str) -> Dict[str, str]:
    """{pin number: pin name} of a part, from the netlist's library parts."""
    nl()
    return _LIBPARTS[parts()[ref].part]


def pin_of(ref: str, name: str) -> str:
    hits = [num for num, n in pin_names(ref).items() if n == name]
    assert len(hits) == 1, f"{ref}: pin named {name}: {hits}"
    return hits[0]


def net_of(ref: str, pin: str) -> str:
    return nl().pin_net()[(ref, pin)]


def short(name: str) -> str:
    return name.split("/")[-1]


def nodes(net: str) -> Set[Tuple[str, str]]:
    """The pins on a net, by its short name: `I2C_SDA`, `+3V3`, or a local `BL_PB`."""
    hits = [n for n in nl().nets if n == net or n.split("/")[-1] == net]
    assert len(hits) == 1, f"net {net}: found {hits}"
    return set(nl().nets[hits[0]])


def is_open(ref: str, pin: str) -> bool:
    net = net_of(ref, pin)
    return net.startswith("unconnected-") and nodes(net) == {(ref, pin)}


# ---------------------------------------------------------------------------
# Parts: the netlist, plus the parts that stay off the board


class _Part:
    def __init__(self, ref: str, value: str, dnp: bool, footprint: str):
        self.ref, self.value, self.dnp, self.footprint = ref, value, dnp, footprint


def off_board() -> Dict[str, _Part]:
    """Parts in the BOM but not on the board, read from the schematic files."""
    out = {}
    for path in glob.glob(os.path.join(BOARD, "kicad", "*.kicad_sch")):
        with open(path, encoding="utf-8") as fh:
            tree = sexp.parse(fh.read())
        for sym in sexp.children(tree, "symbol"):
            if str(sexp.value(sym, "on_board")) != "no" or str(sexp.value(sym, "in_bom")) != "yes":
                continue
            props = {p[1]: p[2] for p in sexp.children(sym, "property")}
            out[props["Reference"]] = _Part(props["Reference"], props["Value"],
                                            str(sexp.value(sym, "dnp")) == "yes", props["Footprint"])
    return out


def parts() -> Dict[str, object]:
    out: Dict[str, object] = {r: c for r, c in nl().components.items() if not r.startswith("#")}
    out.update(off_board())
    return out


# ---------------------------------------------------------------------------
# The BOM table of SPEC.md section 7


def expand(cell: str) -> List[str]:
    """'R40 to R48, C1' to ['R40', ..., 'R48', 'C1']."""
    out: List[str] = []
    for part in cell.split(","):
        part = part.strip()
        m = re.fullmatch(r"([A-Z]+)(\d+) to ([A-Z]+)(\d+)", part)
        if m:
            out += [f"{m.group(1)}{k}" for k in range(int(m.group(2)), int(m.group(4)) + 1)]
        elif part:
            out.append(part)
    return out


def spec_bom() -> List[dict]:
    text = open(SPEC, encoding="utf-8").read()
    section = text.split("## 7. Bill of materials", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("Designator", "") or set(cells[0]) <= set("-"):
            continue
        refs = expand(cells[0])
        notes = cells[4].lower()
        unfitted = set(refs) if notes.startswith("not fitted") else \
            {r for r in refs if f"{r.lower()} not fitted" in notes}
        rows.append({"refs": refs, "qty": int(cells[1]), "value": cells[2], "unfitted": unfitted})
    return rows


def _norm(text: str) -> str:
    text = text.lower().replace("kohm", "k").replace("ohm", "").replace("uf", "u").replace("nf", "n")
    return re.sub(r"\s+", "", text)


def _r_value(token: str) -> str:
    """'4k7' to '4.7k', '3k9' to '3.9k'; other tokens unchanged."""
    m = re.fullmatch(r"(\d+)k(\d+)", token)
    return f"{m.group(1)}.{m.group(2)}k" if m else token


def value_matches(sch_value: str, spec_value: str) -> bool:
    """Each part of the schematic value, split on '/' and ',', is in the spec value."""
    spec = _norm(spec_value)
    for t in re.split(r"[/,]", sch_value):
        if _norm(" ".join(_r_value(p) for p in t.strip().lower().split())) not in spec:
            return False
    return True


def test_bom_designators_match_the_spec():
    rows = spec_bom()
    listed = [r for row in rows for r in row["refs"]]
    assert len(listed) == len(set(listed)), "a designator is listed twice in the spec BOM"
    for row in rows:
        assert row["qty"] == len(row["refs"]), f"spec BOM row {row['refs']}: quantity {row['qty']}"
    have = set(parts())
    assert sorted(have - set(listed)) == [], "on the schematic, not in the spec BOM"
    assert sorted(set(listed) - have) == [], "in the spec BOM, not on the schematic"


def test_bom_fitted_parts_and_values_match_the_spec():
    comps = parts()
    for row in spec_bom():
        for ref in row["refs"]:
            c = comps[ref]
            assert c.dnp == (ref in row["unfitted"]), f"{ref}: dnp={c.dnp}, spec says fitted={ref not in row['unfitted']}"
            prefix = re.match(r"[A-Z]+", ref).group(0)
            if prefix in VALUE_PREFIXES:
                assert value_matches(c.value, row["value"]), f"{ref}: value '{c.value}' not in '{row['value']}'"


def test_every_board_part_has_a_footprint_and_only_ds1_and_ls1_stay_off():
    off = off_board()
    assert set(off) == OFF_BOARD
    assert all(not p.footprint and not p.dnp for p in off.values()), "DS1 and LS1: bought, no footprint"
    assert "DS1" not in nl().components and "LS1" not in nl().components
    missing = sorted(r for r, c in nl().components.items() if not r.startswith("#") and not c.footprint)
    assert missing == [], f"parts on the board without a footprint: {missing}"


# ---------------------------------------------------------------------------
# Signal nets that reach the Pi


def test_each_key_and_dial_line_reaches_its_pin_resistor_and_capacitor():
    for net, pin, rs, cs, (sw, swpin), j5 in INPUTS:
        assert nodes(net) == {("J1", pin), (rs, "1"), (cs, "1")}, net
        assert nodes(f"{net}_SW") == {(rs, "2"), (sw, swpin), ("J5", j5)}, f"{net}_SW"
        assert net_of(cs, "2") == "GND", f"{cs} to GND"
        if sw != "SW7":
            assert net_of(sw, "2") == "GND", f"{sw} to GND"
    assert net_of("SW7", "C") == "GND" and net_of("SW7", "S2") == "GND"
    assert net_of("J5", "1") == "GND" and net_of("J5", "11") == "GND"


def test_display_backlight_audio_serial_and_i2c_nets():
    for net, want in PI_NETS.items():
        assert nodes(net) == want, net
    assert nodes("SPI_SCK_J") == {("R24", "2"), ("J2", "7")}
    for pin in PI_OPEN:
        assert is_open("J1", pin), f"J1 pin {pin} must stay open"


def test_every_pi_signal_net_is_checked():
    """No net reaches a J1 signal pin without an exact pin set above."""
    checked = set(PI_NETS) | {row[0] for row in INPUTS}
    j1 = {net for (ref, _), net in nl().pin_net().items() if ref == "J1"}
    signals = {short(n) for n in j1 if n not in ("+5V", "+3V3", "GND") and not n.startswith("unconnected-")}
    assert signals == checked, sorted(signals ^ checked)


def test_f1_uses_the_larger_fuse_outline():
    assert parts()["F1"].footprint == "RobCo:Fuse_PTC_Radial_W10.0mm_T3.5mm_P5.10mm"


def test_no_part_ties_plus_5v_to_a_pi_signal():
    j1 = {pin: net for (ref, pin), net in nl().pin_net().items() if ref == "J1"}
    assert sorted(p for p, n in j1.items() if n == "+5V") == ["2", "4"]
    signals = {n for n in j1.values() if n not in ("+5V", "+3V3", "GND") and not n.startswith("unconnected-")}
    assert "+5V" not in signals
    by_ref: Dict[str, Set[str]] = {}
    for n, pins in nl().nets.items():
        for ref, _ in pins:
            by_ref.setdefault(ref, set()).add(n)
    bridges = sorted(r for r, ns in by_ref.items() if r != "J1" and "+5V" in ns and ns & signals)
    assert bridges == [], f"parts between +5V and a Pi signal: {bridges}"


# ---------------------------------------------------------------------------
# Power


def test_power_path_in_order():
    assert parts()["Q3"].part == "RobCo:Q_PMOS_GSD_SOT23"
    d, s, g = pin_of("Q3", "D"), pin_of("Q3", "S"), pin_of("Q3", "G")
    assert (d, s, g) == ("3", "2", "1"), "SOT-23 pads: 1 gate, 2 source, 3 drain"
    assert nodes("V_EXT") == {("J3", "1"), ("F1", "1")}
    assert net_of("J3", "2") == "GND"
    assert nodes("V_F") == {("F1", "2"), ("Q3", d)}, "the drain faces the fuse"
    assert net_of("Q3", s) == "+5V", "the source is +5V"
    assert nodes("RP_G") == {("Q3", g), ("R1", "1"), ("D2", pin_of("D2", "A"))}
    assert net_of("R1", "2") == "GND"
    assert net_of("D2", pin_of("D2", "K")) == "+5V", "zener cathode on the source"
    assert net_of("D1", pin_of("D1", "K")) == "+5V" and net_of("D1", pin_of("D1", "A")) == "GND"


def test_rails_carry_only_the_stated_parts():
    assert nodes("+5V") == {("J1", "2"), ("J1", "4"), ("Q3", "2"), ("D2", "1"), ("D1", "1"), ("M1", "1"),
                            ("C32", "1"), ("C33", "1"), ("TP2", "1")}
    assert nodes("+3V3") == {("J1", "1"), ("J1", "17"), ("J2", "1"), ("C1", "1"), ("C2", "1"),
                             ("Q1", pin_of("Q1", "E")), ("R20", "1"), ("R23", "1"), ("U1", "8"), ("C10", "1"),
                             ("U2", "8"), ("C11", "1"), ("R10", "1"), ("R11", "1"), ("R12", "1"), ("R13", "1"),
                             ("R14", "1"), ("R15", "1"), ("TP1", "1")}


# ---------------------------------------------------------------------------
# Backlight, clock, pull-ups, display socket, serial


def test_backlight_switch_as_the_spec_sums_assume():
    comps = parts()
    assert (comps["Q1"].value, comps["Q2"].value) == ("BC327-25", "2N3904")
    b1, e1, c1 = pin_of("Q1", "B"), pin_of("Q1", "E"), pin_of("Q1", "C")
    b2, e2, c2 = pin_of("Q2", "B"), pin_of("Q2", "E"), pin_of("Q2", "C")
    assert net_of("Q1", e1) == "+3V3"
    assert nodes("TFT_LED") == {("Q1", c1), ("J2", "8"), ("TP7", "1")}
    assert nodes("BL_PB") == {("Q1", b1), ("R22", "1"), ("R23", "2")}
    assert net_of("R23", "1") == "+3V3", "R23 from base to emitter"
    assert nodes(short(net_of("Q2", c2))) == {("Q2", c2), ("R22", "2")}
    assert net_of("Q2", e2) == "GND"
    assert nodes("BL_NB") == {("Q2", b2), ("R21", "2")}
    assert net_of("R20", "1") == "+3V3" and short(net_of("R20", "2")) == "TFT_BL"
    assert not comps["R20"].dnp, "the default-on pull-up is fitted"
    values = {r: comps[r].value for r in ("R20", "R21", "R22", "R23")}
    assert values == {"R20": "4k7", "R21": "4k7", "R22": "470", "R23": "10k"}, values


def test_clock_battery_jumper():
    assert nodes("VBAT") == {("U1", "3"), ("BT1", "1"), ("JP1", "2")}
    assert net_of("JP1", "1") == "GND" and net_of("BT1", "2") == "GND"
    assert parts()["JP1"].part == "Jumper:SolderJumper_2_Open", "JP1 is open by default"
    assert nodes("SQW") == {("U1", "7"), ("R15", "2"), ("TP8", "1")}


def test_unfitted_pull_ups():
    comps = parts()
    want = {"R10": ("4k7", "I2C_SDA"), "R11": ("4k7", "I2C_SCL"), "R12": ("3k9", "ID_SD"),
            "R13": ("3k9", "ID_SC"), "R14": ("1k", "EE_WP"), "R15": ("10k", "SQW")}
    for ref, (value, net) in want.items():
        assert comps[ref].dnp, f"{ref} is not fitted"
        assert comps[ref].value == value, f"{ref}: {comps[ref].value}"
        assert net_of(ref, "1") == "+3V3" and short(net_of(ref, "2")) == net, ref
    assert nodes("EE_WP") == {("U2", "7"), ("R14", "2"), ("JP2", "2")}
    assert net_of("JP2", "1") == "GND"


def spec_socket() -> List[Tuple[str, str, str]]:
    """[(J2 pin, module pin, net)] from the module header table of spec section 4.1."""
    text = open(SPEC, encoding="utf-8").read()
    section = text.split("### 4.1 Display", 1)[1].split("\n### ", 1)[0]
    rows = re.findall(r"^\| (\d+) \| ([^|]+?) \| ([^|]+?) \|", section, re.M)
    assert [int(r[0]) for r in rows] == list(range(1, 15)), rows
    return [(p, m.replace(" ", ""), n.strip("`")) for p, m, n in rows]


def test_display_socket_follows_the_spec_pin_order():
    names = pin_names("J2")
    for pin, module_pin, net in spec_socket():
        assert names[pin] == module_pin, f"J2 pin {pin} is {names[pin]}, spec says {module_pin}"
        if net == "not connected":
            assert is_open("J2", pin), f"J2 pin {pin} must stay open"
        else:
            assert short(net_of("J2", pin)) == net, f"J2 pin {pin} on {net_of('J2', pin)}, spec says {net}"


def test_serial_header_keeps_vcc_open():
    assert net_of("J4", "1") == "GND"
    for pin in ("2", "3", "6"):
        assert is_open("J4", pin), f"J4 pin {pin} must stay open"
    assert short(net_of("J4", "4")) == "UART_RX" and short(net_of("J4", "5")) == "UART_TX"


# ---------------------------------------------------------------------------


def _run_alone() -> int:
    failed = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"ok    {name}")
        except Skip as exc:
            print(f"skip  {name}: {exc}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
    print(f"test_pipboy_hat: {len(tests) - failed} passed, {failed} failed")
    return 1 if failed else 0


try:
    import pytest

    @pytest.fixture(autouse=True)
    def _skip_without_netlist():
        try:
            nl()
        except Skip as exc:
            pytest.skip(str(exc))
except ImportError:
    pass


if __name__ == "__main__":
    sys.exit(_run_alone())
