"""Read and write KiCad S-expressions.

A list becomes a Python list. A bare atom becomes a `Sym`. A quoted atom
becomes a plain `str`. Bare atoms keep their exact text, so a file read and
written again keeps its numbers as they were.

The writer follows the KiCad layout: tabs for indent, a list whose items are
all atoms on one line, and every child list on its own line.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

import math
from typing import Any, List


class Sym(str):
    """A bare atom, such as a keyword or a number."""

    def __repr__(self) -> str:
        return f"Sym({str.__repr__(self)})"


class SexpError(ValueError):
    pass


_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}


def parse(text: str) -> Any:
    """Parse one S-expression and return it."""
    node, pos = _parse_at(text, _skip(text, 0))
    pos = _skip(text, pos)
    if pos != len(text):
        raise SexpError(f"trailing data at offset {pos}")
    return node


def _skip(text: str, pos: int) -> int:
    n = len(text)
    while pos < n and text[pos] in " \t\r\n":
        pos += 1
    return pos


def _parse_at(text: str, pos: int):
    if pos >= len(text):
        raise SexpError("unexpected end of input")
    if text[pos] != "(":
        raise SexpError(f"expected '(' at offset {pos}")
    stack: List[list] = [[]]
    pos += 1
    n = len(text)
    while True:
        pos = _skip(text, pos)
        if pos >= n:
            raise SexpError("unbalanced parentheses")
        c = text[pos]
        if c == "(":
            stack.append([])
            pos += 1
        elif c == ")":
            done = stack.pop()
            pos += 1
            if not stack:
                return done, pos
            stack[-1].append(done)
        elif c == '"':
            pos += 1
            out = []
            while True:
                if pos >= n:
                    raise SexpError("unterminated string")
                c = text[pos]
                if c == "\\":
                    nxt = text[pos + 1] if pos + 1 < n else ""
                    out.append(_ESCAPES.get(nxt, nxt))
                    pos += 2
                elif c == '"':
                    pos += 1
                    break
                else:
                    out.append(c)
                    pos += 1
            stack[-1].append("".join(out))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            stack[-1].append(Sym(text[start:pos]))


def fmt_num(v: float) -> str:
    """Format a number the way KiCad does: no trailing zeros, no -0."""
    if isinstance(v, bool):
        raise TypeError("bool is not a number here")
    if isinstance(v, int):
        return str(v)
    if not math.isfinite(v):
        raise ValueError(f"not a finite number: {v}")
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _atom(v: Any) -> str:
    if isinstance(v, Sym):
        return str(v)
    if isinstance(v, str):
        s = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{s}"'
    if isinstance(v, (int, float)):
        return fmt_num(v)
    raise TypeError(f"cannot write {type(v).__name__}: {v!r}")


WRAP_COLUMN = 72
"""KiCad wraps a run of atoms once a line passes this column."""

XY_WRAP_COLUMN = 99
"""KiCad packs `xy` points on one line up to this column."""


def _col(line: str) -> int:
    return len(line)


def dumps(node: Any, indent: int = 0) -> str:
    """Write a node in the KiCad layout, with no final newline."""
    if not isinstance(node, list):
        return _atom(node)
    pad = "\t" * indent
    inner = "\t" * (indent + 1)
    lines: List[str] = [pad + "("]
    first = True
    i = 0
    n = len(node)
    # Leading atoms share the opening line and wrap past the column.
    while i < n and not isinstance(node[i], list):
        tok = _atom(node[i])
        if first:
            lines[-1] += tok
            first = False
        elif _col(lines[-1]) > WRAP_COLUMN:
            lines.append(inner + tok)
        else:
            lines[-1] += " " + tok
        i += 1
    if i == n:
        if len(lines) > 1:
            lines.append(pad + ")")
            return "\n".join(lines)
        return lines[0] + ")"
    prev_xy = False
    while i < n:
        item = node[i]
        if isinstance(item, list):
            is_xy = tag(item) == "xy" and all(not isinstance(x, list) for x in item)
            text = dumps(item, indent + 1)
            if is_xy and prev_xy and _col(lines[-1]) < XY_WRAP_COLUMN:
                lines[-1] += " " + text.lstrip("\t")
            else:
                lines.append(text)
            prev_xy = is_xy
        else:
            lines.append(inner + _atom(item))
            prev_xy = False
        i += 1
    lines.append(pad + ")")
    return "\n".join(lines)


def dump_file(node: Any) -> str:
    return dumps(node) + "\n"


def load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return parse(fh.read())


# Helpers to walk parsed trees.

def tag(node: Any) -> str:
    return str(node[0]) if isinstance(node, list) and node else ""


def children(node: list, name: str) -> List[list]:
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def child(node: list, name: str):
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def value(node: list, name: str, default: Any = None) -> Any:
    c = child(node, name)
    return c[1] if c is not None and len(c) > 1 else default
