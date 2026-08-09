# TW-1A v0.9 fixed-theta thermal gradient SNR microscope — preregistration

Date: 2026-08-09

Status: **spent-body diagnostic only; frozen before outcomes.**

## Why this exists

The partitioned thermal experiments established three facts on task/fabrication 2400:

1. with sampled thermal sources off, the fabricated machine has a strong learning gradient;
2. uniform capacitor enlargement does not economically recover the learner;
3. averaging 4 and 16 complete noisy physical gradients per optimizer update does not reliably recover training at `b=2e-5`.

That leaves an important distinction unresolved:

- **variance-limited**: each physical gradient is an unbiased but extremely noisy estimate of the clean physical gradient, so its running mean should converge toward the clean direction as `N` grows;
- **biased estimator**: thermal perturbations of forward/reverse trajectories plus nonlinear energy/contrast construction make the mean physical gradient itself differ from the clean physical gradient, so averaging eventually plateaus on the wrong vector.

This experiment freezes theta and measures the estimator directly, without optimizer dynamics.

## Frozen task / fabrication

```text
task seed          2400
fabrication seed   2400
sense PGA          compiler-recommended static value
edge switches      residual set to zero after construction
drift switches     residual set to zero after construction
```

Use the exact formal v0.9 static fabricated silicon. No theta updates occur.

## Clean reference gradient

On the same fabricated target/distractor pair and same initial theta, construct one deterministic physical reference by temporarily setting only dynamic zero-mean sources to zero:

```text
edge b               0
kick-self b          0
drift b              0
credit noise fraction 0
```

Keep converter quantization, codebooks, site mismatch, leakage, static credit offset, self calibration residual, LCC curvature and all other static physical effects unchanged.

Evaluate target and distractor once and form the same normalized contrast gradient used by training:

```text
g_ref = dC/dtheta
```

This is a **clean fabricated-machine reference**, not an ideal mathematical gradient.

## Noisy estimator

Restore:

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
formal credit readout noise
```

For each dynamic seed

```text
8000, 8001, 8002, 8003, 8004
```

reseed target/distractor streams with the same role-offset convention as the partitioned learner, then acquire 1024 complete target+distractor physical gradients at fixed theta.

Record running-mean metrics at:

```text
N = 1, 4, 16, 64, 256, 1024
```

## Frozen metrics

For `g_bar_N` report:

```text
cosine              = dot(g_bar_N, g_ref) / (||g_bar_N|| ||g_ref||)
projection_gain     = dot(g_bar_N, g_ref) / ||g_ref||^2
relative_error      = ||g_bar_N - g_ref|| / ||g_ref||
trace_standard_error = sqrt((E||g||^2 - ||E g||^2)/N) / ||g_ref||
```

Also record `||g_ref||`, `||g_bar_N||`, and the mean single-acquisition gradient norm.

## Frozen interpretation

At `N=1024`:

- If median cosine across the five dynamic seeds is `>=0.90` **and** median relative error is comparable to the reported trace standard error, call the estimator **variance-limited** at this scale.
- If cosine improves with `N` but relative error remains materially above the standard-error estimate, call it **mixed bias + variance**.
- If cosine/projection visibly plateau away from the clean reference while statistical standard error shrinks, call it **biased by trajectory/contrast construction**.

This is not a qualification criterion and does not authorize larger averaging factors. Its purpose is to determine what kind of estimator/circuit change should be attempted next.

## Physical interpretation guardrail

Do not infer from this emulator-only microscope that arbitrary forward/reverse thermal correlation is physically available. If bias is found, any proposed correlated/coherent remedy must identify what charge/state is actually retained or jointly sampled in the circuit. A shared RNG is not a hardware mechanism.
