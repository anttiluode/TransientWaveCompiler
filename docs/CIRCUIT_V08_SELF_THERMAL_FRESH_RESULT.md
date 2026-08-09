# TW-1A v0.8 fresh qualification with self-sampling kT/C — PASS

The preregistered fresh gate in `CIRCUIT_V08_SELF_THERMAL_PREREG.md` passed on
untouched temporal-order bodies 2300--2309.

## Qualified operating point

This supersedes the earlier fresh v0.8 checkpoint by additionally including the
local programmable self-sampling thermal path.

```text
reverse representation                   common/difference C=F, D=A
active virtual charge summing            yes
structural -PREV                          yes
terminal analog clone                    absent
matched +/- error injection              absent
edge nominal positive range               0.265
edge unit-cap mismatch                    3% RMS
site-common Cunit/Cstate mismatch         1% RMS
edge sampling thermal base                b_edge=1e-5
self sampling thermal base                b_self=1e-5
kick-cancellation measurement error       0.5% RMS
common residual kick floor                2e-6 state FS RMS
differential residual kick floor          1e-6 state FS RMS
training iterations                       30
step size                                 0.20
```

The self-noise law is the two-slice reusable-bank result

```text
sigma_self / VFS = b_self * sqrt(|self coefficient|).
```

## Fresh result

```text
fabrication pass                         10/10
improvement >= +0.10                     10/10
final exact > shuffled                   10/10
median improvement                       +0.396735
minimum improvement                      +0.150625
median placement gap                     +0.310108
minimum placement gap                    +0.189134
minimum observed edge full scale          0.257965
mean common residual kick RMS             2.501e-6 state FS
mean differential residual kick RMS       1.097e-6 state FS
maximum programmed |self|                 1.998937
maximum self thermal RMS                  1.414e-5 state FS/tick
```

Per-body improvements:

```text
2300  +0.473804
2301  +0.416401
2302  +0.845009
2303  +0.468451
2304  +0.150625
2305  +0.204581
2306  +0.488580
2307  +0.377069
2308  +0.212647
2309  +0.343390
```

All ten finished above their shuffled-credit controls.

## What this now qualifies

At emulator level, the v0.8 body has now survived simultaneously:

- site-specific measured nonlinear reciprocal edge codebooks;
- 3% unit-cap and 1% site-ratio fabrication mismatch;
- active edge kT/C packets;
- local programmable self-sampling kT/C;
- common/difference reverse coordinates;
- structural history coefficient;
- retained C/D hold mismatch, self gain/calibration residual, state leakage,
  converter precision, square/LCC curvature, credit noise/offset/leakage;
- 0.5% foreground switch-kick cancellation measurement error and the unchanged
  2 ppm / 1 ppm residual floors.

## What remains circuit-level rather than qualified

- transistor OTA slew/output swing/common-mode/PVT/noise/power;
- the physical segmented self-code capacitor array and its measurement codebook;
- the self sample-reference/reset driver used by C1e3;
- the read-only `DeltaC +/- DeltaD` credit-sensor front end;
- the foreground switch-kick measurement/cancellation circuit;
- foundry layout, area and energy.

C1e2/C1e3 already establish a process-independent working self timing of two
20 ns transfers with one reusable half-range bank, a 10 ns reset/resample
aperture, and about 300 MHz GBW in the first-order amplifier model.
