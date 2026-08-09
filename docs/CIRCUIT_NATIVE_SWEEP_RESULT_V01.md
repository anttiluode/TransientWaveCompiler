# TW-1A circuit-native one-axis sweep result v0.1

This is the result of the frozen experiment in `CIRCUIT_NATIVE_SWEEP_PREREG_V01.md`.

The complete machine-readable run is preserved as the GitHub Actions artifact `circuit-native-sweep-v01` from workflow run 31302004119. The sweep used frozen temporal-order bodies 1110-1114, 25 updates/body/value and the preregistered placed-vs-shuffled qualification predicate.

## 1. Preconditions passed

Before sweeping any circuit error:

- the zero-error lockstep `F+A / F-A` physical credit passed the finite-difference audit;
- the independent fresh 8/12/8/10/8 quantized reference confirmation on seeds 1100-1104 passed 5/5;
- its five contrast improvements were `+.5816, +.8327, +1.0546, +.7426, +.4359`;
- all five placed-credit learners beat their shuffled-credit controls.

So the circuit-native sweeps are testing a working lockstep learner, not a broken baseline.

## 2. Measured one-axis envelope

| circuit error | largest qualified value | first failed value | preregistered inward recommendation |
|---|---:|---:|---:|
| common edge-MDAC gain CV | **>= 30% tested** | not reached | 10% |
| common self-MDAC gain CV | **1%** | **3%** | **0.3%** |
| terminal clone gain RMS | **3%** | **10%** | **1%** |
| lane-B edge settling deficit | **>= 30% tested** | not reached | 10% |
| A -> B edge memory | **10%** | **30%** | **3%** |
| lane-select edge charge injection RMS / state FS | **1e-4** | **3e-4** | **3e-5** |
| `-PREV` ratio RMS error | **1%** | **3%** | **0.3%** |
| error-DAC +/- magnitude asymmetry | **>= 30% tested** | not reached | 10% |
| normalized LCC quartic curvature | **>= 3 tested** | not reached | 1 |
| credit accumulator decay rate / tick | **>= 3% tested** | not reached | 1% |

`>=` means the sweep exhausted the preregistered grid without finding failure. It is a lower bound, not an estimate of the actual boundary.

## 3. The 10-ppm problem did not come back

This was the main architectural question.

The old emulator required extremely small *independent* PLUS/MINUS operator change because two long physical passes were subtracted after the fact. In the lockstep circuit, lane A and lane B reuse one held coefficient element inside adjacent subphases.

The new isolated tests did **not** reproduce a 10-ppm requirement:

- 30% lane-B edge-settling deficit still qualified 5/5;
- 30% error-DAC sign asymmetry still qualified 5/5;
- 30% common edge-MDAC gain CV still qualified 5/5;
- 10% A->B edge memory still qualified 5/5.

This does not mean a real circuit may be 30% sloppy. It means these particular errors are not the first-order kill mechanism that independent long-pass drift was.

The structural coherence idea therefore survives this first hostile emulator.

## 4. What actually became critical

### 4.1 The node self path

Common self-MDAC gain mismatch qualified at 1% but failed at 3%.

At 1% the qualification was already marginal:

```text
4/5 bodies >= +0.10 contrast improvement
4/5 final placed > shuffled
median improvement +0.205
median placement gap +0.193
```

At 3% essentially learning disappeared.

This is qualitatively different from edge-MDAC gain mismatch. Edge coefficients are the trainable geometry and the learner can partly adapt around a common static edge realization. The large node self term fixes the modal backbone of the recurrence and is not presently trainable. Its error can move the entire spectrum.

**Circuit consequence:** the +/-3.0 12-bit self MDAC needs calibration/trim for *accuracy*, not merely code resolution. The v0.2 target is <=0.3% residual node-to-node gain error after calibration.

### 4.2 The unity `-PREV` path

The `-z[n-1]` capacitor-ratio path showed almost the same boundary:

```text
1% RMS   qualified 5/5
3% RMS   failed
```

The inward target is <=0.3% RMS.

This makes sense physically: the exact second-order coefficient is the primitive that makes a current/previous pointer swap implement time reversal. A wrong coefficient is not merely a static Q mismatch; it changes the recurrence class and damages retracing itself.

**Circuit consequence:** the `-PREV` path gets a matched capacitor ratio plus calibration observable. It should not be implemented as an untrimmed approximate unity transconductor.

### 4.3 Terminal cloning

The one-time A -> B terminal-state copy is much less severe than the old long-pass stability problem, but it is not free:

```text
3% RMS clone mismatch   qualified
10% RMS                 failed
```

The inward target is <=1% RMS copy-gain error.

That is now the correct quantity to measure at bring-up gate C2.

### 4.4 Edge charge injection

The first clear switch-level limitation was lane-select-dependent edge charge injection:

```text
1e-4 state-FS RMS / active edge / tick   qualified
3e-4                                     failed
```

The inward target from the frozen rule is `3e-5` of state full scale RMS per active edge/tick.

This number is normalization-dependent: the emulator currently defines analog state full scale as 20 internal units. It must be translated into volts/coulombs only after a concrete state-cap voltage swing is selected. It should therefore be used as a **relative SPICE target**, not quoted as a transistor-level charge budget yet.

Practical mitigations to test are bottom-plate sampling, complementary/dummy switches, differential cancellation and keeping the coefficient-zero path physically disconnected.

## 5. Robust but not yet bounded axes

### Edge gain mismatch

No failure through 30% common edge gain CV. This is encouraging evidence that absolute reciprocal fabrication mismatch is fundamentally less dangerous than differential gradient-pass drift, provided it is one coherent realization.

It is **not** permission to design a 30%-accurate MDAC. The v0.2 implementation target remains much tighter for linearity/range reasons; the experiment only says this is not where the learner first dies.

### Edge settling

No failure through a 30% B-subphase edge-transfer deficit. The credit remains useful even when the instantaneous plus/minus gradient is badly scaled/distorted.

Again this is a learning-robustness result, not an analog-linearity specification. The conservative inward design value from the frozen grid is 10%.

### Error-DAC sign asymmetry

No failure through 30%. Reusing one magnitude code with opposite routing appears to be a strong structural choice. A 10% inward value is retained for the first combination test.

### LCC curvature

The normalized quartic curvature sweep was numerically almost invisible through `kappa=3`. This does **not** earn a useful square-law linearity boundary because the benchmark edge amplitudes occupy a small fraction of the declared state full scale, so the quartic term was weak in the actually visited region.

A later detector-specific test must sweep curvature against **observed LCC input amplitude**, not only state full scale.

### Credit-cap leakage

No failure through a 3% exponential decay rate per wave tick. At 1% and 3% the learner still strongly beat shuffled credit. The first combination test uses 1% per tick because that is one frozen grid step inward, but a real integrator can and should target substantially lower droop if inexpensive.

## 6. New circuit priority order

The emulator changes the implementation priority from

```text
make every analog coefficient fantastically stable
```

to

```text
1. precise/calibrated -PREV unity ratio
2. precise/calibrated node self MDAC
3. clean terminal A -> B state cloning
4. low differential lane-select charge injection
5. suppress A -> B edge-memory residue
6. ordinary edge settling / edge gain / error-sign matching
7. LCC linearity and credit retention at the actually used amplitude range
```

That is a much more conventional switched-capacitor design problem than 10-ppm stability between two long analog traversals.

## 7. What is not yet earned

These are independent one-axis results. Their inward values are **not** a Cartesian safe box.

The next registered experiment must combine the inward values on untouched arbors. It should also reintroduce the already-earned background imperfections from the older mixed-signal emulator (state leakage/noise and credit readout noise/offset) so the architecture is tested as one device rather than as ten isolated axes.

No ASIC/process/area/energy claim follows from this experiment.