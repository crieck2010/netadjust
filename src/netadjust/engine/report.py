"""Adjustment reports: plain text (the record copy) and simple HTML."""

from __future__ import annotations

import html
import math

from .. import __version__
from .angles import ARCSEC_PER_RAD, format_dms
from .models import AdjustmentResult, Project

ANGULAR_KINDS = {"angle", "azimuth", "direction"}


def _fmt_obs_value(kind: str, value: float, units: str) -> str:
    if kind in ANGULAR_KINDS:
        return format_dms(value)
    return f"{value:.4f}"


def _fmt_residual(kind: str, residual: float, units: str) -> str:
    if kind in ANGULAR_KINDS:
        return f"{residual * ARCSEC_PER_RAD:+.2f}\""
    return f"{residual:+.4f}"


def render_text(result: AdjustmentResult, project: Project) -> str:
    lines: list[str] = []
    lines.append(f"NetAdjust v{__version__} — Least Squares Adjustment Report")
    lines.append(f"Project: {result.project_name}   Dimension: {result.dimension}   Units: {project.units}")
    lines.append("=" * 78)
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"  Observations: {result.n_obs}   Unknowns: {result.n_unknowns}   "
                 f"Degrees of freedom: {result.dof}")
    lines.append(f"  Iterations: {result.iterations}   Converged: {result.converged}")
    lines.append(f"  v^T P v: {result.vtpv:.4f}")
    if result.sigma0 is not None:
        lines.append(f"  Sigma0 (a posteriori std dev of unit weight): {result.sigma0:.4f}")
    else:
        lines.append("  Sigma0: undefined (zero redundancy)")
    if result.chi2_p_value is not None:
        verdict = "PASS" if result.chi2_pass_95 else "FAIL"
        lines.append(f"  Global chi-square test (95%, two-sided): {verdict} "
                     f"(p = {result.chi2_p_value:.3f})")
    if result.warnings:
        lines.append("")
        lines.append("WARNINGS")
        for w in result.warnings:
            lines.append(f"  ! {w}")
    lines.append("")
    if result.dimension == "2D":
        lines.append("ADJUSTED COORDINATES (95% error ellipse: a = semi-major, b = semi-minor)")
        lines.append(f"  {'Pt':<8}{'E':>14}{'N':>14}{'sigE':>9}{'sigN':>9}"
                     f"{'a(95%)':>10}{'b(95%)':>10}{'theta':>9}")
        for pid, adj in result.adjusted.items():
            sig = result.point_sigma[pid]
            a, b, theta = result.ellipses[pid]
            lines.append(
                f"  {pid:<8}{adj['e']:>14.4f}{adj['n']:>14.4f}"
                f"{sig['e']:>9.4f}{sig['n']:>9.4f}{a:>10.4f}{b:>10.4f}"
                f"{math.degrees(theta):>9.2f}"
            )
    else:
        lines.append("ADJUSTED HEIGHTS")
        lines.append(f"  {'Pt':<8}{'H':>14}{'sigH':>9}")
        for pid, adj in result.adjusted.items():
            sig = result.point_sigma[pid]
            lines.append(f"  {pid:<8}{adj['h']:>14.4f}{sig['h']:>9.4f}")
    lines.append("")
    lines.append("OBSERVATIONS AND RESIDUALS  (flag: |w| > 3.29, Baarda data snooping)")
    lines.append(f"  {'#':>3} {'Observation':<28}{'Observed':>16}{'Residual':>11}"
                 f"{'Redund':>8}{'w-test':>8}  Flag")
    for o in result.observations:
        flag = "  <-- CHECK" if o.flagged else ""
        lines.append(
            f"  {o.index + 1:>3} {o.label:<28}"
            f"{_fmt_obs_value(o.kind, o.observed, project.units):>16}"
            f"{_fmt_residual(o.kind, o.residual, project.units):>11}"
            f"{o.redundancy:>8.3f}{o.w_test:>8.2f}{flag}"
        )
    lines.append("")
    lines.append("Notes: residuals are observed - predicted at the adjusted coordinates.")
    lines.append("Angular residuals are in arcseconds; linear residuals in project units.")
    lines.append("Point sigmas and ellipses use the a posteriori sigma0 when redundancy > 0.")
    return "\n".join(lines) + "\n"


def render_html(result: AdjustmentResult, project: Project) -> str:
    text = render_text(result, project)
    return (
        "<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
        f"<title>NetAdjust report — {html.escape(result.project_name)}</title>"
        "<style>body{font-family:ui-monospace,Menlo,Consolas,monospace;"
        "margin:2rem;white-space:pre-wrap}</style></head><body>"
        + html.escape(text)
        + "</body></html>\n"
    )


def adjusted_csv(result: AdjustmentResult) -> str:
    rows = []
    if result.dimension == "2D":
        rows.append("point,e,n,sigma_e,sigma_n,ellipse_a_95,ellipse_b_95,ellipse_theta_deg")
        for pid, adj in result.adjusted.items():
            sig = result.point_sigma[pid]
            a, b, theta = result.ellipses[pid]
            rows.append(
                f"{pid},{adj['e']:.4f},{adj['n']:.4f},{sig['e']:.4f},{sig['n']:.4f},"
                f"{a:.4f},{b:.4f},{math.degrees(theta):.2f}"
            )
    else:
        rows.append("point,h,sigma_h")
        for pid, adj in result.adjusted.items():
            rows.append(f"{pid},{adj['h']:.4f},{result.point_sigma[pid]['h']:.4f}")
    return "\n".join(rows) + "\n"
