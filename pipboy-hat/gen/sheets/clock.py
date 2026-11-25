"""Sheet: the DS1338 clock, its crystal, the CR1220 cell and the VBAT jumper.

Spec section 4.6. R10, R11 sit on the Pi header sheet, TP4, TP5 on the serial sheet.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import SJ2, SOIC8, decoupling, flag_at, note, res, testpoint


def draw(s: Schematic) -> None:
    s.frame("Clock, address 0x68", (g(10), g(12)), (g(152), g(76)))
    x, y = g(60), g(40)
    u1 = s.symbol("RobCo:DS1338", "U1", "DS1338, 3.3 V grade", (x, y), footprint=SOIC8,
                  ref_at=(g(3), g(11)), value_at=(g(3), g(13)),
                  description="Real-time clock at 0x68, 3.3 V grade, SOIC-8, example DS1338Z-33+")
    s.global_label(u1, "5", "I2C_SDA", shape="bidirectional", stub=g(3))
    s.global_label(u1, "6", "I2C_SCL", shape="input", stub=g(3))
    s.power(u1, "8", "+3V3", stub=g(2))
    s.power(u1, "4", "GND", stub=g(2))
    s.label(u1, "3", "VBAT", stub=g(2), then=[(g(6), 0)])
    s.label(u1, "7", "SQW", stub=g(3))
    y1 = s.symbol("Device:Crystal", "Y1", "32.768 kHz, 6 pF", (x - g(18), y + g(3)), rot=90,
                  footprint="Crystal:Crystal_C26-LF_D2.1mm_L6.5mm_Horizontal",
                  ref_at=(g(5), g(6)), value_at=(g(5), g(8)),
                  description="32.768 kHz crystal, 6 pF load, cylindrical. No load capacitors.")
    x1, x2 = u1.pin("1"), u1.pin("2")
    s.wire(x1, (x1[0] - g(2), x1[1]), (x1[0] - g(2), y), y1.pin("2"))
    s.wire(x2, (x2[0] - g(2), x2[1]), (x2[0] - g(2), y + g(6)), y1.pin("1"))
    bt1 = s.symbol("Device:Battery_Cell", "BT1", "CR1220 holder", (x + g(30), y + g(2)),
                   footprint="Battery:BatteryHolder_Keystone_3001_1x12mm", ref_at=(g(3), g(-1)),
                   value_at=(g(3), g(1)), description="CR1220 cell holder, through-hole. Cell not included.")
    s.label(bt1, "1", "VBAT", stub=g(2), then=[(g(-8), 0)])
    # The cell feeds VBAT: the flag tells ERC.
    flag_at(s, (bt1.pin("1")[0], bt1.pin("1")[1] - g(2)))
    s.power(bt1, "2", "GND", stub=g(1))
    decoupling(s, "C10", "100n", (x + g(46), y + g(2)), "+3V3", desc="U1 VCC decoupling")
    r15 = res(s, "R15", "10k", (x + g(56), y), dnp=True, desc="SQW pull-up, not fitted")
    s.power(r15, "1", "+3V3", stub=g(1))
    s.label(r15, "2", "SQW", stub=g(2))
    tp8 = testpoint(s, "TP8", "SQW", (x + g(70), y - g(2)))
    s.label(tp8, "1", "SQW", stub=g(2))
    jp1 = s.symbol("Jumper:SolderJumper_2_Open", "JP1", "VBAT-GND", (x + g(80), y + g(2)), rot=90, footprint=SJ2,
                   ref_at=(g(10), g(-1)), value_at=(g(10), g(1)),
                   description="Open by default. Close only with no cell in BT1: grounds VBAT. Shorts a fitted cell.")
    s.label(jp1, "2", "VBAT", stub=g(2))
    s.power(jp1, "1", "GND", stub=g(1))
    note(s, "VBAT must not float: fit the cell before first power-up,\n"
            "or close JP1 with no cell (DS1307 family rule, to verify\n"
            "for the DS1338). A closed JP1 shorts a fitted cell.", (g(80), g(72)))
    note(s, "Y1: 6 pF load, no capacitors on X1 and X2 (typical, check).\n"
            "Keep Y1 within 5 mm of U1, no traces under it.\n"
            "U1 pinout as the DS1307 (to verify): 1 X1, 2 X2, 3 VBAT,\n"
            "4 GND, 5 SDA, 6 SCL, 7 SQW, 8 VCC. Buy the 3.3 V grade.", (g(14), g(72)))
    note(s, "CR1220: about 35 mAh, under 1 uA from VBAT: about 4 years (typical, check).\n"
            "BT1 Keystone 3001 pad polarity: to verify against the holder bought.\n"
            "R15 not fitted: SQW is unused. Pip-OS reads the DS1338 at 0x68 as chip=0.\n"
            "SQW is open drain (to verify): fit R15 to probe TP8, else TP8 floats.", (g(14), g(88)))
