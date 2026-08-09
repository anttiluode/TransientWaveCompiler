# TW-1A v0.9 fresh failure diagnosis — preregistration

Date: 2026-08-09

Status: **diagnostic only on now-spent fresh bodies 2400..2409.**

The formal fresh gate failed the frozen 10/10 improvement clause while retaining fabrication 10/10, exact-over-shuffled 10/10 and passing median clauses. Only seeds 2400 and 2405 failed to improve by +0.10.

This diagnostic is frozen before inspecting modified conditions. It does not authorize new fresh seeds or change the formal threshold.

## Reference point

Reproduce the exact failed fresh v0.9 point:

```text
edge b                  2e-5
kick-self b             2e-5
drift b                 2e-5
drift common residual   5 ppm RMS
drift C/D diff residual 5 ppm RMS
```

All fabrication/converter/leakage/LCC/credit settings and the 30-update protocol remain unchanged.

## Surgical conditions

Use the same task/fabrication seeds and dedicated random-field definitions. Change only the named physical source:

```text
formal_reference
no_drift_switch_residual      common=diff=0
no_drift_thermal              drift b=0
no_edge_thermal               edge b=0
no_kick_self_thermal          kick-self b=0
all_thermal_zero              edge=kick-self=drift b=0
all_thermal_1e-5              edge=kick-self=drift b=1e-5
```

Additionally run the previously fresh-qualified **v0.8 self-thermal architecture** on the same 2400..2409 tasks at its frozen `b_edge=b_self=1e-5` operating point. This is a task-tail control, not a candidate v0.9 condition.

## Interpretation frozen before results

- If v0.8 is also weak on 2400/2405, the fresh failure primarily exposes benchmark/task-tail variation rather than a kick-drift-specific regression.
- If removing one v0.9 source alone restores 10/10, that source becomes the next quantitative circuit target.
- If `all_thermal_1e-5` restores 10/10 but no individual 2e-5 source removal does, the failure is a distributed thermal interaction and the 4x-capacitance corner lacks generalization margin.
- If `all_thermal_zero` still fails while v0.8 passes, inspect kick-drift quantization/static residuals before any new thermal tuning.
- If zero-thermal v0.9 and v0.8 are both weak, do not interpret the result as a circuit tolerance boundary; the benchmark family itself has a hard tail under the frozen 30-step learner.

No fresh seed is authorized by this diagnostic.
