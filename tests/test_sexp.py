import glob
import os

import pytest

import sexp
from conftest import FIXTURES, STOCK_SYMBOLS
from sexp import Sym


def test_parse_atoms_and_strings():
    node = sexp.parse('(a "b c" 1.5 (d "e\\"f") -2)')
    assert node == ["a", "b c", "1.5", ["d", 'e"f'], "-2"]
    assert isinstance(node[0], Sym)
    assert not isinstance(node[1], Sym)


@pytest.mark.parametrize("text", ["(a", "(a))", "a", '(a "b', ""])
def test_parse_rejects_bad_input(text):
    with pytest.raises(sexp.SexpError):
        sexp.parse(text)


def test_write_quotes_and_escapes():
    assert sexp.dumps([Sym("t"), 'a"b\\c\nd']) == '(t "a\\"b\\\\c\\nd")'
    assert sexp.parse(sexp.dumps([Sym("t"), 'a"b\\c\nd'])) == ["t", 'a"b\\c\nd']


@pytest.mark.parametrize("v,text", [(1.27, "1.27"), (2.0, "2"), (-0.0, "0"), (0.1 + 0.2, "0.3"), (5, "5")])
def test_number_format(v, text):
    assert sexp.fmt_num(v) == text


def test_layout_matches_kicad():
    node = [Sym("a"), Sym("b"), [Sym("at"), 1, 2, 0], [Sym("pts"), [Sym("xy"), 0, 0], [Sym("xy"), 1, 1]]]
    assert sexp.dumps(node) == "(a b\n\t(at 1 2 0)\n\t(pts\n\t\t(xy 0 0) (xy 1 1)\n\t)\n)"


def _lib_files():
    files = sorted(glob.glob(os.path.join(FIXTURES, "symbols", "*.kicad_sym")))
    for name in ("Device", "power", "Connector_Generic", "Interface_UART", "74xx_IEEE"):
        path = os.path.join(STOCK_SYMBOLS, f"{name}.kicad_sym")
        if os.path.exists(path):
            files.append(path)
    return files


@pytest.mark.parametrize("path", _lib_files(), ids=os.path.basename)
def test_round_trip_is_byte_exact(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert sexp.dump_file(sexp.parse(text)) == text


def test_round_trip_footprint_tree():
    pattern = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Resistor_SMD.pretty/*.kicad_mod"
    files = sorted(glob.glob(pattern))[:20]
    if not files:
        pytest.skip("stock footprints not installed")
    for path in files:
        tree = sexp.load(path)
        assert sexp.parse(sexp.dump_file(tree)) == tree


def test_tree_helpers():
    node = sexp.parse('(pin passive line (at 1 2 0) (name "A") (number "1"))')
    assert sexp.tag(node) == "pin"
    assert sexp.value(node, "number") == "1"
    assert sexp.child(node, "at") == ["at", "1", "2", "0"]
    assert sexp.children(node, "missing") == []
