"""Monetization / product hooks (stubs, non-enforcing in v0.x).

Kept in the engine so a future packaged release can enforce licensing
without touching adjustment code. Both functions degrade safely offline.
"""

from __future__ import annotations


def check_license(key: str | None = None) -> bool:
    """License-key check hook. v0.x: always valid (open-source MIT build)."""
    return True


def check_for_update(current_version: str) -> str | None:
    """Update-check hook. Returns a newer version string, or None.

    v0.x: no network call is made; returns None.
    """
    return None
