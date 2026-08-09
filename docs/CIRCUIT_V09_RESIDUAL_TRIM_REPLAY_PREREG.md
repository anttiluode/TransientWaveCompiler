# TW-1A v0.9 10%-residual-trim spent-cohort replay — preregistration

Date: 2026-08-09

Status: **diagnostic only on spent bodies 2400..2409. No fresh seeds authorized.**

The same-draw seed-2400 switch-interaction sweep found:

```text
formal simultaneous switch residual scale 1.00   DeltaC +0.047842
scale 0.25                                      DeltaC +0.096319
scale 0.10                                      DeltaC +0.304593
scale 0                                         DeltaC +0.706913
```

At scale 0.10 the realized seed-2400 residual RMS values were approximately:

```text
edge A packet residual       0.25 ppm state FS
edge A-B differential        0.21 ppm state FS
drift C residual             0.73 ppm state FS
drift C-D differential       0.54 ppm state FS
```

This diagnostic asks whether a **second-stage aggregate residual trim leaving 10% of the already-post-cancellation switch field** is sufficient when the complete v0.9 thermal model is restored across the entire spent 2400..2409 cohort.

## Anti-redraw / frozen circuit point

For every seed:

1. construct the exact formal v0.9 fresh-corner silicon first;
2. copy static disorder exactly as in the formal learner;
3. freeze the same task-static PGA selected by the formal config;
4. scale the already-drawn inherited edge switch residual arrays by `0.10`;
5. scale the already-drawn 5 ppm common + 5 ppm C/D differential drift residual amplitudes by `0.10`;
6. change nothing else.

In particular, restore/retain the full thermal point:

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
```

and retain all codebook, site-ratio, leakage, converter, LCC and credit-path nonidealities.

## Frozen learning protocol

```text
seeds              2400..2409 (already spent)
updates            30
step size          0.20
RMS-normalized update
same same-credit shuffled control
```

## Readout

Report the historical absolute predicate descriptively, but **do not reinterpret this replay as a formal qualification** because ideal control has already established that seed 2405 cannot reach +0.10 under the same 30-update ideal physical-credit algorithm.

Also report the diagnostic ideal-learnable subset fixed from `docs/BENCHMARK_2400_2409_IDEAL_CONTROL.md`:

```text
ideal >= +0.10: 2400,2401,2402,2403,2404,2406,2407,2408,2409
ideal-tail:      2405
```

For the ideal-learnable subset, count hardware bodies with improvement >= +0.10. For seed 2405, report only sign, exact-over-shuffled placement and hardware/ideal improvement without imposing the impossible +0.10 requirement.

## Interpretation

- If 2400 is rescued and the other ideal-learnable bodies retain >=+0.10, a 10%-accuracy **aggregate post-residual trim** is a plausible next circuit requirement and should be implemented as a node-level calibration primitive before another fresh hardware cohort.
- If 2400 remains weak, do not tighten residual trim further from this single cohort; inspect whether the two residuals need separate compensation coordinates or a shared cancellation measurement.
