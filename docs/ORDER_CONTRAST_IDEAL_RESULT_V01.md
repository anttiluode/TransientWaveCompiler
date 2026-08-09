# TW-1A temporal-order contrast benchmark — ideal result v0.1

Preregistration: `docs/ORDER_CONTRAST_IDEAL_PREREG_V01.md`

Workflow: `order-contrast-ideal-v01`

Frozen holdout seeds: 840–849.

## Result

**QUALIFIED: PASS (6/6 registered criteria).**

Across all ten ideal 40-cell irregular arbors:

- every exact learner had positive contrast improvement;
- 10/10 had `DeltaC_exact >= 0.10`;
- median exact contrast improvement: **+0.655179**;
- exact final contrast beat shuffled final contrast: **10/10**;
- median placed-credit improvement advantage over shuffled credit: **+0.621240**;
- all values remained finite.

Per-seed exact contrast improvements were:

| seed | C initial | C exact final | C shuffled final | Delta C exact | placement gap |
|---:|---:|---:|---:|---:|---:|
| 840 | +0.6760 | +0.8388 | +0.5721 | +0.1628 | +0.2667 |
| 841 | +0.2908 | +0.8477 | +0.3335 | +0.5569 | +0.5142 |
| 842 | +0.5588 | +0.7963 | +0.4798 | +0.2375 | +0.3166 |
| 843 | +0.3563 | +0.9173 | +0.4365 | +0.5610 | +0.4808 |
| 844 | +0.0120 | +0.8648 | +0.1048 | +0.8528 | +0.7600 |
| 845 | +0.0694 | +0.7199 | +0.0748 | +0.6504 | +0.6450 |
| 846 | +0.0453 | +0.7959 | -0.5721 | +0.7507 | +1.3680 |
| 847 | -0.0000 | +0.6687 | -0.0035 | +0.6687 | +0.6721 |
| 848 | +0.0441 | +0.7041 | -0.1321 | +0.6600 | +0.8361 |
| 849 | -0.0401 | +0.9212 | +0.3238 | +0.9614 | +0.5974 |

## What this earns

The old single-port energy-minimization benchmark was confounded because randomly weakening transmission could improve the objective. This normalized order-contrast benchmark removes that easy escape: AB and BA contain the same two source events and the same total input energy; only their order differs.

On the ideal reciprocal tile, the physically placed local credit therefore carries task-specific structural information that a norm-matched edge permutation does not preserve.

This result reopens mixed-signal hardware-envelope work. It does **not** by itself establish any bit-depth, leakage, drift, mirror-error, or detector-noise tolerance.
