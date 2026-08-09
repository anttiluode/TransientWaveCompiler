# TransientWaveCompiler

**A compiler and mixed-signal reference architecture for finite-time dissipative wave computation on an echo-trainable reciprocal mesh.**

TransientWaveCompiler (TWC) grew out of the GeometricNeuronPlusField experiments. The engineering question is deliberately narrower than “analog neural hardware”:

> Can a finite-time dissipative reciprocal computation be compiled into reversible wave coordinates so that a physical mesh regenerates transient history and exposes local trainable credit without storing an `N x T` trajectory tape?

The project is a research architecture, **not a fabricated chip**. The repository now contains a compiler, circuit-native emulators, preregistered learning gates, process-independent ngspice bring-up tests and assumption-explicit area/timing budgets.

---

## Current architecture: TW-1A v0.8

The current fresh-qualified architecture is **v0.8 common/difference active summing**.

```text
source dynamical program
        |
        v
scalar damping / conformal compile
        |
        v
z[n+1] = Q z[n] - z[n-1] + u[n]
        |
        v
8 x 8 TW-1A reciprocal mesh
        |
        +-- forward common field C
        |
        +-- structural time mirror / structural -PREV
        |
        +-- returned difference/adjoint field D
        |
        `-- local edge sensor forms DeltaC +/- DeltaD
                                  |
                                  v
                         signed square difference
                                  |
                                  v
                         one credit / trainable edge
```

The live-memory target remains

```text
stored-trajectory implementation: O(N*T) state tape
TW echo implementation:            O(N) live physical state
                                  + O(E) scalar credit accumulators
```

### Four precision-heavy operations already removed structurally or rejected

The branch has repeatedly used failed circuit/learning gates to simplify the architecture instead of merely tightening tolerances:

1. **`-PREV` multiply/trim deleted.** The coefficient `-1` is a state-bank orientation/role invariant.
2. **Terminal 64-node analog clone deleted.** Reverse coordinates are common/difference rather than stored `F+A` / `F-A` trajectories.
3. **Matched `+error/-error` pair deleted.** One signed error waveform drives the D lane.
4. **Passive NEXT charge sharing rejected.** C1b showed it is a first-order lag, not an additive accumulator; node updates use active virtual charge summing.

The current reverse representation is

```text
C = F
D = A
```

and only the local credit sensor reconstructs

```text
Delta_plus  = DeltaC + DeltaD
Delta_minus = DeltaC - DeltaD

credit = 1/4 * sum_t(Delta_plus^2 - Delta_minus^2)
       = sum_t DeltaF * DeltaA.
```

No full internal trajectory is stored.

---

## Physical operator

The sparse symmetric recurrence operator is lowered as

```text
Q = diag(d) + sum_e a_e b_e b_e^T,
b_e = e_i - e_j.
```

For physical edge `(i,j)`:

```text
a_e = -Q_ij
d_i = Q_ii - sum_(e incident i) a_e.
```

One reciprocal edge capacitor bank therefore produces the complete equal/opposite rank-one stamp. Four independently matched matrix entries are not required.

Current edge target:

```text
8 x 8 nodes                         64
four-neighbor physical edges       112
edge magnitude units / site        127
selection                           4-bit binary + 3-bit thermometer
nominal positive edge range        0.265
compiler-required range            0.250
unit-cap mismatch model            3% RMS
site-common Cunit/Cstate model     1% RMS
exact zero code                    yes
```

A measured monotonic physical codebook is part of the compiler/hardware contract; uniformly spaced analog levels are not required.

---

## Strongest fresh emulator qualification

Fresh bodies **2300..2309** passed with both reciprocal-edge and node-local self sampling thermal noise enabled.

```text
edge thermal base                         1e-5
self thermal base                         1e-5
edge nominal range                        0.265
unit-cap mismatch                         3% RMS
site-common ratio mismatch                1% RMS
foreground kick-cancellation error        0.5% RMS
residual kick floor                       2 ppm common / 1 ppm differential
training iterations                       30
step size                                 0.20

fabrication                               10/10
improvement >= +0.10                      10/10
final exact > same-credit shuffled        10/10
median DeltaC                             +0.396735
minimum DeltaC                            +0.150625
median placement gap                      +0.310108
```

See `docs/CIRCUIT_V08_SELF_THERMAL_FRESH_RESULT.md` and `docs/HARDWARE_STATUS_V08_2026-08-09.md`.

### Switch-kick target came from a real failure

A failed fresh body localized the remaining v0.8 tail to foreground cancellation accuracy, not the irreducible switch floor. The working target is

```text
kick-cancellation measurement error <= 0.5% RMS
common residual floor               <= 2e-6 state FS RMS
differential residual floor         <= 1e-6 state FS RMS
```

Tightening the floor alone did not rescue the failed body; improving cancellation measurement did.

---

## C1 circuit ladder

The process-independent ngspice ladder is under `spice/`.

```text
C1b passive precharged-destination addition     REJECTED
     state-dependent additivity error            ~50.000077%

C1c active virtual-sum charge integration       PASS
     nominal packet                              25.600 mV
     packet state-dependence                     numerical floor

C1d finite DC gain                              PASS / budgeted

C1e monolithic |self|=3, 20 ns                  REJECTED
     even 1 GHz misses frozen 0.1% packet marker

C1e2 two self slices                            PASS
     300 MHz, Cin/Cf=1.5 per slice

C1e3 one half-range self bank reused twice      PASS
     20 ns transfer
     10 ns reset/resample
     20 ns transfer
     ~0.099% total packet magnitude error
```

The current v0.8 self implementation therefore uses one reusable `|self|<=1.5` bank twice instead of one monolithic `|self|<=3` packet.

---

## Thermal result: the self sampler is the present wall

The current active-integrator edge sampling law is

```text
sigma_edge / VFS = b_edge * sqrt(alpha),
alpha = Cedge/Cstate.
```

The two-slice reusable self path has

```text
sigma_self / VFS = b_self * sqrt(|d|).
```

A controlled path split on the spent fresh bodies `2300..2309` found:

```text
edge=1e-5, self=1e-5     clean 10/10
edge=2e-5, self=1e-5     clean 10/10
edge=3e-5, self=1e-5     9/10   -> fail

edge=1e-5, self=2e-5     5/10   -> fail
edge=1e-5, self=3e-5     2/10   -> fail
```

So reciprocal edge sampling is **not** the first thermal bottleneck. Node-local self sampling is. See `docs/CIRCUIT_V08_THERMAL_PATH_SPLIT_RESULT.md`.

---

## Area model

The executable area model is assumption-explicit, not a foundry claim.

Current v0.8 known provisioned capacitor subtotal:

```text
state banks       256.00 Cstate
edge banks         29.68 Cstate
self banks         96.00 Cstate
-------------------------------
known subtotal    381.68 Cstate
```

This excludes OTA area/energy, credit detector/integrator, switches, dummy/calibration caps, reference distribution, control, clocks, routing and guard structures.

Scalar thermal sizing:

```text
Cstate >= kT / (b * VFS)^2.
```

With deliberately illustrative `1 fF/um^2` MIM and `2.5 um^2/SRAM bit` assumptions:

```text
b=1e-5, VFS=1 V    known caps ~15.81 mm^2    tape crossover ~12,351 ticks
b=3e-5, VFS=1 V    known caps ~ 1.76 mm^2    but this thermal point fails
b=3e-5, VFS=2 V    known caps ~ 0.44 mm^2    but this thermal point fails
```

The combined edge+self outward sweep showed that even `2e-5` is not a passing common-noise point under v0.8. See `docs/CIRCUIT_V08_COMBINED_THERMAL_SWEEP_RESULT.md`.

---

# v0.9 probe: remove the inertial +2 from the programmable self path

**v0.9 is not qualified. It is the current architectural experiment.**

For the compiled continuous-wave source class,

```text
Q = [(1+a)I - dt^2 H] / sqrt(a).
```

The local self term is dominated by the universal second-order inertial baseline. Define

```text
p[n] = z[n] - z[n-1]
K = Q - 2I.
```

Then exactly

```text
p[n+1] = p[n] + K z[n] + u[n]
z[n+1] = z[n] + p[n+1].
```

Unit tests verify one-step, 100-step and inverse equivalence, and subtracting `2I` leaves every edge/rank-one derivative unchanged.

On all spent `2300..2309` benchmark bodies:

```text
old active-node programmable self |d|     1.993759520
kick residual |d-2|                       0.006240480
magnitude reduction                       319.49x
sampled-self noise-amplitude reduction     17.87x
```

The first v0.9 circuit abstraction therefore keeps the proven v0.8 state/echo representation but splits

```text
d_i = fixed_measured_inertial_gain_i + programmable_residual_i.
```

Static fixed-path mismatch is measured and absorbed by the residual code. Dynamic noise of the fixed near-2 path is **explicitly swept**; it is not assumed free.

Provisional residual-self range:

```text
+/-0.125, 10 signed bits
```

which would reduce the self capacitor provision from `96 Cstate` to `8 Cstate` if a practical fixed inertial circuit earns the required noise/area/energy point.

See `transientwave/kick_drift.py`, `docs/CIRCUIT_V09_KICK_SELF_AUDIT_RESULT.md` and `docs/CIRCUIT_V09_INERTIAL_BASELINE_PREREG.md`.

---

## Compiler path

The compiler currently:

1. accepts a narrow reciprocal finite-time dynamical program;
2. lowers supported continuous damped waves to a second-order recurrence;
3. applies the scalar damping/conformal gauge;
4. checks reversibility/stability;
5. routes sparse symmetric couplings onto the 8x8 physical mesh;
6. emits reciprocal rank-one edge semantics and converter/calibration requirements;
7. emits objective/error schedules and hardware contract metadata.

For uniform source damping,

```text
a = 1 - dt*gamma
r = sqrt(a)
psi[n] = r^n z[n]
Q = M/r
```

so intended uniform dissipation is moved into source/readout envelopes rather than requiring the physical echo to reverse loss.

The compiler remains conservative: unsupported topology/range/reciprocity is rejected rather than silently approximated.

---

## Repository map

```text
transientwave/
  compiler.py
  physical.py
  backend.py
  circuit_architecture.py
  active_summing_budget.py
  circuit_emulator_v08_common_diff.py
  circuit_emulator_v08_self_thermal.py
  circuit_emulator_v09_inertial_baseline.py
  kick_drift.py

spice/
  README.md
  check_c1b_passive_additivity.py
  check_c1c_virtual_sum.py
  check_c1d_finite_gain.py
  check_c1e_finite_bandwidth.py
  check_c1e2_self_slicing.py
  check_c1e3_self_reuse.py

docs/
  HARDWARE_STATUS_V08_2026-08-09.md
  CIRCUIT_V08_SELF_THERMAL_FRESH_RESULT.md
  CIRCUIT_V08_COMBINED_THERMAL_SWEEP_RESULT.md
  CIRCUIT_V08_THERMAL_PATH_SPLIT_RESULT.md
  CIRCUIT_V09_KICK_SELF_AUDIT_RESULT.md
  COST_MODEL.md
```

Failed preregistered gates are intentionally retained. They have repeatedly been more useful than a smooth success narrative because they identified which physical assumption should be deleted or redesigned.

---

## Prior-art boundary

This repository does **not** claim invention of adjoint optimization, in-situ physical backpropagation, Hamiltonian echo learning, integrating-factor/damping transforms, physical wave computing or trainable scattering media.

The narrower research question remains:

> Can useful finite-time dissipative reciprocal computations be compiled into stable echo-compatible wave coordinates so that a physically local mesh regenerates transient history and exposes broadband local credit without an `O(N*T)` stored trajectory?
