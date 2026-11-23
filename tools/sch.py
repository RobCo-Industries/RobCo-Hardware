"""Write `.kicad_sch` files from a circuit description with explicit placement.

The generator places every symbol where it is told. Connections are made with
a short wire stub on the pin and a net label or a power symbol at the stub
end. The text then points away from the part, so it never covers pin numbers.

Every position must be on the 1.27 mm grid. Every UUID comes from the
project name and the item path, so the output is the same on every run.

A board can be one sheet (`Schematic`) or a root sheet with one sub-sheet per
block (`Hierarchy`). Nets that cross sheets use global labels or power
symbols.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

import copy
import os
from typing import Callable, Dict, List, Optional, Tuple

import sexp
from common import GRID, check_grid, g, own_lib_dir, stable_uuid, stock_dir, write_if_changed
from sexp import Sym

PROPOSAL = "Proposal. Not built, not validated on hardware."
"""The status line every sheet's title block carries."""

LABEL_SHAPES = ("input", "output", "bidirectional", "tri_state", "passive")
"""Global label shapes that KiCad knows."""

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


def lib_pins(sym: list, unit: Optional[int] = None) -> Dict[str, Tuple[float, float, float]]:
    """Return {pin number: (x, y, angle)} in library coordinates (y up).

    With `unit`, only the pins of that unit and of the common unit 0.
    """
    pins: Dict[str, Tuple[float, float, float]] = {}
    for sub in sexp.children(sym, "symbol"):
        if unit is not None and int(sub[1].rsplit("_", 2)[-2]) not in (0, unit):
            continue
        unit_node = sub
        for p in sexp.children(unit_node, "pin"):
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

    def __init__(self, sch: "Schematic", lib_id: str, ref: str, at: Point, rot: int, pins,
                 mirror: str = ""):
        self.sch = sch
        self.lib_id = lib_id
        self.ref = ref
        self.at = at
        self.rot = rot
        self.mirror = mirror
        self._pins = pins

    def _tf(self, x: float, y: float) -> Tuple[float, float]:
        """Library vector (y up) to sheet vector (y down): rotate, then mirror."""
        dx, dy = _rot(x, y, self.rot)
        sx, sy = dx, -dy
        if self.mirror == "x":  # flip top and bottom
            sy = -sy
        elif self.mirror == "y":  # flip left and right
            sx = -sx
        return sx, sy

    def pin(self, number: str) -> Point:
        """The pin's connection point in sheet coordinates."""
        px, py, _ = self._pin(number)
        sx, sy = self._tf(px, py)
        return (_r(self.at[0] + sx), _r(self.at[1] + sy))

    def outward(self, number: str) -> str:
        """The direction from the pin end away from the body."""
        _, _, ang = self._pin(number)
        # The pin angle points from the end into the body, in library axes.
        body = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[int(ang) % 360]
        bx, by = self._tf(*body)
        return _dir_name(-bx, -by)

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
        sheet: Optional[str] = None,
        shared: Optional[dict] = None,
        power_libs: Optional[Dict[str, str]] = None,
    ):
        self.project = project
        self.sheet = sheet
        self.title = title
        self.date = date
        self.rev = rev
        self.company = company
        self.comments = comments or []
        self.paper = paper
        self.libs = libs or SymbolLibs()
        self.root = self.uuid("root")
        # The path of this sheet's instance, for symbol annotation. A sub-sheet
        # gets "/<root uuid>/<sheet uuid>" from its Hierarchy.
        self.instance_path = f"/{self.root}"
        # Reference and power symbol counters, shared by every sheet of a design.
        self.shared = shared if shared is not None else {"refs": set(), "power": 0, "flag": 0}
        self.shared.setdefault("units", set())
        # Rails whose power symbol is not in the stock "power" library: {net: library}.
        self.power_libs = power_libs or {}
        self.lib_symbols: Dict[str, list] = {}
        self.items: List[list] = []
        self.symbols: List[list] = []
        self.refs: Dict[str, Placed] = {}
        self._wire_count = 0
        self._junctions: List[Point] = []
        self._texts: set = set()

    def uuid(self, *path: object) -> str:
        if self.sheet is None:
            return stable_uuid(self.project, "sch", *path)
        return stable_uuid(self.project, "sch", self.sheet, *path)

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
        mirror: str = "",
        unit: int = 1,
        dnp: bool = False,
    ) -> Placed:
        """Place a symbol.

        `ref_at` and `value_at` are offsets from `at` for left-justified
        text. The default puts both to the right of the symbol. `ref_at="lib"`
        keeps the library's centred field positions instead. `mirror` is
        "x" (flip top and bottom) or "y" (flip left and right), applied after
        the rotation, as KiCad does. On a symbol mirrored left to right KiCad
        right-justifies the fields, so `ref_at` then marks the end of the text.

        `unit` places one unit of a multi-unit part, such as one channel of a
        quad optocoupler. Each unit of a reference is placed once. `dnp`
        marks a part that is not fitted: it stays in the netlist and the BOM
        with KiCad's "do not populate" flag.
        """
        if (ref, unit) in self.shared["units"]:
            raise ValueError(f"duplicate reference {ref}" + (f" unit {unit}" if unit != 1 else ""))
        if mirror not in ("", "x", "y"):
            raise ValueError(f"mirror must be '', 'x' or 'y', got {mirror!r}")
        check_grid(f"{ref} position", *at)
        if lib_id not in self.lib_symbols:
            self.lib_symbols[lib_id] = self.libs.get(lib_id)
        units = {int(s[1].rsplit("_", 2)[-2]) for s in sexp.children(self.lib_symbols[lib_id], "symbol")}
        if unit not in units and not (unit == 1 and units <= {0, 1}):
            raise ValueError(f"{ref}: {lib_id} has no unit {unit}")
        pins = lib_pins(self.lib_symbols[lib_id], unit if max(units) > 1 else None)
        placed = Placed(self, lib_id, ref, at, rot, pins, mirror)
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
        ]
        if mirror:
            node.append([Sym("mirror"), Sym(mirror)])
        node += [
            [Sym("unit"), unit],
            [Sym("body_style"), 1],
            [Sym("exclude_from_sim"), Sym("no")],
            [Sym("in_bom"), _yes(in_bom)],
            [Sym("on_board"), _yes(in_bom)],
            [Sym("in_pos_files"), _yes(in_bom)],
            [Sym("dnp"), _yes(dnp)],
            [Sym("uuid"), self.uuid("symbol", ref) if unit == 1 else self.uuid("symbol", ref, unit)],
            self._prop("Reference", ref, (x + ra[0], y + ra[1]), hide=hide_ref,
                       left=not lib_fields, angle=text_angle),
            self._prop("Value", value, (x + va[0], y + va[1]), left=not lib_fields, angle=text_angle),
            self._prop("Footprint", footprint, at, hide=True),
            self._prop("Datasheet", datasheet, at, hide=True),
            self._prop("Description", description, at, hide=True),
        ]
        for num in sorted(pins, key=_pin_key):
            node.append([Sym("pin"), num, [Sym("uuid"), self.uuid("pin", ref, num)]])
        # The instance path is filled in at output time: a Hierarchy may set
        # instance_path after the symbols are placed.
        self.symbols.append(node)
        self.refs[ref if unit == 1 else f"{ref}:{unit}"] = placed
        self.shared["refs"].add(ref)
        self.shared["units"].add((ref, unit))
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

    def label_at(self, net: str, at: Point, direction: str = "right") -> None:
        """A local net label whose connection point is `at`, text running `direction`."""
        check_grid(f"label {net}", *at)
        angle = 180 if direction == "left" else 0
        justify = [Sym("justify"), Sym("right" if angle == 180 else "left"), Sym("bottom")]
        self.items.append(
            [
                Sym("label"),
                net,
                [Sym("at"), _r(at[0]), _r(at[1]), angle],
                [Sym("fields_autoplaced"), Sym("yes")],
                [Sym("effects"), _font(), justify],
                [Sym("uuid"), self.uuid("label_at", net, _r(at[0]), _r(at[1]))],
            ]
        )

    def power(self, part: Placed, pin: str, net: str, stub: float = 2 * GRID, then=()) -> None:
        """Connect a pin to a rail with a wire stub and a power symbol.

        `then` adds wire moves (dx, dy) after the stub, to clear other pins.
        """
        end, _ = self._stub(part, pin, stub, then)
        self.power_symbol(net, end)

    def power_symbol(self, net: str, at: Point, rot: int = 0) -> Placed:
        self.shared["power"] += 1
        ref = f"#PWR{self.shared['power']:02d}"
        lib = self.power_libs.get(net, "power")
        return self.symbol(f"{lib}:{net}", ref, net, at, rot=rot, hide_ref=True, ref_at="lib",
                           in_bom=False, description=f"Power symbol for the {net} rail")

    def power_flag(self, net: str, at: Point) -> None:
        """Mark a rail as driven, so ERC knows a source feeds it.

        Draws the rail's power symbol at `at`, a short wire and a PWR_FLAG.
        """
        self.shared["flag"] += 1
        ref = f"#FLG{self.shared['flag']:02d}"
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

    def text(self, body: str, at: Point, size: float = 1.27, bold: bool = False) -> None:
        """A text note. The point is the bottom left corner of the first line."""
        font = _font(size)
        if bold:
            font += [[Sym("thickness"), _r(size / 6)], [Sym("bold"), Sym("yes")]]
        self.items.append(
            [
                Sym("text"),
                body,
                [Sym("exclude_from_sim"), Sym("no")],
                [Sym("at"), _r(at[0]), _r(at[1]), 0],
                [Sym("effects"), font, [Sym("justify"), Sym("left"), Sym("bottom")]],
                [Sym("uuid"), self._text_uuid(body, at)],
            ]
        )

    def _text_uuid(self, body: str, at: Point) -> str:
        # The body alone keys the first note with that text; repeats add the position.
        key = ("text", body) if body not in self._texts else ("text", body, _r(at[0]), _r(at[1]))
        self._texts.add(body)
        return self.uuid(*key)

    def global_label(self, part: Placed, pin: str, net: str, shape: str = "passive",
                     stub: float = 2 * GRID, then=()) -> None:
        """Connect a pin to a net that crosses sheets, with a stub and a global label.

        `shape` is one of LABEL_SHAPES, seen from this sheet: "input" for a
        signal that comes in, "output" for one that leaves.
        """
        end, d = self._stub(part, pin, stub, then)
        self.global_label_at(net, end, d, shape, key=(part.ref, pin))

    def global_label_at(self, net: str, at: Point, direction: str = "right", shape: str = "passive",
                        key=None) -> None:
        """A global label whose connection point is `at`, text running `direction`."""
        if shape not in LABEL_SHAPES:
            raise ValueError(f"label shape must be one of {LABEL_SHAPES}, got {shape!r}")
        check_grid(f"global label {net}", *at)
        angle = 180 if direction == "left" else 0
        just = Sym("right" if angle == 180 else "left")
        self.items.append(
            [
                Sym("global_label"),
                net,
                [Sym("shape"), Sym(shape)],
                [Sym("at"), _r(at[0]), _r(at[1]), angle],
                [Sym("fields_autoplaced"), Sym("yes")],
                [Sym("effects"), _font(), [Sym("justify"), just]],
                [Sym("uuid"), self.uuid("global_label", *(key or (net, at[0], at[1])))],
                [
                    Sym("property"), "Intersheetrefs", "${INTERSHEET_REFS}",
                    [Sym("at"), _r(at[0]), _r(at[1]), 0],
                    [Sym("effects"), _font(), [Sym("justify"), just], [Sym("hide"), Sym("yes")]],
                ],
            ]
        )

    def no_connect(self, part: Placed, pin: str) -> None:
        """Mark a pin as left open on purpose. ERC then accepts it."""
        at = part.pin(pin)
        self.items.append([Sym("no_connect"), [Sym("at"), at[0], at[1]],
                           [Sym("uuid"), self.uuid("no_connect", part.ref, pin)]])

    def junction(self, at: Point) -> None:
        """A junction dot. Needed where a wire ends on the middle of another wire."""
        check_grid("junction", *at)
        at = (_r(at[0]), _r(at[1]))
        if at in self._junctions:
            return
        self._junctions.append(at)
        self.items.append([Sym("junction"), [Sym("at"), at[0], at[1]], [Sym("diameter"), 0],
                           [Sym("color"), 0, 0, 0, 0], [Sym("uuid"), self.uuid("junction", *at)]])

    def frame(self, title: str, start: Point, end: Point) -> None:
        """A dashed rectangle around a block, with its title above the top left corner."""
        check_grid(f"frame {title}", *start, *end)
        self.items.append(
            [
                Sym("rectangle"),
                [Sym("start"), _r(start[0]), _r(start[1])],
                [Sym("end"), _r(end[0]), _r(end[1])],
                [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("dash")]],
                [Sym("fill"), [Sym("type"), Sym("none")]],
                [Sym("uuid"), self.uuid("frame", title)],
            ]
        )
        self.text(title, (start[0] + GRID, start[1] - GRID / 2), size=2.0, bold=True)

    def repeat(self, count: int, origin: Point, step: Point, channel: Callable[[int, Point], None]) -> None:
        """Place `count` copies of a channel, the i-th at origin + i * step.

        `channel(i, at)` draws one channel at `at`. Use i in reference and
        net names, such as R1{i} and X0.{i}.
        """
        check_grid("repeat origin", *origin)
        check_grid("repeat step", *step)
        for i in range(count):
            channel(i, (_r(origin[0] + i * step[0]), _r(origin[1] + i * step[1])))

    # -- checks -------------------------------------------------------------

    def _wire_segments(self) -> List[Tuple[Point, Point]]:
        segs = []
        for it in self.items:
            if sexp.tag(it) == "wire":
                pts = sexp.child(it, "pts")
                a, b = pts[1], pts[2]
                segs.append(((float(a[1]), float(a[2])), (float(b[1]), float(b[2]))))
        return segs

    def missing_junctions(self) -> List[Point]:
        """Points where wires form a T or a cross of three or more ends, with no junction.

        A wire end on the middle of another wire needs a junction, and so do
        three or more wire ends at one point. Without the dot KiCad may leave
        the nets apart, and a reader cannot tell a crossing from a join.
        """
        segs = self._wire_segments()
        ends: Dict[Point, int] = {}
        for a, b in segs:
            for p in (a, b):
                ends[p] = ends.get(p, 0) + 1
        need = set()
        for p, n in ends.items():
            if n >= 3:
                need.add(p)
            for a, b in segs:
                if p != a and p != b and _inside(p, a, b):
                    need.add(p)
        have = set(self._junctions)
        return sorted(p for p in need if p not in have)

    # -- output -------------------------------------------------------------

    def _with_instance(self, node: list) -> list:
        ref = next(p[2] for p in sexp.children(node, "property") if p[1] == "Reference")
        unit = sexp.value(node, "unit")
        return node + [
            [
                Sym("instances"),
                [
                    Sym("project"),
                    self.project,
                    [Sym("path"), self.instance_path, [Sym("reference"), ref], [Sym("unit"), unit]],
                ],
            ]
        ]

    def tree(self) -> list:
        missing = self.missing_junctions()
        if missing:
            raise ValueError(f"sheet {self.sheet or 'root'}: wires meet without a junction at {missing}")
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
            + [self._with_instance(s) for s in self.symbols]
            + self._tail()
        )

    def _tail(self) -> list:
        # Only the root file carries sheet_instances. A sub-sheet file has none.
        if self.sheet is None:
            return [
                [Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]],
                [Sym("embedded_fonts"), Sym("no")],
            ]
        return [[Sym("embedded_fonts"), Sym("no")]]

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


def _inside(p: Point, a: Point, b: Point) -> bool:
    """True when p lies on the axis-parallel segment a-b, strictly between its ends."""
    (x, y), (ax, ay), (bx, by) = p, a, b
    if ax == bx == x:
        return min(ay, by) < y < max(ay, by)
    if ay == by == y:
        return min(ax, bx) < x < max(ax, bx)
    return False


# ---------------------------------------------------------------------------
# Hierarchy


class Hierarchy:
    """A root sheet with one sheet symbol per block, each block in its own file.

    The root sheet shows the blocks as boxes. Each block sheet is a
    `Schematic` with its own title block. Reference designators and power
    symbol numbers are unique across the design.
    """

    def __init__(self, project: str, board: str, date: str, rev: str,
                 comments: Optional[List[str]] = None, libs: Optional[SymbolLibs] = None,
                 paper: str = "A4", power_libs: Optional[Dict[str, str]] = None):
        self.project = project
        self.board = board
        self.date = date
        self.rev = rev
        self.libs = libs or SymbolLibs()
        self.paper = paper
        self.shared: dict = {"refs": set(), "units": set(), "power": 0, "flag": 0}
        self.power_libs = power_libs or {}
        self.comments = comments or []
        self.root = Schematic(project, title=board, date=date, rev=rev,
                              comments=[PROPOSAL] + self.comments, libs=self.libs,
                              paper=paper, shared=self.shared, power_libs=self.power_libs)
        self.sheets: List[Tuple[str, str, Schematic]] = []

    def sheet(self, name: str, file: str, at: Point, size: Point = (g(30), g(12)),
              paper: Optional[str] = None, notes: str = "") -> Schematic:
        """Add a block: a sheet symbol on the root at `at`, and its own file.

        `notes` is a short text drawn inside the sheet symbol, such as the
        parts and nets the block holds.
        """
        if any(n == name for n, _, _ in self.sheets):
            raise ValueError(f"duplicate sheet name {name}")
        if any(f == file for _, f, _ in self.sheets):
            raise ValueError(f"duplicate sheet file {file}")
        check_grid(f"sheet {name}", *at, *size)
        page = str(len(self.sheets) + 2)
        sheet_uuid = self.root.uuid("sheet", name)
        child = Schematic(self.project, title=f"{name}", date=self.date, rev=self.rev,
                          comments=[self.board, PROPOSAL] + self.comments, libs=self.libs,
                          paper=paper or self.paper, sheet=name, shared=self.shared,
                          power_libs=self.power_libs)
        child.instance_path = f"/{self.root.root}/{sheet_uuid}"
        x, y = at
        w, h = size
        self.root.items.append(
            [
                Sym("sheet"),
                [Sym("at"), _r(x), _r(y)],
                [Sym("size"), _r(w), _r(h)],
                [Sym("exclude_from_sim"), Sym("no")],
                [Sym("in_bom"), Sym("yes")],
                [Sym("on_board"), Sym("yes")],
                [Sym("dnp"), Sym("no")],
                [Sym("fields_autoplaced"), Sym("yes")],
                [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]],
                [Sym("uuid"), sheet_uuid],
                [Sym("property"), "Sheetname", name, [Sym("at"), _r(x), _r(y - 0.7116), 0],
                 [Sym("effects"), _font(), [Sym("justify"), Sym("left"), Sym("bottom")]]],
                [Sym("property"), "Sheetfile", file, [Sym("at"), _r(x), _r(y + h + 0.5984), 0],
                 [Sym("effects"), _font(), [Sym("justify"), Sym("left"), Sym("top")]]],
                [Sym("instances"), [Sym("project"), self.project,
                                    [Sym("path"), f"/{self.root.root}", [Sym("page"), page]]]],
            ]
        )
        if notes:
            self.root.text(notes, (x + GRID, y + (3 + 2 * notes.count("\n")) * GRID))
        self.sheets.append((name, file, child))
        return child

    def files(self) -> Dict[str, str]:
        """{file name: text} for the root and every block sheet."""
        out = {f"{self.project}.kicad_sch": self.root.text_out()}
        for _, file, child in self.sheets:
            out[file] = child.text_out()
        return out

    def write(self, folder: str) -> None:
        for name, text in self.files().items():
            write_if_changed(os.path.join(folder, name), text)

    def stock_libs(self) -> List[str]:
        libs = set(self.root.stock_libs())
        for _, _, child in self.sheets:
            libs.update(child.stock_libs())
        return sorted(libs)


def _pin_key(num: str):
    return (0, int(num), "") if num.isdigit() else (1, 0, num)
