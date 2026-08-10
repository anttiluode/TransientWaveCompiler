# Exact realization rotation behind the v0.6 `(2,5)` alias

Date: 2026-08-10

Status: **post-hoc algebraic mechanism proof / not a qualifying benchmark**

## Result

The machine-zero Jacobian novelty found for the failed v0.6 hidden edge `(2,5)` is not merely a numerical near-degeneracy.

It is the tangent of an exact internal orthogonal change of resonator basis that leaves every source/load S-parameter unchanged.

The explicit-port model is

```text
A(Omega) = M + Omega U - j(q + lambda U)
```

where `U` is identity on the internal resonators and zero on source/load, while `q` is nonzero only at the source/load ports.

Let `R(theta)` be an orthogonal rotation acting only on internal resonators 2 and 4, with source and load coordinates fixed. Then

```text
R U R^T = U
R q R^T = q
```

and therefore

```text
A'(Omega) = R A(Omega) R^T
A'(Omega)^-1 = R A(Omega)^-1 R^T.
```

Because `R` is identity on the source and load coordinates, the port entries of `A^-1` are unchanged. Hence `S11`, `S21`, `S12`, and `S22` are all unchanged for every frequency under this realization rotation.

## Infinitesimal generator

For the actual compensated v0.6 case 4303 / start A matrix, the load coupling is

```text
m4L = 1.020359910890014.
```

Choose a skew generator `K` with

```text
K[2,4] = +1 / m4L
K[4,2] = -1 / m4L.
```

The infinitesimal matrix motion is

```text
delta M = K M - M K.
```

This gives a unit `(2,5)` tangent together with

```text
delta m12 = -0.1653941943
delta m23 = -0.8611000992
delta m34 = -0.7337177767
delta m14 = +0.8471544716
delta m25 = +1.0000000000
```

or equivalently

```text
d/dm25 response
 = +0.1653941943 * d/dm12 response
   +0.8611000992 * d/dm23 response
   +0.7337177767 * d/dm34 response
   -0.8471544716 * d/dm14 response.
```

Those are exactly the coefficients independently recovered by the response-Jacobian least-squares microscope, to floating-point precision.

So the `eta ~ 1e-15` result is explained structurally: the missing-edge derivative is a realization-gauge direction already spanned by the declared physical matrix knobs.

## Why S22 cannot help

The transformation leaves **all port coordinates fixed**, not merely source excitation / load observation. Therefore the entire two-port S matrix is invariant, including `S22`.

That is why adding S22 left the physical-only novelty of `(2,5)` at machine zero rather than rescuing it.

## Why R2/R4 detuning breaks it and R1/R3 does not

Let `D_i` be a known unit diagonal detuning stamp on physical resonator `i`.

The same generator obeys

```text
[K, D1] = 0
[K, D3] = 0
[K, D2] != 0
[K, D4] != 0.
```

Therefore a known physical perturbation of R1 or R3 is compatible with the same hidden 2<->4 basis rotation and cannot anchor that gauge direction.

A known perturbation of R2 or R4 does not commute with the rotation. It labels one of the physical coordinates being mixed, thereby breaking the exact equivalence across the measurement states.

This exactly matches the post-hoc experiment-design scan:

```text
BASE + R4 +/-0.08    novelty ~0.05354
BASE + R2 +/-0.08    novelty ~0.05326
BASE + R1 +/-0.08    novelty ~machine zero
BASE + R3 +/-0.08    novelty ~machine zero
```

The preregistered v0.7 state set already contains R2 and R4 perturbations, so it contains the correct kind of physical coordinate anchors even though it was chosen before this mechanism proof was derived.

## Engineering consequence

A single static S-parameter measurement cannot, in general, tell an engineer which member of a response-equivalent coupling-matrix realization orbit corresponds to the literal physical resonators in the hardware.

To turn matrix extraction into physical diagnosis, the measurement set must contain information that fixes the physical internal coordinates. A deliberately known resonator perturbation is one way to do that.

This reframes topology diagnosis as an identifiability problem:

```text
static port response
    -> possibly only a realization equivalence class

known physical perturbation(s)
    -> coordinate anchors
    -> potentially unique physical diagnosis
```

Coupling-matrix similarity transformations and non-unique realizations are established prior art. The useful TWC contribution under test is the exact local identifiability diagnostic and its use for measurement/perturbation design and uncertainty-aware reporting.

## Reproducibility

Executable proof/microscope:

- `experiments/filter_identifiability_rotation_proof.py`

Related:

- `transientwave/identifiability.py`
- `docs/FILTER_IDENTIFIABILITY_ALIASING_2026-08-10.md`
- frozen v0.6 result `docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md`
