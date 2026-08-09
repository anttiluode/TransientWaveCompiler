# TW-1A v0.4 calibration-first simultaneous corner — result

The preregistered corner on untouched bodies 1400–1409 **failed** the frozen
qualification predicate and is retained as a formal failure.

## Frozen predicate

```text
10/10 exact improvement >= +0.10
10/10 final exact > final shuffled
median exact improvement >= +0.30
median placement gap      >= +0.25
```

## Result

```text
qualified                 false
improvement >= +0.10      8/10
final exact wins           9/10
median improvement        +0.375795
median placement gap      +0.434292
minimum improvement       -0.067219
minimum placement gap     -0.047972
```

The medians pass strongly, but the all-body requirements do not.

## Failed / marginal bodies

```text
seed 1401
  DeltaC  +0.026430
  gap     +0.103259
  final exact still beats shuffled

seed 1403
  DeltaC  -0.067219
  gap     -0.047972
  final exact loses to shuffled
```

The other eight bodies clear +0.10, and nine of ten finish above shuffled
credit.

## Comparison with v0.3

The v0.3 simultaneous corner produced only 5/10 bodies above +0.10 and median
DeltaC about +0.087.  v0.4 reaches 8/10 and median +0.376 while intentionally
using larger raw process mismatch on calibrated blocks:

```text
raw edge gain CV       10%
raw self gain CV       10%
raw -PREV mismatch      3%
raw clone mismatch      5%
raw common switch kick  3e-4 FS
raw diff switch kick    1e-4 FS
```

Thus calibration-first is a substantial improvement, but not yet a qualified
simultaneous envelope.

## Status of bodies

Bodies 1400–1409 are now spent.  They may be used for diagnosis only.  Any
revised formal corner must use untouched bodies.
