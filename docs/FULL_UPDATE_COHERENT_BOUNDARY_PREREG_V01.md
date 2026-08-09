# TW-1A full-update coherent drift boundary — preregistration v0.1

Date frozen: 2026-08-09

## Motivation

Full-gradient-cycle coherence at 0.2% RMS operator variation passed the spent 970–979 block and narrowly failed fresh 990–999 only because one learner had a small negative DeltaC. The mechanism nevertheless gave 9/10 DeltaC >=0.10 and 10/10 exact final contrast above shuffled.

The next question is no longer architectural selection. It is the quantitative **coherence-window drift magnitude** that the same architecture can tolerate.

## Development data status

Use only now-spent seeds:

`990,991,992,993,994,995,996,997,998,999`.

No result from these seeds may itself establish a hardware requirement.

## Fixed hardware/task contract

Unchanged from `FULL_UPDATE_COHERENT_DRIFT_PREREG_V01.md`:

- rank-one reciprocal edge-cell Q;
- Q/DAC/ADC = 8/8/8;
- leakage = 0.0005/tick;
- leakage CV = 0.50;
- mirror error = 0.15;
- zero-mean credit noise = 0.25;
- credit offset = 0.00015;
- state noise = 5e-9 FS;
- static PGA;
- temporal-order contrast benchmark;
- 40 updates, step size 0.20;
- one complete spatially varying reciprocal Q realization frozen across all AB+BA forward/reverse traversals in one gradient evaluation, then redrawn next optimizer update.

Only the RMS magnitude of that coherent operator variation is swept.

## Frozen drift grid

`[0, 0.00025, 0.0005, 0.001, 0.0015, 0.002, 0.003, 0.005]`

Equivalent percentages:

`[0, 0.025%, 0.05%, 0.10%, 0.15%, 0.20%, 0.30%, 0.50%]`.

## Predicate

Use the existing final ten-seed predicate:

1. every exact DeltaC >0;
2. at least 8/10 DeltaC >=0.10;
3. median DeltaC >=0.15;
4. exact final > shuffled final in at least 8/10;
5. median placement gap >=0.10;
6. all values finite.

## Boundary rule

- pass prefix = consecutive qualifying drift magnitudes starting at zero;
- measured development boundary = largest drift in that prefix;
- fresh-confirmation candidate = one tested step inward from that boundary when possible;
- if all points pass, candidate = second-highest tested value;
- if only zero passes, stop with no nonzero candidate.

Later passing islands after the first failure do not extend the boundary.

## Fresh confirmation

If the algorithm selects a nonzero candidate, release untouched seeds:

`1000,1001,1002,1003,1004,1005,1006,1007,1008,1009`.

Run that one candidate once under the same full-update-coherent architecture and the same final predicate. No fallback.

## Claim if confirmed

A passing fresh candidate earns a **coherence-window drift tolerance**: the physical Q may differ from its nominal programmed value by that RMS amount, provided it remains effectively frozen over the complete AB+BA physical gradient evaluation.

This is distinct from the much tighter differential PLUS/MINUS mismatch tolerance when the operator changes inside one gradient evaluation.
