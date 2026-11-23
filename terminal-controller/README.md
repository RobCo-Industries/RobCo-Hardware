# Terminal controller HAT

Status: proposal. The schematic is drawn and ERC is clean. The board is not placed: the parts do not fit a 65 by 56 mm HAT, see [Board](#board). Nobody has built or tested it.

The spec is in [spec/SPEC.md](spec/SPEC.md), the header map in [spec/pins.yaml](spec/pins.yaml) and the bring-up checklist in [spec/BRINGUP.md](spec/BRINGUP.md).

## Schematic

`gen/circuit.py` writes the schematic into `kicad/`. Each sheet has its own module in `gen/sheets/`. The root sheet holds one box per sheet.

| Page | Sheet | Paper | What it holds |
|---|---|---|---|
| 1 | Root | A4 | One box per block, the safety line and the cross-sheet net names |
| 2 | Power and arm switch | A4 | J2, JP1, F1, D1, D2, C1, C2 to `V_PROT`. F2 to `+V_S`. The arm switch Q1, Q2, R20 to R24, D3, D4, LED8, JP8 to `V_SW`. C3, C4 and TP1 to TP3, TP6, TP7. |
| 3 | Pi header and I2C | A3 | J1, the expanders U1 and U2 with their straps JP2 to JP7, C5, C6, R3, J9. R1, R2, TP4, TP5. The clock U3 with Y1, BT1, C7, R4, TP8. The ID EEPROM U7 with C12, R80, R81, JP11. H1 to H4. |
| 4 | Outputs | A4 | U4 ULN2803A, the pull-downs RN1, C8, the status LEDs LED0 to LED7 with R10 to R17, J3 and C9 |
| 5 | Inputs | A4 | Eight channels of U5 and U6 LTV-847 with R60 to R67, D10 to D17, R70 to R77 and C40 to C47. J4, JP10, C11. |
| 6 | Audio | A4 | R30 and C30, the jack J10 with R31 and R32, JP9, C31, RV1, M1, C32 and J8 |
| 7 | Headers | A4 | J5 with R40 to R45, R50 to R55 and R59. J6 serial console. J7 free pins. |

Nets that cross sheets use global labels with the names of plan section 5: `I2C_SDA`, `I2C_SCL`, `X0.0` to `X1.7`, `ARM`, `AUDIO_PWM`, `UART_TX`, `UART_RX`, `BTN_UP` and the other buttons, and `GPIO4` style names for free pins. Rails use power symbols: `+3V3`, `+5V`, `GND`, `V_PROT`, `V_SW` and `+V_S`. The last three are own symbols in `lib/RobCo.kicad_sym`.

Regenerate and check:

```sh
tools/build.sh gen terminal-controller     # rewrite kicad/ from gen/
tools/build.sh check terminal-controller   # regen-diff, ERC, pin checks, netlist tests
tools/build.sh docs terminal-controller    # PDF, SVG, netlist and BOM in build/terminal-controller/
```

CI runs the same check and keeps the PDF as part of the `toy-outputs` artifact. Nobody commits the PDF.

`check` runs `tests/test_terminal_controller.py` on the exported netlist. It compares the BOM of the schematic with the BOM table of the spec, the address straps with the address map, the pull-down on each driver input, the parts on each expander line, the `ARM` net, the parts between the load side and the logic rails, and the I2C bus.

ERC has no waiver. The project file sets no rule severity.

### Assumptions to verify

The sheets mark these "to verify". Check each one against the data sheet of the part bought:

- Q1: TO-220 pin order 1 gate, 2 drain, 3 source, as the IRF9540N. The own symbol `Q_PMOS_GDS` assumes it.
- Q2: 2N5551 TO-92 pin order 1 emitter, 2 base, 3 collector, from the stock symbol `Q_NPN_EBC`. KiCad has no 2N5551 TO-92 symbol.
- U1, U2: PCA9554 pinout and address formula. The own symbol is drawn from the TCA9554DW.
- U3: DS1338 pinout, same as the DS1307. The 6 pF crystal with no load capacitors.
- U5, U6: LTV-847 pinout from the stock symbol: 1 to 8 anode and cathode pairs, 16 C1 and 15 E1 down to 10 C4 and 9 E4.
- M1: the PAM8302A module pin order and that it pulls SD high. SD is left open.
- D2: the standoff voltage and the pad order of the DO-15 TVS.
- JP11: how the 24C32 treats an open WP pin.
- BT1: the pad polarity of the Keystone 3002 holder.

### Own footprints

No stock footprint fits these parts. They use own footprints in `lib/RobCo.pretty`. Every dimension comes from memory and is to verify:

| Ref | Footprint | Assumed dimensions |
|---|---|---|
| F1 | `RobCo:Fuse_PTC_Radial_W10.0mm_T3.5mm_P5.10mm` | Littelfuse RXEF110 class: body 10.0 x 3.5 mm, leads 5.1 mm apart, drill 1.0 mm |
| F2 | `RobCo:Fuse_PTC_Radial_W7.4mm_T3.0mm_P5.10mm` | Bourns MF-R020 class: body 7.4 x 3.0 mm, leads 5.1 mm apart, drill 0.8 mm |
| M1 | `RobCo:PAM8302A_Module_1x07_P2.54mm` | One row of 7 pins on 2.54 mm in the symbol's order, module 20.3 x 17.8 mm |

None of the three has a 3D model.

### Other choices on the sheets

- JP1 and JP9 have no default shunt on the schematic. The spec gives none.
- JP2 to JP7 use the stock `SolderJumper_3_Bridged12`: pad 1 is the bridged default. The netlist keeps pads 1 and 2 apart, so the board step must accept the bridge in the footprint.
- C8 sits from `V_SW` to `GND`, which is U4 COM to GND, as the spec says.
- The four HAT mounting holes are H1 to H4. The spec BOM now lists them.

## Board

There is no board file yet. The through-hole parts of the schematic do not fit on the 65 by 56 mm HAT, on one side or on two.

Areas below are the sums of the footprint courtyards, with J1 and the four holes left out:

| Case | Courtyard area |
|---|---|
| Every footprint, through-hole as drawn | 7540 mm² |
| Fitted parts only, through-hole | 6820 mm² |
| SMD variants of the passives, diodes, LEDs, U4 to U6, Q1, Q2 and BT1 | 5080 mm² |
| Free top side of the HAT: outline less J1, the holes and the display and camera slots | about 3060 mm² |

Parts never pack at 100 %. A hand layout of through-hole parts reaches about 60 to 70 %.

The screw terminals need 88 mm of edge: J3 and J4 are 36 mm each, J2 and J8 8 mm each. The long edge opposite J1 has 52 mm between the mounting holes. The short edge away from the Pi's USB and Ethernet has 43 mm, or two pieces of 13 mm with the display slot kept.

The HAT outline, hole positions and slots come from KiCad's `template/RaspberryPi-HAT`: board 65 x 56 mm, corner radius 3 mm, M2.5 holes 3.5 mm in from each edge, 58 x 49 mm apart.

Options, for the owner to choose:

- A larger board beyond the HAT standard. Through-hole as drawn needs about 11 000 mm² of free area, for example 100 x 120 mm.
- SMD variants of the named parts on both sides of a HAT, without the footprints of parts not fitted. This is close to the limit and needs a new fit check.
- Two boards: a HAT with the logic, the clock, the audio and the headers, and a field board with the terminals, the output and input stages and the load supply, joined by a ribbon cable.
