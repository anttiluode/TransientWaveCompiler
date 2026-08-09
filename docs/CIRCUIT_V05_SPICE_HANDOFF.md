# TW-1A v0.5 SPICE handoff — Gate C0 edge cell

Status: **emulator-qualified architecture -> circuit-validation contract**.

This document is deliberately process-independent. It does not choose transistor
sizes, supply voltage, absolute state voltage full scale, or unit capacitor size.
It states what the first SPICE edge-cell experiment must measure before those
choices are allowed to propagate into a tile estimate.

---

## 1. What the emulator has now earned

The preregistered phase-symmetric v0.5 simultaneous corner passed on untouched
bodies 1500–1509:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median DeltaC       +0.500078
median placement gap +0.546270
minimum DeltaC      +0.227308
```

The passing corner retained the calibration, leakage/noise, autozero, error-DAC
and local-credit background from the failed v0.4 design. The architecture change
was specifically the removal of B-only edge settling/history.

The subsequent diagnostic SPICE-budget sweep on those now-spent bodies found:

```text
post-settle A/B gain mismatch RMS
  0.1%   all-body clean
  0.3%   all-body clean
  1.0%   all-body clean
  3.0%   all-body clean
 10.0%   failed

raw common settling loss (included in calibration map)
 10%     all-body clean
 20%     all-body clean
 30%     all-body clean
 40%     all-body clean
 50%     all-body clean
```

These are diagnostic boundaries on a finite task set, not new formal
qualifications. They are used only to choose inward circuit targets.

---

## 2. Preferred C0 topology: reset-equalized shared MDAC

The preferred implementation keeps **one digital edge code and one signed
coefficient array per physical bond**. It does not require two independently
programmed edge multipliers.

The key change from v0.2 is phase history:

```text
PARAM_HOLD: code_e fixed

A microcycle
  EDGE_RESET    force dynamic edge nodes to defined common mode
  A_SAMPLE      sample Delta z_A = z_Ai - z_Aj
  A_SETTLE      fixed settling aperture
  A_TRANSFER    stamp +q_A / -q_A into NEXT_A endpoints

B microcycle
  EDGE_RESET    force the same dynamic nodes to the same common mode again
  B_SAMPLE      sample Delta z_B = z_Bi - z_Bj
  B_SETTLE      the same settling aperture
  B_TRANSFER    stamp +q_B / -q_B into NEXT_B endpoints
```

The second `EDGE_RESET` is architectural, not optional dead time. It prevents the
B transfer from inheriting A's just-used charge/state and makes A and B see the
same initial condition and settling interval.

A fallback implementation may use two small matched post-settle holds fed from
one calibrated coefficient element. The emulator treats either implementation as
one common transfer plus a residual A/B mismatch.

---

## 3. Edge-transfer equation

For physical edge `e=(i,j)`, the intended rank-one action is

```text
Delta z_e = z_i - z_j
q_e       proportional to a_e * Delta z_e
NEXT_i   += q_e
NEXT_j   -= q_e
```

Let the fabricated edge-path gain be `g_e`, and let finite common settling leave
fraction `s_e` of the steady-state transfer. Foreground calibration measures the
combined transfer

```text
gbar_e = g_e * s_e.
```

The controller inverse-programs the fixed 8-bit edge code through the measured
map. During `PARAM_HOLD`, no calibration or weight write may change it.

For reverse A/B reuse, define the post-reset transfer gains

```text
g_A = gbar_e * (1 + delta_e/2)
g_B = gbar_e * (1 - delta_e/2).
```

`delta_e` is the v0.5 quantity SPICE must minimize. Absolute `gbar_e` error is a
calibration/range problem; `delta_e` is a gradient-coherence problem.

---

## 4. Inward C0 design targets

### 4.1 A/B phase symmetry — primary target

Diagnostic all-body behavior stayed clean through 3% RMS mismatch and failed at
10%. Therefore the **initial SPICE design target is**:

```text
RMS[(g_A-g_B) / ((g_A+g_B)/2)] <= 1%
```

across the intended input range after foreground calibration.

This is intentionally one third of the largest tested clean point. It is not a
claim that 1% is a hard mathematical boundary.

### 4.2 Common settling

The emulator remained clean through 50% common gain loss when that loss was
inside the measured edge map. Use the more conservative C0 timing target:

```text
common settled transfer >= 70% of steady-state
common settling loss     <= 30%
```

provided monotonicity, calibration range and code headroom remain valid.

The circuit should **not** burn power merely to make common gain settle to
99.99% if phase matching and calibration dominate the learning requirement.

### 4.3 Edge calibration residual

The qualified formal corner used:

```text
raw reciprocal edge gain CV     10%
edge-map fractional residual     0.1% RMS
```

C0 must therefore demonstrate a foreground measurement/pre-distortion loop that
leaves approximately

```text
<= 0.1% RMS transfer-map residual
```

or explicitly rerun the emulator with the achieved residual.

### 4.4 Charge injection after autozero/cancellation

The qualified corner used raw fixed edge packets

```text
common       3e-4 * state_full_scale RMS
differential 1e-4 * state_full_scale RMS
```

with 2% fractional cancellation error and residual floors of 2e-6 / 1e-6 FS.
The implied RMS post-cancellation scales are approximately

```text
common residual       sqrt((3e-4*0.02)^2 + (2e-6)^2) = 6.3e-6 FS
differential residual sqrt((1e-4*0.02)^2 + (1e-6)^2) = 2.2e-6 FS
```

Use rounded C0 targets:

```text
common edge-kick residual       <= 7e-6 FS RMS
differential A/B kick residual  <= 3e-6 FS RMS
```

These must be measured after the same reset/autozero sequence used during real
A/B evaluation.

---

## 5. Other retained contracts for later C1/C2 gates

The passing v0.5 corner also retained:

```text
-PREV raw mismatch             3% RMS
-PREV calibration residual     0.1%
-PREV trim                     12 bit, +/-12.5%
terminal clone raw mismatch    5% RMS
clone calibration residual     0.1%
error DAC sign asymmetry       10%
state leakage                  5e-4/tick mean, CV 0.50
state noise                    5e-9 FS emulator injection
credit noise                   25% of credit RMS
credit offset                  1.5e-4 energy-scale fraction
LCC curvature                  1.0 emulator parameter
credit-cap leakage             0.01/reverse tick
```

Do not translate the state-noise or LCC/credit emulator normalizations directly
into capacitor or transistor noise requirements. Those need a voltage-domain
re-identification after state full scale and the credit-cell circuit are chosen.

---

## 6. C0 SPICE measurements

For each edge-cell candidate, automate at least these measurements.

### Exact-zero / monotonic code

Sweep representative signed codes including

```text
0, +/-1, +/-2, +/-16, +/-64, +/-127
```

Check:

```text
code 0 disconnects programmable transfer;
sign reverses endpoint stamp;
|transfer| is monotonic with |code|;
no code produces opposite-sign local gain.
```

### Reciprocity / rank-one stamp

For each sampled differential input, measure endpoint transferred charge:

```text
q_i + q_j approximately 0
q_i - q_j has the programmed sign/magnitude
```

Reciprocity comes from one packet split equal/opposite, not from matching two
independently programmed coefficients.

### A/B phase-history test

Run both sequences:

```text
A(nonzero) -> RESET -> B(nonzero)
B(nonzero) -> RESET -> A(nonzero)
```

and measure normalized transfer mismatch. Also run

```text
A(nonzero) -> RESET -> B(zero)
B(nonzero) -> RESET -> A(zero)
```

to expose residual state-dependent memory after reset.

### Common-settling calibration test

Shorten the settle aperture intentionally until common transfer is only about
70%, then calibrate the code->transfer map and repeat A/B testing. The criterion
is not absolute DC accuracy before calibration; it is monotonic headroom plus
post-calibration phase symmetry.

### Charge-kick test

With zero differential input and representative codes, measure the state/summing
node disturbance left after reset/autozero. Separate

```text
common packet = (kick_A + kick_B)/2
differential packet = (kick_A - kick_B)/2.
```

Compare against the normalized FS targets above.

---

## 7. Monte Carlo / PVT ordering

Do not begin with a full 64-node transient simulation. C0 ordering should be:

1. nominal one-edge transient and code sweep;
2. mismatch Monte Carlo on the edge cell and reset switches;
3. calibration applied to each Monte Carlo sample;
4. A/B phase-history mismatch after calibration;
5. PVT corners with calibration rerun at each bring-up condition;
6. temperature/reference drift **during a frozen PARAM_HOLD** without recalibration.

The last item is important: calibration may run between gradients, not inside a
gradient.

---

## 8. What constitutes C0 success

C0 is ready to feed the two-node second-order C1 experiment when one concrete
edge implementation simultaneously shows:

```text
exact-zero code behavior;
monotonic signed transfer;
equal/opposite endpoint stamping;
post-calibration edge-map residual near 0.1% RMS;
A/B normalized transfer mismatch <= 1% RMS;
common settling loss <= 30% at chosen clock aperture;
post-autozero common kick <= 7e-6 FS RMS;
post-autozero differential kick <= 3e-6 FS RMS;
no measurable A->B state-dependent residue large enough to violate the 1% lane target.
```

If SPICE cannot meet these together, feed the measured error distribution back
into the circuit emulator rather than silently relaxing the requirements.

---

## 9. Next physical decision

The next unresolved physical quantity is **state voltage full scale**. Once a
candidate `VFS_state` is chosen, the normalized charge-kick and state-retention
contracts can be converted into volts/coulombs and a first unit-capacitance /
kT/C / switch-size study can begin.
