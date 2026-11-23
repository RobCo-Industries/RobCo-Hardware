"""Netlist checks of the terminal controller that ERC cannot make.

The tests read the netlist that `kicad-cli sch export netlist` writes from the
committed schematic, and compare it with terminal-controller/spec/SPEC.md:
the BOM, the expander address straps, the driver pull-downs, the parts on
each expander line, the ARM net, the rails and the I2C bus.

The netlist comes from ROBCO_NETLIST when set (tools/build.sh check sets it),
else from kicad-cli when one is found. Without either the tests are skipped.

Runs under pytest, or alone with any Python 3.9 (KiCad's has no pytest):
    python3 tests/test_terminal_controller.py
"""

from __future__ import annotations

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

BOARD = os.path.join(ROOT, "terminal-controller")
SPEC = os.path.join(BOARD, "spec", "SPEC.md")
SCH = os.path.join(BOARD, "kicad", "terminal-controller.kicad_sch")

# Pins of the PCA9554 port P0 to P7, of the ULN2803A inputs and outputs.
P_PINS = ["4", "5", "6", "7", "9", "10", "11", "12"]
# Values are compared for these designator prefixes. Connectors, jumpers, test
# points and holes carry a function name as value, not a part value.
VALUE_PREFIXES = ("R", "RN", "RV", "C", "U", "Q", "D", "LED", "F", "Y", "BT", "M")


class Skip(Exception):
    pass


_NL = None


def _kicad_cli() -> str:
    for path in (os.environ.get("KICAD_CLI", ""), "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                 shutil.which("kicad-cli") or ""):
        if path and os.path.exists(path):
            return path
    return ""


def nl() -> netlist.Netlist:
    global _NL
    if _NL is None:
        path = os.environ.get("ROBCO_NETLIST", "")
        if path:
            _NL = netlist.load(path)
        else:
            cli = _kicad_cli()
            if not cli:
                raise Skip("no netlist: set ROBCO_NETLIST or install kicad-cli")
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "tc.net")
                subprocess.run([cli, "sch", "export", "netlist", "-o", out, SCH], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _NL = netlist.load(out)
    return _NL


def net_of(ref: str, pin: str) -> str:
    return nl().pin_net()[(ref, pin)]


def nodes(net: str) -> Set[Tuple[str, str]]:
    """The pins on a net, by its short name: `I2C_SDA`, `+3V3`, or a local `OUT0`."""
    hits = [n for n in nl().nets if n == net or n.split("/")[-1] == net]
    assert len(hits) == 1, f"net {net}: found {hits}"
    return set(nl().nets[hits[0]])


def short(name: str) -> str:
    return name.split("/")[-1]


# ---------------------------------------------------------------------------
# The BOM table of SPEC.md section 6


def expand(cell: str) -> List[str]:
    """'R10 to R17, R24' to ['R10', ..., 'R17', 'R24']."""
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
    section = text.split("## 6. Bill of materials", 1)[1].split("\n## ", 1)[0]
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
    """'4k7' to '4.7k', '1k5' to '1.5k'; other tokens unchanged."""
    m = re.fullmatch(r"(\d+)k(\d+)", token)
    return f"{m.group(1)}.{m.group(2)}k" if m else token


def value_matches(sch_value: str, spec_value: str) -> bool:
    """Each part of the schematic value, split on '/' and ',', is in the spec value."""
    spec = _norm(spec_value)
    tokens = [t for t in re.split(r"[/,]", sch_value)]
    for t in tokens:
        parts = [_r_value(p) for p in t.strip().lower().split()]
        if _norm(" ".join(parts)) not in spec:
            return False
    return True


def parts() -> Dict[str, netlist.Component]:
    return {r: c for r, c in nl().components.items() if not r.startswith("#")}


def test_bom_designators_match_the_spec():
    rows = spec_bom()
    listed = [r for row in rows for r in row["refs"]]
    assert len(listed) == len(set(listed)), "a designator is listed twice in the spec BOM"
    for row in rows:
        assert row["qty"] == len(row["refs"]), f"spec BOM row {row['refs']}: quantity {row['qty']}"
    have = set(parts())
    assert sorted(have - set(listed)) == [], "on the schematic, not in the spec BOM"
    assert sorted(set(listed) - have) == [], "in the spec BOM, not on the schematic"
    for retired in ("R78", "C10", "R46", "R47", "R48", "R56", "R57", "R58"):
        assert retired not in have, f"{retired} is retired"


def test_bom_fitted_parts_and_values_match_the_spec():
    comps = parts()
    for row in spec_bom():
        for ref in row["refs"]:
            c = comps[ref]
            assert c.dnp == (ref in row["unfitted"]), f"{ref}: dnp={c.dnp}, spec says fitted={ref not in row['unfitted']}"
            prefix = re.match(r"[A-Z]+", ref).group(0)
            if prefix in VALUE_PREFIXES:
                assert value_matches(c.value, row["value"]), f"{ref}: value '{c.value}' not in '{row['value']}'"


# ---------------------------------------------------------------------------
# Circuit checks


def spec_straps() -> Dict[str, List[Tuple[str, str, str]]]:
    """{chip: [(address pin name, rail, jumper)]} and the address, from the spec table."""
    text = open(SPEC, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^\| (U\d) \| (\S+) \((JP\d)\) \| (\S+) \((JP\d)\) \| (\S+) \((JP\d)\) \| `(0x[0-9a-f]+)` \|$",
                         text, re.M):
        out[m.group(1)] = ([("A2", m.group(2), m.group(3)), ("A1", m.group(4), m.group(5)),
                            ("A0", m.group(6), m.group(7))], int(m.group(8), 16))
    assert sorted(out) == ["U1", "U2"], out
    return out


def _rail(spec_name: str) -> str:
    return {"GND": "GND", "3V3": "+3V3", "+3V3": "+3V3"}[spec_name.strip("`")]


def test_address_straps_follow_the_spec():
    pin_of = {"A0": "1", "A1": "2", "A2": "3"}
    for chip, (straps, address) in spec_straps().items():
        bits = 0
        for name, rail, jp in straps:
            assert nodes(short(net_of(chip, pin_of[name]))) == {(chip, pin_of[name]), (jp, "2")}, f"{chip} {name}"
            assert parts()[jp].part == "Jumper:SolderJumper_3_Bridged12", f"{jp}: pad 1 must be the bridged pad"
            default, other = _rail(rail), ({"GND", "+3V3"} - {_rail(rail)}).pop()
            assert net_of(jp, "1") == default, f"{jp} pad 1 (bridged) on {net_of(jp, '1')}, spec says {default}"
            assert net_of(jp, "3") == other, f"{jp} pad 3 on {net_of(jp, '3')}, should be {other}"
            bits |= (1 if default == "+3V3" else 0) << int(name[1])
        assert 0x20 | bits == address, f"{chip}: straps give {hex(0x20 | bits)}, spec says {hex(address)}"


def test_each_driver_input_has_its_pull_down():
    assert net_of("RN1", "1") == "GND"
    for i in range(8):
        net = net_of("U4", str(i + 1))
        assert short(net) == f"X0.{i}"
        assert ("RN1", str(i + 2)) in nodes(net), f"U4 input {i + 1} has no pull-down"


def test_expander_lines_reach_the_listed_parts():
    for i, p in enumerate(P_PINS):
        assert nodes(f"X0.{i}") == {("U1", p), ("U4", str(i + 1)), ("RN1", str(i + 2))}, f"X0.{i}"
        unit = i % 4 + 1
        opto = "U5" if i < 4 else "U6"
        assert nodes(f"X1.{i}") == {("U2", p), (opto, str(18 - 2 * unit)), (f"R7{i}", "2"), (f"C4{i}", "1")}, f"X1.{i}"


def test_outputs_reach_driver_led_and_terminal():
    for i in range(8):
        assert nodes(f"OUT{i}") == {("U4", str(18 - i)), (f"LED{i}", "1"), ("J3", str(i + 1))}, f"OUT{i}"


def test_arm_reaches_only_the_header_and_the_switch_input():
    assert nodes("ARM") == {("J1", "22"), ("R22", "1")}


def test_load_side_never_touches_the_logic_rails():
    load = {"V_EXT", "V_IN", "V_FUSED", "V_PROT", "V_SW", "+V_S", "ARM_G", "IN_COM"} | \
        {f"OUT{i}" for i in range(8)} | {f"IN{i}" for i in range(8)}
    logic = {"+3V3", "+5V"}
    names = {short(n) for n in nl().nets}
    assert load <= names, f"missing load nets: {sorted(load - names)}"
    by_ref: Dict[str, Set[str]] = {}
    for n, pins in nl().nets.items():
        for ref, _ in pins:
            by_ref.setdefault(ref, set()).add(short(n))
    bridges = sorted(r for r, ns in by_ref.items() if ns & load and ns & logic)
    # JP1 picks the load supply: terminal (V_EXT) or Pi 5 V. Spec 4.1.
    assert bridges == ["JP1"], f"parts between the load side and +3V3 or +5V: {bridges}"
    assert nodes("V_IN") == {("JP1", "2"), ("F1", "1")}
    assert nodes("+5V") == {("J1", "2"), ("J1", "4"), ("JP1", "3"), ("M1", "1"), ("C4", "1"), ("C32", "1"),
                            ("TP2", "1")}


def test_arm_switch_pins():
    assert net_of("Q1", "3") == "V_PROT" and net_of("Q1", "2") == "V_SW"
    assert short(net_of("Q1", "1")) == "ARM_G"
    assert nodes("ARM_G") == {("Q1", "1"), ("R20", "2"), ("D3", "2"), ("R21", "1"), ("C13", "2")}
    assert net_of("Q2", "1") == "GND" and short(net_of("Q2", "2")) == short(net_of("R22", "2"))


def _volts(value: str) -> float:
    """The voltage rating in a value: '100u 50V' or 'P-channel MOSFET, 60 V' to 50.0 or 60.0."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*V\b", value)
    assert m, f"no voltage in '{value}'"
    return float(m.group(1))


def test_ratings_stand_above_the_surge_clamp():
    # D2 clamps near 42 V at its rated pulse (to verify). Spec 4.1.
    comps = parts()
    for ref in ("C1", "C9"):
        assert _volts(comps[ref].value) >= 50, f"{ref}: {comps[ref].value}"
    for ref in ("Q1", "F1", "F2"):
        assert _volts(comps[ref].value) >= 60, f"{ref}: {comps[ref].value}"
    for ref in ("D1", "D4"):
        assert comps[ref].value == "SB360", f"{ref}: {comps[ref].value}"
    rows = {r: row["value"] for row in spec_bom() for r in row["refs"]}
    assert "60 V" in rows["D1"] and "60 V" in rows["Q1"] and "50 V" in rows["C1"], rows["D1"]
    for ref in ("F1", "F2"):
        assert _volts(rows[ref]) >= 60, f"{ref}: {rows[ref]}"


def test_arm_gate_resistor_and_turn_on_capacitor():
    comps = parts()
    assert comps["R20"].value == "100k", comps["R20"].value
    assert {net_of("C13", "1"), net_of("C13", "2")} == {"V_SW", net_of("Q1", "1")}
    assert comps["C13"].dnp, "C13 is not fitted"


def test_eeprom_write_protect_pull_up():
    comps = parts()
    wp = net_of("U7", "7")
    assert nodes(short(wp)) == {("U7", "7"), ("JP11", "2"), ("R82", "2")}, wp
    assert net_of("R82", "1") == "+3V3"
    assert comps["R82"].dnp and comps["R82"].value == "1k"
    for ref in ("R80", "R81"):
        assert comps[ref].dnp and comps[ref].value == "3k9", f"{ref}: {comps[ref].value}"


def test_vbat_ground_jumper():
    assert nodes("VBAT") == {("U3", "3"), ("BT1", "1"), ("JP12", "2")}
    assert net_of("JP12", "1") == "GND"
    assert parts()["JP12"].part == "Jumper:SolderJumper_2_Open"


def test_i2c_reaches_the_three_devices_and_test_points_only():
    # R1 and R2 are the unfitted pull-up footprints of spec 4.2.
    assert nodes("I2C_SDA") == {("J1", "3"), ("U1", "15"), ("U2", "15"), ("U3", "5"), ("TP4", "1"), ("R1", "2")}
    assert nodes("I2C_SCL") == {("J1", "5"), ("U1", "14"), ("U2", "14"), ("U3", "6"), ("TP5", "1"), ("R2", "2")}


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
    print(f"test_terminal_controller: {len(tests) - failed} passed, {failed} failed")
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
