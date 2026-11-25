"""Sheet: PWM audio filter, source jumper, volume trimmer, amplifier module, speaker.

Spec section 4.5.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import C_FILM, CP_5MM, HDR, PAM8302A_MODULE, TERM_2, decoupling, note, res

# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-2)), value_at=(g(3), g(3)))


def sources(s: Schematic) -> None:
    s.frame("Sources: GPIO 18 PWM filter or the Pi's jack", (g(10), g(12)), (g(104), g(96)))
    # PWM path, lower row.
    yp = g(62)
    r30 = res(s, "R30", "270", (g(40), yp), horizontal=True, desc="PWM low-pass, with C30: 17.9 kHz", **H_FIELDS)
    s.global_label_at("AUDIO_PWM", (g(30), yp), "left", shape="input")
    s.wire((g(30), yp), r30.pin("1"))
    c30 = s.symbol("Device:C", "C30", "33n film", (g(56), yp + g(6)), footprint=C_FILM,
                   ref_at=(g(2), g(-1)), value_at=(g(2), g(1)), description="PWM low-pass, film or C0G")
    s.power(c30, "2", "GND", stub=g(1))
    s.wire(r30.pin("2"), (g(90), yp))
    s.wire(c30.pin("1"), (g(56), yp))
    s.junction((g(56), yp))
    s.label_at("AUD_F", (g(62), yp))
    # Jack path, upper rows.
    j10 = s.symbol("Connector_Audio:AudioJack3", "J10", "3.5 mm jack", (g(20), g(36)), mirror="x",
                   footprint="Connector_Audio:Jack_3.5mm_CUI_SJ1-3513N_Horizontal",
                   ref_at=(g(-8), g(-8)), value_at=(g(-8), g(-6)),
                   description="Audio in from the Pi's jack (Pi 1 to 3). Tip and ring mixed to mono.")
    t, r, sl = j10.pin("T"), j10.pin("R"), j10.pin("S")
    r31 = res(s, "R31", "1k", (g(38), g(30)), horizontal=True, desc="Mixes tip into mono", **H_FIELDS)
    r32 = res(s, "R32", "1k", (g(38), g(42)), horizontal=True, desc="Mixes ring into mono", **H_FIELDS)
    s.wire(t, (t[0] + g(2), t[1]), (t[0] + g(2), g(30)), r31.pin("1"))
    s.wire(r, (r[0] + g(4), r[1]), (r[0] + g(4), g(42)), r32.pin("1"))
    s.power(j10, "S", "GND", stub=g(1), then=[(0, g(8))])
    xj = g(50)
    s.wire(r31.pin("2"), (xj, g(30)), (xj, g(42)), r32.pin("2"))
    s.junction((xj, g(36)))
    s.wire((xj, g(36)), (g(90), g(36)))
    s.label_at("AUD_J", (g(62), g(36)))
    note(s, "R30 and C30: 1 / (2 pi x 270 x 33 nF) = 17.9 kHz,\n"
            "the low-pass of audio.md. GPIO 18 at ALT5 is the\n"
            "PWM pin of the Pi Zero. A Pi 1 to 3 has PWM only on\n"
            "its analogue jack: a short cable brings it to J10.", (g(14), g(92)))


def select(s: Schematic) -> None:
    jp9 = s.symbol("Jumper:Jumper_3_Open", "JP9", "GPIO18 / JACK", (g(90), g(50)), rot=90,
                   footprint=HDR.format("1x03"), ref_at=(g(-2), g(-2)), value_at=(g(-2), g(2)),
                   description="Audio source. Shunt 1-2: GPIO 18 filter. Shunt 2-3: the jack J10.")
    s.wire((g(90), g(62)), jp9.pin("1"))
    s.wire((g(90), g(36)), jp9.pin("3"))
    c31 = s.symbol("Device:C_Polarized", "C31", "10u 16V", (g(112), g(50)), rot=90, footprint=CP_5MM,
                   description="DC block, + side at AUD_SEL", **H_FIELDS)
    s.wire(jp9.pin("2"), c31.pin("1"))
    s.label_at("AUD_SEL", (g(96), g(50)))
    rv1 = s.symbol("Device:R_Potentiometer_Trim", "RV1", "10k trimmer", (g(128), g(56)),
                   footprint="Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical",
                   ref_at=(g(-8), g(4)), value_at=(g(-8), g(6)),
                   description="Volume, 10 kOhm trimmer, log taper if available")
    s.wire(c31.pin("2"), (g(128), g(50)), rv1.pin("1"))
    s.label_at("AUD_DC", (g(118), g(50)))
    s.power(rv1, "3", "GND", stub=g(1))
    return rv1


def amplifier(s: Schematic, rv1) -> None:
    s.frame("Level, amplifier and speaker", (g(107), g(12)), (g(224), g(96)))
    m1 = s.symbol("RobCo:PAM8302A_Module", "M1", "PAM8302A", (g(164), g(56)), footprint=PAM8302A_MODULE,
                  ref_at=(g(-2), g(-11)), value_at=(g(-2), g(-9)),
                  description="PAM8302A class-D mono amplifier breakout. Inputs on a 5-pin 2.54 mm row, outputs on the opposite edge. Pinout and geometry from the module bought.")
    wiper = rv1.pin("2")
    s.wire(wiper, m1.pin("4"))
    s.label_at("AUD_IN", (wiper[0] + g(4), wiper[1]))
    for pin, net in (("1", "+5V"), ("2", "GND"), ("5", "GND")):
        end, _ = s._stub(m1, pin, g(3))
        s.power_symbol(net, end, rot=90, value_at=(-g(4 + len(net)), 0))
    s.no_connect(m1, "3")
    s.label(m1, "6", "SPK+", stub=g(3))
    s.label(m1, "7", "SPK-", stub=g(3))
    decoupling(s, "C32", "100n", (g(184), g(32)), "+5V", desc="M1 VIN decoupling")
    j8 = s.symbol("Connector:Screw_Terminal_01x02", "J8", "SPK 4-8 Ohm", (g(212), g(58)), footprint=TERM_2,
                  ref_at=(g(-2), g(-4)), value_at=(g(-6), g(4)),
                  description="Speaker terminal. Bridge output: neither side is ground.")
    s.label(j8, "1", "SPK+", stub=g(3))
    s.label(j8, "2", "SPK-", stub=g(3))
    note(s, "M1 drives the speaker in bridge mode: never tie\n"
            "SPK+ or SPK- to GND. 4 to 8 Ohm speaker.\n"
            "1 W at 8 Ohm draws about 0.24 A from +5V.", (g(150), g(82)))
    note(s, "To verify: M1 pins assumed. Input row 1 VIN, 2 GND,\n"
            "3 SD, 4 A+, 5 A-. Output edge 6 OUT+, 7 OUT-.\n"
            "Footprint from memory: redraw before ordering.\n"
            "Pins at both edges carry OUT+ and OUT- to J8.\n"
            "A builder may wire the speaker to M1's terminal.\n"
            "SD open: the module pulls it high (to verify).", (g(150), g(92)))


def draw(s: Schematic) -> None:
    sources(s)
    rv1 = select(s)
    amplifier(s, rv1)
