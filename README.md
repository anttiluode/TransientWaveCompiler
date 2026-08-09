# TransientWaveCompiler

**A compiler/tuning toolkit for sparse reciprocal wave systems, plus a mixed-signal research architecture for transient-wave computation.**

TransientWaveCompiler (TWC) grew out of the GeometricNeuronPlusField experiments. The repository now contains **two related but experimentally distinct projects**:

1. **TWC compiler / reciprocal-system tuner** — compile, analyze and optimize sparse symmetric wave/filter operators on an ordinary computer.
2. **TW-1A mixed-signal research backend** — explore whether a reciprocal switched-cap wave body can regenerate transient history and expose physical training credit without an `O(N*T)` stored trajectory tape.

The second project produced real circuit simplifications and ngspice results, but its attractive small-cap stochastic on-device gradient point is **not qualified** after controlled task × fabrication × dynamic-noise experiments. The first project is now the stronger application mainline.

For the detailed hardware audit, start with:

> **[`docs/HARDWARE_STATUS_2026-08-09.md`](docs/HARDWARE_STATUS_2026-08-09.md)**

---

## Current headline: the compiler has escaped the toy benchmark

The classical coupled-resonator filter formalism is built from the same kind of object TWC already understands well:

```text
sparse reciprocal symmetric matrix
+ prescribed graph topology
+ local matrix parameters
+ measurable response
+ exact edge/knob derivatives
```

TWC now includes a separate, explicit coupling-matrix application layer rather than pretending microwave normalization and the TW transient recurrence are literally the same equation.

### Published three-resonator filter — 5/5 exact recovery

For the published target

```text
M = [[0,   .6, .2],
     [.6,  0,  .6],
     [.2, .6,  0 ]],
```

an exact inverse-matrix gradient was checked against central finite differences and then used to tune five deliberately detuned matrices.

Result:

```text
5/5 response pass
5/5 exact coupling recovery
worst coupling-vector RMSE ~1.14e-4
```

See:

- `transientwave/coupled_resonator_filter.py`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_PREREG.md`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_RESULT.md`

### Resonator offsets + couplings — 5/5 exact six-knob recovery

The same published target was then made into a more realistic matrix-level tuning problem:

```text
[d1, d2, d3, m12, m23, m13]
```

All three resonator self-detuning terms and all three couplings start wrong.

Result:

```text
5/5 response pass
5/5 six-knob recovery pass
5/5 exact six-knob recovery
worst overall parameter RMSE  0.009734
worst detuning RMSE           0.013222
worst coupling RMSE           0.003832
```

See:

- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_PREREG.md`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_RESULT.md`

### Generalized source–resonator–load matrices

The repository now also contains the proper explicit-port formulation

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)
```

with audited exact gradients for arbitrary reciprocal matrix knobs:

- `transientwave/generalized_coupling_matrix.py`
- `tests/test_generalized_coupling_matrix.py`

The current benchmark target is a published fourth-order cross-coupled tunable filter containing both resonator cross-coupling and direct source-load coupling, i.e. a topology designed around multiple transmission zeros.

---

## Why the filter application is a natural TWC target

The transient compiler and a classical coupling-matrix tuner are not identical physical models. What they share is the structural core:

```text
parameterized sparse symmetric operator
        |
        +-- reciprocal local edge stamps
        +-- topology constraints
        +-- exact local matrix derivative
        +-- forward response
        `-- inverse / adjoint sensitivity
```

For an explicit matrix parameter `p`, the filter layer uses

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

A diagonal resonator tuning knob is a one-entry stamp. A reciprocal coupling is a symmetric two-entry stamp. The same compiler-side sparse-parameter machinery can therefore reason about both without hand-differentiating a whole filter.

The practical next layers are measurement noise, actuator calibration, constrained topology, and larger published/real filters — not a fabrication run.

---

# TW-1A hardware research

## Original question

The hardware project asks whether a finite-time dissipative reciprocal computation can be lowered to wave coordinates so that a physical mesh regenerates enough transient history to train locally without storing the full trajectory:

```text
stored trajectory: O(N*T)
physical echo:      O(N) live wave state + O(E) credit state
```

The compiled deterministic recurrence is of the form

```text
z[n+1] = Q z[n] - z[n-1] + u[n]
```

with a sparse symmetric physical operator

```text
Q = diag(d) + sum_e a_e b_e b_e^T,
b_e = e_i - e_j.
```

Each reciprocal edge is therefore one rank-one equal/opposite physical stamp rather than four independently matched matrix entries.

## Structural circuit progress that survived

The circuit branch repeatedly used failed gates to delete fragile operations:

1. **Analog `-PREV` multiplier/trim deleted.** The `-1` history coefficient is structural through state-bank orientation.
2. **Terminal analog clone deleted.** Reverse state moved to common/difference coordinates.
3. **Matched positive/negative error DACs deleted.** One signed error waveform is enough.
4. **Passive NEXT charge sharing rejected in ngspice.** It is state dependent; active virtual summing replaced it.
5. **Monolithic `|self|=3` transfer rejected.** Two reusable half-range transfers satisfy the timing abstraction.
6. **Kick-drift `(Z,P)` coordinates passed deterministic algebra and ngspice C1f shear tests.**

The process-independent circuit ladder lives under `spice/`.

## The important negative result

The later v0.9 kick-drift rewrite made the known capacitor subtotal look dramatically better at a nominal common thermal base `b=2e-5`. That operating point did **not** survive a properly factored stochastic harness.

Once task, fabricated silicon and dynamic noise were separated:

```text
fixed strongly learnable task 2400
5 fabrication seeds
5 dynamic seeds
formal b=2e-5 point

DeltaC >= +0.10    1/25
exact > shuffled  16/25
```

A source factorial on fixed task/fabrication 2400 showed:

```text
thermal off                  median DeltaC +0.687113
self thermal only            median DeltaC +0.149811
edge thermal only            median DeltaC +0.019995
drift thermal only           median DeltaC -0.014737
all three                    median DeltaC +0.028717
```

The static/quantized fabricated body is therefore not the main failure. Sampled dynamic noise is.

## Easy rescues were tested and rejected

### Make the capacitors bigger

A uniform thermal backoff swept all three sampled thermal bases together. Only `b=0` met the frozen robustness criterion. Even `b=2.5e-6` failed — despite implying 64× the capacitance of the attractive `b=2e-5` point.

**Capacitor-only rescue rejected.**

### Average more physical adjoints

Complete physical gradients averaged per optimizer update:

```text
N=1    median DeltaC +0.028717
N=4    median DeltaC -0.006610
N=16   median DeltaC +0.080290
N=64   median DeltaC +0.095307
```

Still not robust at 64× acquisition cost.

### Forward-only perturbation

The forward objective itself is highly trainable when dynamic thermal sampling is removed:

```text
clean SPSA median DeltaC          +0.446339
clean 64-row Hadamard DeltaC      +0.839012
```

At `b=2e-5`, however:

```text
thermal SPSA              3/15 above +0.10
64-row thermal Hadamard    2/5 above +0.10
```

The Hadamard estimator uses 256 forward traversals per optimizer update and still misses the frozen margin.

## What the fixed-theta microscope says

At one fixed theta, averaging **1024** noisy physical gradients still gives median:

```text
cosine to clean gradient        0.280
projection onto clean gradient  0.191
relative vector error           1.048
relative trace standard error   0.521
```

So the small-cap physical gradient is not merely a mildly noisy unbiased vector. It has extreme variance and evidence of a bias component. A likely physical reason is that the reverse pass receives new thermal packets rather than the stochastic history that perturbed the particular forward trajectory it is supposed to adjoint.

This does not invalidate deterministic echo mathematics. It limits the present **stochastic physical implementation** of that echo.

---

## Current project split

### TWC compiler / tuner — mainline

Good current targets:

- classical coupled-resonator filter synthesis/tuning;
- measured resonator detuning and coupling correction;
- mechanical/acoustic/metamaterial reciprocal systems;
- any sparse symmetric linear wave model with a useful measured response and constrained topology.

### TW-1A — research backend

Worth preserving:

- structural recurrence transformations;
- reciprocal rank-one edge lowering;
- active-summing switched-cap topology;
- ngspice rejection/pass ladder;
- kick-drift representation;
- hardware-aware codebooks and calibration semantics;
- controlled negative stochastic-learning results.

Not currently supported:

> **a claim that the `b=2e-5` small-cap TW-1A is an economical general on-device gradient-learning accelerator.**

A future chip path would need a genuinely different physical estimator or a use case that does not require fast in-situ stochastic gradient recovery.

---

## Repository map

```text
transientwave/
  compiler.py
  physical.py
  backend.py

  # circuit research
  circuit_emulator_v08_common_diff.py
  circuit_emulator_v09_partitioned_rng.py
  circuit_emulator_v09_kick_drift.py
  kick_drift.py

  # filter / reciprocal-system application layer
  coupled_resonator_filter.py
  generalized_coupling_matrix.py

experiments/
  v09_*.py
  v10_*.py
  published_coupled_filter_v01.py
  published_coupled_filter_v02.py
  published_cross_coupled_filter_v03.py

spice/
  check_c1b_passive_additivity.py
  check_c1c_virtual_sum.py
  check_c1d_finite_gain.py
  check_c1e_finite_bandwidth.py
  check_c1e2_self_slicing.py
  check_c1e3_self_reuse.py
  check_c1f_kick_drift_shear.py

docs/
  HARDWARE_STATUS_2026-08-09.md
  BENCHMARK_V09_*_RESULT.md
  BENCHMARK_V10_*_RESULT.md
  BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_RESULT.md
  BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_RESULT.md
```

Failed preregistered gates are intentionally retained. In this repository they are part of the design record, not clutter: most of the useful architecture came from identifying which assumption should be deleted rather than tightening every tolerance.

---

## Prior-art boundary

This repository does **not** claim invention of adjoint optimization, in-situ physical backpropagation, Hamiltonian echo learning, integrating-factor damping transforms, physical wave computing, trainable scattering media, or classical microwave coupling-matrix synthesis.

The narrower contribution being explored is the compiler/engineering combination:

> **Represent trainable reciprocal systems as constrained sparse symmetric operators, lower them into physically meaningful local parameters, preserve exact sensitivity structure, and make the assumptions/failure boundaries explicit enough that the same compiler can target both simulated tuning problems and future physical backends.**
