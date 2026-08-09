# TW-1A v0.9 fixed-theta thermal gradient SNR microscope — result

Date: 2026-08-09

Status: **mixed bias + extreme variance at `b=2e-5`; ordinary Monte Carlo gradient recovery is not economically credible.**

Preregistration: `docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_PREREG.md`

Workflow: `v09-fixed-theta-gradient-snr`, successful run `31329151806`.

## Frozen reference

Task/fabrication 2400, initial theta, compiler-selected PGA `32`, edge/drift switch residuals zero. The clean fabricated-machine gradient keeps static converter/codebook/leakage/calibration/offset effects but sets the three zero-mean sampled thermal sources and zero-mean credit noise to zero.

Every job reproduced

```text
||g_ref|| = 2.358577541e-02
```

The noisy point restores

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
formal credit readout noise
```

and never updates theta.

## N=1024 result

| dynamic seed | cosine to clean | projection gain | relative error | trace SE / clean norm |
|---:|---:|---:|---:|---:|
| 8000 | +0.416511 | +0.191466 | 0.910156 | 0.517226 |
| 8001 | +0.095491 | +0.052385 | 1.093700 | 0.537806 |
| 8002 | +0.280275 | +0.196194 | 1.047672 | 0.521362 |
| 8003 | +0.694966 | +0.546851 | 0.724893 | 0.537669 |
| 8004 | +0.055476 | +0.044713 | 1.249075 | 0.521409 |
| **median** | **+0.280275** | **+0.191466** | **1.047672** | **0.521409** |

The preregistered variance-limited condition required median cosine `>=0.90` with relative error comparable to the trace standard error. It is not met.

The running means do improve from the wild single-acquisition vectors, but at `N=1024` the typical mean is still mostly not the clean gradient. Median projection is only about 19% of the clean reference and the median vector error is slightly larger than the reference norm itself.

## Classification

Per the frozen interpretation this is:

```text
MIXED BIAS + VARIANCE
```

rather than a clean variance-limited estimator.

The finite-sample term is still large enough that this experiment does not claim an asymptotic bias vector with high precision. However, the observed relative error (~1.05) is about twice the estimated trace standard error (~0.52), and the projection/cosine remain poor after 1024 acquisitions. The data therefore give positive evidence for a non-negligible bias component in addition to enormous variance.

A simple quadrature residual using the median values,

```text
sqrt(relative_error^2 - trace_SE^2) ~= 0.91
```

is only a diagnostic scale, not a confidence interval, but it shows why ordinary averaging is not closing quickly.

## What the variance scale means

At `N=1024`, median relative trace standard error is `0.521409`. Multiplying by `sqrt(1024)=32` implies a single-acquisition stochastic gradient trace scale of roughly

```text
16.69 * ||g_ref||.
```

If that variance alone followed ideal independent `1/sqrt(N)` scaling, reaching trace standard error

```text
0.20 * ||g_ref||  -> about 6,960 complete gradients
0.10 * ||g_ref||  -> about 27,839 complete gradients
```

would be required at this theta. Those counts ignore the apparent bias and ignore the fact that the optimizer moves theta after every update.

Therefore even the optimistic variance-only extrapolation is already incompatible with an efficient on-device gradient-training story at the small-cap `b=2e-5` point.

## Why bias is physically plausible here

The physical credit primitive is not differentiating a noiseless stored tape. The forward wave experiences new sampled thermal packets, while reverse C/D propagation experiences additional independent sampled thermal packets. The local LCC product and normalized contrast coefficients are then formed from these perturbed trajectories.

For a deterministic reversible second-order body, physical echo reconstructs the state needed by the adjoint. With independent process noise, the reverse body cannot reproduce the exact stochastic forward trajectory unless information about the forward noise realization is retained or otherwise made coherent. Repeating the whole gradient therefore attacks variance but does not automatically repair trajectory-replay mismatch or nonlinear contrast bias.

This is a model-level interpretation supported by the measurements, not yet a transistor-level proof. The next circuit work must distinguish physically available coherence from emulator-only correlation.

## Consequence

Together with the uniform-capacitor backoff result, this removes two easy rescue stories:

```text
make C much larger        -> economically killed
average ordinary gradients -> SNR scale already prohibitive; bias remains
```

The remaining chip question is now structural:

> Can the physical gradient protocol be changed so the reverse credit measurement is coherent with the forward stochastic trajectory, without storing a T-long analog/digital tape that destroys the architecture's reason to exist?

Any proposed solution must identify the retained physical state/charge or an estimator identity that does not require same-noise replay. Merely assigning the same RNG samples to forward and reverse in the emulator is not an implementation.
