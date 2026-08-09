# TransientWaveCompiler

**A compiler and mixed-signal reference architecture for finite-time dissipative wave computation on an echo-trainable physical mesh.**

TransientWaveCompiler (TWC) grows out of the GeometricNeuronPlusField experiments. The central engineering question is whether reciprocal wave dynamics, damping transforms and local echo credit can be assembled into a compiler target whose **physical body regenerates transient history instead of storing a BPTT tape**.

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
TW-1A physical mesh
    |
    +--> forward transient
    +--> terminal state clone + pointer-swap mirror
    +--> simultaneous F+A / F-A reverse pair
    +--> local signed energy difference
    `--> one scalar credit per trainable edge
```

The live-memory target is

```text
ordinary BPTT-like implementation: O(N*T) trajectory memory
TW echo implementation:            O(N) live physical state
                                   + O(E) scalar credit accumulators
```

The project is still a research architecture, not a fabricated chip.  But the hardware path is now much more concrete than the original v0.1 proposal: the reciprocal edge primitive has crossed process-independent ngspice gates, the nonlinear physical capacitor codebook has been fed back into the learner, independently mismatched codebooks have passed on every physical edge, and a circuit-native edge kT/C model has passed a fresh formal learning gate.

---

## Compiled recurrence

Each wave context advances

```text
z[n+1] = Q z[n] - z[n-1] + B u[n]
```

with sparse symmetric `Q`.

A compiler may start from a uniformly damped recurrence

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

to obtain the reversible TW recurrence exactly.  Source and readout envelopes absorb the intended uniform damping rather than requiring the physical mesh itself to reverse dissipation.

---

## Local training primitive

For trainable physical edge `(i,j)`, define returned forward and adjoint edge fields

```text
Delta w = w_i - w_j
Delta a = a_i - a_j.
```

The local overlap is recovered from two energies:

```text
E+ = sum_t |Delta w + Delta a|^2
E- = sum_t |Delta w - Delta a|^2

credit = (E+ - E-) / 4.
```

TW-1A does not store the forward trajectory.  After the terminal state is cloned and mirrored, two reverse contexts evolve under the same held physical operator:

```text
lane A = F + A
lane B = F - A.
```

A local square/integrate cell accumulates their signed energy difference.

---

# Current chip architecture: TW-1A v0.5 phase-symmetric

The original v0.2 idea reused one edge MDAC A-first/B-second inside a tick. Circuit-native failure analysis showed that this still gave B a different analog history: a 10% B-only settling loss was enough to create the remaining hard learning tail.

v0.5 removes that asymmetry **architecturally**.

Preferred shared-edge microcycle:

```text
PARAM_HOLD: edge code and measured codebook frozen

EDGE_RESET -> sample A -> fixed settle -> transfer A
EDGE_RESET -> sample B -> same settle -> transfer B
```

The second reset is essential.  It makes finite settling a **common calibrated transfer gain**, not a PLUS/MINUS coherence error.

The physical operator is decomposed as

```text
Q = diag(d) + sum_e a_e (e_i-e_j)(e_i-e_j)^T.
```

Therefore one reciprocal edge coefficient creates the complete rank-one stamp

```text
+a_e on Q_ii and Q_jj
-a_e on Q_ij and Q_ji
```

by one equal/opposite charge packet, not four separately matched matrix entries.

The residual self path must cover approximately `+/-3`, so the current node-local self actuator remains a 12-bit design problem distinct from the 8-bit edge path.

---

## Calibration-first physical contract

v0.5 assumes foreground measurement and then freezes the corrected realization for one complete physical gradient:

```text
raw mismatch
    -> measure
    -> inverse-program / trim
    -> residual
    -> PARAM_HOLD
    -> forward + simultaneous reverse gradient
```

Calibrated/trimmed primitives currently modeled:

```text
reciprocal edge transfer
node self transfer
-PREV unity history ratio
terminal A->B clone gain
fixed edge switch-charge cancellation/autozero
```

The important requirement is therefore **within-gradient coherence of the measured physical realization**, not tiny absolute fabrication mismatch everywhere.

---

# Formal emulator qualifications

All formal gates use the same temporal-order learning predicate unless stated otherwise:

```text
10/10 exact improvement >= +0.10
10/10 final exact > same-credit shuffled control
median exact improvement >= +0.30
median placement gap >= +0.25
```

Failed preregistered gates are retained in `docs/`; bodies used for a formal gate are never recycled into a later qualification.

## v0.5 phase-symmetric simultaneous corner — QUALIFIED

Untouched bodies `1500..1509`:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median DeltaC        +0.500078
median placement gap +0.546270
minimum DeltaC       +0.227308
```

The passing corner simultaneously retained:

```text
edge / self raw gain CV                 10% / 10%
edge / self calibration residual        0.1% / 0.1%
raw -PREV mismatch                      3% RMS
-PREV calibration residual              0.1%
raw terminal clone mismatch             5% RMS
clone calibration residual              0.1%
raw switch charge common/differential   3e-4 / 1e-4 state FS
charge cancellation fractional error    2%
error-DAC sign asymmetry                 10%
credit noise                             25% of credit RMS
credit offset                            1.5e-4 energy-scale fraction
credit-cap leakage                       0.01 / reverse tick
```

See `docs/CIRCUIT_V05_CORNER_RESULT.md`.

## Physical nonlinear capacitor codebook — QUALIFIED

The ideal uniform 8-bit edge ladder was replaced by the actual nominal switched-capacitor charge-sharing codebook

```text
f(m) = m*r / (1 + 2*m*r),

m = 0..127
r = Cunit/Cstate = 0.001.
```

Untouched bodies `1600..1609` still qualified 10/10:

```text
median DeltaC        +0.444847
median placement gap +0.428426
minimum DeltaC       +0.262596
```

This establishes that the compiler/controller does not require uniformly spaced analog edge levels. It can use a measured monotonic exact-zero physical codebook directly.

See `docs/CIRCUIT_V05_CAPCODEBOOK_RESULT.md`.

## 3% mismatched codebook on every physical edge — QUALIFIED

The selected edge magnitude DAC is **4-bit binary + 3-bit thermometer segmented**:

```text
lower: 1,2,4,8 unit groups
upper: seven ordered 16-unit thermometer segments
physical units per edge: 127
selectable magnitude branches: 11
```

Each of the 112 physical edge sites received its own independently fabricated 3%-sigma unit-capacitor bank and site-specific measured codebook.

Untouched bodies `1700..1709`:

```text
fabricated monotonic tiles     10/10
monotonic edge codebooks       112/112 on every tile
learning improvement >= +0.10  10/10
final exact > shuffled         10/10
median DeltaC                  +0.581887
median placement gap           +0.494918
```

See `docs/CIRCUIT_C0D_MISMATCH_RESULT.md` and `docs/CIRCUIT_V05_SEGMENTED_MISMATCH_RESULT.md`.

## Circuit-native edge kT/C — QUALIFIED

The old arbitrary independent full-node noise stress term has now been removed from the physical thermal gate.  For selected edge capacitance ratio

```text
alpha = Cedge/Cstate
b = sqrt(kT/Cstate)/VFS_state
```

one sampled edge packet injects equal/opposite endpoint noise with

```text
sigma_edge/VFS = b * sqrt(alpha)/(1 + 2*alpha).
```

At the fresh formal target

```text
b = 1e-5
```

untouched bodies `1800..1809` passed with the 3%-mismatched per-edge capacitor codebooks still present:

```text
fabricated monotonic tiles     10/10
learning improvement >= +0.10  10/10
final exact > shuffled         10/10
median DeltaC                  +0.645397
median placement gap           +0.632325
minimum DeltaC                 +0.330965
```

At 300 K the edge-thermal lower-bound relation

```text
Cstate = kT / (1e-5 * VFS_state)^2
```

gives candidate scales:

```text
VFS=0.2 V -> Cstate~1.035 nF, Cunit~1.035 pF
VFS=0.4 V -> Cstate~258.9 pF, Cunit~258.9 fF
VFS=0.6 V -> Cstate~115.1 pF, Cunit~115.1 fF
```

These are **not final silicon sizes**. They qualify only the reciprocal edge-sampling thermal contribution. Matching, parasitics, self/history-path noise and layout may set larger values.

See `docs/CIRCUIT_V05_EDGE_THERMAL_RESULT.md`.

---

# SPICE bring-up ladder

The repository now contains an executable process-independent ngspice ladder under `spice/`.

## C0a — phase-history timing — PASS

At an intentionally incomplete ~70% settled transfer:

```text
old sequential A/B mismatch     35.5117%
v0.5 reset-equalized mismatch    0.003686%
```

This reproduces the emulator diagnosis in a circuit simulator: **incomplete common settling is not the problem; unequal phase history is.**

## C0b — signed reciprocal charge packet — PASS

Real capacitor redistribution demonstrates:

```text
exact zero/off code
correct sign
monotonic magnitude
equal/opposite endpoint motion
+/- symmetry
```

## C0c — explicit 7-bit magnitude array — PASS

An explicit `1,2,4,8,16,32,64` capacitor bank checked all 128 positive magnitude codes plus mirrored negative codes:

```text
max SPICE vs analytic transfer error   0.000163%
reported endpoint common residue       0
reported sign asymmetry                0.000000%
zero-code differential leakage         ~3.46e-13 V
```

The later C0d mismatch study selected 4+3 segmentation because pure binary begins to suffer the expected `63->64` carry failures under larger unit mismatch.

See `spice/README.md` and `docs/CIRCUIT_V05_SPICE_HANDOFF.md`.

---

# What is still open

The reciprocal edge path is no longer the vaguest part of the design.  The next physical questions are node-local:

```text
1. build the two-node second-order C1 loop around CUR/PREV state banks;
2. validate the matched unity -PREV/history inversion path;
3. choose and validate a concrete +/-3 self-MDAC topology;
4. attach circuit-native thermal/switch noise to self/history/copy paths;
5. replace ideal-switch C0 devices with MOS-level switch/cap models;
6. add extracted parasitics and spatially correlated capacitor mismatch;
7. move from one-edge / two-node gates to a small recurrent tile.
```

The old question “can two independent long PLUS/MINUS analog passes remain matched?” is no longer the design target. v0.5 eliminates that requirement by construction.

---

## Compiler contract

TWC compiles a `WaveProgram` through these stages:

1. normalize a finite-time reciprocal dynamical model into a second-order recurrence;
2. factor legal uniform damping and emit boundary envelopes;
3. check stability/reversibility;
4. place graph nodes onto physical wave cells;
5. route reciprocal rank-one edge coefficients;
6. schedule forward, terminal clone/mirror, returned-error and local-credit phases;
7. emit converter/calibration/codebook requirements;
8. emit the training protocol and parameterization scales.

Strict `twc-tw1a` output carries a machine-readable `hardware_contract`. The compiler rejects programs that violate backend topology/range constraints rather than silently producing an invalid physical program.

---

## Repository map

```text
docs/
  ARCHITECTURE.md
  COMPILER_IR.md
  TRAINING_PROTOCOL.md
  HARDWARE_STATUS_2026-08-09.md
  CIRCUIT_ARCHITECTURE_V01.md       historical v0.2 circuit derivation
  CIRCUIT_V05_CORNER_RESULT.md
  CIRCUIT_V05_CAPCODEBOOK_RESULT.md
  CIRCUIT_C0D_MISMATCH_RESULT.md
  CIRCUIT_V05_SEGMENTED_MISMATCH_RESULT.md
  CIRCUIT_C0E_EDGE_THERMAL_RESULT.md
  CIRCUIT_V05_EDGE_THERMAL_RESULT.md
  CIRCUIT_V05_SPICE_HANDOFF.md

spice/
  README.md
  tw1a_v05_phase_symmetry.cir
  check_phase_symmetry.py
  check_edge_charge_cell.py
  check_binary_edge_array.py

transientwave/
  compiler.py
  backend.py
  physical.py
  hardware_contract.py
  circuit_architecture.py
  circuit_emulator.py
  circuit_emulator_v03.py
  circuit_emulator_v04.py
  circuit_emulator_v05.py
  circuit_emulator_v05_capcodebook.py
  circuit_emulator_v05_segmented_mismatch.py
  circuit_emulator_v05_edge_thermal.py
```

---

## Prior-art boundary

This repository does **not** claim invention of adjoint optimization, in-situ physical backpropagation, Hamiltonian echo learning, damping/integrating-factor transforms, physical wave computing or trainable scattering media.

The narrower research question is:

> Can a useful class of finite-time dissipative reciprocal computations be compiled into stable echo-compatible wave coordinates so that a physically local mesh regenerates transient history and exposes trainable broadband local credit without an O(N*T) stored trajectory?
