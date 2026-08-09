# TW-1A v0.9 separated task / fabrication / dynamic-noise factorial — preregistration

Date: 2026-08-09

Status: **diagnostic benchmark-harness study; no formal fresh qualification.**

The original experimental seed has been doing three jobs simultaneously:

1. generating the temporal-order task;
2. generating static fabricated circuit disorder;
3. determining dynamic stochastic noise streams.

The fresh 2400..2409 controls proved this is scientifically awkward: seed 2405 is intrinsically hard even for ideal physical credit, while seed 2400 is highly learnable ideally but weak for one mixed-signal draw. In addition, the older v0.9 harness allowed edge kT/C and credit readout noise to consume a shared generic RNG stream, so disabling one source could shift samples seen by the other.

`transientwave/circuit_emulator_v09_partitioned_rng.py` changes **only stochastic bookkeeping**. Static circuit equations/tolerances remain the same, but edge thermal, self thermal, drift thermal and credit readout receive independent RNG streams and can be explicitly reseeded after fabrication.

## Fixed task

Use only temporal-order task seed:

```text
TASK = 2400
```

Its ideal physical-credit improvement is frozen at approximately

```text
DeltaC_ideal = +0.864382
```

so failure to reach +0.10 cannot be attributed to intrinsic task difficulty.

## Fabrication axis

Independent static circuit seeds:

```text
2400, 3000, 3001, 3002, 3003
```

Seed 2400 deliberately includes the original problematic fabrication draw. Seeds 3000..3003 are exploratory diagnostic draws and are not reserved for later formal qualification.

Each fabrication is constructed once per run with the unchanged v0.9 physical point:

```text
edge b                  2e-5
kick-self b             2e-5
drift b                 2e-5
edge nominal range      0.265
edge unit mismatch      3% RMS
site-ratio mismatch     1% RMS
edge kick model         unchanged
post-cancel drift common residual 5 ppm RMS
post-cancel drift C/D differential 5 ppm RMS
all converter/leakage/LCC/credit settings unchanged
```

No residual trim is applied in this first factorial.

## Dynamic-noise axis

After static fabrication and disorder copying are complete, reseed only the partitioned dynamic streams with:

```text
8000, 8001, 8002, 8003, 8004
```

Target and distractor physical measurements receive deterministic role offsets from each dynamic seed; static silicon is unchanged.

This yields 25 task-identical training runs.

## Frozen learning protocol/readout

```text
30 updates
step size 0.20
RMS-normalized update
same fixed shuffled-credit control
```

For every cell report:

```text
DeltaC
placement gap
final exact > shuffled
hardware / ideal DeltaC ratio
```

For each fabrication seed summarize the five dynamic replicates:

```text
count DeltaC >= +0.10
count final exact > shuffled
median/min/max DeltaC
median hardware/ideal ratio
```

## Interpretation frozen before results

- If fabrication 2400 succeeds for most independent dynamic seeds, its historical red result contains a substantial dynamic-noise-sequence component.
- If fabrication 2400 is consistently weak while other fabrications succeed, the issue is primarily static silicon interaction/yield.
- If most fabrications show a broad dynamic success/failure spread, the current v0.9 operating point lacks stochastic SNR margin even if individual fresh cohorts look good.
- If most of the 25 runs are strong, the next qualification protocol should decouple task, fabrication and dynamic-noise seeds rather than using one seed as all three axes.

This diagnostic does not change the historical red fresh v0.9 result and does not authorize new formal seeds.
