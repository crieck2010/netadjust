"""Data model for a survey network project and adjustment results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Point:
    id: str
    e: float  # approximate / fixed easting
    n: float  # approximate / fixed northing
    h: float | None = None  # approximate / fixed height (1D network)
    fixed_e: bool = False
    fixed_n: bool = False
    fixed_h: bool = False

    @property
    def fixed_en(self) -> bool:
        return self.fixed_e and self.fixed_n


@dataclass
class DistanceObs:
    frm: str
    to: str
    value: float  # horizontal distance, project linear units
    sigma: float  # a priori standard deviation, same units
    kind: str = "distance"


@dataclass
class AngleObs:
    at: str
    frm: str  # backsight point
    to: str  # foresight point
    value: float  # radians, clockwise from backsight to foresight direction
    sigma: float  # radians
    kind: str = "angle"


@dataclass
class DirectionObs:
    at: str
    to: str
    value: float  # radians on the instrument circle
    sigma: float  # radians
    setup: str = "S1"  # observations sharing a setup share one orientation unknown
    kind: str = "direction"


@dataclass
class AzimuthObs:
    frm: str
    to: str
    value: float  # radians, clockwise from north
    sigma: float  # radians
    kind: str = "azimuth"


@dataclass
class CoordinateObs:
    """A weighted prior observation of one coordinate of a point."""

    point: str
    coord: str  # "e" or "n"
    value: float
    sigma: float
    kind: str = "coordinate"


@dataclass
class HeightDiffObs:
    frm: str
    to: str
    value: float  # observed height difference (h_to - h_frm)
    sigma: float
    kind: str = "height_diff"


@dataclass
class HeightObs:
    point: str
    value: float
    sigma: float
    kind: str = "height"


Observation = (
    DistanceObs | AngleObs | DirectionObs | AzimuthObs | CoordinateObs | HeightDiffObs | HeightObs
)

TWO_D_KINDS = {"distance", "angle", "direction", "azimuth", "coordinate"}
ONE_D_KINDS = {"height_diff", "height"}


@dataclass
class Project:
    name: str = "Untitled network"
    units: str = "m"  # linear unit label: "m" or "ft" (US survey feet by label only)
    points: dict[str, Point] = field(default_factory=dict)
    observations: list[Observation] = field(default_factory=list)

    def obs_2d(self) -> list[Observation]:
        return [o for o in self.observations if o.kind in TWO_D_KINDS]

    def obs_1d(self) -> list[Observation]:
        return [o for o in self.observations if o.kind in ONE_D_KINDS]


@dataclass
class ObsResult:
    index: int
    kind: str
    label: str
    observed: float
    predicted: float
    residual: float  # observed - predicted, linear units or radians by kind
    sigma: float  # a priori sigma
    redundancy: float
    w_test: float  # Baarda w statistic: residual / sigma_residual (a priori)
    studentized: float | None  # residual scaled by a posteriori sigma0
    flagged: bool  # |w_test| > 3.29 (alpha ~= 0.001, two-sided)


@dataclass
class AdjustmentResult:
    dimension: str  # "2D" or "1D"
    project_name: str
    adjusted: dict[str, dict[str, float]]  # point id -> {"e":..,"n":..} or {"h":..}
    point_sigma: dict[str, dict[str, float]]  # point id -> coordinate sigmas (a posteriori)
    ellipses: dict[str, tuple[float, float, float]]  # 2D only: (a, b, orientation_rad) at 95%
    observations: list[ObsResult]
    n_obs: int
    n_unknowns: int
    dof: int
    vtpv: float
    sigma0: float | None  # a posteriori std dev of unit weight; None when dof == 0
    chi2_p_value: float | None
    chi2_pass_95: bool | None  # two-sided 95% global test vs a priori sigmas
    iterations: int
    converged: bool
    warnings: list[str] = field(default_factory=list)
