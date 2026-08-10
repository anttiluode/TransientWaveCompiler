# Filter tuner prior art and claim boundary

Date: 2026-08-10

Status: living boundary document, not an exhaustive literature review.

## Why this document exists

The filter-tuning branch became useful quickly enough that it would be easy to overstate what is new.

That would be a mistake. Coupling-matrix synthesis, extraction, reconfiguration, computer-aided tuning, and even localization of parasitic couplings are established research areas. TWC should be evaluated on the narrower behavior it actually demonstrates, not on claims that belong to prior art.

## Claims TWC does **not** make

TWC does not claim invention of:

- the coupling-matrix formalism;
- extracting coupling matrices from measured or simulated S-parameters;
- fitting a predefined coupling topology;
- recovering resonator losses / unloaded Q from lossy filter measurements;
- using the difference between an extracted and target coupling matrix to guide physical tuning;
- handling transmission-line/reference-plane phase without a mandatory separate de-embedding step in every method;
- numerical, gradient-free, vector-fitting, Cauchy, homotopy-continuation, isospectral-flow, or neural-network coupling-matrix extraction;
- detecting, locating, or fitting parasitic cross-couplings as a general concept.

## Concrete prior-art examples

This short list is intentionally selected around the claims most likely to be confused with TWC.

### Ng et al. — modified vector fitting, 2023

C. L. Ng, S. Soeung, S. Cheab, and K. Y. Leong,
“A Modified Vector Fitting Technique to Extract Coupling Matrix from S-parameters,”
*Radioengineering*, vol. 32, no. 3, pp. 325–331, 2023.
DOI: `10.13164/re.2023.0325`.

The paper explicitly supports predefined topologies and forms the rational polynomials from S-parameter responses **without first removing phase offset or de-embedding transmission lines**. It then generates the desired coupling-matrix configuration using bounded/unbounded nonlinear-polynomial optimization.

This rules out an overbroad TWC claim such as “existing extraction always de-embeds phase first.”

### Javadi et al. — lossy measurement extraction, 2023

S. Javadi, B. Rezaee, M. Stadler, M. Leitner, M. E. Gadringer, and W. Bösch,
“Coupling Matrix Extraction From Lossy Filter Measurements,”
*2023 Asia-Pacific Microwave Conference (APMC)*, pp. 832–835, 2023.
DOI: `10.1109/APMC57107.2023.10439819`.

The method fits measured scattering parameters with simulated annealing and targets an arbitrary desired coupling topology while treating lossy measurements.

So lossy coupling-matrix extraction itself is not a TWC novelty.

### Djianga et al. — matrix-error-guided physical correction, 2025

A. N. Djianga, C. Mbinack, G. A. Eyebe, P. Zhao, and J. S. A. E. Fouda,
“Design and simultaneous analytical optimization of microwave filters with superimposed rectangular cavities for radar applications,”
*AEU - International Journal of Electronics and Communications*, vol. 188, 155572, 2025.
DOI: `10.1016/j.aeue.2024.155572`.

Their CAD process extracts a coupling matrix from S-parameters, compares the extracted coefficients with the target matrix, and uses the signs/differences to guide simultaneous physical dimension corrections.

Therefore the broad idea “turn a measured response into coupling-matrix diagnosis and tuning corrections” is also established prior art.

### Michalczyk and Michalski — measured parasitic cross-couplings, 2021

J. Michalczyk and J. Michalski,
“Coupling Matrix Extraction by Numerical Solving of Polynomial Systems by Homotopy Continuation,”
*IEEE Microwave and Wireless Components Letters*, 2021.
DOI: `10.1109/LMWC.2021.3096659`.

The reported measurement validation includes a sixth-order filter containing regular and **parasitic cross-couplings**. Thus fitting measured responses that contain parasitic coupling structure is already part of the literature.

### Michalczyk and Michalski — locating parasitic couplings, 2024

J. Michalczyk and J. J. Michalski,
“Method to Determine Parasitic Couplings in Microwave Filters,”
*54th European Microwave Conference (EuMC)*, pp. 128–131, 2024.

This work goes beyond merely fitting a matrix: it proposes a method for determining the **location of parasitic couplings** from S-parameter measurements, using slightly detuned resonators and differences between extracted coupling matrices.

This is especially important for the TWC v0.6/v0.7 direction. “Parasitic topology discovery” by itself is **not** a defensible novelty claim. Deliberately perturbed multi-state measurements are also established as a way to expose parasitic structure.

### Sallam and Attiya — physics-informed extraction, 2026

T. Sallam and A. M. Attiya,
“Fast and accurate extraction of microwave filter coupling matrix via physics-informed deep learning,”
*Scientific Reports*, vol. 16, 17192, 2026.
DOI: `10.1038/s41598-026-46255-w`.

This work again uses the standard symmetric coupling-matrix response model and predefined physical structure, while learning coupling values from S-parameter responses. It also states the classical bandpass normalized frequency

```text
gamma = (f0/BW) * (f/f0 - f0/f).
```

TWC now supports this normalization explicitly when preparing Touchstone measurements.

## What TWC has actually demonstrated

The strongest current filter-side statements are narrower.

### 1. Exact direct response derivatives over the declared physical knobs

For the explicit-port reciprocal model, TWC differentiates the matrix inverse analytically:

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

The same optimizer can therefore carry physical coupling/detuning parameters and supported measurement nuisance in one bounded complex-response objective.

This is a property of the implementation and method. It should not be advertised as the first use of gradients in filter extraction without a deeper method-by-method literature audit.

### 2. A frozen failure comparison for this joint nuisance model

The v0.5 experiment is a concrete result, not a broad historical claim:

```text
same 15 frozen measurement/start cells

lossless matrix-only fit               hidden-matrix recovery 0/15
matrix + loss + phase nuisance fit     full recovery         15/15
```

The supported lesson is:

> Under the frozen systematic corruption used in v0.5, allowing the physical matrix to absorb omitted loss/reference-plane nuisance corrupted the hidden matrix, while joint estimation recovered it on all 15 cells.

This does **not** imply that all conventional pipelines perform de-embedding first or that all previous methods fail under phase loading.

### 3. A real-data-ready diagnosis surface

The branch now combines:

```text
Touchstone S11/S21
+ explicit frequency normalization
+ declared/nominal reciprocal topology
+ bounded physical parameters
+ optional joint loss/phase nuisance
-> fitted physical matrix
-> fitted-minus-nominal diagnosis
```

That packaging can still be useful even when each mathematical ingredient has prior art.

### 4. The v0.6 topology experiment qualifies a specific estimator only

The preregistered v0.6 local residual-probe experiment produced:

```text
true hidden edge top-1      12/15
true hidden edge top-3      12/15
augmented recovery          12/15
primary discovery clause    FAIL
```

Four of five hidden-edge locations were perfect across all starts. One hidden edge, `(2,5)=-0.025`, ranked `8,8,7` and failed systematically.

Therefore TWC should **not** advertise its current local residual-gradient scan as a reliable automatic parasitic-topology detector.

Even if a later candidate-conditioned or multi-state TWC method succeeds, the correct claim would concern the behavior and engineering properties of that **specific estimator** — for example joint nuisance handling, exact direct sensitivities, computational cost, robustness, or generalization across reciprocal systems — not invention of parasitic-coupling localization itself.

## Current defensible positioning

A compact accurate description is:

> **TWC is an experimental reciprocal-system diagnosis toolkit that directly fits constrained coupling-matrix physics and supported measurement nuisance to complex S-parameters using exact inverse-matrix sensitivities. Its frozen benchmarks show how omitted nuisance can corrupt inferred physical parameters, and its research branch tests explicit model-mismatch diagnostics under preregistered failure gates.**

That leaves coupling-matrix extraction, computer-aided tuning, and parasitic-coupling localization where they belong: in the prior art.

## What would materially strengthen the project next

The highest-value evidence is no longer another synthetic low-RMSE fit.

1. **Real VNA data:** repeat sweeps of a physical filter, then deliberate resonator/coupling perturbations with known direction.
2. **Stability:** show that fitted physical corrections are reproducible across repeated sweeps while nuisance absorbs measurement-chain variation.
3. **Predictive diagnosis:** after fitting one trace, make the prescribed physical adjustment and test whether the next trace moves in the predicted direction.
4. **Topology research:** use the v0.6 failure to compare local residual scoring, candidate-conditioned refits, and multi-state/perturbation-aided identification without treating any of those broad ideas as automatically novel.
5. **Cross-domain value:** test whether the same sparse-reciprocal diagnosis machinery transfers cleanly to a second domain rather than optimizing only for microwave-filter conventions.

Those experiments distinguish a useful reciprocal-system engineering tool from another coupling-matrix fitting implementation.
