# TWC cost model v0.1

The compiler must not translate “parallel physical dynamics” into an efficiency claim without counting the hardware that makes the dynamics trainable.

This document defines the first accounting model.

## 1. Symbols

```text
N   active wave nodes
E   active propagation edges
Et  trainable edges / local credit cells
P   ports
T   transient ticks
R   physical traversals per training example
```

Reference TW-1A without terminal snapshot:

```text
R = 4
```

with terminal snapshot:

```text
R = 3 + O(N) snapshot/restore operation
```

## 2. State memory

Distributed wave state:

```text
2N analog state scalars
```

because the recurrence stores current and previous state.

Internal trajectory history:

```text
0 * N*T
```

for the echo protocol.

This does **not** mean total memory is O(N) in every system component. Output/error handling may store sensed traces:

```text
O(P*T)
```

and the host may store training data, optimizer state, or calibration tables.

The precise claim is:

> The physical gradient protocol does not require storage of the distributed internal forward trajectory `N*T`.

## 3. Local training memory

Each trainable edge stores approximately:

```text
1 signed accumulated credit scalar
```

or two unsigned phase accumulators before subtraction.

Therefore:

```text
O(Et)
```

local training state independent of `T`.

Optimizer state may add:

```text
SGD             0 extra / edge
momentum        1 extra / edge
Adam-like       2 extra / edge
```

The first chip should use host-side SGD before paying area for local optimizers.

## 4. Area units

Until a circuit/process is selected, report normalized architecture units:

```text
A_state       one differential analog state scalar
A_sum         one node weighted-sum front end
A_edge        one reciprocal programmable coupling
A_credit      one local square/integrate credit unit
A_port        one waveform/sense/error port
A_snapshot    one optional extra terminal state scalar
A_cal         calibration multiplexing overhead
```

Approximate architecture area score:

```text
A ~= 2N*A_state
   + N*A_sum
   + E*A_edge
   + Et*A_credit
   + P*A_port
   + snapshot*(2N*A_snapshot)
   + A_cal.
```

This is intentionally not converted to mm^2 before transistor-level estimates exist.

## 5. Runtime

Let one physical mesh tick take `tau_tick`.

Inference latency:

```text
L_infer ~= T * tau_tick + port/setup overhead.
```

Training gradient acquisition without snapshot:

```text
L_grad ~= 4T * tau_tick
        + objective/error preparation
        + credit read/update overhead.
```

With terminal snapshot:

```text
L_grad ~= 3T * tau_tick
        + snapshot/restore overhead.
```

The important scaling property is pass count independent of `N`, `E`, and `T`; the actual physical elapsed time still grows linearly with transient duration `T`.

## 6. Physical parallelism

All physically instantiated edges participate during one tick.

A digital sparse simulator would conventionally perform O(E) numerical interactions per tick. TW-1A performs those local interactions spatially in parallel, but pays their cost in **area and analog settling energy** instead of instruction count.

Therefore never report:

```text
"O(1) computation per time step"
```

without qualification.

The proper statement is:

> propagation work is spatially instantiated rather than time-multiplexed over a central arithmetic unit.

## 7. Energy accounting

A future measured model should separate:

```text
E_state_clock       state sample/hold switching
E_edge              local coupling/charge transfer
E_port_DAC          input/error waveform generation
E_credit            square/integrate operation
E_ADC               output and credit digitization
E_controller        digital sequencer
E_calibration       amortized calibration cost
```

Inference energy:

```text
E_infer = T * (E_state_clock + E_edge + E_port_DAC) + readout.
```

Training energy:

```text
E_train ~= R * E_infer-like traversal
         + E_credit for PLUS/MINUS
         + credit read/update
         + calibration amortization.
```

Local credit cells are not free just because they operate in parallel.

## 8. Dynamic-range cost of damping compilation

For scalar damping recurrence coefficient `a`:

```text
r = sqrt(a)
G_boundary = r^(-T).
```

The compiler reports `G_boundary`.

This can dominate practical cost even though state memory is small.

Consequences of large `G_boundary`:

- extra DAC bits / headroom;
- lower effective SNR late in a transient;
- saturation risk;
- higher source energy;
- harder calibration;
- stronger sensitivity to gain error.

The compiler should reject programs exceeding backend gain limits.

## 9. Time-mirror cost

For TW-1A sampled recurrence, reversal is a controller/state-bank operation.

For continuous-wave backends, time reversal may require expensive phase conjugation or global temporal modulation. Such a backend must include the time-mirror circuit in both area and energy totals.

A comparison that counts propagation but omits the time mirror is invalid.

## 10. Pass-drift cost

Separate PLUS/MINUS trials create a stability requirement over a gradient-acquisition window of approximately

```text
~ 4T ticks + setup.
```

Achieving sub-percent differential operator drift may require:

- thermal control;
- rapid trial interleaving;
- reference calibration tones;
- differential local accumulation;
- single-run lock-in alternatives.

Those control costs belong in the architecture budget.

## 11. Baselines

TWC should compare against at least:

### Digital sparse recurrence + BPTT

Count:

- E interactions/tick;
- N*T internal-state storage or checkpoint/recompute strategy;
- backward arithmetic;
- memory traffic.

### Digital sparse recurrence + adjoint checkpointing

Use realistic checkpoint/recompute rather than the worst possible full tape.

### Physics-aware training

Physical forward body + digital differentiable model for gradients.

This may be an especially strong practical baseline because it avoids difficult echo hardware.

### Hamiltonian/reversible digital model

If the source task can simply be reformulated as a reversible model, compare against that rather than crediting the compiler for solving a self-imposed damping problem.

## 12. Compiler resource report

Every physical manifest should eventually report:

```text
nodes
active propagation edges
trainable edges
ports
tiles
live state scalars
credit scalars
optional terminal snapshot scalars
output trace samples
traversals/inference
traversals/gradient
boundary gain max
coefficient bit targets
estimated calibration burden
```

Once transistor/PCB measurements exist, append:

```text
area
clock/tick rate
inference energy
training gradient energy
ADC/DAC energy share
calibration interval
measured pass drift
```

## 13. Efficiency claim gate

The repository should not make a speed/energy advantage claim until one complete TWC configuration is compared to one complete baseline under the **same task accuracy and training criterion**.

The architectural research can be worthwhile before that. The efficiency claim cannot.