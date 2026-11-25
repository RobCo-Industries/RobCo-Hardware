"""Sheet: the holotape slot. J7, a full-size SD socket on SPI0 CE1, its own
3.3 V regulator U3 from +5V, the bus resistors and the pull-ups.

Spec section 4.12.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import C_DISC, CP_5MM, TO92, cap, note, res, sideways, testpoint

SD_SOCKET = "Connector_Card:SD_Hirose_DM1AA_SF_PEJ82"

# J7 pin: card-side net, in SPI mode. Pin numbers of the own symbol, which
# follow the pads of the stock Hirose DM1AA footprint.
J7_LINES = {"7": "SD_DO", "8": "SD_DAT1", "9": "SD_DAT2", "1": "SD_CS", "5": "SD_CLK", "2": "SD_DI"}

# (ref, Pi-side net, its label shape here, card-side net). 33 Ohm each, at J7.
SERIES = [
    ("R54", "SPI_SCLK", "input", "SD_CLK"),
    ("R55", "SPI_MOSI", "input", "SD_DI"),
    ("R56", "HOLO_CS", "input", "SD_CS"),
    ("R57", "SPI_MISO", "output", "SD_DO"),
]

# (ref, value, rail, net, global?). Pi-side lines pull to +3V3, card-only lines to SD_3V3.
PULLUPS = [
    ("R50", "10k", "+3V3", "HOLO_CS", "input", "CS pull-up: the card stays deselected while the Pi boots"),
    ("R53", "47k", "+3V3", "SPI_MISO", "output", "MISO pull-up: holds the line with no card selected"),
    ("R58", "10k", "+3V3", "HOLO_CD", "output", "Card detect pull-up"),
    ("R59", "10k", "+3V3", "HOLO_WP", "output", "Write protect pull-up"),
    ("R51", "47k", "SD_3V3", "SD_DAT1", None, "DAT1 pull-up, unused in SPI mode (10k to 100k, to verify)"),
    ("R52", "47k", "SD_3V3", "SD_DAT2", None, "DAT2 pull-up, unused in SPI mode (10k to 100k, to verify)"),
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
    for k, (ref, value, fp, polar, desc) in enumerate((
            ("C51", "10u 10V", C_DISC, False, "U3 output, ceramic, at U3"),
            ("C52", "100u 10V", CP_5MM, True, "Slot bulk: takes the charge of a card pushed in live"),
            ("C53", "100n", C_DISC, False, "J7 VDD decoupling, at J7 pin 4"))):
        c = cap(s, ref, value, (g(90 + 14 * k), g(36)), fp=fp, polar=polar, desc=desc)
        s.label(c, "1", "SD_3V3", stub=g(2))
        s.power(c, "2", "GND", stub=g(1))
    note(s, "SPI mode: 1 CS, 2 DI, 5 CLK, 7 DO. DAT1 and DAT2 unused, pulled up.\n"
            "CP closes to SW, the common, with a card in: HOLO_CD low.\n"
            "WP open with the card's slider on LOCK: HOLO_WP high.\n"
            "With no card WP reads high. Switch pads and polarity:\n"
            "from memory, TO VERIFY against the Hirose DM1AA data sheet.\n"
            "Shell to GND. No TVS: the contacts sit inside the socket.", (g(14), g(92)))
    note(s, "Each SPI line meets J7 through its own\n"
            "33 Ohm at J7, a star from J1. MISO reaches\n"
            "the card only: the display SDO is on JP3,\n"
            "open, on the display sheet.", (g(88), g(66)))


def supply(s: Schematic) -> None:
    s.frame("Slot supply: U3 from +5V", (g(132), g(12)), (g(224), g(60)))
    u3 = s.symbol("Regulator_Linear:MCP1700x-330xxTO", "U3", "MCP1700-3302E/TO", (g(170), g(28)),
                  mirror="x", footprint=TO92, ref_at=(g(-3), g(-4)), value_at=(g(-3), g(-6)),
                  description="3.3 V LDO, 250 mA, TO-92, pins 1 GND, 2 VIN, 3 VOUT (from memory, to verify)")
    s.power(u3, "2", "+5V", stub=g(4))
    s.power(u3, "1", "GND", stub=g(1))
    s.label(u3, "3", "SD_3V3", stub=g(6))
    c50 = cap(s, "C50", "10u 16V", (g(146), g(30)), desc="U3 input, ceramic, at U3")
    s.power(c50, "1", "+5V", stub=g(1))
    s.power(c50, "2", "GND", stub=g(1))
    tp9 = testpoint(s, "TP9", "SD_3V3", (g(196), g(22)))
    s.label(tp9, "1", "SD_3V3", stub=g(2), then=[(g(-6), 0)])
    note(s, "SD_3V3 feeds only the card and the DAT1, DAT2 pull-ups.\n"
            "+3V3 from the Pi has no room for a card: 120 + 100 mA.\n"
            "Card in live: C51 + C52 + C53 hold SD_3V3, U3 limits\n"
            "the current drawn from +5V. Card up to 100 mA (to verify).\n"
            "U3 max input about 6 V (from memory, to verify).", (g(136), g(56)))


def resistors(s: Schematic) -> None:
    s.frame("Bus resistors and pull-ups", (g(132), g(66)), (g(224), g(126)))
    for k, (ref, net, shape, card) in enumerate(SERIES):
        r = res(s, ref, "33", (g(150), g(74 + 8 * k)), horizontal=True,
                desc=f"{net} to J7, series, within 10 mm of J7")
        s.global_label(r, "1", net, shape=shape, stub=g(3))
        s.label(r, "2", card, stub=g(3))
    for k, (ref, value, rail, net, shape, desc) in enumerate(PULLUPS):
        x, y = g(180 + 14 * (k % 3)), g(76 + 26 * (k // 3))
        r = res(s, ref, value, (x, y), desc=desc)
        if rail == "SD_3V3":
            s.label(r, "1", rail, stub=g(2))
        else:
            s.power(r, "1", rail, stub=g(1))
        if shape:
            s.global_label(r, "2", net, shape=shape, stub=g(2))
        else:
            s.label(r, "2", net, stub=g(2))
    note(s, "33 Ohm damps the card's edges at 10 MHz and\n"
            "slows an ESD pulse into the Pi's pads.", (g(136), g(110)))


def draw(s: Schematic) -> None:
    socket(s)
    supply(s)
    resistors(s)
