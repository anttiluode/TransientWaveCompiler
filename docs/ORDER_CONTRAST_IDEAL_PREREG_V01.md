# TW-1A temporal-order contrast benchmark — ideal preregistration v0.1

Date frozen: 2026-08-09

## Why this benchmark exists

The first noisy-emulator benchmark minimized quadratic energy at one distal output. That task was unsuitable for proving local physical credit because a norm-matched shuffled update could often improve the objective simply by weakening or detuning transmission anywhere in the arbor.

This preregistration replaces that task **before inspecting any result from the new task family**.

The new benchmark asks the wave medium to discriminate temporal order while holding event content and total input energy fixed.

## Task family

For each seed, grow the existing 40-active-cell irregular four-neighbor tree on the 8x8 TW-1A tile.

- root / sense node: physical node 0
- choose two distinct non-root leaves A and B deterministically from the tree, preferring pairs that are both distal from the root and far apart from each other
- target sequence AB: identical unit-energy event at A at `t_early`, then the same event at B at `t_late`
- distractor sequence BA: the same two events with their times exchanged
- the two sequences therefore contain exactly the same event waveforms, amplitudes, source nodes, and total input energy; only temporal order differs
- both sequences use the same Q, trainable edge list, damping gauge, root sense port, and hardware configuration

Frozen numerical task parameters:

- active cells: 40
- steps: 96
- dt: 0.08
- gamma: 0.40
- active onsite stiffness: 1.0
- physical edge stiffness initial value: 10.0
- trainable stiffness range: [2.0, 18.0]
- parked-cell onsite stiffness: 10.0
- event amplitude: 6.0
- event waveform: one-sample impulse
- early event tick: 4
- late event tick: 20

## Objective

Let `E_AB` and `E_BA` be the compiled quadratic root-output energies measured by two ordinary TW-1A four-pass programs.

The host objective is normalized contrast

`C = (E_AB - E_BA) / (E_AB + E_BA + eps)`

with `eps = 1e-30`.

The learner **maximizes** C.

No new analog gradient primitive is introduced. Each sequence produces the existing local physical edge-energy credit. The host combines them using the exact chain rule:

`dC/dtheta = [2 E_BA / S^2] dE_AB/dtheta - [2 E_AB / S^2] dE_BA/dtheta`,

where `S = E_AB + E_BA + eps`.

The physical implementation therefore remains two ordinary four-pass energy-gradient measurements per contrast update.

## Ideal-machine gate

The first experiment is intentionally hardware-ideal:

- weight quantization: disabled
- DAC quantization: disabled
- ADC quantization: disabled
- state noise: 0
- leakage: 0
- mirror error: 0
- differential +/- pass drift: 0
- local credit offset/noise: 0
- state clipping: disabled

Optimizer is frozen:

- iterations: 40
- host step size: 0.20
- RMS-normalized combined contrast gradient
- one fixed norm-matched shuffled-credit permutation per seed

## Holdout seeds

The ideal qualification seeds are frozen as:

`840, 841, 842, 843, 844, 845, 846, 847, 848, 849`

They must not be used to alter task parameters, optimizer settings, leaf selection, event timing, or thresholds.

Implementation/algebra debugging may use already-seen earlier seeds, but not 840–849.

## Shuffled-credit control

At every iteration the control receives the **same combined physical contrast-gradient values** as the exact learner, with one frozen edge permutation.

Thus update norm and marginal gradient distribution are identical; only edge placement is destroyed.

The control uses the same initial Q and deterministic task pair.

## Kill thresholds

The ideal temporal-order benchmark qualifies only if **all** of the following hold across the 10 frozen seeds:

1. every exact learner has positive contrast improvement `DeltaC_exact > 0`;
2. at least 8/10 seeds have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast exceeds shuffled final contrast in at least 8/10 seeds;
5. median `(DeltaC_exact - DeltaC_shuffle) >= 0.10`;
6. all energies, contrasts, gradients, and parameters remain finite.

A separate clean algebra test must also show the physically combined contrast gradient matches finite differences with correlation > 0.999999 and relative L2 error < 2e-5 on a non-holdout seed.

## Decision rule

If the ideal benchmark fails, **do not resume bit/leakage/mirror/drift requirement sweeps**. Diagnose the task/credit mechanism first.

If it passes, the next preregistered stage may add sense-port range control and then re-open the hardware-requirements envelope on a new untouched seed block.
