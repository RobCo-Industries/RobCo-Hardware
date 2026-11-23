"""Sheet: the 5 V input J3, the polyfuse, the reverse-polarity MOSFET and the clamp.

Spec section 4.8.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import DO15, DO35, FUSE_MF_R, H_FIELDS, HDR, SOT23, note, res


def draw(s: Schematic) -> None:
    s.frame("5 V input J3: a regulated 5 V source only", (g(10), g(12)), (g(150), g(72)))
    y = g(36)  # the V_EXT, V_F, +5V line
    j3 = s.symbol("Connector_Generic:Conn_01x02", "J3", "5V IN", (g(18), y), mirror="y",
                  footprint=HDR.format("1x02"), ref_at=(g(-2), g(-3)), value_at=(g(-2), g(6)),
                  description="5 V input header, 2.54 mm, or a 2-pin JST PH. Pin 1 V_EXT, pin 2 GND. "
                              "Silkscreen: REGULATED 5 V IN. NO USB CABLE ON THE PI.")
    s.power(j3, "2", "GND", stub=g(2), then=[(0, g(4))])
    f1 = s.symbol("Device:Polyfuse", "F1", "MF-R090", (g(40), y), rot=90, footprint=FUSE_MF_R,
                  description="Radial polyfuse, 0.9 A hold, 1.8 A trip, 16 V or more, example Bourns MF-R090",
                  **H_FIELDS)
    s.wire(j3.pin("1"), f1.pin("1"))
    s.label_at("V_EXT", (g(26), y))
    # Q3 turned so the drain faces F1, the source faces +5V and the gate points down.
    q3 = s.symbol("RobCo:Q_PMOS_GSD_SOT23", "Q3", "AO3401A/DMG2305UX", (g(62), y + g(2)), rot=90,
                  footprint=SOT23, ref_at=(g(-3), g(-6)), value_at=(g(-8), g(-8)),
                  description="P-channel MOSFET, -20 V or more, +-8 V gate or more, 0.06 Ohm at -4.5 V, "
                              "SOT-23. Drain V_F, source +5V, gate RP_G. Reverse-polarity block.")
    d, src, gate = q3.pin("3"), q3.pin("2"), q3.pin("1")
    s.wire(f1.pin("2"), d)
    s.label_at("V_F", (g(47), y))
    xe = g(100)  # D1 ends the +5V line
    s.wire(src, (xe, y))
    s.wire((g(74), y), (g(74), y - g(6)))
    s.junction((g(74), y))
    s.power_symbol("+5V", (g(74), y - g(6)))
    # Gate: RP_G runs down from the gate, R1 to GND, D2 up to +5V.
    yg = y + g(12)
    d2 = s.symbol("Device:D_Zener", "D2", "1N5234B", (g(84), y + g(6)), rot=270, footprint=DO35,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)),
                  description="Gate clamp, 6.2 V zener, 500 mW, DO-35. Cathode +5V, anode RP_G.")
    s.wire((g(84), y), d2.pin("1"))
    s.junction((g(84), y))
    s.wire(gate, (gate[0], yg), (g(84), yg), d2.pin("2"))
    s.label_at("RP_G", (g(64), yg))
    r1 = res(s, "R1", "10k", (g(76), yg + g(6)), desc="Q3 gate to GND: turns Q3 on, limits D2's current")
    s.wire((g(76), yg), r1.pin("1"))
    s.junction((g(76), yg))
    s.power(r1, "2", "GND", stub=g(1))
    d1 = s.symbol("RobCo:D_TVS_Unidir", "D1", "P6KE6.8A", (xe, y + g(6)), rot=270, footprint=DO15,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)),
                  description="TVS, 600 W, unidirectional, 5.8 V standoff, DO-15, example P6KE6.8A. "
                              "Cathode +5V, anode GND. Short spikes only.")
    s.wire((xe, y), d1.pin("1"))
    s.power(d1, "2", "GND", stub=g(1))
    s.text("REGULATED 5 V ONLY", (g(110), g(24)), size=2.5, bold=True)
    s.text("No USB cable on the Pi\nwhile J3 is powered.", (g(110), g(32)), size=1.8, bold=True)
    note(s, "Q3 orientation: the drain faces J3 and the source is +5V, so the body diode\n"
            "conducts on a correct supply and the gate at GND turns the channel on.\n"
            "Reversed, the body diode blocks and Vgs stays 0 V: Q3 stays off.", (g(14), g(64)))
    note(s, "D2 clamps Vgs near -6.2 V. R1 limits D2's current and discharges the gate.\n"
            "D1 sits after Q3: it takes short spikes, never a reversed supply.", (g(14), g(70)))
    note(s, "J3 and the Pi's USB power port feed the same +5V rail: never both at once.\n"
            "A 9 V or 12 V adapter on J3 damages the Pi and M1 in seconds: the board has\n"
            "no overvoltage protection. Silkscreen at J3: REGULATED 5 V IN. NO USB CABLE ON THE PI.",
         (g(14), g(88)))
    note(s, "To verify: Q3 SOT-23 pads 1 gate, 2 source, 3 drain, as the AO3401A and\n"
            "DMG2305UX (from memory, common but not universal). Own symbol Q_PMOS_GSD_SOT23.\n"
            "D1 P6KE6.8A DO-15 pads 1 cathode, 2 anode. F1 MF-R090 body and lead spacing:\n"
            "own footprint, dimensions from memory. All example parts from memory.", (g(14), g(102)))
