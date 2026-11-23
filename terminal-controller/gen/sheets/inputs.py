"""Sheet: the eight optocoupler inputs, J4 and the field common jumper.

Spec section 4.8.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import C_DISC, DO35, HDR, R_HALF_WATT, TERM_10, decoupling, note, res

CHANNELS = 8
# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-4)), value_at=(g(6), g(-2)))


def terminal(s: Schematic) -> None:
    j4 = s.symbol("Connector:Screw_Terminal_01x10", "J4", "Inputs", (g(16), g(66)), mirror="y",
                  footprint=TERM_10, ref_at=(g(2), g(-11)), value_at=(g(2), g(13)),
                  description="Input terminals, 10 ways, 3.5 mm: IN0 to IN7, IN_COM, +V_S")
    for i in range(CHANNELS):
        s.label(j4, str(i + 1), f"IN{i}", stub=g(3))
    s.label(j4, "9", "IN_COM", stub=g(3))
    end, _ = s._stub(j4, "10", g(3))
    s.power_symbol("+V_S", end, rot=270, value_at=(g(3), 0))
    note(s, "Silkscreen:\nX1.0 to X1.7,\nCOM, +V.", (g(12), g(90)))


def channel(s: Schematic, i: int, at) -> None:
    """IN{i} through R6{i} to the LED of one opto channel; its transistor pulls X1.{i} low."""
    x, oy = at
    unit = i % 4 + 1
    ref = "U5" if i < 4 else "U6"
    ox = x + g(30)
    opto = s.symbol("Isolator:LTV-847", ref, "LTV-847", (ox, oy), unit=unit, footprint="Package_DIP:DIP-16_W7.62mm",
                    ref_at=(g(-6), g(-5)), value_at=(g(0), g(-5)),
                    description="Quad optocoupler, DIP-16, LTV-847 class. Channels 0 to 3 in U5, 4 to 7 in U6.")
    a, k = opto.pin(str(2 * unit - 1)), opto.pin(str(2 * unit))
    c = opto.pin(str(18 - 2 * unit))
    ya = a[1]
    r6 = res(s, f"R6{i}", "2k2/1k, 0.5W", (x + g(8), ya), horizontal=True, fp=R_HALF_WATT,
             desc=f"IN{i} LED current: 2.2 kOhm for 12 V and 24 V, 1 kOhm for 5 V; 0.5 W", **H_FIELDS)
    s.label_at(f"IN{i}", (x, ya))
    s.wire((x, ya), r6.pin("1"))
    # D1{i}: cathode at the opto anode, anode at the opto cathode.
    xd = x + g(18)
    d = s.symbol("Diode:1N4148", f"D1{i}", "1N4148", (xd, oy + g(1)), rot=270, footprint=DO35,
                 ref_at=(g(-5), g(0)), value_at=(g(-8), g(2)),
                 description=f"Reverse clamp across the LED of channel {i}")
    s.wire(r6.pin("2"), d.pin("1"))
    s.wire(d.pin("1"), a)
    s.junction(d.pin("1"))
    yk = oy + g(4)
    s.wire(k, (k[0] - g(2), k[1]), (k[0] - g(2), yk), d.pin("2"))
    s.wire(d.pin("2"), (x + g(4), yk))
    s.junction(d.pin("2"))
    s.label_at("IN_COM", (x + g(4), yk), "left")
    # Transistor side: emitter to GND, collector to X1.{i} with its pull-up and filter.
    s.power(opto, str(17 - 2 * unit), "GND", stub=g(2), then=[(0, g(2))])
    xr, xc, xl = ox + g(14), ox + g(22), ox + g(30)
    r7 = res(s, f"R7{i}", "47k", (xr, c[1] - g(4)), desc=f"X1.{i} pull-up to +3V3")
    s.power(r7, "1", "+3V3", stub=g(1))
    c4 = s.symbol("Device:C", f"C4{i}", "10n", (xc, c[1] + g(4)), footprint=C_DISC, dnp=True,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)), description=f"X1.{i} filter, not fitted")
    s.power(c4, "2", "GND", stub=g(1))
    s.wire(c, (xl, c[1]))
    s.wire(r7.pin("2"), (xr, c[1]))
    s.wire(c4.pin("1"), (xc, c[1]))
    s.junction((xr, c[1]))
    s.junction((xc, c[1]))
    s.global_label_at(f"X1.{i}", (xl, c[1]), "right", shape="output", key=("X1", i))


def common(s: Schematic) -> None:
    s.frame("Field common and logic decoupling", (g(160), g(12)), (g(224), g(52)))
    jp10 = s.symbol("Jumper:Jumper_2_Bridged", "JP10", "COM-GND", (g(180), g(28)), rot=90,
                    footprint=HDR.format("1x02"), ref_at=(g(9), g(-1)), value_at=(g(11), g(1)),
                    description="IN_COM to GND. Shunt fitted. Remove for sensors with their own isolated supply.")
    s.label(jp10, "2", "IN_COM", stub=g(2))
    s.power(jp10, "1", "GND", stub=g(1))
    decoupling(s, "C11", "100n", (g(206), g(28)), "+3V3", desc="+3V3 decoupling at the R70 to R77 pull-ups")
    note(s, "JP10 fitted: sensors on +V_S return on IN_COM.\n"
            "Remove it when sensors have their own\n"
            "isolated supply and return on IN_COM.", (g(164), g(48)))


def table(s: Schematic) -> None:
    s.frame("Resistor to fit per field voltage", (g(160), g(58)), (g(224), g(128)))
    note(s, "5 V on +V_S: R60 to R67 = 1 kOhm, 0.5 W.\n"
            "12 V on +V_S: R60 to R67 = 2.2 kOhm, 0.5 W.\n"
            "24 V on +V_S: R60 to R67 = 2.2 kOhm, 0.5 W.\n"
            "Every voltage: R70 to R77 = 47 kOhm.", (g(164), g(72)))
    note(s, "Never put 24 V on 1 kOhm inputs: 23.9 mA x\n"
            "23.9 V = 0.57 W, above the 0.5 W rating.\n"
            "At 24 V, 2.2 kOhm dissipates 0.26 W: keep\n"
            "R60 to R67 at least 2 mm apart.\n"
            "Mark the fitted value on the board.", (g(164), g(86)))
    note(s, "An active input lights the LED and pulls\n"
            "X1.n low: the expander reads 0 when active.\n"
            "D10 to D17 clamp a reversed input to 0.7 V.\n"
            "Worst case with all eight inputs on: margin\n"
            "at least 3.2 (spec 4.8). LTV-847 pinout\n"
            "from the stock symbol: 1-8 anode, cathode;\n"
            "16 C1, 15 E1 down to 10 C4, 9 E4. To check\n"
            "against the data sheet.", (g(164), g(112)))
    note(s, "C40 to C47 not fitted: 24 kOhm x 10 nF\n"
            "= 0.24 ms if long cables bring noise.", (g(164), g(122)))


def draw(s: Schematic) -> None:
    s.frame("Eight optocoupler inputs, one per expander line X1.0 to X1.7", (g(10), g(12)), (g(154), g(128)))
    terminal(s)
    s.repeat(CHANNELS, (g(36), g(26)), (0, g(13)), lambda i, at: channel(s, i, at))
    common(s)
    table(s)
