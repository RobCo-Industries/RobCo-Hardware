#!/usr/bin/env python3
"""Check a board's header pins against its netlist and the software's pin table.

    check_pins.py --pins spec/pins.yaml [--netlist board.net] [--board-support BOARD_SUPPORT.md]

With `--netlist`, every header pin in `pins.yaml` must carry the same net in
the netlist, and every connected header pin in the netlist must be listed.

With `--board-support`, every GPIO that the software uses, as listed in the
"Pins" section of RobCo-Core `docs/spec/BOARD_SUPPORT.md`, must have the same
use in `pins.yaml`. On a `pi40` header, every such GPIO must be present, and
each pin name must match the Raspberry Pi pin at that number.

Exit codes. With several kinds of difference, the lowest code wins.
    0   no difference
    2   bad arguments or unreadable input
    10  a header pin has another net in the netlist
    11  a header pin is in one of netlist or pins.yaml but not in the other
    12  pins.yaml gives a GPIO another use than the software
    13  a GPIO the software uses is missing from a pi40 pins.yaml
    14  a pin name does not match the Raspberry Pi pin at that number

Runs on Python 3.9 or later, with the standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import netlist as netlist_mod  # noqa: E402

OK = 0
USAGE = 2
WRONG_NET = 10
MISSING_PIN = 11
WRONG_USE = 12
MISSING_USE = 13
WRONG_NAME = 14

# Raspberry Pi 40-pin header: pin number to name.
PI40 = {
    1: "3V3", 2: "5V", 3: "GPIO2", 4: "5V", 5: "GPIO3", 6: "GND", 7: "GPIO4", 8: "GPIO14",
    9: "GND", 10: "GPIO15", 11: "GPIO17", 12: "GPIO18", 13: "GPIO27", 14: "GND", 15: "GPIO22",
    16: "GPIO23", 17: "3V3", 18: "GPIO24", 19: "GPIO10", 20: "GND", 21: "GPIO9", 22: "GPIO25",
    23: "GPIO11", 24: "GPIO8", 25: "GND", 26: "GPIO7", 27: "GPIO0", 28: "GPIO1", 29: "GPIO5",
    30: "GND", 31: "GPIO6", 32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16",
    37: "GPIO26", 38: "GPIO20", 39: "GND", 40: "GPIO21",
}
ALIASES = {"ID_SD": "GPIO0", "ID_SC": "GPIO1", "3.3V": "3V3", "+3V3": "3V3", "+5V": "5V"}
HEADER_GPIOS = range(0, 28)
"""GPIO 0 to 27 reach the 40-pin header. Higher numbers are internal."""

NC_NETS = {"", "NC", "none"}


class Problem:
    def __init__(self, code: int, text: str):
        self.code = code
        self.text = text

    def __repr__(self) -> str:
        return f"Problem({self.code}, {self.text!r})"


class InputError(Exception):
    pass


# ---------------------------------------------------------------------------
# pins.yaml: a small YAML subset, so the check needs no third-party module.


def _scalar(text: str):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def _strip_comment(line: str) -> str:
    if line.lstrip().startswith("#"):
        return ""
    return re.sub(r"\s+#.*$", "", line).rstrip()


def parse_pins_yaml(text: str) -> dict:
    """Parse the pins.yaml shape: top-level keys and a `pins:` list of maps."""
    data: dict = {}
    current: Optional[dict] = None
    in_list = False
    for n, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if indent == 0:
            key, sep, val = body.partition(":")
            if not sep:
                raise InputError(f"line {n}: expected 'key: value'")
            if val.strip():
                data[key.strip()] = _scalar(val)
                in_list = False
            else:
                data[key.strip()] = []
                in_list = True
            continue
        if not in_list:
            raise InputError(f"line {n}: unexpected indent")
        if body.startswith("- "):
            current = {}
            data[list(data)[-1]].append(current)
            body = body[2:]
        if current is None:
            raise InputError(f"line {n}: list item expected")
        key, sep, val = body.partition(":")
        if not sep:
            raise InputError(f"line {n}: expected 'key: value'")
        current[key.strip()] = _scalar(val)
    return data


class PinEntry:
    def __init__(self, pin: int, name: str, net: str, use: str, source: str):
        self.pin, self.name, self.net, self.use, self.source = pin, name, net, use, source

    @property
    def gpio(self) -> Optional[int]:
        m = re.fullmatch(r"GPIO(\d+)", ALIASES.get(self.name, self.name))
        return int(m.group(1)) if m else None


class PinMap:
    def __init__(self, board: str, connector: str, header: str, pins: List[PinEntry], ignore: List[str]):
        self.board, self.connector, self.header, self.pins, self.ignore = board, connector, header, pins, ignore


def load_pins(path: str) -> PinMap:
    with open(path, encoding="utf-8") as fh:
        data = parse_pins_yaml(fh.read())
    for key in ("board", "connector", "header", "pins"):
        if key not in data:
            raise InputError(f"{path}: missing '{key}'")
    if data["header"] not in ("pi40", "generic"):
        raise InputError(f"{path}: header must be pi40 or generic")
    entries = []
    seen = set()
    for item in data["pins"]:
        for key in ("pin", "name", "net", "use"):
            if key not in item:
                raise InputError(f"{path}: a pin entry has no '{key}'")
        if item["pin"] in seen:
            raise InputError(f"{path}: pin {item['pin']} is listed twice")
        seen.add(item["pin"])
        entries.append(PinEntry(int(item["pin"]), str(item["name"]), str(item["net"]),
                                str(item["use"]), str(item.get("source", ""))))
    ignore = data.get("ignore_sources", [])
    return PinMap(str(data["board"]), str(data["connector"]), str(data["header"]), entries, ignore)


# ---------------------------------------------------------------------------
# BOARD_SUPPORT.md: the tables in its "Pins" section.

SoftwareUse = Dict[int, List[Tuple[str, str]]]
"""{gpio: [(use, source table)]}"""


def _gpio_list(cell: str) -> List[int]:
    """'GPIO 7, 8, 9' or 'GPIO 34 to 39, 48 to 53' to a list of numbers."""
    m = re.match(r"^\s*GPIO\s+(.*)$", cell)
    if not m:
        return []
    text = re.sub(r"\s+at\s+ALT\d+.*$", "", m.group(1))
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        rng = re.fullmatch(r"(\d+)\s+to\s+(\d+)", part)
        if rng:
            out.extend(range(int(rng.group(1)), int(rng.group(2)) + 1))
        elif re.fullmatch(r"\d+", part):
            out.append(int(part))
    return out


def _functions(cell: str, count: int) -> List[str]:
    """'PL011 TXD, RXD at ALT0' with 2 pins to ['PL011 TXD', 'PL011 RXD']."""
    text = cell.split(". ")[0].rstrip(".")
    text = re.sub(r"\s+at\s+ALT\d+$", "", text.strip())
    names = [x.strip() for x in text.split(",")]
    if len(names) != count:
        return [text] * count
    first = names[0].split()
    prefix = " ".join(first[:-1])
    return [names[0]] + [n if " " in n or not prefix else f"{prefix} {n}" for n in names[1:]]


def _tables(lines: List[str]) -> List[List[List[str]]]:
    tables: List[List[List[str]]] = []
    current: List[List[str]] = []
    for line in lines + [""]:
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def parse_board_support(text: str) -> SoftwareUse:
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Pins")
    except StopIteration:
        raise InputError("BOARD_SUPPORT.md has no '## Pins' section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    uses: SoftwareUse = {}

    def add(gpio: int, use: str, source: str) -> None:
        if gpio in HEADER_GPIOS:
            uses.setdefault(gpio, [])
            if (use, source) not in uses[gpio]:
                uses[gpio].append((use, source))

    for table in _tables(lines[start:end]):
        head, rows = table[0], table[1:]
        if head[:2] == ["Pins", "Function"]:
            for row in rows:
                gpios = _gpio_list(row[0])
                for g, f in zip(gpios, _functions(row[1], len(gpios))):
                    add(g, f, "Pins")
        elif head and head[0] == "Board":
            for row in rows:
                for col in range(1, len(head)):
                    for g in _gpio_list(row[col]):
                        add(g, head[col], "Audio channels")
        elif head and head[0] == "Input":
            for row in rows:
                for col in range(0, len(row) - 1, 2):
                    if row[col]:
                        for g in _gpio_list(row[col + 1]):
                            add(g, row[col], "Input example")
    if not uses:
        raise InputError("no GPIO found in the 'Pins' section")
    return uses


# ---------------------------------------------------------------------------
# Checks


def check_netlist(pm: PinMap, nl: netlist_mod.Netlist) -> List[Problem]:
    problems: List[Problem] = []
    ref = pm.connector
    if ref not in nl.components:
        return [Problem(MISSING_PIN, f"connector {ref} is not in the netlist")]
    pin_net = {pin: netlist_mod.short_net(net) for (r, pin), net in nl.pin_net().items() if r == ref}
    listed = {str(e.pin) for e in pm.pins}
    for e in pm.pins:
        got = pin_net.get(str(e.pin))
        if got is None:
            if e.net not in NC_NETS:
                problems.append(Problem(MISSING_PIN, f"{ref} pin {e.pin}: in pins.yaml but not in the netlist"))
            continue
        if got.startswith("unconnected-") and e.net in NC_NETS:
            continue
        if got != e.net:
            problems.append(Problem(WRONG_NET, f"{ref} pin {e.pin}: netlist has net '{got}', pins.yaml says '{e.net}'"))
    for pin in sorted(set(pin_net) - listed, key=lambda p: (len(p), p)):
        if not pin_net[pin].startswith("unconnected-"):
            problems.append(Problem(MISSING_PIN, f"{ref} pin {pin}: net '{pin_net[pin]}' in the netlist but not in pins.yaml"))
    return problems


def check_software(pm: PinMap, uses: SoftwareUse) -> List[Problem]:
    problems: List[Problem] = []
    by_gpio: Dict[int, PinEntry] = {}
    for e in pm.pins:
        if e.gpio is not None:
            by_gpio[e.gpio] = e
        if pm.header == "pi40":
            want = PI40.get(e.pin)
            have = ALIASES.get(e.name, e.name)
            if want is None:
                problems.append(Problem(WRONG_NAME, f"pin {e.pin}: no such pin on a 40-pin header"))
            elif have != want:
                problems.append(Problem(WRONG_NAME, f"pin {e.pin}: named '{e.name}', the Pi has '{want}' there"))
    for gpio in sorted(uses):
        wanted = [(u, s) for u, s in uses[gpio] if s not in pm.ignore]
        if not wanted:
            continue
        names = [u for u, _ in wanted]
        e = by_gpio.get(gpio)
        if e is None:
            if pm.header == "pi40":
                src = ", ".join(sorted({s for _, s in wanted}))
                problems.append(Problem(MISSING_USE, f"GPIO{gpio}: used by the software as {' or '.join(repr(n) for n in names)} ({src}), missing from pins.yaml"))
            continue
        if e.use not in names:
            problems.append(Problem(WRONG_USE, f"GPIO{gpio} (pin {e.pin}): the software uses it as {' or '.join(repr(n) for n in names)}, pins.yaml says '{e.use}'"))
    return problems


def run(pins: str, net: Optional[str], board_support: Optional[str]) -> Tuple[int, List[Problem]]:
    pm = load_pins(pins)
    problems: List[Problem] = []
    if net:
        problems += check_netlist(pm, netlist_mod.load(net))
    if board_support:
        with open(board_support, encoding="utf-8") as fh:
            problems += check_software(pm, parse_board_support(fh.read()))
    code = min((p.code for p in problems), default=OK)
    return code, problems


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pins", required=True, help="the board's spec/pins.yaml")
    ap.add_argument("--netlist", help="netlist from kicad-cli sch export netlist")
    ap.add_argument("--board-support", help="path to RobCo-Core docs/spec/BOARD_SUPPORT.md")
    args = ap.parse_args(argv)
    if not args.netlist and not args.board_support:
        ap.error("give --netlist, --board-support or both")
    try:
        code, problems = run(args.pins, args.netlist, args.board_support)
    except (OSError, InputError, ValueError) as exc:
        print(f"check_pins: error: {exc}", file=sys.stderr)
        return USAGE
    for p in problems:
        print(f"check_pins: [{p.code}] {p.text}", file=sys.stderr)
    if code == OK:
        checked = [x for x, on in (("netlist", args.netlist), ("software pin table", args.board_support)) if on]
        print(f"check_pins: {args.pins}: no difference with the {' and the '.join(checked)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
