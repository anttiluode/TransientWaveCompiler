# TW-1A v0.9 kick-drift self residual audit — result

Date: 2026-08-09

Status: **algebra/compiler audit PASS; circuit implementation not yet qualified.**

The exact coordinate identity

```text
p[n] = z[n] - z[n-1]
K = Q - 2 I

p[n+1] = p[n] + K z[n] + u[n]
z[n+1] = z[n] + p[n+1]
```

was tested against the existing second-order recurrence for one step, 100 steps and exact inverse retracing. All tests passed to machine precision. Subtracting `2I` leaves every reciprocal edge/rank-one parameter derivative unchanged.

## Qualified-task audit

On spent fresh-qualified temporal-order tasks `2300..2309`, all ten compiled operators give the same active-node values:

```text
scalar damping-gauge inertial q0       2.000264445
old active-node self |d|max            1.993759520
kick self |d-2|max                     0.006240480
force-only self |d-q0|max              0.006504925
edge coefficient delta after -2I       0 exactly
```

Summary:

```text
old/new active self magnitude ratio    319.488x
sampling-noise amplitude ratio         sqrt(319.488) = 17.874x
```

The large old self coefficient is therefore overwhelmingly the universal second-order inertial baseline, not node-specific onsite physics.

For the source class used by the benchmark,

```text
Q = [(1+a)I - dt^2 H] / sqrt(a)
q0 = sqrt(a) + 1/sqrt(a).
```

After the graph Laplacian is lowered into the existing reciprocal rank-one edge cells, the remaining source-physics self term is approximately

```text
-dt^2 * onsite / sqrt(a),
```

which is small at the current `dt=0.08` benchmark.

## Hardware interpretation

This result does **not** establish that a fixed `+2*CUR` operation is free. It only establishes that making a wide programmable sampled-capacitor self DAC perform that universal operation every tick is not mathematically necessary.

The first v0.9 circuit abstraction therefore keeps the v0.8 position-history storage and structural `-PREV`, but splits

```text
d_i = g_inertial_i + k_residual_i
```

where `g_inertial` is a fixed measured near-2 path and only `k_residual` is programmable. Static fixed-path gain error can be foreground-measured and absorbed into the residual code as long as range remains. Dynamic noise/drift of the fixed path remains a real circuit requirement and is being swept separately.

## Provisional capacitor consequence

Replacing the current max `1.5*Cstate` reusable self bank per node by a `0.125*Cstate` residual bank changes the known tile capacitor subtotal from

```text
v0.8: 256 + 29.68 + 96.00 = 381.68 Cstate
v0.9 provisional: 256 + 29.68 + 8.00 = 293.68 Cstate
```

before adding any area needed by the fixed inertial path itself. This is a hypothesis for the cost model, not a layout estimate.
