# Published cross-coupled filter with noisy measured response v0.4 — preregistration

Date: 2026-08-09

Status: **synthetic measurement-robustness benchmark; frozen before outcomes.**

## Purpose

v0.3 recovered the seven nonzero entries of a published fourth-order cross-coupled filter exactly when the target complex S parameters were generated without measurement error.

v0.4 asks a more practical question:

> If the exact matrix response is hidden and the tuner receives only repeated noisy complex S-parameter sweeps, does the same exact model gradient still recover the underlying matrix knobs?

This remains a synthetic benchmark. The noise numbers below are explicit stress-test assumptions, **not claims about universal VNA performance**.

## Frozen physical target

Use the exact v0.3 published source–four-resonator–load matrix and topology:

```text
[mS1,m12,m23,m34,m4L,m14,mSL]
=
[1.02,-0.86,0.77,-0.86,1.02,-0.19,0.0005].
```

Use the same composite normalized-frequency grid and generalized explicit-port S-parameter equations as v0.3.

## Frozen measurement model

For one clean complex sample `S`, one synthetic measured sweep reports

```text
S_meas = S * (1 + eps_A) * exp(j eps_phi)
```

with independent draws for every frequency point, S parameter and sweep:

```text
eps_A   ~ Normal(0, 0.005)             # 0.5% RMS multiplicative amplitude
eps_phi ~ Normal(0, deg2rad(0.5))       # 0.5 degree RMS phase
```

Generate **8 independent sweeps** and arithmetic-average their complex values pointwise. The optimizer sees only this averaged noisy target.

No reference-plane delay, finite-Q mismatch, parasitic topology error or systematic calibration bias is included in v0.4; those remain separate future failure modes.

Frozen measurement seeds:

```text
4100, 4101, 4102, 4103, 4104
```

## Frozen detuned starts

Use three already-spent v0.3 starts spanning mild/severe detuning:

```text
A = [0.80,-0.60,0.95,-1.05,1.15,-0.05,+0.020]
C = [0.70,-0.45,0.50,-0.50,0.75,+0.10,+0.030]
D = [1.25,-1.15,1.00,-1.10,1.25,-0.40,-0.025]
```

Cross all three starts with all five measurement seeds for **15 frozen fits**.

## Frozen objective

Optimize the same complex response loss, but against the 8-sweep noisy average:

```text
mean [ |S11-S11_measured_avg|^2 + |S21-S21_measured_avg|^2 ].
```

The gradient differentiates the model response only. Measurement samples are fixed data.

The benchmark records both:

1. **fit-to-measurement loss** — what the optimizer actually sees;
2. **clean hidden-target loss / parameter error** — available only to the benchmark scorer.

This prevents a low noisy-fit loss from silently being called true knob recovery.

## Frozen optimizer

No retuning from v0.3 except stopping earlier because the noiseless runs had already converged well before 1000 iterations:

```text
iterations    = 1200
learning rate = 0.015
beta1         = 0.9
beta2         = 0.999
epsilon       = 1e-8
```

Use the same parameter bounds and no restarts/schedules/second-stage rescue.

## Frozen readouts

For every one of 15 fits record:

```text
measurement seed
start ID
measured-target noise RMS in complex S11/S21
initial noisy fit loss
final noisy fit loss
clean hidden-target complex response loss
final seven matrix knobs
overall parameter RMSE
main-path RMSE
m14 absolute error
mSL absolute error
clean max complex S11/S21 error
```

## Frozen pass criteria

Call v0.4 a **NOISY RESPONSE ROBUSTNESS PASS** only if at least 14/15 runs satisfy:

```text
clean hidden-target complex response loss <= 5e-5
clean max complex S11 error <= 0.03
clean max complex S21 error <= 0.03
```

Call it a **NOISY KNOB RECOVERY PASS** only if the response pass holds and at least 14/15 runs satisfy:

```text
overall parameter RMSE <= 0.015
main-path RMSE <= 0.015
|m14 - target| <= 0.015
|mSL - 0.0005| <= 0.001
```

A stronger **15/15 ROBUST RECOVERY** label requires all 15 fits to satisfy both response and knob clauses.

## Frozen decision

- **15/15 robust recovery:** move next to systematic phase/reference-plane nuisance and finite-Q/model mismatch; exact-equation measurement noise is no longer the main concern.
- **14/15 pass:** keep the application mainline, diagnose the single spent failure and add uncertainty/robust fitting before systematic model mismatch.
- **<14/15:** do not lower noise post hoc. Treat even zero-mean complex measurement noise as a real tuning limitation and diagnose the current objective/optimizer on these spent measurements.

This benchmark concerns computer-side resonator tuning only and is independent of the TW-1A stochastic on-device learner.
