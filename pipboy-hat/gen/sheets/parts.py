"""Footprints and small drawing helpers shared by the Pip-Boy HAT sheets.

Every stock footprint named here exists in the KiCad 10.0.8 stock libraries.
The fuse, the dial and the amplifier module use own footprints in
lib/RobCo.pretty.
"""

from __future__ import annotations

from typing import Optional

from common import g
from sch import Placed, Schematic

R_AXIAL = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
C_DISC = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
C_FILM = "Capacitor_THT:C_Rect_L7.2mm_W2.5mm_P5.00mm"
CP_5MM = "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"
CP_6MM = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
DO35 = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
DO15 = "Diode_THT:D_DO-15_P12.70mm_Horizontal"
TO92 = "Package_TO_SOT_THT:TO-92_Inline"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOIC8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
TP_LOOP = "TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm"
TP_LOOP_BIG = "TestPoint:TestPoint_Loop_D3.80mm_Drill2.0mm"
HDR = "Connector_PinHeader_2.54mm:PinHeader_{}_P2.54mm_Vertical"
SJ2 = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
KEY_12MM = "Button_Switch_THT:SW_PUSH-12mm"
FUSE_MF_R = "RobCo:Fuse_PTC_Radial_W7.4mm_T3.0mm_P5.10mm"
PAM8302A_MODULE = "RobCo:PAM8302A_Module_1x07_P2.54mm"
ENCODER = "RobCo:RotaryEncoder_Bourns_PEC11R-Switch_Vertical"

# Fields of a vertical two-pin part, to its right.
RIGHT = dict(ref_at=(g(2), g(-1)), value_at=(g(2), g(1)))
# Horizontal parts are turned 90 degrees: KiCad then right-justifies their
# fields, so each anchor is the end of the text.
H_FIELDS = dict(ref_at=(g(3), g(-2)), value_at=(g(3), g(3)))


def res(s: Schematic, ref: str, value: str, at, horizontal: bool = False, fp: str = R_AXIAL,
        dnp: bool = False, desc: str = "", **kw) -> Placed:
    """A resistor. Vertical by default, pin 1 at the top. Horizontal, pin 1 on the left."""
    fields = dict(H_FIELDS if horizontal else RIGHT)
    fields.update(kw)
    return s.symbol("Device:R", ref, value, at, rot=90 if horizontal else 0, footprint=fp, dnp=dnp,
                    description=desc, **fields)


def cap(s: Schematic, ref: str, value: str, at, fp: str = C_DISC, polar: bool = False,
        dnp: bool = False, desc: str = "", **kw) -> Placed:
    """A capacitor, vertical, pin 1 at the top (the + side of a polarised one)."""
    fields = dict(RIGHT)
    fields.update(kw)
    lib = "Device:C_Polarized" if polar else "Device:C"
    return s.symbol(lib, ref, value, at, footprint=fp, dnp=dnp, description=desc, **fields)


def decoupling(s: Schematic, ref: str, value: str, at, rail: str, fp: str = C_DISC, polar: bool = False,
               dnp: bool = False, desc: str = "", **kw) -> Placed:
    """A capacitor from a rail at the top to GND at the bottom."""
    c = cap(s, ref, value, at, fp=fp, polar=polar, dnp=dnp, desc=desc, **kw)
    s.power(c, "1", rail, stub=g(1))
    s.power(c, "2", "GND", stub=g(1))
    return c


def testpoint(s: Schematic, ref: str, net: str, at, fp: str = TP_LOOP, rot: int = 0,
              desc: str = "") -> Placed:
    """A test point loop. The loop is on top and the pin points down; with
    rot=180 the loop hangs below and the pin points up."""
    fields = dict(ref_at=(g(2), g(-3)), value_at=(g(2), g(-1))) if rot == 0 else \
        dict(ref_at=(g(6), g(1)), value_at=(g(8), g(3)))
    return s.symbol("Connector:TestPoint", ref, net, at, rot=rot, footprint=fp,
                    description=desc or f"Test point on {net}", **fields)


def sideways(s: Schematic, part: Placed, pin: str, net: str, stub: float = g(3)) -> None:
    """A rail on a side pin: the symbol turned to point away, its name beside it."""
    end, d = s._stub(part, pin, stub)
    left = d == "left"
    s.power_symbol(net, end, rot=90 if left else 270,
                   value_at=(-g(4 + len(net)), 0) if left else (g(3), -0.6 if net == "GND" else 0))


def flag_at(s: Schematic, at, rot: int = 0) -> None:
    """A PWR_FLAG whose pin sits at `at`: marks a local net that a part such as a cell feeds."""
    s.shared["flag"] += 1
    s.symbol("power:PWR_FLAG", f"#FLG{s.shared['flag']:02d}", "PWR_FLAG", at, rot=rot, hide_ref=True,
             ref_at="lib", in_bom=False)


def note(s: Schematic, body: str, at, size: Optional[float] = None) -> None:
    """A text note. KiCad puts a multi-line note above its anchor: `at` is the
    bottom left corner of the last line."""
    s.text(body, at, size=size or 1.27)
