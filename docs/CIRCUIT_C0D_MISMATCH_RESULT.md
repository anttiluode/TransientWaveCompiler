# TW-1A C0d capacitor mismatch architecture study — result

The frozen 5000-sample-per-point study compared three ways to select the same
127 nominal unit capacitors under iid unit mismatch.

## Monotonic yield

| unit-cap sigma | pure binary | segmented 4+3 | full thermometer |
|---:|---:|---:|---:|
| 0.1% | 100.00% | 100.00% | 100.00% |
| 0.3% | 100.00% | 100.00% | 100.00% |
| 1% | 100.00% | 100.00% | 100.00% |
| 3% | 99.82% | **100.00%** | 100.00% |
| 5% | 95.60% | **99.94%** | 100.00% |
| 10% | 70.48% | 83.74% | 100.00% |

No generated unit capacitor was nonpositive at any frozen point.

## Binary carry failure appears exactly where expected

At 3% mismatch, the pure binary array already showed nine non-monotonic samples
out of 5000.  The dominant failing transition was

```text
63 -> 64
```

At 5%, pure-binary monotonic yield fell to 95.6%, again dominated by the
`63->64` carry.

The 4+3 segmented array replaces the 64-unit binary branch with ordered 16-unit
thermometer segments.  It remained 5000/5000 monotonic at 3% and 4997/5000 at
5%.  Its remaining high-mismatch failures are smaller carry boundaries such as
`63->64` / `31->32`, where one 16-unit segment replaces the 15-unit lower bank.

## Calibrated gap size

99th-percentile worst nearest-code half-gap, normalized to each fabricated
cell's measured code-127 full scale:

| unit-cap sigma | pure binary | segmented 4+3 | full thermometer |
|---:|---:|---:|---:|
| 0.1% | 0.4938% FS | 0.4938% FS | 0.4938% FS |
| 0.3% | 0.4973% FS | 0.4973% FS | 0.4962% FS |
| 1% | 0.5324% FS | 0.5276% FS | 0.5050% FS |
| 3% | 0.7140% FS | 0.6520% FS | 0.5323% FS |
| 5% | 0.9051% FS | 0.7774% FS | 0.5596% FS |
| 10% | 1.4729% FS | 1.1216% FS | 0.6350% FS |

Thus segmentation improves both yield and calibrated worst-gap behavior without
requiring full unary selection.

## Selected working topology

The next physical edge DAC uses **4-bit binary + 3-bit thermometer segmentation**:

```text
lower bank: 1, 2, 4, 8 unit groups
upper bank: seven ordered 16-unit thermometer segments
units total: 15 + 7*16 = 127
selectable magnitude branches: 4 + 7 = 11
```

Nominally this produces exactly the same total selected capacitance `m*Cunit` for
magnitude code `m=0..127`, so the already-qualified nominal C0c codebook does not
change.

The working inward mismatch target for the next bridge is

```text
unit capacitor sigma <= 3%
```

because the frozen Monte Carlo observed 5000/5000 monotonic segmented cells at
that point while preserving large margin relative to the 5% onset of rare
failures.

## Claim boundary

This Monte Carlo is a unit-capacitance statistical model, not a process/PVT
layout extraction.  It does not include spatial gradients, correlated mismatch,
bottom-plate parasitic, switch overlap capacitance, or edge-to-edge common-mode
variation.

The next gate therefore gives **each physical edge its own fabricated 3%-sigma
segmented codebook**, measures/uses that codebook for calibration, and reruns the
v0.5 temporal-order learner on untouched bodies.  A later extracted-layout C0d
SPICE study must replace the iid unit model.
