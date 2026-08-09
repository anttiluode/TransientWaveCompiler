# TW-1A SPICE bring-up

This directory starts the transistor/circuit validation side of TW-1A.

The current emulator-qualified architecture is **v0.5 phase-symmetric**. The
SPICE work is intentionally staged so an ideal timing result cannot be mistaken
for transistor feasibility.

## C0a — phase-history timing harness — PASS

`tw1a_v05_phase_symmetry.cir` is a process-independent RC/switch experiment. It
compares two uses of one edge dynamic node with an intentionally incomplete
(~70%) settling aperture:

1. `edge_seq`: reset before A only; B inherits A's dynamic-node history;
2. `edge_sym`: reset before A **and again before B**.

Measured with ngspice-42:

```text
A sequential gain       0.69868525
B sequential gain       0.48798225
sequential mismatch    35.511717%

A symmetric gain        0.69868525
B symmetric gain        0.69865950
symmetric mismatch      0.003686%
```

Thus the circuit simulator reproduces the emulator diagnosis: incomplete common
settling is compatible with phase coherence, while unequal A/B phase history is
not.

## C0b — signed reciprocal equivalent-cap packet — PASS

`check_edge_charge_cell.py` generates ngspice decks using one equivalent selected
edge capacitance `|code|*Cunit` and real capacitor charge redistribution into two
endpoint sum capacitors.

The sweep checks codes

```text
0, +1, +2, +16, +64, +127, -1, -16, -127
```

and passed all checks:

```text
code 0                exactly zero transfer
endpoint stamp         equal/opposite to numerical precision
positive magnitude     monotonic
signed transfer        correct polarity
+/- code symmetry      0.000000% at |code| 1,16,127
```

Representative measured endpoint voltages:

```text
code +1    +0.399202 mV / -0.399202 mV
code +16   +6.201550 mV / -6.201550 mV
code +127  +40.49552 mV / -40.49552 mV
code -127  -40.49552 mV / +40.49552 mV
```

The measured redistribution also agrees with the analytic capacitor-sharing
formula to the C0b tolerance.

C0b proves the reciprocal signed packet abstraction, but its magnitude DAC is
still represented by one equivalent capacitance.

## C0c — explicit 7-bit magnitude array — next

Replace the equivalent `|code|*Cunit` capacitor by seven independently switched
binary branches:

```text
1, 2, 4, 8, 16, 32, 64 * Cunit
```

with exact magnitude-zero obtained by disconnecting every programmable branch.
C0c must reproduce C0b's signed transfer across representative and exhaustive
codes before mismatch is introduced.

## C0d — unit mismatch + foreground calibration

After C0c, perturb the explicit capacitor branches and switch parasitics, measure
the resulting code->transfer map, and test whether foreground calibration can
meet the emulator-qualified residual target without losing monotonicity or code
headroom.

The current circuit-facing targets from `docs/CIRCUIT_V05_SPICE_HANDOFF.md` are:

```text
A/B transfer mismatch       <= 1% RMS
common settling loss        <= 30% at chosen aperture
post-cal edge residual      ~ 0.1% RMS
common kick residual        <= 7e-6 state FS RMS
differential A/B kick       <= 3e-6 state FS RMS
```

Absolute capacitor size, VDD and state voltage full scale remain intentionally
open until a device/process context is chosen.
