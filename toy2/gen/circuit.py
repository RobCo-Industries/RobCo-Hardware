"""Toy 2: a two-sheet schematic that tests the hierarchy tools.

The Controller sheet holds a 4-pin header, a PCA9554 expander and a DS1338
clock on one I2C bus. The Outputs sheet holds eight LED channels, the same
circuit eight times, driven by the expander through global labels X0.0 to
X0.7. Toy 2 is a test bed for the tools, not a real board. It has no board
file.

Usage: python3 toy2/gen/circuit.py [output folder]
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

from common import g  # noqa: E402
from project import write_project  # noqa: E402
from sch import Hierarchy, Schematic  # noqa: E402

PROJECT = "toy2"
CHANNELS = 8

FOOTPRINTS = {
    "J1": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "U1": "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
    "U2": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "C": "Capacitor_SMD:C_0805_2012Metric",
    "R": "Resistor_SMD:R_0805_2012Metric",
    "LED": "LED_SMD:LED_0805_2012Metric",
}


def controller(s: Schematic) -> None:
    # Header block, top left.
    s.frame("Header", (g(16), g(20)), (g(60), g(56)))
    j1 = s.symbol("Connector_Generic:Conn_01x04", "J1", "I2C header", (g(32), g(36)),
                  footprint=FOOTPRINTS["J1"], ref_at=(g(-2), g(-4)), value_at=(g(-2), g(7)),
                  description="4-pin header: +3V3, GND, SDA, SCL")
    s.power(j1, "1", "+3V3", stub=g(3))
    s.power(j1, "2", "GND", stub=g(8), then=[(0, g(10))])
    s.global_label(j1, "3", "I2C_SDA", shape="bidirectional", stub=g(3))
    s.global_label(j1, "4", "I2C_SCL", shape="bidirectional", stub=g(3))
    s.power_flag("+3V3", (g(44), g(26)))
    s.power_flag("GND", (g(52), g(34)))

    # Expander block, centre.
    s.frame("I2C expander, address 0x20", (g(72), g(20)), (g(160), g(66)))
    u1 = s.symbol("RobCo:PCA9554", "U1", "PCA9554", (g(112), g(48)), footprint=FOOTPRINTS["U1"],
                  ref_at=(g(3), g(-11)), value_at=(g(3), g(-9)),
                  description="I2C expander, outputs X0.0 to X0.7")
    s.global_label(u1, "14", "I2C_SCL", shape="bidirectional", stub=g(4))
    s.global_label(u1, "15", "I2C_SDA", shape="bidirectional", stub=g(4))
    s.no_connect(u1, "13")
    # A0, A1 and A2 to GND through one vertical wire: two T joins need dots.
    a0, a1, a2 = u1.pin("1"), u1.pin("2"), u1.pin("3")
    x = a0[0] - g(4)
    bottom = (x, a2[1] + g(4))
    s.wire(a0, (x, a0[1]), bottom)
    s.wire(a1, (x, a1[1]))
    s.wire(a2, (x, a2[1]))
    s.junction((x, a1[1]))
    s.junction((x, a2[1]))
    s.power_symbol("GND", bottom)
    s.power(u1, "16", "+3V3", stub=g(2))
    s.power(u1, "8", "GND", stub=g(2))
    for i, pin in enumerate(["4", "5", "6", "7", "9", "10", "11", "12"]):
        s.global_label(u1, pin, f"X0.{i}", shape="output", stub=g(4))
    c1 = s.symbol("Device:C", "C1", "100n", (g(132), g(28)), footprint=FOOTPRINTS["C"],
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)), description="U1 decoupling")
    s.power(c1, "1", "+3V3", stub=g(1))
    s.power(c1, "2", "GND", stub=g(1))

    # Clock block, mirrored so its bus pins face right, towards the labels.
    s.frame("Clock, address 0x68", (g(16), g(90)), (g(100), g(132)))
    u2 = s.symbol("RobCo:DS1338", "U2", "DS1338", (g(52), g(112)), mirror="y",
                  footprint=FOOTPRINTS["U2"], ref_at=(g(11), g(-11)), value_at=(g(11), g(-9)),
                  description="Real-time clock")
    s.global_label(u2, "5", "I2C_SDA", shape="bidirectional", stub=g(4))
    s.global_label(u2, "6", "I2C_SCL", shape="bidirectional", stub=g(4))
    s.no_connect(u2, "1")
    s.no_connect(u2, "2")
    s.no_connect(u2, "7")
    s.power(u2, "8", "+3V3", stub=g(2))
    s.power(u2, "4", "GND", stub=g(2))
    s.power(u2, "3", "GND", stub=g(2), then=[(g(-6), 0), (0, g(20))])
    s.text("Toy only: no crystal on X1 and X2, VBAT tied to GND.", (g(18), g(130)))


def outputs(s: Schematic) -> None:
    top = g(36)
    step = g(10)
    left = g(40)
    bus = left + g(26)
    s.frame("Eight output channels, one per expander line", (g(24), g(20)), (g(80), top + CHANNELS * step + g(6)))

    def channel(i: int, at) -> None:
        x, y = at
        r = s.symbol("Device:R", f"R1{i}", "1k", (x + g(8), y), rot=90, footprint=FOOTPRINTS["R"],
                     ref_at=(g(-2), g(-2)), value_at=(g(-1), g(2)),
                     description=f"LED current limit, channel {i}")
        d = s.symbol("Device:LED", f"D1{i}", "Red", (x + g(16), y), rot=180, footprint=FOOTPRINTS["LED"],
                     ref_at=(g(-2), g(-3)), value_at=(g(-2), g(3)),
                     description=f"Channel {i} indicator")
        s.global_label_at(f"X0.{i}", (x, y), "left", shape="input")
        s.wire((x, y), r.pin("1"))
        s.wire(r.pin("2"), d.pin("2"))
        s.wire(d.pin("1"), (bus, y))
        if 0 < i:
            s.junction((bus, y))

    s.repeat(CHANNELS, (left, top), (0, step), channel)
    end = (bus, top + CHANNELS * step)
    s.wire((bus, top), end)
    s.power_symbol("GND", end)
    s.text("Channel i: X0.i drives R1i and D1i. The same circuit eight times.", (g(26), top - g(6)))


def build() -> Hierarchy:
    h = Hierarchy(PROJECT, board="Toy 2: hierarchy test", date="2026-11-23", rev="0.1",
                  comments=["Generated by toy2/gen/circuit.py. Do not edit by hand."])
    controller(h.sheet("Controller", "controller.kicad_sch", (g(40), g(40)), (g(40), g(16)),
                       notes="Header J1, expander U1 at 0x20,\nclock U2 at 0x68."))
    outputs(h.sheet("Outputs", "outputs.kicad_sch", (g(110), g(40)), (g(40), g(16)),
                    notes="Eight LED channels\non X0.0 to X0.7."))
    h.root.text("Toy 2 tests the hierarchy tools. The Controller sheet drives the Outputs sheet\n"
                "through the global labels X0.0 to X0.7. Rails use power symbols.", (g(40), g(30)))
    return h


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "kicad")
    h = build()
    h.write(out)
    fp_libs = [fp.split(":", 1)[0] for fp in FOOTPRINTS.values()]
    write_project(out, PROJECT, h.stock_libs(), fp_libs)


if __name__ == "__main__":
    main()
