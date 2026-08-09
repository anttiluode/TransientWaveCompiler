# TW-1A v0.9 partitioned thermal-source factorial — result

Date: 2026-08-09

Status: **diagnostic FAIL at the uniform `b=2e-5` point; distributed thermal interaction identified. No fresh qualification authorized.**

Preregistration: `docs/BENCHMARK_V09_THERMAL_FACTORIAL_PREREG.md`

Workflow: `v09-partitioned-thermal-factorial`, successful run `31328045529`.

## Why this rerun exists

The earlier v0.9 kick-drift thermal experiments used the old stochastic bookkeeping in which one seed selected task, fabrication and dynamic trajectories, and some dynamic sources consumed a shared RNG stream. The partitioned-RNG emulator changes no circuit equation. It only gives edge thermal, residual-self thermal, drift thermal and credit readout independent reproducible streams and allows dynamic reseeding without redrawing static silicon.

The first Actions attempt was stopped by a structural guardrail because the RNG unit test still instantiated the removed analog `-PREV` calibration path. The test was corrected to `prev_ratio_calibration=False`; no circuit parameter or learner outcome was inspected before the successful matrix reran.

## Frozen point

```text
task seed              2400
fabrication seed       2400
dynamic seeds          8000..8004
edge switch residual   0
drift switch residual  0
edge b                  0 or 2e-5
kick-self b             0 or 2e-5
drift b                 0 or 2e-5
```

Task 2400 has the previously frozen ideal physical-credit improvement

```text
DeltaC_ideal = +0.864382
```

so a weak result here cannot be blamed on the intrinsic task-tail failure found at task 2405.

## Results

| thermal sources on | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | maximum DeltaC | median gap | median HW/ideal |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 5/5 | 5/5 | +0.687113 | +0.660349 | +0.760447 | +0.725182 | 0.7949 |
| self | 3/5 | 5/5 | +0.149811 | +0.073171 | +0.197276 | +0.161905 | 0.1733 |
| edge | 0/5 | 4/5 | +0.019995 | -0.111274 | +0.053696 | +0.033055 | 0.0231 |
| drift | 1/5 | 2/5 | -0.014737 | -0.060669 | +0.191079 | -0.012293 | -0.0170 |
| edge + self | 0/5 | 4/5 | +0.063291 | -0.133579 | +0.074443 | +0.049654 | 0.0732 |
| edge + drift | 0/5 | 2/5 | -0.005349 | -0.061588 | +0.042720 | -0.020044 | -0.0062 |
| self + drift | 0/5 | 4/5 | +0.034505 | -0.014122 | +0.037401 | +0.028767 | 0.0399 |
| edge + self + drift | 0/5 | 3/5 | +0.028717 | -0.046686 | +0.066484 | +0.039150 | 0.0332 |

The all-off control is the key reference. The same task and the same fabricated silicon learn strongly in every dynamic replicate when only the three sampled thermal streams are removed. Median improvement is `+0.687`, about 79.5% of the ideal task improvement.

## Preregistered diagnosis

No single-source removal closes the all-on point:

```text
remove edge   -> self + drift : 0/5 >= +0.10
remove self   -> edge + drift : 0/5 >= +0.10
remove drift  -> edge + self  : 0/5 >= +0.10
```

Therefore the frozen diagnosis is:

```text
distributed / interaction-limited thermal margin failure
```

There is still a useful sensitivity ordering. At `b=2e-5`, edge thermal alone is already 0/5 and unity-drift thermal alone is 1/5; residual-self thermal alone is less destructive at 3/5. That is evidence for where a redesign or time/area trade should first be tested, but it does **not** make edge or drift a unique culprit.

## What this changes

1. **Do not tighten switch cancellation first.** The experiment sets both edge and drift switch residuals to zero and still fails badly.
2. **Do not spend the next revision on static calibration first.** The all-thermal-off control is strong on the exact same fabricated body.
3. **Do not claim the uniform `b=2e-5` 4.27x known-capacitor point as qualified.** It is now a failed stochastic operating point.
4. **Do retain kick-drift itself.** The no-thermal machine is strong, and C1f remains a valid deterministic topology test. The failure is dynamic sampled-noise margin, not the kick-drift algebra.

## Relation to the older kick-drift thermal result

`docs/CIRCUIT_V09_KICK_DRIFT_THERMAL_RESULT.md` is retained unchanged as historical evidence. It reported 10/10 on the old spent cohort through `b_drift=2e-5`, but it predates partitioned dynamic RNG streams. The new factorial does not retroactively alter those measurements; it shows that they are not sufficient evidence for stochastic margin once task, fabrication and dynamic-noise axes are factored.

## Physical caution for the next sweep

The three `b` fields are independent emulator controls but are **not three free capacitor knobs in C1f**. In the present circuit interpretation:

```text
b = sqrt(kT/Cstate) / VFS
```

and the unity drift uses a sampled capacitor equal to `Cstate` so that its transfer coefficient is exactly one. Edge sampling also derives its base noise from the state-cap scale, with the edge ratio multiplying that base. A per-source `b` boundary sweep is therefore a sensitivity map only unless a concrete circuit mechanism is supplied for changing one source independently.

The next hardware step should first map the partitioned thermal boundaries, then attach any proposed improvement to a real mechanism (larger common state scale, coherent/correlated shear, oversampling/averaging, or a different unity-transfer topology) before updating the area model.
