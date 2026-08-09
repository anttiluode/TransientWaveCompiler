# TW-1A v0.9 full-thermal switch-residual boundary — preregistration

Date: 2026-08-09

Status: **diagnostic only on spent bodies 2400..2409. No fresh seeds authorized.**

The zero-thermal seed-2400 interaction sweep showed that scaling the already-post-cancellation edge and drift switch residual fields to 0.10x rescued that one body. A complete spent-cohort replay with the full `b=2e-5` thermal model restored did **not** reproduce the rescue: seed 2400 reached only +0.0690 and seed 2406 +0.0902. Therefore the switch-residual boundary must be measured with all qualified v0.9 thermal sources present.

## Anti-redraw / frozen hardware rule

For every seed and every scale:

1. construct the exact formal v0.9 fresh-corner silicon first;
2. copy static disorder exactly as in the formal learner;
3. freeze the same task-static PGA selected from the unmodified formal configuration;
4. preserve the complete v0.9 thermal model:

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
```

5. scale only the already-drawn inherited edge-switch residual arrays and the already-drawn/formal drift-switch residual amplitudes by the common factor `s`;
6. change no codebook, site-ratio, leakage, converter, lane-hold, self-gain, LCC or credit-path setting.

The same task/fabrication seeds `2400..2409` are already spent. No point in this sweep is a fresh qualification.

## Frozen residual scales

```text
s = 0,
    0.025,
    0.050,
    0.075,
    0.100,
    0.150,
    0.250
```

`0.100` must reproduce the existing full-thermal replay closely enough to serve as an implementation check.

## Fixed ideal-reference classification

The ideal physical-credit control has already been measured on these same tasks and is frozen before this sweep:

```text
ideal-learnable (ideal DeltaC >= +0.10):
2400, 2401, 2402, 2403, 2404, 2406, 2407, 2408, 2409

ideal-tail:
2405  (ideal DeltaC = +0.052904)
```

This diagnostic does **not** retroactively alter the red formal v0.9 gate. It only avoids asking hardware to satisfy an absolute threshold that the ideal reference cannot satisfy on seed 2405.

## Diagnostic closure predicate

A residual scale is called **cohort-closed** only if all clauses hold:

```text
9/9 ideal-learnable bodies improve >= +0.10
10/10 final exact > same-credit shuffled
median improvement over all 10 >= +0.30
median placement gap over all 10 >= +0.25
```

Seed 2405 is still required to beat shuffled; it is not required to exceed its impossible +0.10 absolute gain.

Also report hardware/ideal improvement ratio for every seed and the minimum ratio across the nine ideal-learnable tasks.

## Decision frozen before results

- If `s=0` is not cohort-closed, switch residuals are not sufficient to explain the remaining mixed-signal tail. Stop tightening them and return to a broader interaction diagnosis.
- If one or more nonzero scales are cohort-closed, the **largest** such scale is the diagnostic boundary on this spent cohort.
- Do not design on the boundary. The next tested smaller scale is the provisional inward trim reference.
- Only after that inward reference is replayed/understood should a concrete C1g aggregate residual-measurement/trim circuit be specified. No new fresh seeds are authorized by this sweep.
