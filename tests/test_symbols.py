"""The own symbol library equals a fresh generation and keeps its proposal notes."""

import os

import gen_symbols
import sexp
from conftest import ROOT
from sch import SymbolLibs, lib_pins

LIB = os.path.join(ROOT, "lib", "RobCo.kicad_sym")


def test_library_equals_generation():
    text = sexp.dump_file(gen_symbols.library(SymbolLibs()))
    with open(LIB, encoding="utf-8") as fh:
        assert fh.read() == text, "lib/RobCo.kicad_sym differs: run tools/gen_symbols.py"


def _sym(name):
    return SymbolLibs().get(f"RobCo:{name}")


def _pins(sym):
    out = {}
    for unit in sexp.children(sym, "symbol"):
        for p in sexp.children(unit, "pin"):
            out[sexp.value(p, "number")] = sexp.value(p, "name")
    return out


def test_pca9554_pinout():
    pins = _pins(_sym("PCA9554"))
    want = {"1": "A0", "2": "A1", "3": "A2", "4": "P0", "5": "P1", "6": "P2", "7": "P3", "8": "VSS",
            "9": "P4", "10": "P5", "11": "P6", "12": "P7", "13": "~{INT}", "14": "SCL", "15": "SDA",
            "16": "VDD"}
    assert pins == want


def test_ds1338_pinout():
    pins = _pins(_sym("DS1338"))
    assert pins == {"1": "X1", "2": "X2", "3": "VBAT", "4": "GND", "5": "SDA", "6": "SCL",
                    "7": "SQW/OUT", "8": "VCC"}


def test_fields_mark_the_proposal():
    for name, fp in (("PCA9554", "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm"),
                     ("DS1338", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")):
        sym = _sym(name)
        props = {p[1]: p[2] for p in sexp.children(sym, "property")}
        assert props["Footprint"] == fp
        assert "To check against the data sheet" in props["Description"]
        assert props["Status"].startswith("Proposal, pinout to verify")
        assert lib_pins(sym)
