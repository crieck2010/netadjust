# Theory — what NetAdjust solves

## Model

Parametric least squares. Each observation *lᵢ* with a priori standard
deviation *σᵢ* is a known nonlinear function of the unknown parameters
(point coordinates, plus one orientation unknown per direction setup):

    lᵢ + vᵢ = fᵢ(x)

Linearizing about approximations x₀ gives **A dx ≈ w**, with
w = l − f(x₀), weights **P = diag(1/σᵢ²)**, and the weighted solution

    dx = (Aᵀ P A)⁻¹ Aᵀ P w

The 2D adjuster iterates (Gauss–Newton) until the largest coordinate
correction is below 1e-7 project units. The 1D problem is linear and is
solved in one step.

Observation equations and their partials:

- **Distance** i→j: f = √(ΔE² + ΔN²); partials ±ΔE/f, ±ΔN/f.
- **Azimuth** i→j: f = atan2(ΔE, ΔN); ∂az/∂Eⱼ = ΔN/L², ∂az/∂Nⱼ = −ΔE/L²,
  origin partials negated.
- **Angle** at a, from b to c: f = (az(a→c) − az(a→b)) mod 360°.
- **Direction** at a to b, setup s: f = az(a→b) − zₛ, where zₛ is the
  setup's orientation unknown (∂f/∂zₛ = −1), initialized by the circular
  mean of (azimuth − direction).
- **Coordinate observation**: f = the coordinate itself (a weighted prior).
- **Height difference**: f = hⱼ − hᵢ. **Height observation**: f = hᵢ.

## Statistics

At the solution, with residuals **v = l − f(x̂)** and cofactor
**Qxx = (Aᵀ P A)⁻¹**:

- **vᵀPv** and **sigma0² = vᵀPv / r**, r = n − u (degrees of freedom).
- **Global test**: vᵀPv is compared with the χ² distribution on r degrees
  of freedom (two-sided 95%). Failure means the residuals are inconsistent
  with the a priori sigmas — blunders, optimistic sigmas, or a datum issue.
  (Failing on the *low* side means sigmas were pessimistic or residuals are
  suspiciously small.)
- **Residual cofactor** Qvv = P⁻¹ − A Qxx Aᵀ. **Redundancy numbers**
  rᵢ = Qvv,ᵢᵢ · Pᵢᵢ sum to r — used as an internal consistency check in tests.
- **Baarda w-test** (data snooping): wᵢ = vᵢ / √Qvv,ᵢᵢ is standard normal
  under the null; |wᵢ| > 3.29 (α ≈ 0.001) flags a suspected blunder.
- **Covariance** of adjusted coordinates: Cx = sigma0² · Qxx.
- **Error ellipses**: from each point's 2×2 block of Cx; semi-axes are
  √(eigenvalue · χ²₂,conf). Studentized residuals divide vᵢ by
  sigma0·√Qvv,ᵢᵢ instead of the a priori √Qvv,ᵢᵢ.

## Datum

Distances, angles and directions determine a network up to translation,
rotation and (for angle/direction-only nets) scale. Without constraints the
normal matrix is singular; NetAdjust detects this and raises
`DatumDefectError` explaining the fix rather than returning coordinates
from a pseudo-inverse that hides the defect.

Created 2026-10-29 · accompanies NetAdjust v0.1.0
