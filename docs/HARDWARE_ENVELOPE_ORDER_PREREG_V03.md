# TW-1A hardware requirements envelope — temporal-order benchmark preregistration v0.3

Date frozen: 2026-08-09

This experiment begins only after the ideal temporal-order benchmark passed 10/10 (`ORDER_CONTRAST_IDEAL_RESULT_V01.md`).

## Hardware semantic correction carried forward

All sparse weight, DAC and ADC paths use signed zero-preserving mid-tread quantization. Disabled edges and zero drive samples must remain exactly zero.

## Sense front-end added before precision tests

The fixed +/-2 ADC range in emulator v0.2 was shown to erase legitimate small root signals on some arbors. v0.3 therefore adds a **static programmable-gain sense front-end (PGA)**.

For each compiled AB/BA task and candidate precision configuration:

1. use the compiled model to predict the two initial root traces with ADC quantization disabled;
2. retain the candidate Q and DAC quantization during this prediction;
3. take the larger absolute peak across AB and BA;
4. choose one gain from the frozen binary ladder `1,2,4,...,16384`;
5. choose the largest gain that keeps the predicted initial peak at or below 25% of ADC full scale;
6. use the same gain for AB and BA;
7. freeze that gain for all 40 learning iterations;
8. after ADC quantization, digitally divide by the nominal gain so objective/error values remain in original physical units.

This is compiler-predicted static range setting, not per-sample or per-iteration AGC.

ADC full scale remains +/-2.0 before the PGA de-gain.

## Learning task and optimizer

Use the frozen temporal-order benchmark v0.1:

- 40 active cells on the 8x8 tile
- 96 ticks
- AB vs BA leaf-event order
- normalized root energy contrast `C=(E_AB-E_BA)/(E_AB+E_BA)`
- 40 iterations
- RMS-normalized combined physical contrast credit
- host step size 0.20
- one fixed norm-matched shuffled-credit permutation per seed

## Qualification predicate

For any 6-seed discovery block, a hardware point qualifies only if all of the following hold:

1. every exact learner has `DeltaC_exact > 0`;
2. at least 5/6 have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast beats shuffled final contrast in at least 5/6;
5. median `(DeltaC_exact-DeltaC_shuffle) >= 0.10`;
6. all values remain finite.

For the final 10-seed combined confirmation, replace 5/6 by 8/10 and retain the same median thresholds.

## Stage A — isolate precision axes

Frozen discovery seeds: `850,851,852,853,854,855`.

Sweep each axis with the other two precision paths ideal and all non-precision imperfections zero.

### A1. Q / coupling precision

`weight_bits = [4,5,6,7,8,9,10,12]`

DAC = ideal, ADC = ideal.

### A2. drive/error DAC precision

`dac_bits = [4,5,6,7,8,9,10,12]`

Q = ideal, ADC = ideal.

### A3. sense ADC precision

`adc_bits = [4,5,6,7,8,9,10,12]`

Q = ideal, DAC = ideal, static PGA enabled.

### Stable minimum rule

For each axis, the minimum acceptable bit depth is the smallest tested value for which that value **and every higher tested precision** qualifies. Isolated low-bit islands do not count.

The proposed design bit depth is one tested step higher than that stable minimum when available; if the stable minimum is 12, design depth remains 12.

If any precision axis has no stable minimum, stop. No tolerance sweep is permitted.

## Stage A4 — joint precision confirmation

Fresh seeds: `856,857,858,859,860,861`.

Run Q, DAC and ADC simultaneously at the three proposed design bit depths with static PGA enabled and all other imperfections zero.

The joint point must satisfy the 6-seed qualification predicate. If it fails, stop.

## Stage B — sweep physical imperfection axes to failure

Fresh seeds: `862,863,864,865,866,867`.

Use the jointly confirmed design Q/DAC/ADC precision and static PGA. Sweep one damage axis at a time, with all other damage axes zero, except leakage CV as specified below.

Frozen grids:

- leakage rate per tick: `[0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]`
- mirror error: `[0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00]`
- differential +/- pass drift: `[0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]`
- analog state-noise RMS fraction of state full scale: `[0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2]`
- local credit readout noise fraction: `[0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00]`
- local credit DC-offset fraction: `[0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50]`

### Leakage CV

First determine the leakage-rate pass prefix. Choose the **recommended leakage rate** by the safety-margin rule below. Then sweep leakage CV at that fixed nonzero recommended rate:

`leakage_cv = [0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 1.50]`.

If the recommended leakage rate is zero, leakage-CV tolerance is reported as unresolved rather than pretending CV of zero leakage is meaningful.

### Failure boundary and safety-margin rule

For every monotone damage grid, define the pass prefix as the consecutive qualifying values starting from zero. The first non-qualifying point ends the prefix even if a later point happens to pass.

- measured boundary = largest value in the pass prefix;
- recommended specification = one grid step below that boundary when possible;
- if all grid points qualify, recommended specification = second-highest tested value;
- if only zero qualifies, recommended specification = zero.

This one-step inward margin is frozen before seeing results.

## Stage C — combined conservative-corner confirmation

Fresh seeds: `870,871,872,873,874,875,876,877,878,879`.

Run all of the following simultaneously:

- proposed design Q/DAC/ADC bits from Stage A;
- recommended leakage rate;
- recommended leakage CV if resolved;
- recommended mirror error;
- recommended differential pass drift;
- recommended state noise;
- recommended credit noise;
- recommended credit offset;
- static PGA.

The 10-seed final qualification predicate must pass.

If Stage C passes, these conservative values become the first earned TW-1A v0 hardware requirements envelope for this benchmark.

If Stage C fails, report the independent boundaries but do **not** claim the combined envelope is buildable. A new preregistration is required for interaction/backoff testing.

## Baseline comparison requested earlier

Regardless of the earned boundary, explicitly report whether the originally proposed nominal point lies inside or outside the measured envelope:

- 8-bit Q
- 8-bit DAC
- 8-bit ADC
- 5% mirror error
- 0.2% differential pass drift
- 5% local credit noise

No threshold may be changed to make that nominal point pass.
