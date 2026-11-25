"""Sheet: the PWM audio filter, the level trimmer, the amplifier module and the speaker.

Spec section 4.5.
"""

from __future__ import annotations

from common import g
from sch import Schematic

from sheets.parts import (C_FILM, CP_5MM, CP_6MM, H_FIELDS, HDR, PAM8302A_MODULE, TP_LOOP, decoupling, note, res,
                          sideways, testpoint)


def draw(s: Schematic) -> None:
    s.frame("Filter, level ceiling, amplifier and speaker", (g(10), g(12)), (g(200), g(70)))
    y = g(40)  # the filter line
    s.global_label_at("AUDIO_PWM", (g(26), y), "left", shape="input")
    r30 = res(s, "R30", "270", (g(36), y), horizontal=True, desc="PWM low-pass, with C30: 17.9 kHz")
    s.wire((g(26), y), r30.pin("1"))
    c30 = s.symbol("Device:C", "C30", "33n film", (g(46), y + g(6)), footprint=C_FILM,
                   ref_at=(g(2), g(-1)), value_at=(g(2), g(1)), description="PWM low-pass, film or C0G")
    s.power(c30, "2", "GND", stub=g(1))
    c31 = s.symbol("Device:C_Polarized", "C31", "10u 16V", (g(60), y), rot=90, footprint=CP_5MM,
                   description="DC block, + side at AUD_F. Electrolytic or film.", **H_FIELDS)
    s.wire(r30.pin("2"), c31.pin("1"))
    s.wire(c30.pin("1"), (g(46), y))
    s.junction((g(46), y))
    s.label_at("AUD_F", (g(49), y))
    r31 = res(s, "R31", "33k", (g(76), y), horizontal=True, desc="Above RV1: sets its working range")
    s.wire(c31.pin("2"), r31.pin("1"))
    s.label_at("AUD_DC", (g(65), y))
    rv1 = s.symbol("Device:R_Potentiometer_Trim", "RV1", "10k trimmer", (g(90), y + g(6)),
                   footprint="Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical",
                   ref_at=(g(-11), g(-1)), value_at=(g(-11), g(1)),
                   description="Level ceiling, 10 kOhm trimmer, through-hole. Ends AUD_T and GND, wiper AUD_IN.")
    s.wire(r31.pin("2"), (g(90), y), rv1.pin("1"))
    s.label_at("AUD_T", (g(81), y))
    s.power(rv1, "3", "GND", stub=g(1))
    m1 = s.symbol("RobCo:PAM8302A_Module", "M1", "PAM8302A", (g(128), y + g(6)), footprint=PAM8302A_MODULE,
                  ref_at=(g(-2), g(-11)), value_at=(g(-2), g(-9)),
                  description="PAM8302A class-D mono amplifier breakout. Inputs on a 5-pin 2.54 mm row, outputs on the opposite edge. Pinout and geometry from the module bought.")
    wiper = rv1.pin("2")
    s.wire(wiper, m1.pin("4"))
    s.label_at("AUD_IN", (wiper[0] + g(12), wiper[1]))
    tp6 = testpoint(s, "TP6", "AUD_IN", (g(100), wiper[1] - g(6)), fp=TP_LOOP)
    s.wire(tp6.pin("1"), (g(100), wiper[1]))
    s.junction((g(100), wiper[1]))
    for pin, net in (("1", "+5V"), ("2", "GND"), ("5", "GND")):
        sideways(s, m1, pin, net)
    s.no_connect(m1, "3")
    s.label(m1, "6", "SPK_P", stub=g(3))
    s.label(m1, "7", "SPK_N", stub=g(3))
    decoupling(s, "C32", "100n", (g(140), g(24)), "+5V", desc="M1 Vin decoupling, at the module")
    decoupling(s, "C33", "47u 16V", (g(150), g(24)), "+5V", fp=CP_6MM, polar=True,
               desc="+5V reservoir near M1, electrolytic, 16 V")
    j6 = s.symbol("Connector_Generic:Conn_01x02", "J6", "SPK", (g(170), y + g(4)), footprint=HDR.format("1x02"),
                  ref_at=(g(2), g(-2)), value_at=(g(2), g(4)),
                  description="Speaker header, 2.54 mm, or a 2-pin JST PH. Silkscreen: SPK 8 Ohm. "
                              "Neither side is ground.")
    s.label(j6, "1", "SPK_P", stub=g(3))
    s.label(j6, "2", "SPK_N", stub=g(3))
    ls1 = s.symbol("Device:Speaker", "LS1", "8 Ohm, 0.5 W", (g(190), y + g(4)), on_board=False,
                   ref_at=(g(-2), g(-5)), value_at=(g(-2), g(6)),
                   description="Speaker, 8 Ohm, 0.5 W or more, 20 to 28 mm round. On J6, off the board: no footprint.")
    s.label(ls1, "1", "SPK_P", stub=g(2))
    s.label(ls1, "2", "SPK_N", stub=g(2))
    note(s, "R30, C30: 1 / (2 pi x 270 x 33 nF) = 17.9 kHz, the low-pass\n"
            "of audio.md. GPIO 18 at ALT5 is the PWM pin of the Pi Zero.\n"
            "C31 blocks DC. R31 divides first, so RV1 works mid-travel.", (g(14), g(66)))
    note(s, "RV1 is a level ceiling, set once, not a volume knob.\n"
            "EXPECTED POSITION: 30 % to 50 % of the travel from\n"
            "the GND end for 2 V peak at the speaker. It depends\n"
            "on M1's input impedance, 10 to 100 kOhm (to verify\n"
            "at bring-up step 18). Software volume: [audio] volume.", (g(84), g(92)))
    note(s, "M1 drives the speaker in bridge mode:\n"
            "neither SPK_P nor SPK_N is ground.\n"
            "8 Ohm speaker only. LS1 is bought and\n"
            "sits off the board, wired to J6, the\n"
            "board's connector.", (g(150), g(68)))
    note(s, "To verify: M1 pins assumed. Input row 1 VIN, 2 GND, 3 SD,\n"
            "4 A+, 5 A-. Output edge 6 OUT+, 7 OUT-. Footprint drawn\n"
            "from memory: redraw it from the module before ordering.\n"
            "Pins soldered at both edges carry OUT+ and OUT- to J6.\n"
            "A builder may instead wire LS1 to M1's own terminal.\n"
            "SD left open: the module pulls it high.\n"
            "Gain about 24 dB and input impedance: from memory.", (g(14), g(92)))
