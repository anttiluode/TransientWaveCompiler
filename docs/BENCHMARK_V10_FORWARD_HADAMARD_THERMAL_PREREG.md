# TW-1A full-basis forward Hadamard estimator at the small-cap thermal point — preregistration

Date: 2026-08-09

Status: **spent-body estimator test; frozen before outcomes. No fresh qualification.**

## Motivation

The clean forward-only SPSA learner works, but one-direction SPSA fails the partitioned `b=2e-5` thermal body. The failure is consistent with the scalar `C_plus-C_minus` measurement being too noisy for one random rank-one directional estimate to stand in for a 39-parameter gradient.

This experiment replaces that rank-one estimate with a complete structured measurement basis.

The temporal-order task has 40 active tree nodes and therefore 39 trainable tree edges. Embed those 39 coordinates in the first 39 columns of a Sylvester `64 x 64` Walsh-Hadamard matrix `H`, for which

```text
H.T @ H = 64 I.
```

All 64 rows are measured on every optimizer update. In the unclipped linear limit the directional finite differences can therefore be projected back into the 39 parameter coordinates without SPSA cross-talk.

## Frozen task / fabrication / physical point

```text
task seed          2400
fabrication seed   2400
PGA                 compiler-recommended
edge b              2e-5
kick-self b         2e-5
drift b             2e-5
```

Construct exact formal v0.9 silicon first, then set inherited edge-switch and drift-switch residuals to zero after construction. Keep all static codebook, converter, leakage, site-ratio, self-calibration and fabricated mismatch effects.

No reverse lane, error injection, LCC credit detector, or credit accumulator is executed.

## Frozen stochastic axis

```text
dynamic seeds = 8000, 8001, 8002, 8003, 8004
```

For each dynamic seed, target and distractor forward streams are independently reseeded using the existing role-offset convention. Every plus/minus evaluation consumes new forward thermal samples naturally. **No common-random-number pairing is used.**

## Frozen perturbation / reconstruction

Use the clean-SPSA selected values without retuning:

```text
nominal c = 1.0
step_size = 0.40
updates   = 30
```

For each update and each Hadamard row `h_r` restricted to 39 coordinates:

```text
theta_plus  = clip(theta + c h_r, bounds)
theta_minus = clip(theta - c h_r, bounds)
v_r         = (theta_plus - theta_minus) / 2
D_r         = (C(theta_plus) - C(theta_minus)) / 2
```

Stack `v_r` into `V` (`64 x 39`) and `D_r` into `D`. Reconstruct the coordinate gradient by the deterministic least-squares solve

```text
g_hat = argmin_g ||V g - D||_2
```

using NumPy `lstsq` with fixed `rcond=1e-10`.

Using the actual clipped perturbation vectors rather than blindly multiplying by `H.T` keeps the reconstruction defined if optimizer motion reaches a source-space bound. Record matrix rank and condition number each update. No ridge parameter or adaptive regularizer may be added after outcomes.

Apply the same RMS-normalized host update semantics as prior experiments. The shuffled-placement control receives `g_hat` under the frozen parameter permutation and performs no additional physical measurement.

## Structural clean control

Before interpreting thermal outcomes, run the exact same 64-direction estimator on task/fabrication 2400 with the three sampled thermal bases set to zero. This is an implementation sanity control, not a hyperparameter selection stage. It must reach:

```text
DeltaC >= +0.10
exact > shuffled
```

or the thermal result is considered uninterpretable until the estimator implementation is fixed.

## Physical acquisition cost

One Hadamard row requires:

```text
plus  : target + distractor = 2 forward traversals
minus : target + distractor = 2 forward traversals
```

Therefore:

```text
256 noisy forward traversals / optimizer update
7680 noisy forward traversals / 30-update run
0 reverse traversals
```

This cost is part of the result. A pass would establish physical learnability, not necessarily economical on-device adaptation.

## Frozen thermal pass criterion

Across the five thermal dynamic seeds call the estimator **thermal-Hadamard-viable** only if all hold:

```text
5/5 DeltaC >= +0.10
5/5 exact > shuffled
median DeltaC >= +0.30
median placement gap >= +0.20
minimum reconstruction rank = 39
```

Call it a **strong pass** if, in addition:

```text
minimum DeltaC >= +0.20
minimum placement gap >= +0.15
```

## Frozen decision

- **Strong pass:** forward-only training is physically demonstrated at the small-cap point. Next restore formal forward switch residuals and then test fresh factored task x fabrication x dynamic cohorts. Start a reverse-hardware deletion/cost model, but carry the 256-forward/update training tax honestly.
- **Viable but not strong:** retain forward-only as the leading learner, but first test whether a smaller deterministic subset/block of the Hadamard basis can retain the result at lower acquisition cost. No fresh seeds yet.
- **Fail:** do not increase the direction count or average each direction post hoc. Treat brute-force forward finite differences as economically and statistically unpromising at this thermal point. Preserve the forward body as a tunable/inference object and move the compiler/chip program toward off-chip training, calibration/tuning applications, or a genuinely different physical estimator.

The historical v0.9 physical-adjoint fresh gate remains red regardless of this result.
