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


def test_pmos_gds_pad_order():
    pins = _pins(_sym("Q_PMOS_GDS"))
    assert pins == {"1": "G", "2": "D", "3": "S"}


def test_tvs_unidirectional_has_cathode_and_anode():
    assert _pins(_sym("D_TVS_Unidir")) == {"1": "K", "2": "A"}


def test_pam8302a_module_pins_are_named_and_shown():
    sym = _sym("PAM8302A_Module")
    assert _pins(sym) == {"1": "VIN", "2": "GND", "3": "SD", "4": "A+", "5": "A-", "6": "OUT+", "7": "OUT-"}
    assert sexp.child(sexp.child(sym, "pin_names"), "hide") is None
    body = sexp.children(sexp.children(sym, "symbol")[0], "rectangle")[0]
    assert float(sexp.child(body, "end")[1]) == 10.16


def test_own_power_symbols_name_their_rail():
    for name in ("V_PROT", "V_SW", "+V_S"):
        sym = _sym(name)
        props = {p[1]: p[2] for p in sexp.children(sym, "property")}
        assert props["Value"] == name
        assert sexp.child(sym, "power") is not None


def test_pmos_sot23_pad_order():
    sym = _sym("Q_PMOS_GSD_SOT23")
    assert _pins(sym) == {"1": "G", "2": "S", "3": "D"}
    props = {p[1]: p[2] for p in sexp.children(sym, "property")}
    assert props["Footprint"] == "Package_TO_SOT_SMD:SOT-23"
    assert "to verify" in props["Description"]


def test_ili9341_socket_pins_follow_the_spec_order():
    sym = _sym("ILI9341_Socket_1x14")
    names = ["VCC", "GND", "CS", "RESET", "DC/RS", "SDI(MOSI)", "SCK", "LED", "SDO(MISO)",
             "T_CLK", "T_CS", "T_DIN", "T_DO", "T_IRQ"]
    assert _pins(sym) == {str(i + 1): n for i, n in enumerate(names)}
    assert sexp.child(sexp.child(sym, "pin_names"), "hide") is None


def test_ili9341_module_has_no_pins():
    sym = _sym("ILI9341_Module")
    props = {p[1]: p[2] for p in sexp.children(sym, "property")}
    assert _pins(sym) == {} and props["Reference"] == "DS"


def test_sd_card_socket_pins_match_the_hirose_footprint_pads():
    sym = _sym("SD_Card_Hirose_DM1AA")
    assert _pins(sym) == {"1": "DAT3/CS", "2": "CMD/DI", "3": "VSS", "4": "VDD", "5": "CLK", "6": "VSS",
                          "7": "DAT0/DO", "8": "DAT1", "9": "DAT2", "CP": "CD", "WP": "WP", "SW": "COM",
                          "SH": "SHELL"}
    props = {p[1]: p[2] for p in sexp.children(sym, "property")}
    assert props["Footprint"] == "Connector_Card:SD_Hirose_DM1AA_SF_PEJ82"
    assert "to check against the data sheet" in props["Description"]
