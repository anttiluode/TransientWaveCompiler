# TW-1A hardware requirements envelope — temporal-order result v0.4

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V04.md`

## Primary exact-point confirmation

The development-selected exact quantizer point `Q9 / DAC5 / ADC7` was tested on untouched seeds 880–885.

**Result: FAIL.**

Summary:

- median exact contrast improvement: **+0.01869**;
- only 2/6 seeds reached `DeltaC >= 0.10`;
- exact final contrast beat shuffled final contrast in 4/6;
- median placed-vs-shuffled improvement gap: **+0.03481**;
- one exact learner worsened.

Per seed:

| seed | initial C | exact final C | shuffled final C | exact DeltaC | placement gap |
|---:|---:|---:|---:|---:|---:|
| 880 | -0.05905 | -0.10511 | +0.30508 | -0.04606 | -0.41018 |
| 881 | 0 | +0.00756 | +0.01103 | +0.00756 | -0.00346 |
| 882 | 0 | +0.00390 | -0.02331 | +0.00390 | +0.02721 |
| 883 | 0 | +0.02981 | -0.01258 | +0.02981 | +0.04240 |
| 884 | -0.03800 | +0.30684 | -0.43332 | +0.34483 | +0.74016 |
| 885 | -0.24646 | +0.64813 | -0.55982 | +0.89458 | +1.20795 |

Per preregistration, no physical-tolerance sweeps were run.

## Originally requested nominal baseline

The predeclared `8-bit Q / 8-bit DAC / 8-bit ADC + 5% mirror error + 0.2% differential pass drift + 5% local credit noise` control also failed on the same fresh block.

Summary:

- median exact contrast improvement: **+0.05545**;
- 2/6 reached `DeltaC >= 0.10`;
- exact final beat shuffled final in 4/6;
- median placement gap: **+0.04772**.

Therefore the originally proposed nominal mixed-signal baseline is **not demonstrated** by emulator v0.4.

## Emulator-model issue discovered after the frozen result

Inspection after v0.4 revealed that emulator versions through v0.4 quantized the completed Q matrix coefficient-by-coefficient, even though the compiler declares trainable edges with a rank-one edge parameterization.

For a declared trainable edge,

`dQ/dtheta = s (e_i-e_j)(e_i-e_j)^T`.

A single physical edge-cell coefficient should therefore generate its two diagonal and two off-diagonal contributions together. Entrywise quantization snaps those four contributions on different coefficient ranges and destroys that physical parameterization while the credit readout still assumes it.

This does **not** retroactively convert v0.4 into a pass. It means v0.4 is not a faithful test of the compiler-declared edge-cell hardware and motivates a new emulator semantic version before further bit-depth claims.
