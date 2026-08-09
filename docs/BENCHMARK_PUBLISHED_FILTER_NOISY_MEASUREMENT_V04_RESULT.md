# Published cross-coupled filter with noisy measured response v0.4 — result

Date: 2026-08-09

Status: **PASS — 15/15 ROBUST RECOVERY under the frozen synthetic repeated-measurement model.**

Preregistration: `docs/BENCHMARK_PUBLISHED_FILTER_NOISY_MEASUREMENT_V04_PREREG.md`

Workflow: `published-filter-noisy-measurement-v04`, successful run `31330853631`.

## Frozen measurement stress

The hidden physical target is the published seven-knob source–four-resonator–load matrix from v0.3. The optimizer never receives its clean S parameters.

For each frozen measurement seed it receives the pointwise complex average of eight independent synthetic sweeps:

```text
S_meas = S_clean * (1 + eps_A) * exp(j eps_phi)

eps_A   ~ N(0, 0.005)
eps_phi ~ N(0, 0.5 degrees)
```

These are benchmark assumptions, not universal VNA specifications.

Five frozen measurement seeds were crossed with three substantially different detuned starts (`A`, `C`, `D`) for 15 fits total.

## Aggregate result

```text
hidden-clean response clause   15/15
hidden-clean knob clause       15/15
full-run pass                  15/15
```

The stronger preregistered label therefore applies:

```text
15/15 ROBUST RECOVERY
```

### Hidden matrix / response accuracy

Across all 15 fits:

| metric | minimum | median | maximum |
|---|---:|---:|---:|
| overall 7-knob RMSE | 3.928e-5 | 6.060e-5 | 1.305e-4 |
| main-path RMSE | 2.800e-5 | 7.049e-5 | 1.316e-4 |
| `m14` absolute error | 2.918e-5 | 4.197e-5 | 1.802e-4 |
| `mSL` absolute error | 1.697e-6 | 2.945e-6 | 1.407e-5 |
| hidden-clean complex-response MSE | 2.773e-9 | 2.592e-8 | 4.696e-8 |
| max hidden-clean complex `S11` error | 6.787e-5 | 2.907e-4 | 4.066e-4 |
| max hidden-clean complex `S21` error | 1.184e-4 | 2.209e-4 | 5.250e-4 |

The tiny published direct source-load path is

```text
mSL_target = 0.0005.
```

Even the worst measurement realization recovers it within about `1.41e-5`, roughly 2.8% of that already-small coefficient and far inside the preregistered `0.001` tolerance.

### Noise actually presented to the optimizer

After averaging eight sweeps, the frozen measurement targets have approximately:

```text
complex S11 RMS error: 0.00307 .. 0.00317
complex S21 RMS error: 0.00163 .. 0.00167
```

The final optimizer loss against the noisy measurement does not go to zero, as it should not:

```text
final noisy-target fit loss: ~1.21e-5 .. 1.28e-5.
```

Yet scoring the fitted matrix against the hidden clean target gives response MSE only `2.8e-9 .. 4.7e-8`. The optimizer is therefore not simply overfitting each noisy sample point; the constrained seven-knob reciprocal model is acting as a strong physical regularizer.

## Start dependence disappeared

For a given measurement seed, starts `A`, `C`, and `D` converge to numerically the same fitted matrix to the precision recorded by the benchmark. The residual recovery error is controlled by the noisy measurement realization, not by the deliberately different optimization basin starts.

That is stronger than the minimum 14/15 success criterion and is useful for an eventual automated tuner: at this stress level, initial matrix detuning is no longer the dominant uncertainty.

## What v0.4 earns

The compiler application has now passed, in order:

```text
published 3-resonator coupling recovery          5/5 exact
published resonator offsets + couplings          5/5 exact
published 6x6 cross-coupled four-zero topology   5/5 exact
8-sweep noisy complex measurement recovery      15/15 robust
```

This is enough evidence to stop hiding the filter work under `experiments/`. A dedicated `twc-filter` command-line interface is justified.

## What remains untested

v0.4 contains only zero-mean pointwise amplitude/phase measurement noise. Real tuning is harder because the model and measurement can disagree systematically:

```text
unknown reference-plane phase / electrical delay
finite unloaded Q / dissipation
frequency-dependent parasitics
actuator nonlinearities and hysteresis
unmodeled topology paths
measurement outliers / drift
```

Per preregistration, the next benchmark should introduce **systematic reference-plane phase nuisance and finite-Q/model mismatch**, keeping the matrix topology fixed and reporting response fit separately from physical-knob recovery.

The application claim remains computer-side resonator/filter tuning. Nothing in this result rescues the rejected TW-1A small-cap stochastic on-device learner.
