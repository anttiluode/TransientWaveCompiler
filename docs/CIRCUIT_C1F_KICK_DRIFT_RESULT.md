# C1f — kick-drift two-bank shear — result

Date: 2026-08-09

Status: **PASS for deterministic topology/settling. Thermal/OTA noise remains unqualified.**

Preregistration: `docs/CIRCUIT_C1F_KICK_DRIFT_PREREG.md`

The gate reinterprets the existing two state vectors per lane as

```text
Z = z[n]
P = z[n] - z[n-1]
```

and uses two active virtual-sum state banks to execute

```text
P <- P + K*Z
Z <- Z + P.
```

Frozen deck:

```text
Cz = Cp = 1 nF
A0 = 1e5
switch Ron = 1 ohm
kick packet Ck = |K|*Cstate
unity drift packet Cd = Cstate
explicit non-overlap sample/transfer phases
read-only ideal buffers for source-state sampling
```

Five signed cases covered representative benchmark residual `|K|=0.00625` and
provisional full residual range `|K|=0.125`.

## Results

```text
max P1 scaled error          0.000480%
max Z1 scaled error          0.004285%
max P disturbance in drift   0.000000%
max virtual-sum excursion    3.000000 uV
```

Frozen limits were 0.1% for P/Z transfer and P disturbance and 100 uV for the
virtual summing nodes. All cases pass with wide deterministic margin.

## Interpretation

C1f establishes only that two finite-gain active state banks can realize the
kick-drift **shear topology** without the passive state-dependence that killed
C1b. It does not establish that the unity `P -> Z` transfer is thermally cheap.
The deck deliberately includes a full-size `Cstate` sample capacitor for that
unity drift, so the next gate must account for its kT/C / buffer / OTA noise or
find a more structural non-resampling state transfer.

The important architectural fact remains: `(Z,P)` uses the same two vectors per
lane as `(CUR,PREV)`. No extra trajectory/state bank is introduced, and the
terminal common/difference echo boundary has already been proven exactly in
unit tests.
