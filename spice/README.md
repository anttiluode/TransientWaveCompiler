# TW-1A SPICE bring-up

This directory is the circuit-validation side of the emulator-qualified
**TW-1A v0.5 phase-symmetric** architecture.  The ladder is staged so an ideal
timing result cannot be mistaken for transistor feasibility.

## Current status

```text
C0a  phase-history reset/equalization       PASS in ngspice
C0b  signed reciprocal charge packet        PASS in ngspice
C0c  explicit 7-bit magnitude cap array     PASS in ngspice
C0c->learning nominal nonlinear codebook    QUALIFIED 10/10
C0d  mismatch topology study                PASS / segmented selected
C0d->learning 3% per-edge mismatch          QUALIFIED 10/10
C0e  absolute state-noise / capacitance     IN PROGRESS
```

## C0a — phase-history timing harness — PASS

`tw1a_v05_phase_symmetry.cir` compares one shared edge dynamic node with and
without the v0.5 reset before B.  The aperture is intentionally only ~70%
settled.

Measured with ngspice-42:

```text
A sequential gain       0.69868525
B sequential gain       0.48798225
sequential mismatch    35.511717%

A symmetric gain        0.69868525
B symmetric gain        0.69865950
symmetric mismatch      0.003686%
```

The circuit simulator therefore reproduces the emulator diagnosis: incomplete
**common** settling is compatible with learning; unequal A/B phase history is
not.

## C0b — signed reciprocal equivalent-cap packet — PASS

`check_edge_charge_cell.py` uses real capacitor redistribution with one
equivalent selected capacitance `|code|*Cunit`.

The tested signed codes passed:

```text
code 0                exactly zero transfer
endpoint stamp         equal/opposite
positive magnitude     monotonic
signed transfer        correct polarity
+/- code symmetry      0.000000% at tested mirrors
```

Representative endpoint motion:

```text
code +1    +0.399202 mV / -0.399202 mV
code +16   +6.201550 mV / -6.201550 mV
code +127  +40.49552 mV / -40.49552 mV
code -127  -40.49552 mV / +40.49552 mV
```

## C0c — explicit 7-bit array — PASS

`check_binary_edge_array.py` replaced the equivalent capacitor with seven
physical magnitude branches

```text
1, 2, 4, 8, 16, 32, 64 * Cunit.
```

After separating the static topology test from C0a's speed test and separating
DC numerical anchors from off-switch isolation, ngspice passed:

```text
positive codes checked             128 (exhaustive 0..127)
negative mirror codes checked        9
max array vs analytic error       0.000163%
max endpoint common residual      0 V (reported precision)
max tested sign asymmetry         0.000000%
zero-code differential leak       3.46e-13 V
```

The physical level spacing is intentionally nonlinear because of capacitor
charge sharing.  That nonlinear codebook was fed back into the full v0.5
emulator on untouched bodies 1600–1609 and **qualified 10/10**.  See
`docs/CIRCUIT_V05_CAPCODEBOOK_RESULT.md`.

## C0d — unit mismatch and segmentation — PASS

A frozen 5000-sample-per-point mismatch study compared the same 127 unit
capacitors as:

```text
pure 7-bit binary
4-bit binary + 3-bit thermometer segmentation
full thermometer
```

At 3% iid unit-cap mismatch:

```text
pure binary monotonic yield       99.82%
segmented 4+3 monotonic yield    100.00%
full thermometer yield           100.00%
```

Pure binary failures appeared at the expected large carry (`63->64`).  The
working topology is therefore:

```text
lower magnitude bank   1,2,4,8 unit groups
upper magnitude bank   seven ordered 16-unit thermometer segments
physical units total   127
selectable branches    11
```

The next formal bridge then gave **each of the 112 physical edge sites its own
independent 3%-sigma fabricated segmented codebook**.  On untouched bodies
1700–1709:

```text
fabricated monotonic tiles        10/10
monotonic edge codebooks          112/112 on every tile
learning DeltaC >= +0.10          10/10
final exact > shuffled            10/10
median DeltaC                    +0.581887
```

See `docs/CIRCUIT_C0D_MISMATCH_RESULT.md` and
`docs/CIRCUIT_V05_SEGMENTED_MISMATCH_RESULT.md`.

## Circuit-facing residual targets

The current emulator/SPICE handoff in `docs/CIRCUIT_V05_SPICE_HANDOFF.md` uses:

```text
A/B transfer mismatch       <= 1% RMS
common settling loss        <= 30% at chosen aperture
post-cal edge residual      ~ 0.1% RMS
common kick residual        <= 7e-6 state FS RMS
differential A/B kick       <= 3e-6 state FS RMS
unit-cap mismatch target    <= 3% sigma with 4+3 segmentation
```

## C0e — absolute scale — current work

The SPICE decks above use convenient absolute capacitor values.  What has been
validated is chiefly the ratio

```text
Cunit/Csum = 0.001.
```

C0e now measures how much normalized per-tick state noise the fully mismatched,
calibrated machine can tolerate.  That boundary will be translated to candidate
state capacitances using a first-order

```text
sigma_V ~= sqrt(kT/Cstate)
```

budget for several possible state-voltage full scales.

Only after that should the convenient C0b/C0c capacitor values be replaced by a
first realistic silicon size estimate.
