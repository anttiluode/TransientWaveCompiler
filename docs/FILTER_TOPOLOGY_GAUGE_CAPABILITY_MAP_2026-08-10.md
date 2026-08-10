# Filter topology gauge capability map

Date: 2026-08-10

Status: **topology-only negative-capability / experiment-design report**

This page answers a question that should be asked **before** ranking candidate parasitic couplings:

> Does a static two-port response contain enough information to distinguish this proposed physical edge from a response-equivalent coupling-matrix realization?

The calculation uses the declared coupling-matrix topology and nominal matrix values. It does **not** use measured S-parameters, optimizer output, noise realizations, or a hidden answer key.

## Classical boundary

Internal orthogonal/similarity transformations between response-equivalent coupling matrices are classical filter-synthesis machinery associated with Atia–Williams, Cameron, and subsequent coupling-matrix synthesis literature. TWC does not claim this invariance.

TWC uses the invariance as an explicit capability test:

```text
internal rotation generators K in so(N)
        ↓
realization tangent dM = K M - M K
        ↓
impose every declared-zero entry as a constraint
        ↓
release one proposed candidate zero
        ↓
did the surviving gauge dimension increase?
```

If yes, opening that candidate edge can be part of a response-equivalent internal coordinate rotation. A static port response cannot uniquely identify the literal physical edge without additional coordinate information.

## Published four-pole folded example

Node convention:

```text
0 = source
1..4 = physical resonators R1..R4
5 = load
```

Declared nonzero/tunable couplings:

```text
(0,1)  source-R1
(1,2)  R1-R2
(2,3)  R2-R3
(3,4)  R3-R4
(4,5)  R4-load
(1,4)  folded cross-coupling R1-R4
(0,5)  source-load
```

Four internal resonators give

```text
dim so(4) = 4*3/2 = 6
```

rotation generators before topology zeros pin the internal basis.

### Candidate capability table

| Candidate edge | Static gauge alias? | Freed internal rotation | Single known resonator detuning(s) that anchor it |
|---|---:|---|---|
| `(0,2)` | No | — | — |
| `(0,3)` | **YES** | **R1 ↔ R3 (`K13`)** | **R1 or R3** |
| `(0,4)` | No | — | — |
| `(1,3)` | No | — | — |
| `(1,5)` | No | — | — |
| `(2,4)` | No | — | — |
| `(2,5)` | **YES** | **R2 ↔ R4 (`K24`)** | **R2 or R4** |
| `(3,5)` | No | — | — |

The declared topology itself has zero surviving gauge dimension at the nominal point. Releasing `(0,3)` or `(2,5)` increases that dimension by one; releasing any other absent reciprocal edge does not.

## Independent cross-check

Before this topology-only test existed, a completely separate response-Jacobian microscope had evaluated all eight absent edges at the compensated v0.6 fit.

It found exactly two physical-only candidate derivatives with machine-zero orthogonal novelty:

```text
(0,3)
(2,5)
```

The topology-only calculation predicts exactly the same set.

Eight additional deterministic draws of generic nonzero values on the same declared topology also preserve that alias set, supporting that this example is a topology-pattern effect rather than an accidental equality at one coefficient vector.

## What an alias means

For an aliased candidate the problem is not merely that the optimizer is weak.

Opening that edge re-opens an internal realization coordinate that the original declared zero pattern had fixed. Along the corresponding similarity orbit, the internal matrix entries change while the external two-port response stays unchanged.

Therefore a static response should not be reported as

```text
candidate A rank #1
candidate B rank #2
```

when A and B lie in the same response-equivalent realization family.

The appropriate output is closer to

```text
STATIC RESPONSE DOES NOT UNIQUELY LABEL THIS PHYSICAL EDGE

candidate: (2,5)
reason: releasing it frees R2<->R4 realization rotation
coordinate anchor: perturb R2 or R4 and measure again
```

## What an anchor means

A known physical detuning labels a resonator coordinate.

For `(2,5)`, the exact static gauge mixes R2 and R4. Known detuning of R2 or R4 does not commute with that rotation and therefore breaks the exact equivalence. Detuning R1 or R3 commutes with it and cannot break that particular gauge.

Likewise `(0,3)` is the source-side mirror:

```text
(0,3) -> R1<->R3 rotation -> anchor R1 or R3
```

This turns classical matrix non-uniqueness into an experiment-design instruction.

## Important limit: gauge-breaking is not sufficient

The preregistered v0.7 experiment measured the same synthetic hidden device in four known states:

```text
BASE
R1 +0.080
R2 -0.070
R4 +0.060
```

That schedule mathematically anchors both exact aliases in this table.

Nevertheless v0.7 achieved only:

```text
top-1       9/15
top-3       9/15
recovery    9/15
```

and both gauge-class hidden edges failed across every optimizer start.

So the correct hierarchy is:

```text
exact gauge survives
    -> unique static physical diagnosis impossible

exact gauge broken by known state
    -> unique diagnosis becomes possible in principle
    -> but practical detectability may still be weak
```

The response-space microscope estimates that practical weakness. For the difficult `(2,5)` direction under the frozen four-state schedule, only a few percent of the raw candidate sensitivity remains orthogonal to the fitted physical+nuisance tangent space.

A future real-data design score should therefore use the residualized candidate signal after whitening by measured sweep covariance, rather than treating gauge-breaking alone as success.

## Why this page is useful without a VNA

This capability map is a property of the chosen model/topology. It can be computed before hardware exists and before a sweep is taken.

It can therefore be used to:

- reject a proposed one-shot topology diagnosis that is structurally impossible;
- identify which physical resonator coordinates need to be perturbed to remove an exact ambiguity;
- distinguish structural non-identifiability from ordinary optimizer/noise failure;
- avoid false confidence from ranking response-equivalent candidate models;
- plan a future measurement protocol around the topology rather than collecting more copies of an uninformative static state.

## Reproducibility

Implementation:

- `transientwave/topology_gauge.py`
- `tests/test_topology_gauge.py`
- `experiments/published_filter_topology_gauge_table.py`
- `.github/workflows/filter-topology-gauge-table.yml`

Related response-space analysis:

- `transientwave/identifiability.py`
- `docs/FILTER_REALIZATION_ROTATION_PROOF_2026-08-10.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md`

Prior-art boundary:

- `docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md`
