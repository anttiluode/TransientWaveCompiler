# TW-1A v0.9 kick-drift fresh qualification — preregistration

Date: 2026-08-09

Status: **fresh seeds 2400..2409 reserved; become spent when the formal workflow begins.**

The spent-body simultaneous reference at 5 ppm common + 5 ppm C/D differential drift-switch residual passed every frozen predicate. This document freezes the complete v0.9 emulator point for fresh qualification without any further tuning.

## Architecture

```text
state coordinates       Z = z[n], P = z[n]-z[n-1]
operator                K = Q - 2I
forward/reverse tick    P <- P + K Z + source/error
                        Z <- Z + P
reverse coordinates     common/difference C/D
terminal C mirror       Z <- Z-P, P <- -P
terminal D boundary     Z = error_T, P = error_T
local credit            1/4 sum[(DeltaC+DeltaD)^2-(DeltaC-DeltaD)^2]
```

The representation uses the same two live state vectors per context as the previous CUR/PREV design. Reciprocal edge coefficients are unchanged by `Q -> Q-2I`.

## Frozen physical parameters

```text
tile                                   8 x 8 / 64 nodes
physical reciprocal edges              112
edge nominal positive full scale       0.265
compiler-required edge range           0.250
edge magnitude units/site              127
edge segmentation                      4-bit binary + 3-bit thermometer
edge unit-cap mismatch                 3% RMS
site-common Cunit/Cstate mismatch      1% RMS

kick-residual self signed range        +/-0.125
kick-residual self resolution          10 bits

edge thermal base                      2e-5
kick-self thermal base                 2e-5
unity-drift thermal base               2e-5

inherited edge kick cancellation err   0.5% RMS
inherited edge residual floors         2 ppm common / 1 ppm differential

drift post-cancel common residual      5 ppm state FS RMS
drift post-cancel C/D differential     5 ppm state FS RMS

all converter, state-leakage,
LCC, credit noise/offset/leakage        unchanged from v0.8 fresh-qualified point
```

The drift-switch numbers are direct **post-cancellation residuals**, not claims about raw MOS charge injection.

## Frozen learning protocol

```text
fresh task/fabrication seeds   2400..2409
parameter updates              30
step size                      0.20
credit update normalization    RMS normalization enabled
sense PGA                      same task-static recommender
control                        same-credit fixed shuffled-edge permutation
```

## Physical audit required before learning on each seed

```text
112/112 monotonic edge codebooks
all site ratios positive
minimum physical edge positive range >= 0.250
kick-residual target within +/-0.125
```

Report realized spatial RMS of drift C, D and C-D residual fields and kick-self maximum.

## Formal success predicate

All clauses must pass:

```text
fabrication audit                      10/10
exact improvement >= +0.10             10/10
final exact > same-credit shuffled     10/10
median exact improvement               >= +0.30
median placement gap                   >= +0.25
```

No individual minimum placement-gap threshold is added beyond `final exact > shuffled`; the median gap clause is the preregistered placement requirement used throughout this sequence.

## Interpretation

- PASS: v0.9 becomes the fresh-qualified **emulator architecture** and the preferred first-chip candidate, subject to transistor/noise/area validation of the active shears and credit frontend.
- FAIL: retain the failure exactly. Do not change the 5/5 ppm contract or thermal bases on these seeds; diagnose only after all 2400..2409 are spent.
