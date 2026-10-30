# Input format

A project is either a single JSON file or a CSV bundle (a folder with
`points.csv` and `observations.csv`, same field names as columns).

## Points

| field | meaning |
|---|---|
| `id` | point name (required) |
| `e`, `n` | approximate easting/northing (required for 2D) |
| `h` | approximate height (required for points used in height obs) |
| `fixed_e`, `fixed_n`, `fixed_h` | hold this coordinate fixed |

Approximations for free points should be within a metre or so of the final
values — the iteration is robust, but gross approximations slow convergence.
Fixed points define the datum: fix at least two points, or one point plus
an azimuth / enough coordinate observations.

## Observations

Common fields: `type`, `sigma` (linear observations, in project units).

| type | fields | notes |
|---|---|---|
| `distance` | `from`, `to`, `value`, `sigma` | horizontal distance |
| `angle` | `at`, `from`, `to`, angle value, `sigma_arcsec` | clockwise angle from backsight to foresight |
| `direction` | `at`, `to`, `setup`, angle value, `sigma_arcsec` | all directions with the same `setup` share one orientation unknown |
| `azimuth` | `from`, `to`, angle value, `sigma_arcsec` | |
| `coordinate` | `point`, `coord` (`e`/`n`), `value`, `sigma` | weighted prior on a coordinate |
| `height_diff` | `from`, `to`, `value`, `sigma` | h(to) − h(from) |
| `height` | `point`, `value`, `sigma` | weighted height prior |

Angle values: give exactly one of `value_deg` (decimal degrees),
`value_dms` (`"123-45-30.5"` or `"123°45'30.5\""`), or `value_rad`.
Angular sigmas: `sigma_arcsec` or `sigma_rad`.

## Outputs

- `*-report.txt` / `*-report.html` — full report: summary, global test,
  adjusted coordinates with sigmas and 95% ellipses, residual table with
  redundancy and w-test flags, warnings.
- `*-adjusted.csv` — machine-readable adjusted coordinates.

Created 2026-10-29 · accompanies NetAdjust v0.1.0
