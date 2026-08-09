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

Strict `twc-tw1a` output now also carries a machine-readable `hardware_contract` block. The current physical semantics are **one reciprocal rank-one edge cell / one programmable coefficient / one local credit accumulator**, with an exact zero/off code. The block distinguishes per-program converter spans from the architecture-wide damping-gauge promise and records the current mixed-signal evidence without turning benchmark results into hard universal compile errors.

## Current mixed-signal result

The first fully preregistered simultaneous noisy operating point has now passed on ten untouched irregular temporal-order tasks using the corrected rank-one edge-cell emulator:

```text
Q / drive DAC / sense ADC     8 / 8 / 8
mean leakage per tick          0.0005
leakage CV                     0.50
mirror gain error              15%
PLUS/MINUS differential drift  10 ppm RMS
zero-mean local credit noise   25%
local credit DC offset         0.015%
state noise                    5e-9 of full scale RMS/tick
```

All 10/10 learners improved by at least +0.10 normalized temporal-order contrast and all 10/10 beat a norm-matched shuffled-credit control.

The important caveat is that the 10-ppm number is a **within-gradient differential-stability** result, not necessarily an absolute fabrication-accuracy limit. Experiments in which one drifting reciprocal Q is held coherent across the complete physical gradient evaluation are far more tolerant of absolute Q variation, but an absolute coherent-drift boundary is not yet confirmed.

See [`docs/HARDWARE_STATUS_2026-08-09.md`](docs/HARDWARE_STATUS_2026-08-09.md) for the current evidence map and exact caveats.

## Circuit architecture: TW-1A v0.2 lockstep reverse

The first circuit-level answer to that coherence problem is now specified in [`docs/CIRCUIT_ARCHITECTURE_V01.md`](docs/CIRCUIT_ARCHITECTURE_V01.md).

Rather than running PLUS and MINUS as two long independent reverse passes and requiring the analog mesh to remain nearly identical between them, TW-1A v0.2 carries **two reverse state contexts** but routes both through the **same physical edge MDAC and the same local square/integrate credit path inside each wave tick**:

```text
forward lane A
    |
terminal clone -> lane B
    |
pointer-swap mirror both lanes
    |
    +--> lane A: F + A --+
    |                    | same held edge MDAC
    +--> lane B: F - A --+ reused in adjacent subphases
                         |
                         v
                same local square/LCC
             +square(PLUS), -square(MINUS)
                         |
                    signed credit
```

The design also makes the physical `Q` representation explicit:

```text
Q = diag(d) + sum_e a_e (e_i-e_j)(e_i-e_j)^T.
```

That decomposition exposed a previously hidden circuit requirement. With the backend's `|Q_ii|<=1.95`, `|Q_ij|<=0.25` and grid degree four, the local self path must cover at least **+/-2.95** after the rank-one edge diagonal stamps are included. The reference circuit therefore uses a **+/-3.0, 12-bit self MDAC** so its absolute LSB is no coarser than the current 8-bit edge path.

The lockstep design reduces the T-length training cost from roughly four traversals per objective term (`forward -> reverse+ -> recreate -> reverse-`) to two (`forward -> simultaneous reverse pair`) and converts the most dangerous PLUS/MINUS drift into a same-element adjacent-subphase residual that can now be measured directly.

See [`docs/CIRCUIT_BRINGUP_V01.md`](docs/CIRCUIT_BRINGUP_V01.md) for the edge-cell, second-order recurrence, terminal-clone, local-credit and small-tile kill gates.

## Repository layout

```text
docs/
  ARCHITECTURE.md                 TW-1 machine architecture
  COMPILER_IR.md                  WaveProgram intermediate representation
  TRAINING_PROTOCOL.md            echo/adjoint training sequence
  HARDWARE_TILE.md                node, edge, port and local-credit concepts
  HARDWARE_STATUS_2026-08-09.md   current mixed-signal evidence and limits
  CIRCUIT_ARCHITECTURE_V01.md     TW-1A v0.2 switched-cap/lockstep circuit
  CIRCUIT_BRINGUP_V01.md          circuit bring-up and kill gates

backends/
  tw1a_circuit_v0.json            machine-readable circuit profile

transientwave/
  ir.py                           typed compiler IR
  compiler.py                     damped -> reversible compilation
  backend.py                      strict 8x8 TW-1A physical backend
  physical.py                     TW-1A lowering/routing + hardware contract
  hardware_contract.py            dynamic-range and hardware-profile report
  circuit_architecture.py         rank-one circuit decomposition/resources/timing
  emulator_v05.py                 rank-one edge-cell mixed-signal emulator
  cli.py                          command-line compiler

examples/
  three_node.json                 minimal compilable wave program

tests/
  test_compiler.py                algebra and rejection tests
  test_hardware_contract.py       converter-budget and contract tests
  test_emulator_v05.py            rank-one edge-cell hardware semantics
  test_circuit_architecture.py    circuit decomposition/coherence invariants
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

`v0.1` is a **reference architecture and executable algebraic compiler**, not a fabricated chip. The compiler algebra, strict 8x8 backend, microcode, rank-one mixed-signal emulator, temporal-order credit benchmark, hardware-contract reporting and process-independent v0.2 circuit architecture are executable or machine-readable and covered by tests where appropriate.

The next hardware question is now concrete: **does same-element lockstep A/B reuse actually collapse differential operator/credit error enough once edge-settling, charge injection, terminal-clone error, history-ratio error, LCC curvature and clock feedthrough are modeled as circuits rather than generic pass noise?**

See [`docs/CIRCUIT_ARCHITECTURE_V01.md`](docs/CIRCUIT_ARCHITECTURE_V01.md), [`docs/CIRCUIT_BRINGUP_V01.md`](docs/CIRCUIT_BRINGUP_V01.md), and [`docs/HARDWARE_STATUS_2026-08-09.md`](docs/HARDWARE_STATUS_2026-08-09.md) for the current hardware path.