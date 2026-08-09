# TW-1 control command set v0.1

TW-1 is not intended to execute arbitrary scalar instructions inside the wave mesh. The mesh executes a compiled dynamical program; a small controller sequences **phases of the physical experiment**.

The command set is therefore closer to a DMA/accelerator command stream than to a CPU ISA.

## Architectural state

```text
EDGE_CODE[e]        reciprocal propagation coefficient code
STATE0[i]           current wave state
STATE1[i]           previous wave state
PORT_MEM[p][k]      source/error schedule samples
CREDIT[e]           local scalar credit accumulator
MODE                forward / reverse-plus / reverse-minus / calibration
TICK                 current schedule index
```

Optional:

```text
TERMINAL0[i]
TERMINAL1[i]
```

for an O(N) terminal-state snapshot backend.

## Commands

### `RESET_STATE`

Zero or load compiler-declared initial `STATE0/STATE1`.

### `LOAD_STATE bank, data`

Bring-up/debug operation for loading explicit node state vectors.

### `LOAD_EDGE edge, code`

Program one reciprocal physical edge.

### `LOAD_DIAG node, code`

Program one node diagonal coefficient.

### `LOAD_PORT port, schedule`

Load/stream one forward or error schedule.

### `CREDIT_CLEAR [group]`

Reset local credit accumulators.

### `SET_MODE mode`

Modes:

```text
FORWARD
REVERSE_PLUS
REVERSE_MINUS
CALIBRATE
```

### `RUN ticks`

Execute `ticks` local wave updates using the current mode and port schedule.

This is the core compute instruction.

### `FREEZE`

Stop state updates at a deterministic boundary.

### `MIRROR_ARM`

Transition terminal state into the backend-defined reversal convention.

For TW-1A's sampled recurrence this is a controller/state-bank operation. Continuous-wave backends may map this to a physical time-mirror primitive.

### `SNAPSHOT_TERMINAL`

Optional O(N) copy of terminal state.

### `RESTORE_TERMINAL`

Restore optional terminal snapshot before another reverse phase.

### `CREDIT_PHASE sign`

Select `PLUS` or `MINUS` local edge interference accumulation.

A backend may fold this into `SET_MODE`.

### `READ_OBJECTIVE port`

Read accumulated output statistics or output samples required by the host/objective controller.

### `READ_CREDIT edge|group|all`

Digitize local accumulated parameter credits.

### `APPLY_LOCAL_UPDATE group, eta`

Optional future command for backends with local parameter-update hardware.

### `CALIBRATE kind`

Calibration classes:

```text
EDGE_GAIN
RECIPROCITY
STATE_LEAK
PORT_GAIN
CREDIT_GAIN
PASS_DRIFT
```

## Default inference command stream

```text
RESET_STATE
LOAD_PORT forward_schedule
SET_MODE FORWARD
RUN T
READ_OBJECTIVE output
```

## Default four-traversal training stream

```text
CREDIT_CLEAR

RESET_STATE
LOAD_PORT forward_schedule
SET_MODE FORWARD
RUN T
READ_OBJECTIVE output

FREEZE
LOAD_PORT plus_error_schedule
SET_MODE REVERSE_PLUS
MIRROR_ARM
RUN T

RESET_STATE
LOAD_PORT forward_schedule
SET_MODE FORWARD
RUN T

FREEZE
LOAD_PORT minus_error_schedule
SET_MODE REVERSE_MINUS
MIRROR_ARM
RUN T

READ_CREDIT all
```

Host or local update logic then changes `EDGE_CODE` values.

## Why not expose per-node arithmetic?

The design goal is to preserve the physical-computation model:

```text
programming changes geometry/ports
RUN lets the body compute
```

If the controller starts reading every node each tick and computing the next state digitally, the architecture has collapsed back into a conventional simulator.

A valid hardware backend may expose node reads for calibration/debug, but compiled normal execution must not depend on them.

## Manifest lowering

A future code-generation pass will convert the high-level training schedule already emitted by the compiler into this command stream plus binary coefficient/port memories.

The command set is intentionally stable across physical media; `MIRROR_ARM` and `RUN` are backend primitives whose implementation may differ dramatically.