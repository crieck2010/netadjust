"""Project file I/O: JSON project files and CSV bundles.

JSON format (angles in decimal degrees, DMS strings, or explicit radians)::

    {
      "name": "Control loop", "units": "m",
      "points": [{"id": "A", "e": 1000.0, "n": 1000.0, "h": 100.0,
                  "fixed_e": true, "fixed_n": true, "fixed_h": true}],
      "observations": [
        {"type": "distance", "from": "A", "to": "B", "value": 200.0, "sigma": 0.005},
        {"type": "angle", "at": "B", "from": "A", "to": "C",
         "value_dms": "90-00-10", "sigma_arcsec": 5},
        {"type": "direction", "at": "B", "to": "C", "setup": "B1",
         "value_deg": 12.5, "sigma_arcsec": 5},
        {"type": "azimuth", "from": "A", "to": "B", "value_deg": 90.0, "sigma_arcsec": 3},
        {"type": "coordinate", "point": "A", "coord": "e", "value": 1000.0, "sigma": 0.002},
        {"type": "height_diff", "from": "A", "to": "B", "value": 1.234, "sigma": 0.002},
        {"type": "height", "point": "B", "value": 101.234, "sigma": 0.003}
      ]
    }

CSV bundle: a directory (or a points.csv path) containing points.csv and
observations.csv with the same field names as columns; angle values go in
`value_deg` or `value_dms`, angular sigmas in `sigma_arcsec`.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from .angles import RAD_PER_ARCSEC, parse_angle
from .models import (
    AngleObs,
    AzimuthObs,
    CoordinateObs,
    DirectionObs,
    DistanceObs,
    HeightDiffObs,
    HeightObs,
    Point,
    Project,
)


def _angle_value(d: dict) -> float:
    if "value_rad" in d:
        return float(d["value_rad"])
    if "value_dms" in d and d["value_dms"] not in ("", None):
        return parse_angle(d["value_dms"])
    return parse_angle(d["value_deg"])


def _angle_sigma(d: dict) -> float:
    if "sigma_rad" in d:
        return float(d["sigma_rad"])
    return float(d["sigma_arcsec"]) * RAD_PER_ARCSEC


def _obs_from_dict(d: dict):
    t = d["type"]
    if t == "distance":
        return DistanceObs(d["from"], d["to"], float(d["value"]), float(d["sigma"]))
    if t == "angle":
        return AngleObs(d["at"], d["from"], d["to"], _angle_value(d), _angle_sigma(d))
    if t == "direction":
        return DirectionObs(
            d["at"], d["to"], _angle_value(d), _angle_sigma(d), setup=d.get("setup", "S1")
        )
    if t == "azimuth":
        return AzimuthObs(d["from"], d["to"], _angle_value(d), _angle_sigma(d))
    if t == "coordinate":
        return CoordinateObs(d["point"], d["coord"], float(d["value"]), float(d["sigma"]))
    if t == "height_diff":
        return HeightDiffObs(d["from"], d["to"], float(d["value"]), float(d["sigma"]))
    if t == "height":
        return HeightObs(d["point"], float(d["value"]), float(d["sigma"]))
    raise ValueError(f"Unknown observation type: {t!r}")


def _point_from_dict(d: dict) -> Point:
    return Point(
        id=str(d["id"]),
        e=float(d.get("e", 0.0)),
        n=float(d.get("n", 0.0)),
        h=(float(d["h"]) if d.get("h") not in (None, "") else None),
        fixed_e=bool(d.get("fixed_e", False)),
        fixed_n=bool(d.get("fixed_n", False)),
        fixed_h=bool(d.get("fixed_h", False)),
    )


def project_from_dict(data: dict) -> Project:
    proj = Project(name=data.get("name", "Untitled network"), units=data.get("units", "m"))
    for pd in data.get("points", []):
        pt = _point_from_dict(pd)
        proj.points[pt.id] = pt
    for od in data.get("observations", []):
        proj.observations.append(_obs_from_dict(od))
    return proj


def load_project(path: str | Path) -> Project:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return project_from_dict(json.loads(path.read_text(encoding="utf-8")))
    directory = path if path.is_dir() else path.parent
    with open(directory / "points.csv", newline="", encoding="utf-8") as f:
        point_rows = list(csv.DictReader(f))
    with open(directory / "observations.csv", newline="", encoding="utf-8") as f:
        obs_rows = list(csv.DictReader(f))
    data = {
        "name": directory.name,
        "points": [
            {k: _csv_cast(v) for k, v in row.items() if v not in ("", None)} for row in point_rows
        ],
        "observations": [
            {k: _csv_cast(v) for k, v in row.items() if v not in ("", None)} for row in obs_rows
        ],
    }
    # CSV booleans arrive as strings.
    for pd in data["points"]:
        for key in ("fixed_e", "fixed_n", "fixed_h"):
            if key in pd:
                pd[key] = str(pd[key]).lower() in ("true", "1", "yes", "y")
    return project_from_dict(data)


def _csv_cast(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def project_to_dict(project: Project) -> dict:
    pts = []
    for pt in project.points.values():
        d = {"id": pt.id, "e": pt.e, "n": pt.n}
        if pt.h is not None:
            d["h"] = pt.h
        for k in ("fixed_e", "fixed_n", "fixed_h"):
            if getattr(pt, k):
                d[k] = True
        pts.append(d)
    obs = []
    for o in project.observations:
        if o.kind == "distance":
            obs.append({"type": "distance", "from": o.frm, "to": o.to,
                        "value": o.value, "sigma": o.sigma})
        elif o.kind == "angle":
            obs.append({"type": "angle", "at": o.at, "from": o.frm, "to": o.to,
                        "value_deg": math.degrees(o.value),
                        "sigma_arcsec": o.sigma / RAD_PER_ARCSEC})
        elif o.kind == "direction":
            obs.append({"type": "direction", "at": o.at, "to": o.to, "setup": o.setup,
                        "value_deg": math.degrees(o.value),
                        "sigma_arcsec": o.sigma / RAD_PER_ARCSEC})
        elif o.kind == "azimuth":
            obs.append({"type": "azimuth", "from": o.frm, "to": o.to,
                        "value_deg": math.degrees(o.value),
                        "sigma_arcsec": o.sigma / RAD_PER_ARCSEC})
        elif o.kind == "coordinate":
            obs.append({"type": "coordinate", "point": o.point, "coord": o.coord,
                        "value": o.value, "sigma": o.sigma})
        elif o.kind == "height_diff":
            obs.append({"type": "height_diff", "from": o.frm, "to": o.to,
                        "value": o.value, "sigma": o.sigma})
        elif o.kind == "height":
            obs.append({"type": "height", "point": o.point,
                        "value": o.value, "sigma": o.sigma})
    return {"name": project.name, "units": project.units, "points": pts, "observations": obs}


def save_project_json(project: Project, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(project_to_dict(project), indent=2), encoding="utf-8"
    )
