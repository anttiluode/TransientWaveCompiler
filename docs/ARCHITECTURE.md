# TW-1 Reference Architecture v0.1

## 1. Purpose

TW-1 is a reference mixed-signal computer for **finite-time sparse wave programs**. It is inspired by the Geometric Neuron experiments in one specific sense: computation is not represented as a sequence of dense layers. A fixed physical geometry defines a distributed dynamical basis, signals propagate through that geometry, and trainable material/coupling parameters alter the computation locally.

The architecture is designed around two equally important operations:

1. **forward transient computation**;
2. **physical/local gradient acquisition through an echo**.

The v0.1 architecture optimizes for auditability rather than maximum density.

---

## 2. Abstract machine

A TW-1 program consists of a sparse symmetric operator `Q`, input matrix `B`, a finite horizon `T`, port schedules, readout rules, and optional trainable edge parameters.

The state equation is

```text
z[n+1] = Q z[n] - z[n-1] + B u[n]
```

with

```text
Q = Q^T.
```

For an unforced eigenmode with eigenvalue `lambda(Q)`, the scalar recurrence is

```text
q[n+1] = lambda q[n] - q[n-1].
```

The ideal discrete-time stability band is

```text
-2 <= lambda(Q) <= 2.
```

The compiler uses a configurable guard margin and rejects operators too close to the boundary.

The state is second-order. TW-1 therefore stores only

```text
z[n]
z[n-1]
```

at each node.

This is enough both to advance and exactly reverse the ideal recurrence.

---

## 3. Physical organization

A chip contains one or more **Wave Mesh Tiles (WMTs)**.

A tile has:

```text
+---------------------------------------------------------+
|                    WAVE MESH TILE                       |
|                                                         |
|   P0 ---- [node]---edge---[node] ---- P1               |
|             | \             |                           |
|           edge edge         edge                        |
|             |     \         |                           |
|           [node]---edge---[node]                        |
|             |               |                           |
|          local sparse reciprocal graph                  |
|                                                         |
|  state clock | port sequencer | credit readout bus      |
+---------------------------------------------------------+
```

The physical floorplan may be regular, but the **active coupling graph need not be**. The compiler may realize irregular/arbor-like geometry by enabling only a subset of available local reciprocal links and assigning graded edge weights.

### Proposed v0.1 tile size

The architecture document uses the following logical target for costing:

```text
64 wave nodes / tile
up to 4 nearest-neighbor physical links / node
up to 128 unique reciprocal trainable edges / tile
8 configurable external ports / tile
1 shared timing sequencer / tile
1 scalar credit accumulator / trainable edge
```

These are not transistor-count claims. They are the initial compiler resource model.

---

## 4. Wave Node (WN)

Each Wave Node contains:

- `S0`: analog sample representing `z_i[n]`;
- `S1`: analog sample representing `z_i[n-1]`;
- weighted current/charge summation input from incident reciprocal edges;
- local diagonal coefficient path `q_ii`;
- optional source injection input;
- state swap/update switches;
- calibration sense path.

Logical update:

```text
next_i = q_ii * z_i[n]
       + sum_j q_ij * z_j[n]
       - z_i[n-1]
       + source_i[n]
```

followed by

```text
z_i[n-1] <- z_i[n]
z_i[n]   <- next_i
```

### Implementation family

The exact v0.1 backend assumes a clocked charge-domain or transconductance-domain realization. Candidate circuits include:

- switched-capacitor weighted summation;
- programmable transconductance cells charging state capacitors;
- differential current-mode summation followed by sample-and-hold.

The compiler does not assume a specific transistor topology. It assumes calibrated coefficients within declared bounds.

---

## 5. Reciprocal Programmable Edge (RPE)

An edge connects nodes `i` and `j` with **one shared parameter**.

Reciprocity is structural:

```text
q_ij == q_ji.
```

The edge must not contain two independently programmable directional gains in the exact backend.

Each trainable RPE exposes three logical functions:

1. **propagation coupling** `g_e`;
2. **edge-difference observation** `Delta z_e = z_i - z_j`;
3. **local scalar credit accumulator**.

The same physical parameter that affects both directions is the parameter updated by training.

### Why edge differences?

For Laplacian-like wave bodies, the derivative with respect to a bond/coupling naturally depends on the difference of the two fields across that bond. The edge therefore has a physically local gradient observable.

---

## 6. Ports

A **Wave Port (WP)** attaches to one node or a compiler-defined linear combination of a small number of boundary nodes.

Port modes:

- `DRIVE`: inject compiler-generated waveform;
- `SENSE`: record or square/integrate a readout;
- `ERROR`: inject objective derivative / adjoint source;
- `BIAS`: calibration stimulus;
- `OFF`.

A port includes a gain-envelope multiplier. This is required because the compiler may move intended damping into known temporal boundary scaling.

The v0.1 reference architecture permits digitally generated envelope coefficients. A future analog envelope generator is optional.

---

## 7. Terminal time mirror

The ideal second-order recurrence is reversed by presenting the body with the state pair in reverse order:

```text
forward terminal state:    (z[T], z[T-1])
reverse initial state:      (w[0], w[1]) = (z[T], z[T-1])
```

and executing the recurrence with the forcing schedule reversed as required.

In a clocked two-register implementation, the **minimum logical time-mirror primitive** is therefore not a full trajectory capture. It is controlled access to the two existing node state registers at the terminal boundary.

### v0.1 mirror implementation

TW-1 defines a `MIRROR_ARM` control phase that:

1. freezes the mesh clock;
2. prevents state-register overwrite;
3. switches the scheduler from forward indexing to reverse indexing;
4. selects the reverse forcing schedule;
5. optionally applies a calibrated momentum/reversal correction if the physical state representation requires it;
6. resumes mesh clocks synchronously.

For a pure sampled recurrence backend, no distributed `T`-deep memory exists and no per-node waveform recording is required.

### Continuous-wave backends

A continuous LC/microwave/photonic backend would require a physical phase-conjugation or instantaneous-time-mirror primitive. That is a separate backend and is **not** assumed solved by TW-1 v0.1.

---

## 8. Local gradient measurement unit

Each trainable edge includes a **Local Credit Cell (LCC)**.

During reverse training trials, the edge can observe two co-propagating local edge-difference components:

```text
f_e[t] = retraced forward edge field
a_e[t] = returned adjoint edge field
```

The compiler requests two phase states:

```text
PLUS:   f_e + a_e
MINUS:  f_e - a_e
```

The LCC performs square-law accumulation:

```text
A_plus  += (f_e + a_e)^2
A_minus += (f_e - a_e)^2
```

and forms

```text
credit_e = scale_e * (A_plus - A_minus) / 4.
```

For real-valued v0.1 state this is sufficient. Complex/analytic-signal backends may use I/Q state and the corresponding real overlap.

### LCC state cost

The local training memory is constant in sequence length:

```text
1-2 analog scalar accumulators per edge
```

rather than one local sample per edge per time step.

---

## 9. Parameter update plane

TW-1 separates **credit acquisition** from **parameter persistence**.

### Mode A — host update (v0.1 bring-up)

1. LCC values are digitized.
2. Host applies optimizer/projection constraints.
3. Edge DAC codes are rewritten.

This is easiest to validate and still tests the physical-gradient architecture.

### Mode B — local mixed-signal update

An edge-local update cell performs

```text
theta_e <- project(theta_e + eta * credit_e)
```

using a local DAC register, charge-domain integrator, floating-gate state, memristive device, or equivalent.

The compiler emits allowed range and optimizer gain.

Mode B is a research target, not required for the first silicon proof.

---

## 10. Forward execution protocol

For one example:

```text
RESET_STATE
LOAD_EDGE_CODES
LOAD_PORT_PROGRAM
FOR n = 0..T-1:
    APPLY source envelope/sample n
    CLOCK wave mesh once
    ACCUMULATE declared readouts
END
RETURN readout/objective observables
```

The whole mesh updates in parallel.

The logical cost of a wave step is independent of the number of active edges, provided they are physically instantiated.

---

## 11. Training execution protocol

The default no-terminal-snapshot protocol is:

```text
PASS 1: forward trajectory
        compute readout/objective
        retain only terminal live state

PASS 2: reverse PLUS echo
        retraced forward component + adjoint component
        local E+ accumulation

PASS 3: recreate forward terminal state
        required if PASS 2 consumed the terminal state

PASS 4: reverse MINUS echo
        retraced forward component - adjoint component
        local E- accumulation

UPDATE: credit_e = scale_e * (E+ - E-) / 4
```

If the terminal state can be duplicated/restored cheaply, PASS 3 becomes a state restore instead of another full traversal.

A single-run lock-in backend may reduce pass count further, but v0.1 does not require it.

---

## 12. Damping compiler

The source language may specify a uniformly damped recurrence

```text
psi[n+1] = M psi[n] - a psi[n-1] + s[n]
```

with scalar `a > 0`.

Set

```text
r = sqrt(a)
psi[n] = r^n z[n].
```

Then

```text
z[n+1] = (M/r) z[n] - z[n-1] + r^(-(n+1)) s[n].
```

The TW-1 core therefore stores

```text
Q = M/r
```

and the port sequencer absorbs the time-varying input scale.

Readout/error sources receive the corresponding compiler-generated output scale.

### Compiler implication

The physical core need not implement the intended uniform damping. The intended loss is part of the **program semantics**, represented by boundary schedules.

Residual hardware loss is a backend imperfection to calibrate, not the intended source-model damping.

---

## 13. Compiler hard failures

The exact TW-1 v0.1 backend rejects a program when any of the following is true:

### Non-scalar damping

A generic spatial damping field does not commute with an arbitrary wave operator, so one scalar boundary envelope no longer yields a fixed reversible core.

### Nonreciprocal operator

If

```text
Q != Q^T
```

then the same body is not its own transpose. A separate transpose backend or explicit reconfiguration is required.

### Stability violation

If any eigenvalue is outside the backend guard band around `[-2,2]`, the compiled recurrence is rejected.

### Boundary dynamic range violation

If compiler envelopes exceed backend source/readout gain limits, compilation fails or requires a shorter horizon / different scaling.

### Unsupported objective

v0.1 supports objectives whose derivative can be represented as scheduled port injections. Arbitrary hidden-state losses may require extra error ports or digital derivative generation.

### Routing failure

A sparse source graph that cannot be embedded in available physical links must be repartitioned or rejected.

---

## 14. Calibration model

The backend exports a calibration record containing at least:

```text
node_gain[i]
edge_gain[e]
edge_offset[e]
edge_reciprocity_error[e]
state_leak[i]
port_gain[p]
port_latency[p]
clock_skew[tile]
credit_gain[e]
credit_offset[e]
```

The compiler may incorporate stable calibration into emitted coefficients.

Some errors cannot be compiled away and instead generate warnings/spec violations:

- fast pass-to-pass operator drift;
- strongly spatially varying loss;
- time-mirror error;
- insufficient credit SNR.

---

## 15. Development-derived error targets

The following are **simulation-derived starting points**, not silicon guarantees:

```text
mean residual loss per step          ~0.005 tested
cell-to-cell loss coefficient CV     ~20% tested
loss-envelope calibration error      ~5% tested
terminal mirror amplitude error      ~5% tested
common reverse-operator mismatch     ~2% tested
local gradient readout noise         ~5% tested
+/- differential pass drift          0.2% useful; 0.5% degraded but learning survived in dev
```

The compiler should treat these as provisional characterization targets and report the estimated operating margin.

---

## 16. Multi-tile scaling

Larger sparse programs are partitioned across tiles.

Inter-tile links are explicit wave ports with one-tick or calibrated fixed latency. The compiler inserts delay states so that the program semantics include this latency.

Preferred partition objective:

```text
minimize cut edges
subject to:
    node capacity
    edge capacity
    port capacity
    latency constraints
    reciprocal routing constraints
```

A multi-tile design remains a physical recurrent graph; it is not converted into dense layer communication.

---

## 17. What counts as a TW-1 computer?

A device is a TW-1-compatible backend if it can implement the following contract:

1. sparse symmetric second-order recurrence;
2. finite-time port waveforms;
3. terminal-state reversal or equivalent echo operation;
4. causal returned error/adjoint injection;
5. local edge overlap measurement or an equivalent exact observable;
6. programmable reciprocal edge parameters;
7. backend calibration limits visible to the compiler.

Everything below that line—switched capacitors, microwave resonators, acoustic cavities, photonics—is implementation detail.

---

## 18. First chip milestone

The first meaningful silicon/demo milestone is not MNIST.

It is:

> **Compile a known damped finite-time sparse wave task into TW-1, verify forward equivalence, perform a physical four-pass echo gradient acquisition, update at least 32 reciprocal edge parameters, and show that the measured local credits improve the original source-domain objective without storing internal trajectories.**

Only after that works should larger ML benchmarks matter.