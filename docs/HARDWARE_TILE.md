# TW-1 Hardware Tile v0.1

## 1. Two backend families

TransientWaveCompiler separates the **wave-computer semantics** from the medium used to realize them.

### TW-1A — clocked analog / mixed-signal

Status: **reference correctness backend**.

Implements the exact discrete recurrence using analog state storage and local weighted interactions synchronized by a clock.

Advantages:

- exact correspondence to compiler recurrence;
- terminal reversal is explicit and testable;
- coefficient calibration is straightforward;
- mature CMOS building blocks;
- easiest path to a first physical gradient demo.

### TW-1C — continuous wave body

Status: **future research backend**.

Potential media:

- LC / RF transmission-line mesh;
- microwave resonators;
- integrated photonics;
- acoustic/mechanical network.

Advantages:

- propagation is intrinsically continuous and massively parallel;
- potentially higher bandwidth and lower per-step control overhead.

Harder requirements:

- phase conjugation / time mirror;
- residual dissipation model;
- continuous-time compiler equivalence;
- local overlap detector implementation.

TW-1A comes first because it tests the computer architecture without conflating it with unsolved time-mirror device physics.

---

# 2. TW-1A Wave Mesh Tile

## Logical resources

Initial costing target:

```text
64 Wave Nodes (WN)
128 Reciprocal Programmable Edges (RPE) maximum
8 Wave Ports (WP)
128 Local Credit Cells (LCC) maximum
1 tile sequencer
1 calibration ADC path
1 credit readout/update bus
```

The physical grid may expose more fixed neighbor links than a program uses.

---

## 3. Differential state encoding

The preferred first implementation uses differential analog state:

```text
z = V+ - V-
```

for common-mode rejection and natural representation of signed wave states.

Each state register consists conceptually of two sample capacitors or equivalent analog memories.

Per node:

```text
current state      Z0+/Z0-
previous state     Z1+/Z1-
```

After a wave tick:

```text
Z1 <- Z0
Z0 <- NEXT
```

The two physical state generations can be implemented as ping-pong banks to avoid destructive read-before-write hazards.

---

## 4. Local wave update circuit

Each node computes

```text
NEXT_i = q_ii Z0_i
       + sum_j q_ij Z0_j
       - Z1_i
       + PORT_i.
```

### Candidate circuit strategy

A practical first design can use a two-phase switched-capacitor MAC local to each node:

#### PHI_A — sample / distribute

- sample current node states;
- connect calibrated edge capacitors/transconductors to neighbor states;
- sample source port contribution.

#### PHI_B — sum / commit

- charge-share or integrate weighted contributions;
- include fixed `-Z1` feedback path;
- sample result into next-state bank;
- rotate state-bank roles.

This is an **analog local stencil**, not a central digital matrix-vector multiply.

---

## 5. Reciprocal edge circuit

One physical control code must determine both directions of an edge.

Preferred structures:

```text
shared programmable capacitor
shared differential transconductance bridge
shared multiplying DAC controlling paired symmetric gm elements
```

The design rule is more important than the circuit choice:

> There is one calibrated parameter object for edge `(i,j)`, not independent `i->j` and `j->i` weights.

That makes reciprocity hardware-enforced rather than a software promise.

---

## 6. Edge-difference tap

For a trainable edge, the LCC needs

```text
Delta z = z_i - z_j.
```

With differential state encoding this can be obtained by a local differential amplifier or charge-domain subtractor placed at the edge.

No global node-state bus is required for gradient acquisition.

The compiler may choose only a subset of physical edges as trainable, reducing LCC area.

---

## 7. PLUS/MINUS field composition

The reverse protocol conceptually contains two components:

```text
retraced forward edge field F
returned error/adjoint edge field A.
```

A local selector forms

```text
PLUS  = F + A
MINUS = F - A.
```

There are two implementation strategies.

### Strategy 1 — field superposition in the mesh

Inject the error field with phase/sign `+1` or `-1` so the physical edge signal itself is the sum/difference.

This is closest to an in-situ interference measurement.

### Strategy 2 — dual observation paths

Observe `F` and `A` separately and combine them in a local analog LCC.

This is less physically pure but may be easier on TW-1A.

The compiler manifest records which strategy a backend supports.

---

## 8. Square-law Local Credit Cell

For real differential signals the LCC requires a quantity proportional to `x^2`.

Candidate circuits:

- translinear / Gilbert-cell squarer;
- MOS square-law region demonstrator;
- full-wave precision rectifier followed by quadratic transconductor;
- sampled multiplication `x*x` in switched-capacitor domain.

The result charges an integration capacitor:

```text
Ccredit dV/dt ~ x^2.
```

Two modes accumulate `E_plus` and `E_minus`.

### Minimal storage

Option A:

```text
C+ accumulator
C- accumulator
```

Option B:

one accumulator reused sequentially:

```text
accumulate +E_plus
then accumulate -E_minus
```

which directly leaves a signed overlap proportional to the desired credit.

Option B is attractive if leakage/offset can be controlled.

---

## 9. Credit conversion and update

### Bring-up mode

- multiplex LCC capacitor voltage to ADC;
- host rescales by compiler credit coefficient;
- host computes edge code update;
- edge DAC is rewritten.

This keeps the physical test honest: the **gradient is acquired physically**, while optimizer bookkeeping is digital.

### Autonomous mode

Later local update circuit:

```text
Vtheta <- Vtheta - eta * Vcredit
```

with rail clamps / projection.

A persistent nonvolatile analog element is optional, not fundamental to the architecture.

---

## 10. Port circuit

A v0.1 port consists of:

```text
waveform SRAM / streaming input
DAC
programmable envelope multiplier
node injection switch
sense buffer
optional square/integrate readout
ADC path
```

The envelope multiplier realizes compiler schedules such as

```text
r^(-(n+1))
```

for a damped source program.

For a fixed compiled model the envelope can be pretabulated as DAC codes.

No exponential analog circuit is required.

---

## 11. Error injection controller

For a quadratic objective the controller stores or streams only the **output trace**, not internal states.

It forms

```text
error[k] = compiler_multiplier[k] * measured_output[k].
```

The output trace memory is `O(P*T)` for `P` sensed ports. This is not hidden internal trajectory memory and is normally much smaller than `O(N*T)`.

If even output trace storage is undesirable, an objective-specific streaming/echo schedule may be developed later.

---

## 12. Terminal-state handling

### No-snapshot baseline

The existing two state banks are the terminal state. Reverse PLUS consumes them. The forward computation is rerun before reverse MINUS.

No extra distributed memory is required.

### O(N) terminal snapshot option

A third sample bank per node can copy the terminal state pair, reducing one full forward recreation pass.

Trade:

```text
+ roughly one extra analog state bank
- one complete physical traversal per gradient
```

This should be decided from measured area/energy rather than ideology.

---

## 13. Clocking and synchronization

The architecture is sensitive to phase/timing, so the chip uses a low-skew tile clock.

Minimum global phases:

```text
RESET
FORWARD
MIRROR_ARM
REVERSE_PLUS
RECREATE
REVERSE_MINUS
CREDIT_READ/UPDATE
CALIBRATE
```

Within a mesh tick, non-overlapping analog phases avoid charge corruption.

Inter-tile operation requires deterministic latency and compiler-inserted delay states.

---

## 14. Calibration hardware

The first chip should spend area on calibration rather than pretending mismatch is absent.

Required observability:

- drive one port/node with calibration waveform;
- sense selected node response;
- measure each programmable edge's effective coefficient;
- estimate reciprocity mismatch;
- estimate state leakage per node;
- estimate credit-cell gain/offset;
- estimate pass-to-pass drift over training timescale.

The resulting calibration file is consumed by the compiler backend.

---

## 15. Quantization target

Initial suggestion, to be verified by simulation:

```text
edge coefficient DAC:      8-10 effective bits
port waveform DAC:          10-12 effective bits
state analog SNR:           >= 40 dB initial target
credit accumulator ADC:     10-12 effective bits
```

These are design hypotheses, not derived requirements.

A proper quantization sweep belongs in the compiler simulator before transistor design.

---

## 16. Area accounting unit

The compiler cost model should report normalized units instead of fake square micrometers until a process/circuit is selected:

```text
WN_STATE      two differential analog state banks
WN_SUM        local weighted summer
RPE_COUPLING  one reciprocal programmable edge
LCC           one square/integrate credit cell
WP            one source/sense/error port
SNAPSHOT      optional terminal state bank
```

This enables architecture comparisons before layout.

---

# 17. TW-1C continuous backend sketch

A future continuous implementation would compile toward something like

```text
C x_ddot + D x_dot + K(theta) x = B u(t)
```

or a first-order complex wave/scattering equivalent.

The backend must supply:

- reciprocal physical propagation;
- a legal damping/conformal mapping or alternate adjoint method;
- a real time-reversal / phase-conjugation operation;
- local parameter-sensitive field observable;
- integrated interference detector.

Potential implementations include tunable LC meshes and integrated photonic resonator networks.

The compiler should share the high-level IR but use a separate numerical equivalence proof and stability/calibration model.

---

## 18. Geometric-neuron inheritance

TW-1 borrows the following design instincts from the Geometric Neuron work:

- geometry is computational state, not decoration;
- simple local detectors can read consequences of globally complicated propagation;
- graded coupling material is a useful trainable coordinate;
- forward and returned fields can make local causal sensitivity observable;
- the same body can be both compute substrate and credit-routing substrate when reciprocity holds.

It does **not** require a claim that biological neurons implement this architecture.

---

## 19. First board before first ASIC

Before custom silicon, the architecture should be emulated by a small board or FPGA-controlled switched-capacitor / analog array if practical.

A sensible staged path is:

```text
Python exact backend
  -> quantized/noisy mixed-signal simulator
  -> discrete analog breadboard / PCB tile
  -> small test ASIC
  -> multi-tile chip
  -> continuous-wave backend research
```

The compiler should remain the same conceptual front end across that path.