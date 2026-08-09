# TW-1A v0.5 C0d per-edge segmented-mismatch learning gate — QUALIFIED

The preregistered gate on untouched bodies 1700–1709 **passes** both the frozen
fabrication-yield predicate and the frozen temporal-order learning predicate.

## Fabrication-yield result

Each body's exact physical target tile contained 112 independently fabricated
segmented edge codebooks at 3% iid unit-cap mismatch.

```text
monotonic fabricated tiles   10/10
monotonic edge codebooks     112/112 on every tile
minimum observed code step   +6.855744e-4 coefficient units
```

No codebook was sorted, repaired, or replaced in software.

## Learning result

```text
qualified                 true
improvement >= +0.10      10/10
final exact wins           10/10
median improvement        +0.581887
median placement gap      +0.494918
minimum improvement       +0.251034
minimum placement gap     +0.191267
```

Per-body exact improvements:

```text
1700  +0.498299
1701  +0.540172
1702  +0.463935
1703  +0.251034
1704  +0.479933
1705  +0.623602
1706  +0.684925
1707  +0.637555
1708  +0.662506
1709  +1.208190
```

All ten exact learners beat their same-credit shuffled controls.

## What this gate added

The previous C0c bridge used one nominal nonlinear capacitor charge-sharing
codebook.  C0d gives **every physical edge cell its own independently mismatched
measured codebook**:

```text
127 fabricated unit caps per edge
unit-cap sigma              3%
Cunit/Csum                  0.001
magnitude topology          4-bit binary + 3-bit thermometer
physical edges per tile     112
```

The controller may choose only among that edge's actual measured levels.

## Architectural consequence

The edge-weight requirement can now be stated more physically:

> TW-1A does not require matched absolute analog weights across the tile. It
> requires a reciprocal, phase-symmetric, monotonic local actuator with an
> exact-zero state and a measured per-cell codebook that remains frozen during
> one physical gradient.

The learning primitive survived substantial variation in the analog level set
from edge to edge.

## Claim boundary

This remains a statistical unit-cap model. It does not include layout-correlated
capacitance gradients, MOS switch parasitics/mismatch, noisy calibration readout,
or drift of the measured codebook during `PARAM_HOLD`.

Bodies 1700–1709 are now spent.

The next design bridge is absolute analog scale: determine useful state-noise
tolerance for the qualified mismatched machine, then translate that normalized
noise budget into candidate state voltage and capacitance through kT/C rather
than treating the arbitrary C0b/C0c absolute capacitor values as silicon sizes.
