"""One-command Windows .exe build (run on a Windows PC).

    python build.py

Produces dist/NetAdjust.exe (PyInstaller single-file, windowed).
A Linux run works as a smoke test but produces a Linux binary —
PyInstaller always targets the OS it runs on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "NetAdjust",
        "--paths", str(ROOT / "src"),
        str(ROOT / "launcher.py"),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
