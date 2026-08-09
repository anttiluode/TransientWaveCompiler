# TW-1A hardware status — v0.8 qualified / v0.9 probes

Date: 2026-08-09

This is the current evidence map for the circuit branch. Historical failures are
kept because several of them directly produced architectural simplifications.

## Current qualified body: v0.8 common/difference active summing

```text
forward C context
  two physical state vectors
  structural -PREV role/orientation
  active virtual charge summing at each node
  measured reciprocal capacitor edge codebooks

terminal boundary
  mirror the forward state by current/previous role swap
  D starts at exact zero
  inject one signed error waveform into D

reverse
  C = returned forward field F
  D = returned adjoint/error field A

local edge credit
  delta_plus  = delta_C + delta_D
  delta_minus = delta_C - delta_D
  credit += [square(delta_plus)-square(delta_minus)]/4
```

Architectural removals already earned:

1. `-PREV` analog multiplier/trim -> **deleted**; coefficient -1 is structural.
2. terminal 64-node analog clone -> **deleted** by common/difference coordinates.
3. matched `+error/-error` injection -> **deleted**; one signed error drives D.
4. passive NEXT charge sharing -> **rejected**; active virtual charge summing is required.

## Strongest fresh emulator gate — PASS

Fresh bodies **2300--2309** passed with both reciprocal edge and local self
sampling kT/C present.

```text
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

fabrication                                   10/10
improvement >= +0.10                          10/10
exact final > shuffled                        10/10
median improvement                            +0.396735
minimum improvement                           +0.150625
median placement gap                          +0.310108
minimum placement gap                         +0.189134
minimum observed edge full scale               0.257965
```

This is an emulator qualification, not transistor/foundry qualification.

## Reciprocal edge implementation

```text
8 x 8 nodes                         64
four-neighbor edges                 112
127 physical magnitude units/edge
4-bit binary + 3-bit thermometer selection
exact zero/off code
nominal positive physical range     0.265
compiler-required range             0.250
```

The compiler/controller uses measured monotonic site-specific codebooks; it does
not require uniformly spaced analog levels.

## Switch-kick contract

The failed fresh 2100--2109 gate localized one hard body to post-cancellation
switch kick. Controlled same-silicon splitting showed the useful target is
foreground cancellation measurement, not an unrealistically tiny raw switch:

```text
foreground cancellation measurement error   <=0.5% RMS
common residual floor                        <=2e-6 state FS RMS
differential residual floor                  <=1e-6 state FS RMS
```

Reducing the residual floor by itself did not rescue the hard body.

---

# C1 process-independent circuit ladder

## C1b — passive NEXT accumulation — REJECTED

Direct passive charge sharing with an already charged destination gives about
**50.000077%** state-dependent additivity error in the frozen deck.

## C1c — virtual-sum active accumulation — PASS

The same sampled charge transferred into an active virtual summing node gives a
state-independent 25.600 mV packet to numerical precision in the ideal-gain
deck.

## C1d — finite DC gain — PASS / budgeted

Representative first points clearing the frozen 0.1% packet marker:

```text
edge Cin/Cf=0.265      A0 ~3,000
old self Cin/Cf=3      A0 ~30,000
```

`A0=1e5` is therefore conservative, not a sacred absolute-accuracy requirement.
Fixed positive node gain can also be compiler-calibrated by the tested diagonal
similarity transform; drift/nonlinearity/context dependence remain real errors.

## C1e — monolithic |self|=3 timing — REJECTED

At a 20 ns transfer aperture the full self packet misses the 0.1% marker even at
1 GHz. This is a load/topology failure, not a reason to require a multi-GHz OTA.

## C1e2/C1e3 — two-slice reusable self bank — PASS

```text
one reusable self bank, max Cin/Cf=1.5
GBW = 300 MHz in first-order deck
TRANSFER1 = 20 ns
RESET/RESAMPLE = 10 ns
TRANSFER2 = 20 ns
~52 ns total including non-overlap
```

The 10 ns reset case gives about 0.099% packet magnitude error and 0.023%
state-dependent mismatch. Five ns reset fails.

---

# Thermal boundary: self sampling, not edge sampling

The active-summing edge law used by the qualified emulator is

```text
sigma_edge/VFS = b_edge * sqrt(Cedge/Cstate).
```

For the two-slice reusable self bank,

```text
sigma_self/VFS = b_self * sqrt(|d|).
```

## Combined outward sweep — FAIL beyond 1e-5

Spent fresh-qualified bodies 2300--2309:

```text
edge=self=1e-5   10/10 >=+0.10, 10/10 wins, median +0.396735   PASS
edge=self=2e-5    5/10 >=+0.10, 10/10 wins, median +0.100997   FAIL
edge=self=3e-5    2/10 >=+0.10,  8/10 wins                     FAIL
edge=self=5e-5    1/10 >=+0.10,  6/10 wins                     FAIL
```

The `2e-5` point is informative: exact credit still beats shuffled on every
body, but update amplitude/SNR is too weak under the frozen one-echo protocol.

## Edge/self path split — self is the bottleneck

```text
edge=2e-5, self=1e-5   10/10 >=+0.10, 10/10 wins,
                       median DeltaC +0.364810, gap +0.268236   PASS

edge=3e-5, self=1e-5    9/10 >=+0.10                           FAIL

edge=1e-5, self=2e-5    5/10 >=+0.10, 10/10 wins,
                       median DeltaC +0.100568                  FAIL
```

The present sampled-cap kT/C wall is therefore **node-local self sampling**.
Uniformly paying the same capacitance penalty to the reciprocal edge path is
not supported by the evidence.

---

# Area model at the qualified v0.8 topology

Known provisioned capacitor subtotal:

```text
state banks     256.00 Cstate
edge banks       29.68 Cstate
self banks       96.00 Cstate
-------------------------------
known subtotal  381.68 Cstate
```

Excluded: OTA, square/credit integrator, dummy/calibration caps, switches,
reference buffers, clocks, control, routing and guard structures.

Scalar thermal relation:

```text
Cstate >= kT / (b*VFS)^2.
```

Illustrative only, with 1 fF/um^2 MIM and 2.5 um^2/SRAM bit:

```text
b=1e-5, VFS=1 V   known caps ~15.81 mm^2   tape crossover ~12,351 ticks
b=3e-5, VFS=1 V   known caps ~ 1.76 mm^2   but thermal point fails
b=3e-5, VFS=2 V   known caps ~ 0.44 mm^2   but thermal point fails
```

The voltage convention is explicit: the often-quoted 1.15 pF at `b=3e-5`
corresponds to an effective 2 V swing; 1 V gives about 4.60 pF.

---

# v0.9 probe 1: remove the inertial near-2 from programmable self

For the continuous-wave source class,

```text
Q = [(1+a)I - dt^2 H] / sqrt(a).
```

Define

```text
p[n] = z[n] - z[n-1]
K = Q - 2I.
```

Then exactly

```text
p[n+1] = p[n] + K z[n] + u[n]
z[n+1] = z[n] + p[n+1].
```

Unit tests cover one-step, 100-step and inverse equivalence. Subtracting `2I`
changes no reciprocal edge coefficient or edge parameter derivative.

On all spent 2300--2309 benchmark tasks:

```text
old active-node |self|max       1.993759520
kick |self|max                  0.006240480
magnitude reduction             319.488x
sampled-noise amplitude ratio    17.874x
```

## Fixed measured near-2 implementation — static PASS, dynamic-noise REJECTED

A conservative v0.9 emulator kept the v0.8 position/history state but split

```text
d_i = fixed measured inertial gain + sampled residual self.
```

Frozen static assumptions:

```text
raw fixed gain mismatch          1% RMS
measurement error                0.1% RMS
residual range                   +/-0.125
residual bits                    10
edge thermal                     2e-5
residual-self thermal            2e-5
```

With **zero additional fixed-path dynamic noise**, spent 2300--2309 are very
clean:

```text
10/10 >=+0.10
10/10 wins
median DeltaC +0.499283
minimum DeltaC +0.332556
median gap +0.549227
```

But adding independent fixed-path full-node noise gives:

```text
1e-5 FS/tick   8/10 >=+0.10, 10/10 wins   FAIL
2e-5 FS/tick   6/10 >=+0.10,  8/10 wins   FAIL
```

Therefore the static decomposition is useful, but an ordinary noisy gain-2
analog amplifier is **not** an earned replacement for the self bank.

---

# v0.9 probe 2: exact (Z,P) state-bank coordinates

The existing two state vectors per lane can be reinterpreted exactly as

```text
Z = z[n]
P = z[n] - z[n-1]
```

rather than allocating a third state bank.

Per tick:

```text
P <- P + (Q-2I) Z + source
Z <- Z + P
```

The v0.8 terminal common/difference boundary maps exactly to

```text
C_Z <- Z-P
C_P <- -P
D_Z <- error_T
D_P <- error_T
```

and subsequent reverse evolution produces the same current fields as the old
position/history recurrence. Tests cover the boundary and 80 reverse ticks.

This route removes both the explicit near-2 self multiplier and explicit
`-PREV` packet algebraically, but it introduces two fixed unity state shears.
**Those shears are not yet a circuit-qualified/noise-free operation.** This is
currently an architectural probe, not v0.9 qualification.

---

# Current live experiment: complete-gradient averaging

The failed combined `b=2e-5` point preserved 10/10 exact-over-shuffled ordering.
A preregistered diagnostic on the same spent silicon is therefore testing

```text
M = 1, 2, 4, 8 complete physical echoes per parameter update
```

at

```text
edge b = self b = 2e-5.
```

Each repeat produces a complete physical contrast-gradient estimate. Those
vectors are averaged and **one** parameter update is made; the total update
count remains 30.

If `M=2` passes, the ideal kT/C capacitor scale is 4x smaller for only 2x echo
traversal count. If only `M=4` passes, capacitor-switching work is roughly
break-even in the ideal `C*V^2` term but area still falls 4x. Active-circuit,
clock and converter energy must be counted separately.

No fresh seeds are authorized until this diagnostic resolves.

---

## Remaining circuit gates

1. **Foreground kick-cancellation circuit** demonstrating <=0.5% measurement/cancellation error.
2. **Read-only credit frontend** producing `DeltaC+DeltaD` / `DeltaC-DeltaD` without disturbing state.
3. **MOS-level OTA realism**: slew, swing, common mode, noise, PVT, power and stability.
4. **(Z,P) unity-shear circuit** if the kick-drift state representation remains attractive.
5. **Area/energy model** including active circuits and clocks, not only capacitor area.
6. **Small recurrent tile** after individual primitives survive these gates.

The branch should continue to preserve failures rather than retune them away.
The passive-addition failure, v0.7 tail, v0.8 kick tail, monolithic self timing
failure and noisy fixed-inertial failure have all been useful precisely because
they forced architectural changes instead of tolerance wish-listing.
