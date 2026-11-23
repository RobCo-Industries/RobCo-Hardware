import os

import check_models as cm
from conftest import ROOT

TOY = os.path.join(ROOT, "toy", "kicad", "toy.kicad_pcb")


def _models(tmp_path, names):
    for n in names:
        p = tmp_path / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")


def test_toy_paths():
    paths = cm.model_paths(open(TOY, encoding="utf-8").read())
    assert len(paths) == 3
    assert all(p.startswith("${KICAD10_3DMODEL_DIR}/") for p in paths)


def test_all_found(tmp_path, monkeypatch, capsys):
    _models(tmp_path, ["LED_SMD.3dshapes/LED_0805_2012Metric.step",
                       "Resistor_SMD.3dshapes/R_0805_2012Metric.step",
                       "Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x03_P2.54mm_Vertical.wrl"])
    monkeypatch.setenv("KICAD10_3DMODEL_DIR", str(tmp_path))
    assert cm.check(TOY)[1] == []
    assert cm.main([TOY]) == 0
    assert "all 3 3D models found" in capsys.readouterr().out


def test_missing_models_warn_with_count(tmp_path, monkeypatch, capsys):
    _models(tmp_path, ["LED_SMD.3dshapes/LED_0805_2012Metric.step"])
    monkeypatch.setenv("KICAD10_3DMODEL_DIR", str(tmp_path))
    assert cm.main([TOY]) == 0
    out = capsys.readouterr().out
    assert "::warning::2 of 3 3D models missing" in out
    assert out.count("::warning::3D model not found:") == 2


def test_unset_folder_counts_as_missing(monkeypatch):
    monkeypatch.delenv("KICAD10_3DMODEL_DIR", raising=False)
    assert len(cm.check(TOY)[1]) == 3


def test_unreadable_board(tmp_path):
    assert cm.main([str(tmp_path / "none.kicad_pcb")]) == 2
