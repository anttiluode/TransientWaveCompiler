# Published coupled-resonator filter tuning benchmark v0.2 — result

Date: 2026-08-09

Status: **PASS — EXACT SIX-KNOB RECOVERY on all 5/5 preregistered detuned starts.**

Preregistration: `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_PREREG.md`

Workflow: `published-coupled-filter-v02`, successful run `31330407101`.

## What changed from v0.1

v0.1 tuned only the three reciprocal couplings of the published three-resonator filter. v0.2 simultaneously tunes six matrix knobs:

```text
[d1, d2, d3, m12, m23, m13]
```

with published target

```text
[0, 0, 0, 0.6, 0.6, 0.2].
```

The first three diagonal matrix entries are normalized resonator self-detuning parameters. The latter three are reciprocal inter-resonator couplings.

The generic matrix-parameter derivative was audited against central finite differences with diagonal and off-diagonal parameters in the same vector before any benchmark result was interpreted. All four filter unit tests passed in every Actions job.

## Results

| start | final `[d1,d2,d3,m12,m23,m13]` | final loss | reduction | overall RMSE | detuning RMSE | coupling RMSE | max `|S11|` err | max `|S21|` err |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | `[-.009493,-.000117,+.009579,.603290,.596778,.200032]` | 2.854e-9 | 5.745e7 | .005818 | .007786 | .002659 | 1.367e-4 | 7.211e-5 |
| B | `[+.012039,-.000185,-.011924,.596032,.604075,.200053]` | 6.893e-9 | 3.542e7 | .007297 | .009783 | .003284 | 1.957e-4 | 1.132e-4 |
| C | `[-.013957,-.000208,+.014003,.604076,.596064,.200070]` | 1.049e-8 | 1.057e7 | .008397 | .011415 | .003271 | 2.660e-4 | 1.413e-4 |
| D | `[-.016167,-.000288,+.016219,.604786,.595403,.200098]` | 1.900e-8 | 7.661e6 | .009734 | .013222 | .003832 | 3.364e-4 | 1.922e-4 |
| E | `[+.015887,-.000285,-.015863,.595511,.604671,.200101]` | 1.750e-8 | 9.193e6 | .009540 | .012963 | .003741 | 3.284e-4 | 1.863e-4 |

All five starts pass the response criteria and the six-knob recovery criteria. The stronger exact label required every overall parameter RMSE to be <= `0.01`; the worst observed value is `0.009734`.

Therefore:

```text
RESPONSE PASS            5/5
SIX-KNOB RECOVERY PASS   5/5
EXACT SIX-KNOB RECOVERY  5/5
```

## What this adds to the application case

The first published benchmark could still be dismissed as “recover three couplings from their own response.” This one asks the optimizer to separate two physically different classes of matrix error from one S-parameter response:

```text
move a resonator frequency/self term
versus
change an inter-resonator coupling
```

The exact inverse-matrix gradient handles both through the same sparse local stamp. Across all five starts the coupling recovery is especially tight (worst coupling RMSE about `0.00383`) while the residual diagonal errors are still within the preregistered exact overall criterion.

This is the first result in the branch that reasonably resembles a matrix-level **filter tuning** task rather than only coupling synthesis.

## Caveat

The benchmark maps directly to normalized coupling-matrix entries. It does not yet contain a measured nonlinear map from a physical cavity screw, varactor voltage, MEMS actuator, or tunable coupling element to those entries. A real tuning product will need that actuator calibration layer and measurement noise/model mismatch.

## Next earned experiment

Per preregistration, exact six-knob recovery authorizes the next external-domain benchmark:

> a larger published cross-coupled resonator filter whose matrix contains a prescribed transmission-zero topology.

That test should preserve the published sparse topology, keep response recovery separate from matrix recovery, and use a generalized source/resonator/load coupling-matrix formulation rather than silently squeezing an `(N+2)x(N+2)` source/load matrix into the three-resonator endpoint-loading convention.
