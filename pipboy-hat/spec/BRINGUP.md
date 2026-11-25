# Pip-Boy HAT bring-up

> **This is a proposal.** Nobody has built or tested this board. This checklist has never run on a real board.

See [SPEC.md](SPEC.md) for the circuit, the nets and the test points.

## Bring-up and test checklist

Do each step in order. Stop at the first failure. Use a bench supply with a current limit for the steps without the Pi. Fit the CR1220 cell in BT1 before the first power-up, or close JP1 if you run without a cell. VBAT must not float.

J3 takes a regulated 5 V source only. The board does not survive a 9 V or 12 V adapter. Never plug a USB cable into the Pi while J3 is powered: the Zero's data port would feed the computer's VBUS, and its power port would fight J3.

### Before power

| Step | Action | Expected result | Software |
|---|---|---|---|
| 1 | Visual check: polarity of D1, D2, C31, C33, C52, BT1; pin 1 of U1; Q3's gate, source and drain against the part's data sheet; the flat side of Q1, Q2 and U3; RV1 and M1 orientation. No solder bridges on U1 or J7. JP1, JP2 and JP3 open. | All parts oriented as the silkscreen shows | None |
| 2 | Check J1's pin 1 against the Pi Zero's pin 1, with the Pi face up below the board. Check J2's pin names against the module bought. | Pin 1 meets pin 1. The module's VCC, GND, CS, RESET, DC, SDI, SCK and LED match J2 pins 1 to 8. J2 pin 9, SDO, goes to JP3 only. | None |
| 3 | No Pi, no module. Resistance from `+3V3`, `+5V` and `V_EXT` to `GND`, and from `+3V3` to `+5V`. | No short. Several kOhm or more. | None |

### First power, no Pi

| Step | Action | Expected result | Software |
|---|---|---|---|
| 4 | No Pi, no module. 5.0 V on J3, limit 100 mA. | TP2 within 0.1 V of the supply. Current under 10 mA: only M1 idles. TP1 near 0 V. | None |
| 5 | No Pi, no module. Reverse 5.0 V on J3, limit 100 mA, for 10 seconds. Meter on TP2. | Supply current under 1 mA. TP2 stays at 0 V, within 0.05 V. Nothing warms: not F1, not Q3, not D1. If the supply hits its limit, Q3 is in backwards or its pins are swapped: stop. Restore the polarity: TP2 returns to within 0.1 V of 5 V. | None |
| 6 | No Pi, module fitted. 3.3 V from a second supply on TP1, limit 200 mA. 5 V on J3. Ground both supplies together. | Backlight on: R20 holds Q2 on. Current from the 3.3 V supply 120 mA or less. Note it. TP7 at 3.0 V or more. The current may be well under 100 mA: the LEDs' forward voltage is high at 3.1 V, or the module switches its LEDs with its own transistor. Note which, and whether the screen is bright enough, see SPEC.md section 4.2. | None |
| 7 | Same set-up. Short `TFT_BL`, header pin 35, to `GND` with a 100 Ohm resistor. | Backlight off. TP7 under 0.2 V. 3.3 V current drops by the backlight current. Remove the resistor. | None |

### With the Pi

| Step | Action | Expected result | Software |
|---|---|---|---|
| 8 | Fit the Pi Zero. Power through the Pi's USB power port only, from a USB meter. J3 open. Boot Pip-OS with no `PIPOS.CFG`. | TP2 4.75 V or more. TP1 3.2 V to 3.4 V. Total current 0.4 A or less on a Zero. Backlight on. | Pip-OS boot |
| 9 | Serial console on J4 with a 3.3 V FTDI cable at 115200 8N1. | `@RC` lines from Pip-OS. Typed keys reach the Pi. | Pip-OS console |
| 10 | Same boot. Look for the clock. | `ev=rtc present=1`, `chip=0`. A new chip gives `RTC_ERR_HALTED` until set. | Pip-OS boot markers |
| 11 | Set the time. Power off for an hour with the cell fitted, then boot. | The time moved on by the hour. Deitrix shows `HH:MM`, not `--:--`. | Deitrix status line |
| 12 | Each key, SW1 to SW6. | One press and one release per click, the right key name: up, down, left, right, select, back. | Deitrix, or the RobCo-Core `examples/input` |
| 13 | Turn the dial slowly one detent at a time, both ways. Press it. | One step per detent. Clockwise is positive. One `dial_push` press per click. If it counts the wrong way, swap A and B in the build, not on the board. | Deitrix tab changes, or `examples/input` |
| 14 | Turn the dial steadily at half a turn per second, 12 detents per second, for several turns both ways. Then turn it slowly. | One step per detent, none in the wrong direction. After the fast turns, slow clicks still count on the click, not between clicks. Faster than about 12 detents per second is a software limit, see SPEC.md section 4.4. | Deitrix |
| 15 | Write the display lines below into `/PIPBOY/PIPOS.CFG` without `tft_backlight`. Reboot. | Deitrix on the panel, landscape, right way up, true colours. Upside down: add `tft_rotation = 270`. Red and blue swapped: add `tft_bgr = no`. Colours inverted: add `tft_invert = yes`. | Pip-OS `[display]` |
| 16 | Optional, debug only. Power off. Take any card out of J7. Close JP3. Boot and read the panel id. Power off and open JP3 again. | `tft_read_id()` returns an id, not `TFT_ERR_NO_PANEL`. All zeros or all ones means JP3 is open or the module does not drive SDO. With JP3 open the call returns `TFT_ERR_NO_PANEL`: that is the normal state. | A Pip-OS display marker if the branch prints the id, else a RobCo-Core test build that calls `tft_read_id()` |
| 17 | Add `tft_backlight = 19`. Reboot. Turn the display off with `power` off in Deitrix, then on. | Backlight off while the display is off. On again with it. | Pip-OS `[display]` |
| 18 | Audio. First measure the module's input impedance. Unplug the speaker from J6. Set RV1 to its maximum. `[audio] volume = 100`. Play a 1 kHz tone. With the oscilloscope AC-coupled, read the peak at `AUD_DC`, Vs, on R31 at its end toward C31, and at TP6, Vt. Zin and RV1 in parallel make P = 33 kOhm x Vt / (Vs - Vt). Zin = 1 / (1 / P - 1 / 10 kOhm). Then set RV1 to its minimum, plug the speaker in, play the power-on beep and a tune, and raise RV1 with the oscilloscope across J6 and a USB meter on the supply. | Vs near 1.65 V peak. Zin between 10 kOhm and 100 kOhm; note it. Outside that range, recompute R31 with SPEC.md section 4.5. Beep and tune on the speaker. Stop raising RV1 at 2 V peak across the speaker, 0.5 W in 8 Ohm with the square-wave tones, or where the supply current rises by 150 mA over idle, whichever comes first. RV1 should stop between 30 % and 50 % of its travel: about 47 % for Zin of 10 kOhm, 34 % for 100 kOhm. Note where. No distortion below that. | Pip-OS beep, Deitrix RADIO |
| 19 | Same set-up. `[audio] volume = 30`. | Quieter, no distortion. | Pip-OS `[audio]` |
| 20 | Every USB cable off the Pi. J3 from a USB power bank lead. Run Deitrix with sound for 10 minutes. Measure J3 pin 1 and TP2 under sound. | Drop from J3 pin 1 to TP2 0.21 V or less: F1 0.15 V warm plus Q3 0.055 V. TP2 4.43 V or more, the worst case of SPEC.md section 4.8. That margin is thin. Below 4.6 V, note it and try a shorter lead. No reset. F1 and Q3 warm at most. Total current 0.55 A or less. | Deitrix |
| 21 | Zero 2 W in place of the Zero, if Pip-OS runs on it. Repeat steps 8, 18 and 20. | Same results. Total current 0.55 A or less with sound. | Pip-OS boot |

### Holotape slot

See SPEC.md section 4.12. Steps 22 to 24 run before any card goes in. Card detect and write protect levels are from memory of the socket: if they come out swapped, note it for the software, do not rework the board.

| Step | Action | Expected result | Software |
|---|---|---|---|
| 22 | No Pi, no module, no card. Resistance from `SD_3V3`, TP9, to `GND` and to `+5V`. Then 5.0 V on J3, limit 100 mA. Meter on TP9. | No short. TP9 3.23 V to 3.37 V (U3 at 2 %, typical, check). Supply current under 10 mA more than step 4. U3 stays cold. | None |
| 23 | Same set-up, plus 3.3 V on TP1 as in step 6. Meter on header pins 26, 32 and 33, and on J7 pins 8 and 9. | Pin 26, `HOLO_CS`, 3.3 V: R50 holds the card deselected. Pins 32 and 33 at 3.3 V: no card, both switches open. J7 pins 8 and 9 at `SD_3V3`. Header pin 21, `SPI_MISO`, at 3.3 V through R53. | None |
| 24 | Fit the Pi. Boot Pip-OS with the display running. Scope on R54 at J7, the card side of `SD_CLK`, and on J7 pin 1. No card. | `SD_CLK` shows the display's clock, clean edges, overshoot under 0.5 V. J7 pin 1 stays high through every display frame. | Pip-OS boot |
| 25 | Power off. Insert a card with the slider on unlock. Boot. Meter on header pins 32 and 33. Then move the slider to LOCK, power off, insert, boot, measure again. | Unlocked: pin 32 low, pin 33 low. Locked: pin 32 low, pin 33 high. Card out: both high. | None |
| 26 | Card in, a tape file on it. Load it with the holotape driver at 400 kHz, then at 9.62 MHz. Scope on `SD_CLK` at J7 and on header pin 21. USB meter on the supply. | The card answers its initialisation and the file loads with no read error. MISO edges reach 3.0 V and 0.3 V within a quarter of a clock period. A 256 KB tape loads in about 0.4 s. Supply current rises by 100 mA at most while it loads. The display keeps working after the load. | The holotape driver, once it exists |
| 27 | Hot insertion. Pip-OS running, display on, power from a USB power bank through J3. Scope on TP9 and on TP1 at 1 ms per division, trigger on TP9 falling, a second channel on TP2. Push a card in. Repeat ten times, then pull it out ten times. | TP9 dips to 2.9 V or more and recovers within 1 ms. TP1, `+3V3`, moves by under 0.1 V. TP2, `+5V`, dips by 0.15 V or less. No reset of the Pi, no glitch on the display. If the Pi resets, note the TP2 minimum and see SPEC.md section 4.12, Risks. | Pip-OS running |

## Configuration lines

`/PIPBOY/PIPOS.CFG` for this board. Only `backend` and `tft_backlight` differ from the defaults. The other display keys are listed with their defaults for reference and can be left out.

```
[display]
backend = tft
tft_backlight = 19
; defaults, shown for reference:
; tft_cs = 0
; tft_dc = 25
; tft_reset = 4
; tft_hz = 10000000
; tft_rotation = 90
; tft_bgr = yes
; tft_invert = no

[audio]
volume = 80
```

The `[display]` keys come from a Pip-OS branch not yet merged. Check their names and the value format of `tft_hz` once it merges. Use `backend = both` to keep HDMI as well.
