# TW-1A hardware requirements envelope — rank-one edge-cell preregistration v0.5

Date frozen: 2026-08-09

## Why v0.5 supersedes the emulator model used for v0.1–v0.4

The compiler has always declared trainable physical edges with a rank-one parameterization:

`Q += a_e (e_i-e_j)(e_i-e_j)^T`.

Emulator versions through v0.4 instead quantized the completed Q matrix entry-by-entry, snapping diagonal and off-diagonal pieces of one edge on different coefficient ranges. This destroyed the declared one-edge/one-parameter hardware abstraction while the physical credit readout still assumed it.

v0.5 quantizes each reciprocal physical edge-cell coefficient once and reconstructs its exact rank-one Q contribution. Residual onsite coefficients are quantized separately. Structural CI tests require one edge-code change to produce exactly one rank-one matrix change.

Development-only replay on already-spent v0.4 seeds showed the semantic correction was decisive and restored monotone precision behavior. Those results are not confirmatory evidence for this preregistration.

## Fixed benchmark and optimizer

Use temporal-order contrast benchmark v0.1 unchanged:

- 40 active cells on the 8x8 TW-1A tile;
- 96 ticks, dt=0.08, gamma=0.40;
- same two leaf events, AB vs BA ordering;
- root/soma quadratic output-energy contrast `C=(E_AB-E_BA)/(E_AB+E_BA)`;
- two ordinary four-pass physical energy-gradient measurements per contrast update;
- 40 updates;
- host step size 0.20;
- RMS-normalized combined physical contrast credit;
- fixed norm-matched shuffled-credit edge permutation.

Hardware constants:

- zero-preserving signed mid-tread edge/DAC/ADC quantizers;
- one quantized coefficient per reciprocal edge cell;
- internal state full scale +/-20, clipping enabled;
- sense ADC full scale +/-2;
- compiler-predicted static binary PGA, fixed for the task/run;
- uniform weight quantizer for this envelope.

## Qualification predicate

For a 6-seed discovery/confirmation block, a point qualifies only if:

1. every exact learner has `DeltaC_exact > 0`;
2. at least 5/6 have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast beats shuffled final contrast in at least 5/6;
5. median `(DeltaC_exact-DeltaC_shuffle) >= 0.10`;
6. all values remain finite.

For the final 10-seed combined confirmation, replace 5/6 by 8/10 and keep the median thresholds.

## Stage A — precision floors on untouched seeds

Fresh seeds: `910,911,912,913,914,915`.

Bit grid for each isolated path:

`[4,5,6,7,8,9,10,12]`.

All physical damage axes are zero.

### A1 edge-cell / Q precision

Sweep `weight_bits`; DAC and ADC ideal.

### A2 drive + returned-error DAC precision

Sweep `dac_bits`; edge cells and ADC ideal.

### A3 sense ADC precision

Sweep `adc_bits`; edge cells and DAC ideal; static PGA enabled.

### Stable minimum

For each precision path, the measured minimum is the smallest tested bit depth for which that value **and every higher tested depth** qualifies. If no such stable suffix exists, stop.

The empirical one-step-margin bit depth is the next tested value above the stable minimum when available.

These minima are benchmark-specific. They do not override the separate architecture-wide dynamic-range budget associated with the compiler's maximum boundary-gain promise.

## Stage A4 — clean 8/8/8 joint confirmation

Fresh seeds: `916,917,918,919,920,921`.

Run simultaneously:

- edge-cell Q: 8 bits;
- drive/error DAC: 8 bits;
- sense ADC: 8 bits;
- static PGA;
- all damage axes zero.

This point must qualify before Stage B is allowed to run.

### Predeclared requested nominal control

On the same 916–921 block also report, independently:

- Q/DAC/ADC = 8/8/8;
- mirror error = 0.05;
- differential +/- pass drift = 0.002;
- local credit noise fraction = 0.05;
- all other damage axes zero.

Its result is descriptive and does not alter the clean-8/8/8 progression rule.

## Stage B — physical imperfection sweeps to first failure

Only if clean 8/8/8 qualifies.

Fresh seeds: `922,923,924,925,926,927`.

Use Q/DAC/ADC = 8/8/8 throughout. Sweep one damage axis at a time with all other damage axes zero.

Frozen grids:

- leakage rate per tick: `[0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]`
- mirror error: `[0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00]`
- differential +/- pass drift: `[0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]`
- analog state-noise RMS fraction of +/-20 full scale: `[0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2]`
- local credit readout noise fraction: `[0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00]`
- local credit DC-offset fraction: `[0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50]`

### Leakage CV

After the leakage-rate sweep, choose its recommended nonzero leakage rate by the safety-margin rule below. At that fixed rate sweep:

`leakage_cv = [0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 1.50]`.

If recommended leakage is zero, leakage-CV tolerance is unresolved.

### Boundary and safety margin

For each monotone damage grid:

- pass prefix = consecutive qualifying values starting at zero and ending before the first failure;
- measured boundary = largest value in the pass prefix;
- recommended specification = one tested step inside that boundary when possible;
- if all points pass, recommended = second-highest tested value;
- if only zero passes, recommended = zero.

Later passing islands after the first failure do not extend the boundary.

## Stage C — combined conservative-corner confirmation

Fresh seeds: `930,931,932,933,934,935,936,937,938,939`.

Run all simultaneously:

- Q/DAC/ADC = 8/8/8;
- recommended leakage rate;
- recommended leakage CV if resolved;
- recommended mirror error;
- recommended differential pass drift;
- recommended analog state noise;
- recommended credit noise;
- recommended credit offset;
- static PGA.

The 10-seed final predicate must pass.

If Stage C passes, v0.5 earns the first combined mixed-signal operating envelope for an 8-bit TW-1A tile on this benchmark.

If Stage C fails, independent boundaries remain measured but no combined buildability claim is allowed.

## Allowed precision wording

If Stage A confirms a stable suffix, benchmark-specific precision may be stated as `edge bits >= X`, `DAC bits >= Y`, `ADC bits >= Z` **within the tested grid and this exact zero-preserving quantizer/PGA contract**.

The architecture-wide DAC/detector dynamic-range requirement from the compiler's maximum `G=8` boundary-gain promise must still be reported separately; a task-specific lower bit floor does not weaken that broader contract.
