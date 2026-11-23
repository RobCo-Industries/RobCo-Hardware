#!/usr/bin/env python3
"""Write `lib/RobCo.kicad_sym`, the project's own symbols.

    gen_symbols.py [output file]

Each own symbol starts from a stock KiCad symbol of a close part and changes
only its name, fields and the pins that differ. The pinouts are proposals:
each symbol's description says which pins to check against the data sheet.

Needs the stock symbol folder: KICAD10_SYMBOL_DIR or a known install path.
Runs on Python 3.9 so KiCad's bundled Python can run it.
"""

from __future__ import annotations

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sexp  # noqa: E402
from common import own_lib_dir, write_if_changed  # noqa: E402
from sch import SymbolLibs  # noqa: E402
from sexp import Sym  # noqa: E402

LIB_VERSION = 20251024
"""The `.kicad_sym` format version that KiCad 10.0.8 writes."""

PROPOSAL = "Proposal, pinout to verify against the data sheet of the part bought."

# name: (stock lib, stock symbol, fields, {pin number: new pin name})
SYMBOLS = {
    "PCA9554": (
        "Interface_Expansion", "TCA9554DW",
        {
            "Value": "PCA9554",
            "Footprint": "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
            "Datasheet": "",
            "Description": (
                "8-bit I2C I/O expander with interrupt, 100 kOhm pull-ups, SOIC-16 wide. "
                "Drawn from the stock TCA9554DW. Pinout from memory of the PCA9554 data sheet: "
                "1 A0, 2 A1, 3 A2, 4-7 P0-P3, 8 VSS, 9-12 P4-P7, 13 INT, 14 SCL, 15 SDA, 16 VDD. "
                "Same as the TCA9554DW except the name of pin 8. To check against the data sheet."
            ),
            "ki_keywords": "I2C expander GPIO PCA9554 PCA9554A",
            "ki_fp_filters": "SOIC*7.5x10.3mm*P1.27mm*",
        },
        {"8": "VSS"},
    ),
    "DS1338": (
        "Timer_RTC", "DS1307+",
        {
            "Value": "DS1338",
            "Footprint": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            "Datasheet": "",
            "Description": (
                "I2C real-time clock with battery input, 3.0 V or 3.3 V grade, SOIC-8, address 0x68. "
                "Drawn from the stock DS1307+. Pinout from memory of the DS1338 data sheet, "
                "same as the DS1307: 1 X1, 2 X2, 3 VBAT, 4 GND, 5 SDA, 6 SCL, 7 SQW/OUT, 8 VCC. "
                "To check against the data sheet."
            ),
            "ki_keywords": "RTC I2C clock DS1338",
            "ki_fp_filters": "SOIC*3.9x4.9mm*P1.27mm*",
        },
        {},
    ),
}


def _field(name: str, value: str, like: list) -> list:
    node = copy.deepcopy(like)
    node[1] = name
    node[2] = value
    if sexp.child(node, "hide") is None:
        node.insert(4, [Sym("hide"), Sym("yes")])
    return node


def own_symbol(libs: SymbolLibs, name: str) -> list:
    lib, stock, fields, renames = SYMBOLS[name]
    node = copy.deepcopy(libs.raw(lib, stock))
    node[1] = name
    props = {p[1]: p for p in sexp.children(node, "property")}
    for key, val in fields.items():
        props[key][2] = val
    # A user field with the proposal note, where KiCad puts user fields.
    node.insert(node.index(props["Description"]) + 1, _field("Status", PROPOSAL, props["Datasheet"]))
    for unit in sexp.children(node, "symbol"):
        unit[1] = name + unit[1][len(stock):]
        for pin in sexp.children(unit, "pin"):
            num = sexp.value(pin, "number")
            if num in renames:
                sexp.child(pin, "name")[1] = renames[num]
    return node


def library(libs: SymbolLibs) -> list:
    return [
        Sym("kicad_symbol_lib"),
        [Sym("version"), LIB_VERSION],
        [Sym("generator"), "robco_gen"],
        [Sym("generator_version"), "10.0"],
    ] + [own_symbol(libs, n) for n in sorted(SYMBOLS)]


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(own_lib_dir(), "RobCo.kicad_sym")
    write_if_changed(out, sexp.dump_file(library(SymbolLibs())))


if __name__ == "__main__":
    main()
