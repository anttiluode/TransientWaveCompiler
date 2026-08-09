# TW-1A v0.9 fixed-task fabrication × dynamic-noise factorial preregistration

Status: **diagnostic, frozen before outcomes**.

This experiment exists because the original v0.9 fresh gate used one integer seed to choose three logically distinct things: the temporal-order task, the fabricated circuit realization, and the stochastic dynamic-noise trajectory. The partitioned-RNG emulator now lets those axes be separated without changing the physical equations.

## Frozen question

For the known ideal-learnable temporal-order task **2400** (ideal-credit improvement `+0.864382`), is the v0.9 failure primarily:

1. a particular fabricated-silicon realization,
2. dynamic-run luck on otherwise acceptable silicon, or
3. a broad interaction of both axes?

## Frozen matrix

- task seed: `2400` only
- fabrication seeds: `2400, 2401, 2402, 2403, 2404`
- dynamic seeds: `8000, 8001, 8002, 8003, 8004`
- 25 total learner runs
- 30 updates, step size `0.20`, RMS-normalized credit
- complete formal v0.9 kick-drift configuration from `experiments/v09_fresh_corner.py`
- **no surgical removal or rescaling of switch residuals**
- edge/self/drift thermal bases all remain at `2e-5`
- drift switch common/differential residual settings remain at the formal v0.9 point

For each fabrication seed, the circuit is reconstructed once per run from the same fabrication seed; `dynamic_seed` changes only the partitioned edge/self/drift/credit stochastic streams. Static disorder is not redrawn by dynamic reseeding.

## Frozen readouts

For every cell record:

- contrast improvement `DeltaC`
- final exact-vs-shuffled placement gap
- final exact/shuffled contrast
- exact > shuffled boolean
- `DeltaC / 0.864382` hardware/ideal ratio

For each fabrication seed summarize the five dynamic replicates by:

- count with `DeltaC >= +0.10`
- count with exact > shuffled
- median/min/max `DeltaC`
- median placement gap
- median hardware/ideal improvement ratio

## Frozen interpretation

This is a **diagnostic**, not a replacement formal qualification gate.

- If one fabrication seed is consistently poor across dynamic replicates while others are consistently good, prioritize calibration/fabrication sensitivity.
- If each fabrication seed spans both good and bad dynamic outcomes, prioritize stochastic/thermal margin or a repeat-aware qualification protocol.
- If most or all fabrication seeds are consistently poor, the present v0.9 physical operating point is under-margined and needs architectural/circuit change.
- If most cells are strong and only a small stochastic tail is poor, do not tighten a single analog tolerance without evidence; quantify run-to-run reliability and compare against the ideal task ceiling.

The original red v0.9 fresh result remains red. This factorial may explain it but may not retroactively reclassify it.
