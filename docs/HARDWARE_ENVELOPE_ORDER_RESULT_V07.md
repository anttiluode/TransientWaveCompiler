# TW-1A hardware envelope — 50% simultaneous-corner result v0.7

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V07.md`

Workflow: `hardware-envelope-order-v07`

Fresh confirmatory seeds: 970–979.

## Frozen corner

Q/DAC/ADC = 8/8/8 with:

- leakage rate: `0.0005/tick`;
- leakage CV: `0.50`;
- mirror error: `0.15`;
- differential +/- pass drift: `0.00025`;
- zero-mean credit noise: `0.25`;
- credit DC offset: `0.00015`;
- state noise: `5e-9 FS` = `1e-7` state-unit RMS at +/-20 full scale.

## Result

**FAIL.**

- all values finite;
- median exact contrast improvement: **+0.45411**;
- median placed-vs-shuffled improvement gap: **+0.41345**;
- exact final contrast beat shuffled final in **8/10**;
- only **6/10** reached `DeltaC >= 0.10`;
- not every exact learner improved.

Per-seed exact improvements:

| seed | DeltaC exact | placement gap |
|---:|---:|---:|
| 970 | +0.05726 | +0.07550 |
| 971 | +1.00203 | +1.06937 |
| 972 | +0.57404 | +0.40205 |
| 973 | +1.08998 | +1.36163 |
| 974 | **-0.07163** | **-0.07868** |
| 975 | +0.02061 | +0.03885 |
| 976 | +0.03351 | -0.00088 |
| 977 | +0.61872 | +0.76275 |
| 978 | +1.04449 | +0.96036 |
| 979 | +0.33419 | +0.42485 |

Therefore no simultaneous mixed-signal corner is claimed from v0.7.

## Interpretation

The repeated failure of uniformly scaled combined corners, despite strong medians and independently passing one-axis tolerances, indicates a genuine interaction/tail-robustness problem rather than a simple scalar margin problem.

The next development step is therefore not another blind global backoff. Use only the now-spent v0.7 seeds to remove one damage component at a time from the frozen 50% corner and identify which interaction is load-bearing. Any revised corner must then be preregistered on new seeds.
