"""Write a `.kicad_sch` from a circuit description with explicit placement.

The generator places every symbol where it is told. Connections are made with
a short wire stub on the pin and a net label or a power symbol at the stub
end. The text then points away from the part, so it never covers pin numbers.

Every position must be on the 1.27 mm grid. Every UUID comes from the
project name and the item path, so the output is the same on every run.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

import copy
import os
from typing import Dict, List, Optional, Tuple

import sexp
from common import GRID, check_grid, own_lib_dir, stable_uuid, stock_dir, write_if_changed
from sexp import Sym

FILE_VERSION = 20260306
"""The `.kicad_sch` format version that KiCad 10.0.8 writes."""


Point = Tuple[float, float]

# Unit vectors in screen coordinates (y grows down) for a pin pointing
# outward from the body, by direction name.
_DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}


def _r(v: float) -> float:
    return round(v, 4)


def _yes(flag: bool) -> Sym:
    return Sym("yes" if flag else "no")


def _font(size: float = 1.27) -> list:
    return [Sym("font"), [Sym("size"), size, size]]


# ---------------------------------------------------------------------------
# Symbol libraries


class LibraryError(LookupError):
    pass


class SymbolLibs:
    """Load symbol definitions from the stock libraries and from `lib/`."""

    def __init__(self, stock: Optional[str] = None, own: Optional[str] = None):
        self.stock = stock
        self.own = own or own_lib_dir()
        self._cache: Dict[str, list] = {}

    def _path(self, lib: str) -> str:
        if lib == "RobCo":
            return os.path.join(self.own, "RobCo.kicad_sym")
        return os.path.join(self.stock or stock_dir("symbols"), f"{lib}.kicad_sym")

    def _lib(self, lib: str) -> list:
        if lib not in self._cache:
            path = self._path(lib)
            if not os.path.exists(path):
                raise LibraryError(f"symbol library not found: {path}")
            self._cache[lib] = sexp.load(path)
        return self._cache[lib]

    def raw(self, lib: str, name: str) -> list:
        for s in sexp.children(self._lib(lib), "symbol"):
            if s[1] == name:
                return s
        raise LibraryError(f"symbol {lib}:{name} not found")

    def get(self, lib_id: str) -> list:
        """Return the symbol as it goes into `lib_symbols`: renamed, flat."""
        lib, name = lib_id.split(":", 1)
        node = copy.deepcopy(self.raw(lib, name))
        parent = sexp.value(node, "extends")
        if parent is not None:
            node = _flatten(copy.deepcopy(self.raw(lib, parent)), node, parent, name)
        node[1] = f"{lib}:{name}"
        return node


def _flatten(parent: list, child: list, pname: str, cname: str) -> list:
    """Merge a derived symbol into a copy of its parent, as KiCad does."""
    props = {p[1]: p for p in sexp.children(child, "property")}
    out = []
    for item in parent:
        if sexp.tag(item) == "property" and item[1] in props:
            out.append(props.pop(item[1]))
        elif sexp.tag(item) == "symbol":
            item[1] = cname + item[1][len(pname):]
            out.append(item)
        else:
            out.append(item)
    # Properties only the child has go after the parent's properties.
    last = max(i for i, it in enumerate(out) if sexp.tag(it) == "property")
    for k, p in enumerate(props.values()):
        out.insert(last + 1 + k, p)
    return out


def lib_pins(sym: list) -> Dict[str, Tuple[float, float, float]]:
    """Return {pin number: (x, y, angle)} in library coordinates (y up)."""
    pins: Dict[str, Tuple[float, float, float]] = {}
    for unit in sexp.children(sym, "symbol"):
        for p in sexp.children(unit, "pin"):
            at = sexp.child(p, "at")
            num = sexp.value(p, "number")
            pins[num] = (float(at[1]), float(at[2]), float(at[3]))
    return pins


# ---------------------------------------------------------------------------
# Geometry


def _rot(x: float, y: float, deg: int) -> Tuple[float, float]:
    deg %= 360
    if deg == 0:
        return x, y
    if deg == 90:
        return -y, x
    if deg == 180:
        return -x, -y
    if deg == 270:
        return y, -x
    raise ValueError(f"rotation must be a multiple of 90, got {deg}")


def _dir_name(dx: float, dy: float) -> str:
    for k, (a, b) in _DIRS.items():
        if (a, b) == (round(dx), round(dy)):
            return k
    raise ValueError("not an axis direction")


class Placed:
    """A symbol placed on the sheet."""

    def __init__(self, sch: "Schematic", lib_id: str, ref: str, at: Point, rot: int, pins):
        self.sch = sch
        self.lib_id = lib_id
        self.ref = ref
        self.at = at
        self.rot = rot
        self._pins = pins

    def pin(self, number: str) -> Point:
        """The pin's connection point in sheet coordinates."""
        px, py, _ = self._pin(number)
        dx, dy = _rot(px, py, self.rot)
        return (_r(self.at[0] + dx), _r(self.at[1] - dy))

    def outward(self, number: str) -> str:
        """The direction from the pin end away from the body."""
        _, _, ang = self._pin(number)
        # The pin angle points from the end into the body, in library axes.
        body = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[int(ang) % 360]
        bx, by = _rot(body[0], body[1], self.rot)
        return _dir_name(-bx, by)

    def _pin(self, number: str):
        number = str(number)
        if number not in self._pins:
            raise KeyError(f"{self.ref} has no pin {number}")
        return self._pins[number]


# ---------------------------------------------------------------------------
# The schematic


class Schematic:
    """Build one schematic sheet and write it."""

    def __init__(
        self,
        project: str,
        title: str,
        date: str,
        rev: str,
        company: str = "RobCo-Industries",
        comments: Optional[List[str]] = None,
        paper: str = "A4",
        libs: Optional[SymbolLibs] = None,
    ):
        self.project = project
        self.title = title
        self.date = date
        self.rev = rev
        self.company = company
        self.comments = comments or []
        self.paper = paper
        self.libs = libs or SymbolLibs()
        self.root = self.uuid("root")
        self.lib_symbols: Dict[str, list] = {}
        self.items: List[list] = []
        self.symbols: List[list] = []
        self.refs: Dict[str, Placed] = {}
        self._power_count = 0
        self._flag_count = 0
        self._wire_count = 0

    def uuid(self, *path: object) -> str:
        return stable_uuid(self.project, "sch", *path)

    # -- symbols ----------------------------------------------------------

    def symbol(
        self,
        lib_id: str,
        ref: str,
        value: str,
        at: Point,
        rot: int = 0,
        footprint: str = "",
        datasheet: str = "",
        description: str = "",
        ref_at=None,
        value_at: Optional[Point] = None,
        hide_ref: bool = False,
        in_bom: bool = True,
    ) -> Placed:
        """Place a symbol.

        `ref_at` and `value_at` are offsets from `at` for left-justified
        text. The default puts both to the right of the symbol. `ref_at="lib"`
        keeps the library's centred field positions instead.
        """
        if ref in self.refs:
            raise ValueError(f"duplicate reference {ref}")
        check_grid(f"{ref} position", *at)
        if lib_id not in self.lib_symbols:
            self.lib_symbols[lib_id] = self.libs.get(lib_id)
        pins = lib_pins(self.lib_symbols[lib_id])
        placed = Placed(self, lib_id, ref, at, rot, pins)
        for num in pins:
            check_grid(f"{ref} pin {num}", *placed.pin(num))
        x, y = at
        # KiCad turns field text with the symbol. Undo that so it reads level.
        text_angle = rot % 180
        lib_fields = ref_at == "lib"
        if lib_fields:
            ra = _lib_field(self.lib_symbols[lib_id], "Reference", rot)
            va = _lib_field(self.lib_symbols[lib_id], "Value", rot)
        else:
            ra = ref_at if ref_at is not None else (2.54, -1.27)
            va = value_at if value_at is not None else (2.54, 1.27)
        node = [
            Sym("symbol"),
            [Sym("lib_id"), lib_id],
            [Sym("at"), x, y, rot],
            [Sym("unit"), 1],
            [Sym("body_style"), 1],
            [Sym("exclude_from_sim"), Sym("no")],
            [Sym("in_bom"), _yes(in_bom)],
            [Sym("on_board"), _yes(in_bom)],
            [Sym("in_pos_files"), _yes(in_bom)],
            [Sym("dnp"), Sym("no")],
            [Sym("uuid"), self.uuid("symbol", ref)],
            self._prop("Reference", ref, (x + ra[0], y + ra[1]), hide=hide_ref,
                       left=not lib_fields, angle=text_angle),
            self._prop("Value", value, (x + va[0], y + va[1]), left=not lib_fields, angle=text_angle),
            self._prop("Footprint", footprint, at, hide=True),
            self._prop("Datasheet", datasheet, at, hide=True),
            self._prop("Description", description, at, hide=True),
        ]
        for num in sorted(pins, key=_pin_key):
            node.append([Sym("pin"), num, [Sym("uuid"), self.uuid("pin", ref, num)]])
        node.append(
            [
                Sym("instances"),
                [
                    Sym("project"),
                    self.project,
                    [Sym("path"), f"/{self.root}", [Sym("reference"), ref], [Sym("unit"), 1]],
                ],
            ]
        )
        self.symbols.append(node)
        self.refs[ref] = placed
        return placed

    def _prop(self, name: str, value: str, at: Point, hide: bool = False, left: bool = False,
              angle: int = 0) -> list:
        effects = [Sym("effects"), _font()]
        if left:
            effects.append([Sym("justify"), Sym("left")])
        node = [Sym("property"), name, value, [Sym("at"), _r(at[0]), _r(at[1]), angle]]
        if hide:
            node.append([Sym("hide"), Sym("yes")])
        node += [[Sym("show_name"), Sym("no")], [Sym("do_not_autoplace"), Sym("no")], effects]
        return node

    # -- connections --------------------------------------------------------

    def wire(self, *points: Point) -> None:
        """Draw a wire through the points. Each segment is a separate wire."""
        for a, b in zip(points, points[1:]):
            check_grid("wire end", *a, *b)
            self._wire_count += 1
            self.items.append(
                [
                    Sym("wire"),
                    [Sym("pts"), [Sym("xy"), _r(a[0]), _r(a[1])], [Sym("xy"), _r(b[0]), _r(b[1])]],
                    [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                    [Sym("uuid"), self.uuid("wire", self._wire_count)],
                ]
            )

    def _stub(self, part: Placed, pin: str, length: float, then=()) -> Tuple[Point, str]:
        start = part.pin(pin)
        d = part.outward(pin)
        dx, dy = _DIRS[d]
        end = (_r(start[0] + dx * length), _r(start[1] + dy * length))
        points = [start, end] if length else [start]
        for mx, my in then:
            end = (_r(end[0] + mx), _r(end[1] + my))
            points.append(end)
            if mx and not my:
                d = "right" if mx > 0 else "left"
            elif my and not mx:
                d = "down" if my > 0 else "up"
            else:
                raise ValueError("each move must be horizontal or vertical")
        if len(points) > 1:
            self.wire(*points)
        return end, d

    def label(self, part: Placed, pin: str, net: str, stub: float = 2 * GRID, then=()) -> None:
        """Connect a pin to a net with a wire stub and a net label.

        `then` adds wire moves (dx, dy) after the stub. The label text runs
        away from the part. On a vertical end the text is horizontal and
        starts at the wire end.
        """
        end, d = self._stub(part, pin, stub, then)
        check_grid(f"label {net}", *end)
        angle = {"right": 0, "left": 180, "up": 0, "down": 0}[d]
        justify = [Sym("justify"), Sym("right" if angle == 180 else "left"), Sym("bottom")]
        self.items.append(
            [
                Sym("label"),
                net,
                [Sym("at"), end[0], end[1], angle],
                [Sym("fields_autoplaced"), Sym("yes")],
                [Sym("effects"), _font(), justify],
                [Sym("uuid"), self.uuid("label", part.ref, pin)],
            ]
        )

    def power(self, part: Placed, pin: str, net: str, stub: float = 2 * GRID, then=()) -> None:
        """Connect a pin to a rail with a wire stub and a power symbol.

        `then` adds wire moves (dx, dy) after the stub, to clear other pins.
        """
        end, _ = self._stub(part, pin, stub, then)
        self.power_symbol(net, end)

    def power_symbol(self, net: str, at: Point, rot: int = 0) -> Placed:
        self._power_count += 1
        ref = f"#PWR{self._power_count:02d}"
        return self.symbol(f"power:{net}", ref, net, at, rot=rot, hide_ref=True, ref_at="lib",
                           in_bom=False, description=f"Power symbol for the {net} rail")

    def power_flag(self, net: str, at: Point) -> None:
        """Mark a rail as driven, so ERC knows a source feeds it.

        Draws the rail's power symbol at `at`, a short wire and a PWR_FLAG.
        """
        self._flag_count += 1
        ref = f"#FLG{self._flag_count:02d}"
        x, y = at
        if net == "GND":
            top = (x, _r(y - 2 * GRID))
            self.power_symbol(net, at)
            self.wire(at, top)
            self.symbol("power:PWR_FLAG", ref, "PWR_FLAG", top, hide_ref=True,
                        ref_at="lib", in_bom=False)
        else:
            bottom = (x, _r(y + 2 * GRID))
            self.power_symbol(net, at)
            self.wire(at, bottom)
            self.symbol("power:PWR_FLAG", ref, "PWR_FLAG", bottom, rot=180, hide_ref=True,
                        ref_at="lib", in_bom=False)

    def text(self, body: str, at: Point, size: float = 1.27) -> None:
        self.items.append(
            [
                Sym("text"),
                body,
                [Sym("exclude_from_sim"), Sym("no")],
                [Sym("at"), _r(at[0]), _r(at[1]), 0],
                [Sym("effects"), _font(size), [Sym("justify"), Sym("left"), Sym("bottom")]],
                [Sym("uuid"), self.uuid("text", body)],
            ]
        )

    # -- output -------------------------------------------------------------

    def tree(self) -> list:
        tb = [Sym("title_block"), [Sym("title"), self.title], [Sym("date"), self.date],
              [Sym("rev"), self.rev], [Sym("company"), self.company]]
        for i, c in enumerate(self.comments[:9], start=1):
            tb.append([Sym("comment"), i, c])
        return (
            [
                Sym("kicad_sch"),
                [Sym("version"), FILE_VERSION],
                [Sym("generator"), "robco_gen"],
                [Sym("generator_version"), "10.0"],
                [Sym("uuid"), self.root],
                [Sym("paper"), self.paper],
                tb,
                [Sym("lib_symbols")] + [self.lib_symbols[k] for k in sorted(self.lib_symbols)],
            ]
            + self.items
            + self.symbols
            + [
                [Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]],
                [Sym("embedded_fonts"), Sym("no")],
            ]
        )

    def text_out(self) -> str:
        return sexp.dump_file(self.tree())

    def write(self, path: str) -> bool:
        return write_if_changed(path, self.text_out())

    def stock_libs(self) -> List[str]:
        return sorted({k.split(":", 1)[0] for k in self.lib_symbols})


def _lib_field(sym: list, name: str, rot: int) -> Point:
    for p in sexp.children(sym, "property"):
        if p[1] == name:
            at = sexp.child(p, "at")
            dx, dy = _rot(float(at[1]), float(at[2]), rot)
            return (_r(dx), _r(-dy))
    return (0.0, 0.0)


def _pin_key(num: str):
    return (0, int(num), "") if num.isdigit() else (1, 0, num)
