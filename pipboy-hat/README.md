# Pip-Boy HAT

Status: specification only. No schematic, no board. Nobody has built or tested it.

The board turns a Raspberry Pi Zero, Zero W or Zero 2 W into a wrist device that runs Pip-OS and Deitrix. It carries a 2.8 inch ILI9341 SPI display, six keys, a rotary dial with a push button, a small speaker amplifier, a DS1338 clock and a serial console header. Revision 1 has no battery circuit: it runs from the Pi's USB port or a 5 V input header.

- The spec: [spec/SPEC.md](spec/SPEC.md)
- The header map: [spec/pins.yaml](spec/pins.yaml). The pin table in the spec is generated from it.
- The bring-up checklist: [spec/BRINGUP.md](spec/BRINGUP.md)

Check it:

```sh
tools/build.sh check pipboy-hat   # pin check against the software, pin table check
```

With no generator yet, `check` skips the regen-diff and ERC. It compares `pins.yaml` with the pin tables of RobCo-Core `docs/spec/BOARD_SUPPORT.md` and the pin table in the spec with `pins.yaml`.

The owner must still decide the outline with the case: see [section 6 of the spec](spec/SPEC.md#6-size-and-shape).
