"""The committed toy schematic and project files match a fresh generation."""

import importlib.util
import os

import pytest

from conftest import ROOT

KICAD = os.path.join(ROOT, "toy", "kicad")
FILES = ["toy.kicad_sch", "toy.kicad_pro", "sym-lib-table", "fp-lib-table"]


def _load_circuit():
    spec = importlib.util.spec_from_file_location("toy_circuit", os.path.join(ROOT, "toy", "gen", "circuit.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("name", FILES)
def test_regenerated_equals_committed(tmp_path, monkeypatch, name):
    circuit = _load_circuit()
    monkeypatch.setattr("sys.argv", ["circuit.py", str(tmp_path)])
    circuit.main()
    with open(os.path.join(KICAD, name), encoding="utf-8") as fh:
        committed = fh.read()
    assert (tmp_path / name).read_text(encoding="utf-8") == committed, f"{name} differs: run tools/build.sh gen"
