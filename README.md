# RobCo-Hardware

Status: proposals. Nothing here is built, tested or validated on hardware.

This repository holds the board designs for the RobCo suite. Two boards are planned: a terminal controller HAT and a Pip-Boy HAT for the Raspberry Pi. Neither exists yet. The only board today is `toy/`, a 3-pin header, a resistor and an LED. It proves the toolchain from generator to renders.

## Safety

The boards are for low voltage only, 5 to 24 V. They never switch mains. Mains loads need an external, rated relay module.

## Tools

- KiCad 10.0.8 with `kicad-cli`. On macOS the scripts find it in `/Applications/KiCad`. On Linux they look in `/usr/bin` and `/usr/share/kicad`.
- The Python that ships with KiCad. It can import `pcbnew`, which the board generator needs.
- Python 3.9 or later with `pytest` for the tests. `tools/build.sh test` makes a venv under `build/`.
- RobCo-Core, for the pin check. Set `ROBCO_BOARD_SUPPORT` to the path of its `docs/spec/BOARD_SUPPORT.md`. The script also finds a RobCo-Core clone next to this one.

## Generate, check and export a board

```sh
tools/build.sh gen toy     # rewrite toy/kicad/ from toy/gen/
tools/build.sh check toy   # regen-diff, ERC, pin check, DRC
tools/build.sh out toy     # PDF, SVG, netlist, BOM, renders, gerbers, drill
tools/build.sh test        # Python tests
```

Every output goes to `build/<board>/`. Run `tools/build.sh` with no command for the full list and the variables it reads.

`check` fails when:

- the committed KiCad files differ from a fresh generation,
- ERC finds any violation,
- a header pin in the netlist differs from `spec/pins.yaml`, or `pins.yaml` gives a GPIO another use than the software,
- DRC finds a violation, on a board whose `board.env` says `ROUTED=yes`. On other boards DRC only writes a report.

## Where the PDFs and renders come from

Nobody commits them. CI builds them on every push and pull request and keeps them as run artifacts: `toy-outputs` holds the schematic PDF, SVG, netlist, BOM, reports and fab files, and `toy-renders` holds the 3D pictures. Locally, `tools/build.sh out` writes the same files.

## Layout

```
lib/       own symbols and footprints, shared by the boards
tools/     generators, checks and build script
tests/     pytest for the tools
toy/       the toolchain test board
  spec/    pins.yaml
  gen/     circuit.py writes the schematic, board.py writes the board
  kicad/   generated KiCad files, committed
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions and [LICENSE.md](LICENSE.md) for the licences.
