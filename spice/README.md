# TW-1A SPICE bring-up

This directory is the process-independent circuit-validation side of the
TW-1A research architecture. The active learning reference is now **v0.8
common/difference active summing**; older C0 tests are retained because they
record why the architecture changed.

These decks are not transistor/foundry qualification. They use idealized or
first-order active elements to kill topology/timing ideas before MOS sizing.

## Current ladder

```text
C0a  A/B phase-history reset/equalization        PASS
C0b  signed reciprocal charge packet             PASS
C0c  explicit capacitor magnitude array          PASS
C0d  unit mismatch / segmentation                PASS; 4+3 selected
C0e  circuit-native edge kT/C bridge             QUALIFIED in emulator

C1b  passive precharged NEXT accumulation        REJECTED
C1c  active virtual-sum accumulation             PASS
C1d  finite DC gain                              PASS / budgeted
C1e  monolithic |self|=3 timing                  REJECTED
C1e2 two-slice self timing                       PASS
C1e3 one half-range self bank reused twice       PASS
```

The most important rule of this directory is: **failed gates remain part of the design record.** C1b and C1e directly caused better architectures.

---

## C0a — phase-history timing

`tw1a_v05_phase_symmetry.cir` showed that incomplete **common** settling is much less dangerous than unequal analog history between reverse contexts.

```text
old sequential A/B mismatch     35.511717%
reset-symmetric mismatch         0.003686%
```

v0.8 later removed the old stored `F+A` / `F-A` reverse pair entirely by using common/difference coordinates, but C0a remains the evidence that motivated same-element phase symmetry.

## C0b/C0c/C0d — reciprocal edge capacitor bank

The edge cell established:

```text
exact zero/off code
correct sign
equal/opposite endpoint stamp
monotonic positive magnitude
mirrored +/- polarity
```

The explicit array and mismatch study selected

```text
lower bank: 1,2,4,8 units
upper bank: seven ordered 16-unit thermometer segments
physical units: 127 / edge
selectable magnitude branches: 11
```

The current emulator adds 3% RMS unit-cap mismatch and 1% RMS site-common
`Cunit/Cstate` mismatch and uses a nominal positive range of 0.265 so all 112
sites retain the compiler-required 0.250 range with useful yield margin.

---

# C1 — node active summing

## C1b — passive NEXT accumulation — REJECTED

`check_c1b_passive_additivity.py` directly connects a sampled capacitor to a
precharged destination state. The packet depends on the destination's existing
charge, exactly as a charge-sharing first-order lag predicts.

Frozen result:

```text
state-dependent additivity error ~50.000077%
```

This kills passive charge sharing as the node accumulator.

## C1c — active virtual-sum accumulation — PASS

`check_c1c_virtual_sum.py` transfers the same sampled charge into a virtual
summing node with a feedback/state capacitor.

Frozen result:

```text
packet magnitude                 25.600 mV
packet mismatch vs stored state  numerical floor
virtual-node excursion           ~0.001744 uV in ideal-gain deck
```

This is the architectural basis for the active-summing emulator. It is not yet a transistor OTA claim.

## C1d — finite DC gain — PASS / budgeted

`check_c1d_finite_gain.py` sweeps first-order open-loop gain under the actual
capacitive feedback factors. The point of the test is to avoid treating
`A0=1e5` as sacred.

Representative frozen 0.1% packet marker:

```text
edge load, Cin/Cf=0.265      first passing A0 ~3,000
old unsliced self, Cin/Cf=3  first passing A0 ~30,000
```

Fixed node gain can also be compiler-calibrated through the tested diagonal
similarity transform when it is stable, positive and measured. Drift,
nonlinearity and context dependence remain real residuals.

## C1e — monolithic self transfer — REJECTED

`check_c1e_finite_bandwidth.py` includes the worst self input load rather than
specifying GBW from a friendly edge case.

At `Cin/Cf=3` and a 20 ns aperture, the monolithic self packet misses the frozen
0.1% magnitude marker even at 1 GHz. The edge path itself passes at much lower
GBW.

The failure is a load/topology problem, not a request for a multi-GHz OTA.

## C1e2 — self slicing — PASS

`check_c1e2_self_slicing.py` holds the mathematical self coefficient fixed and
splits its charge transfer.

```text
1 slice, Cin/Cf=3       no tested GBW passes
2 slices, Cin/Cf=1.5    300 MHz passes
4 slices, Cin/Cf=0.75   300 MHz passes
8 slices, Cin/Cf=0.375  100 MHz passes
```

The smallest useful architectural change is two slices.

## C1e3 — reuse one half-range bank — PASS

`check_c1e3_self_reuse.py` asks whether two slices require duplicated physical
self banks. They do not in the first-order deck.

At 300 MHz:

```text
TRANSFER1          20 ns
RESET/RESAMPLE      5 ns   FAIL
RESET/RESAMPLE     10 ns   PASS
TRANSFER2          20 ns
```

The 10 ns reset case gives about

```text
packet magnitude error       0.0987%
state-dependent mismatch     0.0233%
```

so v0.8 uses one `|self|<=1.5` bank twice.

---

# Thermal result feeding back into circuit architecture

The strongest fresh v0.8 emulator gate includes both edge and self sampling
kT/C with

```text
b_edge = b_self = 1e-5
```

and passes 10/10 on fresh bodies 2300..2309.

A controlled spent-body split then found:

```text
edge=2e-5, self=1e-5   PASS 10/10
edge=1e-5, self=2e-5   FAIL 5/10
```

So the first sampled-cap thermal wall is **node-local self sampling**, not the
reciprocal edge bank.

The v0.9 algebra/compiler audit explains why: for the present continuous-wave
source class, the active-node self coefficient is about 1.994 because the
second-order recurrence carries a universal near-2 inertial term. Subtracting
`2I` in exact kick-drift coordinates leaves only about 0.00624 programmable
active-node self while every edge coefficient remains unchanged.

A first attempt to realize that near-2 term as an ordinary measured fixed-gain
analog path was rejected by emulator diagnostics: static calibration works, but
an added independent `1e-5 FS/tick` full-node noise source already creates a
hard learning tail.

Therefore the next C1 circuit question is **not** “build a quieter x2 amplifier.”
It is whether the same two state banks can implement exact kick-drift shears
structurally enough to avoid recreating a noisy wide self multiplier:

```text
P <- P + (Q-2I) Z + source
Z <- Z + P
```

with terminal mirror

```text
Z <- Z-P
P <- -P.
```

That candidate is still unqualified.

---

## Current circuit-facing targets

```text
edge nominal positive range                 0.265
compiler required edge range                0.250
edge unit mismatch model                    3% RMS
site Cunit/Cstate mismatch model            1% RMS
foreground switch-kick cancellation error   <=0.5% RMS
common residual kick floor                  <=2e-6 state FS RMS
differential residual kick floor            <=1e-6 state FS RMS
active edge packet aperture                 20 ns class
v0.8 reusable self path                     two x 20 ns transfers
self bank reset/resample                    >=10 ns in C1e3 deck
working first-order self OTA point           ~300 MHz
```

The branch should not translate normalized emulator thermal noise into a final
MIM value until state voltage convention, topology noise factor and active-circuit noise are chosen explicitly.
