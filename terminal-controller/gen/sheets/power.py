"""Sheet: the load supply, its protection, the arm switch and the Pi rails.

Spec sections 4.1, 4.4, 4.8 (F2) and 5.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import (FUSE_1A1, FUSE_200MA, C_DISC, CP_5MM, CP_8MM, DO35, DO201, HDR, LED_3MM, TERM_2, TP_LOOP,
                          TP_LOOP_BIG, cap, decoupling, note, res, testpoint)

# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor below is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-2)), value_at=(g(3), g(3)))


def supply(s: Schematic) -> None:
    s.frame("Load supply input and protection", (g(10), g(12)), (g(150), g(66)))
    y = g(36)  # the V_IN, V_FUSED, V_PROT line
    j2 = s.symbol("Connector:Screw_Terminal_01x02", "J2", "LOAD + 5-24 V DC", (g(18), g(24)), mirror="y",
                  footprint=TERM_2, ref_at=(g(2), g(-3)), value_at=(g(14), g(6)),
                  description="Load supply terminal, 3.5 mm. Pin 1 V_EXT, pin 2 GND.")
    jp1 = s.symbol("Jumper:Jumper_3_Open", "JP1", "EXT / PI5V", (g(38), g(24)), footprint=HDR.format("1x03"),
                   ref_at=(g(-3), g(-4)), value_at=(g(-9), g(-6)),
                   description="Load supply source. Shunt 1-2: terminal J2. Shunt 2-3: Pi 5 V.")
    s.wire(j2.pin("1"), jp1.pin("1"))
    s.label_at("V_EXT", (g(26), g(24)))
    s.power(j2, "2", "GND", stub=g(2), then=[(0, g(4))])
    s.power(jp1, "3", "+5V", stub=g(4), then=[(0, g(-4))])
    f1 = s.symbol("Device:Polyfuse", "F1", "1.1 A hold, 60 V", (g(54), y), rot=90, footprint=FUSE_1A1,
                  description="Radial PPTC fuse, 1.1 A hold, trip about 2.2 A, 60 V or more", **H_FIELDS)
    pin2 = jp1.pin("2")
    s.wire(pin2, (pin2[0], y), f1.pin("1"))
    s.label_at("V_IN", (g(44), y))
    d1 = s.symbol("Device:D_Schottky", "D1", "SB360", (g(70), y), rot=180, footprint=DO201,
                  ref_at=(g(-3), g(-3)), value_at=(g(-3), g(3)),
                  description="Reverse polarity diode, Schottky 3 A 60 V, SB360 class, DO-201AD. "
                              "Anode V_FUSED, cathode V_PROT.")
    s.wire(f1.pin("2"), d1.pin("2"))
    s.label_at("V_FUSED", (g(59), y))
    # V_PROT line: D1 cathode to the right, the clamp and the reservoir hang below.
    xe = g(130)
    s.wire(d1.pin("1"), (xe, y))
    s.wire((g(82), y), (g(82), y - g(6)))
    s.junction((g(82), y))
    s.power_symbol("V_PROT", (g(82), y - g(6)))
    d2 = s.symbol("RobCo:D_TVS_Unidir", "D2", "TVS, 26 V", (g(92), y + g(8)), rot=270,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)),
                  footprint="Diode_THT:D_DO-15_P12.70mm_Horizontal",
                  description="TVS, 600 W, unidirectional, about 26 V standoff, DO-15. Cathode V_PROT.")
    c1 = cap(s, "C1", "100u 50V", (g(108), y + g(8)), fp=CP_8MM, polar=True, desc="V_PROT reservoir")
    c2 = cap(s, "C2", "100n", (g(120), y + g(8)), desc="V_PROT decoupling")
    tp6 = testpoint(s, "TP6", "V_PROT", (g(130), y - g(6)))
    s.wire(tp6.pin("1"), (xe, y))
    for part, pin in ((d2, "1"), (c1, "1"), (c2, "1")):
        top = part.pin(pin)
        s.wire((top[0], y), top)
        s.junction((top[0], y))
    for part, pin in ((d2, "2"), (c1, "2"), (c2, "2")):
        s.power(part, pin, "GND", stub=g(1))
    s.power_flag("V_PROT", (g(140), y - g(6)))
    note(s, "LOW VOLTAGE ONLY: 5 V to 24 V DC. No mains on any terminal.\n"
            "JP1 1-2: J2 feeds the loads. JP1 2-3: the Pi 5 V feeds them,\n"
            "300 mA at most (assumed). Only one source reaches V_IN.\n"
            "D1 blocks a reversed supply. D2 clamps spikes on V_PROT;\n"
            "its 26 V standoff stays above 24 V + 5 % = 25.2 V. It clamps\n"
            "near 42 V at its rated pulse (to verify): D1, D4, Q1,\n"
            "F1 and F2 are rated 60 V, C1 and C9 50 V.\n"
            "F1 limits a short on V_SW. Footprints of F1, F2: none in the\n"
            "stock library, to add in the board step.", (g(14), g(63)))


def sensor_supply(s: Schematic) -> None:
    s.frame("Sensor supply", (g(156), g(12)), (g(224), g(52)))
    f2 = s.symbol("Device:Polyfuse", "F2", "200 mA hold, 60 V", (g(184), g(28)), rot=90, footprint=FUSE_200MA,
                  description="Radial PPTC fuse, hold 200 mA or more, trip 400 mA or less, 60 V or more, "
                              "example Bourns MF-R020", **H_FIELDS)
    s.power(f2, "1", "V_PROT", stub=g(4), then=[(0, g(-2))])
    s.power(f2, "2", "+V_S", stub=g(4), then=[(0, g(-2))])
    s.power_flag("+V_S", (g(214), g(30)))
    note(s, "+V_S feeds sensors and dry contacts on J4.\n"
            "It stays live when the arm switch is off.\n"
            "F2 limits a short from +V_S to IN_COM.", (g(160), g(49)))


def arm_switch(s: Schematic) -> None:
    s.frame("Arm switch: the load rail V_SW is live only while ARM is high", (g(10), g(74)), (g(136), g(154)))
    x, y = g(50), g(90)
    q1 = s.symbol("RobCo:Q_PMOS_GDS", "Q1", "P-channel MOSFET, 60 V", (x, y), rot=90, mirror="y",
                  footprint="Package_TO_SOT_THT:TO-220-3_Vertical", ref_at=(g(2), g(5)), value_at=(g(2), g(7)),
                  description="P-channel MOSFET, 60 V or more, |Vgs(th)| 2.5 V or less, Vgs max 20 V, "
                              "Rds(on) 0.1 Ohm or less specified at -4.5 V or lower drive. "
                              "Source V_PROT, drain V_SW.")
    src, drn, gate = q1.pin("3"), q1.pin("2"), q1.pin("1")
    ys = src[1]
    xs = x - g(28)
    s.wire(src, (xs, ys), (xs, ys - g(4)))
    s.power_symbol("V_PROT", (xs, ys - g(4)))
    # R20 and D3 from V_PROT to ARM_G, side by side.
    r20 = res(s, "R20", "100k", (x - g(20), ys + g(6)), desc="Holds Q1 off: gate to source")
    d3 = s.symbol("Device:D_Zener", "D3", "12 V, 500 mW", (x - g(12), ys + g(6)), rot=270, footprint=DO35,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)),
                  description="Gate clamp, 12 V zener, DO-35. Cathode V_PROT, anode ARM_G.")
    yg = ys + g(12)
    for part, pin in ((r20, "1"), (d3, "1")):
        p = part.pin(pin)
        s.wire((p[0], ys), p)
        s.junction((p[0], ys))
    for part, pin in ((r20, "2"), (d3, "2")):
        p = part.pin(pin)
        s.wire(p, (p[0], yg))
    s.wire((x - g(20), yg), (x, yg))
    s.junction((x - g(12), yg))
    s.wire(gate, (x, yg))
    s.label_at("ARM_G", (x - g(10), yg))
    # C13, gate to drain, not fitted: slows the turn-on if arming dips the supply.
    xc = x + g(23)
    c13 = cap(s, "C13", "47n", (xc, ys + g(6)), dnp=True,
              desc="Q1 gate to drain, not fitted. 10 nF to 47 nF, 50 V, slows the turn-on. Spec 4.4.")
    s.wire((xc, ys), c13.pin("1"))
    s.junction((xc, ys))
    s.wire(c13.pin("2"), (xc, yg), (x, yg))
    r21 = res(s, "R21", "1k", (x, yg + g(6)), desc="Q1 gate to Q2 collector")
    s.wire((x, yg), r21.pin("1"))
    s.junction((x, yg))
    q2 = s.symbol("Transistor_BJT:Q_NPN_EBC", "Q2", "2N5551", (x - g(2), yg + g(16)),
                  footprint="Package_TO_SOT_THT:TO-92_Inline", ref_at=(g(4), g(-1)), value_at=(g(4), g(1)),
                  description="NPN, 160 V, TO-92. Pulls ARM_G down when ARM is high.")
    s.wire(r21.pin("2"), q2.pin("3"))
    s.power(q2, "1", "GND", stub=g(1))
    b = q2.pin("2")
    r22 = res(s, "R22", "4k7", (b[0] - g(12), b[1]), horizontal=True, desc="ARM to Q2 base", **H_FIELDS)
    s.wire(r22.pin("2"), b)
    s.global_label(r22, "1", "ARM", shape="input", stub=g(3))
    r23 = res(s, "R23", "100k", (b[0] - g(4), b[1] + g(6)), desc="Holds Q2 off while ARM floats")
    s.wire((b[0] - g(4), b[1]), r23.pin("1"))
    s.junction((b[0] - g(4), b[1]))
    s.power(r23, "2", "GND", stub=g(1))
    # Drain side: the switched rail V_SW.
    xe = x + g(52)  # TP7 ends the line
    s.wire(drn, (xe, ys))
    # JP8 across Q1, above it.
    jp8 = s.symbol("Jumper:Jumper_2_Open", "JP8", "ARM BYPASS, TEST ONLY", (x, ys - g(8)),
                   footprint=HDR.format("1x02"), ref_at=(g(-3), g(-3)), value_at=(g(-8), g(-5)),
                   description="Shorts Q1 source to drain. No shunt fitted. Test only.")
    # JP8 pads sit right above the source and drain pins.
    s.wire((src[0], ys), jp8.pin("1"))
    s.wire((drn[0], ys), jp8.pin("2"))
    s.wire((x + g(16), ys), (x + g(16), ys - g(6)))
    s.junction((x + g(16), ys))
    s.power_symbol("V_SW", (x + g(16), ys - g(6)))
    d4 = s.symbol("Device:D_Schottky", "D4", "SB360", (x + g(30), ys + g(8)), rot=270, footprint=DO201,
                  ref_at=(g(2), g(-1)), value_at=(g(2), g(1)),
                  description="Coil current path when Q1 opens. Schottky 3 A 60 V, SB360 class. "
                              "Anode GND, cathode V_SW.")
    r24 = res(s, "R24", "1k5/4k7/10k", (x + g(40), ys + g(6)), desc="LED8 current, value by load supply as R10")
    led8 = s.symbol("Device:LED", "LED8", "Green", (x + g(40), ys + g(16)), rot=90, footprint=LED_3MM,
                    ref_at=(g(-2), g(-1)), value_at=(g(-2), g(1)), description="Armed indicator, 3 mm green")
    s.wire(r24.pin("2"), led8.pin("2"))
    s.power(led8, "1", "GND", stub=g(1))
    tp7 = testpoint(s, "TP7", "V_SW", (xe, ys - g(6)))
    s.wire(tp7.pin("1"), (xe, ys))
    for part, pin in ((d4, "1"), (r24, "1")):
        p = part.pin(pin)
        s.wire((p[0], ys), p)
        s.junction((p[0], ys))
    s.power(d4, "2", "GND", stub=g(1))
    s.power_flag("V_SW", (xe + g(10), ys - g(6)))
    note(s, "ARM high: Q2 on, ARM_G pulled down, Q1 on, V_SW = V_PROT.\n"
            "ARM low or floating: R23 holds Q2 off, R20 holds Q1 off, V_SW dead.\n"
            "A Pi reset returns GPIO 25 to an input with a pull-down: the loads\n"
            "lose power through every reboot. Power-on safety: spec section 5.\n"
            "D3 clamps Vgs: at 24 V the R20/R21 divider gives -23 V, D3 holds -12 V.\n"
            "At a 5 V supply Vgs is only about -4.0 V: spec section 4.4.\n"
            "C13 not fitted: 10 nF to 47 nF slows Q1 turn-on if arming dips +5V.\n"
            "D4: when Q1 opens with coils energised, their current flows through D4.\n"
            "JP8: no shunt. Fitted, it bypasses the arm switch. Test only.", (x + g(10), g(134)))
    note(s, "To verify: Q1 pin order assumed for TO-220 as\n"
            "1 gate, 2 drain, 3 source (IRF9540N style).\n"
            "Q2 2N5551, TO-92: 1 emitter, 2 base, 3 collector.\n"
            "Check both against the parts bought.", (x + g(10), g(150)))


def pi_rails(s: Schematic) -> None:
    s.frame("Pi rails and test points", (g(156), g(64)), (g(224), g(118)))
    decoupling(s, "C3", "10u 10V", (g(162), g(80)), "+3V3", fp=C_DISC, desc="+3V3 bulk, near U1. Ceramic or tantalum.")
    decoupling(s, "C4", "47u 10V", (g(174), g(80)), "+5V", fp=CP_5MM, polar=True, desc="+5V bulk, near M1")
    for k, (ref, net) in enumerate((("TP1", "+3V3"), ("TP2", "+5V"), ("TP3", "GND"))):
        # Rail test points hang below their rail, the ground loop sits above GND.
        up = net != "GND"
        tp = testpoint(s, ref, net, (g(188 + 11 * k), g(84) if up else g(76)),
                       fp=TP_LOOP if up else TP_LOOP_BIG, rot=180 if up else 0)
        s.power(tp, "1", net, stub=g(2))
    note(s, "The board has no regulator. +3V3 and +5V\n"
            "come from the Pi. TP3 is a loop\nfor a probe clip.", (g(160), g(114)))


def draw(s: Schematic) -> None:
    supply(s)
    sensor_supply(s)
    arm_switch(s)
    pi_rails(s)
