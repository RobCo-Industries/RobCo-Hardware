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
