"""Sheet: the button header J5, the serial console J6 and the free-pin header J7.

Spec sections 4.6, 4.7 and 4.9.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import HDR, note, res

# (J5 pin, net from the Pi, series resistor, unfitted pull-up)
BUTTONS = [(2, "BTN_UP", "R40", "R50"), (3, "BTN_DOWN", "R41", "R51"), (4, "BTN_LEFT", "R42", "R52"),
           (5, "BTN_RIGHT", "R43", "R53"), (6, "BTN_SELECT", "R44", "R54"), (7, "BTN_BACK", "R45", "R55")]
# J7 odd pin: free Pi pin. Every even pin is GND.
FREE = [(1, "GPIO4"), (3, "GPIO12"), (5, "GPIO13"), (7, "GPIO19"), (9, "GPIO20"), (11, "GPIO21"),
        (13, "GPIO16"), (15, "GPIO23"), (17, "GPIO24")]
# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-2)), value_at=(g(3), g(3)))


def sideways(s: Schematic, part, pin: str, net: str) -> None:
    """A rail on a connector pin: the symbol turned to point away, its name beside it."""
    end, d = s._stub(part, pin, g(3))
    left = d == "left"
    s.power_symbol(net, end, rot=90 if left else 270,
                   value_at=(-g(4 + len(net)), 0) if left else (g(3), -0.6 if net == "GND" else 0))


def buttons(s: Schematic) -> None:
    s.frame("Buttons J5: six buttons, each to GND, Pi pull-ups", (g(10), g(12)), (g(150), g(110)))
    top, step = g(28), g(13)

    def channel(i: int, at) -> None:
        x, y = at
        pin, net, rs, rp = BUTTONS[i]
        name = net[4:]
        s.global_label_at(net, (x, y), "left", shape="bidirectional", key=("btn", i))
        r = res(s, rs, "1k", (x + g(8), y), horizontal=True, desc=f"{name}: series resistor, Pi pin to J5",
                **H_FIELDS)
        s.wire((x, y), r.pin("1"))
        node = x + g(20)
        rpu = res(s, rp, "10k", (node + g(6), y - g(3)), dnp=True, desc=f"{name}: pull-up to +3V3, not fitted")
        s.power(rpu, "1", "+3V3", stub=g(1))
        s.wire(r.pin("2"), (node + g(12), y))
        s.wire(rpu.pin("2"), (node + g(6), y))
        s.junction((node + g(6), y))
        s.label_at(f"J5_{name}", (node + g(12), y))

    s.repeat(len(BUTTONS), (g(30), top), (0, step), channel)
    j5 = s.symbol("Connector_Generic:Conn_01x09", "J5", "Buttons", (g(124), g(54)),
                  footprint=HDR.format("1x09"), ref_at=(g(2), g(-11)), value_at=(g(2), g(13)),
                  description="Button header, 1x9, 2.54 mm: GND, UP, DOWN, LEFT, RIGHT, SELECT, BACK, GND, 3V3")
    for pin, net, _, _ in BUTTONS:
        s.label(j5, str(pin), f"J5_{net[4:]}", stub=g(3))
    sideways(s, j5, "1", "GND")
    sideways(s, j5, "8", "GND")
    p9 = j5.pin("9")
    r59 = res(s, "R59", "100", (p9[0] - g(10), p9[1]), horizontal=True,
              desc="Limits a short on J5 pin 9 to 33 mA", ref_at=(g(3), g(3)), value_at=(g(3), g(5)))
    s.wire(r59.pin("2"), p9)
    end, _ = s._stub(r59, "1", g(2))
    s.power_symbol("+3V3", end, rot=90, value_at=(-g(8), 0))
    note(s, "R40 to R45: 1 kOhm limit a cable fault on a rail to 3.3 mA.\n"
            "A pressed button reads 3.3 V x 1 / (50 + 1) = 0.065 V.\n"
            "R50 to R55 not fitted: for a BCM2711, not supported.\n"
            "R59: a short on pin 9 draws 33 mA; it feeds a panel LED only.\n"
            "No dial: UOS has six buttons. GPIO 16, 23, 24 go to J7.", (g(14), g(106)))


def serial(s: Schematic) -> None:
    s.frame("Serial console J6", (g(156), g(12)), (g(224), g(70)))
    j6 = s.symbol("Connector_Generic:Conn_01x06", "J6", "Serial 3.3 V", (g(208), g(34)),
                  footprint=HDR.format("1x06"), ref_at=(g(2), g(-7)), value_at=(g(2), g(10)),
                  description="FTDI-style 6-pin serial header: 1 GND, 2 CTS, 3 VCC open, 4 TXD in, 5 RXD out, 6 RTS")
    sideways(s, j6, "1", "GND")
    for pin in ("2", "3", "6"):
        s.no_connect(j6, pin)
    s.global_label(j6, "4", "UART_RX", shape="output", stub=g(3))
    s.global_label(j6, "5", "UART_TX", shape="input", stub=g(3))
    s.text("3.3 V ONLY", (g(160), g(52)), size=2.5, bold=True)
    note(s, "FTDI cable order. Pin 4 is the cable TXD,\n"
            "into the Pi RXD. Pin 5 is the cable RXD.\n"
            "Pin 3 (VCC) stays open: a 5 V cable cannot\n"
            "back-feed the Pi. 115200 8N1.", (g(160), g(66)))


def free_pins(s: Schematic) -> None:
    s.frame("Free Pi pins J7, each beside a ground", (g(10), g(116)), (g(136), g(156)))
    j7 = s.symbol("Connector_Generic:Conn_02x09_Odd_Even", "J7", "Free pins", (g(60), g(136)),
                  footprint=HDR.format("2x09"), ref_at=(g(-1), g(-11)), value_at=(g(-2), g(13)),
                  description="Free-pin header, 2x9, 2.54 mm: odd pins GPIO, even pins GND")
    for pin, net in FREE:
        s.global_label(j7, str(pin), net, shape="passive", stub=g(3))
    for pin in range(2, 19, 2):
        sideways(s, j7, str(pin), "GND")
    s.text("3.3 V LOGIC, NO LOAD", (g(84), g(126)), size=2.0, bold=True)
    note(s, "No resistors. A relay module input or a\n"
            "logic input only, never a coil or a lamp.\n"
            "At reset GPIO 4 has a pull-up and\n"
            "GPIO 16, 23, 24 a pull-down (typical, check).\n"
            "An active-high module on GPIO 4 can switch\n"
            "on during boot: use it for active-low ones.", (g(84), g(146)))


def draw(s: Schematic) -> None:
    buttons(s)
    serial(s)
    free_pins(s)
