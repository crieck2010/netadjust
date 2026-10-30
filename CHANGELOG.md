# Changelog

## [0.1.0] — 2026-10-29
- Initial release.
- 2D parametric weighted least-squares network adjustment (Gauss–Newton):
  distances, angles, direction sets with per-setup orientation unknowns,
  azimuths, weighted coordinate observations.
- Separate 1D level-network adjustment: height differences and height observations.
- Full statistics: sigma0, chi-square global test, standardized (Baarda w)
  and studentized residuals, redundancy numbers, covariance, 95% error ellipses.
- Datum-defect detection with actionable error messages.
- JSON and CSV-bundle project files; text/HTML reports; adjusted-coordinate CSV.
- Tkinter desktop app (coordinates, residuals, report, plot) and CLI.
- Worked example network and a validation test suite (closed-form, zero-error,
  Monte-Carlo ellipse-coverage, and blunder-detection tests).
