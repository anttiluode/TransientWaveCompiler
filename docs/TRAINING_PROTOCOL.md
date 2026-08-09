# Echo Training Protocol v0.1

## 1. Scope

This document specifies the **machine protocol** used to acquire parameter credit on a TW-1-compatible backend.

It does not claim invention of physical adjoint training or Hamiltonian echo learning. The protocol combines a reversible compiled recurrence with local edge observables so that a transient source-domain gradient can be recovered without storing the internal trajectory.

---

## 2. Preconditions

A training execution is legal only if the compiler has emitted:

- a symmetric reversible core `Q`;
- source/port schedules;
- an objective derivative lowering;
- trainable edge parameterizations;
- local credit scale factors;
- a valid terminal-mirror sequence;
- backend calibration within declared limits.

The reference recurrence is

```text
z[n+1] = Q z[n] - z[n-1] + u[n]
```

with `Q=Q^T`.

---

## 3. Edge parameter semantics

A trainable edge `e=(i,j)` uses

```text
b_e = e_i - e_j
```

and source-domain parameterization

```text
dM/dtheta_e = c_e * b_e b_e^T.
```

After scalar damping compilation `Q=M/r`,

```text
dQ/dtheta_e = (c_e/r) * b_e b_e^T.
```

Therefore the local gradient contribution is proportional to a time sum of

```text
(b_e^T forward_state) * (b_e^T adjoint_state).
```

This is exactly an **edge-difference times edge-difference** observable.

---

## 4. Pass 1 — forward

Start from compiler-declared initial states and run the compiled input schedule.

At each tick:

```text
source[n] -> mesh clock -> sense state n+1
```

The machine may accumulate the requested objective/readout observables, but it does **not** store internal node histories.

At the terminal boundary the live mesh contains the only distributed state needed for the echo:

```text
z[T], z[T-1].
```

The objective controller computes the error/readout derivative coefficients required by the emitted objective schedule.

---

## 5. Returned adjoint/error wave

For a quadratic readout objective in compiled coordinates,

```text
J = sum_k w_compiled[k] * y_z[k]^2
```

so

```text
dJ/dy_z[k] = 2 * w_compiled[k] * y_z[k].
```

The error port therefore needs only the measured output sample and the compiler-emitted multiplier.

For more complex supported objectives, the compiler supplies the derivative program explicitly.

---

## 6. Reverse echo alignment

The reverse execution regenerates the forward trajectory dynamically while injecting the returned error/adjoint signal.

At reverse index `j`, the machine aligns

```text
retraced forward state   ~ z[T-j]
returned adjoint state   ~ p[T-j+1]
```

according to the exact recurrence convention used by the backend.

The crucial machine invariant is not the names of the arrays; it is:

> The local forward factor and the local adjoint factor belonging to the same parameter derivative must be physically present at the same edge and same integration tick.

The backend validation suite must test this index alignment independently.

---

## 7. PLUS phase

For every trainable edge, the local credit path sees

```text
x_plus[t] = Delta f[t] + Delta a[t]
```

and integrates

```text
E_plus = sum_t gain[t] * x_plus[t]^2.
```

`gain[t]` is normally one for the ideal compiled core. A calibrated lossy echo backend may use a compiler-generated global integration envelope.

All edges integrate simultaneously.

---

## 8. MINUS phase

The same terminal state and schedules are reproduced, but the adjoint/error component changes sign:

```text
x_minus[t] = Delta f[t] - Delta a[t]
```

Each edge integrates

```text
E_minus = sum_t gain[t] * x_minus[t]^2.
```

Then

```text
raw_overlap = (E_plus - E_minus) / 4
```

because

```text
(x+y)^2 - (x-y)^2 = 4xy.
```

The compiler maps this raw overlap to the source parameter gradient using `compiled_credit_scale` plus objective/step conventions.

---

## 9. Why full bandwidth is free in the ideal accumulator

The LCC integrates directly in time. It does not select frequency bins.

Therefore

```text
sum_t Delta f[t] Delta a[t]
```

already includes the complete transient spectrum and all cross-frequency consequences permitted by the real time-domain fields.

A spectral K-bin representation can still be useful for diagnostics or alternative hardware, but it is not required by the TW-1 reference protocol.

---

## 10. Four-pass reference schedule

Without terminal-state duplication:

```text
0 RESET/CALIBRATE

1 FORWARD
  - run input
  - acquire objective
  - end at terminal live state

2 REVERSE_PLUS
  - arm terminal mirror
  - inject +error schedule
  - integrate E_plus locally

3 FORWARD_RECREATE
  - reset
  - rerun identical input
  - recreate terminal live state

4 REVERSE_MINUS
  - arm terminal mirror
  - inject -error schedule
  - integrate E_minus locally

5 UPDATE
  - form local credits
  - apply optimizer/projection
```

The four traversals are independent of `N`, `E`, and `T` in pass count. Runtime still scales with the physical transient duration.

---

## 11. Three-pass option

If terminal state can be duplicated/restored without replaying the whole forward trajectory:

```text
FORWARD
REVERSE_PLUS
RESTORE_TERMINAL_STATE
REVERSE_MINUS
```

The state snapshot is only `O(N)`.

The compiler resource report should distinguish:

```text
trajectory memory    O(N*T)  -- forbidden/not required
terminal snapshot    O(N)    -- optional optimization
```

---

## 12. Single-run lock-in option

A future backend may modulate the adjoint sign during one reverse trial and use a synchronous signed accumulator.

This can remove the separate `+/-` trials only if self-energy leakage is sufficiently rejected by modulation/spectral separation.

It is **not** the v0.1 correctness path because pass-to-pass subtraction is easier to reason about and test.

---

## 13. Loss-compensated echo backend

If the physical compiled core has calibrated uniform residual recurrence loss `alpha`, the reverse trajectory may be an exponentially scaled retrace rather than a literal retrace.

The backend can compensate using compiler-emitted global envelopes so that the local overlap integral remains exact for the calibrated model.

The important architectural result is:

```text
uniform known loss -> global schedule / dynamic-range tax
```

not necessarily distributed history memory.

Generic spatially varying loss does not admit the same scalar correction and is treated as an approximation/error source.

---

## 14. Pass-to-pass drift

The `E_plus - E_minus` subtraction cancels large self-energy terms only when the two trials are sufficiently matched.

The compiler/backend therefore exposes a **differential pass-drift specification**, distinct from ordinary static calibration error.

Development simulations from the parent project suggest the following rough gradient-map behavior under its tested conditions:

```text
+/- differential operator drift   mean gradient correlation
0.05%                             ~0.996
0.10%                             ~0.987
0.20%                             ~0.943
0.50%                             ~0.801
1.00%                             ~0.572
```

These values are not universal chip specifications. They are the first engineering targets to reproduce on the reference simulator and eventually on hardware.

---

## 15. Update modes

### Host optimizer

The chip digitizes one scalar credit per trainable edge. A host applies:

- learning rate;
- clipping;
- projection to edge range;
- optional material-budget constraint;
- optimizer state.

This is the v0.1 validation path.

### Local SGD

```text
theta_e <- clip(theta_e - eta * grad_e, min_e, max_e)
```

implemented locally.

### Local budget-constrained update

Groups of edges may share a total material budget. This requires a local/group projection mechanism or a host-side projection. It is useful for geometry-learning experiments but not mandatory for first hardware.

---

## 16. Validation hierarchy

A backend earns training support in this order:

### V1 Forward semantics

Compiled and source trajectories/readouts agree within tolerance.

### V2 Echo retrace

With no error injection, reverse execution reconstructs the declared forward factors.

### V3 Adjoint semantics

Returned error wave agrees with a numerical transpose/adjoint reference.

### V4 Local overlap

Ideal `+/-` measurements match numerical parameter gradients.

### V5 Damaged overlap

Calibration error, residual loss, mirror error, noise, and drift produce bounded degradation.

### V6 Closed-loop learning

Measured hardware credits improve the **source-domain** objective repeatedly.

Static gradient correlation alone is not sufficient for V6.

---

## 17. First training demo

The recommended first real demo is intentionally small:

```text
32-64 nodes
16-32 trainable reciprocal edges
2 drive ports
1-2 sense/error ports
T ~ 64-256 ticks
quadratic or contrast-energy objective
```

Show:

1. no trajectory RAM;
2. a measurable transient computation;
3. local scalar credits from echo passes;
4. credit/shuffle control;
5. several physical parameter updates;
6. improvement of the source-domain objective.

That would validate the architecture more directly than a large benchmark implemented with hidden digital assistance.