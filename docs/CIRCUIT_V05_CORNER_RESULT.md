# TW-1A v0.5 phase-symmetric simultaneous corner — QUALIFIED

The preregistered gate on untouched bodies 1500–1509 **passes** the frozen
qualification predicate.

## Frozen predicate

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

## Result

```text
qualified                 true
improvement >= +0.10      10/10
final exact wins           10/10
median improvement        +0.500078
median placement gap      +0.546270
minimum improvement       +0.227308
minimum placement gap     +0.052463
```

Per-body improvements:

```text
1500  +0.673003
1501  +0.252065
1502  +0.684043
1503  +0.685741
1504  +0.367690
1505  +0.967545
1506  +0.485463
1507  +0.340398
1508  +0.227308
1509  +0.514693
```

All ten final exact learners beat their same-credit shuffled controls.

## What changed from the failed v0.4 corner

The calibration-first v0.4 corner had already improved the simultaneous result
to 8/10, but its spent-body diagnosis isolated one dominant residual: a 10% B-
only edge settling loss.  Removing only that error rescued all ten spent bodies.
Removing A->B memory or error-DAC sign asymmetry alone did not.

v0.5 therefore does not tighten the old B settling tolerance.  It deletes the
A-first/B-second transfer model:

1. settle the shared calibrated reciprocal edge transfer;
2. sample it into matched A and B local holds;
3. only after both holds exist, evaluate the two reverse lanes;
4. never use the just-evaluated A edge node as the source of B's coefficient.

The formal v0.5 gate used:

```text
raw common edge settling loss     10%
post-settle A/B hold mismatch      0.1% RMS
legacy B-only settling loss        0
legacy A->B edge memory            0
```

The common 10% settling loss is part of the foreground measured edge transfer
map, so it is common to forward/A/B and inverse-programmed like static edge gain.

## Other nonidealities retained in the passing gate

```text
edge / self raw gain CV           10% / 10%
edge / self calibration residual  0.1% / 0.1%
raw -PREV mismatch                 3% RMS
-PREV calibration residual         0.1%
raw terminal clone mismatch        5% RMS
clone calibration residual         0.1%
raw switch charge common/diff      3e-4 / 1e-4 FS
autozero cancellation error        2%
charge residual floors             2e-6 / 1e-6 FS
error DAC sign asymmetry           10%
credit noise fraction              25%
credit offset fraction             1.5e-4
LCC curvature                      1.0
credit accumulator leakage         0.01/tick
state leakage                      5e-4/tick, CV 0.50
state noise                        5e-9 FS
```

Thus qualification is not the result of making the rest of the emulator ideal.

## Claim boundary

This is an **emulator-level architecture qualification**, not a transistor-level
claim.  The next gate is SPICE: demonstrate that a concrete matched pre-settle /
dual-hold edge cell can meet the residual A/B mismatch, charge-cancellation,
calibration range, and settling/headroom contracts while preserving the required
reciprocal rank-one edge action.

Bodies 1500–1509 are now spent and may not be reused for a future formal corner.
