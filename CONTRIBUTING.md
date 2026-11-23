# Contributing

Every board here is a proposal. Do not write that a board works, or was tested, unless someone tested a real board.

## Run the checks

```sh
tools/build.sh test        # Python tests
tools/build.sh check toy   # the board checks; also toy2, terminal-controller, pipboy-hat
```

CI runs the same commands. See the README for the tools.

## Board folders

Each board has the same shape:

- `spec/` holds the spec and `pins.yaml`, the single source for the header map. One entry per header pin: `pin`, `name` (the Pi pin name, such as `GPIO17`), `net`, `use` (the software use) and `source`. Keep to the YAML shape of `toy/spec/pins.yaml`: `check_pins.py` reads it without a YAML library.
- `gen/circuit.py` writes the schematic and the project files. `gen/board.py` writes the board with `pcbnew`.
- `kicad/` holds the generated files. Commit them. Do not edit them by hand until the owner routes the board. From then on the routed board file is the source.
- `board.env` may set `ROUTED=yes`. DRC then fails CI on any violation. It may also set `OWNER_ROUTED=yes` once the owner routes the board in KiCad. The routed board file is then the source, and the regen-diff skips it.
- `pins.yaml` may list `ignore_sources`: a source table name skips that table, and `Input example:GPIO16` skips it for one pin. Write the reason in the file.
- `board.env` may set `NETTEST=tests/test_<board>.py`, the board's netlist tests. `tools/build.sh check` runs that file with the exported netlist in `ROBCO_NETLIST`.
- `spec/SPEC.md` may hold the header pin table between `<!-- pin-table:start -->` and `<!-- pin-table:end -->`. Edit `pins.yaml`, then run `tools/gen_pin_table.py spec/pins.yaml spec/SPEC.md`. `check` fails when the two differ.

## Conventions

- Put every symbol, wire and label on the 1.27 mm grid. The schematic writer raises an error on an off-grid point.
- Connect pins with net labels by default. `Schematic.label()` draws a short wire stub and puts the label at its end, so the text never covers a pin number.
- Use power symbols for rails, and `Schematic.power_flag()` once per rail that a connector feeds. ERC needs the flag.
- Reference designators: J1 is the Pi header, U for chips, then Q, D, R, C, JP, TP. Group numbers by block, such as R1x for I2C.
- Net names match the software: `GPIO17`, `X0.0` to `X1.7`, `BTN_UP`, `+3V3`, `+5V`, `GND`.
- Each project has its own `sym-lib-table` and `fp-lib-table`. Stock libraries go through `${KICAD10_SYMBOL_DIR}` and `${KICAD10_FOOTPRINT_DIR}`, ours through `${KIPRJMOD}/../../lib`. The generator writes both tables.
- UUIDs come from the project name and the item path. Never use random UUIDs: CI compares a fresh generation with the committed files byte for byte.
- Do not commit generated outputs: PDFs, renders, netlists, BOMs, fab files. They live under `build/`, which git ignores.

## Hierarchical schematics

A board with several blocks uses `Hierarchy` from `tools/sch.py`. See `toy2/gen/circuit.py` for a small example.

- The root sheet holds one sheet symbol per block and a short note in each. Each block is its own `.kicad_sch` file, named after the block in lower case, such as `outputs.kicad_sch`.
- Each block sheet has its own title block: the block name as title, then the board name and the line "Proposal. Not built, not validated on hardware."
- Reference designators and power symbol numbers are unique across all sheets. The writer raises an error on a duplicate.
- Nets inside one block use local labels. Nets that cross blocks use global labels. Rails use power symbols on every sheet.
- Global labels carry the net name of the software or the spec: `I2C_SDA`, `X0.3`, `BTN_UP`, `ARM`. Give each one a shape seen from its sheet: `output` where the block drives the net, `input` where it reads it, `bidirectional` for a bus such as I2C, `passive` otherwise.
- Draw a junction with `junction()` wherever a wire ends on the middle of another wire, or three wire ends meet. The writer refuses a sheet that lacks one. A corner of two wires needs none.
- Mark every pin left open on purpose with `no_connect()`.
- Put a `frame()` with a title around each group of parts on a sheet.
- Draw a channel that repeats, such as eight outputs, once in a function and place it with `repeat()`. Put the index in the reference and net names: `R1{i}`, `X0.{i}`.
- Mirror a symbol with `mirror="y"` when its pins would face away from what they connect to. KiCad then right-justifies its fields. It does the same for a symbol turned 90 or 180 degrees: give the end of the text as the field position.
- Place each unit of a multi-unit part with `unit=`, such as one channel of a quad optocoupler.
- Mark a part that is not fitted with `dnp=True`. It stays in the netlist and the BOM.
- A rail with no stock power symbol gets an own one in `lib/RobCo.kicad_sym`, passed through `power_libs`.
- KiCad draws a multi-line note above its anchor: give the bottom left corner of the last line.
- KiCad needs these items for a hierarchy written by a script, and the writer emits them: a `sheet` node with its UUID, `Sheetname` and `Sheetfile` fields and an `instances` block with the page number; `sheet_instances` in the root file only; and an instance path `/<root uuid>/<sheet uuid>` on every symbol of a block, so references stay annotated.

## Add a symbol

Own symbols live in `lib/RobCo.kicad_sym`. `tools/gen_symbols.py` writes the file. Each symbol starts from a stock symbol of a close part.

1. Add an entry to `SYMBOLS` in `tools/gen_symbols.py`: the stock library and symbol, the fields, and the pins to rename.
2. Give it a stock footprint that exists in `${KICAD10_FOOTPRINT_DIR}`, and a description that lists the pinout and what is still to check against the data sheet.
3. Run `tools/gen_symbols.py`. Prove that KiCad loads the file: `kicad-cli sym upgrade --force -o /tmp/x.kicad_sym lib/RobCo.kicad_sym` must succeed and change only the generator line.
4. Copy the stock symbol into `tests/fixtures/symbols/` unchanged, so the tests can regenerate the library without KiCad. Add a test for the pinout.
5. Use the symbol in a toy so ERC covers it.

## Commits

Use short imperative subjects. Each commit should pass the tests.
