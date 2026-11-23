# Terminal controller bring-up

> **This is a proposal.** Nobody has built or tested this board. This checklist has never run on a real board.

This checklist was section 10 of the board specification. See [SPEC.md](SPEC.md) for the circuit, the nets and the test points.

## Bring-up and test checklist

Do each step in order. Stop at the first failure. Use a bench supply with a current limit.

| Step | Action | Expected result | Software |
|---|---|---|---|
| 1 | Visual check: polarity of D1 to D4, D10 to D17, C1, C4, C9, C31, the LEDs, U1 to U6 pin 1, the zener. No solder bridges on the SOIC parts. | All parts oriented as the silkscreen shows | None |
| 2 | No Pi. Resistance from `+3V3`, `+5V`, `V_PROT` to `GND`. | No short. Several kOhm or more. | None |
| 3 | No Pi. 12 V on J2 with JP1 at 1-2, limit 100 mA. | TP6 about 11.5 V. TP7 near 0 V. LED8 off. Current a few mA. | None |
| 4 | No Pi. Reverse the supply on J2. | No current. Nothing warms. | None |
| 5 | No Pi. Fit JP8 briefly. | TP7 follows TP6. LED8 on. Remove JP8. | None |
| 6 | No Pi. 12 V on J2, limit 1 A. Fit JP10. Connect a 120 Ohm, 5 W resistor from J4 `+V` to J4 `COM` for 5 minutes. | 12 V / 120 Ohm = 0.1 A, below F2's 200 mA hold. `+V` stays near 11.5 V. F2 does not trip. The resistor runs warm at 1.2 W. | None |
| 7 | Same set-up. Replace the resistor with 10 Ohm, 5 W, for 1 minute. | About 12 V / (10 + 2) Ohm = 1 A at first, with F2 near 2 Ohm (typical, check). F2 trips within seconds. The current then falls to tens of mA. Only F2 warms. TP6 stays near 11.5 V. Remove the resistor: `+V` returns within a minute. | None |
| 8 | Fit the Pi, no load supply. Boot the RTC example. | `@RC stage=rtc ev=scan found=0x20,0x21,0x68 errors=0` | `examples/rtc` |
| 9 | Same run. | `ev=rtc present=1`, `chip=0`. A new chip gives `RTC_ERR_HALTED` until set. | `examples/rtc`, HARDWARE_VALIDATION.md section "RTC module" |
| 10 | Power off the Pi for an hour with the cell fitted, then boot. | The time moved on by the hour | `examples/rtc` |
| 11 | Load supply on, 12 V. Pi running UOS with no expander devices. | All output LEDs off. LED8 off. | Pending: UOS on hardware |
| 12 | Drive GPIO 25 high through the ARM device. | LED8 on. Output LEDs still off. | `SHOW DEVICES` in UOS, ARM `ON` |
| 13 | A 12 V LED with a 1 kOhm resistor on each output in turn. Turn the channel on, then off. | Only that LED and the status LED light. | Pending: the expander driver and the `X0.n` syntax |
| 14 | Reboot the Pi with output 0 on. | LED8 goes off at reset. Output 0 load stays dark through the reboot. | Pending, as above |
| 15 | Each input: bridge `+V` to `INn`. | The expander reads that bit as 0. The device shows `TRIPPED`. | Pending: the expander driver. `SHOW DEVICES` in UOS. |
| 16 | 5 V on J2 at its lowest, 4.75 V, with R60 to R67 at 1 kOhm and JP10 fitted. Bridge `+V` to all eight inputs at once. | The expander reads `0x00`. Each `X1.n` measures 0.4 V or less. With no sensors on `+V_S`, J4 `+V` measures 4.75 - 0.45 - 22 mA x 8 Ohm = 4.12 V or more, with 8 x 2.75 mA = 22 mA in the inputs. | Pending: the expander driver |
| 17 | Audio on a Zero, JP9 on GPIO18. | Beep, arpeggio and tune on the speaker. RV1 sets the volume. | `examples/audio`, keys `b`, `s`, `t` |
| 18 | Audio on a Pi 3, JP9 on the jack, cable from the Pi's jack to J10. | Same sounds | `examples/audio` |
| 19 | Each button. The board has no dial. | One press and one release per click. `ev=gpio status=active`. | `examples/input` |
| 20 | Serial console on J6 with a 3.3 V FTDI cable at 115200 8N1. | `@RC` lines appear, typed keys reach the Pi | Every example |
