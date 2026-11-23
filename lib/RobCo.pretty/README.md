# RobCo footprints

Own footprints go here, one `.kicad_mod` file each. Each project's `fp-lib-table` reaches this folder as the library `RobCo` through `${KIPRJMOD}/../../lib/RobCo.pretty`, so the CI image finds it with the checkout.

| Footprint | Part | Dimensions, all to verify |
|---|---|---|
| `Fuse_PTC_Radial_W10.0mm_T3.5mm_P5.10mm` | F1, radial PTC fuse, 1.1 A hold, 60 V, such as Littelfuse RXEF110 | Body 10.0 x 3.5 mm, leads 5.1 mm apart, drill 1.0 mm |
| `Fuse_PTC_Radial_W7.4mm_T3.0mm_P5.10mm` | F2, radial PTC fuse, 200 mA hold, 60 V, such as Bourns MF-R020 | Body 7.4 x 3.0 mm, leads 5.1 mm apart, drill 0.8 mm |
| `PAM8302A_Module_1x07_P2.54mm` | M1, PAM8302A breakout module | One row of 7 pins on 2.54 mm in the symbol's order, module outline 20.3 x 17.8 mm |

Every dimension comes from memory of a data sheet or a module photo. Check each one against the part you buy. None has a 3D model.
