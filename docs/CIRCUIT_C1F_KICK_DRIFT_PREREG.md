# C1f — kick-drift two-bank shear — preregistration

Status: process-independent deterministic ngspice kill gate.

The exact kick-drift coordinate probe reinterprets the existing two temporal
state vectors as

```text
Z = z[n]
P = z[n] - z[n-1]
```

and advances

```text
P <- P + K Z
Z <- Z + P
```

for a scalar local test (source omitted in this gate). C1f asks whether two
active virtual-sum state banks can perform those shears without passive
state-dependent charge sharing.

## Frozen deck abstraction

- `Cz = Cp = 1 nF` feedback/state capacitors;
- finite idealized op-amp DC gain `A0 = 1e5` on each virtual-sum bank;
- switch on-resistance `1 ohm`;
- a `|K|*Cstate` sampled packet capacitor for the kick;
- one `Cstate` sampled packet capacitor for the unity drift;
- ideal high-input-impedance voltage buffers sample Z and updated P without loading their storage nodes;
- explicit non-overlap between sample and transfer phases.

The full-size unity drift sample is intentionally present. C1f does **not** call
that operation thermally free; it only tests deterministic topology, settling
and state additivity. Noise/PVT/OTA power remain later gates.

## Frozen cases

Exercise positive/negative Z, P and K including

```text
|K| = 0.00625   representative active benchmark residual
|K| = 0.125     provisional v0.9 residual full scale
```

## Acceptance

For every case compare ngspice against

```text
P1 = P0 + K*Z0
Z1 = Z0 + P1.
```

Require:

```text
relative-or-1mV-scaled P1 error  <= 0.1%
relative-or-1mV-scaled Z1 error  <= 0.1%
P disturbance during Z drift     <= 0.1%
max virtual-sum excursion         <= 100 uV
```

No learning qualification follows directly from C1f. A pass only earns the
right to model/measure dynamic noise of the two unity state shears.
