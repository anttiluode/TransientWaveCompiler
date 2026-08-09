# TW-1A v0.8 edge/self thermal path split — result

Date: 2026-08-09

Status: **diagnostic on spent bodies 2300..2309. Self sampling is the thermal bottleneck. No fresh seed authorized.**

Preregistration: `docs/CIRCUIT_V08_THERMAL_PATH_SPLIT_PREREG.md`

The combined thermal sweep had already shown that tying both edge and self sampling to `b=2e-5` fails. This split changed only one path at a time on the same static silicon and the same underlying thermal RNG streams.

## Frozen predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Results

| edge b | self b | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1e-5 | 1e-5 | 10/10 | 10/10 | +0.396735 | +0.150625 | +0.310108 | YES |
| 2e-5 | 1e-5 | 10/10 | 10/10 | +0.364810 | +0.159801 | +0.268236 | YES |
| 3e-5 | 1e-5 | 9/10 | 10/10 | +0.242390 | +0.008843 | +0.202290 | NO |
| 5e-5 | 1e-5 | 8/10 | 10/10 | +0.176120 | +0.009267 | +0.162252 | NO |
| 1e-5 | 2e-5 | 5/10 | 10/10 | +0.100568 | -0.000296 | +0.096932 | NO |
| 1e-5 | 3e-5 | 2/10 | 10/10 | +0.056391 | +0.003552 | +0.050784 | NO |
| 1e-5 | 5e-5 | 1/10 | 6/10 | +0.017304 | -0.022409 | +0.013819 | NO |

## Interpretation

The preregistered diagnosis is therefore:

```text
self_sampling_bottleneck
```

The reciprocal edge sampling path has real thermal margin: doubling its base RMS while leaving self sampling at the fresh-qualified value still clears every frozen predicate. The node-local self path does not have comparable margin.

This is especially important for area reasoning. The current one-knob model makes `Cstate` set both thermal bases, but the evidence does **not** support paying the same capacitance penalty to both paths. Any next circuit revision should either:

1. reduce/remove the near-2 node-local self sampling operation structurally;
2. give self sampling a different physical noise/energy tradeoff from the edge/state resource; or
3. trade repeated physical measurements for self-noise averaging before simply enlarging the whole tile.

The result does not by itself prove that state storage can be shrunk independently: OTA/state-hold noise is not yet transistor-qualified. It does prove that, within the current sampled-capacitor emulator, **self sampling—not reciprocal edge sampling—is the first kT/C wall.**

## Next architectural probe

For the compiled continuous-wave source class,

```text
Q = [(1+a) I - dt^2 H] / sqrt(a).
```

After the graph Laplacian is represented by reciprocal rank-one edge cells, most of the remaining self coefficient is the universal inertial term near +2. The exact coordinate change

```text
p[n] = z[n] - z[n-1]
K = Q - 2 I

p[n+1] = p[n] + K z[n] + u[n]
z[n+1] = z[n] + p[n+1]
```

moves that universal +2 out of the programmable operator while leaving every edge derivative unchanged. `transientwave/kick_drift.py` and the v0.9 self audit test this algebra before any new circuit claim is made.
