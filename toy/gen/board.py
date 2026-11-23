"""Toy board layout: placement, outline, mounting holes and three tracks.

Run with KiCad's bundled Python, which can import `pcbnew`:
    $PY toy/gen/board.py <netlist> [output folder]

The netlist comes from `kicad-cli sch export netlist` on the toy schematic.
Scripted routing is for the toy only. Real boards are routed by hand.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import netlist  # noqa: E402
import pcb  # noqa: E402
from pcb import Place  # noqa: E402

PROJECT = "toy"

# Board corner on the page, and its size, in mm.
X0, Y0, W, H = 100.0, 100.0, 30.0, 20.0

PLACEMENT = {
    "J1": Place(X0 + 4, Y0 + 6),  # pin 1 at the top, pins go down 2.54 mm apart
    "R1": Place(X0 + 13, Y0 + 11.08),
    "D1": Place(X0 + 21, Y0 + 11.08, rot=180),  # anode faces R1
}

HOLES = {"H1": (X0 + 3.5, Y0 + 16.5), "H2": (X0 + W - 3.5, Y0 + 16.5)}


def route(board, fps) -> None:
    """Three nets: SIG and LED_A run straight, GND goes over the top."""
    pcb.track(board, fps["J1"], "3", fps["R1"], "1")
    pcb.track(board, fps["R1"], "2", fps["D1"], "2")
    kx, _ = pcb.pad_pos(fps["D1"], "1")
    jx, jy = pcb.pad_pos(fps["J1"], "2")
    top = Y0 + 2.5
    pcb.track(board, fps["J1"], "2", fps["D1"], "1",
              via=[(jx + 2.5, jy), (jx + 2.5, top), (kx, top)])


def build(net_path: str):
    nl = netlist.load(net_path)
    board = pcb.new_board()
    fps = pcb.add_parts(board, nl, PLACEMENT, f"{PROJECT}.kicad_sch")
    pcb.rect_outline(board, X0, Y0, W, H)
    for ref, at in HOLES.items():
        pcb.mounting_hole(board, ref, at)
    route(board, fps)
    return board


def main() -> None:
    net_path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "kicad")
    board = build(net_path)
    pcb.save(board, os.path.join(out, f"{PROJECT}.kicad_pcb"), PROJECT)


if __name__ == "__main__":
    main()
