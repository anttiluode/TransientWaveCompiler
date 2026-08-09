# TW-1A v0.7 controlled edge-residual split

Status: **diagnostic only; seeds 2000--2009 are already spent**.

The failed formal gate and first diagnosis showed:

- v0.7 formal: 7/10 bodies improved by >= +0.10;
- removing edge thermal alone did not rescue the tail;
- jointly idealizing the edge bank (unit-cap mismatch, edge calibration residual,
  and A/B hold mismatch) restored 10/10;
- the old C0e model is also weak on this same task tail.

This experiment freezes a controlled physical split before observing its result.

## Common starting point

Every condition starts from the exact **v0.7 formal physical draw** for a given
seed, except edge thermal is set to zero in all conditions to make the split
deterministic. The tile is constructed first; only then are selected edge
attributes surgically idealized. This is deliberate: changing config sigmas
before construction can change RNG consumption and redraw unrelated physical
errors.

All non-edge background disorder remains bit-for-bit inherited from the formal
physical realization.

## Frozen edge defects

The three defects under test are:

`caps`
: 3% unit-cap fabrication mismatch, which changes each site's measured physical
  code lattice. Removing it replaces each 127-unit bank by ideal equal unit
  capacitors while retaining nominal Cunit/Cstate and all other disorder.

`cal`
: the 0.1% RMS foreground edge-map measurement residual represented by
  `edge_calibration_error_std`. Removing it replaces the measured effective
  common edge gain by its true held gain without touching the physical codebook.

`lane`
: the 0.1% RMS phase-symmetric A/B post-sample hold mismatch. Removing it sets
  the two lane hold gains to exactly one without changing common edge transfer.

## Frozen conditions

```text
baseline_no_thermal
perfect_caps
perfect_cal
perfect_lane
perfect_caps_cal
perfect_caps_lane
perfect_cal_lane
perfect_all_edge
```

No conditions or magnitudes are added after results are observed.

## Readout

For each condition report the same spent-body learning summary:

```text
count improvement >= +0.10
count final exact > shuffled
median/min improvement
median/min placement gap
seed 2006 / 2007 / 2008 values
```

## Decision rule

Prefer an architectural or calibration change that corresponds to the smallest
single removed defect that restores 10/10. If no single removal restores 10/10,
use pair results to identify the minimal interaction. A fresh qualification is
not opened from this experiment alone; the chosen change must first be stated as
a new physical contract and its own inward target frozen.
