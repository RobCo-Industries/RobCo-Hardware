"""The committed toy schematics and project files match a fresh generation."""

import importlib.util
import os

import pytest

from conftest import ROOT

FILES = {
    "toy": ["toy.kicad_sch", "toy.kicad_pro", "sym-lib-table", "fp-lib-table"],
    "toy2": ["toy2.kicad_sch", "controller.kicad_sch", "outputs.kicad_sch", "toy2.kicad_pro",
             "sym-lib-table", "fp-lib-table"],
}


def _load_circuit(board):
    spec = importlib.util.spec_from_file_location(f"{board}_circuit".replace("-", "_"),
                                                  os.path.join(ROOT, board, "gen", "circuit.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FILES["terminal-controller"] = (["terminal-controller.kicad_sch"]
                                + [row[1] for row in _load_circuit("terminal-controller").SHEETS]
                                + ["terminal-controller.kicad_pro", "sym-lib-table", "fp-lib-table"])
CASES = [(board, name) for board, names in FILES.items() for name in names]


@pytest.mark.parametrize("board,name", CASES)
def test_regenerated_equals_committed(tmp_path, monkeypatch, board, name):
    circuit = _load_circuit(board)
    monkeypatch.setattr("sys.argv", ["circuit.py", str(tmp_path)])
    circuit.main()
    with open(os.path.join(ROOT, board, "kicad", name), encoding="utf-8") as fh:
        committed = fh.read()
    assert (tmp_path / name).read_text(encoding="utf-8") == committed, f"{board}/{name} differs: run tools/build.sh gen {board}"


def test_toy2_writes_no_other_file(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["circuit.py", str(tmp_path)])
    _load_circuit("toy2").main()
    assert sorted(os.listdir(tmp_path)) == sorted(FILES["toy2"])
