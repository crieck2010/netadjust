"""Parametric weighted least-squares adjustment of 2D horizontal networks.

Method: Gauss-Newton iteration on the nonlinear observation equations.
Unknowns are the free E/N coordinates plus one orientation unknown per
direction setup. Fixed coordinates are held at their given values.

Datum requirement: the normal matrix is singular unless the datum is
defined, e.g. by >= 2 fixed points, or 1 fixed point + a fixed azimuth /
coordinate observations that pin translation, rotation and scale.
A singular system raises DatumDefectError with guidance, never a
silently wrong answer.
"""

from __future__ import annotations

import math

import numpy as np

from .angles import azimuth_rad, wrap_pi, wrap_2pi
from .finalize import finalize_statistics
from .models import (
    AdjustmentResult,
    AngleObs,
    AzimuthObs,
    CoordinateObs,
    DirectionObs,
    DistanceObs,
    Project,
)
from .stats import error_ellipse

TOL_COORD = 1e-7  # convergence: max coordinate correction (project units)
MAX_ITER = 100


class DatumDefectError(RuntimeError):
    """Raised when the network datum is under-defined (singular normals)."""


def _az_partials(de: float, dn: float):
    """Partials of azimuth wrt (E_to, N_to); origin partials are the negatives.

    az = atan2(de, dn); d(az)/dE_to = dn / L^2 ; d(az)/dN_to = -de / L^2.
    """
    l2 = de * de + dn * dn
    if l2 <= 0:
        raise ValueError("Zero-length line in an angle/azimuth/direction observation")
    return dn / l2, -de / l2


def adjust_network_2d(project: Project) -> AdjustmentResult:
    obs = project.obs_2d()
    if not obs:
        raise ValueError("Project has no 2D observations")

    points = project.points

    # --- unknown indexing -------------------------------------------------
    unk: dict[tuple, int] = {}
    for pid, pt in points.items():
        if not pt.fixed_e:
            unk[(pid, "e")] = len(unk)
        if not pt.fixed_n:
            unk[(pid, "n")] = len(unk)
    setups = sorted({o.setup for o in obs if isinstance(o, DirectionObs)})
    for s in setups:
        unk[("setup", s)] = len(unk)
    n_unk = len(unk)

    coords = {pid: [pt.e, pt.n] for pid, pt in points.items()}

    # Initial orientation per setup: circular mean of (azimuth - direction).
    orient: dict[str, float] = {}
    for s in setups:
        diffs = []
        for o in obs:
            if isinstance(o, DirectionObs) and o.setup == s:
                a = points[o.at]
                b = points[o.to]
                diffs.append(wrap_pi(azimuth_rad(b.e - a.e, b.n - a.n) - o.value))
        if diffs:
            orient[s] = math.atan2(
                sum(math.sin(d) for d in diffs), sum(math.cos(d) for d in diffs)
            )
        else:
            orient[s] = 0.0

    def build(crd, ori):
        """Return (A, w, predicted, observed, sigmas, labels, kinds).

        w = observed - predicted, angle-wrapped where applicable; the
        linearized system is A dx ~= w with residuals v = w - A dx.
        """
        rows, w, pred, obsv, sig, labels, kinds = [], [], [], [], [], [], []
        for o in obs:
            row = np.zeros(n_unk)
            if isinstance(o, DistanceObs):
                a, b = crd[o.frm], crd[o.to]
                de, dn = b[0] - a[0], b[1] - a[1]
                dist = math.hypot(de, dn)
                if dist <= 0:
                    raise ValueError(f"Zero-length distance {o.frm}->{o.to}")
                for pid, sgn in ((o.frm, -1.0), (o.to, 1.0)):
                    if (pid, "e") in unk:
                        row[unk[(pid, "e")]] += sgn * de / dist
                    if (pid, "n") in unk:
                        row[unk[(pid, "n")]] += sgn * dn / dist
                p, v = dist, o.value
                mis = v - p
                labels.append(f"dist {o.frm}-{o.to}")
            elif isinstance(o, (AngleObs, AzimuthObs, DirectionObs)):
                if isinstance(o, AngleObs):
                    a = crd[o.at]
                    az_b = azimuth_rad(crd[o.frm][0] - a[0], crd[o.frm][1] - a[1])
                    az_t = azimuth_rad(crd[o.to][0] - a[0], crd[o.to][1] - a[1])
                    p = wrap_2pi(az_t - az_b)
                    pairs = ((o.frm, az_b, -1.0), (o.to, az_t, 1.0))
                    station = o.at
                    for pid, azv, coef in pairs:
                        de = crd[pid][0] - a[0]
                        dn = crd[pid][1] - a[1]
                        d_e, d_n = _az_partials(de, dn)
                        if (pid, "e") in unk:
                            row[unk[(pid, "e")]] += coef * d_e
                        if (pid, "n") in unk:
                            row[unk[(pid, "n")]] += coef * d_n
                        if (station, "e") in unk:
                            row[unk[(station, "e")]] -= coef * d_e
                        if (station, "n") in unk:
                            row[unk[(station, "n")]] -= coef * d_n
                    v = o.value
                    labels.append(f"angle {o.frm}-{o.at}-{o.to}")
                elif isinstance(o, AzimuthObs):
                    a, b = crd[o.frm], crd[o.to]
                    de, dn = b[0] - a[0], b[1] - a[1]
                    p = wrap_2pi(azimuth_rad(de, dn))
                    d_e, d_n = _az_partials(de, dn)
                    if (o.to, "e") in unk:
                        row[unk[(o.to, "e")]] += d_e
                    if (o.to, "n") in unk:
                        row[unk[(o.to, "n")]] += d_n
                    if (o.frm, "e") in unk:
                        row[unk[(o.frm, "e")]] -= d_e
                    if (o.frm, "n") in unk:
                        row[unk[(o.frm, "n")]] -= d_n
                    v = o.value
                    labels.append(f"azimuth {o.frm}-{o.to}")
                else:  # DirectionObs
                    a, b = crd[o.at], crd[o.to]
                    de, dn = b[0] - a[0], b[1] - a[1]
                    p = wrap_2pi(azimuth_rad(de, dn) - ori[o.setup])
                    d_e, d_n = _az_partials(de, dn)
                    if (o.to, "e") in unk:
                        row[unk[(o.to, "e")]] += d_e
                    if (o.to, "n") in unk:
                        row[unk[(o.to, "n")]] += d_n
                    if (o.at, "e") in unk:
                        row[unk[(o.at, "e")]] -= d_e
                    if (o.at, "n") in unk:
                        row[unk[(o.at, "n")]] -= d_n
                    row[unk[("setup", o.setup)]] -= 1.0
                    v = o.value
                    labels.append(f"dir {o.at}-{o.to} [{o.setup}]")
                mis = wrap_pi(v - p)
            elif isinstance(o, CoordinateObs):
                cur = crd[o.point][0 if o.coord == "e" else 1]
                p, v = cur, o.value
                if (o.point, o.coord) in unk:
                    row[unk[(o.point, o.coord)]] = 1.0
                mis = v - p
                labels.append(f"coord {o.point}.{o.coord}")
            else:  # pragma: no cover - obs_2d filters kinds
                continue
            rows.append(row)
            w.append(mis)
            pred.append(p)
            obsv.append(v)
            sig.append(o.sigma)
            kinds.append(o.kind)
        return (
            np.array(rows),
            np.array(w),
            np.array(pred),
            np.array(obsv),
            np.array(sig),
            labels,
            kinds,
        )

    # --- Gauss-Newton iteration ------------------------------------------
    converged = False
    iterations = 0
    for iterations in range(1, MAX_ITER + 1):
        A, w, *_ = build(coords, orient)
        sig_arr = np.array([o.sigma for o in obs])
        Pw = w / sig_arr**2
        N = A.T @ (A / sig_arr[:, None] ** 2)
        rhs = A.T @ Pw
        try:
            dx = np.linalg.solve(N, rhs)
        except np.linalg.LinAlgError as exc:
            raise DatumDefectError(
                "Normal matrix is singular: the network datum is not "
                "defined. Fix at least two points, or one point plus an "
                "azimuth / sufficient coordinate observations, and make "
                "sure every point is connected by observations."
            ) from exc
        max_coord_step = 0.0
        for (key, idx) in unk.items():
            if key[0] == "setup":
                orient[key[1]] = wrap_pi(orient[key[1]] + dx[idx])
            else:
                axis = 0 if key[1] == "e" else 1
                coords[key[0]][axis] += dx[idx]
                max_coord_step = max(max_coord_step, abs(dx[idx]))
        if max_coord_step < TOL_COORD:
            converged = True
            break

    # --- finalize at the solution -----------------------------------------
    A, w, pred, obsv, sig_arr, labels, kinds = build(coords, orient)
    residuals = w - A @ np.zeros(n_unk)  # w at solution IS obs - predicted
    # More precisely residuals = observed - predicted at final coordinates:
    residuals = np.array(
        [wrap_pi(o - p) if k in ("angle", "azimuth", "direction") else o - p
         for o, p, k in zip(obsv, pred, kinds)]
    )
    N = A.T @ (A / sig_arr[:, None] ** 2)
    try:
        qxx = np.linalg.inv(N)
    except np.linalg.LinAlgError as exc:
        raise DatumDefectError("Normal matrix is singular at the solution.") from exc

    stats = finalize_statistics(
        labels=labels,
        kinds=kinds,
        observed=obsv,
        predicted=pred,
        residuals=residuals,
        sigmas=sig_arr,
        a_matrix=A,
        qxx=qxx,
        n_unknowns=n_unk,
    )

    sigma0 = stats["sigma0"]
    cov_scale = (sigma0**2) if sigma0 is not None else 1.0
    cov = cov_scale * qxx

    adjusted: dict[str, dict[str, float]] = {}
    point_sigma: dict[str, dict[str, float]] = {}
    ellipses: dict[str, tuple[float, float, float]] = {}
    for pid in points:
        e_adj, n_adj = coords[pid]
        adjusted[pid] = {"e": e_adj, "n": n_adj}
        cov_en = np.zeros((2, 2))
        s_e = s_n = 0.0
        for axis_i, axis in enumerate(("e", "n")):
            if (pid, axis) in unk:
                var = cov[unk[(pid, axis)], unk[(pid, axis)]]
                if axis == "e":
                    s_e = math.sqrt(max(var, 0.0))
                else:
                    s_n = math.sqrt(max(var, 0.0))
        for ai, aaxis in enumerate(("e", "n")):
            for bi, baxis in enumerate(("e", "n")):
                if (pid, aaxis) in unk and (pid, baxis) in unk:
                    cov_en[ai, bi] = cov[unk[(pid, aaxis)], unk[(pid, baxis)]]
        point_sigma[pid] = {"e": s_e, "n": s_n}
        ellipses[pid] = error_ellipse(cov_en, 0.95)

    warnings = list(stats["warnings"])
    if not converged:
        warnings.append(f"Did not converge in {MAX_ITER} iterations.")
    if abs(stats["redundancy_sum"] - stats["dof"]) > 1e-6 and stats["dof"] > 0:
        warnings.append("Internal check: redundancy numbers do not sum to the dof.")

    return AdjustmentResult(
        dimension="2D",
        project_name=project.name,
        adjusted=adjusted,
        point_sigma=point_sigma,
        ellipses=ellipses,
        observations=stats["observations"],
        n_obs=len(obs),
        n_unknowns=n_unk,
        dof=stats["dof"],
        vtpv=stats["vtpv"],
        sigma0=sigma0,
        chi2_p_value=stats["chi2_p_value"],
        chi2_pass_95=stats["chi2_pass_95"],
        iterations=iterations,
        converged=converged,
        warnings=warnings,
    )
