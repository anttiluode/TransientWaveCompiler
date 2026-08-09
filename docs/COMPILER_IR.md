# WaveProgram IR v0.1

## 1. Goal

WaveProgram is the machine-independent input to TransientWaveCompiler.

It describes a **finite-time sparse reciprocal dynamical computation** without committing to a transistor, resonator, acoustic cavity, or photonic implementation.

The IR is intentionally small. If a feature cannot be represented clearly, v0.1 should reject it rather than hide it in backend-specific magic.

---

## 2. Source model

The canonical source form is

```text
psi[n+1] = M psi[n] - A psi[n-1] + B s[n]
```

where:

- `psi` is an `N`-vector of real state variables;
- `M` is sparse;
- `A` is either a scalar multiple of identity in the exact damping-gauge backend or an explicitly supplied matrix for future backends;
- `B` maps input ports to state nodes;
- `s[n]` is the input waveform vector.

The v0.1 exact compiler requires

```text
A = a I
0 < a <= 1
M = M^T
```

for the damping-gauge path.

A program may instead be declared already reversible:

```text
z[n+1] = Q z[n] - z[n-1] + B u[n]
Q = Q^T.
```

---

## 3. JSON schema by example

```json
{
  "name": "three_node_demo",
  "version": 1,
  "dt": 0.05,
  "steps": 64,
  "state": {
    "nodes": 3,
    "initial": [0.0, 0.0, 0.0],
    "initial_previous": [0.0, 0.0, 0.0]
  },
  "dynamics": {
    "form": "damped_second_order",
    "a": 0.99,
    "M": [
      [1.90, 0.04, 0.00],
      [0.04, 1.88, 0.03],
      [0.00, 0.03, 1.91]
    ]
  },
  "ports": [
    {
      "name": "input",
      "node": 0,
      "kind": "drive",
      "waveform": [0.0, 1.0, 0.0]
    },
    {
      "name": "output",
      "node": 2,
      "kind": "sense"
    }
  ],
  "objective": {
    "kind": "quadratic_energy",
    "port": "output",
    "weight": 1.0
  },
  "trainable_edges": [
    {"i": 0, "j": 1, "min": 0.00, "max": 0.10},
    {"i": 1, "j": 2, "min": 0.00, "max": 0.10}
  ],
  "constraints": {
    "stability_margin": 0.001,
    "max_boundary_gain": 8.0,
    "require_reciprocal": true
  }
}
```

Waveforms shorter than `steps` are zero-padded by the front end. Longer waveforms are rejected unless explicit truncation is requested.

---

## 4. Core objects

### `Program`

```text
name
version
dt
steps
state
dynamics
ports
objective
trainable_edges
constraints
metadata
```

### `StateSpec`

```text
nodes: integer > 0
initial: length-N vector
initial_previous: length-N vector
```

### `DynamicsSpec`

Supported v0.1 forms:

#### `damped_second_order`

```text
a: scalar
M: NxN matrix
```

Semantics:

```text
psi[n+1] = M psi[n] - a psi[n-1] + source[n]
```

#### `reversible_second_order`

```text
Q: NxN matrix
```

Semantics:

```text
z[n+1] = Q z[n] - z[n-1] + source[n]
```

---

## 5. Ports

Every port has:

```text
name
node | sparse_weights
kind
waveform (for drives)
gain_limit (optional)
```

Supported kinds:

```text
drive
sense
error
calibration
```

A port normally attaches to one node. `sparse_weights` permits a small compiler-visible linear combination when the backend supports it.

The compiler lowers all external interaction into an explicit `PortSchedule`.

---

## 6. Objectives

### `quadratic_energy`

```text
J = weight * sum_n y[n]^2
```

The compiler knows the derivative waveform and can generate the transformed error-port schedule.

### `weighted_quadratic_energy`

```text
J = sum_n weight[n] * y[n]^2
```

### `contrast_energy`

For two executions `target` and `distractor`:

```text
C = (E_target - E_distractor) / (E_target + E_distractor + epsilon)
```

This corresponds closely to the development task used in GeometricNeuronPlusField. The front end lowers it into two executions and two adjoint/error schedules.

### Future objectives

Cross-entropy, learned digital heads, multi-port vector losses, and hidden-state penalties can be added if their derivatives can be lowered to explicit error-port injections.

---

## 7. Trainable parameters

v0.1 exposes trainable **reciprocal edges**.

```json
{
  "i": 4,
  "j": 5,
  "min": 0.0,
  "max": 0.12,
  "scale": 1.0,
  "group": "arbor"
}
```

The compiler checks:

- `i != j`;
- edge exists in the sparse operator or backend permits insertion;
- reciprocal entries are tied;
- requested range is realizable;
- local gradient scale can be derived.

Future IR versions may add node restoring terms, port couplings, resonant frequencies, and nonlinear local parameters.

---

## 8. Compiler constraints

```text
stability_margin
max_boundary_gain
max_operator_asymmetry
max_nodes
max_edges
max_ports
require_reciprocal
allow_partition
```

Constraints are part of program semantics because a compile that silently clips them is not equivalent to the requested dynamical system.

---

## 9. Lowered reversible IR

After legal damping factorization, the front end emits `ReversibleProgram`:

```text
N
T
Q
z0
z_previous
compiled_ports
objective_schedule
trainable_edges
edge_gradient_scales
gauge_record
stability_report
resource_report
```

### `GaugeRecord`

```text
source_form: damped_second_order
scalar_a
r = sqrt(a)
input_envelope[n] = r^(-(n+1))
state_to_source_scale[n] = r^n
readout_envelope[n] = r^n or objective-specific derivative scale
max_input_gain
min_output_scale
```

The record is emitted even if later stages quantize the operator, because it is needed to audit semantic equivalence.

---

## 10. Hardware IR

The backend lowers `ReversibleProgram` to `TW1Manifest`:

```text
backend: "tw1-clocked-mixed-signal"
clock_period
node_map
edge_map
coefficient_codes
port_program
mirror_program
training_program
calibration_requirements
warnings
```

The hardware manifest contains **codes and schedules**, not mathematical matrices wherever possible.

Example edge record:

```json
{
  "logical_edge": [1, 2],
  "tile": 0,
  "physical_edge": 17,
  "q": 0.03125,
  "dac_code": 411,
  "trainable": true,
  "credit_scale": -0.0025
}
```

---

## 11. Compiler passes

```text
parse
  -> shape_check
  -> reciprocity_analysis
  -> damping_analysis
  -> conformal_lowering
  -> objective_lowering
  -> stability_analysis
  -> sparse_graph_extraction
  -> tile_partition
  -> placement
  -> reciprocal_route
  -> coefficient_quantization
  -> post_quantization_stability
  -> port_schedule_generation
  -> echo_schedule_generation
  -> resource_and_gain_audit
  -> emit_manifest
```

Every pass can attach diagnostics.

---

## 12. Refusal philosophy

A TransientWaveCompiler error should say **why the physical semantics cannot be guaranteed**.

Examples:

```text
E102 NONSCALAR_DAMPING
The exact TW-1 damping-gauge backend requires A=aI. Observed diagonal range
0.984..0.997 and nonzero damping/operator commutator. Use an approximate backend
or rewrite the model.
```

```text
E211 STABILITY_MARGIN
Compiled Q has max eigenvalue 2.0041, exceeding allowed +1.9990.
```

```text
E305 BOUNDARY_GAIN
Required input envelope reaches 23.8x while backend limit is 8x.
Shorten the horizon, reduce intended damping, or select another backend.
```

A physically invalid program must not become a plausible-looking netlist.