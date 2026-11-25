# Changelog

## Unreleased

- Add the repository basics: licences, ignore rules, changelog.
- Add the S-expression reader and writer, and the schematic writer.
- Add the netlist reader and the `pcbnew` board builder.
- Add the toy board: schematic, routed board, pin map.
- Add `check_pins.py` for the header pin map.
- Add `tools/build.sh` as the single entry point.
- Add the CI workflow: tests, toy checks and exports, renders.
- Move the terminal controller spec here from RobCo-Core, without the PCB tool prompt. Split its bring-up checklist into `BRINGUP.md`.
- Add the terminal controller header map, `pins.yaml`, and `tools/gen_pin_table.py`, which writes the pin table in the spec from it.
- Add own PCA9554 and DS1338 symbols, written by `tools/gen_symbols.py`. Their pinouts are still to check against the data sheets.
- Write hierarchical schematics: sheet symbols, global labels, no-connect flags, junctions, frames, notes, mirrored symbols and repeated channels.
- Add `toy2/`, a two-sheet schematic that tests the hierarchy tools.
- Check boards that have no board file yet, and boards that the owner routed.
- Render in `kicad/kicad:10.0-full`, which has the 3D models, and warn on each missing model.
- Find RobCo-Core two levels up, so the checks run from a worktree.
- Move the dial pins GPIO 16, 23 and 24 of the terminal controller to its free-pin header. The pin check skips the input example for those three pins only.
- Place one unit of a multi-unit part, mark parts not fitted, draw local labels at a point, and use own rail symbols.
- Add own symbols: a TO-220 P-MOSFET, a DO-15 TVS, the PAM8302A module and the rails `V_PROT`, `V_SW` and `+V_S`.
- Draw the terminal controller schematic on six sheets. ERC is clean with no waiver.
- Add netlist tests for the terminal controller: BOM against the spec, address straps, driver pull-downs, expander lines, `ARM`, rails and I2C. `tools/build.sh check` runs them.
- Fix terminal controller review findings: 60 V diodes and Q1, 50 V reservoir capacitors above the TVS clamp; R20 at 100 kOhm and the real gate drive at 5 V; WP, ID_SD and ID_SC pull-ups; footprints for C13 and a VBAT jumper; notes on GPIO 25, back-fed loads, arming inrush and audio level.
- Refuse units of one reference that use different library symbols, or differ in value, footprint or fitting, across all sheets.
- Rate the terminal controller fuses F1 and F2 at 60 V or more, above the TVS clamp.
- Add own footprints for the fuses F1 and F2 and the amplifier module M1, and a test that every footprint a schematic names exists. Measure the terminal controller parts against the HAT outline: they do not fit, so the board is not placed yet.
- Check `pins.yaml` against the SPI display table of BOARD_SUPPORT.md too. The toy and the terminal controller skip it for GPIO 25 and GPIO 4, which they use otherwise.
- Find RobCo-Core two levels up in the tests too, so the real pin table tests run from a worktree.
- Draw the Pip-Boy HAT schematic on seven sheets. ERC is clean with no waiver.
- Add netlist tests for the Pip-Boy HAT. `tools/build.sh check pipboy-hat` runs them, and CI keeps its PDF, BOM and netlist.
- Give the Pip-Boy fuse F1 the larger fuse outline, and make the J1 pin 1 note exact for the board step.
- Add an "Off board" column to the exported BOM for parts bought that do not sit on the board.
- Add the Pip-Boy HAT spec, its header map and its bring-up checklist. Specification only.
- Apply the electrical review to the Pip-Boy spec: reverse-polarity MOSFET, plain overvoltage limits and voltage budget, dial speed limit, audio trimmer range, backlight notes.
