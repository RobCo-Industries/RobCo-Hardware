# RobCo-Hardware

Status: proposals. Nothing here is built, tested or validated on hardware.

This repository holds the board designs for the RobCo suite. Two boards are planned: a terminal controller HAT and a Pip-Boy HAT for the Raspberry Pi. Neither exists yet.

## Boards

| Folder | Board | Status |
|---|---|---|
| `toy/` | Toolchain test: a 3-pin header, a resistor and an LED | Test bed. Schematic, routed board, renders. |
| `toy2/` | Hierarchy test: an expander, a clock and eight LED channels on two sheets | Test bed. Schematic only. |
| `terminal-controller/` | Terminal controller HAT | Schematic drawn, ERC clean; board not started. See its [README](terminal-controller/README.md). |
| `pipboy-hat/` | Pip-Boy HAT: display, keys, dial, speaker and clock for a Pi Zero | Specification only. See its [README](pipboy-hat/README.md). |

The terminal controller spec is in [terminal-controller/spec/SPEC.md](terminal-controller/spec/SPEC.md), with its bring-up checklist in [BRINGUP.md](terminal-controller/spec/BRINGUP.md) and its header map in [pins.yaml](terminal-controller/spec/pins.yaml). The Pip-Boy HAT spec is in [pipboy-hat/spec/SPEC.md](pipboy-hat/spec/SPEC.md), with [BRINGUP.md](pipboy-hat/spec/BRINGUP.md) and [pins.yaml](pipboy-hat/spec/pins.yaml).

## Safety

The boards are for low voltage only, 5 to 24 V. They never switch mains. Mains loads need an external, rated relay module.

## Tools

- KiCad 10.0.8 with `kicad-cli`. On macOS the scripts find it in `/Applications/KiCad`. On Linux they look in `/usr/bin` and `/usr/share/kicad`.
- The Python that ships with KiCad. It can import `pcbnew`, which the board generator needs.
- Python 3.9 or later with `pytest` for the tests. `tools/build.sh test` makes a venv under `build/`.
- RobCo-Core, for the pin check. Set `ROBCO_BOARD_SUPPORT` to the path of its `docs/spec/BOARD_SUPPORT.md`. The script also finds a RobCo-Core clone next to this one, or two levels up from a worktree.

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
- the pin table in `spec/SPEC.md` differs from the one `tools/gen_pin_table.py` writes from `pins.yaml`,
- a board whose `board.env` names netlist tests with `NETTEST` fails one of them,
- DRC finds a violation, on a board whose `board.env` says `ROUTED=yes`. On other boards DRC only writes a report.

A board with no board file yet is checked as a schematic. `check` runs the regen-diff, ERC and the pin checks, and prints a line for each step it skips. A board with no generator yet gets the pin checks only. When the owner routes a board, `board.env` says `OWNER_ROUTED=yes`. The committed board file is then the source: `gen` and the regen-diff cover the schematic and project files only.

## Where the PDFs and renders come from

Nobody commits them. CI builds them on every push and pull request and keeps them as run artifacts: `toy-outputs` holds the schematic PDFs, SVGs, netlists, BOMs and reports of both toys and the fab files of `toy/`, and `toy-renders` holds the 3D pictures. Locally, `tools/build.sh out` writes the same files.

The render job runs in `kicad/kicad:10.0-full`, the image with the stock 3D models. `kicad/kicad:10.0` has none. Before it renders, `tools/check_models.py` lists every model the board file references and prints a `::warning::` line for each one it cannot find, with the count.

## Layout

```
lib/       own symbols and footprints, shared by the boards
tools/     generators, checks and build script
tests/     pytest for the tools
toy/       the toolchain test board
  spec/    pins.yaml
  gen/     circuit.py writes the schematic, board.py writes the board
  kicad/   generated KiCad files, committed
toy2/      the hierarchy test, same shape, no board file
terminal-controller/
  spec/    SPEC.md, BRINGUP.md, pins.yaml
  gen/     circuit.py and one module per sheet in sheets/
  kicad/   generated KiCad files, committed
pipboy-hat/
  spec/    SPEC.md, BRINGUP.md, pins.yaml; no generator yet
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions and [LICENSE.md](LICENSE.md) for the licences.
