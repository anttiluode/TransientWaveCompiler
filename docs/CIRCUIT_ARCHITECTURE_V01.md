# TW-1A v0.2 Circuit Architecture

Status: **process-independent circuit proposal**. This document sits between the mathematical TW-1A backend and transistor-level/SPICE design. It fixes the physical cell topology, state/storage organization, coefficient sharing, reverse-pair timing, local credit path and calibration contract without pretending that transistor dimensions or absolute area/energy have already been earned.

The design is driven by the current hardware result: the dangerous error is not ordinary absolute fabrication mismatch. It is **differential change between physical measurements that the host later combines as one gradient**. TW-1A v0.2 therefore attacks coherence structurally.

The central choice is:

> **Do not acquire REVERSE_PLUS and REVERSE_MINUS as two long independent physical passes. Carry two reverse state contexts in lockstep and time-multiplex both through the same physical edge multiplier and the same local credit detector inside each wave tick.**

This converts the current 10-ppm-style PLUS/MINUS differential-stability problem from a whole-pass stability demand into an adjacent-subphase/common-element matching problem.

---

## 1. Tile summary

```text
TW-1A v0.2 / tw1a-sc-lockstep-v0.2

8 x 8 wave nodes                         64
four-neighbor reciprocal edge cells     112
external wave ports                       8
reverse wave contexts                     2
state generations/context                 2
local credit accumulators            <= 112

nominal coefficient paths
  reciprocal edge                         8 signed bits
  local self term                         12 signed bits
  forward drive                           8 signed bits
  returned error                         10 signed bits
  sense ADC + static PGA                   8 bits
  credit ADC                              10 bits
```

The two wave contexts are not two independent meshes. They are two state-bank contexts routed through the **same local analog compute fabric**.

```text
                         PARAM_HOLD
                             |
                             v
                    +-----------------+
 edge code SRAM --->| shared edge MDAC |<--- one code per bond
                    +--------+--------+
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
          lane A state banks      lane B state banks
           current / previous      current / previous
                 |                       |
                 +-----------+-----------+
                             |
                       same edge tap
                             |
                      same square/LCC
                             |
                      signed credit C_e
```

During inference only lane A needs to be active. Lane B and the local-credit path can be clock-gated.

---

## 2. Physical matrix decomposition

The logical recurrence remains

```text
z[n+1] = Q z[n] - z[n-1] + u[n].
```

For a routed local symmetric `Q`, define one incidence vector per physical edge

```text
b_e = e_i - e_j.
```

Then any such `Q` can be written exactly as

```text
Q = diag(d) + sum_e a_e b_e b_e^T,
```

with

```text
a_e = -Q_ij

d_i = Q_ii - sum_{e incident i} a_e.
```

This is the useful circuit form.

One physical edge cell computes a scalar edge difference

```text
Delta z_e = z_i - z_j
```

and generates one charge/current packet

```text
s_e = a_e Delta z_e.
```

That *same packet* is stamped with opposite sign into the two endpoint sums:

```text
NEXT_i += s_e
NEXT_j -= s_e.
```

The physical cell therefore realizes

```text
a_e (e_i-e_j)(e_i-e_j)^T
```

by construction. Reciprocity and the two diagonal stamps do not come from four separately programmed matrix entries.

### Hidden self-path range

The existing backend allows approximately

```text
|Q_ii| <= 1.95
|Q_ij| <= 0.25
```

and an interior grid node has degree four. Because each rank-one edge cell contributes to the diagonal, the residual local self path must cover

```text
|d_i| <= 1.95 + 4*0.25 = 2.95.
```

TW-1A v0.2 therefore specifies a **+/-3.0 local self MDAC**.

If the 8-bit signed edge path uses exact-zero mid-tread codes, its positive-side LSB is

```text
0.25 / 127 = 0.0019685...
```

A +/-3.0 self path needs **12 signed bits** for a self-path LSB no coarser than that edge LSB. This is a derived circuit choice, not an emulator-derived learning floor.

---

## 3. Wave node cell

Each node owns two wave contexts, A and B. Each context owns the current and previous second-order state.

```text
NODE i

 lane A                    lane B
+---------+               +---------+
| ZA_CUR  |               | ZB_CUR  |
| ZA_PREV |               | ZB_PREV |
+----+----+               +----+----+
     |                         |
     +------------+------------+
                  |
          local state buffer
                  |
      +-----------+-----------+
      |                       |
      v                       v
 incident edge taps       self MDAC
      |                       |
      +-----------+-----------+
                  |
           NEXT summing node
                  |
          fixed -PREV path
                  |
              state commit
```

Preferred state representation is differential:

```text
z = Vp - Vn.
```

The architecture therefore contains

```text
64 nodes * 2 contexts * 2 temporal generations
= 256 differential state registers
= 512 scalar sample-capacitor halves minimum
```

before dummy/common-mode/calibration capacitors.

### Current/previous history term

The `-z[n-1]` recurrence coefficient should be a matched unity switched-capacitor inversion path, not another general programmable weight. Its ratio is a first-class calibration observable because second-order reversibility depends on it.

### Ping-pong commit

Within a context, CUR and PREV are logical roles rather than permanently named capacitors. After computing NEXT,

```text
PREV <- CUR
CUR  <- NEXT
```

is implemented by bank-role control so no destructive read/write race occurs.

---

## 4. Reciprocal edge cell

Each of the 112 grid bonds owns one **signed, exact-zero, charge-domain rank-one coefficient cell**.

A practical first implementation is a switched-capacitor multiplying DAC:

```text
              node i buffer
                   |
                   +---- sample Delta z ----+
                   |                        |
              node j buffer                 v
                                    signed C-DAC / MDAC
                                    magnitude + polarity
                                            |
                                     transfer charge q_e
                                      /             \
                                  +q_e               -q_e
                                   |                   |
                              NEXT sum i          NEXT sum j
```

### Code semantics

Reference edge code:

```text
sign + 7-bit magnitude
magnitude zero disconnects the programmable array exactly
```

This matches the compiler's zero/off semantic better than an offset-binary DAC whose numerical zero still connects a nonzero analog element.

The magnitude array can later be segmented for matching. The v0.2 architecture does not prescribe unit-cap size or MSB segmentation yet.

### One code, one physical parameter

An edge owns one digital parameter word. It is latched into a `PARAM_HOLD` register before gradient acquisition. The host, calibration engine and background trim logic are all write-blocked until `PARAM_RELEASE`.

This means the trainable quantity is digital-state stable across the complete gradient evaluation. Remaining drift comes from the analog realization of the held ratio/reference, not from a drifting analog weight memory.

---

## 5. Shared-element two-context compute

The most important circuit choice is that lane A and lane B **do not have separate edge multipliers**.

Within one global wave tick, the same edge MDAC is used twice:

```text
PHI1  sample Delta z_A
PHI2  transfer a_e Delta z_A to lane-A node sums

PHI4  sample Delta z_B
PHI5  transfer a_e Delta z_B to lane-B node sums
```

The coefficient code, capacitor array, sign network and local reference are the same physical objects for both contexts. The lane state stores are separate; the operator element is shared.

This turns lane-to-lane coefficient mismatch into **short-term reuse error** rather than duplicated-device mismatch.

The self MDAC follows the same policy: one self coefficient path per node is time-multiplexed between the two contexts.

---

## 6. Forward mode

Forward inference uses lane A only.

One conceptual tick is:

```text
PHI0  precharge/autozero local dynamic nodes
PHI1  sample lane-A edge differences and node self states
PHI2  transfer edge/self charge into lane-A NEXT sums
PHI3  add fixed -PREV contribution and source-port charge
PHI4  settle
PHI5  commit NEXT; rotate CUR/PREV roles
```

The exact transistor clock may use more non-overlapping phases. The architectural requirement is only that all local edge operations occur without a central matrix-vector unit.

---

## 7. Terminal clone and time mirror

At the end of the forward traversal, lane A holds

```text
z[T], z[T-1].
```

Training now needs two reverse trajectories under the same operator.

### Clone

Copy both terminal state generations from lane A into lane B:

```text
B.CUR  <- A.CUR
B.PREV <- A.PREV.
```

The clone path is a calibration target. Its gain/offset error replaces much of what the older emulator called generic `mirror_error`.

### Mirror

For the discrete recurrence used by TW-1, exact reversal is a swap of the two state generations. Therefore `MIRROR_ARM` should be a **pointer/switch-role swap** in both contexts:

```text
CUR <-> PREV
```

There is no reason for the first chip to implement an analog momentum-subtraction multiplier if the compiled recurrence only requires a state swap. This removes an unnecessary analog gain-error mechanism.

---

## 8. Lockstep reverse pair

After clone + mirror,

```text
lane A receives +error injection
lane B receives -error injection.
```

Because the recurrence is linear and both lanes start from the same mirrored forward terminal state,

```text
lane A = F + A
lane B = F - A
```

where `F` is the retraced forward component and `A` is the returned adjoint/error component.

The two contexts advance once per global tick under the same held `Q`.

### Error DAC sharing

At each error port a single magnitude sample is generated. A local polarity switch routes

```text
+e[n] -> lane A
-e[n] -> lane B.
```

The compiler-wide returned-error envelope keeps the current 10-bit signed requirement for the `G=8` damping-gauge promise.

Using one DAC sample plus a sign switch makes instantaneous DAC gain/reference error primarily common-mode between PLUS and MINUS.

---

## 9. Local credit cell: subtract before digitizing

For edge `e`, reverse lanes expose

```text
x_plus  = Delta z_A = Delta F + Delta A
x_minus = Delta z_B = Delta F - Delta A.
```

The desired local overlap is

```text
credit_e = 1/4 sum_n (x_plus[n]^2 - x_minus[n]^2)
         =     sum_n Delta F[n] Delta A[n].
```

The v0.2 Local Credit Cell does **not** separately store `E_plus` and `E_minus` and ask an ADC/host to subtract two large numbers later.

Instead one physical square/charge path is reused in adjacent subphases:

```text
PHI3  Ccredit +=  +k * x_plus^2
PHI6  Ccredit +=  -k * x_minus^2
```

One differential integration capacitor therefore accumulates the signed energy difference directly.

```text
                 same squarer / charge cell
                +--------------------------+
 x_plus  ------>| + square charge          |
                |                          |----> Ccredit(+/-)
 x_minus ------>| - square charge          |
                +--------------------------+
```

The same nonlinear element, gain path and accumulator see PLUS and MINUS only a few clock subphases apart. First-order static offset and slowly varying gain therefore become common rather than independent whole-pass errors.

An explicit autozero/precharge phase is included before accumulation. Chopping the input polarity on successive gradient evaluations is an optional second-order calibration technique, not a prerequisite for the architecture.

After `GRADIENT_END`, the local signed accumulators are multiplexed to a shared **10-bit credit ADC**. Credit conversion is not on the wave critical path. The host may still normalize and apply SGD digitally.

---

## 10. Reverse-pair microphases

Reference reverse tick:

```text
PHI0  PRECHARGE / AUTOZERO
PHI1  lane A edge-difference sample
PHI2  lane A edge/self charge transfer into NEXT_A
PHI3  LCC += square(Delta z_A)
PHI4  lane B edge-difference sample
PHI5  lane B edge/self charge transfer into NEXT_B
PHI6  LCC -= square(Delta z_B)
PHI7  commit NEXT_A and NEXT_B; rotate both state-bank roles
```

The important invariant is stronger than the literal phase names:

> PLUS and MINUS use the same edge coefficient element and same credit element before either trajectory advances to the next global wave time.

---

## 11. Complete-gradient coherence window

`PARAM_HOLD` begins before the first objective forward traversal and ends only after all objective values and physical derivatives used in that optimizer update have been acquired.

For the temporal-order contrast benchmark:

```text
GRADIENT_BEGIN / PARAM_HOLD

  AB_FORWARD                 T
  AB_CLONE_MIRROR            O(1)
  AB_REVERSE_PAIR            T      (+ and - simultaneous)

  BA_FORWARD                 T
  BA_CLONE_MIRROR            O(1)
  BA_REVERSE_PAIR            T

GRADIENT_END / PARAM_RELEASE
READ_CREDIT
HOST_UPDATE
```

The old sequential +/- protocol costs approximately four T-length traversals per objective term:

```text
forward -> reverse+ -> recreate -> reverse-
```

The lockstep circuit costs two:

```text
forward -> simultaneous reverse pair.
```

For a two-term contrast objective this reduces the T-length traversal count from roughly `8T` to `4T` while also removing the long PLUS/MINUS separation.

For `T=210` at a deliberately modest 1 MHz bring-up clock, the two-term wave-traversal portion is about

```text
840 us
```

plus a few clone/mirror/control slots. This is not a maximum clock claim; it is only a useful scale for the parameter-hold window.

---

## 12. State retention target

The current inward hardware recommendation is mean leakage no worse than approximately

```text
0.001 amplitude / tick.
```

For a simple exponential sample-hold model,

```text
exp(-Ttick/tau) = 1 - 0.001.
```

At a 1 MHz bring-up clock this corresponds to roughly

```text
tau >= 0.9995 ms.
```

The previous emulator's normalized `state_noise_fraction_of_full_scale` must **not** yet be turned directly into a capacitor `kT/C` requirement. Its normalization/injection model is algorithmic and produced unrealistically tiny numerical fractions. SPICE/board work must re-identify state-noise sensitivity in volts after choosing state full-scale and settling bandwidth.

---

## 13. Port slice

Each of eight ports contains conceptually:

```text
waveform memory / stream
        |
 compiler envelope code
        |
  signed DAC path
        |
  +-----+----------------------+
  |                            |
forward drive             reverse error
8-bit useful code         10-bit useful code
                               |
                          polarity split
                         +e -> lane A
                         -e -> lane B

sense node -> sample/hold -> static binary PGA -> 8-bit SAR ADC
```

A practical implementation may simply use one 10-bit DAC per port and quantize forward schedules to the 8-bit profile in code. The architecture does not require two separate physical DACs.

The static sense PGA remains frozen for a task; it is not sample-by-sample AGC.

---

## 14. Calibration architecture

Calibration is explicit, but it is **paused during PARAM_HOLD**.

Minimum calibration observables:

1. edge coefficient: stimulate an endpoint pair and estimate `a_e`;
2. edge reciprocity: verify equal/opposite endpoint stamp from the same cell;
3. local self coefficient `d_i`;
4. history unity path `-PREV`;
5. lane-A -> lane-B terminal clone gain and offset;
6. state retention per bank/context;
7. LCC zero-input offset and square-law gain;
8. port DAC gain/offset and sign symmetry;
9. sense PGA/ADC gain and zero.

The calibration database belongs to the backend/compiler and can be used for pre-distortion and range checks. Background calibration must not modify an edge or reference in the middle of a gradient evaluation.

---

## 15. What happened to the 10-ppm requirement?

It does **not** disappear mathematically. The emulator demonstrated that independent differential operator changes inside one gradient can be damaging.

The circuit response is not:

```text
manufacture 112 analog weights whose absolute values never move by more than 10 ppm.
```

It is:

```text
store the parameter digitally;
reuse the same physical coefficient element for PLUS and MINUS;
reuse it within one wave tick;
share error magnitude generation;
subtract squared energies locally in the same analog path;
hold all parameter writes over the complete objective gradient.
```

The new residual quantity to measure is therefore **same-element adjacent-subphase differential error**, plus slower coherent change over the complete `PARAM_HOLD` window.

Those are different physical questions from independent pass drift and must be measured anew. The architecture is designed to make the hardest emulator error common-mode; it has not yet experimentally proven the resulting residual ppm value.

---

## 16. Process-independent resource count

For a fully trainable 8x8 tile:

```text
64   wave nodes
112  reciprocal edge MDAC cells
64   local self MDACs
112  local signed credit integrators
256  differential state registers
512  scalar state sample-cap halves minimum
8    source/error DAC port slices
1    or more shared/multiplexed sense ADC path(s)
1    shared credit ADC path
1    sequencer + PARAM_HOLD/interlock controller
```

This is still not an area estimate. The dominant unknowns are capacitor array size/matching, state buffer settling current, squarer implementation and routing/parasitics.

---

## 17. First circuit candidates

### State register

- fully differential sample/hold capacitor pair;
- bootstrapped or transmission-gate sampling switch;
- local unity buffer during fanout/sample phases;
- common-mode control separate from computational differential value.

### Edge MDAC

- signed switched-capacitor magnitude array;
- exact magnitude-zero disconnect;
- polarity crossbar for sign;
- sample `z_i-z_j`, then transfer equal/opposite charge to endpoint NEXT sums;
- one physical array reused across contexts A/B.

### Self MDAC

- signed switched-capacitor coefficient around +/-3.0 equivalent recurrence gain;
- 12-bit reference code to match the absolute 8-bit edge LSB criterion;
- segmentation/trim to be chosen after mismatch simulation.

### Local credit cell

Two candidates should be SPICE-compared:

1. switched-cap sampled multiplier using the same input twice (`x*x`), followed by signed charge integration;
2. differential transconductor/squarer followed by a switched sign into the credit capacitor.

The winner should be chosen on offset cancellation and input loading, not on aesthetic analog purity.

---

## 18. Circuit errors to simulate next

The next emulator/SPICE model should stop using generic independent `pass_drift` as the main circuit error and add the actual v0.2 residuals:

```text
edge MDAC settling error
edge charge-injection asymmetry
same-element A/B subphase memory error
self-MDAC settling / code mismatch
history unity-ratio error
terminal clone gain/offset
state-bank droop during the two-context tick
error-DAC sign asymmetry
LCC square-law curvature
LCC add/subtract timing mismatch
credit-cap leakage
clock feedthrough / common-mode movement
port-buffer loading of edge sample capacitors
complete-gradient coherent temperature/reference drift
```

The old generic emulator remains useful as a hostile abstraction, but these are the errors that now correspond to an actual circuit.

---

## 19. Bring-up ladder

Do not jump directly to a 64-node ASIC.

### Gate C0 — one edge cell

Two held differential voltages, one edge MDAC, two endpoint integration capacitors.

Prove:

```text
endpoint stamp is equal/opposite;
zero code is physically off;
code monotonicity;
A/B same-element reuse residual.
```

### Gate C1 — one node pair + second-order state

Implement two nodes, CUR/PREV state, unity history path and one edge. Prove forward recurrence and pointer-swap retracing.

### Gate C2 — lockstep PLUS/MINUS + LCC

Add second context and one shared squarer/credit capacitor. Prove physical

```text
1/4 sum(x_plus^2 - x_minus^2)
```

against a digitized reference over transient waveforms.

### Gate C3 — 2x2 / 4x4 tile

FPGA sequencer, real port DAC, static PGA/ADC, several trainable edges. Run the temporal-order benchmark and a shuffled-credit control.

### Gate C4 — 8x8 test ASIC

Only after C0-C3 identify realistic capacitor ratios, settling time, state full-scale and credit-cell topology.

---

## 20. What would kill this circuit architecture?

Useful negative results include:

- one shared edge cell cannot stamp sufficiently equal/opposite endpoint charge without destroying state accuracy;
- time-multiplexing A/B through one edge cell introduces memory/settling errors comparable to independent-pass drift;
- terminal clone error cannot be calibrated without a second full forward recreation;
- local same-element square/add/subtract cannot make signed credit robust enough for placement-sensitive learning;
- the state capacitors/buffers required for retention and settling make the architecture less attractive than simply storing/digitizing the trajectory.

Those are circuit kills, not story kills.

---

## 21. Compiler-visible additions

`transientwave/circuit_architecture.py` formalizes:

- exact rank-one-edge + self decomposition;
- derived +/-2.95 minimum self range;
- 12-bit self-path equal-LSB criterion for the current 8-bit edge range;
- two-context state count;
- two-traversal/objective lockstep training schedule;
- parameter-hold duration;
- leakage -> retention-time conversion;
- structural coherence invariants.

For now these are reported/tested architecture semantics. They should not become universal hard compiler rejection rules until the circuit-level emulator and first hardware measurements confirm the new residual-error model.

---

## 22. Shortest circuit description

TW-1A v0.2 is:

> **an 8x8 switched-capacitor wave mesh in which each neighbor bond is one signed rank-one charge-transfer cell, each node holds two second-order wave contexts, and PLUS/MINUS reverse trajectories are advanced in lockstep through the same coefficient hardware. A single local square/integrate path adds PLUS energy and subtracts MINUS energy before digitization, while digital parameter latches freeze the physical program over the complete gradient evaluation.**

That is the first TW-1A circuit architecture specific enough to hand to an analog designer without silently changing the computer on the way to silicon.
