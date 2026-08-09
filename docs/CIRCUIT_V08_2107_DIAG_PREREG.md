# TW-1A v0.8 fresh-gate failure diagnosis

Status: **diagnostic only; seeds 2100--2109 are spent by the failed formal gate**.

The preregistered v0.8 common/difference gate failed narrowly:

```text
fabrication pass       10/10
final exact > shuffled 10/10
improvement >= +0.10    9/10
median improvement     +0.611408
median placement gap   +0.477184
```

Only seed 2107 failed the per-body improvement bar (`DeltaC=+0.035623`).
This diagnostic is frozen before observing any modified result on 2100--2109.

## Same-silicon rule

Every condition starts by constructing the exact formal v0.8 physical draw for
that seed: 0.265 nominal edge range, 3% unit-cap mismatch, 1% site-common ratio
mismatch, `b=1e-5`, and the complete retained background. Only *after* the tile
has been drawn are named defects surgically removed. No condition may alter RNG
consumption or redraw unrelated blocks.

Exact/shuffled target and distractor bodies are kept on one copied physical
realization as in the formal gate.

## Frozen conditions

```text
formal
no_thermal
perfect_switch_kick
perfect_cd_hold
perfect_self_path
perfect_credit_readout
perfect_state_retention
perfect_credit_accumulator
ideal_lcc
perfect_edge_fabrication
perfect_converters
```

Definitions:

`no_thermal`
: set active edge `kT/C` base fraction to zero after construction.

`perfect_switch_kick`
: zero the residual equal/common and differential edge-injection packets seen by
C and D after the fabricated/autozero draw has been made.

`perfect_cd_hold`
: remove the residual phase-symmetric C/D post-sample edge-hold mismatch while
retaining the measured common edge codebook.

`perfect_self_path`
: set effective self gain and measured self gain to one; the existing self-code
resolution remains.

`perfect_credit_readout`
: remove local-credit DC offset and the 25% local-credit readout noise.

`perfect_state_retention`
: set every held state retention factor to one.

`perfect_credit_accumulator`
: set local-credit accumulator leakage to zero.

`ideal_lcc`
: set square-detector curvature to zero.

`perfect_edge_fabrication`
: after the formal draw, replace only the edge coefficient lattice by ideal
127 equal unit capacitors and unity site ratio at the same nominal 0.265 range.
All other blocks keep their exact formal values.

`perfect_converters`
: after construction, disable weight/edge, self, drive, sense and error
quantization and rebuild the programmed Q; all analog disorder remains.

No single-block condition is added or removed after results are observed.

## Readout

For every condition report all ten seeds, with emphasis on 2107:

```text
count improvement >= +0.10
count final exact > shuffled
median/minimum improvement
median/minimum placement gap
seed 2107 improvement/gap/final contrast
```

## Decision rule

If one single removal restores seed 2107 above +0.10 while retaining the other
nine bodies, that block becomes the next quantitative residual target. If no
single removal rescues 2107, freeze a pair split among only the strongest
single-block effects before running any pair. No fresh seed range is reserved
until this diagnosis is complete.
