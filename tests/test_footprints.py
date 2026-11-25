"""Every footprint a committed schematic names exists in a library.

Own footprints must be in lib/RobCo.pretty. Stock footprints are checked
only where a stock footprint folder exists, as on a Mac with KiCad or in
the KiCad CI image; the plain Python job skips them.
"""

import glob
import os
import re

import pytest

import sexp
from conftest import ROOT

STOCK_ROOTS = ["/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
               "/usr/share/kicad/footprints", "/usr/local/share/kicad/footprints"]
OWN = os.path.join(ROOT, "lib", "RobCo.pretty")


def _named():
    names = set()
    for path in glob.glob(os.path.join(ROOT, "*", "kicad", "*.kicad_sch")):
        with open(path, encoding="utf-8") as fh:
            names.update(re.findall(r'\(property "Footprint" "([^"]+)"', fh.read()))
    return sorted(names)


def _stock():
    for root in STOCK_ROOTS:
        if os.path.isdir(root):
            return root
    return None


@pytest.mark.parametrize("fpid", [n for n in _named() if n.startswith("RobCo:")])
def test_own_footprint_exists_and_parses(fpid):
    path = os.path.join(OWN, fpid.split(":", 1)[1] + ".kicad_mod")
    assert os.path.isfile(path), f"{fpid} missing from lib/RobCo.pretty"
    with open(path, encoding="utf-8") as fh:
        tree = sexp.parse(fh.read())
    assert sexp.tag(tree) == "footprint"
    descr = sexp.value(tree, "descr", "")
    assert "to verify" in descr, f"{fpid}: dimensions from memory must say 'to verify'"
    layers = [sexp.value(c, "layer") for c in sexp.children(tree, "fp_rect")]
    assert "F.CrtYd" in layers, f"{fpid} has no courtyard"


def _pads(name):
    with open(os.path.join(OWN, name + ".kicad_mod"), encoding="utf-8") as fh:
        tree = sexp.parse(fh.read())
    return [c[1] for c in sexp.children(tree, "pad")]


def test_amplifier_module_footprint_has_two_edges():
    """M1: 5 input pads in one row, 2 output pads on the opposite edge. The old 1x07 row is gone."""
    assert not glob.glob(os.path.join(OWN, "PAM8302A_Module_1x07*"))
    assert all("PAM8302A_Module_1x07" not in n for n in _named())
    pads = _pads("PAM8302A_Module_In1x05_P2.54mm_Out1x02_P3.50mm")
    assert sorted(pads) == ["1", "2", "3", "4", "5", "6", "7"]


def test_10mm_fuse_names_both_parts():
    with open(os.path.join(OWN, "Fuse_PTC_Radial_W10.0mm_T3.5mm_P5.10mm.kicad_mod"), encoding="utf-8") as fh:
        descr = sexp.value(sexp.parse(fh.read()), "descr", "")
    assert "RXEF110" in descr and "MF-R090" in descr


@pytest.mark.parametrize("fpid", [n for n in _named() if not n.startswith("RobCo:")])
def test_stock_footprint_exists(fpid):
    root = _stock()
    if root is None:
        pytest.skip("no stock footprint folder here")
    lib, name = fpid.split(":", 1)
    assert os.path.isfile(os.path.join(root, f"{lib}.pretty", f"{name}.kicad_mod")), f"{fpid} not in {root}"
