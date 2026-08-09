# TW-1A v0.8 self-sampling thermal diagnostic result

The frozen diagnostic in
`CIRCUIT_V08_SELF_THERMAL_DIAGNOSTIC_PREREG.md` passed on the spent fresh-qualified
bodies 2200--2209.

## Result

```text
condition      >=+0.10   wins   median DeltaC   min DeltaC   median gap
self_b0          10/10  10/10      +0.559700    +0.165905    +0.442903
self_b1e-5       10/10  10/10      +0.516990    +0.189823    +0.372913
```

The largest programmed self magnitude observed across the ten target tiles was
approximately

```text
|max self coefficient| = 2.878246
```

which gives a maximum local self-sampling thermal RMS fraction

```text
b * sqrt(|d|) = 1.69654e-5 state FS per tick
```

at `b=1e-5`.

## Interpretation

The two-slice reusable self actuator does not require a tighter state-cap thermal
base than the already-qualified active edge path under these spent-body tests.
Equal slicing changes instantaneous loading/timing but not total ideal sampling
variance:

```text
sigma_self / VFS = b * sqrt(|d|).
```

This result is diagnostic-only because the task bodies were already used by the
fresh kick-calibrated v0.8 qualification. The preregistered decision rule allows
a new fresh qualification on seeds 2300--2309 with self thermal enabled at the
same `b=1e-5` operating point.
