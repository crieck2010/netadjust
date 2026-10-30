"""Weighted least-squares adjustment of 1D level (height) networks.

Linear observation equations, so the solution is direct (no iteration):
  height difference:  h_to - h_frm = observed
  height observation: h_point      = observed
Fixed heights are held. At least one height must be fixed or observed
with weight, otherwise the datum is undefined and DatumDefectError is raised.
"""

from __future__ import annotations

import math

import numpy as np

from .adjust2d import DatumDefectError
from .finalize import finalize_statistics
from .models import AdjustmentResult, HeightDiffObs, HeightObs, Project


def adjust_level_network(project: Project) -> AdjustmentResult:
    obs = project.obs_1d()
    if not obs:
        raise ValueError("Project has no height observations")
    points = project.points
    for o in obs:
        for pid in ([o.frm, o.to] if isinstance(o, HeightDiffObs) else [o.point]):
            if points[pid].h is None:
                raise ValueError(f"Point {pid} needs an approximate height")

    unk: dict[str, int] = {}
    for pid, pt in points.items():
        involved = any(
            (isinstance(o, HeightDiffObs) and pid in (o.frm, o.to))
            or (isinstance(o, HeightObs) and o.point == pid)
            for o in obs
        )
        if involved and not pt.fixed_h:
            unk[pid] = len(unk)
    n_unk = len(unk)

    rows, obsv, sig, labels, kinds = [], [], [], [], []
    for o in obs:
        row = np.zeros(n_unk)
        if isinstance(o, HeightDiffObs):
            if o.to in unk:
                row[unk[o.to]] += 1.0
            if o.frm in unk:
                row[unk[o.frm]] -= 1.0
            approx = points[o.to].h - points[o.frm].h
            labels.append(f"dh {o.frm}-{o.to}")
        else:
            if o.point in unk:
                row[unk[o.point]] = 1.0
            approx = points[o.point].h
            labels.append(f"height {o.point}")
        rows.append(row)
        obsv.append(o.value)
        sig.append(o.sigma)
        kinds.append(o.kind)
        # misclosure computed against approximations below via A x0
        _ = approx

    A = np.array(rows)
    obsv = np.array(obsv)
    sig = np.array(sig)
    x0 = np.array([points[pid].h for pid, _ in sorted(unk.items(), key=lambda kv: kv[1])])
    # Predicted at approximations for all points (fixed included):
    pred0 = []
    for o in obs:
        if isinstance(o, HeightDiffObs):
            pred0.append(points[o.to].h - points[o.frm].h)
        else:
            pred0.append(points[o.point].h)
    w = obsv - np.array(pred0)

    N = A.T @ (A / sig[:, None] ** 2)
    rhs = A.T @ (w / sig**2)
    try:
        qxx = np.linalg.inv(N)
        dx = qxx @ rhs
    except np.linalg.LinAlgError as exc:
        raise DatumDefectError(
            "Level network datum is undefined: fix at least one height "
            "or add a weighted height observation."
        ) from exc

    heights = {pid: pt.h for pid, pt in points.items() if pt.h is not None}
    for pid, idx in unk.items():
        heights[pid] = points[pid].h + dx[idx]

    pred_final = []
    for o in obs:
        if isinstance(o, HeightDiffObs):
            pred_final.append(heights[o.to] - heights[o.frm])
        else:
            pred_final.append(heights[o.point])
    pred_final = np.array(pred_final)
    residuals = obsv - pred_final

    stats = finalize_statistics(
        labels=labels,
        kinds=kinds,
        observed=obsv,
        predicted=pred_final,
        residuals=residuals,
        sigmas=sig,
        a_matrix=A,
        qxx=qxx,
        n_unknowns=n_unk,
    )

    sigma0 = stats["sigma0"]
    cov_scale = (sigma0**2) if sigma0 is not None else 1.0
    adjusted = {pid: {"h": h} for pid, h in heights.items()}
    point_sigma = {}
    for pid in heights:
        if pid in unk:
            var = cov_scale * qxx[unk[pid], unk[pid]]
            point_sigma[pid] = {"h": math.sqrt(max(var, 0.0))}
        else:
            point_sigma[pid] = {"h": 0.0}

    return AdjustmentResult(
        dimension="1D",
        project_name=project.name,
        adjusted=adjusted,
        point_sigma=point_sigma,
        ellipses={},
        observations=stats["observations"],
        n_obs=len(obs),
        n_unknowns=n_unk,
        dof=stats["dof"],
        vtpv=stats["vtpv"],
        sigma0=sigma0,
        chi2_p_value=stats["chi2_p_value"],
        chi2_pass_95=stats["chi2_pass_95"],
        iterations=1,
        converged=True,
        warnings=list(stats["warnings"]),
    )
