# TransientWaveCompiler

**A compiler and reference architecture for finite-time dissipative wave computation on an echo-trainable physical mesh.**

TransientWaveCompiler (TWC) grows out of the GeometricNeuronPlusField experiments. The central engineering idea is not that physical adjoints, wave interference, Hamiltonian echo learning, or damping factorizations are individually new. They are not. The project asks whether these pieces can be assembled into a practical compiler target for **transient dissipative computation**:

```text
user dynamical program
    |
    v
finite-time damped reciprocal system
    |
    | conformal / damping-gauge compile
    v
reversible second-order wave program
    |
    v
TW-1 physical mesh
    |
    +--> forward computation
    |
    +--> terminal time mirror
    |
    +--> returned adjoint / error wave
    |
    +--> local +/- energy interference
    |
    `--> one scalar credit per tunable edge
```

The key memory goal is:

```text
ordinary BPTT-like implementation:   O(N*T) trajectory memory
TW echo implementation:              O(N) live physical state
                                     + O(E) scalar credit accumulators
```

The body regenerates the required forward history dynamically during an echo instead of reading it from a stored tape.

## TW-1 v0.1

TW-1 is the first reference chip target. It is deliberately specified as a **clocked mixed-signal reciprocal wave mesh** rather than assuming difficult photonic hardware from day one.

Each wave node contains two analog state registers representing `z[n]` and `z[n-1]`. Each reciprocal edge contains a programmable symmetric coupling. A clocked local update realizes

```text
z[n+1] = Q z[n] - z[n-1] + B u[n]
```

where `Q` is sparse and symmetric.

A compiler may start from the uniformly damped recurrence

```text
psi[n+1] = M psi[n] - a psi[n-1] + dt^2 s[n]
```

and, for scalar `a > 0`, apply

```text
r = sqrt(a)
psi[n] = r^n z[n]
Q = M / r
u[n] = dt^2 r^(-(n+1)) s[n]
```

to obtain the reversible TW-1 recurrence exactly.

Readout objectives are transformed by the same known boundary-time envelopes. The transformation moves intended uniform dissipation out of the distributed body and into compiler-generated source/readout schedules.

## Why a clocked analog mesh first?

It gives the project an exact hardware contract:

- local propagation only;
- sparse reciprocal geometry;
- physical state evolves in parallel;
- no digital matrix-vector multiply is required during a wave step;
- the exact second-order recurrence is explicit;
- time reversal can be implemented as a state operation rather than an idealized optical phase-conjugation assumption;
- the same compiler IR can later target continuous LC, microwave, acoustic, mechanical, or photonic wave bodies.

## Training primitive

For a trainable edge `(i,j)`, define local edge fields

```text
Delta w = w_i - w_j
Delta a = a_i - a_j
```

where `w` is the dynamically retraced forward field and `a` is the returned adjoint/error field.

Two local energy measurements give

```text
E+ = sum_t |Delta w + Delta a|^2
E- = sum_t |Delta w - Delta a|^2

credit = (E+ - E-) / 4
```

which is the broadband local overlap required by the edge gradient, up to the compiler-known parameterization scale/sign.

The gradient accumulation cost is independent of the transient length and does not require a local FFT or complex multiplier bank.

## Compiler contract

TWC compiles a `WaveProgram` through these stages:

1. **Normalize** a finite-time reciprocal dynamical model into a second-order recurrence.
2. **Factor damping** when legal and produce boundary gain envelopes.
3. **Check reversibility/stability** of the compiled operator.
4. **Place** graph nodes onto physical wave cells.
5. **Route** symmetric couplings onto reciprocal programmable edges.
6. **Schedule ports** for forward drive, readout/error injection, echo recreation and +/- measurements.
7. **Emit calibration requirements**: gain range, timing, residual loss tolerance and pass-drift budget.
8. **Emit a training protocol** containing local credit scale factors and update constraints.

The compiler refuses designs that violate hard backend constraints instead of silently producing an unstable body.

## Repository layout

```text
docs/
  ARCHITECTURE.md       TW-1 machine architecture
  COMPILER_IR.md        WaveProgram intermediate representation
  TRAINING_PROTOCOL.md  echo/adjoint training sequence
  HARDWARE_TILE.md      node, edge, port and local-credit circuits

transientwave/
  ir.py                 typed compiler IR
  compiler.py           damped -> reversible compilation
  cli.py                command-line compiler

examples/
  three_node.json       minimal compilable wave program

tests/
  test_compiler.py      algebra and rejection tests
```

## Prior-art boundary

This repository does **not** claim invention of:

- adjoint optimization;
- in-situ photonic backpropagation / local interference gradients;
- Hamiltonian Echo Backpropagation;
- recurrent Hamiltonian echo learning;
- integrating-factor or conformally symplectic damping transforms;
- physical wave computing;
- trainable scattering media.

The research question is narrower:

> Can a useful class of finite-time dissipative reciprocal computations be compiled into stable echo-compatible wave coordinates so that the physical body regenerates transient history and exposes trainable broadband local credit with constant-pass, local measurements?

## Status

`v0.1` is a **reference architecture and executable algebraic compiler**, not a fabricated chip. The immediate success criteria are:

- exact numerical equivalence between source program and compiled program;
- correct compiler rejection of illegal damping/nonreciprocity/stability cases;
- exact gradient reconstruction in the ideal backend;
- graceful degradation under calibrated hardware errors;
- a concrete pass/area/energy model before making speed or efficiency claims.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the machine spec.