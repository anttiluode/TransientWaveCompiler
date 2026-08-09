# TW-1A full-update coherent drift boundary — result v0.1

Preregistration: `docs/FULL_UPDATE_COHERENT_BOUNDARY_PREREG_V01.md`

Workflow: `full-update-coherent-boundary-v01`

Development data: already-spent seeds 990–999.

## Result

**No drift boundary can be inferred from this block.**

The frozen pass-prefix rule stopped immediately because even the `drift=0` point failed the strict final predicate: seed 998 had a small negative exact improvement.

Crucially, the same seed remained the only negative tail across the entire tested coherent-drift grid:

`0, 0.025%, 0.05%, 0.10%, 0.15%, 0.20%, 0.30%, 0.50%`.

At every point:

- 9/10 seeds reached `DeltaC >=0.10`;
- exact final contrast beat shuffled final in 10/10;
- medians remained strongly positive;
- seed 998 stayed slightly negative.

Representative medians:

- 0% coherent drift: `median DeltaC = +0.6312`;
- 0.20% coherent drift: `+0.6097`;
- 0.50% coherent drift: `+0.6106`.

Thus this block does **not** support the claim that increasing coherent operator variation from 0 to 0.5% is causing the robustness failure. The baseline simultaneous non-drift damage context already creates the tail.

No fresh confirmation seeds 1000–1009 were consumed because the preregistered algorithm found no nonzero candidate.

## Interpretation

Full-gradient coherence changes the drift question qualitatively. Once all terms in the physical gradient refer to one common Q realization, absolute quasi-static Q variation becomes much less important than the other within-update error sources.

The next allowed diagnostic is to keep coherent drift at zero on the spent 990–999 block and remove one other damage component at a time to identify the source of seed 998's tail. This is mechanism diagnosis only, not a new hardware claim.
