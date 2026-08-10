# Published filter multi-state topology diagnosis v0.7 — result

Date: 2026-08-10

Preregistration: `docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_PREREG.md`

Frozen workflow run: `31359232293`

Status: **PRIMARY DISCOVERY FAIL / PRIMARY RECOVERY FAIL**

## Frozen question

Can several known physical resonator-detuning states rescue the compensated static-topology ambiguity exposed by v0.6, while the same hidden physical matrix is shared across states and each state retains its own five-variable measurement nuisance block?

The frozen states were:

```text
BASE
R1_UP    d1 = +0.080
R2_DOWN  d2 = -0.070
R4_UP    d4 = +0.060
```

The stage-1 fit used one shared seven-parameter declared matrix plus `4 x 5 = 20` independent nuisance variables. Stage 2 ranked every absent edge using one shared exact multi-state derivative/probe. Only the top-ranked candidate was allowed into the stage-3 augmented refit.

## Aggregate result

```text
cells                         15
true hidden edge top-1         9/15
true hidden edge top-3         9/15
augmented recovery             9/15

primary discovery clause       FAIL
primary recovery clause        FAIL
strong 15/15 label             FALSE

median true-edge rank          1
worst true-edge rank           8
median stage-1 matrix RMSE     2.180344e-3
median stage-3 matrix RMSE     2.610587e-4
median loss reduction          21.0106x
median parasitic abs error
  when true edge selected      3.497957e-5
```

The preregistered primary clauses required:

```text
TOP1 >= 12/15
TOP3 = 15/15
RECOVERY >= 12/15
```

None was met. The frozen result is therefore an unambiguous **FAIL**.

## Case breakdown

| Case | Hidden edge | Hidden value | True-edge ranks A/C/D | Top-1 | Top-3 | Recovery |
|---|---:|---:|---:|---:|---:|---:|
| 4400 | `(2,5)` | `-0.032` | `6, 8, 7` | 0/3 | 0/3 | 0/3 |
| 4401 | `(1,5)` | `+0.028` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |
| 4402 | `(0,3)` | `-0.026` | `4, 6, 6` | 0/3 | 0/3 | 0/3 |
| 4403 | `(3,5)` | `+0.033` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |
| 4404 | `(0,4)` | `-0.022` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |

The failure is highly structured, not a general optimizer collapse. Three hidden-edge locations were discovered and recovered perfectly across all starts. Two locations failed across all starts.

## What the successful cells still show

When the true edge was selected, value recovery remained very accurate. Across the nine successful cells, the median hidden-edge absolute error was approximately

```text
3.50e-5.
```

The stage-3 base matrix was also generally accurate, with aggregate median RMSE approximately

```text
2.61e-4.
```

So the limiting problem remains **topology identifiability/selection**, not fitting the value of an already-correctly-selected edge.

## Post-result mechanism update — not part of the frozen gate

After v0.7 had already been committed and launched, a separate Jacobian/gauge analysis identified a classical coupling-matrix similarity-transformation mechanism behind the difficult static cases.

For the published four-resonator folded topology, internal orthogonal rotations live in `so(4)`, which has six infinitesimal generators. The declared zero pattern fixes that gauge at the nominal topology. Releasing particular absent edges re-opens one generator:

```text
candidate (0,3)  -> frees the R1 <-> R3 rotation
candidate (2,5)  -> frees the R2 <-> R4 rotation
```

A topology-only calculation using no S-parameter data predicted **exactly those two** machine-zero static physical aliases and no others among the eight absent edges. This matched the independently computed response-Jacobian microscope exactly.

Known diagonal detuning of either resonator touched by the corresponding rotation breaks that exact gauge:

```text
(0,3) alias anchors: R1 or R3
(2,5) alias anchors: R2 or R4
```

The frozen v0.7 schedule therefore contained mathematically valid gauge anchors for both difficult cases: R1 anchors `(0,3)`, while R2/R4 anchor `(2,5)`.

Yet those two cases still failed.

That establishes an important distinction:

> **breaking the exact realization gauge is necessary for unique physical diagnosis, but it is not sufficient for reliable finite-noise topology ranking after a flexible wrong-model fit has compensated.**

The post-hoc response-space identifiability microscope found that the four-state schedule gives the difficult `(2,5)` direction only a small residualized novelty fraction (about `0.044` for S11/S21). The symmetry is no longer exact, but most of the candidate response direction is still explainable by the fitted physical+nuisance tangent space.

This motivates a noise-whitened/Fisher detectability score for experiment design, but **no v0.8 synthetic rescue is opened here**.

## Stopping line

v0.7 was the preregistered software-only test of the multi-state rescue idea. It failed.

Accordingly:

- automatic parasitic topology discovery remains **unqualified**;
- the topology-only gauge table is retained as a negative-capability/experiment-design tool;
- the next meaningful external test is a real reciprocal resonator/filter measured in at least two known physical states;
- without physical hardware, the project should not manufacture further synthetic hit-rate ladders merely to improve the score.

The software work remains useful independently of that missing experiment: nuisance-aware fitting, Touchstone ingestion, fitted-minus-design diagnosis, repeated-sweep analysis, exact sensitivities, and topology/gauge capability analysis are all retained.

## Reproducibility

Frozen experiment:

- `experiments/published_filter_multistate_topology_v07.py`
- `experiments/summarize_multistate_topology_v07.py`
- `.github/workflows/published-filter-multistate-topology-v07.yml`

Post-hoc mechanism tools:

- `transientwave/identifiability.py`
- `transientwave/topology_gauge.py`
- `experiments/published_filter_topology_gauge_table.py`
- `docs/FILTER_REALIZATION_ROTATION_PROOF_2026-08-10.md`
