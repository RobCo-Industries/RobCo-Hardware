#!/usr/bin/env python3
"""List the 3D models a board file references and report the missing ones.

    check_models.py BOARD.kicad_pcb

Resolves `${KICAD10_3DMODEL_DIR}` (and the older `${KICAD*_3DMODEL_DIR}`
names) from the environment and `${KIPRJMOD}` from the board's folder. A
model with a `.wrl` path also counts as found when the `.step` file of the
same name exists, as KiCad substitutes one for the other.

Prints one `::warning::` line per missing model and one with the count, so a
GitHub Actions run shows them. Exit 0 always, unless the board file cannot be
read (exit 2): a render with bare pads is a warning, not a failure.

Runs on Python 3.9 or later, with the standard library only.
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Optional, Tuple

_VAR = re.compile(r"\$\{([A-Z0-9_]+)\}")


def model_paths(text: str) -> List[str]:
    """The model paths in a board file, in order, without repeats."""
    seen: List[str] = []
    for m in re.finditer(r'\(model\s+"([^"]+)"', text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def resolve(path: str, board_dir: str) -> Optional[str]:
    """Expand the variables in a model path. None when a variable is unset."""
    def sub(m: "re.Match[str]") -> str:
        name = m.group(1)
        if name == "KIPRJMOD":
            return board_dir
        if re.fullmatch(r"KICAD\d*_3DMODEL_DIR", name):
            val = os.environ.get("KICAD10_3DMODEL_DIR") or os.environ.get(name)
        else:
            val = os.environ.get(name)
        if not val:
            raise KeyError(name)
        return val

    try:
        return _VAR.sub(sub, path)
    except KeyError:
        return None


def exists(path: str) -> bool:
    if os.path.isfile(path):
        return True
    stem, ext = os.path.splitext(path)
    alt = {".wrl": ".step", ".step": ".wrl", ".stp": ".wrl"}.get(ext.lower())
    return bool(alt) and os.path.isfile(stem + alt)


def check(board: str) -> Tuple[List[str], List[str]]:
    """Return (referenced, missing) model paths of a board file."""
    with open(board, encoding="utf-8") as fh:
        paths = model_paths(fh.read())
    board_dir = os.path.dirname(os.path.abspath(board))
    missing = []
    for p in paths:
        real = resolve(p, board_dir)
        if real is None or not exists(real):
            missing.append(p)
    return paths, missing


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: check_models.py BOARD.kicad_pcb", file=sys.stderr)
        return 2
    try:
        paths, missing = check(argv[0])
    except OSError as exc:
        print(f"check_models: error: {exc}", file=sys.stderr)
        return 2
    for p in missing:
        print(f"::warning::3D model not found: {p}")
    if missing:
        print(f"::warning::{len(missing)} of {len(paths)} 3D models missing: the renders show bare pads for them")
    else:
        print(f"check_models: all {len(paths)} 3D models found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
