# TW-1A hardware envelope — near-zero refinement and combined backoff preregistration v0.6

Date frozen: 2026-08-09

v0.5 established a faithful rank-one edge-cell hardware abstraction, monotone benchmark-specific precision floors, and independent physical-damage boundaries. Its one-step-inside combined corner failed narrowly on 10 fresh seeds, so independent recommended maxima may not simply be combined.

v0.6 makes **no emulator semantic changes**. It refines the two unresolved near-zero axes and measures a scalar backoff of the already-frozen v0.5 combined corner.

## Fixed hardware/task contract

Unchanged from v0.5:

- rank-one reciprocal edge-cell quantization;
- Q/DAC/ADC = 8/8/8 for all v0.6 runs;
- zero-preserving signed mid-tread quantizers;
- static compiler-predicted sense PGA;
- state full scale +/-20 with clipping;
- temporal-order AB/BA contrast benchmark;
- 40 updates, step size 0.20, RMS-normalized physical contrast credit;
- norm-matched shuffled-credit control.

## Qualification predicate

Six-seed point:

1. every exact `DeltaC > 0`;
2. at least 5/6 have `DeltaC >= 0.10`;
3. median `DeltaC >= 0.15`;
4. exact final contrast beats shuffled final in at least 5/6;
5. median placed-vs-shuffled improvement gap >= 0.10;
6. all values finite.

Final ten-seed point: replace 5/6 by 8/10; retain the same median thresholds.

## Stage A — resolve near-zero axes

Fresh seeds: `940,941,942,943,944,945`.

All damage axes other than the swept axis are zero.

### A1 analog state-noise floor

`state_noise_std` is RMS Gaussian noise as a fraction of the +/-20 internal state full scale, injected independently at each node/tick by the frozen emulator.

Sweep:

`[0, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5]`.

Use the same pass-prefix rule as v0.5. The measured boundary is the largest consecutive passing value from zero. Recommended state-noise specification is one tested step inward when possible; if all points pass, use the second-highest point; if only zero passes, recommended remains zero.

### A2 local credit-offset floor

Sweep systematic local credit offset fraction:

`[0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 2e-3, 5e-3]`.

Use the same boundary and one-step-inward rule.

## Stage B — combined-damage backoff discovery

Fresh seeds: `946,947,948,949,950,951`.

The unscaled `s=1` damage vector is the v0.5 preregistered independent recommendation, with the refined Stage-A recommendations inserted for the two previously unresolved axes:

- leakage rate = `0.001/tick`;
- leakage CV = `1.0`;
- mirror error = `0.30`;
- differential +/- drift = `0.0005`;
- credit noise = `0.50`;
- state noise = Stage-A recommended value;
- credit offset = Stage-A recommended value.

Apply one common scalar `s` to **every** damage component above, including leakage CV:

`s = [0, 0.25, 0.50, 0.75, 1.00]`.

The pass prefix is the consecutive qualifying scales starting at zero. The measured combined scale boundary is the largest passing prefix value.

The recommended combined scale for final confirmation is one tested step inward from the discovery boundary when possible. If all five scales pass, recommended `s=0.75`. If only zero passes, recommended `s=0`.

No individual component may be retuned after this discovery.

## Stage C — final combined confirmation

Fresh seeds: `952,953,954,955,956,957,958,959,960,961`.

Run Q/DAC/ADC 8/8/8 at the single recommended Stage-B scale on the v0.5 damage vector plus refined state-noise/offset values.

The 10-seed final predicate must pass.

If it passes, v0.6 earns a **demonstrated simultaneous operating corner**. The claim is the specific component vector at that corner, not the entire Cartesian hyperrectangle beneath each independent bound.

If it fails, no combined corner is earned and a different interaction model or calibration mechanism is required.
