# TW-1A v0.9 partitioned uniform-thermal backoff — preregistration

Date: 2026-08-09

Status: **spent-body diagnostic only; no fresh qualification. Frozen before outcomes.**

## Motivation

The partitioned thermal-source factorial showed that the uniform

```text
edge b = self b = drift b = 2e-5
```

point is not stochastically robust on task/fabrication 2400 even with edge and drift switch residuals set to zero. The all-thermal-off control is strong, so kick-drift algebra/static fabrication remain viable.

Unlike independently changing the three thermal controls, a **uniform** change in base

```text
b = sqrt(kT/Cstate) / VFS
```

has a direct physical interpretation in the current C1f architecture: scale the common state/packet capacitance family while preserving all programmed capacitor ratios.

This experiment therefore asks a narrower hardware question:

> How far must the common kT/C base be backed off before the same fabricated kick-drift machine becomes robust across independent dynamic trajectories?

## Frozen task / silicon / dynamic axes

```text
task seed          2400
fabrication seed   2400
dynamic seeds      8000, 8001, 8002, 8003, 8004
ideal DeltaC       +0.864382
```

Construct the exact formal v0.9 fabrication first, then set both inherited edge-switch residuals and drift-switch residuals to zero **after construction**. This preserves the exact static draw and prevents fabrication RNG redraws.

All converter, leakage, codebook, site-ratio, self-gain/calibration, LCC and credit-path fields remain at the formal v0.9 point.

## Frozen uniform thermal grid

Set all three sampled thermal bases to the same `b`:

```text
0
2.5e-6
5.0e-6
7.5e-6
1.0e-5
1.25e-5
1.5e-5
1.75e-5
2.0e-5
```

For a given dynamic seed, every grid point reseeds the partitioned streams identically before training so changing `b` scales the same underlying edge/self/drift random samples rather than redrawing them.

## Frozen learner

```text
30 updates
step size 0.20
RMS-normalized credit
same fixed shuffled-credit permutation
```

## Frozen readouts

For every `b` report across five dynamic replicates:

```text
count DeltaC >= +0.10
count final exact > shuffled
median/min/max DeltaC
median/min placement gap
median/min hardware/ideal DeltaC ratio
```

Call a point **robust on this spent diagnostic** only if all hold:

```text
5/5 DeltaC >= +0.10
5/5 final exact > shuffled
median DeltaC >= +0.30
median placement gap >= +0.25
```

The diagnostic thermal boundary is the **largest** preregistered `b` satisfying all four clauses. The next smaller grid point is the provisional inward reference; neither is a fresh qualification.

## Frozen capacitor interpretation

For fixed temperature and full-scale convention,

```text
C ∝ 1 / b^2.
```

Relative to the current kick-drift `b=2e-5` known-cap estimate, a boundary `b*` costs

```text
cap_multiplier = (2e-5 / b*)^2.
```

Apply this multiplier only to the known capacitor subtotal under the same C1f scaling assumptions. Do not call it total chip area; OTA, switches, credit cells, routing, clocks and other active overhead remain excluded.

## Decision frozen before results

- If `b >= 1.5e-5` is robust, retain a substantial fraction of the kick-drift capacitor win and next investigate path-selective redesign only for margin/energy optimization.
- If the boundary lies around `1e-5`, the kick-drift algebra still survives but the current uniform-capacitance economic advantage largely collapses; path-selective or coherent-noise suppression becomes the next architectural question.
- If even `b <= 7.5e-6` is required, stop presenting the current sampled-cap kick-drift implementation as an area win. Preserve it as a research circuit and prioritize a different noise mechanism/topology before any fresh qualification.
- If no nonzero grid point is robust, treat the current independent-sampling noise model as fundamentally incompatible with the learner at this task length and investigate coherence/correlation or protocol-level gradient estimation before more capacitor tuning.

This experiment cannot change the historical red v0.9 fresh result and cannot repair the task-2405 qualification-tail problem. It only measures the physical kT/C backoff needed on one spent, strongly ideal-learnable task/fabrication pair.
