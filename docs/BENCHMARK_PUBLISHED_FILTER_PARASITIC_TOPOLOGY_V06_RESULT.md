# Published filter parasitic-topology discovery v0.6 — result

Date: 2026-08-10

Preregistration: `docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_PREREG.md`

Frozen workflow run: `31357543837`

Status: **PRIMARY DISCOVERY FAIL / RECOVERY 12/15**

## Frozen question

Starting from the published six-node, seven-edge cross-coupled filter model, hide one weak reciprocal edge that is absent from the declared topology. Fit the knowingly wrong declared topology together with the already-qualified v0.5 measurement nuisance, then ask whether the remaining complex residual identifies the missing reciprocal edge.

The discovery stage was deliberately local and restrictive:

1. finish the wrong-topology 12-variable fit;
2. hold that fitted matrix and nuisance fixed;
3. for every absent reciprocal edge, compute the exact response derivative at zero edge strength;
4. take one bounded Gauss-Newton probe step;
5. rank candidates by the **actual** probe loss;
6. allow the augmented refit to use the top-ranked edge only.

No second-ranked rescue was allowed.

## Aggregate result

```text
cells                                      15
true hidden edge ranked #1                 12/15
true hidden edge ranked in top 3           12/15
augmented recovery clause                  12/15

frozen discovery-primary clause            FAIL
frozen recovery-primary clause             PASS
strong 15/15 label                         FALSE

median true-edge rank                      1
worst true-edge rank                       8
median stage-1 wrong-topology matrix RMSE  5.807021e-4
median stage-3 base-matrix RMSE             1.215978e-4
median stage-3 loss reduction vs stage 1   40.8152x
median parasitic abs error when selected   5.766139e-5
```

The preregistered discovery clause required:

```text
TOP1 >= 12/15
AND
TOP3 = 15/15.
```

The first half was met exactly. The second half was not. Therefore the primary discovery result is **FAIL**, not a partial pass.

## Case breakdown

| Case | Hidden edge | Hidden value | True-edge ranks across A/C/D | Top-1 | Top-3 | Recovery |
|---|---:|---:|---:|---:|---:|---:|
| 4300 | `(0,2)` | `+0.030` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |
| 4301 | `(1,3)` | `-0.040` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |
| 4302 | `(2,4)` | `+0.035` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |
| 4303 | `(2,5)` | `-0.025` | **`8, 8, 7`** | **0/3** | **0/3** | **0/3** |
| 4304 | `(0,4)` | `+0.020` | `1, 1, 1` | 3/3 | 3/3 | 3/3 |

This is not random degradation across all cases. Four hidden-edge locations are recovered perfectly across all three optimizer starts, while one load-side hidden edge fails systematically.

## What worked

When the local probe selected the true edge, the subsequent augmented fit was very accurate.

For example, case 4300 / start A hid

```text
(0,2) = +0.030000
```

and the residual scorer ranked `(0,2)` first. The one-step probe reduced the wrong-topology residual by about 60.7%, and the augmented fit recovered approximately

```text
(0,2) = +0.030047
```

with base seven-knob matrix RMSE about `9.41e-5`.

Across all cells in which the true edge was selected, the median parasitic absolute error was only

```text
5.77e-5.
```

So **value recovery after correct topology selection is not the limiting problem here.**

## Failure anatomy: case 4303

The hidden edge

```text
(2,5) = -0.025
```

is qualitatively different under this local scoring rule.

Across starts A/C/D, its true-edge rank was

```text
8, 8, 7.
```

The scorer instead preferred another absent edge, commonly `(0,2)`. The wrong-topology stage-1 matrix had already moved substantially:

```text
stage-1 base-matrix RMSE ≈ 0.013487
```

compared with roughly `1.6e-4` to `6.0e-4` for the four successful hidden-edge cases.

The top-ranked wrong augmentation did not repair that basin. Depending on start it barely improved or even worsened the measured fit, while the physical matrix remained badly displaced.

This suggests a specific mechanism:

> **a wrong-topology fit can absorb an omitted physical interaction into the allowed matrix and nuisance variables strongly enough that the local derivative of the missing edge at the fitted point is no longer a reliable topology identifier.**

The exact sensitivity is still mathematically correct at that fitted point. The problem is that the fitted point is a compensated wrong model.

## Boundary established by v0.6

The v0.6 result does **not** support an automatic claim that one local residual-gradient scan can discover an arbitrary single missing reciprocal edge.

It supports the narrower statement:

> For four of five frozen hidden-edge locations, the local residual probe identified and recovered the omitted reciprocal edge perfectly across three starts; one location produced a systematic identifiability failure in which the true edge ranked near the bottom.

Accordingly, the local scorer remains a research diagnostic. It is **not** promoted into the public CLI as an automatic topology-discovery command.

## Next test

The failure points to the next estimator directly.

Instead of holding the wrong-topology fit fixed while probing one candidate edge locally, score each absent edge by a **candidate-conditioned refit**:

```text
wrong-topology solution
    + candidate edge c
    -> jointly re-optimize physical matrix + c + nuisance
    -> compare final complex residual / model score
```

All candidate models have the same number of added parameters, so the first microscope can compare final fit loss directly. A later production version can add explicit information criteria or sparsity penalties when model sizes differ.

The existing 4303 data may be used only as a post-hoc mechanism microscope. A qualifying v0.7 result should use fresh hidden edges/noise seeds and be preregistered before outcome inspection.

## Research lesson

The useful negative result here mirrors the hardware work in spirit:

- in TW-1A, an exact deterministic adjoint relationship did not imply an adjoint of a separately perturbed stochastic history;
- here, an exact local derivative did not imply globally reliable topology identification after a flexible wrong model had already compensated for the missing interaction.

In both cases, **the derivative can be right while the state at which it is evaluated is the wrong object for the inference being asked of it.**
