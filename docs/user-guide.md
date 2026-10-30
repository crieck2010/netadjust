# User guide

## Desktop app

1. Launch `NetAdjust.exe` (or `netadjust-app` from a Python install).
2. **Load example** to see a complete run, or **Open project…** for your
   own JSON project file.
3. **Run adjustment.** Tabs:
   - *Adjusted coordinates* — coordinates, sigmas, 95% error ellipses.
   - *Residuals* — every observation with residual, redundancy, w-test.
     Rows marked **CHECK** are suspected blunders (|w| > 3.29).
   - *Report* — the full text report (the record copy).
   - *Plot* — network sketch from the adjusted coordinates.
4. **Save report… / Save adjusted CSV…** for the job file.

## Reading the result — the three checks that matter

1. **Chi-square PASS/FAIL.** FAIL means your a priori sigmas and your
   residuals disagree. Look for blunders first, then honest sigmas
   (a 5″ gun is not a 1″ gun; a distance sigma should be a + b·ppm, not a
   flat guess for every leg).
2. **Flagged observations.** A CHECK row is a *suspect*, not a verdict.
   Check the field notes; if the observation is genuinely bad, remove or
   re-observe it and re-run. Never delete observations just to make the
   test pass — and watch redundancy: an observation with redundancy near
   zero *cannot* be checked by the adjustment at all.
3. **Sigma0 near 1** and ellipses sized for the job's tolerance. Sigma0 far
   above 1 with no flags usually means uniformly optimistic sigmas.

## CLI

```bash
netadjust adjust network.json --out results/
netadjust demo --out demo-out/
```

A project with both horizontal and height observations produces both a
2D and a 1D result from the same file.

Created 2026-10-29 · accompanies NetAdjust v0.1.0
