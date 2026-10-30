"""Shared post-solution statistics for the 2D and 1D adjusters.

Given the design matrix A at the solution, residuals v (observed - predicted),
a priori sigmas and the cofactor matrix Qxx = (A^T P A)^-1, compute:
  - v^T P v, degrees of freedom, a posteriori sigma0
  - residual cofactors Qvv = P^-1 - A Qxx A^T and redundancy numbers
  - Baarda w-test statistics (a priori scaling) and studentized residuals
  - the chi-square global test of the a priori stochastic model
"""

from __future__ import annotations

import numpy as np

from .models import ObsResult
from .stats import chi2_cdf

W_FLAG_THRESHOLD = 3.29  # two-sided alpha ~= 0.001 for a standard normal


def finalize_statistics(
    *,
    labels: list[str],
    kinds: list[str],
    observed: np.ndarray,
    predicted: np.ndarray,
    residuals: np.ndarray,
    sigmas: np.ndarray,
    a_matrix: np.ndarray,
    qxx: np.ndarray,
    n_unknowns: int,
) -> dict:
    n = len(observed)
    p_diag = 1.0 / sigmas**2
    vtpv = float(np.sum(p_diag * residuals**2))
    dof = n - n_unknowns

    sigma0 = None
    if dof > 0:
        sigma0 = float(np.sqrt(vtpv / dof))

    # Residual cofactor matrix (a priori scaling).
    qvv = np.diag(sigmas**2) - a_matrix @ qxx @ a_matrix.T
    qvv_diag = np.maximum(np.diag(qvv), 0.0)
    redundancy = qvv_diag * p_diag
    sigma_resid = np.sqrt(qvv_diag)

    obs_results: list[ObsResult] = []
    for i in range(n):
        if sigma_resid[i] > 0:
            w_test = float(residuals[i] / sigma_resid[i])
        else:
            w_test = 0.0
        studentized = None
        if sigma0 is not None and sigma0 > 0 and sigma_resid[i] > 0:
            studentized = float(residuals[i] / (sigma0 * sigma_resid[i]))
        obs_results.append(
            ObsResult(
                index=i,
                kind=kinds[i],
                label=labels[i],
                observed=float(observed[i]),
                predicted=float(predicted[i]),
                residual=float(residuals[i]),
                sigma=float(sigmas[i]),
                redundancy=float(redundancy[i]),
                w_test=w_test,
                studentized=studentized,
                flagged=abs(w_test) > W_FLAG_THRESHOLD,
            )
        )

    chi2_p = None
    chi2_pass = None
    if dof > 0:
        chi2_p = float(chi2_cdf(vtpv, dof))
        chi2_pass = bool(0.025 < chi2_p < 0.975)

    warnings: list[str] = []
    if dof == 0:
        warnings.append(
            "Zero redundancy: the solution is exact but no statistical "
            "testing is possible (sigma0 undefined)."
        )
    elif dof < 0:
        warnings.append("Negative degrees of freedom: network is under-determined.")
    if chi2_pass is False:
        warnings.append(
            "Global chi-square test FAILED at 95%: observed residuals are "
            "inconsistent with the a priori sigmas (blunders, optimistic "
            "sigmas, or a datum problem)."
        )
    low = [o.label for o in obs_results if o.redundancy < 0.1]
    if low:
        warnings.append(
            "Observations with redundancy < 0.1 (weak blunder detection): " + ", ".join(low)
        )

    return {
        "observations": obs_results,
        "dof": dof,
        "vtpv": vtpv,
        "sigma0": sigma0,
        "chi2_p_value": chi2_p,
        "chi2_pass_95": chi2_pass,
        "warnings": warnings,
        "redundancy_sum": float(np.sum(redundancy)),
    }
