"""Shared helpers: stable UUIDs, the 1.27 mm grid, library paths.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

GRID = 1.27
"""The schematic grid in millimetres. Every pin end must sit on it."""

_NAMESPACE = uuid.UUID("6f1d8a52-2b0e-4c8e-9a51-52b0c0c0ffee")


def stable_uuid(seed: str, *path: object) -> str:
    """Return a UUID derived from a seed and an item path.

    The same seed and path always give the same UUID, so a regenerated file
    is byte-identical to the last one.
    """
    key = "/".join([seed] + [str(p) for p in path])
    return str(uuid.uuid5(_NAMESPACE, key))


class GridError(ValueError):
    pass


def g(n: float) -> float:
    """Return n grid steps in millimetres."""
    return round(n * GRID, 4)


def on_grid(v: float) -> bool:
    return abs(v / GRID - round(v / GRID)) < 1e-6


def snap(v: float) -> float:
    """Round a value to the nearest grid point."""
    return round(round(v / GRID) * GRID, 4)


def check_grid(what: str, *values: float) -> None:
    """Raise GridError when a value is off the grid."""
    for v in values:
        if not on_grid(v):
            raise GridError(f"{what}: {v} mm is not on the {GRID} mm grid")


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""The repository root."""

_STOCK_ROOTS = [
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport",
    "/usr/share/kicad",
    "/usr/local/share/kicad",
]


def stock_dir(kind: str) -> str:
    """Find a stock library folder: symbols, footprints or 3dmodels.

    `KICAD10_SYMBOL_DIR`, `KICAD10_FOOTPRINT_DIR` and `KICAD10_3DMODEL_DIR`
    override the search.
    """
    env = {
        "symbols": "KICAD10_SYMBOL_DIR",
        "footprints": "KICAD10_FOOTPRINT_DIR",
        "3dmodels": "KICAD10_3DMODEL_DIR",
    }[kind]
    val = os.environ.get(env)
    if val:
        return val
    for root in _STOCK_ROOTS:
        path = os.path.join(root, kind)
        if os.path.isdir(path):
            return path
    raise FileNotFoundError(f"no stock {kind} folder found; set {env}")


def own_lib_dir() -> str:
    return os.path.join(REPO, "lib")


def write_if_changed(path: str, text: str) -> bool:
    """Write text to path. Return True when the content changed."""
    old: Optional[str] = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
    if old == text:
        return False
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return True
