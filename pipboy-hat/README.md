# Pip-Boy HAT

Status: schematic drawn, ERC clean; board not started. Nobody has built or tested it.

The board turns a Raspberry Pi Zero, Zero W or Zero 2 W into a wrist device that runs Pip-OS and Deitrix. It carries a 2.8 inch ILI9341 SPI display, six keys, a rotary dial with a push button, a small speaker amplifier, a DS1338 clock and a serial console header. Revision 1 has no battery circuit: it runs from the Pi's USB port or from a 5 V input header with reverse-polarity protection. That header takes a regulated 5 V source only, with no USB cable on the Pi.

- The spec: [spec/SPEC.md](spec/SPEC.md)
- The header map: [spec/pins.yaml](spec/pins.yaml). The pin table in the spec is generated from it.
- The bring-up checklist: [spec/BRINGUP.md](spec/BRINGUP.md)

## Schematic

`gen/circuit.py` writes the schematic into `kicad/`. Each sheet has its own module in `gen/sheets/`. The root sheet holds one box per sheet.

| Page | Sheet | Paper | What it holds |
|---|---|---|---|
| 1 | Root | A4 | One box per block, the safety line and the cross-sheet net names |
| 2 | Power input | A4 | J3, F1, Q3, R1, D2, D1 |
| 3 | Pi header | A3 | J1, the I2C pull-ups R10 and R11, the ID EEPROM U2 with C11, R12 to R14 and JP2, the holes H1 to H8, and the J1 note for the board step |
| 4 | Display and backlight | A4 | J2, DS1, R24, C1, C2. The backlight switch Q1, Q2, R20 to R23, TP7. |
| 5 | Keys and dial | A4 | SW1 to SW7, R40 to R48, C40 to C48, J5 |
| 6 | Audio | A4 | R30, C30, C31, R31, RV1, M1, C32, C33, J6, LS1, TP6 |
| 7 | Clock | A4 | U1, Y1, BT1, C10, JP1, R15, TP8 |
| 8 | Serial and test points | A4 | J4, TP1 to TP5 |

Regenerate and check:

```sh
tools/build.sh gen pipboy-hat     # rewrite kicad/ from gen/
tools/build.sh check pipboy-hat   # regen-diff, ERC, pin checks, netlist tests
tools/build.sh docs pipboy-hat    # PDF, SVG, netlist and BOM in build/pipboy-hat/
```

CI runs the same check and keeps the PDF, the BOM and the netlist in the `toy-outputs` artifact. Nobody commits them.

`check` runs `tests/test_pipboy_hat.py` on the exported netlist. It compares the BOM with the spec's BOM table, checks the exact pins of every net that reaches the Pi, the 5 V input path, the members of `+5V` and `+3V3`, the backlight switch, the clock's battery jumper, the unfitted pull-ups, the display socket's pin order and the serial header.

ERC has no waiver.

## Parts you buy that do not sit on the board

- DS1, the ILI9341 display module. It plugs into J2, a 1x14 socket on the board.
- LS1, the 8 Ohm speaker. It is wired to J6, a 2-pin header on the board.

Both are in the BOM with "Excluded from board" in its "Off board" column. They have no footprint and are not in the netlist. J2 and J6 are the board's own parts.

## Own symbols and footprints

Every dimension and pin order below comes from memory and is to verify against the part bought:

| Ref | Own part | What it assumes |
|---|---|---|
| Q3 | Symbol `Q_PMOS_GSD_SOT23` | SOT-23 pads 1 gate, 2 source, 3 drain, as the AO3401A and DMG2305UX |
| J2 | Symbol `ILI9341_Socket_1x14` | Pin names in the order of spec section 4.1, typical of MSP2807 class modules |
| DS1 | Symbol `ILI9341_Module` | No pins: the module only plugs into J2 |
| SW7 | Footprint `RotaryEncoder_Bourns_PEC11R-Switch_Vertical` | Pads copied from the stock Alps EC11E footprint |
| F1 | Footprint `Fuse_PTC_Radial_W10.0mm_T3.5mm_P5.10mm` | The 1.1 A class outline of the terminal controller. An MF-R090, body width about 7.4 mm to verify, fits inside it: leads 5.1 mm apart, drill 1.0 mm |
| M1 | Footprint `PAM8302A_Module_In1x05_P2.54mm_Out1x02_P3.50mm` | Drawn from memory: redraw from the module before ordering. Input row 1 VIN, 2 GND, 3 SD, 4 A+, 5 A-. Output edge 6 OUT+, 7 OUT- |

## Readings of the spec

The spec is silent or loose in these places. The sheets take the smallest reading that works and say so:

- J1: spec section 9 calls the footprint mirrored against a normal HAT. With J1 on the bottom face and the Pi face up below, the stacking is that of a normal HAT, so pin 1 sits straight over the Pi's pin 1. The note on the Pi header sheet tells the board step to prove it with the Zero's footprint or drawing before placing anything.
- The net between R22 and Q2's collector has no name in the spec. It stays unnamed.
- F1 takes the larger fuse outline, as above.

## For the board step

- Prove J1's pin 1 first, as the note on page 3 says.
- Measure the display module for J2's position and H1 to H4.
- The owner must still decide the outline with the case: see [section 6 of the spec](spec/SPEC.md#6-size-and-shape).
