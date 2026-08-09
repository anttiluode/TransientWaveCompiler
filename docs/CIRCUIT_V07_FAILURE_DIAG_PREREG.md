# TW-1A v0.7 formal-failure diagnosis

Status: **diagnostic only; seeds 2000--2009 are spent by the failed formal gate**.

The fresh v0.7 gate failed because only 7/10 bodies achieved improvement >=
+0.10 even though 10/10 fabricated tiles passed monotonicity/headroom and 10/10
finished above shuffled credit.  This diagnostic is frozen before observing any
additional result on those seeds.

## Fixed condition set

The diagnostic runs exactly these conditions on seeds 2000--2009:

1. `formal` — exact failed v0.7 conditions (`b=1e-5`).
2. `no_thermal` — v0.7 unchanged except `b=0`.
3. `ideal_edge_bank` — `b=0`, unit-cap sigma 0, edge codebook calibration error
   0, A/B edge-hold mismatch 0.
4. `clean_quantized_v07` — condition 3 plus zero state leakage, zero self gain
   mismatch/calibration error, perfect terminal clone, zero switch-kick
   residuals, zero error-DAC sign asymmetry, ideal LCC, and zero credit
   noise/offset/leakage. Converter widths remain frozen at the formal values.
5. `clean_precision_v07` — condition 4 with weight/drive/sense/error quantizers
   disabled where supported, to separate converter resolution from the active
   coefficient representation.
6. `old_c0e_formal` — the previous qualified C0e physical model at `b=1e-5` on
   the same now-spent task seeds.
7. `old_c0e_no_thermal` — previous C0e model with edge thermal base set to 0.

No conditions are added or removed after seeing results.

## Readout

For each condition report:

- count with improvement >= +0.10;
- count beating shuffled credit;
- median/minimum improvement;
- median/minimum placement gap;
- per-seed improvement for the failed-tail seeds 2006, 2007 and 2008.

## Interpretation

- `no_thermal` rescue => thermal margin was not portable from spent 1800--1809.
- `ideal_edge_bank` rescue => active edge fabrication/codebook residual is the
  dominant interaction.
- `clean_quantized_v07` rescue => some retained C0e background block is the
  dominant interaction.
- only `clean_precision_v07` rescue => converter/code-lattice resolution is the
  limiting interaction.
- old C0e also fails the same seeds => the formal failure is primarily task-tail
  generalization rather than the active-summing substitution.

No fresh qualification seeds are reserved until this diagnosis is complete.
