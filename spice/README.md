# TW-1A SPICE bring-up

This directory starts the transistor/circuit validation side of TW-1A.

The current emulator-qualified architecture is **v0.5 phase-symmetric**.  The
SPICE work is intentionally staged so an ideal timing result cannot be mistaken
for transistor feasibility.

## C0a — phase-history timing harness

`tw1a_v05_phase_symmetry.cir` is a process-independent RC/switch experiment. It
compares two uses of one edge dynamic node with an intentionally incomplete
(~70%) settling aperture:

1. `edge_seq`: reset before A only; B inherits A's dynamic-node history;
2. `edge_sym`: reset before A **and again before B**.

The expected result is:

```text
absolute/common A and B gain only ~0.7
sequential A/B mismatch large
phase-symmetric A/B mismatch ~0 in the ideal-reset abstraction
```

`check_phase_symmetry.py` parses the ngspice measurements and fails CI if those
relationships do not hold.

This is **not** the edge MDAC transistor circuit. It proves the timing harness and
the architectural meaning of the v0.5 reset/equalization phase.

## C0b — next

Replace the RC/sample abstraction with a concrete signed exact-zero
switched-capacitor edge cell while retaining the same measurement harness:

```text
8-bit signed edge code
sample Delta z = z_i-z_j
one reciprocal packet
equal/opposite endpoint stamping
EDGE_RESET before each A/B use
foreground code->transfer calibration
```

C0b must measure the targets in `docs/CIRCUIT_V05_SPICE_HANDOFF.md`, especially:

```text
A/B transfer mismatch <= 1% RMS
common settling loss   <= 30% at chosen aperture
post-cal edge residual ~0.1% RMS
common kick residual   <= 7e-6 state FS RMS
diff A/B kick residual <= 3e-6 state FS RMS
```

Absolute capacitor size, VDD and state voltage full scale remain intentionally
open until C0b chooses a device/process context.
