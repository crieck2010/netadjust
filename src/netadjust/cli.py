"""Command-line interface: netadjust adjust|demo|level"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine.adjust1d import adjust_level_network
from .engine.adjust2d import adjust_network_2d
from .engine.example import example_project
from .engine.io import load_project, save_project_json
from .engine.report import adjusted_csv, render_html, render_text


def _run_and_write(project, out_dir: Path | None, stem: str) -> int:
    results = []
    if project.obs_2d():
        results.append(adjust_network_2d(project))
    if project.obs_1d():
        results.append(adjust_level_network(project))
    if not results:
        print("No observations found in project.", file=sys.stderr)
        return 2
    for res in results:
        text = render_text(res, project)
        print(text)
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            tag = res.dimension.lower()
            (out_dir / f"{stem}-{tag}-report.txt").write_text(text, encoding="utf-8")
            (out_dir / f"{stem}-{tag}-report.html").write_text(
                render_html(res, project), encoding="utf-8"
            )
            (out_dir / f"{stem}-{tag}-adjusted.csv").write_text(
                adjusted_csv(res), encoding="utf-8"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netadjust", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_adj = sub.add_parser("adjust", help="Adjust a JSON or CSV-bundle project")
    p_adj.add_argument("project", help="project.json or a folder with points.csv/observations.csv")
    p_adj.add_argument("--out", default=None, help="Output directory for report/CSV files")

    p_demo = sub.add_parser("demo", help="Write and adjust the bundled example network")
    p_demo.add_argument("--out", default="netadjust-demo", help="Output directory")

    args = parser.parse_args(argv)

    if args.command == "adjust":
        project = load_project(args.project)
        out = Path(args.out) if args.out else None
        return _run_and_write(project, out, Path(args.project).stem or "network")
    if args.command == "demo":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        project = example_project()
        save_project_json(project, out / "example-project.json")
        print(f"Wrote example project to {out / 'example-project.json'}")
        return _run_and_write(project, out, "example")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
