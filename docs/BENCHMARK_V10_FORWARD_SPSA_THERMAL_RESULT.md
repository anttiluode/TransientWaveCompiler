# TW-1A forward-only SPSA at small-cap thermal point — result

Date: 2026-08-09

Status: **FAIL under the frozen thermal-forward viability rule. Forward-only training remains interesting, but one-direction SPSA is not robust enough at `b=2e-5`.**

Preregistration: `docs/BENCHMARK_V10_FORWARD_SPSA_THERMAL_PREREG.md`

Workflow: `v10-forward-spsa-thermal`, successful run `31329740573`.

## Frozen point

```text
task seed          2400
fabrication seed   2400
edge/self/drift b  2e-5
edge/drift switch residuals zero after construction
c                  1.0
step size          0.40
updates            30
dynamic seeds      8000..8004
SPSA directions    9100..9102
```

Every update used two independently noisy parameter points, each requiring target+distractor forward objectives:

```text
4 noisy forward traversals / update
120 noisy forward traversals / run
0 reverse traversals
```

No common-random-number pairing or reverse credit path was used.

## Fifteen-run aggregate

```text
DeltaC >= +0.10      3/15
exact > shuffled    11/15
median DeltaC       +0.045210
minimum DeltaC      -0.094383
maximum DeltaC      +0.354985
median placement gap +0.057349
minimum placement gap -0.098689
```

The preregistered thermal-forward-viable rule required at least 12/15 improvements above +0.10, at least 12/15 exact wins, median DeltaC >= +0.20, median placement gap >= +0.15, and at least 2/3 successes for every dynamic seed. None of those aggregate margin clauses is met.

## Dynamic-seed summaries

| dynamic seed | >= +0.10 | exact > shuffled | median DeltaC | median placement gap |
|---:|---:|---:|---:|---:|
| 8000 | 1/3 | 2/3 | +0.004995 | +0.057349 |
| 8001 | 2/3 | 3/3 | +0.131803 | +0.176984 |
| 8002 | 0/3 | 3/3 | +0.045210 | +0.150404 |
| 8003 | 0/3 | 2/3 | +0.011872 | +0.035765 |
| 8004 | 0/3 | 1/3 | +0.007409 | -0.010504 |

Dynamic seed 8001 shows that the forward-only estimator can work at the exact small-cap body for some stochastic trajectories, but the other four dynamic seeds prevent any robustness claim.

## Direction-seed summaries

| direction seed | >= +0.10 | exact > shuffled | median DeltaC | median placement gap |
|---:|---:|---:|---:|---:|
| 9100 | 1/5 | 4/5 | +0.081391 | +0.184375 |
| 9101 | 1/5 | 4/5 | +0.045609 | +0.150404 |
| 9102 | 1/5 | 3/5 | +0.007409 | +0.037963 |

No single Rademacher direction sequence rescues the dynamic axis.

## Interpretation

The clean SPSA result was not an artifact: the same estimator on the same fabricated body without sampled thermal noise reached 3/3 robust learning at the frozen selected point, with median DeltaC `+0.446339`. Restoring independent sampled thermal packets collapses that margin.

Forward-only SPSA nevertheless fails differently from the physical adjoint:

- it does not require stochastic reverse trajectory replay;
- 11/15 runs still beat shuffled placement;
- one run reaches `+0.354985` and one dynamic cohort reaches 2/3 above +0.10;
- but the scalar two-point contrast difference is itself too noisy to give a reliable rank-1 gradient estimate from one perturbation direction per update.

The median absolute measured `C_plus-C_minus` during training is typically around `0.18..0.35`, showing that the stochastic scalar difference is large enough to swamp direction-specific finite-difference information even though the deterministic perturbation signal is useful.

## Frozen decision

The preregistration says that on failure the SPSA hyperparameters may **not** be tuned post hoc against this noise realization. The next authorized estimator is a structured orthogonal/Hadamard finite-difference measurement on the same spent task/fabrication.

That estimator attacks a different failure mode: instead of treating one noisy directional derivative as a full 39-dimensional gradient, measure a complete orthogonal direction set and reconstruct each coordinate from the ensemble. It costs more forward traversals but still requires no reverse trajectory and no local credit hardware.

The original v0.9 physical-adjoint fresh gate remains red. This experiment neither rescues nor worsens it; it is evidence for a distinct forward-only training architecture.
