# TW-1A / TWC status — 2026-08-09

This note is the shortest **current** map of what the branch has actually earned. Older hardware sweeps remain in their original benchmark/result documents; this file deliberately reflects the latest evidence rather than freezing the project at v0.5/v0.8.

## 1. The physical wave body is real enough to keep

The compiler's physical semantic is a sparse reciprocal mesh. A trainable bond is one reciprocal rank-one edge cell:

```text
Q += a_e (e_i-e_j)(e_i-e_j)^T.
```

That correction killed the earlier invalid entrywise-Q quantization model and survived subsequent circuit work.

The architecture then became increasingly structural rather than tolerance-driven:

- analog `-PREV` ratio multiplication was deleted; the PREV bank is reinterpreted with opposite differential orientation, making the `-1` history coefficient structural;
- reverse PLUS/MINUS storage became common/difference coordinates, deleting the arbitrary terminal analog clone and matched bipolar error-DAC pair;
- passive state accumulation was **rejected in ngspice** because an identical packet changed an empty versus precharged state by about 50% different amounts;
- active virtual summing passed the same packet-additivity test;
- the large self coefficient was split into two transfers and one half-range self bank can be reused;
- the kick-drift `(Z,P)` representation passed deterministic algebra, echo-boundary equivalence, state-range audit and ngspice C1f two-bank shear tests.

Those are retained circuit results. None depends on the later stochastic-learning diagnosis.

## 2. The formal v0.9 fresh gate is red and stays red

At the frozen small-cap kick-drift point, fresh tasks/fabrications 2400–2409 gave:

```text
fabrication success         10/10
median contrast improvement +0.332
improvement >= +0.10         8/10
```

The old entangled harness also showed 10/10 exact-over-shuffled, but a later audit found that one integer seed simultaneously selected task, fabricated silicon and stochastic dynamic streams. Some thermal and credit noise also consumed shared RNG state. That made the old cohort unsuitable as a stochastic-yield statement.

The red formal result is preserved rather than retroactively repaired.

## 3. The old +0.10 absolute benchmark had an intrinsic task tail

An ideal-physical-credit control on the same fresh cohort found:

```text
task 2400 ideal DeltaC = +0.864382
task 2405 ideal DeltaC = +0.0529
```

Therefore an unconditional `DeltaC >= +0.10` requirement is impossible for at least part of the task distribution. Future formal qualification must separate:

```text
task learnability ceiling
fabrication realization
dynamic stochastic replicate.
```

That benchmark correction does **not** rescue the small-cap hardware point, because task 2400 is strongly ideal-learnable and still fails broadly once the stochastic axes are factored.

## 4. Partitioned RNG changed the thermal conclusion

The v0.9 emulator now gives independent reproducible streams to:

```text
edge thermal
self thermal
drift thermal
credit readout
```

and exposes dynamic reseeding without redrawing static fabricated silicon. Structural tests prove that drawing one noise source cannot advance another source's stream and that dynamic reseeding leaves the fabricated device unchanged.

### Fixed task 2400 x five fabrications x five dynamic replicates

At the formal `b=2e-5` point:

```text
DeltaC >= +0.10       1/25
exact > shuffled     16/25
```

Fabrication 3001 loses exact-over-shuffled on all five dynamic replicates, while dynamic seed 8002 loses placement on all five fabrication seeds. The point therefore has both a broad stochastic-margin problem and a secondary static-silicon interaction.

Result: `docs/BENCHMARK_V09_SEED_AXIS_FACTORIAL_RESULT.md`.

## 5. Thermal-source factorial: the static machine is strong, sampled noise is not

On task/fabrication 2400 with edge/drift switch residuals set exactly to zero:

| thermal sources | >= +0.10 | exact > shuffled | median DeltaC |
|---|---:|---:|---:|
| none | 5/5 | 5/5 | +0.687113 |
| self only | 3/5 | 5/5 | +0.149811 |
| edge only | 0/5 | 4/5 | +0.019995 |
| drift only | 1/5 | 2/5 | -0.014737 |
| edge+self+drift | 0/5 | 3/5 | +0.028717 |

No single-source removal closes the all-on point. The failure is distributed/interaction-limited, with edge and unity-drift sampling especially severe.

Result: `docs/BENCHMARK_V09_THERMAL_FACTORIAL_RESULT.md`.

## 6. The attractive 4.27x capacitor point is not qualified

The deterministic kick-drift rewrite reduced the known capacitor expression enough that, under the previous uniform `b=2e-5` assumption, the known-cap subtotal was about 0.234x the v0.8 estimate — the often-quoted **4.27x reduction**.

The partitioned stochastic model does not support using that point.

A preregistered uniform thermal backoff swept all three sampled thermal bases together:

```text
b = 0, 2.5e-6, 5e-6, 7.5e-6, 1e-5, ... 2e-5.
```

Only `b=0` met the frozen robustness criterion. Even `b=2.5e-6` failed, despite requiring

```text
(2e-5 / 2.5e-6)^2 = 64x
```

more common capacitance than the attractive small-cap point.

Under the same illustrative assumptions that placed the `b=2e-5` known-cap subtotal near 3.70 mm^2, that 64x point would be about 237 mm^2 of known capacitors alone and still fails.

Therefore:

```text
CAPACITOR-ONLY RESCUE OF THE CURRENT STOCHASTIC ADJOINT: REJECTED.
```

Result: `docs/BENCHMARK_V09_UNIFORM_THERMAL_BACKOFF_RESULT.md`.

## 7. Repeating physical gradients does not rescue it cheaply

Averaging complete independently noisy physical gradients before each optimizer update gave:

| gradients averaged/update | >= +0.10 | median DeltaC |
|---:|---:|---:|
| 1 | 0/5 | +0.028717 |
| 4 | 0/5 | -0.006610 |
| 16 | 1/5 | +0.080290 |
| 64 | 2/5 | +0.095307 |

The preregistration stopped at 64. Sixty-four complete physical adjoints per update is already a severe time/energy tax and still does not qualify.

Result: `docs/BENCHMARK_V09_THERMAL_GRADIENT_AVERAGING_RESULT.md`.

## 8. Fixed-theta microscope: extreme variance plus a bias component

On task/fabrication 2400, the clean fabricated physical gradient has

```text
||g_ref|| = 2.358577541e-2.
```

After averaging **1024** noisy physical gradients at `b=2e-5`, median across five dynamic streams is only:

```text
cosine to clean gradient       0.280
projection onto clean gradient 0.191
relative vector error          1.048
trace standard error / ||g||   0.521
```

The single-acquisition stochastic gradient trace scale back-computes to roughly **16.7x the clean-gradient norm**. Even a variance-only extrapolation would require thousands to tens of thousands of complete gradient acquisitions for modest relative standard error, while the observed error also contains a non-negligible bias component.

The physical interpretation is important: a deterministic second-order trajectory can be reconstructed from terminal state, but a forward trajectory struck by independent sampled thermal packets contains stochastic history that the reverse pass does not possess. A new independently noisy reverse traversal is not the exact adjoint of that particular forward stochastic realization.

Result: `docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_RESULT.md`.

## 9. Forward-only estimators prove the body is trainable, but not cheaply on chip

The branch tested a completely different training family that never executes the reverse/credit path.

### Clean SPSA

Two-point simultaneous perturbation, four forward traversals per optimizer update, zero reverse traversals:

```text
c = 1.0
step = 0.40
3/3 clean direction sequences pass
median DeltaC = +0.446339
minimum DeltaC = +0.374621.
```

So the fabricated forward objective is genuinely optimizable without a physical adjoint.

### Thermal SPSA at b=2e-5

Across 15 dynamic x direction runs:

```text
DeltaC >= +0.10   3/15
exact > shuffled 11/15
median DeltaC     +0.045210.
```

### Full 64-row Walsh-Hadamard finite difference

The clean implementation is extremely strong:

```text
DeltaC = +0.839012
full reconstruction rank 39
max condition number 2.0.
```

At `b=2e-5`, all five thermal runs still improve and beat shuffled placement, but only 2/5 exceed +0.10 and median DeltaC is +0.099247. This costs **256 forward traversals/update**, or 7680 training forward traversals for 30 updates.

Therefore brute-force forward finite differences are useful evidence that the objective landscape survives, but are not accepted as an economical on-device trainer at the present thermal point.

Results:

- `docs/BENCHMARK_V10_FORWARD_SPSA_CLEAN_RESULT.md`
- `docs/BENCHMARK_V10_FORWARD_SPSA_THERMAL_RESULT.md`
- `docs/BENCHMARK_V10_FORWARD_HADAMARD_THERMAL_RESULT.md`

## 10. Current hardware conclusion

The branch no longer supports this sentence:

> "TW-1A is a small-cap general on-device gradient-learning accelerator."

What it **does** support is narrower and more interesting:

> The deterministic reciprocal transient-wave body and several concrete switched-cap circuit primitives are valid research results, but economical stochastic on-device gradient recovery at the `b=2e-5` point has not survived controlled task x fabrication x dynamic-noise experiments.

The chip should therefore remain a research object unless a genuinely different physical estimator eliminates the stochastic trajectory-replay problem. More capacitor sizing and more repetitions are not the mainline.

## 11. The compiler/application side has now passed an external-domain test

The same sparse reciprocal operator machinery was moved into the classical coupled-resonator filter formalism instead of another temporal-order toy.

For the published three-resonator matrix

```text
M = [[0,   .6, .2],
     [.6,  0,  .6],
     [.2, .6,  0 ]],
```

TWC's exact inverse-matrix edge gradient recovered the published coupling values from **5/5 deliberately detuned starts** to worst parameter RMSE about `1.14e-4`.

Then diagonal resonator self-detuning terms were promoted to trainable knobs. With all three resonator offsets and all three couplings wrong simultaneously, the six-knob benchmark again passed **5/5 exact recovery**:

```text
worst overall six-parameter RMSE   0.009734
worst resonator-detuning RMSE      0.013222
worst coupling RMSE                0.003832
worst |S11| magnitude error       3.37e-4
worst |S21| magnitude error       1.93e-4.
```

Results:

- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_RESULT.md`

A generalized explicit source/resonator/load coupling-matrix model is now being used for a larger published cross-coupled fourth-order filter with source-load coupling and multiple transmission zeros.

## 12. Shortest current picture

The project has split cleanly into two objects:

### TW-1A chip

A serious circuit-research artifact. Structural deletions, active summation, kick-drift state, converter semantics and ngspice evidence are worth preserving. The present small-cap stochastic physical-adjoint training claim is **not qualified**.

### TWC compiler / reciprocal-system tuner

Now the stronger mainline. It already tunes a published coupled-resonator filter from detuned starts and recovers both coupling and resonator self terms with exact audited gradients on an ordinary computer.

The near-term destination is therefore:

> **compile, analyze and tune sparse reciprocal wave/filter systems first; treat a future physical TW-1A substrate as one possible target backend rather than the reason the compiler exists.**
