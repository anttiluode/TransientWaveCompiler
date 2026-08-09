# Hardware-envelope v0.1 execution notes

Date: 2026-08-09

## Pre-result packing correction

The first CI attempt after `HARDWARE_ENVELOPE_PREREG_V01.md` was frozen did **not** reach either the clean gradient audit or the noisy baseline learning test.

Compilation stopped in the strict TW-1A mapper because the 24 unused cells of the 64-cell physical tile had inherited the active arbor's onsite `H=1.0`. As isolated cells this compiled to diagonal `Q≈1.994`, outside the v0 hardware descriptor's `[-1.95, 1.95]` diagonal programming range.

No gradient or learning result was inspectable.

The execution correction is therefore:

```text
active 40 arbor cells: onsite H = 1.0   (unchanged)
inactive 24 physical cells: onsite H = 10.0, no couplings, no ports, no trainability
```

This parks unused hardware cells inside the physical coefficient range while leaving the preregistered active dynamical task unchanged.

The same frozen task seeds 810-814, optimizer, iterations, noise settings, sweep grids and PASS/FAIL thresholds are retained.

If a later correction changes any active-cell dynamics, objective, optimizer or noise semantics, v0.1 must be superseded rather than silently amended.
