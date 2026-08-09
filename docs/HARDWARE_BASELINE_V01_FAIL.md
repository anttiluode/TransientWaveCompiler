# TW-1A hardware-emulator baseline v0.1 — FAIL

Date: 2026-08-09

Preregistration: `HARDWARE_ENVELOPE_PREREG_V01.md`

Execution correction: `HARDWARE_ENVELOPE_EXECUTION_NOTES_V01.md`

## Result

The requested baseline configuration is a **formal preregistered FAIL**.

The clean zero-imperfection physical-credit audit passed first: the four-pass `E_plus-E_minus` local credit matched finite-difference derivatives on the compiled irregular arbor. Therefore the baseline failure is not explained by a sign/indexing error in the echo-gradient implementation.

Frozen baseline:

```text
weight bits                8
DAC bits                    8
ADC bits                    8
state leakage               0
state noise                 0
time-mirror error           5%
differential +/- drift      0.2% RMS
credit readout noise        5%
iterations                  30
optimizer                   preregistered RMS-normalized SGD
```

Observed deterministic physical loss reductions:

```text
seed 810   exact +0.00000   shuffled +0.00000
seed 811   exact +0.41484   shuffled +0.41484
seed 812   exact +0.00000   shuffled +0.00000
seed 813   exact +0.30309   shuffled -0.03165
seed 814   exact +0.00000   shuffled +0.00000
```

Initial/final losses printed by the frozen test included repeated values

```text
0.00155971
```

for several tasks, making converter/weight resolution an immediate diagnostic suspect. That is only a clue; the preregistered isolated bit sweeps must distinguish DAC/ADC resolution from programmable-Q resolution.

## Frozen PASS rule comparison

Required:

```text
5/5 R >= .10
median R >= .15
exact placement beats shuffled >=4/5
median exact reduction - median shuffled reduction >= .10
```

Observed:

```text
2/5 R >= .10
median exact reduction = 0
```

Therefore the v0.1 baseline fails before the later criteria can rescue it.

## What may not be changed

This result is retained. Do not loosen thresholds, remove difficult seeds or relabel the baseline as successful.

The next valid question is the preregistered one:

> At what converter/weight resolution and other hardware tolerances does the exact same frozen task family cross from FAIL to PASS?

The default CI test is marked as an **expected failure** after this record was committed. If it unexpectedly begins passing without a declared semantic/version change, CI should flag that as an unexpected success rather than silently replacing this record.
