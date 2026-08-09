# TW-1A v0.9 fixed inertial baseline — result

Date: 2026-08-09

Status: **static split PASS; ordinary noisy fixed-gain implementation REJECTED. No fresh seed authorized.**

Preregistration: `docs/CIRCUIT_V09_INERTIAL_BASELINE_PREREG.md`

The v0.8 thermal path split showed that node-local self sampling is the first kT/C wall. The kick audit then showed that the active-node self coefficient is almost entirely the universal inertial baseline near +2. v0.9 split

```text
d_i = g_inertial_i + k_residual_i
```

with a fixed measured near-2 path and a small sampled programmable residual.

## Frozen static model

```text
nominal fixed inertial gain               2.0
raw fixed-gain mismatch                   1% RMS
foreground gain-measurement error         0.1% RMS
residual self range                       +/-0.125
residual signed resolution                10 bits
edge thermal base                         2e-5
residual-self thermal base                2e-5
all other v0.8 nonidealities              unchanged
```

The fixed gain was not assumed exact: each body received a static mismatch draw, the gain was measured with 0.1% RMS error, and the residual self target was programmed against the measured value.

All ten spent bodies passed residual-range and edge-fabrication audits. The maximum residual target across the complete 64-node tile was about 0.114, still inside +/-0.125.

## Inertial dynamic-noise sweep

Independent additive fixed-path noise was injected per node, per wave tick and per context as a fraction of state full scale.

| inertial noise RMS | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 10/10 | 10/10 | +0.499283 | +0.332556 | +0.549227 | YES |
| 1e-5 | 8/10 | 10/10 | +0.316495 | +0.018932 | +0.338922 | NO |
| 1.5e-5 | 8/10 | 10/10 | +0.230075 | +0.036565 | +0.216965 | NO |
| 2e-5 | 6/10 | 8/10 | +0.162067 | -0.048796 | +0.140428 | NO |
| 2.5e-5 | 6/10 | 8/10 | +0.121722 | -0.046217 | +0.109467 | NO |
| 3e-5 | 4/10 | 8/10 | +0.085004 | -0.036475 | +0.090459 | NO |

Only the zero-added-noise point satisfies the frozen predicate.

## Interpretation

The result separates two statements that should not be conflated:

1. **The algebra/static calibration is useful.** Removing the near-2 term from the wide programmable sampled self path works extremely well. With zero extra fixed-path dynamic noise, the spent bodies are stronger than the v0.8 reference despite using `b_edge=b_residual=2e-5`.
2. **An ordinary independently noisy gain-2 analog path is not good enough.** A fresh `1e-5 FS/tick` full-node noise source already produces a hard learning tail.

Therefore v0.9 does **not** justify replacing the old self bank with a generic analog x2 amplifier and claiming the capacitor saving. The universal inertial term must be implemented as a substantially more structural/coherent state operation, or the area must instead be traded for repeated physical gradient averaging.

## What survives from v0.9

The exact kick-drift identity and self audit remain valid:

```text
K = Q - 2 I
p[n] = z[n] - z[n-1]

p[n+1] = p[n] + K z[n] + u[n]
z[n+1] = z[n] + p[n+1]
```

On the benchmark active nodes:

```text
old |self| max       1.993759520
kick |self| max      0.006240480
reduction            319.488x
```

The next circuit interpretation should test whether the existing two temporal state banks can be reinterpreted as `(z,p)` and implement the two unity shears through state-bank topology, rather than recreating `2*CUR` through an independently noisy multiplier.

Separately, because the failed `b=2e-5` v0.8 thermal point preserved 10/10 exact-over-shuffled ordering, complete-gradient averaging is a legitimate area/time trade to test without changing the analog topology.
