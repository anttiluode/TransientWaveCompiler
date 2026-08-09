# TW-1A v0.9 partitioned complete-gradient thermal averaging — preregistration

Date: 2026-08-09

Status: **spent-body time/energy-for-area diagnostic only; frozen before outcomes. No fresh qualification.**

## Motivation

The partitioned uniform-thermal backoff killed capacitor enlargement as an economic rescue: no nonzero preregistered `b` was robust, including `b=2.5e-6`, which would already cost 64x the capacitance of the attractive `b=2e-5` kick-drift point.

The remaining simplest hypothesis is that the independent sampled thermal packets act primarily as a zero-mean **gradient-estimator variance** source. If so, repeated complete physical gradient acquisition may trade training time/energy for capacitor area while leaving inference hardware unchanged.

This experiment measures that trade directly. It does not assume `1/sqrt(N)` scaling and it does not average individual emulator noise arrays. It repeats the **entire target/distractor physical contrast-gradient measurement** and averages the resulting gradient vectors before one optimizer update.

## Frozen task / silicon / dynamic axes

```text
task seed          2400
fabrication seed   2400
dynamic seeds      8000, 8001, 8002, 8003, 8004
ideal DeltaC       +0.864382
```

Construct exact formal v0.9 silicon first, then set inherited edge-switch and drift-switch residuals to zero after construction, preserving the static draw.

Keep the original small-cap thermal point:

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
```

All converter, leakage, codebook, site-ratio, self-gain/calibration, LCC and credit settings remain unchanged.

## Frozen averaging grid

```text
N = 1, 4, 16, 64
```

For each optimizer update:

1. hold theta fixed;
2. perform `N` independent complete target/distractor stochastic physical gradient acquisitions using the naturally advancing partitioned thermal/readout streams;
3. compute one contrast-gradient vector for each acquisition;
4. arithmetic-average the `N` complete gradient vectors;
5. apply one RMS-normalized update from that average;
6. apply the same averaged vector under the frozen shuffled-credit permutation for the control learner.

There are still exactly 30 optimizer updates. `N` changes physical acquisition count, not optimization-step count.

The dynamic streams are reseeded identically at the start of a given dynamic replicate for every `N`, so the `N=4/16/64` cases contain the same initial stochastic sequence used by smaller-N cases and then extend it with additional independent acquisitions.

## Frozen readouts

For every `N` report across five dynamic replicates:

```text
count DeltaC >= +0.10
count final exact > shuffled
median/min/max DeltaC
median/min placement gap
median/min hardware/ideal DeltaC ratio
```

Call `N` **robust on this spent diagnostic** only if:

```text
5/5 DeltaC >= +0.10
5/5 final exact > shuffled
median DeltaC >= +0.30
median placement gap >= +0.25
```

## Cost accounting

Report acquisition multiplier explicitly:

```text
training physical-gradient acquisition cost multiplier = N
```

Do not call averaging free because acquisitions can be performed on the same small-cap hardware. The area may remain unchanged, but traversal time, switching energy, port activity and credit-cell activity all scale approximately with `N` before fixed overhead.

## Frozen decision

- If `N <= 4` is robust, repeated acquisition is a plausible first implementation strategy and should be carried into the energy model.
- If `N=16` is the first robust point, the hardware survives but the architecture becomes primarily an inference/slow-adaptation machine rather than an efficient online trainer.
- If only `N=64` is robust, ordinary repetition is considered a severe training tax; preserve it as a reference but prioritize coherent/correlated gradient acquisition.
- If `N=64` is not robust, **reject ordinary complete-gradient averaging as the primary rescue path** at `b=2e-5`. Do not extend the grid post hoc. The next work must change the within-gradient noise coherence/estimator or the task/compiler dynamics rather than paying still more repetitions.

The historical red v0.9 fresh result remains red throughout this diagnostic.
