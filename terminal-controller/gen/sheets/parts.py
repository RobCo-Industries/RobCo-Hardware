"""Symbols, footprints and small drawing helpers shared by the sheets.

Every footprint named here exists in the KiCad 10.0.8 stock libraries. An
empty footprint means no stock footprint fits: the board step must add one.
"""

from __future__ import annotations

from typing import Optional

from common import g
from sch import Placed, Schematic

# Own rail symbols in lib/RobCo.kicad_sym. The stock "power" library has the rest.
POWER_LIBS = {"V_PROT": "RobCo", "V_SW": "RobCo", "+V_S": "RobCo"}

R_AXIAL = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
R_HALF_WATT = "Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal"
C_DISC = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
C_FILM = "Capacitor_THT:C_Rect_L7.2mm_W2.5mm_P5.00mm"
CP_8MM = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
CP_5MM = "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"
LED_3MM = "LED_THT:LED_D3.0mm"
DO35 = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
DO201 = "Diode_THT:D_DO-201AD_P15.24mm_Horizontal"
TP_LOOP = "TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm"
TP_LOOP_BIG = "TestPoint:TestPoint_Loop_D3.80mm_Drill2.0mm"
HDR = "Connector_PinHeader_2.54mm:PinHeader_{}_P2.54mm_Vertical"
TERM_2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal"
TERM_10 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-10-3.5-H_1x10_P3.50mm_Horizontal"
SJ3 = "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm"
SJ2 = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
NO_FOOTPRINT = ""
"""No stock footprint fits. The board step must add one. See the board README."""

# Fields of a vertical two-pin part, to its right.
RIGHT = dict(ref_at=(g(2), g(-1)), value_at=(g(2), g(1)))
# Fields of a horizontal two-pin part, above and below it.
ABOVE = dict(ref_at=(g(-2), g(-2)), value_at=(g(-2), g(3)))


def res(s: Schematic, ref: str, value: str, at, horizontal: bool = False, fp: str = R_AXIAL,
        dnp: bool = False, desc: str = "", **kw) -> Placed:
    """A resistor. Vertical by default: pin 1 at the top."""
    fields = dict(ABOVE if horizontal else RIGHT)
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


def testpoint(s: Schematic, ref: str, net: str, at, fp: str = TP_LOOP,
              desc: str = "") -> Placed:
    """A test point loop. The loop is on top, the pin points down to a rail or a label."""
    tp = s.symbol("Connector:TestPoint", ref, f"{net}", at, footprint=fp,
                  ref_at=(g(2), g(-3)), value_at=(g(2), g(-1)), description=desc or f"Test point on {net}")
    return tp


def flag_at(s: Schematic, at, rot: int = 0) -> None:
    """A PWR_FLAG whose pin sits at `at`: marks a local net that a part such as a cell feeds."""
    s.shared["flag"] += 1
    s.symbol("power:PWR_FLAG", f"#FLG{s.shared['flag']:02d}", "PWR_FLAG", at, rot=rot, hide_ref=True,
             ref_at="lib", in_bom=False)


def wire_l(s: Schematic, a, b, first: str = "h") -> None:
    """Wire a to b with one corner: horizontal first ("h") or vertical first ("v")."""
    if a[0] == b[0] or a[1] == b[1]:
        s.wire(a, b)
        return
    corner = (b[0], a[1]) if first == "h" else (a[0], b[1])
    s.wire(a, corner, b)


def note(s: Schematic, body: str, at, size: Optional[float] = None) -> None:
    s.text(body, at, size=size or 1.27)
