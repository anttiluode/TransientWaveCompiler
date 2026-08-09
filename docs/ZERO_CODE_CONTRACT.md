# TW-1A exact zero/off contract

Date: 2026-08-09

The v0.1 emulator exposed a requirement that is architectural rather than cosmetic:

> **Zero is a physical program value in TW-1A. It must be represented exactly.**

TW-1A expresses sparse geometry by disabling legal physical grid couplings and expresses finite waveforms using genuinely silent time intervals. A converter that cannot represent zero changes the graph and the program.

Therefore every TW-1A backend claiming sparse-program equivalence must provide exact zero for:

```text
programmable reciprocal edge coupling
programmable diagonal/onsite correction when zero is legal
input DAC sample
error/adjoint DAC sample
ADC/sense code
local update increment when no update is requested
```

## Signed v0.2 code convention

The emulator and first logical hardware target use a symmetric signed mid-tread code:

```text
K = 2^(B-1)-1
integer code = -K ... -1, 0, +1 ... +K
analog value = code * full_scale/K
```

One nominal two's-complement endpoint is unused.

The important invariant is

```text
quantize(0) = 0
```

not the particular binary encoding.

## Physical edge OFF state

A fabrication backend may implement an inactive edge using either:

1. a true switch/disconnect state separate from the graded coupling DAC; or
2. a graded coupling element whose calibrated transfer includes an exact/null state below the backend's allowed residual-coupling tolerance.

The compiler must know which semantic the backend provides.

A backend that has unavoidable residual coupling must not silently treat it as zero. It must instead expose a parasitic-coupling model/tolerance so the physical compiler can re-verify the program under that residual graph.

## Why this matters

The invalid v0.1 emulator used an endpoint quantizer whose zero lay between codes. As a result, every disabled 8x8 grid edge became a weak spring and every silent DAC sample became weak forcing. Coarser bit depth then changed the topology more strongly, producing a false non-monotone "5-bit sweet spot."

This failure is now a compiler lesson:

```text
sparsity is not metadata;
OFF is one of the machine's numerical states.
```

Future physical backends must include a zero/off compliance test in calibration and CI/emulation.
