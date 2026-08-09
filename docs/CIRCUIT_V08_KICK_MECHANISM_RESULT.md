# TW-1A v0.8 switch-kick mechanism result

The controlled same-silicon mechanism split in
`CIRCUIT_V08_KICK_MECHANISM_PREREG.md` separated foreground cancellation error
from the independent post-cancellation floor on the spent 2100--2109 bodies.

## Result

The failed formal residual is dominated by **cancellation measurement error**,
not by the residual floor.

```text
condition          >=+0.10  wins  median DeltaC  min DeltaC  seed2107
formal                9/10  10/10    +0.611408   +0.035623  +0.035623
cancel x0.50         10/10  10/10    +0.767690   +0.109373  +0.109373
cancel x0.25         10/10  10/10    +0.728727   +0.275440  +0.275440
cancel x0.10         10/10  10/10    +0.770650   +0.253448  +0.253448
floor x0.50           9/10  10/10    +0.575619   +0.009076  +0.009076
floor x0.25           9/10  10/10    +0.531651   -0.010518  -0.010518
floor x0.10           9/10  10/10    +0.572083   +0.002873  +0.002873
both x0.50           10/10  10/10    +0.750632   +0.172751  +0.172751
both x0.25           10/10  10/10    +0.798389   +0.143423  +0.143423
```

The formal physical components averaged approximately

```text
cancellation component RMS
  common        5.626e-6 state FS
  differential  2.007e-6 state FS

independent floor RMS
  common        1.907e-6 state FS
  differential  0.999e-6 state FS.
```

Reducing only the floor, even by 10x, does not rescue seed 2107. Reducing only
the cancellation component by 2x is sufficient under the frozen predicate,
but sits close to the +0.10 per-body cliff.

## Working circuit target

Do not design to the 2x boundary. The working first-chip target is the already
tested 4x-inward cancellation point:

```text
edge charge-cancellation measurement error <= 0.5% RMS
residual common floor                     <= 2e-6 state FS RMS
residual differential floor               <= 1e-6 state FS RMS
```

The floor targets are **not tightened** relative to the failed formal point;
the evidence does not justify spending circuit area/power there.

At the tested `cancel x0.25` point, the resulting total residuals on these ten
tiles averaged roughly

```text
common       2.387e-6 state FS RMS
 differential 1.097e-6 state FS RMS
```

and the worst sampled tile was about 2.72 ppm common / 1.20 ppm differential.

## Physical interpretation

The next switch-cell effort should prioritize repeatable foreground measurement
and inverse cancellation of the raw packet. Dummy switches/common-centroid
layout may still be useful, but the current learning evidence does not require
lowering the independent floor below its existing 2 ppm / 1 ppm values.

A fresh v0.8 qualification may now be frozen at the 0.5% cancellation-error
point. The failed 2100--2109 bodies remain diagnostic-only.
