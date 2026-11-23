import os

import pytest

import netlist
from conftest import FIXTURES


@pytest.fixture
def toy():
    return netlist.load(os.path.join(FIXTURES, "toy.net"))


def test_components(toy):
    assert sorted(toy.components) == ["D1", "J1", "R1"]
    r1 = toy.components["R1"]
    assert r1.value == "1k"
    assert r1.footprint == "Resistor_SMD:R_0805_2012Metric"
    assert r1.path == "/" + r1.uuid
    assert r1.part == "Device:R"
    assert r1.dnp is False


def test_dnp_property():
    text = open(os.path.join(FIXTURES, "toy.net"), encoding="utf-8").read()
    text = text.replace('(ref "R1")', '(ref "R1")\n\t\t\t(property (name "dnp"))', 1)
    nl = netlist.parse(text)
    assert nl.components["R1"].dnp is True
    assert nl.components["D1"].dnp is False


def test_nets(toy):
    pins = toy.pin_net()
    assert pins[("J1", "1")] == "+5V"
    assert pins[("J1", "2")] == "GND"
    assert pins[("J1", "3")] == "/SIG"
    assert pins[("R1", "2")] == "/LED_A"
    assert sorted(toy.nets["GND"]) == [("D1", "1"), ("J1", "2")]


@pytest.mark.parametrize("name,short", [("/SIG", "SIG"), ("+5V", "+5V"), ("/Power/X", "/Power/X")])
def test_short_net(name, short):
    assert netlist.short_net(name) == short


def test_rejects_other_files():
    with pytest.raises(ValueError, match="not a KiCad netlist"):
        netlist.parse("(kicad_sch (version 1))")
