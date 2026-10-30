"""Angle helpers: DMS parsing/formatting and angle wrapping.

All angles inside the engine are radians. Linear units are whatever the
project uses (metres or feet) as long as coordinates, distances and sigmas
are consistent.
"""

from __future__ import annotations

import math
import re

ARCSEC_PER_RAD = 206264.80624709636
RAD_PER_ARCSEC = 1.0 / ARCSEC_PER_RAD


def wrap_pi(angle_rad: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


def wrap_2pi(angle_rad: float) -> float:
    """Wrap an angle to [0, 2*pi)."""
    return angle_rad % (2.0 * math.pi)


_DMS_RE = re.compile(
    r"^\s*(-?)\s*(\d+(?:\.\d+)?)\s*(?:-|°|d)\s*(\d+(?:\.\d+)?)\s*(?:'|m)\s*"
    r"(\d+(?:\.\d+)?)\s*(?:\"|s)?\s*$"
)
_DASH_RE = re.compile(r"^\s*(-?)(\d+)-(\d{1,2})-(\d+(?:\.\d+)?)\s*$")


def parse_angle(value) -> float:
    """Parse an angle to radians.

    Accepts: float/int (decimal degrees), "DDD-MM-SS.s", "DDD°MM'SS.s\"".
    """
    if isinstance(value, (int, float)):
        return math.radians(float(value))
    text = str(value).strip()
    m = _DASH_RE.match(text) or _DMS_RE.match(text)
    if m:
        sign = -1.0 if m.group(1) == "-" else 1.0
        deg = float(m.group(2)) + float(m.group(3)) / 60.0 + float(m.group(4)) / 3600.0
        return math.radians(sign * deg)
    # Last resort: a bare numeric string is decimal degrees.
    return math.radians(float(text))


def format_dms(angle_rad: float, decimals: int = 1) -> str:
    """Format radians as DDD°MM'SS.s\" (normalized to [0, 360))."""
    total_seconds = math.degrees(wrap_2pi(angle_rad)) * 3600.0
    deg = int(total_seconds // 3600)
    rem = total_seconds - deg * 3600
    minutes = int(rem // 60)
    seconds = rem - minutes * 60
    if round(seconds, decimals) >= 60.0:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        deg = (deg + 1) % 360
    return f"{deg:3d}°{minutes:02d}'{seconds:04.{decimals}f}\""


def azimuth_rad(de: float, dn: float) -> float:
    """Azimuth (clockwise from north) of a coordinate difference."""
    return math.atan2(de, dn)
