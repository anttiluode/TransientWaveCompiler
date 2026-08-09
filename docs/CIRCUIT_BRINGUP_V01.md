# TW-1A v0.2 Circuit Bring-up and Kill Gates

This is the hardware bring-up ladder for `tw1a-sc-lockstep-v0.2`. It separates requirements already earned by the mixed-signal emulator from new circuit hypotheses introduced by the lockstep/shared-element architecture.

## Rules

1. Do not rescue a failed gate by changing the mathematical task.
2. Keep the temporal-order target-vs-distractor benchmark and shuffled-credit control as the end-to-end test.
3. Record raw waveforms and calibration values, not only final learning score.
4. `PARAM_HOLD` disables coefficient writes and background calibration from the first objective forward pass through the last reverse pair.
5. A primitive gate must work before closed-loop learning is attempted.

## Inherited inward targets

These remain design targets, not universal theorems:

```text
edge code                              8 signed bits
forward drive                          8 signed bits
returned-error path                   10 signed bits for G=8 promise
sense ADC + static PGA                 8 bits
mean state leakage/tick               <= 0.001 recommended
local credit DC offset                <= 0.03% inward recommendation
zero-mean credit noise                <= 50% inward recommendation
```

The old 10-ppm simultaneous-corner number described **independent PLUS/MINUS operator perturbation**. The lockstep circuit is designed to replace that with same-element adjacent-subphase reuse. Do not relabel 10 ppm as a passive capacitor-matching requirement.

## Gate C0 — reciprocal edge cell

Bench object:

```text
one signed edge MDAC
held differential source at endpoint i
held differential source at endpoint j
two endpoint charge/sum capacitors
```

Required checks:

- exact zero code disconnects the magnitude array;
- positive/negative codes produce opposite sign;
- endpoint injections are equal/opposite after calibration;
- code transfer is monotonic over legal edge range;
- repeating lane-A then lane-B sampling through the same cell produces a residual distribution much smaller than two independent coefficient elements.

**Kill:** inability to calibrate the physical stamp to one scalar `a_e` acting on `z_i-z_j` invalidates the rank-one circuit choice.

## Gate C1 — second-order two-node recurrence

Add CUR/PREV differential state, local self coefficient, fixed `-PREV`, NEXT accumulation and state-role rotation.

Test against a compiled two-node recurrence for at least 100 ticks.

Required checks:

- no systematic energy creation at zero drive;
- measured recurrence coefficients remain stable under `PARAM_HOLD`;
- mean per-tick state loss meets the chosen retention target;
- pointer-role `CUR <-> PREV` reversal retraces substantially better than an intentionally wrong no-swap control.

**Kill:** if retracing requires storing the full forward trajectory, this implementation has failed the TW-1A point.

## Gate C2 — terminal clone + lockstep reverse pair

Sequence:

```text
forward in A
clone A.CUR/A.PREV -> B.CUR/B.PREV
pointer-swap mirror in A and B
inject +e into A and -e into B
advance A then B through the same MDAC every global tick
```

Measure:

- terminal clone gain/offset;
- error-DAC positive/negative symmetry;
- A/B operator residual when the same stored input waveform is replayed;
- slow coherent drift across a complete `PARAM_HOLD` window.

The measured same-element A/B residual becomes the new error parameter for the circuit-level emulator. It is not assumed in advance.

## Gate C3 — local signed credit cell

Add one shared square/integrate path and verify

```text
Cphysical ~= 1/4 sum_n (x_plus[n]^2 - x_minus[n]^2).
```

Controls:

1. identical PLUS/MINUS -> near-zero credit;
2. intentionally reverse one sign -> predicted credit sign change;
3. swap detector A/B subphase order -> same calibrated credit;
4. compare to two separate detector chains -> shared-element path should not be worse if common-mode cancellation is useful.

**Kill:** local offset/gain drift dominates signed credit even after same-element add/subtract and autozero.

## Gate C4 — 2x2 or 4x4 closed-loop board

Use the real cell topology with FPGA sequencing. Include:

```text
compiled local symmetric Q
physical rank-one edge cells
static sense PGA
output-trace objective generation
terminal clone
lockstep reverse pair
local signed credit
host SGD
shuffled-credit control
```

Use a placement-sensitive objective, not simple energy minimization.

## Gate C5 — circuit-level emulator update

Replace generic pass-level errors with measured primitive distributions:

```text
edge_settling_rms
edge_charge_injection_bias
ab_subphase_edge_residual_rms
self_path_gain_error
history_unity_error
terminal_clone_gain_rms
terminal_clone_offset_rms
error_dac_sign_asymmetry
lcc_ab_gain_residual
lcc_offset_after_autozero
credit_cap_leakage
coherent_param_hold_drift_rate
```

Only after those measurements exist should a new simultaneous hardware envelope be preregistered.

## First 8x8 ASIC entry criteria

Do not tape out merely because a schematic simulates. Minimum evidence:

- C0-C4 primitive gates pass on hardware or transistor-level Monte Carlo with realistic parasitics;
- circuit-level emulator using measured distributions passes fresh-seed end-to-end learning and shuffled control;
- self path covers at least the derived +/-2.95 range;
- state retention target is met at the selected wave clock;
- static PGA keeps objective readout out of ADC dead zones/saturation;
- complete gradient fits inside a measured coherent `PARAM_HOLD` interval;
- area/energy model includes state buffers, capacitor arrays, LCCs, clocks and calibration.

## Strong circuit kills

The architecture should be abandoned or materially changed if:

- one shared edge cell cannot stamp equal/opposite endpoint charge accurately enough;
- A/B time-multiplexing through one cell creates memory/settling error comparable to independent-pass drift;
- terminal clone cannot be calibrated without recreating the whole forward pass;
- local same-element square/add/subtract cannot produce useful placement-sensitive credit;
- state retention/settling hardware becomes more expensive than simply digitizing and storing the trajectory.
