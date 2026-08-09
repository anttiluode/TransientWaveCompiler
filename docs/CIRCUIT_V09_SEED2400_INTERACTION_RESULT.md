# TW-1A v0.9 seed 2400 same-draw interaction diagnosis — result

Date: 2026-08-09

Status: **diagnostic on spent seed 2400. The weak body is a switch-residual interaction, not thermal noise, codebook error or a single converter/credit defect.**

Fresh seed 2400 had

```text
formal v0.9 DeltaC       +0.025219
ideal physical-credit    +0.864382
```

and remained weak when all edge/self/drift thermal noise was removed. The subsequent static diagnosis therefore used the exact same formal fabrication draw and disabled thermal only **after construction**.

## Single-block split

Common all-thermal-zero baseline:

```text
DeltaC +0.047842
```

| surgery | DeltaC | gain vs baseline |
|---|---:|---:|
| no inherited edge switch kick | +0.093745 | +0.045903 |
| no drift switch residual | +0.081666 | +0.033824 |
| ideal edge codebook | +0.062030 | +0.014188 |
| exact kick-self gain | +0.058980 | +0.011138 |
| no state leakage | +0.055303 | +0.007461 |
| ideal credit path | +0.054785 | +0.006943 |
| ideal converters | +0.052692 | +0.004850 |
| exact C/D edge lane holds | +0.047842 | approximately zero |
| all support blocks clean | **+0.791364** | +0.743522 |

No single block clears +0.10. The complete support cleanup approaches the ideal-control behavior, proving the task itself is strongly learnable and the weakness is a multi-block interaction.

## Frozen pair split

All six pairs among the four strongest individual surgeries were tested on the identical draw:

| pair | DeltaC | placement gap |
|---|---:|---:|
| edge kick + drift residual | **+0.706913** | +0.711339 |
| edge kick + edge codebook | +0.086785 | +0.091794 |
| edge kick + kick-self gain | +0.095441 | +0.100574 |
| drift residual + edge codebook | +0.077598 | +0.082504 |
| drift residual + kick-self gain | +0.092600 | +0.097436 |
| edge codebook + kick-self gain | +0.067444 | +0.071344 |

Only one pair rescues the body: **the inherited edge-switch residual together with the new drift-shear switch residual**.

This is important because it exonerates the new kick-drift coordinate change itself, edge capacitor mismatch, self calibration, leakage and acquisition path as primary causes of seed 2400's failure.

## Simultaneous residual scale

The already-drawn edge and drift residual spatial fields were then scaled together while all other static blocks remained untouched:

| scale | edge A RMS | edge A-B RMS | drift C RMS | drift C-D RMS | DeltaC |
|---:|---:|---:|---:|---:|---:|
| 1.00 | 2.55 ppm | 2.06 ppm | 7.26 ppm | 5.38 ppm | +0.047842 |
| 0.75 | 1.91 ppm | 1.54 ppm | 5.44 ppm | 4.04 ppm | +0.057925 |
| 0.50 | 1.27 ppm | 1.03 ppm | 3.63 ppm | 2.69 ppm | +0.074084 |
| 0.25 | 0.64 ppm | 0.51 ppm | 1.81 ppm | 1.35 ppm | +0.096319 |
| 0.10 | **0.25 ppm** | **0.21 ppm** | **0.73 ppm** | **0.54 ppm** | **+0.304593** |
| 0 | 0 | 0 | 0 | 0 | +0.706913 |

The coarse ladder therefore places the seed-2400 interaction transition between 0.10x and 0.25x of the current post-cancellation residual fields. The result is deliberately not interpreted as a requirement that raw MOS switch injection itself be sub-ppm.

## Circuit interpretation

Both offending fields are **static post-cancellation residuals**. A second-stage aggregate node-level trim that measures the already-small residual and leaves about 10% of it would reproduce the 0.10x diagnostic point without requiring each physical switch to become intrinsically 10x better.

That turns the likely first-chip question into:

> Can the aggregate edge-kick and drift-shear residual seen by each state node/context be foreground-measured and trimmed to about 10% of its present residual before `PARAM_HOLD`?

A spent-cohort replay with full `b=2e-5` thermal noise restored and exactly 0.10x residual fields is the next gate. Only after that should a concrete local trim capacitor/DAC and measurement sequence be specified.
