# TW-1A v0.8 common/difference diagnostic result

The preregistered spent-body diagnostic in
`CIRCUIT_V08_COMMON_DIFF_DIAGNOSTIC_PREREG.md` passed both frozen conditions on
seeds 2000--2009.

## Result

```text
condition             >=+0.10   wins   median DeltaC   min DeltaC   median gap
common_diff_b0          10/10   10/10      +0.427209    +0.119830    +0.447530
common_diff_b1e-5       10/10   10/10      +0.350922    +0.124487    +0.432461
```

The v0.7 failed-tail seeds at the thermal operating point became:

```text
seed 2006   DeltaC +0.382859
seed 2007   DeltaC +0.318984
seed 2008   DeltaC +0.134420
```

For comparison, the failed fresh v0.7 gate on the same task bodies had roughly
`+0.015 / +0.025 / +0.077` for those three seeds.

## Interpretation

The controlled v0.7 pair split predicted that removing terminal-clone residual
and +/- error-DAC sign asymmetry together was sufficient to restore the hard
task tail. v0.8 realizes that pair as a coordinate change rather than as tighter
analog specifications:

```text
C = (PLUS+MINUS)/2 = retraced forward field F
D = (PLUS-MINUS)/2 = returned adjoint field A
```

The terminal boundary is therefore

```text
C <- mirrored forward state already present
D <- exact zero
```

and one signed error waveform drives D. No arbitrary analog terminal state copy
and no matched bipolar error injection pair are required.

The local credit path still evaluates the exact old fields transiently at the
sensor:

```text
delta_plus  = delta_C + delta_D
delta_minus = delta_C - delta_D
credit = (square(delta_plus)-square(delta_minus))/4.
```

This is a diagnostic result on spent bodies, not a fresh qualification. It is
sufficient evidence to make common/difference reverse coordinates the working
v0.8 architecture and move on to explicit fabrication headroom/residual budgets.
