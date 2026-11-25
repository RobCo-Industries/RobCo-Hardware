"""Sheet: the six keys, the dial with its push, the series resistors and the panel header.

Spec section 4.4.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import ENCODER, HDR, KEY_12MM, cap, note, res, sideways

# (Pi-side net, series resistor, capacitor, its value, fitted, switch, J5 pin), in the spec's order.
LINES = [
    ("BTN_UP", "R40", "C40", "100n", False, "SW1", 2),
    ("BTN_DOWN", "R41", "C41", "100n", False, "SW2", 3),
    ("BTN_LEFT", "R42", "C42", "100n", False, "SW3", 4),
    ("BTN_RIGHT", "R43", "C43", "100n", False, "SW4", 5),
    ("BTN_SELECT", "R44", "C44", "100n", False, "SW5", 6),
    ("BTN_BACK", "R45", "C45", "100n", False, "SW6", 7),
    ("DIAL_A", "R46", "C47", "10n", True, "SW7", 8),
    ("DIAL_B", "R47", "C48", "10n", True, "SW7", 9),
    ("DIAL_PUSH", "R48", "C46", "100n", False, "SW7", 10),
]


def lines(s: Schematic) -> None:
    s.frame("Keys and dial: each switch ties its line to GND", (g(10), g(12)), (g(136), g(138)))

    def channel(i: int, at) -> None:
        x, y = at
        net, rs, cs, cval, fitted, sw, _ = LINES[i]
        name = net.split("_", 1)[1] if net.startswith("BTN") else net
        s.global_label_at(net, (x, y), "left", shape="output", key=("line", i))
        r = res(s, rs, "1k", (x + g(18), y), horizontal=True, desc=f"{name}: series resistor, Pi side to switch side")
        s.wire((x, y), r.pin("1"))
        xc = x + g(8)
        c = cap(s, cs, cval, (xc, y + g(4)), dnp=not fitted,
                desc=f"{net} to GND" + ("" if fitted else ", not fitted: for a noisy panel cable"))
        s.wire((xc, y), c.pin("1"))
        s.junction((xc, y))
        s.power(c, "2", "GND", stub=g(1))
        sw_net = f"{net}_SW"
        if sw == "SW7":
            s.wire(r.pin("2"), (x + g(24), y))
            s.label_at(sw_net, (x + g(24), y))
            return
        key = s.symbol("Switch:SW_Push", sw, name, (x + g(48), y), footprint=KEY_12MM,
                       ref_at=(g(-3), g(-4)), value_at=(g(1), g(-4)),
                       description=f"{name} key, 12 x 12 mm tactile switch, example Omron B3F-4055")
        s.wire(r.pin("2"), key.pin("1"))
        s.label_at(sw_net, (x + g(24), y))
        s.power(key, "2", "GND", stub=g(1))

    s.repeat(len(LINES), (g(20), g(20)), (0, g(13)), channel)


def dial(s: Schematic) -> None:
    sw7 = s.symbol("Device:RotaryEncoder_Switch", "SW7", "PEC11R-4215F-S0024", (g(100), g(106)),
                   footprint=ENCODER, ref_at=(g(-4), g(-6)), value_at=(g(-4), g(7)),
                   description="Rotary encoder with push, 24 detents, 24 pulses, example Bourns "
                               "PEC11R-4215F-S0024. A, B, C common; S1, S2 the push switch.")
    s.label(sw7, "A", "DIAL_A_SW", stub=g(2), then=[(0, g(-2)), (g(-3), 0)])
    s.label(sw7, "B", "DIAL_B_SW", stub=g(2), then=[(0, g(2)), (g(-3), 0)])
    sideways(s, sw7, "C", "GND", stub=g(6))
    s.label(sw7, "S1", "DIAL_PUSH_SW", stub=g(3))
    sideways(s, sw7, "S2", "GND")


def panel(s: Schematic) -> None:
    j5 = s.symbol("Connector_Generic:Conn_01x11", "J5", "Front panel", (g(124), g(52)), footprint=HDR.format("1x11"),
                  dnp=True, ref_at=(g(2), g(-14)), value_at=(g(2), g(14)),
                  description="Front panel header, 1x11, 2.54 mm, not fitted: GND, UP, DOWN, LEFT, RIGHT, "
                              "SELECT, BACK, DIAL_A, DIAL_B, DIAL_PUSH, GND, on the switch side nets.")
    for net, _, _, _, _, _, pin in LINES:
        s.label(j5, str(pin), f"{net}_SW", stub=g(3))
    # GND on the end pins, led away from the label column.
    end, _ = s._stub(j5, "1", g(3), then=[(0, g(-2)), (g(-6), 0)])
    s.power_symbol("GND", end, rot=90, value_at=(-g(7), 0))
    s.power(j5, "11", "GND", stub=g(3), then=[(0, g(2))])


def draw(s: Schematic) -> None:
    lines(s)
    dial(s)
    panel(s)
    note(s, "J5 not fitted. Fit the on-board switches\nor a panel on J5, not both on one line.", (g(96), g(78)))
    note(s, "Pull-ups: the Pi's own, about 50 kOhm (typical, check).\n"
            "R40 to R48, 1 kOhm, limit a fault on J5 to 3.3 mA.\n"
            "A pressed key reads 3.3 V x 1 / 51 = 0.065 V.\n"
            "C40 to C46 not fitted: for a noisy panel cable.\n"
            "C47, C48: dial filter, 10 nF. A release rises in\n"
            "50 kOhm x 10 nF = 0.5 ms, a press falls in 10 us.", (g(14), g(154)))
    note(s, "DIAL WORKING LIMIT: about 12 detents per second,\n"
            "half a turn per second, at the 100 Hz sampling.\n"
            "A faster spin can miss a state and shift the detent\n"
            "phase until power-off. Pulses must equal detents.", (g(70), g(147)))
    note(s, "To verify: SW7 pins A, C, B and the push S1, S2 of the\n"
            "PEC11R, and its own footprint, from memory. SW1 to SW6:\n"
            "12 mm switch pads 1 and 2 of the stock SW_PUSH-12mm.", (g(70), g(155)))
