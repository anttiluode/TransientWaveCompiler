# TW-1A hardware status — v0.8 common/difference active summing

Date: 2026-08-09

This is the current evidence map for the circuit branch. It supersedes the old
v0.2/v0.5-facing status narrative without deleting that history.

## Current working architecture

```text
forward lane C
  two physical state banks / structural -PREV role inversion
  active virtual charge summing at each node
  measured reciprocal capacitor edge codebooks

terminal boundary
  C <- mirrored forward terminal state already present
  D <- exact zero state
  inject one signed error waveform into D

reverse
  C = retraced forward field F
  D = returned adjoint/error field A

local edge credit sensor
  delta_plus  = delta_C + delta_D
  delta_minus = delta_C - delta_D
  credit += [square(delta_plus)-square(delta_minus)]/4
```

The key architectural removals accumulated through the branch are:

1. `-PREV` analog multiplier/trim -> **deleted**; coefficient -1 is structural.
2. terminal 64-node analog clone -> **deleted** by common/difference coordinates.
3. matched `+error/-error` injection pair -> **deleted**; one signed error drives D.
4. passive NEXT charge sharing -> **rejected**; active virtual charge summing is required.

## Fresh emulator-qualified point — PASS

Fresh bodies **2300--2309** passed with both edge and self sampling thermal noise
present.

```text
reverse coordinates                         common/difference
edge nominal positive full scale             0.265
edge unit-cap mismatch                        3% RMS
site-common Cunit/Cstate mismatch             1% RMS
edge thermal base                             b_edge = 1e-5
self thermal base                             b_self = 1e-5
kick cancellation measurement error           0.5% RMS
common residual kick floor                    2 ppm state FS RMS
differential residual kick floor              1 ppm state FS RMS
training iterations                           30
step size                                     0.20

fabrication pass                              10/10
improvement >= +0.10                          10/10
exact final > shuffled                        10/10
median improvement                            +0.396735
minimum improvement                           +0.150625
median placement gap                          +0.310108
minimum placement gap                         +0.189134
minimum observed edge full scale               0.257965
```

This is an **emulator-level** qualification. It is not a transistor/foundry
qualification.

## Edge coefficient hardware

Working physical representation:

```text
one reciprocal edge / one measured capacitor codebook
127 unit capacitors per edge
4-bit binary + 3-bit thermometer selection
exact zero/off code
nominal positive physical range 0.265
compiler-required positive range 0.250
```

Fabrication model currently qualified together with learning:

```text
3% RMS independent unit-cap mismatch
1% RMS site-common Cunit/Cstate mismatch
```

A separate 20,000-tile headroom Monte Carlo showed why 0.255 nominal range was
abandoned: common site-ratio error dominates full-scale yield after unit errors
average down. 0.265 is the current inward layout target, not a universal foundry
number.

## Switch-kick contract

The failed fresh 2100--2109 gate was localized to post-cancellation switch-kick
residual on one hard body. Same-silicon mechanism splitting showed:

- reducing only the independent 2 ppm / 1 ppm floor does **not** rescue it;
- improving foreground cancellation measurement does;
- 1% cancellation error is a passing cliff point;
- **0.5% RMS cancellation measurement error** is the working inward target.

Keep the residual floors at

```text
common       <= 2e-6 state FS RMS
differential <= 1e-6 state FS RMS.
```

Do not spend circuit complexity tightening those floors without new evidence.

## C1 active-integrator ladder

### C1b — passive NEXT accumulation — REJECTED

A sampled edge capacitor directly charge-sharing with a precharged state gives
about **50% state-dependent packet error** in the frozen test. Passive sharing
is not an accumulator.

### C1c — virtual-sum active accumulation — PASS

The same packet into a virtual summing node is state independent to numerical
precision in the ideal-gain deck and obeys the direct `Cs/Cf` packet law.

### C1d — finite DC gain — PASS

First frozen A0 points meeting the 0.1% packet marker:

```text
edge load Cin/Cf=0.265     A0 ~ 3,000
unsliced self Cin/Cf=3     A0 ~ 30,000
```

A0=100,000 remains a conservative working value for later nonideal studies, not
an emulator-derived absolute accuracy requirement.

### C1e — monolithic self bandwidth — REJECTED

At 20 ns aperture, a monolithic `Cin/Cf=3` self packet misses the 0.1% marker
even at 1 GHz. The edge packet passes at 100 MHz.

### C1e2/C1e3 — two-slice reusable self bank — PASS

Working first-order timing:

```text
one reusable self bank with max Cin/Cf = 1.5
A0 = 1e5
GBW = 300 MHz
TRANSFER1 = 20 ns
RESET/RESAMPLE = 10 ns
TRANSFER2 = 20 ns
plus non-overlap (~52 ns total in the deck)
```

The 10 ns reset point gives about 0.099% total packet magnitude error and 0.023%
state-dependent mismatch. A 5 ns reset fails.

Two equal self slices have total ideal sampling-noise law

```text
sigma_self/VFS = b * sqrt(|self coefficient|),
```

which is now included in the fresh-qualified emulator point.

## Fixed node-integrator gain calibration

For a fixed measured positive node packet-gain field `D=diag(d_i)`, the compiler
can preserve a symmetric physical operator using

```text
Q_phys = D^(-1/2) Q_logical D^(-1/2)
u_phys = D^(-1/2) u_logical
z      = D^(1/2) x.
```

The identity is covered by tests. Therefore fixed absolute node gain is primarily
a calibration/range issue; **drift, lane dependence, signal/code dependence and
nonlinear gain are not removed by this transform.**

## Edge scheduling / feedback factor

The 8x8 nearest-neighbor mesh has a deterministic four-phase matching schedule:

```text
H0  32 edges
H1  24 edges
V0  32 edges
V1  24 edges
```

No node participates in more than one edge transfer within a phase. This makes
edge-phase input loading deterministic rather than degree/activity dependent.
At edge full scale 0.265 the ideal capacitive feedback factor is

```text
beta_edge = 1/(1+0.265) ~= 0.7905.
```

The two-slice self path has the more demanding instantaneous

```text
beta_self = 1/(1+1.5) = 0.4.
```

## Thermal / area economics

Known provisioned capacitor count in the current architecture, expressed as a
multiple of `Cstate`:

```text
state banks     256 * Cstate
edge banks      112 * 0.265 * Cstate = 29.68 * Cstate
self banks       64 * 1.5   * Cstate = 96.00 * Cstate
-----------------------------------------------
known subtotal                     = 381.68 * Cstate
```

This excludes OTA, credit-integrator/square-sensor, dummy/calibration caps,
switches, reference buffers, control storage, clocks, routing and guard rings.

The scalar thermal sizing law is

```text
Cstate >= kT / (b * VFS)^2.
```

Therefore the area case is extremely sensitive to the tolerable thermal base and
the effective differential voltage convention. With illustrative 1 fF/um^2 MIM
and 2.5 um^2/bit SRAM assumptions:

```text
b=1e-5, VFS=1 V: known capacitors ~15.81 mm^2, tape crossover ~12,351 ticks
b=3e-5, VFS=1 V: known capacitors ~ 1.76 mm^2, tape crossover ~ 1,372 ticks
b=3e-5, VFS=2 V: known capacitors ~ 0.44 mm^2, tape crossover ~   343 ticks
```

These are **illustrative assumptions, not process estimates**. The next thermal
budget experiment is deliberately aimed at this economic axis.

## Current live question

A diagnostic on spent 2300--2309 bodies is sweeping edge and self thermal bases
together at

```text
1e-5, 2e-5, 3e-5, 5e-5.
```

If the body tolerates a larger common thermal base, the kT/C capacitor subtotal
falls quadratically. That is currently a more consequential question than
further increasing edge/self code precision.

## Important remaining circuit gates

1. **Foreground kick calibration circuit** that actually demonstrates <=0.5%
   residual measurement/cancellation error.
2. **Physical self codebook/segmentation** for the reusable ±1.5-per-slice bank.
3. **Read-only credit sensor frontend** producing `DeltaC+DeltaD` and
   `DeltaC-DeltaD` without disturbing stored C/D states.
4. **OTA realism**: slew, output swing, common mode, transistor noise, PVT,
   power and stability at the C1e3 timing/load point.
5. **Area/energy layout model** including active circuits and clock/reference
   distribution, not only capacitor area.

The branch should continue to preserve failed gates rather than retune them away.
The v0.7 and first v0.8 fresh failures were both productive because their tails
identified architectural simplifications rather than merely tighter tolerances.
