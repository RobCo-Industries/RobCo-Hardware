"""Sheet: the holotape slot. J7, a full-size SD socket on SPI0 CE1, behind a
bus buffer U4 and U5 that the card's own switched supply feeds. U3 makes
3.3 V from +5V, Q4 switches it to the card with a slow start, Q5 drives Q4
from HOLO_PWR. HOLO_BUS enables the buffer.

Spec section 4.12. Every part value and pin order here is from memory: to verify.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import (C_DISC, CP_5MM, SOT23, TO92, cap, flag_at, note, res, sideways,
                          testpoint)

SD_SOCKET = "Connector_Card:SD_Hirose_DM1AA_SF_PEJ82"
SOIC14 = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
SOT23_5 = "Package_TO_SOT_SMD:SOT-23-5"
SOT23_6 = "Package_TO_SOT_SMD:SOT-23-6"

# J7 pin: card-side net, in SPI mode. Pin numbers of the own symbol, which
# follow the pads of the stock Hirose DM1AA footprint.
J7_LINES = {"7": "SD_DO", "8": "SD_DAT1", "9": "SD_DAT2", "1": "SD_CS", "5": "SD_CLK", "2": "SD_DI"}

# U4, 74LVC126A, one gate per unit: (unit, OE pin, A pin, Y pin, Pi net, buffer net).
# Pin numbers of the 74x126 in SOIC-14, from memory: to verify.
U4_GATES = [
    (1, "1", "2", "3", "SPI_SCLK", "BUF_CLK"),
    (2, "4", "5", "6", "SPI_MOSI", "BUF_DI"),
    (3, "10", "9", "8", "HOLO_CS", "BUF_CS"),
]

# Series resistors at each driver's output, 33 Ohm: (ref, from, to).
SERIES = [
    ("R54", "BUF_CLK", "SD_CLK"),
    ("R55", "BUF_DI", "SD_DI"),
    ("R56", "BUF_CS", "SD_CS"),
    ("R57", "BUF_DO", "SPI_MISO"),
]

# (ref, value, rail, net, global label shape or None, description).
PULLUPS = [
    ("R50", "10k", "SD_3V3", "SD_CS", None, "SD_CS pull-up to the card rail: card deselected, U5 off"),
    ("R60", "47k", "SD_3V3", "SD_DI", None, "SD_DI pull-up to the card rail, buffer off"),
    ("R61", "47k", "SD_3V3", "SD_CLK", None, "SD_CLK pull-up to the card rail, buffer off"),
    ("R62", "47k", "SD_3V3", "SD_DO", None, "SD_DO pull-up to the card rail: U5 input never floats"),
    ("R51", "47k", "SD_3V3", "SD_DAT1", None, "DAT1 pull-up, unused in SPI mode (10k to 100k, to verify)"),
    ("R52", "47k", "SD_3V3", "SD_DAT2", None, "DAT2 pull-up, unused in SPI mode (10k to 100k, to verify)"),
    ("R53", "4k7", "+3V3", "SPI_MISO", "output", "MISO pull-up: beats the Pi's 30k to 50k reset pull-down"),
    ("R58", "10k", "+3V3", "HOLO_CD", "output", "Card detect pull-up"),
    ("R59", "10k", "+3V3", "HOLO_WP", "output", "Write protect pull-up"),
]


def socket(s: Schematic) -> None:
    s.frame("Holotape socket J7, SD card in SPI mode", (g(10), g(12)), (g(128), g(100)))
    j7 = s.symbol("RobCo:SD_Card_Hirose_DM1AA", "J7", "Full-size SD socket", (g(64), g(48)),
                  footprint=SD_SOCKET, ref_at=(g(-12), g(-24)), value_at=(g(-12), g(-22)),
                  description="Full-size SD socket, push-push, card detect and write protect switches, "
                              "Hirose DM1AA-SF-PEJ(82) class. Pinout and switch polarity to verify.")
    for pin, net in J7_LINES.items():
        s.label(j7, pin, net, stub=g(3))
    sideways(s, j7, "SH", "GND")
    sideways(s, j7, "SW", "GND")
    s.global_label(j7, "CP", "HOLO_CD", shape="output", stub=g(3))
    s.global_label(j7, "WP", "HOLO_WP", shape="output", stub=g(3))
    s.label(j7, "4", "SD_3V3", stub=g(2))
    s.power(j7, "3", "GND", stub=g(1))
    for k, (ref, value, desc) in enumerate((
            ("C53", "100n", "J7 VDD decoupling, at J7 pin 4"),
            ("C57", "4.7u 10V", "Card-side bulk, ceramic, at J7. Small: Q4 charges it slowly"))):
        c = cap(s, ref, value, (g(94 + 14 * k), g(36)), desc=desc)
        s.label(c, "1", "SD_3V3", stub=g(2))
        s.power(c, "2", "GND", stub=g(1))
    note(s, "SPI mode: 1 CS, 2 DI, 5 CLK, 7 DO. DAT1 and DAT2 unused, pulled up.\n"
            "CP closes to SW, the common, with a card in: HOLO_CD low.\n"
            "WP open with the card's slider on LOCK: HOLO_WP high.\n"
            "With no card WP reads high. Switch pads and polarity:\n"
            "from memory, TO VERIFY against the Hirose DM1AA data sheet.\n"
            "Shell to GND. Every card pin meets only U4, U5, D3\n"
            "and pull-ups to SD_3V3: never a Pi pin, never +3V3.", (g(14), g(98)))
    note(s, "SD_3V3 is off until the software sets HOLO_PWR.\n"
            "A card pushed in gets no power and sees 0 V\n"
            "on every pin. D3, not fitted: 4-line ESD array.", (g(88), g(66)))


def buffer(s: Schematic) -> None:
    s.frame("Bus buffer U4, U5: the card sees the bus only on HOLO_BUS", (g(134), g(12)), (g(320), g(104)))
    desc = ("Quad buffer, 3-state, active-high enables, Ioff, SOIC-14. 74LVC126A. Pins from memory of "
            "the 74x126: 1 1OE, 2 1A, 3 1Y, 4 2OE, 5 2A, 6 2Y, 7 GND, 8 3Y, 9 3A, 10 3OE, 11 4Y, 12 4A, "
            "13 4OE, 14 VCC. To verify.")
    for k, (unit, oe, a, y, pi_net, buf) in enumerate(U4_GATES):
        x, yy = g(160), g(30 + 22 * k)
        u = s.symbol("74xx:74LS126", "U4", "74LVC126A", (x, yy), unit=unit, footprint=SOIC14,
                     ref_at=(g(-2), g(-5)), value_at=(g(-2), g(-7)), description=desc)
        s.global_label(u, a, pi_net, shape="input", stub=g(3))
        s.global_label(u, oe, "HOLO_BUS", shape="input", stub=g(2))
        s.label(u, y, buf, stub=g(3))
    u4 = s.symbol("74xx:74LS126", "U4", "74LVC126A", (g(212), g(88)), unit=4, footprint=SOIC14,
                  ref_at=(g(-2), g(-5)), value_at=(g(-2), g(-7)), description=desc)
    s.power(u4, "12", "GND", stub=g(2))
    s.power(u4, "13", "GND", stub=g(2))
    s.no_connect(u4, "11")
    pw = s.symbol("74xx:74LS126", "U4", "74LVC126A", (g(186), g(86)), unit=5, footprint=SOIC14,
                  ref_at=(g(3), g(-1)), value_at=(g(3), g(1)), description=desc)
    s.label(pw, "14", "SD_3V3", stub=g(2))
    s.power(pw, "7", "GND", stub=g(1))
    u5 = s.symbol("74xGxx:74LVC1G125", "U5", "74LVC1G125", (g(250), g(30)), footprint=SOT23_5,
                  ref_at=(g(3), g(-5)), value_at=(g(3), g(-7)),
                  description="Single buffer, 3-state, active-low enable, Ioff, SOT-23-5. Pins from memory: "
                              "1 OE, 2 A, 3 GND, 4 Y, 5 VCC. To verify.")
    s.label(u5, "2", "SD_DO", stub=g(3))
    s.label(u5, "1", "SD_CS", stub=g(2), then=[(g(4), 0)])
    s.label(u5, "4", "BUF_DO", stub=g(3))
    s.label(u5, "5", "SD_3V3", stub=g(2))
    s.power(u5, "3", "GND", stub=g(1))
    for k, (ref, net) in enumerate((("C55", "U4"), ("C56", "U5"))):
        c = cap(s, ref, "100n", (g(232 + 12 * k), g(80)), desc=f"{net} VCC decoupling, on SD_3V3")
        s.label(c, "1", "SD_3V3", stub=g(2))
        s.power(c, "2", "GND", stub=g(1))
    for k, (ref, frm, to) in enumerate(SERIES):
        r = res(s, ref, "33", (g(276), g(42 + 8 * k)), horizontal=True,
                desc=f"{frm} to {to}, source termination at the driver's output")
        s.label(r, "1", frm, stub=g(3))
        if to == "SPI_MISO":
            s.global_label(r, "2", to, shape="output", stub=g(3))
        else:
            s.label(r, "2", to, stub=g(3))
    r63 = res(s, "R63", "100k", (g(296), g(80)), desc="HOLO_BUS pull-down: buffer off while the Pi boots")
    s.global_label(r63, "1", "HOLO_BUS", shape="input", stub=g(2))
    s.power(r63, "2", "GND", stub=g(1))
    note(s, "HOLO_BUS high: U4 passes SCLK, MOSI and CS to the card.\n"
            "Low or floating: U4 off, R63 and the Pi's reset pull-down.\n"
            "U5 passes DO to MISO only while SD_CS is low.\n"
            "SD_3V3 off: U4 and U5 unpowered, Ioff, no current\n"
            "either way. 33 Ohm sit at each driver's output.\n"
            "U4 unit 4 unused: inputs to GND.\n"
            "Parts and pins from memory, TO VERIFY.", (g(226), g(100)))


def supply(s: Schematic) -> None:
    s.frame("Card supply: U3, then Q4 switched by HOLO_PWR, slow start", (g(10), g(108)), (g(190), g(224)))
    u3 = s.symbol("Regulator_Linear:MCP1700x-330xxTO", "U3", "MCP1700-3302E/TO", (g(40), g(132)),
                  mirror="x", footprint=TO92, ref_at=(g(-3), g(-4)), value_at=(g(-3), g(-6)),
                  description="3.3 V LDO, 250 mA, TO-92, pins 1 GND, 2 VIN, 3 VOUT (from memory, to verify)")
    s.power(u3, "2", "+5V", stub=g(4))
    s.power(u3, "1", "GND", stub=g(1))
    s.label(u3, "3", "SD_LDO", stub=g(6))
    c50 = cap(s, "C50", "10u 16V", (g(16), g(134)), desc="U3 input, ceramic, at U3")
    s.power(c50, "1", "+5V", stub=g(1))
    s.power(c50, "2", "GND", stub=g(1))
    for k, (ref, value, fp, polar, desc) in enumerate((
            ("C51", "10u 10V", C_DISC, False, "U3 output, ceramic, at U3"),
            ("C52", "100u 10V", CP_5MM, True, "SD_LDO bulk: feeds the slow start, U3 refills it"))):
        c = cap(s, ref, value, (g(62 + 12 * k), g(136)), fp=fp, polar=polar, desc=desc)
        s.label(c, "1", "SD_LDO", stub=g(2))
        s.power(c, "2", "GND", stub=g(1))
    tp10 = testpoint(s, "TP10", "SD_LDO", (g(98), g(128)))
    s.label(tp10, "1", "SD_LDO", stub=g(2), then=[(g(-6), 0)])
    # Q4 turned so its source faces SD_LDO on the left and its drain SD_3V3 on the right.
    y = g(150)
    q4 = s.symbol("RobCo:Q_PMOS_GSD_SOT23", "Q4", "AO3401A/DMG2305UX", (g(130), y + g(2)), rot=90,
                  mirror="y", footprint=SOT23, ref_at=(g(0), g(-5)), value_at=(g(0), g(-7)),
                  description="P-channel MOSFET, -20 V, SOT-23, the card supply switch. Source SD_LDO, "
                              "drain SD_3V3, gate HOLO_G. Pins from memory, to verify.")
    s.label(q4, "2", "SD_LDO", stub=g(4))
    s.label(q4, "3", "SD_3V3", stub=g(4))
    s.label(q4, "1", "HOLO_G", stub=g(4))
    r66 = res(s, "R66", "100k", (g(112), g(166)), desc="Q4 gate to source: Q4 off by default")
    s.label(r66, "1", "SD_LDO", stub=g(2))
    s.label(r66, "2", "HOLO_G", stub=g(2))
    c54 = cap(s, "C54", "22n", (g(148), g(166)), desc="Q4 gate to drain: sets the slow start with R67")
    s.label(c54, "1", "SD_3V3", stub=g(2))
    s.label(c54, "2", "HOLO_G", stub=g(2))
    r67 = res(s, "R67", "22k", (g(130), g(176)), desc="Q4 gate current: sets the slow start with C54")
    s.label(r67, "1", "HOLO_G", stub=g(2))
    s.label(r67, "2", "HOLO_SW", stub=g(2))
    q5 = s.symbol("Transistor_BJT:2N3904", "Q5", "2N3904", (g(128), g(198)), footprint=TO92,
                  ref_at=(g(4), g(-1)), value_at=(g(4), g(1)),
                  description="NPN, 2N3904, TO-92. Collector HOLO_SW, base HOLO_B, emitter GND.")
    s.label(q5, "3", "HOLO_SW", stub=g(2))
    s.power(q5, "1", "GND", stub=g(1))
    r65 = res(s, "R65", "10k", (g(110), g(198)), horizontal=True, desc="HOLO_PWR to the Q5 base")
    s.global_label(r65, "1", "HOLO_PWR", shape="input", stub=g(3))
    s.wire(r65.pin("2"), q5.pin("2"))
    s.label_at("HOLO_B", (r65.pin("2")[0] + g(1), r65.pin("2")[1]))
    r64 = res(s, "R64", "100k", (g(86), g(206)), desc="HOLO_PWR pull-down: card supply off while the Pi boots")
    s.global_label(r64, "1", "HOLO_PWR", shape="input", stub=g(2))
    s.power(r64, "2", "GND", stub=g(1))
    r68 = res(s, "R68", "1k", (g(166), g(140)), desc="SD_3V3 bleeder: empties the slot rail when Q4 is off")
    s.label(r68, "1", "SD_3V3", stub=g(2))
    s.power(r68, "2", "GND", stub=g(1))
    tp9 = testpoint(s, "TP9", "SD_3V3", (g(178), g(128)))
    s.label(tp9, "1", "SD_3V3", stub=g(2), then=[(g(-6), 0)])
    flag_at(s, (g(176), g(156)))
    s.wire((g(176), g(156)), (g(176), g(160)))
    s.label_at("SD_3V3", (g(176), g(160)))
    note(s, "HOLO_PWR high: Q5 pulls R67 low, Q4's gate falls to the\n"
            "Miller plateau and C54 sets the slope: about 3.5 V/ms,\n"
            "1 ms from 0 to 3.3 V, about 50 mA into 15 uF (to verify).\n"
            "HOLO_PWR low or floating: R64 and the Pi's pull-down keep\n"
            "Q5 off, R66 holds Q4 off, R68 empties SD_3V3 in 50 ms.", (g(14), g(214)))
    note(s, "U3 stays on: only the switch follows the software.\n"
            "U3 max input about 6 V (from memory, to verify).", (g(140), g(214)))


def protection(s: Schematic) -> None:
    s.frame("Pull-ups and ESD footprint", (g(196), g(116)), (g(320), g(196)))
    for k, (ref, value, rail, net, shape, desc) in enumerate(PULLUPS):
        x, yy = g(208 + 14 * (k % 6)), g(130 + 30 * (k // 6))
        r = res(s, ref, value, (x, yy), desc=desc)
        if rail == "SD_3V3":
            s.label(r, "1", rail, stub=g(2))
        else:
            s.power(r, "1", rail, stub=g(1))
        if shape:
            s.global_label(r, "2", net, shape=shape, stub=g(2))
        else:
            s.label(r, "2", net, stub=g(2))
    d3 = s.symbol("Power_Protection:USBLC6-4SC6", "D3", "USBLC6-4SC6", (g(300), g(166)), footprint=SOT23_6,
                  dnp=True, ref_at=(g(5), g(-6)), value_at=(g(5), g(-4)),
                  description="4-line low-capacitance ESD array, SOT-23-6, not fitted. Pins from memory: "
                              "1 I/O1, 2 GND, 3 I/O2, 4 I/O3, 5 VBUS, 6 I/O4. To verify.")
    for pin, net in (("1", "SD_CLK"), ("3", "SD_DI"), ("4", "SD_CS"), ("6", "SD_DO"), ("5", "SD_3V3")):
        s.label(d3, pin, net, stub=g(3))
    s.power(d3, "2", "GND", stub=g(1))
    note(s, "Card pins pull to SD_3V3 only, Pi pins to +3V3 only.\n"
            "R53 4k7 against 30k to 50k: MISO 2.85 V to 3.0 V.\n"
            "D3 not fitted: fit it if a charged card upsets U4.", (g(200), g(192)))


def draw(s: Schematic) -> None:
    socket(s)
    buffer(s)
    supply(s)
    protection(s)
