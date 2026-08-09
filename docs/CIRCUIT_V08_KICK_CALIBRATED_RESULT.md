# TW-1A v0.8 kick-calibrated fresh qualification result

The preregistered fresh gate in
`CIRCUIT_V08_KICK_CALIBRATED_PREREG.md` passed on untouched temporal-order
bodies 2200--2209.

## Qualified operating point

```text
reverse representation                   common/difference C=F, D=A
active virtual charge summing            yes
structural -PREV                          yes
terminal analog clone                    absent
matched +/- error injection              absent
edge unit-cap mismatch                    3% RMS
site-common Cunit/Cstate mismatch         1% RMS
nominal positive edge range               0.265
edge thermal base b                       1e-5
kick-cancellation measurement error       0.5% RMS
independent common kick floor             2e-6 state FS RMS
independent differential kick floor       1e-6 state FS RMS
training iterations                       30
step size                                 0.20
```

All other retained mixed-signal background values are those frozen in the
preregistration.

## Result

```text
fabrication pass                         10/10
improvement >= +0.10                     10/10
final exact > shuffled                   10/10
median improvement                       +0.559700
minimum improvement                      +0.165905
median placement gap                     +0.442903
minimum placement gap                    +0.210940
minimum observed edge full scale          0.256587
mean common residual kick RMS             2.433e-6 state FS
mean differential residual kick RMS       1.123e-6 state FS
```

Per-body improvements were all positive and comfortably above the frozen
+0.10 floor. The weakest fresh body, seed 2202, improved by +0.165905.

## What this qualifies

This is a fresh **emulator-level qualification** of the v0.8 physical contract.
It includes simultaneously:

- measured site-specific nonlinear edge capacitor codebooks;
- 3% unit-cap mismatch and 1% site-common ratio mismatch;
- active-integrator edge thermal packets;
- common/difference reverse coordinates;
- structural history coefficient;
- retained C/D hold mismatch, self calibration, state leakage, converters,
  square/LCC curvature, credit noise/offset/leakage;
- the measured 0.5% foreground switch-kick cancellation requirement with the
  existing 2 ppm / 1 ppm residual floors.

It does **not** qualify a transistor OTA, self actuator, local square sensor,
clock generator or foundry layout.

## Current circuit bottleneck

The restored C1 ngspice ladder now separates the remaining active-integrator
problem cleanly:

- C1b rejects passive state-dependent charge sharing;
- C1c proves state-independent active packet summing;
- C1d shows the 0.1% static marker needs only about A0=3e3 for an edge packet
  and A0=3e4 for the worst unsliced |self|=3 load;
- C1e shows the 20 ns edge packet passes at 100 MHz GBW, while a monolithic
  `Cin/Cf=3` self packet still misses the 0.1% settling marker at 1 GHz.

The next circuit question is therefore **self-path packetization/slicing**, not
further tightening of the already-qualified edge body.
