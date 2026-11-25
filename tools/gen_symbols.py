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

POWER = "Power rail symbol, own net name. Not a part."

# name: (stock lib, stock symbol, fields, {pin number: new pin name}[, options])
# Options: "numbers" {old pin number: new pin number}, for a package whose pads
# differ from the stock symbol; "pin_names": True shows pin names that the
# stock symbol hides; "body_right": the x of the right edge of the body, to
# widen it for the pin names; "status": the Status field, PROPOSAL when absent.
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
    "Q_PMOS_GDS": (
        "Device", "Q_PMOS",
        {
            "Value": "Q_PMOS_GDS",
            "Footprint": "Package_TO_SOT_THT:TO-220-3_Vertical",
            "Datasheet": "",
            "Description": (
                "P-channel MOSFET, TO-220, pads 1 gate, 2 drain, 3 source. Drawn from the stock "
                "Q_PMOS with its letter pins numbered for the TO-220 pad order that parts such as "
                "the IRF9540N use. Pin order assumed. To check against the data sheet of the part bought."
            ),
            "ki_keywords": "PMOS P-MOS P-MOSFET transistor TO-220",
            "ki_fp_filters": "TO?220*",
        },
        {},
        {"numbers": {"G": "1", "D": "2", "S": "3"}},
    ),
    "Q_PMOS_GSD_SOT23": (
        "Device", "Q_PMOS",
        {
            "Value": "Q_PMOS_GSD_SOT23",
            "Footprint": "Package_TO_SOT_SMD:SOT-23",
            "Datasheet": "",
            "Description": (
                "P-channel MOSFET, SOT-23, pads 1 gate, 2 source, 3 drain. Drawn from the stock "
                "Q_PMOS with its letter pins numbered for the SOT-23 pad order that parts such as "
                "the AO3401A and DMG2305UX use, from memory. Common, not universal: to verify "
                "against the data sheet of the part bought."
            ),
            "ki_keywords": "PMOS P-MOS P-MOSFET transistor SOT-23",
            "ki_fp_filters": "SOT?23*",
        },
        {},
        {"numbers": {"G": "1", "S": "2", "D": "3"}},
    ),
    "ILI9341_Socket_1x14": (
        "Connector_Generic", "Conn_01x14",
        {
            "Value": "ILI9341_Socket_1x14",
            "Footprint": "Connector_PinSocket_2.54mm:PinSocket_1x14_P2.54mm_Vertical",
            "Datasheet": "",
            "Description": (
                "Socket for a 2.8 inch ILI9341 SPI display module, one row of 14 on 2.54 mm: "
                "1 VCC, 2 GND, 3 CS, 4 RESET, 5 DC/RS, 6 SDI(MOSI), 7 SCK, 8 LED, 9 SDO(MISO), "
                "10 T_CLK, 11 T_CS, 12 T_DIN, 13 T_DO, 14 T_IRQ. Drawn from the stock Conn_01x14 "
                "with named pins. Order typical of MSP2807 class modules, from memory: "
                "to verify against the module bought."
            ),
            "ki_keywords": "ILI9341 TFT display module socket header",
        },
        {"1": "VCC", "2": "GND", "3": "CS", "4": "RESET", "5": "DC/RS", "6": "SDI(MOSI)", "7": "SCK",
         "8": "LED", "9": "SDO(MISO)", "10": "T_CLK", "11": "T_CS", "12": "T_DIN", "13": "T_DO", "14": "T_IRQ"},
        {"pin_names": True, "body_right": 13.97},
    ),
    "ILI9341_Module": (
        "Mechanical", "Housing",
        {
            "Reference": "DS",
            "Value": "ILI9341_Module",
            "Datasheet": "",
            "Description": (
                "2.8 inch ILI9341 SPI display module, 240 x 320, bought, not soldered. It plugs "
                "into its socket and has no pins of its own on the schematic. Drawn from the "
                "stock Housing symbol. Module size and pin order to verify against the module bought."
            ),
            "ki_keywords": "ILI9341 TFT display module",
            "ki_fp_filters": "",
        },
        {},
    ),
    "D_TVS_Unidir": (
        "Diode", "SMAJ26A",
        {
            "Value": "D_TVS_Unidir",
            "Footprint": "Diode_THT:D_DO-15_P12.70mm_Horizontal",
            "Datasheet": "",
            "Description": (
                "Unidirectional TVS diode, 600 W class, DO-15, pad 1 cathode, pad 2 anode. "
                "Drawn from the stock SMAJ26A with a through-hole footprint. "
                "Standoff voltage and pad order to check against the data sheet of the part bought."
            ),
            "ki_keywords": "TVS unidirectional diode transient voltage suppressor DO-15",
            "ki_fp_filters": "D*DO?15*",
        },
        {"1": "K", "2": "A"},
    ),
    "PAM8302A_Module": (
        "Connector_Generic", "Conn_01x07",
        {
            "Reference": "M",
            "Value": "PAM8302A_Module",
            "Footprint": "",
            "Datasheet": "",
            "Description": (
                "PAM8302A mono class-D amplifier breakout module, seven pins: 1 VIN, 2 GND, 3 SD, "
                "4 A+, 5 A- on the input edge, 6 OUT+, 7 OUT- on the output edge. Drawn from the "
                "stock Conn_01x07 with named pins. Pin order assumed; take it from the module bought."
            ),
            "ki_keywords": "PAM8302 amplifier class-D module breakout",
        },
        {"1": "VIN", "2": "GND", "3": "SD", "4": "A+", "5": "A-", "6": "OUT+", "7": "OUT-"},
        {"pin_names": True, "body_right": 10.16},
    ),
    "V_PROT": (
        "power", "+5V",
        {"Value": "V_PROT", "Description": "Power symbol: the protected load supply V_PROT, after F1 and D1."},
        {},
        {"status": POWER},
    ),
    "V_SW": (
        "power", "+5V",
        {"Value": "V_SW", "Description": "Power symbol: the switched load rail V_SW, after the arm switch Q1."},
        {},
        {"status": POWER},
    ),
    "+V_S": (
        "power", "+5V",
        {"Value": "+V_S", "Description": "Power symbol: the sensor supply +V_S, V_PROT through F2."},
        {},
        {"status": POWER},
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
    lib, stock, fields, renames = SYMBOLS[name][:4]
    opts = SYMBOLS[name][4] if len(SYMBOLS[name]) > 4 else {}
    # get() merges a derived stock symbol into its parent and names it lib:stock.
    node = libs.get(f"{lib}:{stock}")
    node[1] = name
    props = {p[1]: p for p in sexp.children(node, "property")}
    for key, val in fields.items():
        if key in props:
            props[key][2] = val
        else:
            last = max(i for i, it in enumerate(node) if sexp.tag(it) == "property")
            props[key] = _field(key, val, props["Datasheet"])
            node.insert(last + 1, props[key])
    # A user field with the proposal note, where KiCad puts user fields.
    status = opts.get("status", PROPOSAL)
    node.insert(node.index(props["Description"]) + 1, _field("Status", status, props["Datasheet"]))
    if opts.get("pin_names"):
        names = sexp.child(node, "pin_names")
        if names is not None:
            node[node.index(names)] = [Sym("pin_names"), [Sym("offset"), 1.016]]
    numbers = opts.get("numbers", {})
    if "body_right" in opts:
        body = sexp.children(sexp.children(node, "symbol")[0], "rectangle")[0]
        sexp.child(body, "end")[1] = opts["body_right"]
    for unit in sexp.children(node, "symbol"):
        unit[1] = name + unit[1][len(stock):]
        for pin in sexp.children(unit, "pin"):
            num = sexp.value(pin, "number")
            if num in renames:
                sexp.child(pin, "name")[1] = renames[num]
            if num in numbers:
                sexp.child(pin, "number")[1] = numbers[num]
        if numbers:
            # KiCad keeps the pins of a unit in pin number order.
            pins = [i for i, it in enumerate(unit) if sexp.tag(it) == "pin"]
            ordered = sorted((unit[i] for i in pins), key=lambda p: _num_key(sexp.value(p, "number")))
            for i, p in zip(pins, ordered):
                unit[i] = p
    return node


def _num_key(num: str):
    return (0, int(num), "") if num.isdigit() else (1, 0, num)


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
