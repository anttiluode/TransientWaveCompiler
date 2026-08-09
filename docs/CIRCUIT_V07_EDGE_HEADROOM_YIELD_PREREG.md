# TW-1A v0.7 edge full-scale headroom yield study

This is a **fabrication-yield diagnostic only**. It does not run learning and
cannot qualify or rescue a failed learning corner.

The current v0.7 emulator models 3% RMS independent unit-cap mismatch, but a
127-unit bank averages most of that error away at full scale. A real layout can
also have a site-common ratio error between the edge bank and the node state
capacitor. That common ratio error does not average down across the 127 units.

## Frozen Monte Carlo model

For each of 20,000 synthetic 112-edge tiles:

```text
unit-cap sigma                 3% RMS, independent units
site Cunit/Cstate scale sigma  0.25%, 0.5%, 1%, 2% RMS
nominal positive edge FS       0.255, 0.260, 0.265, 0.270
required physical edge FS      >= 0.250 on all 112 sites
```

The full-scale bank sum is drawn from the exact Gaussian sum implied by 127
independent normal unit errors; the site-common scale is an independent normal
multiplicative factor. At these sigmas negative physical scales have negligible
probability, but any such draw is counted as a failure rather than clipped.

The study reports:

- fraction of 112-edge tiles with all edge ranges >= 0.25;
- 1st percentile of the minimum edge full scale across a tile;
- median minimum edge full scale.

No nominal full-scale or sigma point is added after results are observed.

This study intentionally excludes global die-wide process shift, temperature,
aging and state-cap voltage coefficient. Those require process/device data and
should be represented later as separate common-mode corners rather than hidden
inside the site mismatch number.
