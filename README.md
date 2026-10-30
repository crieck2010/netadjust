# NetAdjust

**Standalone least-squares adjustment for survey networks** — a weighted
parametric adjustment engine, a desktop app, and a command-line tool in one
repo. Built to be *operational* (open a project, run it, get a defensible
report) and *accurate* (full covariance statistics, not just coordinates).

![version](https://img.shields.io/badge/version-0.1.0-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

## What it does

- **2D horizontal networks** (Gauss–Newton iteration): horizontal distances,
  horizontal angles, direction sets with a per-setup orientation unknown,
  azimuths, and weighted coordinate observations.
- **1D level networks**: height differences and weighted height observations.
- **Real statistics**, because an adjustment without them is just arithmetic:
  - a posteriori sigma0 and the **chi-square global test** of your a priori sigmas
  - residuals, **redundancy numbers**, **Baarda data-snooping (w-test)** blunder flags
  - full covariance of adjusted coordinates and **95% error ellipses**
- **Datum safety**: an under-defined datum (singular normal matrix) stops
  with an explanation of what to fix — never a silently wrong answer.
- Units: metres or feet (label-consistent); angles in DMS, decimal degrees,
  or radians; angular sigmas in arcseconds.

## Quick start

```bash
pip install -e .
netadjust demo --out demo-out     # writes + adjusts the example network
netadjust adjust my-network.json --out results
netadjust-app                     # desktop app (Tkinter)
```

Input is a JSON project file or a CSV bundle (`points.csv` +
`observations.csv`). See [docs/input-format.md](docs/input-format.md) and
the worked example in [examples/](examples/example-project.json) with its
[expected report](examples/example-2d-report.txt).

## Desktop (.exe)

On a Windows PC:

```bat
build_exe.bat
```

produces `dist\NetAdjust.exe` (PyInstaller single file); `installer.iss`
builds an Inno Setup installer from it. PyInstaller targets the OS it runs
on, so the .exe must be built on Windows.

## How accuracy is verified

`tests/` is a validation suite, not a smoke test:

- a **zero-error** synthetic network recovers the truth exactly;
- a level network matches its **closed-form weighted-mean** solution;
- a **Monte-Carlo coverage test** (120 simulated networks) checks that the
  95% error ellipses actually contain the truth ~95% of the time;
- a **+5 cm blunder** injected into one distance is caught by the w-test;
- chi-square functions are checked against published table values;
- redundancy numbers are verified to sum to the degrees of freedom.

```bash
pip install -e .[dev]
pytest
```

## Layout

```
src/netadjust/engine/   pure-Python engine (no UI imports): models, 2D/1D
                        adjusters, statistics, I/O, reports
src/netadjust/app.py    thin Tkinter desktop UI over the engine
src/netadjust/cli.py    command-line interface
examples/               worked example project + expected report
docs/                   theory, input format, user guide
build.py / build_exe.bat / installer.iss   Windows packaging
```

## Roadmap

- v1.1: STAR*NET `.dat` import; GNSS baseline-vector observations (ΔE/ΔN/ΔH
  with full 3×3 covariance per vector)
- Later: combined 3D adjustment, robust reweighting (Danish method),
  pre-analysis / network design tools

## License

MIT — see [LICENSE](LICENSE).
