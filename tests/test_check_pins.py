import os

import pytest

import check_pins as cp
from conftest import FIXTURES, ROOT

NET = os.path.join(FIXTURES, "toy.net")
SPEC = os.path.join(FIXTURES, "board_support.md")
TOY_PINS = os.path.join(ROOT, "toy", "spec", "pins.yaml")
# Set ROBCO_BOARD_SUPPORT to the real file to check the toy against it.
REAL_SPEC = os.environ.get("ROBCO_BOARD_SUPPORT") or os.path.join(ROOT, "..", "RobCo-Core", "docs", "spec", "BOARD_SUPPORT.md")


def toy_yaml(**override):
    """The toy pins.yaml, with some pin entries replaced: {pin: (name, net, use)}."""
    pins = {1: ("5V", "+5V", "power"), 2: ("GND", "GND", "ground"), 3: ("GPIO25", "SIG", "toy LED")}
    pins.update({int(k[1:]): v for k, v in override.items()})
    lines = ["board: toy", "connector: J1", "header: generic", "pins:"]
    for num, val in sorted(pins.items()):
        if val is None:
            continue
        name, net, use = val
        lines += [f"  - pin: {num}", f"    name: {name}", f"    net: {net}", f"    use: {use}"]
    return "\n".join(lines) + "\n"


def pi40_yaml(drop=(), change=None):
    """A full 40-pin map that matches the fixture software table."""
    uses = cp.parse_board_support(open(SPEC, encoding="utf-8").read())
    change = change or {}
    lines = ["board: hat", "connector: J1", "header: pi40", "pins:"]
    for pin, name in sorted(cp.PI40.items()):
        if pin in drop:
            continue
        gpio = int(name[4:]) if name.startswith("GPIO") else None
        use = uses[gpio][0][0] if gpio in uses else "none"
        name, use = change.get(pin, (name, use))
        net = name if gpio is not None else {"5V": "+5V", "3V3": "+3V3"}.get(name, name)
        lines += [f"  - pin: {pin}", f"    name: {name}", f"    net: {net}", f"    use: {use}"]
    return "\n".join(lines) + "\n"


def run(tmp_path, yaml_text, net=None, spec=None):
    path = tmp_path / "pins.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    return cp.run(str(path), net, spec)


def test_toy_passes_both_checks():
    assert cp.run(TOY_PINS, NET, SPEC) == (cp.OK, [])


def test_toy_against_real_board_support():
    if not os.path.exists(REAL_SPEC):
        pytest.skip("set ROBCO_BOARD_SUPPORT or check out RobCo-Core next to this repository")
    assert cp.run(TOY_PINS, NET, REAL_SPEC) == (cp.OK, [])


def test_wrong_net_fails(tmp_path):
    code, problems = run(tmp_path, toy_yaml(p3=("GPIO25", "LED_A", "toy LED")), net=NET)
    assert code == cp.WRONG_NET == 10
    assert problems[0].text == "J1 pin 3: netlist has net 'SIG', pins.yaml says 'LED_A'"


def test_pin_missing_from_netlist_fails(tmp_path):
    code, problems = run(tmp_path, toy_yaml(p4=("GPIO4", "X", "x")), net=NET)
    assert code == cp.MISSING_PIN == 11
    assert "J1 pin 4: in pins.yaml but not in the netlist" in problems[0].text


def test_pin_missing_from_yaml_fails(tmp_path):
    code, problems = run(tmp_path, toy_yaml(p3=None), net=NET)
    assert code == cp.MISSING_PIN
    assert problems[0].text == "J1 pin 3: net 'SIG' in the netlist but not in pins.yaml"


def test_pi40_map_passes(tmp_path):
    assert run(tmp_path, pi40_yaml(), spec=SPEC) == (cp.OK, [])


def test_software_pin_under_another_name_fails(tmp_path):
    code, problems = run(tmp_path, pi40_yaml(change={8: ("GPIO14", "console TX")}), spec=SPEC)
    assert code == cp.WRONG_USE == 12
    assert problems[0].text == "GPIO14 (pin 8): the software uses it as 'PL011 TXD', pins.yaml says 'console TX'"


def test_wrong_use_on_generic_header_fails(tmp_path):
    code, _ = run(tmp_path, toy_yaml(p3=("GPIO26", "SIG", "toy LED")), spec=SPEC)
    assert code == cp.WRONG_USE


def test_software_pin_missing_fails(tmp_path):
    code, problems = run(tmp_path, pi40_yaml(drop=(3,)), spec=SPEC)
    assert code == cp.MISSING_USE == 13
    assert problems[0].text == "GPIO2: used by the software as 'I2C SDA' (Pins), missing from pins.yaml"


def test_ignored_source_is_skipped(tmp_path):
    text = pi40_yaml(drop=(29,)).replace("header: pi40", "header: pi40\nignore_sources: [Input example]")
    assert run(tmp_path, text, spec=SPEC) == (cp.OK, [])


def test_wrong_pi_name_fails(tmp_path):
    code, problems = run(tmp_path, pi40_yaml(change={7: ("GPIO5", "none")}), spec=SPEC)
    assert cp.WRONG_NAME in {p.code for p in problems}
    assert "pin 7: named 'GPIO5', the Pi has 'GPIO4' there" in [p.text for p in problems]


def test_lowest_code_wins(tmp_path):
    text = toy_yaml(p3=("GPIO26", "LED_A", "toy LED"))
    code, problems = run(tmp_path, text, net=NET, spec=SPEC)
    assert sorted(p.code for p in problems) == [10, 12]
    assert code == 10


def test_parse_board_support_table_shapes():
    uses = cp.parse_board_support(open(SPEC, encoding="utf-8").read())
    assert uses[14] == [("PL011 TXD", "Pins")]
    assert uses[3] == [("I2C SCL", "Pins")]
    assert uses[11] == [("SPI0 SCLK", "Pins")]
    assert uses[18] == [("Audio channel 1", "Audio channels")]
    assert uses[27] == [("BACK", "Input example")]
    assert 34 not in uses and 40 not in uses  # not on the header
    assert 4 not in uses  # outside the Pins section


def test_gpio_list():
    assert cp._gpio_list("GPIO 34 to 36, 48") == [34, 35, 36, 48]
    assert cp._gpio_list("GPIO 18 at ALT5") == [18]
    assert cp._gpio_list("None, mono") == []


def test_cli_exit_codes(tmp_path, capsys):
    assert cp.main(["--pins", TOY_PINS, "--netlist", NET, "--board-support", SPEC]) == 0
    bad = tmp_path / "pins.yaml"
    bad.write_text(toy_yaml(p3=("GPIO25", "LED_A", "toy LED")), encoding="utf-8")
    assert cp.main(["--pins", str(bad), "--netlist", NET]) == 10
    assert "[10] J1 pin 3" in capsys.readouterr().err
    bad.write_text("pins:\n  - pin: 1\n", encoding="utf-8")
    assert cp.main(["--pins", str(bad), "--netlist", NET]) == 2
    assert cp.main(["--pins", str(tmp_path / "missing.yaml"), "--netlist", NET]) == 2


def test_yaml_subset():
    data = cp.parse_pins_yaml("a: 1  # c\nb: 'x y'\nl: [p, q]\npins:\n  - pin: 2\n    net: +5V\n")
    assert data == {"a": 1, "b": "x y", "l": ["p", "q"], "pins": [{"pin": 2, "net": "+5V"}]}
    with pytest.raises(cp.InputError):
        cp.parse_pins_yaml("  - pin: 1\n")
