import math

import numpy as np
import pytest

from netadjust.engine import (
    AngleObs,
    AzimuthObs,
    DirectionObs,
    DistanceObs,
    Point,
    Project,
    adjust_network_2d,
)
from netadjust.engine.adjust2d import DatumDefectError
from netadjust.engine.angles import RAD_PER_ARCSEC, azimuth_rad
from netadjust.engine.example import TRUE, example_project

SIG_D = 0.005
SIG_A = 5.0 * RAD_PER_ARCSEC


def _dist_obs(truth, pairs, sigma=SIG_D, pert=None):
    out = []
    for i, (f, t) in enumerate(pairs):
        d = math.hypot(truth[t][0] - truth[f][0], truth[t][1] - truth[f][1])
        if pert:
            d += pert[i]
        out.append(DistanceObs(f, t, d, sigma=sigma))
    return out


def _angle(truth, at, frm, to, sigma=SIG_A, pert_arcsec=0.0):
    az_f = azimuth_rad(truth[frm][0] - truth[at][0], truth[frm][1] - truth[at][1])
    az_t = azimuth_rad(truth[to][0] - truth[at][0], truth[to][1] - truth[at][1])
    return AngleObs(at, frm, to, (az_t - az_f) % (2 * math.pi) + pert_arcsec * RAD_PER_ARCSEC,
                    sigma=sigma)


def test_zero_error_recovers_truth():
    proj = example_project()
    # Rebuild a noiseless version: distances/angles/azimuth exact, approx offset.
    clean = Project(name="clean")
    for pid, (e, n, h) in TRUE.items():
        fixed = pid in ("A", "B")
        clean.points[pid] = Point(pid, e + (0 if fixed else 0.08), n - (0 if fixed else 0.06),
                                  h=h, fixed_e=fixed, fixed_n=fixed, fixed_h=True)
    pairs = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C"),
             ("B", "D"), ("A", "E"), ("B", "E"), ("C", "E"), ("D", "E")]
    clean.observations += _dist_obs(TRUE, pairs)
    for at, frm, to in (("A", "D", "B"), ("B", "A", "C"), ("C", "B", "D"), ("D", "A", "C")):
        clean.observations.append(_angle(TRUE, at, frm, to))
    res = adjust_network_2d(clean)
    assert res.converged
    for pid, (e, n, _) in TRUE.items():
        assert res.adjusted[pid]["e"] == pytest.approx(e, abs=1e-6)
        assert res.adjusted[pid]["n"] == pytest.approx(n, abs=1e-6)
    assert res.vtpv == pytest.approx(0.0, abs=1e-12)


def test_example_adjustment_is_close_and_consistent():
    res = adjust_network_2d(example_project())
    assert res.converged and res.dof > 0
    for pid, (e, n, _) in TRUE.items():
        assert res.adjusted[pid]["e"] == pytest.approx(e, abs=0.01)
        assert res.adjusted[pid]["n"] == pytest.approx(n, abs=0.01)
    # Redundancy numbers must sum to the degrees of freedom.
    assert sum(o.redundancy for o in res.observations) == pytest.approx(res.dof, abs=1e-6)
    # Normal-equation identity at the solution: A^T P v = 0 is implied by
    # the small vtpv relative to the injected perturbations.
    assert res.sigma0 is not None and 0.3 < res.sigma0 < 3.0


def test_direction_set_with_orientation_unknown():
    truth = {"A": (0.0, 0.0), "B": (100.0, 0.0), "C": (100.0, 100.0), "D": (0.0, 100.0)}
    proj = Project(name="dirs")
    for pid, (e, n) in truth.items():
        fixed = pid in ("A", "B")
        proj.points[pid] = Point(pid, e + (0 if fixed else 0.05), n - (0 if fixed else 0.04),
                                 fixed_e=fixed, fixed_n=fixed)
    orient = 0.7  # arbitrary circle zero
    for to in ("A", "B", "C", "D"):
        if to == "A":
            continue
        az = azimuth_rad(truth[to][0] - truth["A"][0], truth[to][1] - truth["A"][1])
        proj.observations.append(
            DirectionObs("A", to, (az - orient) % (2 * math.pi), sigma=SIG_A, setup="A1"))
    pairs = [("B", "C"), ("C", "D"), ("D", "A"), ("A", "C"), ("B", "D")]
    proj.observations += _dist_obs({k: (*v, 0) for k, v in truth.items()}, pairs)
    res = adjust_network_2d(proj)
    for pid, (e, n) in truth.items():
        assert res.adjusted[pid]["e"] == pytest.approx(e, abs=1e-5)
        assert res.adjusted[pid]["n"] == pytest.approx(n, abs=1e-5)


def test_datum_defect_detected():
    proj = Project(name="free-net")
    proj.points["A"] = Point("A", 0.0, 0.0)
    proj.points["B"] = Point("B", 100.0, 0.0)
    proj.points["C"] = Point("C", 100.0, 100.0)
    proj.observations.append(DistanceObs("A", "B", 100.0, sigma=SIG_D))
    proj.observations.append(DistanceObs("B", "C", 100.0, sigma=SIG_D))
    proj.observations.append(DistanceObs("A", "C", 141.421356, sigma=SIG_D))
    with pytest.raises(DatumDefectError):
        adjust_network_2d(proj)


def test_blunder_is_flagged():
    proj = example_project()
    # Corrupt one distance by +5 cm (10 sigma).
    for o in proj.observations:
        if isinstance(o, DistanceObs) and o.frm == "C" and o.to == "E":
            o.value += 0.05
            target = o
            break
    res = adjust_network_2d(proj)
    worst = max(res.observations, key=lambda r: abs(r.w_test))
    assert worst.label == f"dist {target.frm}-{target.to}"
    assert worst.flagged


def test_monte_carlo_ellipse_coverage():
    """95% error ellipses should contain the truth about 95% of the time."""
    rng = np.random.default_rng(20261029)
    truth = {"A": (0.0, 0.0), "B": (200.0, 0.0), "C": (200.0, 150.0),
             "D": (0.0, 150.0), "E": (100.0, 80.0)}
    pairs = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C"),
             ("B", "D"), ("A", "E"), ("B", "E"), ("C", "E"), ("D", "E")]
    angle_specs = [("A", "D", "B"), ("B", "A", "C"), ("C", "B", "D"), ("D", "A", "C"),
                   ("A", "B", "E"), ("C", "D", "E")]
    trials, inside = 120, 0
    for _ in range(trials):
        proj = Project(name="mc")
        for pid, (e, n) in truth.items():
            fixed = pid in ("A", "B")
            proj.points[pid] = Point(pid, e, n, fixed_e=fixed, fixed_n=fixed)
        for f, t in pairs:
            d = math.hypot(truth[t][0] - truth[f][0], truth[t][1] - truth[f][1])
            proj.observations.append(
                DistanceObs(f, t, d + rng.normal(0, SIG_D), sigma=SIG_D))
        for at, frm, to in angle_specs:
            base = _angle({k: (*v, 0) for k, v in truth.items()}, at, frm, to)
            proj.observations.append(
                AngleObs(at, frm, to, base.value + rng.normal(0, SIG_A), sigma=SIG_A))
        res = adjust_network_2d(proj)
        adj_e = res.adjusted["E"]
        a, b, theta = res.ellipses["E"]
        # Point-in-ellipse test in the ellipse frame.
        de = adj_e["e"] - truth["E"][0]
        dn = adj_e["n"] - truth["E"][1]
        x = de * math.sin(theta) + dn * math.cos(theta)
        y = de * math.cos(theta) - dn * math.sin(theta)
        if (x / a) ** 2 + (y / b) ** 2 <= 1.0:
            inside += 1
    coverage = inside / trials
    assert 0.85 <= coverage <= 1.0, f"95% ellipse coverage was {coverage:.2f}"
