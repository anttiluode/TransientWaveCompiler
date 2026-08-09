# TransientWaveCompiler roadmap

The roadmap is organized by **claim gates**, not feature accumulation.

## Gate 0 — exact compiler semantics

Status: started.

Required:

- continuous damped source lowering;
- discrete damped source form;
- reversible IR;
- exact damping-gauge trajectory equivalence;
- reciprocity rejection;
- stability rejection;
- boundary-gain rejection;
- trainable edge credit-scale lowering.

Current CI covers these first invariants.

Exit criterion:

> Randomized source programs within the legal class reconstruct source-domain trajectories and objectives from compiled trajectories to floating-point tolerance.

## Gate 1 — physical routing semantics

Status: started.

Reference backend:

```text
TW-1A 8x8 four-neighbor reciprocal grid
64 nodes
112 physical edges
8 ports
```

Required:

- strict physical-edge routing;
- coefficient-range checks;
- diagonal-range checks;
- port capacity;
- trainable edge mapping;
- command/microcode emission.

Next:

- node permutation / graph placement;
- routing cost metric;
- optional relay/delay nodes;
- multi-tile partitioning.

Exit criterion:

> `twc-tw1a` produces a manifest that references only physically present resources and rejects every unrepresentable logical coupling.

## Gate 2 — quantized/noisy digital twin

Build a TW-1A mixed-signal error simulator.

Damage axes:

```text
edge coefficient quantization
diagonal coefficient quantization
state sample noise
state leakage
clock gain/skew
port DAC quantization
credit cell gain/offset/noise
residual loss
pass-to-pass drift
```

Required outputs:

- source/compiled readout error;
- stability after quantization;
- echo gradient correlation;
- closed-loop learning gain;
- saturation statistics;
- effective dynamic range.

Kill criterion:

> If plausible 8-10 bit coefficient/state hardware cannot preserve useful learning, stop custom-circuit work and redesign the representation.

## Gate 3 — compiler-native echo gradient

Port the proven parent-project echo identities into TWC itself rather than relying on GeometricNeuronPlusField scripts.

Required:

- exact discrete adjoint reference;
- terminal retrace reference;
- PLUS/MINUS local energy simulator;
- local trainable edge gradients;
- numerical finite-difference audit;
- shuffled-credit control;
- four-pass closed-loop training test.

Exit criterion:

> A compiled WaveProgram trains using only observables represented in the TW-1 hardware contract, with no hidden internal trajectory readout.

## Gate 4 — randomized compiler test corpus

Generate hundreds/thousands of legal sparse programs across:

```text
damping
horizon
spectrum
source positions
readout positions
graph shapes
edge density
trainable parameter subsets
```

Measure:

- compile acceptance region;
- stability margins;
- boundary gain distribution;
- physical route success;
- gradient robustness.

This determines whether the legal class is broad enough to justify hardware.

## Gate 5 — graph placer

The direct-index grid mapping is intentionally primitive.

Implement a placer for tree/sparse graphs:

1. graph degree analysis;
2. BFS/spectral initial embedding;
3. local swaps minimizing unrouted edges and path length;
4. optional insertion of relay states;
5. re-run stability/semantic audit after transformations.

Important:

> A relay that changes delay changes the computation. Routing is part of the dynamical semantics, not merely wire layout.

Therefore every routing transform needs a compiler-visible timing proof.

## Gate 6 — board-level TW-1A prototype

Before ASIC:

- 8-16 nodes is enough;
- reciprocal programmable analog couplings;
- two-state local recurrence;
- 2 drive ports;
- 1 sense/error port;
- 4-8 local credit measurements.

Demonstrate:

```text
compiled forward equivalence
terminal echo/retrace
PLUS/MINUS gradient
shuffled-credit control
multi-step learning
```

No ML benchmark required.

Kill criterion:

> If calibration and drift control dominate operation or local credit SNR is inadequate, do not scale the tile.

## Gate 7 — TW-1A test chip

Candidate first ASIC target:

```text
32-64 nodes
~64-112 physical reciprocal edges
16-32 credit-enabled trainable edges initially
4-8 ports
host-side optimizer
full calibration mux
```

Prioritize observability over density.

The first chip should expose enough internal calibration access to determine *why* an experiment fails.

## Gate 8 — local autonomous updates

Only after physical gradient acquisition is reliable:

- local SGD accumulator;
- edge range projection;
- grouped/material-budget projection if useful;
- nonvolatile parameter storage if justified.

Autonomous learning is a separate claim from physical gradient measurement.

## Gate 9 — continuous-wave backend

Research backend TW-1C:

- LC / microwave first candidate;
- then photonic/acoustic if justified.

Need independent solutions for:

```text
continuous-time compile equivalence
time mirror / phase conjugation
residual loss compensation
local overlap detector
pass synchronization
```

Do not inherit TW-1A correctness automatically.

## Gate 10 — benchmark and efficiency study

Only after a real backend works.

Compare against:

- digital sparse recurrence;
- BPTT with checkpointing;
- reversible digital recurrence;
- physics-aware training;
- relevant physical recurrent/photonic baselines.

Count total system cost, including DAC/ADC, calibration and time-mirror overhead.

## The research fork

There are two equally valid outcomes.

### Hardware route survives

Then TWC becomes a compiler/runtime for a new physical recurrent substrate.

### Hardware route loses

Then the project still yields a precise result:

> which parts of finite-time dissipative wave learning can be converted into reversible local-credit computation, and exactly where real hardware cost removes the apparent advantage.

Both outcomes are more useful than protecting a novelty story.