"""Write the KiCad project files: `.kicad_pro`, `sym-lib-table`, `fp-lib-table`.

The design rules follow the plan's decision for a low-cost 2-layer service.
They are assumed values, to check against the chosen service.

Runs on Python 3.9 so KiCad's bundled Python can import it.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional

from common import write_if_changed

# Plan decision "Design rules". Millimetres.
RULES: Dict[str, float] = {
    "board_thickness": 1.6,
    "copper_thickness": 0.035,  # 1 oz
    "track_width": 0.2,
    "clearance": 0.2,
    "via_drill": 0.4,
    "via_diameter": 0.8,
    "min_hole": 0.3,
    "edge_clearance": 0.5,
    "silk_text_height": 1.0,
}


def kicad_pro(name: str, rules: Dict[str, float] = RULES, erc_severities: Optional[Dict[str, str]] = None) -> str:
    """Return the `.kicad_pro` JSON text with the design rules.

    `erc_severities` sets ERC rule severities, such as
    {"isolated_pin_label": "ignore"}, for a board drawn in steps.
    """
    annular = round((rules["via_diameter"] - rules["via_drill"]) / 2, 4)
    data = {
        "board": {
            "design_settings": {
                "defaults": {},
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": {
                    "min_clearance": rules["clearance"],
                    "min_copper_edge_clearance": rules["edge_clearance"],
                    "min_hole_clearance": rules["clearance"],
                    "min_hole_to_hole": 0.25,
                    "min_text_height": rules["silk_text_height"],
                    "min_through_hole_diameter": rules["min_hole"],
                    "min_track_width": rules["track_width"],
                    "min_via_annular_width": annular,
                    "min_via_diameter": rules["via_diameter"],
                },
                "track_widths": [0.0, rules["track_width"], 0.4],
                "via_dimensions": [
                    {"diameter": 0.0, "drill": 0.0},
                    {"diameter": rules["via_diameter"], "drill": rules["via_drill"]},
                ],
            }
        },
        "boards": [],
        **({"erc": {"rule_severities": dict(erc_severities)}} if erc_severities else {}),
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{name}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": rules["clearance"],
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "priority": 2147483647,
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": rules["track_width"],
                    "via_diameter": rules["via_diameter"],
                    "via_drill": rules["via_drill"],
                    "wire_width": 6,
                }
            ],
            "meta": {"version": 4},
        },
        "pcbnew": {"page_layout_descr_file": ""},
        "sheets": [],
        "text_variables": {},
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def sym_lib_table(stock: Iterable[str], own: bool = True) -> str:
    rows = [
        f'\t(lib (name "{n}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{n}.kicad_sym")(options "")(descr ""))'
        for n in sorted(set(stock))
    ]
    if own:
        rows.append('\t(lib (name "RobCo")(type "KiCad")(uri "${KIPRJMOD}/../../lib/RobCo.kicad_sym")(options "")(descr "RobCo own symbols"))')
    return "(sym_lib_table\n\t(version 7)\n" + "\n".join(rows) + "\n)\n"


def fp_lib_table(stock: Iterable[str], own: bool = True) -> str:
    rows = [
        f'\t(lib (name "{n}")(type "KiCad")(uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty")(options "")(descr ""))'
        for n in sorted(set(stock))
    ]
    if own:
        rows.append('\t(lib (name "RobCo")(type "KiCad")(uri "${KIPRJMOD}/../../lib/RobCo.pretty")(options "")(descr "RobCo own footprints"))')
    return "(fp_lib_table\n\t(version 7)\n" + "\n".join(rows) + "\n)\n"


def write_project(folder: str, name: str, sym_libs: Iterable[str], fp_libs: Iterable[str],
                  erc_severities: Optional[Dict[str, str]] = None) -> None:
    """Write the three project files into folder."""
    sym = [s for s in sym_libs if s != "RobCo"]
    fp = [f for f in fp_libs if f != "RobCo"]
    write_if_changed(os.path.join(folder, f"{name}.kicad_pro"), kicad_pro(name, erc_severities=erc_severities))
    write_if_changed(os.path.join(folder, "sym-lib-table"), sym_lib_table(sym))
    write_if_changed(os.path.join(folder, "fp-lib-table"), fp_lib_table(fp))
