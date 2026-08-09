# TW-1A v0.5 C0e edge-thermal formal gate — preregistration

This gate is frozen before any temporal-order result on bodies 1800–1809 is
inspected.

## Question

Does the emulator-qualified v0.5 + C0d machine retain its learning primitive on
untouched bodies when the legacy independent full-node noise term is removed and
replaced by circuit-native sampled-edge kT/C packets at the inward C0e target?

## Untouched bodies

```text
1800, 1801, 1802, 1803, 1804,
1805, 1806, 1807, 1808, 1809
```

These bodies have not been used by previous formal gates or diagnostics.

## Frozen physical edge architecture

Each physical edge uses the C0d-selected 4+3 segmented magnitude DAC:

```text
127 unit capacitors per edge
lower binary groups              1,2,4,8 units
upper thermometer                seven ordered 16-unit segments
unit-cap sigma                    3%
Cunit/Cstate                      0.001
measured site-specific codebook   yes
software sorting/repair           forbidden
```

## Hard fabrication-yield predicate

Before learning, every exact fabricated target tile must satisfy

```text
10/10 tiles have 112/112 strictly monotonic physical edge codebooks.
```

A non-monotonic edge is a hardware-yield failure. No tile may be replaced.

## Circuit-native thermal model

The legacy arbitrary state stress term is frozen to

```text
state_noise_std = 0.
```

For each selected physical edge capacitance ratio

```text
alpha = Cedge/Cstate,
```

define

```text
b = sqrt(kT/Cstate) / VFS_state.
```

One endpoint's edge-sampling packet RMS is

```text
sigma_edge/VFS = b * sqrt(alpha)/(1 + 2*alpha).
```

Each physical edge sample draws one scalar packet and injects it reciprocal in
space:

```text
+eta at endpoint i
-eta at endpoint j.
```

Forward, reverse-A and reverse-B samples are independent. Physical magnitude
code zero has `alpha=0` and therefore zero edge-sampling thermal packet.

The formal value is frozen at

```text
edge_ktc_base_fraction = b = 1e-5.
```

This value is one third of the largest all-body-clean point in the spent-body
C0e diagnostic (`3e-5`) and below the first tested failure (`1e-4`).

## Other frozen mixed-signal background

All other conditions remain those of the qualified v0.5/C0d machine:

```text
edge path                     measured signed 8-bit site codebook
self code                     12 bit
drive DAC                      8 bit
error DAC                     10 bit
sense ADC                      8 bit
state full scale              20 normalized units
sense ADC full scale           2
state clipping                 enabled

leakage_rate                   5e-4/tick
leakage_cv                     0.50
credit_noise_fraction          0.25
credit_offset_fraction         1.5e-4

raw reciprocal edge gain CV    0.10
edge calibration residual      0.001
raw common settling loss       0.10
A/B hold residual mismatch     0.001 RMS
raw self gain CV               0.10
self calibration residual      0.001
raw -PREV mismatch             0.03 RMS
-PREV calibration residual     0.001
raw terminal clone mismatch    0.05 RMS
clone calibration residual     0.001

raw common switch kick         3e-4 FS
raw differential switch kick   1e-4 FS
autozero cancellation error    0.02
common/diff residual floors    2e-6 / 1e-6 FS

error-DAC sign asymmetry        0.10
LCC curvature                  1.0
credit accumulator leakage     0.01/tick
```

Legacy B-only edge settling loss and A->B edge memory remain structurally zero.

## Frozen learner

```text
iterations = 30
step_size = 0.20
normalize_rms = true
shuffle_seed = 1729
```

## Formal qualification predicate

The gate qualifies only if both the fabrication predicate and all learning
conditions hold:

```text
10/10 fabricated tiles monotonic on all 112 edge codebooks
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

No failed body or fabrication draw may be removed or replaced. A failure remains
part of the record and bodies 1800–1809 become diagnostic-only.

## Physical interpretation if qualified

At 300 K, the frozen `b=1e-5` contract corresponds to the thermal lower-bound
relation

```text
Cstate = kT / (1e-5 * VFS_state)^2.
```

Representative candidate scales are:

```text
VFS=0.2 V: Cstate~1.035 nF, Cunit~1.035 pF
VFS=0.4 V: Cstate~258.9 pF, Cunit~258.9 fF
VFS=0.6 V: Cstate~115.1 pF, Cunit~115.1 fF
```

A pass would qualify the **edge-sampling thermal contribution only**. Self-path,
history-path, reset/copy and extracted MOS/parasitic noise remain later physical
gates.
