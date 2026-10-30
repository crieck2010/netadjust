import math

import numpy as np
import pytest

from netadjust.engine.angles import format_dms, parse_angle
from netadjust.engine.stats import chi2_cdf, chi2_ppf, error_ellipse


def test_chi2_known_values():
    # Standard chi-square table values.
    assert chi2_cdf(5.991, 2) == pytest.approx(0.95, abs=1e-3)
    assert chi2_cdf(3.841, 1) == pytest.approx(0.95, abs=1e-3)
    assert chi2_cdf(18.307, 10) == pytest.approx(0.95, abs=1e-3)
    assert chi2_ppf(0.95, 2) == pytest.approx(5.991, abs=1e-3)
    assert chi2_ppf(0.975, 10) == pytest.approx(20.483, abs=1e-2)


def test_dms_roundtrip():
    for deg in (0.0, 45.5, 123.7625, 359.9997):
        text = format_dms(math.radians(deg))
        assert parse_angle(text) == pytest.approx(math.radians(deg), abs=1e-6)
    assert parse_angle("90-30-00") == pytest.approx(math.radians(90.5))
    assert parse_angle(90.5) == pytest.approx(math.radians(90.5))


def test_error_ellipse_axis_aligned():
    cov = np.diag([0.01, 0.04])  # sigma_e = 0.1, sigma_n = 0.2
    a, b, theta = error_ellipse(cov, 0.95)
    assert a == pytest.approx(0.2 * math.sqrt(5.99146), rel=1e-6)
    assert b == pytest.approx(0.1 * math.sqrt(5.99146), rel=1e-6)
    # Semi-major axis runs north (larger N variance): orientation ~ 0 from north.
    assert theta == pytest.approx(0.0, abs=1e-9)
