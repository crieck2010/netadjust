import pytest

from netadjust.engine import HeightDiffObs, HeightObs, Point, Project, adjust_level_network
from netadjust.engine.adjust2d import DatumDefectError


def test_weighted_mean_height():
    """One unknown height observed by two height obs of unequal weight.

    Closed form: weighted mean with weights 1/sigma^2.
    """
    proj = Project(name="wm")
    proj.points["A"] = Point("A", 0, 0, h=10.000, fixed_h=True)
    proj.points["B"] = Point("B", 0, 0, h=10.4)
    proj.observations.append(HeightObs("B", 10.400, sigma=0.010))
    proj.observations.append(HeightObs("B", 10.430, sigma=0.020))
    res = adjust_level_network(proj)
    w1, w2 = 1 / 0.010**2, 1 / 0.020**2
    expected = (10.400 * w1 + 10.430 * w2) / (w1 + w2)
    assert res.adjusted["B"]["h"] == pytest.approx(expected, abs=1e-9)
    assert res.dof == 1


def test_level_loop_zero_error():
    proj = Project(name="loop")
    heights = {"A": 100.0, "B": 101.0, "C": 100.5}
    for pid, h in heights.items():
        proj.points[pid] = Point(pid, 0, 0, h=h, fixed_h=(pid == "A"))
    for f, t in (("A", "B"), ("B", "C"), ("C", "A")):
        proj.observations.append(HeightDiffObs(f, t, heights[t] - heights[f], sigma=0.003))
    res = adjust_level_network(proj)
    for pid, h in heights.items():
        assert res.adjusted[pid]["h"] == pytest.approx(h, abs=1e-9)
    assert all(abs(o.residual) < 1e-9 for o in res.observations)


def test_level_datum_defect():
    proj = Project(name="free")
    proj.points["A"] = Point("A", 0, 0, h=100.0)
    proj.points["B"] = Point("B", 0, 0, h=101.0)
    proj.observations.append(HeightDiffObs("A", "B", 1.0, sigma=0.003))
    with pytest.raises(DatumDefectError):
        adjust_level_network(proj)
