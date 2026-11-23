"""Sheet: the Pi header J1, the I2C expanders, the clock and the ID EEPROM.

Spec sections 3, 4.2, 4.10 and 4.11.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import HDR, SJ2, SJ3, decoupling, flag_at, note, res, testpoint

# J1 pin: net. Nets that leave this sheet use global labels. NC pins get a flag.
J1_NETS = {
    1: "+3V3", 2: "+5V", 3: "I2C_SDA", 4: "+5V", 5: "I2C_SCL", 6: "GND", 7: "GPIO4", 8: "UART_TX",
    9: "GND", 10: "UART_RX", 11: "BTN_LEFT", 12: "AUDIO_PWM", 13: "BTN_BACK", 14: "GND",
    15: "BTN_RIGHT", 16: "GPIO23", 17: "+3V3", 18: "GPIO24", 19: None, 20: "GND", 21: None,
    22: "ARM", 23: None, 24: None, 25: "GND", 26: None, 27: "ID_SD", 28: "ID_SC", 29: "BTN_UP",
    30: "GND", 31: "BTN_DOWN", 32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16",
    37: "BTN_SELECT", 38: "GPIO20", 39: "GND", 40: "GPIO21",
}
RAILS = ("+3V3", "+5V", "GND")
# Shape of each global label seen from this sheet.
SHAPES = {"I2C_SDA": "bidirectional", "I2C_SCL": "bidirectional", "ID_SD": "bidirectional",
          "ID_SC": "bidirectional", "UART_RX": "input", "UART_TX": "output", "AUDIO_PWM": "output",
          "ARM": "output"}

# Address straps: (jumper, expander, address pin number, pin name, default rail).
STRAPS = [
    ("JP2", "U1", "3", "A2", "GND"), ("JP3", "U1", "2", "A1", "GND"), ("JP4", "U1", "1", "A0", "GND"),
    ("JP5", "U2", "3", "A2", "GND"), ("JP6", "U2", "2", "A1", "GND"), ("JP7", "U2", "1", "A0", "+3V3"),
]


def header(s: Schematic) -> None:
    s.frame("Raspberry Pi header J1", (g(10), g(12)), (g(84), g(112)))
    j1 = s.symbol("Connector_Generic:Conn_02x20_Odd_Even", "J1", "2x20 female header", (g(46), g(52)),
                  footprint="Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
                  ref_at=(g(-3), g(-22)), value_at=(g(-8), g(24)),
                  description="Raspberry Pi 40-pin header, female 2x20 socket. Map in spec/pins.yaml.")
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
            s.global_label(j1, p, net, shape=SHAPES.get(net, "passive" if net.startswith("GPIO") else "output"),
                           stub=g(3))
    note(s, "Odd pins left, even pins right.\n"
            "Pins 19, 21, 23, 24 and 26 are SPI0:\n"
            "not connected, kept for the software.\n"
            "An SPI display added here must not use\n"
            "GPIO 25 (ARM) or 4 as D/C or reset.\n"
            "Pin map and net names: spec/pins.yaml.\n"
            "The pin check compares this sheet with it.", (g(14), g(88)))
    s.power_flag("+3V3", (g(56), g(94)))
    s.power_flag("+5V", (g(66), g(94)))
    s.power_flag("GND", (g(76), g(102)))
    note(s, "The Pi feeds +3V3, +5V and GND.", (g(14), g(108)))


def expander(s: Schematic, ref: str, x: float, y: float, port: str, address: str, desc: str) -> None:
    u = s.symbol("RobCo:PCA9554", ref, "PCA9554", (x, y), footprint="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
                 ref_at=(g(2), g(-13)), value_at=(g(2), g(-11)), description=desc)
    s.global_label(u, "15", "I2C_SDA", shape="bidirectional", stub=g(3))
    s.global_label(u, "14", "I2C_SCL", shape="bidirectional", stub=g(3))
    # INT drops half a row so its label clears the SDA label above it.
    s.label(u, "13", "XINT", stub=g(3), then=[(0, g(3)), (g(-2), 0)])
    for pin, name in (("1", "A0"), ("2", "A1"), ("3", "A2")):
        s.label(u, pin, f"{ref}_{name}", stub=g(3))
    shape = "output" if port == "X0" else "input"
    for i, pin in enumerate(["4", "5", "6", "7", "9", "10", "11", "12"]):
        s.global_label(u, pin, f"{port}.{i}", shape=shape, stub=g(3))
    s.power(u, "16", "+3V3", stub=g(2))
    s.power(u, "8", "GND", stub=g(2))
    s.text(f"{ref} at {address}", (x - g(26), y - g(14)), size=1.5, bold=True)


def straps(s: Schematic, x0: float, y: float, unit: str) -> None:
    for k, (jp, ref, _pin, name, default) in enumerate(t for t in STRAPS if t[1] == unit):
        x = x0 + k * g(13)
        other = "+3V3" if default == "GND" else "GND"
        # Rotated so pad 2, the middle, faces right. Pad 1 is the bridged default.
        j = s.symbol("Jumper:SolderJumper_3_Bridged12", jp, f"{name}={default.lstrip('+')}",
                     (x, y), rot=90, mirror="" if default == "GND" else "x", footprint=SJ3,
                     # Turned 90 degrees, KiCad shows the fields right-justified: the anchor is the text end.
                     ref_at=(g(9), g(-3)), value_at=(g(9), g(3)),
                     description=f"{ref} {name} strap. Pad 1 is bridged by a trace to {default}; cut it to change.")
        top, bottom = ("3", "1") if default == "GND" else ("1", "3")
        s.power(j, top, other if default == "GND" else default, stub=g(1))
        s.power(j, bottom, "GND", stub=g(1))
        s.label(j, "2", f"{ref}_{name}", stub=g(2))


def expanders(s: Schematic) -> None:
    s.frame("I2C expanders", (g(90), g(12)), (g(232), g(112)))
    expander(s, "U1", g(128), g(46), "X0", "0x20", "Expander 0, address 0x20: outputs X0.0 to X0.7")
    expander(s, "U2", g(196), g(46), "X1", "0x21", "Expander 1, address 0x21: inputs X1.0 to X1.7")
    decoupling(s, "C5", "100n", (g(116), g(26)), "+3V3", desc="U1 VDD decoupling, within 3 mm of the pin")
    decoupling(s, "C6", "100n", (g(184), g(26)), "+3V3", desc="U2 VDD decoupling, within 3 mm of the pin")
    straps(s, g(104), g(78), "U1")
    straps(s, g(172), g(78), "U2")
    note(s, "Address = 0100 A2 A1 A0 (typical, check).\n"
            "U1: A2 A1 A0 = GND GND GND, 0x20.  U2: GND GND +3V3, 0x21.\n"
            "Pad 1 of each jumper is bridged by a trace.\n"
            "Cut it and bridge pad 3 to change the address.\n"
            "A PCA9554A has base 0x38: the software must then use 0x38, 0x39.", (g(96), g(98)))
    # INT: open drain on both chips, one pull-up, a header for a later use.
    r3 = res(s, "R3", "10k", (g(212), g(92)), desc="XINT pull-up, shared by U1 and U2 INT")
    s.power(r3, "1", "+3V3", stub=g(1))
    s.label(r3, "2", "XINT", stub=g(2))
    j9 = s.symbol("Connector_Generic:Conn_01x02", "J9", "INT", (g(224), g(100)), mirror="y",
                  footprint=HDR.format("1x02"), ref_at=(g(2), g(-4)), value_at=(g(2), g(4)),
                  description="Expander interrupt, not tied to a Pi pin. Pin 1 XINT, pin 2 GND.")
    s.label(j9, "1", "XINT", stub=g(2))
    s.power(j9, "2", "GND", stub=g(1), then=[(0, g(2))])


def bus(s: Schematic) -> None:
    s.frame("I2C bus", (g(238), g(12)), (g(318), g(60)))
    for k, (ref, net) in enumerate((("R1", "I2C_SDA"), ("R2", "I2C_SCL"))):
        r = res(s, ref, "4k7", (g(248 + 12 * k), g(32)), dnp=True,
                desc=f"{net} pull-up, not fitted: the Pi has 1.8 kOhm on board")
        s.power(r, "1", "+3V3", stub=g(1))
        s.global_label(r, "2", net, shape="bidirectional", stub=g(2))
    for k, (ref, net) in enumerate((("TP4", "I2C_SDA"), ("TP5", "I2C_SCL"))):
        tp = testpoint(s, ref, net, (g(282 + 16 * k), g(28)))
        s.global_label(tp, "1", net, shape="bidirectional", stub=g(2))
    note(s, "R1, R2 not fitted. The Pi has 1.8 kOhm pull-ups\n"
            "on GPIO 2 and 3: a low line sinks 1.83 mA, under\n"
            "the 3 mA limit. 4.7 kOhm more would give 2.54 mA.\n"
            "Every chip on the bus runs from +3V3.", (g(242), g(50)))


def clock(s: Schematic) -> None:
    s.frame("Clock, address 0x68", (g(90), g(122)), (g(232), g(198)))
    x, y = g(140), g(160)
    u3 = s.symbol("RobCo:DS1338", "U3", "DS1338, 3.3 V grade", (x, y),
                  footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", ref_at=(g(3), g(11)), value_at=(g(3), g(13)),
                  description="Real-time clock at 0x68, 3.3 V grade, SOIC-8")
    s.global_label(u3, "5", "I2C_SDA", shape="bidirectional", stub=g(3))
    s.global_label(u3, "6", "I2C_SCL", shape="bidirectional", stub=g(3))
    s.power(u3, "8", "+3V3", stub=g(2))
    s.power(u3, "4", "GND", stub=g(2))
    s.label(u3, "3", "VBAT", stub=g(2), then=[(g(6), 0)])
    s.label(u3, "7", "SQW", stub=g(3))
    y1 = s.symbol("Device:Crystal", "Y1", "32.768 kHz, 6 pF", (x - g(18), y + g(3)), rot=90,
                  footprint="Crystal:Crystal_C26-LF_D2.1mm_L6.5mm_Horizontal",
                  ref_at=(g(5), g(6)), value_at=(g(5), g(8)),
                  description="32.768 kHz crystal, 6 pF load, cylindrical. No load capacitors.")
    x1, x2 = u3.pin("1"), u3.pin("2")
    s.wire(x1, (x1[0] - g(2), x1[1]), (x1[0] - g(2), y), y1.pin("2"))
    s.wire(x2, (x2[0] - g(2), x2[1]), (x2[0] - g(2), y + g(6)), y1.pin("1"))
    bt1 = s.symbol("Device:Battery_Cell", "BT1", "CR2032 holder", (x + g(30), y + g(2)),
                   footprint="Battery:BatteryHolder_Keystone_3002_1x2032", ref_at=(g(3), g(-1)), value_at=(g(3), g(1)),
                   description="CR2032 cell holder, through-hole. Cell not included.")
    s.label(bt1, "1", "VBAT", stub=g(2), then=[(g(-8), 0)])
    # The cell feeds VBAT: the flag tells ERC.
    flag_at(s, (bt1.pin("1")[0], bt1.pin("1")[1] - g(2)))
    s.power(bt1, "2", "GND", stub=g(1))
    decoupling(s, "C7", "100n", (x + g(46), y + g(2)), "+3V3", desc="U3 VCC decoupling")
    r4 = res(s, "R4", "10k", (x + g(56), y), dnp=True, desc="SQW pull-up, not fitted")
    s.power(r4, "1", "+3V3", stub=g(1))
    s.label(r4, "2", "SQW", stub=g(2))
    tp8 = testpoint(s, "TP8", "SQW", (x + g(70), y - g(2)))
    s.label(tp8, "1", "SQW", stub=g(2))
    jp12 = s.symbol("Jumper:SolderJumper_2_Open", "JP12", "VBAT-GND", (x + g(80), y + g(2)), rot=90, footprint=SJ2,
                    ref_at=(g(10), g(-1)), value_at=(g(10), g(1)),
                    description="Open by default. Close only with no cell in BT1: grounds VBAT. Shorts a fitted cell.")
    s.label(jp12, "2", "VBAT", stub=g(2))
    s.power(jp12, "1", "GND", stub=g(1))
    note(s, "VBAT must not float: fit the cell before first power-up,\n"
            "or close JP12 with no cell (DS1307 family rule, to verify\n"
            "for the DS1338). A closed JP12 shorts a fitted cell.", (g(160), g(194)))
    note(s, "Y1: 6 pF load, no capacitors on X1 and X2 (typical, check).\n"
            "A 12.5 pF crystal runs slow. Keep Y1 within 5 mm of U3.\n"
            "U3 pinout as the DS1307 (to verify): 1 X1, 2 X2, 3 VBAT, 4 GND,\n"
            "5 SDA, 6 SCL, 7 SQW, 8 VCC. Buy the 3.3 V grade.", (g(94), g(186)))


def eeprom(s: Schematic) -> None:
    s.frame("HAT ID EEPROM, not fitted", (g(238), g(70)), (g(318), g(160)))
    x, y = g(276), g(100)
    u7 = s.symbol("Memory_EEPROM:24LC32", "U7", "24C32", (x, y), footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                  dnp=True, ref_at=(g(4), g(-9)), value_at=(g(4), g(-11)),
                  description="HAT ID EEPROM, 24C32 class, not fitted. The software does not use it.")
    # A0, A1, A2 to GND through one vertical wire.
    a0, a1, a2 = u7.pin("1"), u7.pin("2"), u7.pin("3")
    xa = a0[0] - g(3)
    s.wire(a0, (xa, a0[1]), (xa, a2[1] + g(3)))
    s.wire(a1, (xa, a1[1]))
    s.wire(a2, (xa, a2[1]))
    s.junction((xa, a1[1]))
    s.junction((xa, a2[1]))
    s.power_symbol("GND", (xa, a2[1] + g(3)))
    s.power(u7, "8", "+3V3", stub=g(2))
    s.power(u7, "4", "GND", stub=g(2))
    s.global_label(u7, "5", "ID_SD", shape="bidirectional", stub=g(3))
    s.global_label(u7, "6", "ID_SC", shape="input", stub=g(3))
    wp = u7.pin("7")
    jp11 = s.symbol("Jumper:SolderJumper_2_Open", "JP11", "WP", (wp[0] + g(4), wp[1] + g(7)), rot=90, footprint=SJ2,
                    ref_at=(g(7), g(-1)), value_at=(g(6), g(1)),
                    description="Closed: WP to GND, writes allowed. Open: R82 pulls WP high, write-protected.")
    s.wire(wp, (wp[0] + g(4), wp[1]), jp11.pin("2"))
    s.power(jp11, "1", "GND", stub=g(1))
    # R82 pulls WP up: open JP11 keeps the chip write-protected.
    xr = wp[0] + g(12)
    r82 = res(s, "R82", "1k", (xr, wp[1] - g(6)), dnp=True,
              desc="WP pull-up to +3V3, not fitted with U7. 1 kOhm as the HAT design guide, to verify.")
    s.power(r82, "1", "+3V3", stub=g(1))
    s.wire(r82.pin("2"), (xr, wp[1]), (wp[0] + g(4), wp[1]))
    s.junction((wp[0] + g(4), wp[1]))
    decoupling(s, "C12", "100n", (g(252), g(128)), "+3V3", dnp=True, desc="U7 VCC decoupling, not fitted")
    for k, (ref, net) in enumerate((("R80", "ID_SD"), ("R81", "ID_SC"))):
        r = res(s, ref, "3k9", (g(266 + 18 * k), g(130)), dnp=True,
                desc=f"{net} pull-up, not fitted. 3.9 kOhm as the HAT design guide, to verify.")
        s.power(r, "1", "+3V3", stub=g(1))
        s.global_label(r, "2", net, shape="bidirectional", stub=g(2))
    note(s, "Not fitted. Separate bus on GPIO 0 and 1, address 0x50.\n"
            "JP11 open: R82 holds WP high, the chip is write-protected.\n"
            "Close JP11 to write. Values from the HAT design guide:\n"
            "R80, R81 3.9 kOhm, R82 1 kOhm (to verify).", (g(242), g(150)))


def holes(s: Schematic) -> None:
    s.frame("Mounting holes", (g(238), g(168)), (g(318), g(198)))
    for k in range(4):
        s.symbol("Mechanical:MountingHole", f"H{k + 1}", "M2.5", (g(250 + 16 * k), g(182)),
                 footprint="MountingHole:MountingHole_2.7mm_M2.5", ref_at=(g(-2), g(4)), value_at=(g(-2), g(6)),
                 description="HAT mounting hole, M2.5. Position from the HAT drawing.")


def draw(s: Schematic) -> None:
    header(s)
    expanders(s)
    bus(s)
    clock(s)
    eeprom(s)
    holes(s)
    note(s, "Proposal. Not built, not validated on hardware.", (g(8), g(206)), size=2.0)
