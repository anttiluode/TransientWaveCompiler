# TW-1A v0.3 key-primitive sweep preregistration

Status: **frozen before v0.3 sweep results are inspected**.

TW-1A v0.3 changes two circuit primitives after the formal v0.1 simultaneous-corner failure and its spent-body diagnostics:

1. edge switch injection is charge-balanced into a common component and a residual differential component;
2. the large node self MDAC is foreground calibrated and programmed through a measured per-node gain map.

This experiment asks whether those architectural changes actually remove sensitivity to *raw* mismatch and move the specification onto the intended residual quantities.

## Bodies / training

Fresh temporal-order bodies: **1250-1254**.

- 25 updates;
- step size 0.20;
- RMS-normalized host update;
- norm-matched shuffled-credit control;
- 8-bit edge, 12-bit self, 8-bit drive, 10-bit error, 8-bit sense + static PGA;
- no legacy independent edge injection;
- no old leakage/noise/readout background in this primitive-isolation experiment.

Qualification at each grid value is the same frozen predicate used in the prior one-axis work:

- >=4/5 placed learners improve by >= +0.10;
- median placed improvement >= +0.20;
- >=4/5 placed final > shuffled final;
- median placement gap > 0.

## Axis A — raw self-MDAC gain CV with perfect gain measurement

Purpose: raw process mismatch should cease to be the effective self-coefficient error once the controller pre-distorts the code.

```text
self_gain_cv:
0, .03, .10, .20, .30, .50

self_calibration_error_std = 0
```

No other v0.3 circuit error is active.

**Kill condition:** if 10% raw self gain CV materially destroys learning even with perfect calibration, the calibration abstraction is wrong or code headroom is insufficient.

## Axis B — self-calibration gain-estimate residual

Raw `self_gain_cv = .10` is held fixed. Sweep:

```text
self_calibration_error_std:
0, .0001, .0003, .001, .003, .01, .03
```

This is the quantity the foreground calibration circuit/algorithm must actually meet.

## Axis C — common charge injection

Perfect self calibration; raw self gain CV .10. Differential charge residual is zero.

```text
edge_charge_injection_common_std / state FS:
0, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3
```

The common packet is replayed in forward and both reverse lanes. If the architecture is correct it should be much less harmful than independent A/B injection.

## Axis D — residual differential charge injection

Perfect self calibration; raw self gain CV .10. Common injection fixed at `1e-4` state FS RMS per active edge/tick.

```text
edge_charge_injection_differential_std / state FS:
0, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4
```

This is the new switch-balancing specification.

## Boundary convention

As before, report the largest qualified grid point before the first failed point if monotone. If no failure occurs, report a lower bound only. The inward design value is one frozen grid step inside the measured boundary.

These primitive sweeps do not qualify a simultaneous corner.