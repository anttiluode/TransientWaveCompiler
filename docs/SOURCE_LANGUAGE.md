# WaveProgram source language v0.1

WaveProgram describes **finite-time reciprocal wave computations**. The source language is intentionally closer to a physical dynamical system than to a neural-network layer graph.

## Continuous source form

The preferred high-level v0.1 form is

```text
x_ddot + gamma x_dot + H x = B u(t)
```

with:

- scalar `gamma >= 0`;
- symmetric `H`;
- finite horizon `steps`;
- explicit sample interval `dt`;
- sparse input/sense ports;
- optional trainable stiffness-like edges.

JSON:

```json
{
  "dynamics": {
    "form": "continuous_damped_wave",
    "gamma": 0.2,
    "integration": "semi_implicit_euler",
    "H": [[80,-20,0],[-20,80,-20],[0,-20,80]]
  }
}
```

The v0.1 compiler defines the source program's discrete semantics using semi-implicit Euler:

```text
v[n+1] = (1-dt*gamma) v[n] - dt H x[n] + dt source[n]
x[n+1] = x[n] + dt v[n+1]
```

Eliminating velocity gives

```text
a = 1-dt*gamma
M = (1+a) I - dt^2 H

x[n+1] = M x[n] - a x[n-1] + dt^2 source[n].
```

The compiler then applies the exact scalar damping gauge to this **declared discrete program**.

This distinction matters: TWC v0.1 does not claim exact integration of the underlying continuous ODE. It claims exact equivalence between the declared discrete source semantics and the compiled TW recurrence.

## Discrete damped source form

Expert users may supply the recurrence directly:

```text
x[n+1] = M x[n] - a x[n-1] + source[n]
```

with

```json
{
  "dynamics": {
    "form": "damped_second_order",
    "a": 0.99,
    "M": [[...]]
  }
}
```

This bypasses the ODE discretization pass.

## Already-reversible source form

A program may target the reversible IR directly:

```text
z[n+1] = Q z[n] - z[n-1] + source[n]
```

using

```json
{
  "dynamics": {
    "form": "reversible_second_order",
    "Q": [[...]]
  }
}
```

No damping gauge is then applied.

## Timing semantics

WaveProgram uses one explicit convention:

```text
source waveform sample k
    -> drives transition state k to state k+1

sense/objective sample k
    -> observes state k+1
```

This makes compiler-generated damping envelopes auditable.

For scalar damping gauge `r=sqrt(a)`:

```text
input recurrence sample k gets factor r^(-(k+1))
source state x[k+1] = r^(k+1) z[k+1]
quadratic readout weight gets factor r^(2(k+1)).
```

## Trainable edge semantics

A local trainable edge is not an arbitrary matrix cell.

Define

```text
b_e = e_i - e_j.
```

### In discrete recurrence space

```json
{
  "i": 0,
  "j": 1,
  "matrix_scale": -0.05,
  "min": 0,
  "max": 0.1
}
```

means

```text
dM/dtheta_e = matrix_scale * b_e b_e^T.
```

### In continuous stiffness space

```json
{
  "i": 0,
  "j": 1,
  "stiffness_scale": 1.0,
  "min": 0,
  "max": 40
}
```

means

```text
dH/dtheta_e = stiffness_scale * b_e b_e^T.
```

Since

```text
M = (1+a)I - dt^2 H,
```

the compiler derives

```text
dM/dtheta_e = -dt^2 stiffness_scale * b_e b_e^T
```

and then

```text
dQ/dtheta_e = (1/r) dM/dtheta_e.
```

This is why the local hardware observable is an edge-difference product.

## Ports

A port may attach to one node:

```json
{"name":"input","kind":"drive","node":0,"waveform":[1,0,0]}
```

or to a small sparse linear combination:

```json
{
  "name":"readout",
  "kind":"sense",
  "sparse_weights":[[10,0.5],[11,0.5]]
}
```

The physical backend may reject a sparse port combination it cannot realize locally.

## Objectives

Executable v0.1 supports:

```text
quadratic_energy
weighted_quadratic_energy
```

The compiler emits the derivative multipliers needed by the error port.

The architecture documentation also discusses contrast objectives used in the parent research, but the executable compiler should not claim support until they are implemented and tested.

## Exact compile conditions

The exact scalar-gauge backend requires:

```text
0 < a <= 1
M = M^T
```

or, for continuous input,

```text
gamma >= 0
H = H^T
0 < 1-dt*gamma <= 1.
```

The compiled

```text
Q = M / sqrt(a)
```

must also lie inside the configured discrete stability band.

## Physical compile conditions

`twc` checks mathematical compilation.

`twc-tw1a` additionally checks the strict first-chip resource model:

```text
8x8 nodes
four-neighbor reciprocal fabric
112 physical edges
8 ports
provisional coefficient ranges
```

Thus these can differ:

```text
WaveProgram is mathematically compilable     YES
WaveProgram physically routes on TW-1A       NO
```

That distinction is intentional.
