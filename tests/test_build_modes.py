"""tools/build.sh on a schematic-only board and on a board routed by the owner.

The tests run build.sh with stand-ins for kicad-cli and the board generator,
so they need neither KiCad nor pcbnew.
"""

import os
import shutil
import stat
import subprocess
import sys

import pytest

from conftest import FIXTURES, ROOT

BUILD = os.path.join(ROOT, "tools", "build.sh")

# Stand-in for kicad-cli: logs each call, writes the files the script reads.
FAKE_CLI = """#!/bin/sh
echo "$@" >> "$FAKE_LOG"
out=""
prev=""
for a in "$@"; do
  [ "$prev" = "-o" ] && out="$a"
  prev="$a"
done
case "$1 $2 $3" in
  "sch export netlist") cp "$FAKE_NET" "$out" ;;
  "sch erc"*) echo "ERC report" > "$out" ;;
  "pcb drc"*) echo "DRC report" > "$out" ;;
esac
exit 0
"""

CIRCUIT = """import os, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "b.kicad_sch"), "w").write("schematic v1\\n")
"""

BOARD = """import os, sys
open(os.path.join(sys.argv[2], "b.kicad_pcb"), "w").write("generated board\\n")
open(os.environ["FAKE_LOG"], "a").write("board.py ran\\n")
"""


def _write(path, text, exe=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if exe:
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


@pytest.fixture
def board(tmp_path):
    bdir = tmp_path / "b"
    _write(str(bdir / "gen" / "circuit.py"), CIRCUIT)
    _write(str(bdir / "kicad" / "b.kicad_sch"), "schematic v1\n")
    os.makedirs(str(bdir / "spec"))
    shutil.copy(os.path.join(ROOT, "toy", "spec", "pins.yaml"), str(bdir / "spec" / "pins.yaml"))
    _write(str(tmp_path / "kicad-cli"), FAKE_CLI, exe=True)
    return tmp_path


def _run(tmp, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp),
        "ROBCO_BOARD_DIR": str(tmp / "b"),
        "KICAD_CLI": str(tmp / "kicad-cli"),
        "KICAD_PY": sys.executable,
        "ROBCO_BOARD_SUPPORT": "skip",
        "FAKE_LOG": str(tmp / "calls.log"),
        "FAKE_NET": os.path.join(FIXTURES, "toy.net"),
        "KICAD10_3DMODEL_DIR": str(tmp),
    }
    r = subprocess.run(["bash", BUILD, *args, "b"], env=env, capture_output=True, text=True)
    shutil.rmtree(os.path.join(ROOT, "build", "b"), ignore_errors=True)
    return r


def _calls(tmp):
    path = tmp / "calls.log"
    return path.read_text() if path.exists() else ""


def test_schematic_only_board_is_checked(board):
    r = _run(board, "check")
    assert r.returncode == 0, r.stderr
    assert "regenerated files equal the committed files" in r.stdout
    assert "ERC clean" in r.stdout
    assert "no difference with the netlist" in r.stdout
    assert "no board file yet, schematic only: DRC skipped" in r.stdout
    assert "pcb drc" not in _calls(board)


def test_schematic_only_board_skips_renders_and_fab(board):
    r = _run(board, "render")
    assert r.returncode == 0 and "schematic only: renders skipped" in r.stdout
    r = _run(board, "fab")
    assert r.returncode == 0 and "schematic only: gerbers and drill skipped" in r.stdout
    assert "pcb " not in _calls(board)


def test_schematic_only_board_fails_on_a_stale_schematic(board):
    _write(str(board / "b" / "kicad" / "b.kicad_sch"), "edited by hand\n")
    r = _run(board, "check")
    assert r.returncode != 0
    assert "b.kicad_sch differs from a fresh generation" in r.stderr


def test_generated_board_file_is_compared(board):
    _write(str(board / "b" / "gen" / "board.py"), BOARD)
    _write(str(board / "b" / "kicad" / "b.kicad_pcb"), "routed by hand\n")
    r = _run(board, "regen")
    assert r.returncode != 0
    assert "b.kicad_pcb differs from a fresh generation" in r.stderr


def test_owner_routed_board_compares_the_schematic_only(board):
    _write(str(board / "b" / "gen" / "board.py"), BOARD)
    _write(str(board / "b" / "kicad" / "b.kicad_pcb"), "routed by hand\n")
    _write(str(board / "b" / "board.env"), "OWNER_ROUTED=yes\n")
    r = _run(board, "regen")
    assert r.returncode == 0, r.stderr
    assert "b.kicad_pcb not compared" in r.stdout
    assert "board.py ran" not in _calls(board)
    r = _run(board, "gen")
    assert r.returncode == 0
    assert (board / "b" / "kicad" / "b.kicad_pcb").read_text() == "routed by hand\n"
    _write(str(board / "b" / "kicad" / "b.kicad_sch"), "edited by hand\n")
    r = _run(board, "regen")
    assert r.returncode != 0 and "b.kicad_sch differs" in r.stderr
