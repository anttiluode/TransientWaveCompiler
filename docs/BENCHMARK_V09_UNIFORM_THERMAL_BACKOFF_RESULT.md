# TW-1A v0.9 partitioned uniform-thermal backoff — result

Date: 2026-08-09

Status: **KILL for capacitor-only rescue of the current independent-sampling model. No nonzero preregistered `b` is robust. No fresh qualification authorized.**

Preregistration: `docs/BENCHMARK_V09_UNIFORM_THERMAL_BACKOFF_PREREG.md`

Workflow: `v09-uniform-thermal-backoff`, successful run `31328715959`.

## Result

The exact formal v0.9 fabrication for task/fabrication 2400 was constructed first, edge and drift switch residuals were then set to zero without redrawing silicon, and the same five partitioned dynamic seeds were replayed at every uniform thermal base.

| uniform `b` | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | maximum DeltaC | median gap | minimum gap | robust |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 5/5 | 5/5 | +0.687113 | +0.660349 | +0.760447 | +0.725182 | +0.647389 | YES |
| 2.5e-6 | 4/5 | 5/5 | +0.129539 | +0.089663 | +0.257925 | +0.152415 | +0.123232 | NO |
| 5.0e-6 | 2/5 | 5/5 | +0.093802 | +0.042817 | +0.181724 | +0.093608 | +0.002919 | NO |
| 7.5e-6 | 1/5 | 4/5 | +0.082214 | +0.000193 | +0.132610 | +0.085674 | -0.042415 | NO |
| 1.0e-5 | 0/5 | 4/5 | +0.039583 | -0.005121 | +0.081962 | +0.083505 | -0.050693 | NO |
| 1.25e-5 | 0/5 | 3/5 | +0.034191 | -0.012374 | +0.071119 | +0.050715 | -0.041564 | NO |
| 1.5e-5 | 0/5 | 3/5 | +0.037357 | -0.007593 | +0.076292 | +0.056759 | -0.053836 | NO |
| 1.75e-5 | 0/5 | 3/5 | -0.001392 | -0.030678 | +0.067372 | +0.013692 | -0.069874 | NO |
| 2.0e-5 | 0/5 | 3/5 | +0.028717 | -0.046686 | +0.066484 | +0.039150 | -0.067130 | NO |

The zero-noise point reproduces the strong control from the source factorial. The response is not perfectly monotone because the learner is quantized/nonlinear and thermal perturbations change code crossings, but the conclusion does not depend on monotonicity: **every nonzero preregistered point fails.**

## Frozen decision

The preregistration states that if no nonzero grid point is robust, the current independent per-use sampled-noise model is to be treated as incompatible with this learner/task length until a coherence/correlation or gradient-estimation mechanism is demonstrated.

That condition is met.

Therefore:

```text
CAPACITOR-ONLY RESCUE: REJECTED
```

for the present model.

## Economic consequence

For common thermal scaling,

```text
C proportional to 1/b^2.
```

Relative to the previously attractive kick-drift `b=2e-5` point, the smallest tested nonzero value `b=2.5e-6` already costs

```text
(2e-5 / 2.5e-6)^2 = 64x
```

more common capacitance. Under the same deliberately illustrative assumptions that put the `b=2e-5` known-cap subtotal near 3.70 mm^2, this would be about

```text
3.70 * 64 ~= 237 mm^2
```

of known capacitors alone, while still failing the frozen robust criterion. Even `b=1e-5` would return the known-cap subtotal to roughly 14.8 mm^2 and still gives 0/5 improvements above +0.10 in this controlled experiment.

So the former **4.27x known-capacitor reduction is not an economically usable operating point under the current independent-sampling stochastic model.** The deterministic kick-drift topology survives; the area claim does not.

## What this says about the model

The discontinuity between `b=0` and very small nonzero `b` is too severe to justify another capacitor sweep. The sampled thermal packets enter every physical traversal and corrupt the in-situ credit estimate. The next question is therefore not “how big must C be?” but:

> Does the physical gradient protocol require independent thermal realizations at every forward/reverse use, or can the estimator be made coherent/paired/averaged so zero-mean sampling noise does not destroy credit?

Three distinct mechanisms must not be conflated:

1. **ordinary capacitor enlargement** — rejected here as an economic rescue;
2. **repeated complete physical gradient measurements** — a legitimate time/energy-for-area trade for independent zero-mean thermal noise and must be tested separately;
3. **coherent/correlated sampling within a gradient** — a circuit/protocol change that may reduce credit variance without requiring a huge C, but must be tied to a physically realizable sampling schedule rather than an emulator-only shared RNG.

## Next authorized diagnostic

Use the same spent task/fabrication and partitioned streams to measure **complete-gradient averaging** at the original `b=2e-5` point with switch residuals zero. Average independent physical contrast-gradient estimates before each optimizer update. This directly measures whether the current failure behaves like zero-mean estimator variance and quantifies the traversal/energy price required to keep the small-cap body.

Do not spend fresh seeds and do not restore an area claim unless a concrete time/energy or coherent-sampling mechanism closes the controlled diagnostic.
