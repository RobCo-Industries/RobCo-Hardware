"""Sheet: the serial console J4 and the test points on the rails and the I2C bus.

Spec sections 4.9 and 4.10. TP6, TP7 and TP8 sit on their blocks' sheets.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import HDR, TP_LOOP, TP_LOOP_BIG, note, sideways, testpoint


def console(s: Schematic) -> None:
    s.frame("Serial console J4", (g(10), g(12)), (g(80), g(70)))
    j4 = s.symbol("Connector_Generic:Conn_01x06", "J4", "Serial 3.3 V", (g(62), g(34)),
                  footprint=HDR.format("1x06"), ref_at=(g(2), g(-7)), value_at=(g(2), g(10)),
                  description="FTDI-style 6-pin serial header: 1 GND, 2 CTS, 3 VCC open, 4 TXD in, 5 RXD out, 6 RTS")
    sideways(s, j4, "1", "GND")
    for pin in ("2", "3", "6"):
        s.no_connect(j4, pin)
    s.global_label(j4, "4", "UART_RX", shape="output", stub=g(3))
    s.global_label(j4, "5", "UART_TX", shape="input", stub=g(3))
    s.text("3.3 V ONLY", (g(14), g(52)), size=2.5, bold=True)
    note(s, "FTDI cable order. Pin 4 is the cable TXD,\n"
            "into the Pi RXD. Pin 5 is the cable RXD.\n"
            "Pin 3, VCC, stays open: a 5 V cable cannot\n"
            "back-feed the Pi. 115200 8N1.\n"
            "Silkscreen: 3.3 V ONLY, GND at pin 1, 115200 8N1.", (g(14), g(66)))


def test_points(s: Schematic) -> None:
    s.frame("Test points", (g(86), g(12)), (g(176), g(70)))
    for k, (ref, net) in enumerate((("TP1", "+3V3"), ("TP2", "+5V"), ("TP3", "GND"))):
        # Rail test points hang below their rail, the ground loop sits above GND.
        up = net != "GND"
        tp = testpoint(s, ref, net, (g(94 + 14 * k), g(36) if up else g(28)),
                       fp=TP_LOOP if up else TP_LOOP_BIG, rot=180 if up else 0)
        s.power(tp, "1", net, stub=g(2))
    for k, (ref, net) in enumerate((("TP4", "I2C_SDA"), ("TP5", "I2C_SCL"))):
        tp = testpoint(s, ref, net, (g(140 + 18 * k), g(28)))
        s.global_label(tp, "1", net, shape="passive", stub=g(2))
    note(s, "The board has no regulator. +3V3 comes\n"
            "from the Pi, +5V from the Pi or J3.\n"
            "TP3 is a loop for a probe clip.", (g(90), g(66)))


def draw(s: Schematic) -> None:
    console(s)
    test_points(s)
