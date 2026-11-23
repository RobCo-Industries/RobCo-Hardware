"""Sheet: the eight switched outputs. U4 ULN2803A, RN1, the status LEDs and J3.

Spec sections 4.3 and 5.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import C_DISC, CP_8MM, LED_3MM, TERM_10, decoupling, note

CHANNELS = 8
# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-2)), value_at=(g(5), g(3)))


def driver(s: Schematic) -> None:
    s.frame("Driver U4 and its input pull-downs RN1", (g(10), g(12)), (g(118), g(100)))
    # RN1 turned so its eight resistor pins face right, one per driver input row.
    rn1 = s.symbol("Device:R_Network08", "RN1", "10k x 8 bussed", (g(26), g(46)), rot=90, mirror="x",
                   footprint="Resistor_THT:R_Array_SIP9", ref_at=(g(2), g(-13)), value_at=(g(8), g(-11)),
                   description="Pull-down on each driver input: 10 kOhm x 8 bussed, SIP-9, pin 1 common to GND")
    s.power(rn1, "1", "GND", stub=g(2), then=[(0, g(20))])
    u4 = s.symbol("Transistor_Array:ULN2803A", "U4", "ULN2803A", (g(80), g(46)),
                  footprint="Package_DIP:DIP-18_W7.62mm", ref_at=(g(2), g(-12)), value_at=(g(2), g(-10)),
                  description="Eight Darlington low-side drivers with flyback diodes to COM, DIP-18")
    for i in range(CHANNELS):
        s.global_label(rn1, str(i + 2), f"X0.{i}", shape="input", stub=g(2))
        s.global_label(u4, str(i + 1), f"X0.{i}", shape="input", stub=g(3))
        s.label(u4, str(18 - i), f"OUT{i}", stub=g(3))
    s.power(u4, "9", "GND", stub=g(2))
    s.power(u4, "10", "V_SW", stub=g(2), then=[(0, g(-6))])
    decoupling(s, "C8", "100n", (g(104), g(30)), "V_SW", fp=C_DISC, desc="U4 COM decoupling, COM is V_SW")
    note(s, "RN1 holds every driver input low. The power-on safety of the board\n"
            "rests on it: at reset the PCA9554 pins are inputs with a 100 kOhm\n"
            "pull-up (typical, check). Against 10 kOhm that gives 0.30 V, well\n"
            "below the 1.4 V a ULN2803A input needs to conduct. The load stays off.\n"
            "Keep RN1 next to U4.", (g(14), g(84)))
    note(s, "COM (pin 10) goes to V_SW, the rail of the loads: the internal\n"
            "diodes then clamp the flyback of each coil. Spec section 4.3.", (g(14), g(96)))


def channels(s: Schematic) -> None:
    s.frame("Status LEDs, one per channel", (g(124), g(12)), (g(176), g(100)))
    top, step = g(28), g(8)
    x0, bus = g(128), g(168)

    def channel(i: int, at) -> None:
        x, y = at
        led = s.symbol("Device:LED", f"LED{i}", "Red", (x + g(10), y), footprint=LED_3MM,
                       ref_at=(g(-2), g(-2)), value_at=(g(-2), g(3)),
                       description=f"Channel {i} status, 3 mm red. Lit while the channel conducts.")
        r = s.symbol("Device:R", f"R1{i}", "1k5/4k7/10k", (x + g(26), y), rot=90,
                     footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                     description=f"LED{i} current, value by load supply", **H_FIELDS)
        s.label_at(f"OUT{i}", (x, y))
        s.wire((x, y), led.pin("1"))
        s.wire(led.pin("2"), r.pin("1"))
        s.wire(r.pin("2"), (bus, y))
        if i > 0:
            s.junction((bus, y))

    s.repeat(CHANNELS, (x0, top), (0, step), channel)
    s.wire((bus, top - g(6)), (bus, top + (CHANNELS - 1) * step))
    s.junction((bus, top))
    s.power_symbol("V_SW", (bus, top - g(6)))
    note(s, "Each LED sits from V_SW to OUTn and lights\n"
            "while the channel conducts, load or not.", (g(128), g(96)))


def terminals(s: Schematic) -> None:
    s.frame("Output terminals J3", (g(182), g(12)), (g(224), g(100)))
    j3 = s.symbol("Connector:Screw_Terminal_01x10", "J3", "Outputs", (g(212), g(40)), footprint=TERM_10,
                  ref_at=(g(-2), g(-11)), value_at=(g(-2), g(13)),
                  description="Output terminals, 10 ways, 3.5 mm: OUT0 to OUT7, then V_SW, V_SW")
    for i in range(CHANNELS):
        s.label(j3, str(i + 1), f"OUT{i}", stub=g(3))
    for pin in ("9", "10"):
        end, _ = s._stub(j3, pin, g(3))
        s.power_symbol("V_SW", end, rot=90, value_at=(-g(8), 0))
    decoupling(s, "C9", "100u 35V", (g(200), g(70)), "V_SW", fp=CP_8MM, polar=True,
               desc="V_SW reservoir near J3")
    note(s, "Silkscreen: X0.0 to X0.7,\n"
            "then +V, +V. A load goes\n"
            "between +V and its OUTn.\n"
            "LOW VOLTAGE ONLY. NO MAINS.", (g(186), g(96)))


def limits(s: Schematic) -> None:
    s.frame("Limits and LED resistors", (g(10), g(108)), (g(136), g(156)))
    note(s, "Design limits (spec 4.3): 200 mA per channel, 900 mA in total.\n"
            "The PCA9554 drives U4 from 3.3 V: at 200 mA the input needs 2.4 V,\n"
            "the expander gives 2.9 V or more (typical, check).\n"
            "Package: 8 x 0.2 A x 1.1 V = 1.76 W is above the 1.5 W rating.\n"
            "1 W derated budget / 1.1 V = 0.9 A in total. F1 holds 1.1 A.\n"
            "Two channels driven together can share one load.", (g(14), g(128)))
    note(s, "R10 to R17 and R24, by load supply, LED at 2 mA, 2.0 V:\n"
            "5 V: 1.5 kOhm.  12 V: 4.7 kOhm.  24 V: 10 kOhm.\n"
            "Fit the value for the supply used and mark it on the board.", (g(14), g(140)))
    note(s, "Door strikes above 200 mA: an external relay or two paralleled channels.", (g(14), g(150)))


def draw(s: Schematic) -> None:
    driver(s)
    channels(s)
    terminals(s)
    limits(s)
