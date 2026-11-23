# Board support (test fixture)

A trimmed copy of the table shapes in RobCo-Core `docs/spec/BOARD_SUPPORT.md`.

## Pins

| Pins | Function | Set by |
|---|---|---|
| GPIO 14, 15 | PL011 TXD, RXD at ALT0 | `uart_init()` |
| GPIO 2, 3 | I2C SDA, SCL at ALT0. The board has fixed 1.8 kOhm pull-ups. | `i2c_init()` |
| GPIO 7, 8, 9, 10, 11 | SPI0 CE1, CE0, MISO, MOSI, SCLK at ALT0 | `spi_init()` |
| GPIO 34 to 39, 48 to 53 | SD card routing, see below | `sd_init()` |
| Audio pins, per board below | PWM | `audio_init()` |

| Board | Audio channel 1 | Audio channel 2 |
|---|---|---|
| Pi Zero, Zero W, Zero 2 W | GPIO 18 at ALT5 | None, mono |
| Pi 3 | GPIO 40 at ALT0 | GPIO 41 at ALT0 |

| Input | Pin | Input | Pin |
|---|---|---|---|
| UP | GPIO 5 | BACK | GPIO 27 |
| SELECT | GPIO 26 | | |

## Next section

| Pins | Function | Set by |
|---|---|---|
| GPIO 4 | Not in the Pins section | none |
