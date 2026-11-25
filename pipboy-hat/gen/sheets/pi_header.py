"""Sheet: the Pi header J1, the I2C pull-up footprints, the ID EEPROM and the holes.

Spec sections 3, 4.6 (R10, R11), 4.7, 6, 7 (H1 to H8) and 9.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import SJ2, SOIC8, decoupling, note, res

# J1 pin: net, from spec/pins.yaml. Nets that leave this sheet use global labels.
# None is not connected and gets a flag.
J1_NETS = {
    1: "+3V3", 2: "+5V", 3: "I2C_SDA", 4: "+5V", 5: "I2C_SCL", 6: "GND", 7: "TFT_RESET", 8: "UART_TX",
    9: "GND", 10: "UART_RX", 11: "BTN_LEFT", 12: "AUDIO_PWM", 13: "BTN_BACK", 14: "GND",
    15: "BTN_RIGHT", 16: "DIAL_A", 17: "+3V3", 18: "DIAL_B", 19: "SPI_MOSI", 20: "GND", 21: "SPI_MISO",
    22: "TFT_DC", 23: "SPI_SCLK", 24: "TFT_CS", 25: "GND", 26: "HOLO_CS", 27: "ID_SD", 28: "ID_SC",
    29: "BTN_UP", 30: "GND", 31: "BTN_DOWN", 32: "HOLO_CD", 33: "HOLO_WP", 34: "GND", 35: "TFT_BL",
    36: "DIAL_PUSH", 37: "BTN_SELECT", 38: "HOLO_BUS", 39: "GND", 40: "HOLO_PWR",
}
RAILS = ("+3V3", "+5V", "GND")
# Shape of each global label seen from this sheet: the Pi's direction.
SHAPES = {"I2C_SDA": "bidirectional", "I2C_SCL": "output", "ID_SD": "bidirectional", "ID_SC": "output",
          "UART_RX": "input", "UART_TX": "output", "SPI_MISO": "input",
          "HOLO_CD": "input", "HOLO_WP": "input"}


def header(s: Schematic) -> None:
    s.frame("Raspberry Pi header J1, on the bottom side", (g(10), g(12)), (g(84), g(112)))
    j1 = s.symbol("Connector_Generic:Conn_02x20_Odd_Even", "J1", "2x20 female header", (g(46), g(52)),
                  footprint="Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
                  ref_at=(g(-3), g(-22)), value_at=(g(-8), g(24)),
                  description="Raspberry Pi 40-pin header, female 2x20 socket, 8.5 mm, on the bottom side. "
                              "Map in spec/pins.yaml.")
    for pin, net in J1_NETS.items():
        p = str(pin)
        if net is None:
            s.no_connect(j1, p)
        elif net in RAILS:
            end, d = s._stub(j1, p, g(3))
            # Turned to point away from J1, the name beside it on the same row.
            left = d == "left"
            s.power_symbol(net, end, rot=90 if left else 270,
                           value_at=(-g(4 + len(net)), g(0)) if left else (g(3), -0.6 if net == "GND" else 0))
        else:
            s.global_label(j1, p, net, shape=SHAPES.get(net, "input" if net.startswith(("BTN", "DIAL"))
                                                         else "output"), stub=g(3))
    note(s, "Odd pins left, even pins right.\n"
            "Pin 26, CE1, selects the holotape card.\n"
            "GPIO 12, 13: card detect, write protect.\n"
            "GPIO 20 HOLO_BUS, 21 HOLO_PWR. No free GPIO.\n"
            "TFT_BL and the holotape pins: no defaults.\n"
            "Pin map and net names: spec/pins.yaml.\n"
            "The pin check compares this sheet with it.", (g(14), g(88)))
    s.power_flag("+3V3", (g(56), g(94)))
    s.power_flag("+5V", (g(66), g(94)))
    s.power_flag("GND", (g(76), g(102)))
    note(s, "The Pi feeds +3V3 and GND. +5V comes from\n"
            "the Pi's USB port or from J3, never both.", (g(14), g(108)))


def board_step(s: Schematic) -> None:
    s.frame("For the board step: J1 side and pin 1", (g(10), g(118)), (g(84), g(146)))
    note(s, "1. J1's body sits on the BOTTOM face of this board.\n"
            "   The Pi Zero hangs below, its own parts facing up,\n"
            "   its male header pushed up into J1.\n"
            "2. That is the stacking of a normal HAT. Seen from\n"
            "   above this board, J1 pin 1 sits straight over the\n"
            "   Pi's pin 1. Do not mirror it a second time.\n"
            "3. In KiCad, J1 goes on the bottom layer, which\n"
            "   flips its pads. Move it so pad 1, seen from the\n"
            "   top, lands on the Pi's pin 1 in a top view.\n"
            "4. Prove it before placing anything else: lay the\n"
            "   Zero's footprint or drawing, top view, under J1\n"
            "   and match pin 1 and pin 2 to J1 pads 1 and 2.\n"
            "H5 to H8 sit at the Zero's M2.5 holes.", (g(14), g(144)))


def pullups(s: Schematic) -> None:
    s.frame("I2C pull-ups, not fitted", (g(90), g(12)), (g(170), g(60)))
    for k, (ref, net) in enumerate((("R10", "I2C_SDA"), ("R11", "I2C_SCL"))):
        r = res(s, ref, "4k7", (g(102 + 22 * k), g(30)), dnp=True,
                desc=f"{net} pull-up, not fitted: the Pi has 1.8 kOhm on board")
        s.power(r, "1", "+3V3", stub=g(1))
        s.global_label(r, "2", net, shape="bidirectional", stub=g(2))
    note(s, "R10, R11 not fitted. The Pi has 1.8 kOhm pull-ups\n"
            "on GPIO 2 and 3: a low line sinks 1.83 mA, under\n"
            "the 3 mA limit. 4.7 kOhm more would give 2.54 mA.", (g(94), g(56)))


def eeprom(s: Schematic) -> None:
    s.frame("HAT ID EEPROM, not fitted", (g(90), g(70)), (g(170), g(160)))
    x, y = g(128), g(100)
    u2 = s.symbol("Memory_EEPROM:24LC32", "U2", "24C32", (x, y), footprint=SOIC8,
                  dnp=True, ref_at=(g(4), g(-9)), value_at=(g(4), g(-11)),
                  description="HAT ID EEPROM, 24C32 class, not fitted. Pip-OS does not read it.")
    # A0, A1, A2 to GND through one vertical wire.
    a0, a1, a2 = u2.pin("1"), u2.pin("2"), u2.pin("3")
    xa = a0[0] - g(3)
    s.wire(a0, (xa, a0[1]), (xa, a2[1] + g(3)))
    s.wire(a1, (xa, a1[1]))
    s.wire(a2, (xa, a2[1]))
    s.junction((xa, a1[1]))
    s.junction((xa, a2[1]))
    s.power_symbol("GND", (xa, a2[1] + g(3)))
    s.power(u2, "8", "+3V3", stub=g(2))
    s.power(u2, "4", "GND", stub=g(2))
    s.global_label(u2, "5", "ID_SD", shape="bidirectional", stub=g(3))
    s.global_label(u2, "6", "ID_SC", shape="input", stub=g(3))
    wp = u2.pin("7")
    jp2 = s.symbol("Jumper:SolderJumper_2_Open", "JP2", "WP", (wp[0] + g(4), wp[1] + g(7)), rot=90, footprint=SJ2,
                   ref_at=(g(7), g(-1)), value_at=(g(6), g(1)),
                   description="Open by default. Closed: WP to GND, writes allowed.")
    s.wire(wp, (wp[0] + g(4), wp[1]), jp2.pin("2"))
    s.power(jp2, "1", "GND", stub=g(1))
    s.label_at("EE_WP", (wp[0] + g(4), wp[1] + g(2)))
    xr = wp[0] + g(12)
    r14 = res(s, "R14", "1k", (xr, wp[1] - g(6)), dnp=True,
              desc="WP pull-up to +3V3, not fitted. 1 kOhm as the HAT design guide, to verify.")
    s.power(r14, "1", "+3V3", stub=g(1))
    s.wire(r14.pin("2"), (xr, wp[1]), (wp[0] + g(4), wp[1]))
    s.junction((wp[0] + g(4), wp[1]))
    decoupling(s, "C11", "100n", (g(104), g(128)), "+3V3", dnp=True, desc="U2 VCC decoupling, not fitted")
    for k, (ref, net) in enumerate((("R12", "ID_SD"), ("R13", "ID_SC"))):
        r = res(s, ref, "3k9", (g(118 + 18 * k), g(130)), dnp=True,
                desc=f"{net} pull-up, not fitted. 3.9 kOhm as the HAT design guide, to verify.")
        s.power(r, "1", "+3V3", stub=g(1))
        s.global_label(r, "2", net, shape="bidirectional", stub=g(2))
    note(s, "Not fitted. Separate bus on GPIO 0 and 1, address 0x50.\n"
            "JP2 open: R14 holds WP high, the chip is write-protected.\n"
            "Close JP2 to write. Values from the HAT design guide:\n"
            "R12, R13 3.9 kOhm, R14 1 kOhm (to verify).", (g(94), g(154)))


def holes(s: Schematic) -> None:
    s.frame("Mounting holes", (g(176), g(12)), (g(260), g(66)))
    rows = (("M3", "MountingHole:MountingHole_3.2mm_M3", "Display module standoff, M3, 11 mm. "
             "Position from the module bought."),
            ("M2.5", "MountingHole:MountingHole_2.7mm_M2.5", "Pi Zero standoff, M2.5. "
             "Position from the Zero drawing."))
    for row, (value, fp, desc) in enumerate(rows):
        for k in range(4):
            n = 4 * row + k + 1
            s.symbol("Mechanical:MountingHole", f"H{n}", value, (g(188 + 18 * k), g(26 + 20 * row)),
                     footprint=fp, ref_at=(g(-2), g(4)), value_at=(g(-2), g(6)), description=desc)
    note(s, "H1 to H4: display module standoffs.\n"
            "H5 to H8: Pi Zero standoffs.", (g(180), g(62)))


def draw(s: Schematic) -> None:
    header(s)
    board_step(s)
    pullups(s)
    eeprom(s)
    holes(s)
    note(s, "Proposal. Not built, not validated on hardware.", (g(12), g(206)), size=2.0)
