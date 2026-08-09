# Prior-art boundary

This file exists to stop TransientWaveCompiler from gradually claiming broad ideas that already have clear precedent.

It is not a complete literature review.

## Physical adjoint / in-situ gradient measurement

**Hughes, Minkov, Shi & Fan, Optica 5, 864–871 (2018), _Training of photonic neural networks through in situ backpropagation and gradient measurement_.**

Established in-situ adjoint/backpropagation for photonic neural networks and physical gradient acquisition using internal intensity measurements.

TWC therefore does not claim:

```text
physical adjoint propagation
local interference/intensity measurement of gradients
same-device forward/backward gradient acquisition
```

Related experimental milestone:

**Pai et al., Science 380, 398–404 (2023), _Experimentally realized in situ backpropagation for deep learning in photonic neural networks_.**

And more recently:

**Ashtiani, Idjadi & Kim, Nature 651, 927–932 (2026), _Integrated photonic neural network with on-chip backpropagation training_.**

This demonstrates end-to-end gradient-descent backpropagation on an integrated photonic neural-network chip. TWC therefore cannot use “training physically/on-chip with backpropagation” as a novelty claim.

---

## Hamiltonian echo learning

**López-Pastor & Marquardt, Physical Review X 13, 031020 (2023), _Self-Learning Machines Based on Hamiltonian Echo Backpropagation_.**

Introduces Hamiltonian Echo Backpropagation (HEB): use time-reversible Hamiltonian dynamics, a time-reversal operation, and an injected error perturbation so physical echo dynamics generate learning updates.

TWC therefore does not claim:

```text
physical time-reversal learning
echo-based temporal credit assignment
memory-free backpropagation in a Hamiltonian physical system
```

**Pourcel & Ernoult, NeurIPS 2025, _Learning long range dependencies through time reversal symmetry breaking_.**

Introduces Recurrent Hamiltonian Echo Learning (RHEL). It computes loss gradients as finite differences of physical trajectories of non-dissipative Hamiltonian systems and, in the reported recurrent construction, uses three forward-style passes independent of model size/sequence length.

TWC therefore does not claim constant-pass Hamiltonian BPTT/adjoint equivalence.

---

## Dissipative physical training

**Dal Cin, Marquardt & Wanjura, arXiv:2508.11750 (2025), _Training nonlinear optical neural networks with Scattering Backpropagation_.**

Scattering Backpropagation extracts approximate gradients for nonlinear optical systems using two scattering experiments and is designed for driven-dissipative systems.

TWC therefore does not claim the broad idea of physics-based gradient learning in dissipative wave hardware.

The distinction currently relevant to TWC is that its source problem is a **finite-time transient trajectory**, while Scattering Backpropagation is formulated around scattering/steady-response experiments.

---

## Broadband time-domain adjoints and memory reduction

**Park, Miller & Chung, arXiv:2607.08159 (2026), _Nyquist-Sampled Time-Domain Adjoint FDTD for Memory-Efficient Broadband Nanophotonic Inverse Design_.**

Shows that full time-step forward-field storage is unnecessary for band-limited broadband adjoint FDTD: Nyquist-sampled histories can reproduce gradients while sharply reducing memory.

TWC therefore does not claim:

```text
first reduction of time-domain adjoint history memory
first broadband transient adjoint with compressed temporal storage
```

TWC asks whether a reversible physical echo can **regenerate** the required transient history dynamically for a compilable dissipative recurrence, rather than retaining even a Nyquist-sampled distributed history.

---

## Damping factorization / conformal symplectic structure

Factoring scalar linear damping into a conservative/symplectic core plus a known scaling is standard mathematical territory.

Recent machine-learning examples include:

**Gong, Jin, Kuang, Li & Tang, arXiv:2607.03339 (2026), _CSympNet-ID: conformal-symplectic map learning for linearly damped Hamiltonian systems_.**

This explicitly uses a symplectic core plus damping-scaling layers and develops scaling-conjugacy structure for conformally symplectic maps.

TWC therefore does not claim the scalar exponential damping transform itself.

---

## Physics-aware training

**Wright et al., Nature 601, 549–555 (2022), _Deep physical neural networks trained with backpropagation_.**

Demonstrates physics-aware training across physical systems: physical forward evolution combined with a differentiable digital model for backward gradients.

TWC differs operationally only if the gradient is actually acquired through the physical echo/local-credit protocol rather than supplied by a digital differentiable twin.

---

# Candidate TWC-specific conjunction

The working research boundary is the conjunction below, not any single ingredient:

> **Compile a finite-time dissipative reciprocal wave program into a stable reversible physical recurrence by moving compilable loss into boundary-time schedules; then use an echo of that compiled body to regenerate forward transient history dynamically and acquire broadband local parameter credit with constant-pass edge measurements.**

Even this conjunction is **not asserted novel** until a deeper literature search is complete.

The purpose of the repository is first to make the conjunction precise enough to test and compare.

---

# What would falsify the architectural value

The architecture becomes uninteresting even if its algebra is correct if any of these occur:

1. useful source models almost never satisfy a compilable damping structure;
2. boundary gain grows too quickly for practical sequence lengths;
3. time-mirror/state-restoration cost dominates trajectory-memory savings;
4. local credit cells cost more area/energy than ordinary digital gradient movement;
5. pass-to-pass drift makes +/- subtraction impractical;
6. quantization/noise destroys closed-loop learning;
7. standard digital or physics-aware training wins decisively once total hardware cost is counted;
8. existing echo/adjoint literature already contains the same dissipative-to-reversible compiler construction.

Those are research outcomes, not failures of documentation.