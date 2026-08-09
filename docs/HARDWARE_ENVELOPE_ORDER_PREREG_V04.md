# TW-1A hardware requirements envelope — temporal-order exact-design preregistration v0.4

Date frozen: 2026-08-09

## Why v0.4 exists

v0.3 established useful **independent** precision minima but its preregistered joint design point `(Q,DAC,ADC)=(9,5,6)` failed fresh confirmation. A development-only map on the already-spent joint seeds then showed that finite-step task performance is not monotone in converter bit depth: `(9,5,7)`, `(9,10,6)` and `(9,5,10)` passed on those spent seeds, while several nominally higher-precision combinations did not.

An ideal control on the same spent seeds qualified strongly, proving the joint miss was caused by the quantized operating point / learning trajectory rather than intrinsically unlearnable arbors.

Therefore v0.4 does **not** claim that every precision greater than some bit count is automatically safe. It confirms one exact quantizer design point and then measures physical imperfection tolerances around that point.

## Fixed architecture and task

Carry forward unchanged:

- temporal-order contrast benchmark v0.1;
- 40 active cells, 96 ticks;
- normalized AB-vs-BA root energy contrast;
- zero-preserving signed mid-tread Q/DAC/ADC quantizers;
- internal state full scale +/-20 with clipping enabled;
- ADC full scale +/-2;
- compiler-predicted static binary PGA, frozen per task;
- 40 learning iterations;
- host step size 0.20;
- RMS-normalized combined physical contrast credit;
- norm-matched frozen edge-permutation control.

## Qualification predicate

For a 6-seed block, a point qualifies only if:

1. every exact learner has `DeltaC_exact > 0`;
2. at least 5/6 have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast beats shuffled final contrast in at least 5/6;
5. median `(DeltaC_exact - DeltaC_shuffle) >= 0.10`;
6. all values remain finite.

For the final 10-seed combined confirmation, replace 5/6 by 8/10 and keep the same median thresholds.

## Stage A — exact joint-design confirmation

Fresh seeds: `880,881,882,883,884,885`.

Primary candidate, chosen before these seeds are inspected:

- Q/coupling precision: **9 bits**
- drive + returned-error DAC: **5 bits**
- sense ADC: **7 bits**
- all other physical imperfections: zero
- static PGA enabled

This exact point was the lowest summed-bit passing candidate in the development-only 856–861 map. That development result does not count as confirmation.

If `(9,5,7)` fails the 6-seed qualification predicate, stop. No physical-tolerance sweep is allowed.

### Predeclared nominal baseline control

On the same fresh 880–885 block, independently report the originally requested realistic baseline:

- Q: 8 bits
- DAC: 8 bits
- ADC: 8 bits
- mirror error: 0.05
- differential +/- pass drift: 0.002
- local credit readout noise: 0.05
- leakage: 0
- leakage CV: 0
- state noise: 0
- credit DC offset: 0
- static PGA enabled

This control is descriptive. Its pass/fail result does not alter the primary `(9,5,7)` progression rule.

## Stage B — physical imperfection sweeps to failure

Only if Stage A primary candidate passes.

Fresh seeds: `890,891,892,893,894,895`.

Use the exact `(9,5,7)` precision point. Sweep one damage axis at a time with all other damage axes zero.

Frozen grids:

- leakage rate per tick: `[0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]`
- mirror error: `[0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00]`
- differential +/- pass drift: `[0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]`
- analog state-noise RMS fraction of state full scale: `[0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2]`
- local credit readout noise fraction: `[0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00]`
- local credit DC-offset fraction: `[0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50]`

### Leakage CV

Determine the leakage-rate pass prefix first. Choose its recommended leakage rate by the safety-margin rule below. If that recommended rate is nonzero, sweep:

`leakage_cv = [0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 1.50]`

at the fixed recommended leakage rate.

If the recommended leakage rate is zero, leakage-CV tolerance is unresolved.

### Failure boundary and inward margin

For every monotone damage grid:

- pass prefix = consecutive qualifying values from zero until first failure;
- measured boundary = largest value in pass prefix;
- recommended specification = one grid step below the measured boundary when possible;
- if every tested value passes, recommended specification = second-highest tested value;
- if only zero passes, recommended specification = zero.

Later passing islands do not extend the boundary after the first failure.

## Stage C — combined conservative-corner confirmation

Fresh seeds: `900,901,902,903,904,905,906,907,908,909`.

Run simultaneously:

- exact Q/DAC/ADC point `(9,5,7)`;
- recommended leakage rate;
- recommended leakage CV if resolved;
- recommended mirror error;
- recommended differential pass drift;
- recommended state noise;
- recommended credit readout noise;
- recommended credit offset;
- static PGA.

The final 10-seed predicate must pass.

If Stage C passes, v0.4 earns the first combined TW-1A hardware operating envelope for this benchmark.

If Stage C fails, report the independent boundaries but do not claim a combined buildable envelope.

## Allowed wording if v0.4 passes

Because v0.3 development showed nonmonotone finite-step behavior across bit depths, the precision claim must be phrased as:

> "TW-1A is demonstrated at the exact zero-preserving quantizer point Q9 / DAC5 / ADC7 with the following physical tolerances..."

Do **not** rewrite this as `Q >= 9, DAC >= 5, ADC >= 7` without a separate monotonic/precision-aware compiler study.
