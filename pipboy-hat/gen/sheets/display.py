"""Sheet: the display socket J2, the module DS1 and the backlight switch.

Spec sections 4.1 and 4.2.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import C_DISC, SJ2, TO92, TP_LOOP, decoupling, note, res, sideways, testpoint

# J2 pin: (net, kind). Global nets come from J1; local ones stay on this sheet.
J2_PINS = {
    1: ("+3V3", "rail"), 2: ("GND", "rail"), 3: ("TFT_CS", "input"), 4: ("TFT_RESET", "input"),
    5: ("TFT_DC", "input"), 6: ("SPI_MOSI", "input"), 7: ("SPI_SCK_J", "local"), 8: ("TFT_LED", "local"),
    9: ("TFT_SDO", "local"),
}
TOUCH = (10, 11, 12, 13, 14)


def socket(s: Schematic) -> None:
    s.frame("Display socket J2 and module DS1", (g(10), g(12)), (g(118), g(92)))
    j2 = s.symbol("RobCo:ILI9341_Socket_1x14", "J2", "1x14 female header",
                  (g(80), g(48)), footprint="Connector_PinSocket_2.54mm:PinSocket_1x14_P2.54mm_Vertical",
                  ref_at=(g(-2), g(-14)), value_at=(g(-2), g(-16)),
                  description="Display module socket, 1x14 female header, 2.54 mm, 8.5 mm tall. "
                              "Pin order of MSP2807 class modules, to verify against the module bought.")
    for pin, (net, kind) in J2_PINS.items():
        p = str(pin)
        if kind == "rail":
            sideways(s, j2, p, net)
        elif kind == "local":
            if net == "SPI_SCK_J":
                continue
            s.label(j2, p, net, stub=g(3))
        else:
            s.global_label(j2, p, net, shape=kind, stub=g(3))
    for pin in TOUCH:
        s.no_connect(j2, str(pin))
    # JP3, open: the panel's SDO stays off MISO, which the holotape card drives.
    jp3 = s.symbol("Jumper:SolderJumper_2_Open", "JP3", "SDO-MISO", (g(40), g(62)), rot=90, footprint=SJ2,
                   ref_at=(g(7), g(-1)), value_at=(g(11), g(1)),
                   description="Open. Debug only, with no card in J7: closed, the panel SDO drives SPI_MISO.")
    s.label(jp3, "2", "TFT_SDO", stub=g(2))
    s.global_label(jp3, "1", "SPI_MISO", shape="output", stub=g(2))
    # SCK through R24, 33 Ohm, near J1.
    y7 = j2.pin("7")[1]
    r24 = res(s, "R24", "33", (g(44), y7), horizontal=True, desc="SPI clock series resistor, within 10 mm of J1")
    s.wire(r24.pin("2"), j2.pin("7"))
    s.label_at("SPI_SCK_J", (g(52), y7))
    s.global_label(r24, "1", "SPI_SCLK", shape="input", stub=g(3))
    decoupling(s, "C1", "10u 10V", (g(20), g(26)), "+3V3", fp=C_DISC, desc="J2 VCC bulk, ceramic, at J2 pin 1")
    decoupling(s, "C2", "100n", (g(32), g(26)), "+3V3", desc="J2 VCC decoupling, at J2 pin 1")
    s.symbol("RobCo:ILI9341_Module", "DS1", "ILI9341 2.8 inch", (g(106), g(32)), on_board=False,
             ref_at=(g(-4), g(5)), value_at=(g(-4), g(7)),
             description="ILI9341 2.8 inch 240 x 320 SPI module, 14-pin header, example MSP2807. "
                         "Bought, plugged into J2, not soldered: no footprint.")
    note(s, "DS1: bought, off the board.\nIt plugs into J2, the\nboard's socket.", (g(96), g(46)))
    note(s, "J2 pin order: typical of MSP2807 class modules, from memory.\n"
            "TO VERIFY AGAINST THE MODULE BOUGHT. If it differs, do not plug\n"
            "it in: change J2. Silkscreen the pin names beside J2.\n"
            "Touch pins 10 to 14 stay open. The module's SD slot is not wired.\n"
            "SDO reaches MISO only through JP3, open: the holotape card owns\n"
            "MISO. Close JP3 for tft_read_id() only, with no card in J7.\n"
            "VCC is +3V3, 3.3 V logic. Close the module's regulator bypass pad\n"
            "if it asks for it at 3.3 V (to verify on the module).\n"
            "R24 damps the clock: keep it within 10 mm of J1, SPI under 50 mm.\n"
            "DS1 sits on H1 to H4, 11 mm M3 standoffs.", (g(14), g(88)))


def backlight(s: Schematic) -> None:
    s.frame("Backlight switch: on by default", (g(122), g(12)), (g(224), g(92)))
    # Q1, PNP high side: emitter +3V3 on top, collector TFT_LED below.
    q1 = s.symbol("Transistor_BJT:BC327", "Q1", "BC327-25", (g(182), g(36)), mirror="x", footprint=TO92,
                  ref_at=(g(4), g(-1)), value_at=(g(4), g(1)),
                  description="PNP, BC327-25, TO-92. Emitter +3V3, collector TFT_LED, base BL_PB.")
    b1, e1, c1 = q1.pin("2"), q1.pin("3"), q1.pin("1")
    s.power(q1, "3", "+3V3", stub=g(1))
    xb = g(160)
    s.wire(b1, (xb, b1[1]))
    r23 = res(s, "R23", "10k", (g(170), b1[1] - g(6)), desc="Holds Q1 off: base to emitter")
    s.power(r23, "1", "+3V3", stub=g(1))
    s.wire(r23.pin("2"), (g(170), b1[1]))
    s.junction((g(170), b1[1]))
    r22 = res(s, "R22", "470", (xb, b1[1] + g(8)), desc="Q1 base current, BL_PB to Q2 collector")
    s.wire((xb, b1[1]), r22.pin("1"))
    s.label_at("BL_PB", (xb, b1[1] + g(3)), direction="left")
    # Q2, NPN low side: collector to R22, emitter GND.
    q2 = s.symbol("Transistor_BJT:2N3904", "Q2", "2N3904", (xb - g(2), b1[1] + g(20)), footprint=TO92,
                  ref_at=(g(4), g(-1)), value_at=(g(4), g(1)),
                  description="NPN, 2N3904, TO-92. Emitter GND, base BL_NB, collector to R22.")
    s.wire(r22.pin("2"), q2.pin("3"))
    s.power(q2, "1", "GND", stub=g(1))
    b2 = q2.pin("2")
    r21 = res(s, "R21", "4k7", (b2[0] - g(10), b2[1]), horizontal=True, desc="TFT_BL to the Q2 base")
    s.wire(r21.pin("2"), b2)
    s.label_at("BL_NB", (b2[0] - g(6), b2[1]))
    xn = b2[0] - g(17)  # the TFT_BL node
    s.wire((xn, b2[1]), r21.pin("1"))
    s.global_label_at("TFT_BL", (xn - g(3), b2[1]), "left", shape="input")
    s.wire((xn - g(3), b2[1]), (xn, b2[1]))
    r20 = res(s, "R20", "4k7", (xn, b2[1] - g(6)), desc="TFT_BL pull-up to +3V3: backlight on by default")
    s.power(r20, "1", "+3V3", stub=g(1))
    s.wire(r20.pin("2"), (xn, b2[1]))
    s.junction((xn, b2[1]))
    # Collector to the LED pin of J2, with TP7.
    yl = c1[1] + g(4)
    tp7 = testpoint(s, "TP7", "TFT_LED", (g(200), yl - g(6)), fp=TP_LOOP)
    s.wire(c1, (c1[0], yl), (g(200), yl), tp7.pin("1"))
    s.label_at("TFT_LED", (c1[0] + g(3), yl))
    note(s, "TFT_BL high: Q2 on, R22 pulls BL_PB down,\n"
            "Q1 on: the module's LED pin gets +3V3.\n"
            "TFT_BL low: both off, R23 holds Q1 off.", (g(126), g(72)))
    note(s, "Default on: GPIO 19 is an input with a pull-down\n"
            "at reset; R20 wins and the backlight lights.\n"
            "Pip-OS switches it only with this line in the\n"
            "[display] section of PIPOS.CFG: tft_backlight = 19", (g(126), g(81)))
    note(s, "To verify: TO-92 pin orders of the stock symbols,\n"
            "Q1 BC327: 1 C, 2 B, 3 E. Q2 2N3904: 1 E, 2 B, 3 C.", (g(126), g(88)))


def draw(s: Schematic) -> None:
    socket(s)
    backlight(s)
