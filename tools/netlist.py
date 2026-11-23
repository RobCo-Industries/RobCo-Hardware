"""Read a KiCad netlist written by `kicad-cli sch export netlist`.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import sexp


class Component:
    def __init__(self, ref: str, value: str, footprint: str, uuid: str, sheet_names: str, sheet_uuids: str):
        self.ref = ref
        self.value = value
        self.footprint = footprint
        self.uuid = uuid
        self.sheet_names = sheet_names
        self.sheet_uuids = sheet_uuids

    @property
    def path(self) -> str:
        """The KIID path a board footprint uses to link back to the symbol."""
        return self.sheet_uuids + self.uuid


class Netlist:
    def __init__(self) -> None:
        self.components: Dict[str, Component] = {}
        self.nets: Dict[str, List[Tuple[str, str]]] = {}

    def pin_net(self) -> Dict[Tuple[str, str], str]:
        """Return {(ref, pin): net name}."""
        out: Dict[Tuple[str, str], str] = {}
        for name, nodes in self.nets.items():
            for node in nodes:
                out[node] = name
        return out


def short_net(name: str) -> str:
    """Drop the root sheet prefix: `/SIG` becomes `SIG`, `+5V` stays."""
    return name[1:] if name.startswith("/") and name.count("/") == 1 else name


def parse(text: str) -> Netlist:
    tree = sexp.parse(text)
    if sexp.tag(tree) != "export":
        raise ValueError("not a KiCad netlist: no (export ...) root")
    nl = Netlist()
    comps = sexp.child(tree, "components") or []
    for c in sexp.children(comps, "comp"):
        ref = sexp.value(c, "ref")
        sp = sexp.child(c, "sheetpath") or []
        nl.components[ref] = Component(
            ref,
            sexp.value(c, "value", ""),
            sexp.value(c, "footprint", ""),
            sexp.value(c, "tstamps", ""),
            sexp.value(sp, "names", "/"),
            sexp.value(sp, "tstamps", "/"),
        )
    nets = sexp.child(tree, "nets") or []
    for n in sexp.children(nets, "net"):
        name = sexp.value(n, "name")
        nl.nets[name] = [(sexp.value(nd, "ref"), sexp.value(nd, "pin")) for nd in sexp.children(n, "node")]
    return nl


def load(path: str) -> Netlist:
    with open(path, encoding="utf-8") as fh:
        return parse(fh.read())
