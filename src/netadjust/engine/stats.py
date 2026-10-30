"""Statistical machinery: incomplete gamma, chi-square, error ellipses.

Implemented in pure Python (Numerical Recipes series / continued fraction)
so the only third-party dependency of the engine stays NumPy.
"""

from __future__ import annotations

import math

import numpy as np


def _gamma_p_series(a: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(1000):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_contfrac(a: float, x: float) -> float:
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / max(b, tiny)
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def regularized_gamma_p(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError("require a > 0 and x >= 0")
    if x == 0:
        return 0.0
    if x < a + 1.0:
        return _gamma_p_series(a, x)
    return 1.0 - _gamma_q_contfrac(a, x)


def chi2_cdf(x: float, dof: int) -> float:
    """P(X <= x) for a chi-square variable with `dof` degrees of freedom."""
    if dof <= 0:
        raise ValueError("dof must be positive")
    return regularized_gamma_p(dof / 2.0, x / 2.0)


def chi2_ppf(p: float, dof: int) -> float:
    """Inverse chi-square CDF by bisection (robust, fast enough for dof < 1e5)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    lo, hi = 0.0, max(float(dof), 1.0)
    while chi2_cdf(hi, dof) < p:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if chi2_cdf(mid, dof) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def error_ellipse(cov_en: np.ndarray, confidence: float = 0.95):
    """Error ellipse from a 2x2 E/N covariance matrix.

    Returns (semi_major, semi_minor, orientation_rad) where orientation is
    the azimuth-style angle of the semi-major axis measured clockwise from
    north, in radians in [0, pi).
    """
    cov = np.asarray(cov_en, dtype=float)
    cov = 0.5 * (cov + cov.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.maximum(eigvals, 0.0)
    factor = chi2_ppf(confidence, 2)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    semi_major = math.sqrt(eigvals[0] * factor)
    semi_minor = math.sqrt(eigvals[1] * factor)
    # Eigenvector components are (E, N); orientation clockwise from north.
    vec = eigvecs[:, 0]
    orientation = math.atan2(vec[0], vec[1]) % math.pi
    return semi_major, semi_minor, orientation
