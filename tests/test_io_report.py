import json

import pytest

from netadjust.cli import main as cli_main
from netadjust.engine.example import example_project
from netadjust.engine.io import load_project, project_from_dict, save_project_json
from netadjust.engine.report import adjusted_csv, render_text
from netadjust.engine import adjust_network_2d


def test_json_roundtrip(tmp_path):
    proj = example_project()
    path = tmp_path / "p.json"
    save_project_json(proj, path)
    loaded = load_project(path)
    assert set(loaded.points) == set(proj.points)
    assert len(loaded.observations) == len(proj.observations)


def test_dms_input(tmp_path):
    data = {
        "name": "dms",
        "points": [
            {"id": "A", "e": 0, "n": 0, "fixed_e": True, "fixed_n": True},
            {"id": "B", "e": 100, "n": 0, "fixed_e": True, "fixed_n": True},
            {"id": "C", "e": 100, "n": 100},
        ],
        "observations": [
            {"type": "angle", "at": "B", "from": "A", "to": "C",
             "value_dms": "90-00-00", "sigma_arcsec": 5},
            {"type": "distance", "from": "B", "to": "C", "value": 100.0, "sigma": 0.005},
            {"type": "distance", "from": "A", "to": "C", "value": 141.4214, "sigma": 0.005},
        ],
    }
    proj = project_from_dict(data)
    res = adjust_network_2d(proj)
    assert res.adjusted["C"]["e"] == pytest.approx(100.0, abs=0.01)
    assert res.adjusted["C"]["n"] == pytest.approx(100.0, abs=0.01)


def test_report_and_cli(tmp_path, capsys):
    proj = example_project()
    res = adjust_network_2d(proj)
    text = render_text(res, proj)
    assert "ADJUSTED COORDINATES" in text and "chi-square" in text
    assert "point,e,n" in adjusted_csv(res)
    path = tmp_path / "ex.json"
    path.write_text(json.dumps(json.loads(json.dumps(
        __import__("netadjust.engine.io", fromlist=["project_to_dict"]).project_to_dict(proj)))))
    out = tmp_path / "out"
    assert cli_main(["adjust", str(path), "--out", str(out)]) == 0
    assert (out / "ex-2d-report.txt").exists()
    assert (out / "ex-1d-adjusted.csv").exists()
