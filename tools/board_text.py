"""Text post-steps for a saved `.kicad_pcb`: stackup and UUIDs.

These do not need `pcbnew`, so the tests run them on any Python 3.9+.
"""

from __future__ import annotations

import re
from typing import Dict

import sexp
from common import stable_uuid
from project import RULES
from sexp import Sym


def stackup_node(rules: Dict[str, float] = RULES) -> list:
    """The stackup as an S-expression: 1 oz copper on 1.6 mm FR-4.

    The `pcbnew` Python module does not expose the stackup editor, so
    `save()` writes this node into the board's `setup` section.
    """
    cu = rules["copper_thickness"]
    mask = 0.01
    core = round(rules["board_thickness"] - 2 * cu - 2 * mask, 4)

    def layer(name: str, kind: str, *extra: list) -> list:
        return [Sym("layer"), name, [Sym("type"), kind]] + list(extra)

    def th(v: float) -> list:
        return [Sym("thickness"), v]

    return [
        Sym("stackup"),
        layer("F.SilkS", "Top Silk Screen"),
        layer("F.Paste", "Top Solder Paste"),
        layer("F.Mask", "Top Solder Mask", [Sym("color"), "Green"], th(mask)),
        layer("F.Cu", "copper", th(cu)),
        layer("dielectric 1", "core", th(core), [Sym("material"), "FR4"],
              [Sym("epsilon_r"), 4.5], [Sym("loss_tangent"), 0.02]),
        layer("B.Cu", "copper", th(cu)),
        layer("B.Mask", "Bottom Solder Mask", [Sym("color"), "Green"], th(mask)),
        layer("B.Paste", "Bottom Solder Paste"),
        layer("B.SilkS", "Bottom Silk Screen"),
        [Sym("copper_finish"), "None"],
        [Sym("dielectric_constraints"), Sym("no")],
    ]


def add_stackup(text: str, rules: Dict[str, float] = RULES) -> str:
    """Put the stackup node first in the board's `setup` section."""
    tree = sexp.parse(text)
    setup = sexp.child(tree, "setup")
    if setup is None:
        raise ValueError("board file has no setup section")
    setup[:] = [c for c in setup if sexp.tag(c) != "stackup"]
    setup.insert(1, stackup_node(rules))
    return sexp.dump_file(tree)


_UUID = re.compile(r'\((uuid|tstamp) "([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-([0-9a-fA-F])[0-9a-fA-F-]{21})"\)')


def normalise(text: str, seed: str) -> str:
    """Replace any random UUID left in the text with a stable one.

    `stamp_uuids()` covers the items we know. This catches the rest: every
    UUID that is not version 5 is replaced, by order of appearance. The same
    UUID gets the same replacement everywhere in the file.
    """
    mapping: Dict[str, str] = {}

    def sub(m: "re.Match[str]") -> str:
        old = m.group(2).lower()
        if m.group(3) == "5":
            return m.group(0)
        if old not in mapping:
            mapping[old] = stable_uuid(seed, "pcb", "leftover", len(mapping))
        return f'({m.group(1)} "{mapping[old]}")'

    return _UUID.sub(sub, text)
