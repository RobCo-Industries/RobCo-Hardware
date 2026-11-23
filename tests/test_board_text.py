import re
import uuid

import sexp
from board_text import add_stackup, normalise
from common import stable_uuid

V4_A = "0b5a7c3e-1f2d-4c6b-8a9e-112233445566"
V4_B = "9d8c7b6a-5f4e-4d3c-9b2a-665544332211"


def test_normalise_replaces_random_uuids_consistently():
    text = f'(a (uuid "{V4_A}") (b (uuid "{V4_B}")) (c (uuid "{V4_A}")))'
    out = normalise(text, "toy")
    ids = re.findall(r'uuid "([^"]+)"', out)
    assert ids[0] == ids[2] != ids[1]
    assert {uuid.UUID(i).version for i in ids} == {5}
    assert normalise(text, "toy") == out


def test_normalise_keeps_stable_uuids():
    stable = stable_uuid("toy", "pcb", "fp", "R1")
    text = f'(a (uuid "{stable}"))'
    assert normalise(text, "toy") == text


def test_normalise_leaves_paths_alone():
    text = f'(fp (path "/{V4_A}"))'
    assert normalise(text, "toy") == text


def test_add_stackup_once():
    text = "(kicad_pcb\n\t(version 1)\n\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t)\n)\n"
    once = add_stackup(text)
    assert add_stackup(once) == once
    setup = sexp.child(sexp.parse(once), "setup")
    stack = setup[1]
    assert sexp.tag(stack) == "stackup"
    th = {layer[1]: float(sexp.value(layer, "thickness", 0)) for layer in sexp.children(stack, "layer")}
    assert th["F.Cu"] == 0.035 and th["B.Cu"] == 0.035
    assert abs(sum(th.values()) - 1.6) < 1e-9
