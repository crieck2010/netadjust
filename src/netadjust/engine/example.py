"""A worked example network: a braced square with a center point.

True coordinates are exact; the stored observations carry small,
deterministic perturbations (a few mm / a few arcseconds) so the
adjustment is a real one with nonzero residuals, and the approximate
coordinates of the free points are offset by ~5 cm, so the iteration
has visible work to do. A and B are held fixed (the datum).
"""

from __future__ import annotations

import math

from .angles import RAD_PER_ARCSEC, azimuth_rad
from .models import (
    AngleObs,
    AzimuthObs,
    DistanceObs,
    HeightDiffObs,
    Point,
    Project,
)

TRUE = {
    "A": (1000.000, 1000.000, 100.000),
    "B": (1200.000, 1000.000, 101.250),
    "C": (1200.000, 1200.000, 102.100),
    "D": (1000.000, 1200.000, 100.850),
    "E": (1103.000, 1097.000, 101.500),
}

# Deterministic observation perturbations (distance in units, angles in arcsec).
_DIST_PERT = [0.006, -0.007, 0.003, 0.008, -0.006, 0.007, -0.004, 0.002, -0.008, 0.006]
_ANG_PERT = [5.0, -4.0, 6.0, -5.0, 4.0, -6.0, 3.0, -2.0]


def example_project() -> Project:
    proj = Project(name="Example: braced square + center point", units="m")
    for pid, (e, n, h) in TRUE.items():
        fixed = pid in ("A", "B")
        off_e, off_n = (0.0, 0.0) if fixed else (0.05, -0.04)
        proj.points[pid] = Point(
            id=pid, e=e + off_e, n=n + off_n, h=h + (0.0 if fixed else 0.02),
            fixed_e=fixed, fixed_n=fixed, fixed_h=(pid == "A"),
        )

    pairs = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C"),
             ("B", "D"), ("A", "E"), ("B", "E"), ("C", "E"), ("D", "E")]
    for i, (f, t) in enumerate(pairs):
        fe, fn, _ = TRUE[f]
        te, tn, _ = TRUE[t]
        dist = math.hypot(te - fe, tn - fn) + _DIST_PERT[i]
        proj.observations.append(DistanceObs(f, t, dist, sigma=0.005))

    # (at, from, to), ordered so each clockwise angle is the interior angle.
    angles = [("A", "D", "B"), ("B", "A", "C"), ("C", "B", "D"), ("D", "C", "A"),
              ("A", "E", "B"), ("B", "E", "C"), ("C", "E", "D"), ("D", "E", "A")]
    for i, (at, frm, to) in enumerate(angles):
        ae, an, _ = TRUE[at]
        az_f = azimuth_rad(TRUE[frm][0] - ae, TRUE[frm][1] - an)
        az_t = azimuth_rad(TRUE[to][0] - ae, TRUE[to][1] - an)
        val = (az_t - az_f) % (2 * math.pi) + _ANG_PERT[i] * RAD_PER_ARCSEC
        proj.observations.append(
            AngleObs(at, frm, to, val, sigma=5.0 * RAD_PER_ARCSEC)
        )

    az_ab = azimuth_rad(TRUE["B"][0] - TRUE["A"][0], TRUE["B"][1] - TRUE["A"][1])
    proj.observations.append(
        AzimuthObs("A", "B", az_ab + 2.0 * RAD_PER_ARCSEC, sigma=3.0 * RAD_PER_ARCSEC)
    )

    # Level loop A-B-C-D-A plus a spur to E (heights from TRUE, mm perturbations).
    dh = [("A", "B", 0.002), ("B", "C", -0.003), ("C", "D", 0.001),
          ("D", "A", -0.002), ("A", "E", 0.003), ("E", "C", -0.001)]
    for f, t, pert in dh:
        proj.observations.append(
            HeightDiffObs(f, t, TRUE[t][2] - TRUE[f][2] + pert, sigma=0.003)
        )
    return proj
