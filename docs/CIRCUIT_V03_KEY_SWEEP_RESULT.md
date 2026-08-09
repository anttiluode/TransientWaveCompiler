# TW-1A v0.3 key-primitive sweep result

Frozen experiment: `CIRCUIT_V03_KEY_SWEEP_PREREG.md`.
Fresh bodies: 1250-1254. Artifact: `circuit-v03-key-sweep`, workflow run 31302761948.

TW-1A v0.3 replaces the two dominant v0.2 simultaneous-corner failure mechanisms with (a) foreground-calibrated self programming and (b) charge-balanced edge sampling.

## Results

| v0.3 quantity | largest qualified | first failed | inward design value |
|---|---:|---:|---:|
| raw self-MDAC gain CV, perfect calibration | **20%** | **30%** | **10%** |
| self gain-calibration residual RMS | **0.3%** | **1%** | **0.1%** |
| common edge charge injection / state FS | **1e-4** | **3e-4** | **3e-5** |
| residual differential edge injection / state FS | **3e-5** | **1e-4** | **1e-5** |

All boundaries were monotone under the frozen predicate.

## 1. Foreground self calibration works

With perfect gain measurement, raw self-MDAC gain CV gave:

```text
0%    5/5  median DeltaC +0.648
3%    5/5                  +0.640
10%   5/5                  +0.631
20%   5/5                  +0.592
30%   FAIL, 3/5
50%   FAIL, 1/5
```

This is a substantial change from v0.2, where an uncalibrated 3% self-gain CV killed the one-axis learner.

The failure at very large raw CV is consistent with **programming headroom**, not an intrinsic inability to calibrate gain. The desired self coefficient is divided by the measured physical gain before 12-bit quantization. At sufficiently low raw gain the required command can exceed the fixed +/-3 self-DAC command range and saturate.

Therefore v0.3 does not specify fantastically matched self multipliers. It specifies:

- enough raw yield/headroom to keep calibrated commands in range;
- foreground measurement of each self path;
- a code-to-effective-coefficient calibration table;
- approximately 0.1% RMS residual calibration target for the first implementation.

### Calibration residual sweep

With raw self gain CV fixed at 10%:

```text
0       5/5  median DeltaC +0.631
0.01%   5/5                  +0.633
0.03%   5/5                  +0.695
0.10%   5/5                  +0.766
0.30%   5/5                  +0.805
1.00%   FAIL, 1/5
3.00%   FAIL, 0/5
```

The apparent improvement at some nonzero errors is not interpreted as beneficial noise; these are five fixed bodies and nonlinear update trajectories. The robust conclusion is only the pass/fail envelope.

## 2. Charge balancing changes the specification

### Common component

With perfect self calibration and 10% raw self gain CV, common edge injection shared by forward/A/B qualified through `1e-4` of state full scale RMS per active edge/tick and failed at `3e-4`.

The inward target is `3e-5` state FS.

This common component is not invisible: it is an additive physical source and can eventually perturb the trajectory enough to hurt the task. But because it is replayed coherently, it is not the severe differential-credit corruption of v0.2.

### Differential residual

With common injection fixed at `1e-4`, the A/B residual differential component qualified through `3e-5` and failed at `1e-4`.

The inward target is `1e-5` state FS.

At the proposed `1e-5` differential level all 5/5 bodies qualified with median `DeltaC ~ +0.433` and minimum improvement about `+0.263`.

## 3. New implementation contract

For the first SPICE/board design, v0.3 therefore targets:

```text
raw self-MDAC gain CV                <= ~10% design population target
self calibration residual RMS        <= 0.1%
common edge switch injection RMS     <= 3e-5 state FS / active edge / tick
A/B differential injection RMS       <= 1e-5 state FS / active edge / tick
```

The raw self number is not a fundamental analog-accuracy requirement. It is mainly a fixed-command-range/headroom requirement for the present +/-3 self MDAC.

## 4. Circuit implications

### Self calibration sequence

A practical foreground sequence can isolate each node self path with edge cells disabled, apply known state samples, sense one-step response and construct a monotone local mapping

```text
desired d_i -> digital self code -> measured effective d_i.
```

The compiler/runtime then programs through that table. Calibration need not run inside `PARAM_HOLD`; it is a setup/refresh operation between gradient evaluations.

### Charge-balanced sampler

The edge cell should use differential bottom-plate sampling plus complementary/dummy switches and a defined reset/autozero phase. Layout must make the A and B lane-select parasitics as symmetric as practical so most switch charge appears in `q_common`, leaving only the smaller `q_diff` residual.

## 5. Remaining gate

These are isolated v0.3 primitive sweeps. They do **not** qualify a simultaneous hardware corner.

The next experiment combines the inward v0.3 values with the surviving v0.2 circuit errors and the older leakage/noise/readout background on untouched bodies.