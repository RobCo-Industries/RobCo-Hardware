"""Build a `.kicad_pcb` with KiCad's `pcbnew` module.

Run this with the Python that ships with KiCad, which can import `pcbnew`.
It creates the board, sets the stackup and the design rules, loads the
footprints named in the schematic netlist, assigns the pad nets, places the
parts from a placement table, draws the outline, adds mounting holes and
saves.

`pcbnew` gives every new item a random UUID, and KiCad sorts some items
by UUID when it saves. So `stamp_uuids()` sets a UUID derived from the
project name and a stable key on each item before saving. Two post-steps
then run on the saved text: `add_stackup()` writes the stackup, because
the Python module cannot, and `normalise()` replaces any random UUID left.
A regenerated board is then byte-identical to the last one. Footprint
`path` values link to the schematic symbols, whose UUIDs are already stable.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Sequence, Tuple

import pcbnew  # type: ignore

from board_text import add_stackup, normalise
from common import own_lib_dir, stable_uuid, stock_dir, write_if_changed
from netlist import Netlist
from project import RULES

Point = Tuple[float, float]


def mm(v: float) -> int:
    return pcbnew.FromMM(v)


def pt(p: Point):
    return pcbnew.VECTOR2I(mm(p[0]), mm(p[1]))


def new_board(rules: Dict[str, float] = RULES):
    """Create an empty 2-layer board with the plan's stackup and rules."""
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(rules["board_thickness"]))
    ds.m_TrackMinWidth = mm(rules["track_width"])
    ds.m_MinClearance = mm(rules["clearance"])
    ds.m_ViasMinSize = mm(rules["via_diameter"])
    ds.m_CopperEdgeClearance = mm(rules["edge_clearance"])
    return board


def footprint_dir(lib: str) -> str:
    if lib == "RobCo":
        return os.path.join(own_lib_dir(), "RobCo.pretty")
    return os.path.join(stock_dir("footprints"), f"{lib}.pretty")


def load_footprint(fpid: str):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(footprint_dir(lib), name)
    if fp is None:
        raise LookupError(f"footprint {fpid} not found in {footprint_dir(lib)}")
    fp.SetFPIDAsString(fpid)
    return fp


class Place:
    """Where a part goes: centre in mm, rotation in degrees, side."""

    def __init__(self, x: float, y: float, rot: float = 0, side: str = "top"):
        self.x, self.y, self.rot, self.side = x, y, rot, side


def add_parts(board, nl: Netlist, placement: Dict[str, Place], sheetfile: str) -> Dict[str, object]:
    """Add one footprint per netlist component and set the pad nets.

    Every component needs a placement entry, and every placement entry needs
    a component. Returns {ref: footprint}.
    """
    missing = sorted(set(nl.components) - set(placement))
    extra = sorted(set(placement) - set(nl.components))
    if missing or extra:
        raise ValueError(f"placement and netlist differ: missing {missing}, unknown {extra}")
    nets: Dict[str, object] = {}
    for name in sorted(nl.nets):
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    pin_net = nl.pin_net()
    out: Dict[str, object] = {}
    for ref in sorted(nl.components):
        comp = nl.components[ref]
        if not comp.footprint:
            raise ValueError(f"{ref} has no footprint in the schematic")
        fp = load_footprint(comp.footprint)
        fp.SetReference(ref)
        fp.SetValue(comp.value)
        fp.SetPath(pcbnew.KIID_PATH(comp.path))
        fp.SetSheetname(comp.sheet_names)
        fp.SetSheetfile(sheetfile)
        p = placement[ref]
        board.Add(fp)
        if p.side == "bottom":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetPosition(pt((p.x, p.y)))
        fp.SetOrientationDegrees(p.rot)
        numbers = set()
        for pad in fp.Pads():
            numbers.add(pad.GetNumber())
            net = pin_net.get((ref, pad.GetNumber()))
            if net is not None:
                pad.SetNet(nets[net])
        for (r, pin) in pin_net:
            if r == ref and pin not in numbers:
                raise ValueError(f"{ref} pin {pin} has no pad on {comp.footprint}")
        out[ref] = fp
    return out


def outline(board, corners: Sequence[Point], width: float = 0.1) -> None:
    """Draw a closed outline on Edge.Cuts through the corners."""
    for a, b in zip(corners, list(corners[1:]) + [corners[0]]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(width))
        s.SetStart(pt(a))
        s.SetEnd(pt(b))
        board.Add(s)


def rect_outline(board, x: float, y: float, w: float, h: float) -> None:
    outline(board, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])


def mounting_hole(board, ref: str, at: Point, fpid: str = "MountingHole:MountingHole_2.7mm_M2.5") -> object:
    """Add a board-only mounting hole footprint. Its reference is hidden."""
    fp = load_footprint(fpid)
    fp.SetReference(ref)
    fp.Reference().SetVisible(False)
    fp.SetBoardOnly(True)
    fp.SetPosition(pt(at))
    board.Add(fp)
    return fp


def pad_pos(fp, number: str) -> Point:
    for pad in fp.Pads():
        if pad.GetNumber() == number:
            p = pad.GetPosition()
            return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
    raise KeyError(f"{fp.GetReference()} has no pad {number}")


def track(board, fp_a, pad_a: str, fp_b, pad_b: str, via: Iterable[Point] = (), width: float = 0.4,
          layer=None) -> None:
    """Draw straight segments from one pad through the points to another pad.

    The segments take the net of the first pad. No checks: DRC finds shorts.
    """
    pad = [p for p in fp_a.Pads() if p.GetNumber() == pad_a][0]
    points: List[Point] = [pad_pos(fp_a, pad_a)] + list(via) + [pad_pos(fp_b, pad_b)]
    for a, b in zip(points, points[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(a))
        t.SetEnd(pt(b))
        t.SetWidth(mm(width))
        t.SetLayer(pcbnew.F_Cu if layer is None else layer)
        t.SetNet(pad.GetNet())
        board.Add(t)


def stamp_uuids(board, seed: str) -> None:
    """Give every item a UUID derived from the seed and a stable key.

    KiCad sorts some items by UUID when it saves, so random UUIDs also
    shuffle the file. Footprints are keyed by reference, their children by
    kind and index, tracks and drawings by the order they were added.
    """

    def kid(*path: object):
        return pcbnew.KIID(stable_uuid(seed, "pcb", *path))

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.SetUuidDirect(kid("fp", ref))
        for f in fp.GetFields():
            f.SetUuidDirect(kid("fp", ref, "field", f.GetName()))
        for i, item in enumerate(fp.GraphicalItems()):
            item.SetUuidDirect(kid("fp", ref, "gfx", i))
        for i, pad in enumerate(fp.Pads()):
            pad.SetUuidDirect(kid("fp", ref, "pad", pad.GetNumber(), i))
        for i, zone in enumerate(fp.Zones()):
            zone.SetUuidDirect(kid("fp", ref, "zone", i))
    for i, t in enumerate(board.GetTracks()):
        t.SetUuidDirect(kid("track", i))
    for i, d in enumerate(board.GetDrawings()):
        d.SetUuidDirect(kid("drawing", i))
    for i, z in enumerate(board.Zones()):
        z.SetUuidDirect(kid("zone", i))


def save(board, path: str, seed: str) -> bool:
    """Save the board, add the stackup and normalise the UUIDs.

    Return True if the file changed.
    """
    stamp_uuids(board, seed)
    tmp = path + ".tmp"
    pcbnew.SaveBoard(tmp, board)
    with open(tmp, encoding="utf-8") as fh:
        text = normalise(add_stackup(fh.read()), seed)
    os.remove(tmp)
    for extra in (tmp.replace(".kicad_pcb.tmp", ".kicad_prl"),):
        if os.path.exists(extra):
            os.remove(extra)
    return write_if_changed(path, text)
