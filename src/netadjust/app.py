"""NetAdjust desktop app (Tkinter) — a thin UI over the engine.

The engine does all computation; this module only loads projects, runs
adjustments, and displays/saves results. Importing this module does not
create a window; call main().
"""

from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .engine.adjust1d import adjust_level_network
from .engine.adjust2d import adjust_network_2d
from .engine.angles import ARCSEC_PER_RAD
from .engine.example import example_project
from .engine.io import load_project
from .engine.models import Project
from .engine.report import adjusted_csv, render_text

ANGULAR = {"angle", "azimuth", "direction"}


class NetAdjustApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"NetAdjust v{__version__} — Least Squares Adjustment")
        root.geometry("1080x720")
        self.project: Project | None = None
        self.results = []
        self._build_ui()

    def _build_ui(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Open project…", command=self.open_project).pack(side="left")
        ttk.Button(bar, text="Load example", command=self.load_example).pack(side="left", padx=4)
        ttk.Button(bar, text="Run adjustment", command=self.run_adjustment).pack(side="left", padx=4)
        ttk.Button(bar, text="Save report…", command=self.save_report).pack(side="left", padx=4)
        ttk.Button(bar, text="Save adjusted CSV…", command=self.save_csv).pack(side="left", padx=4)
        self.status = ttk.Label(bar, text="No project loaded.")
        self.status.pack(side="left", padx=12)

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.coord_tree = self._tree_tab(
            nb, "Adjusted coordinates",
            ("point", "E / H", "N", "sig E/H", "sig N", "a 95%", "b 95%", "theta°"),
        )
        self.resid_tree = self._tree_tab(
            nb, "Residuals",
            ("#", "observation", "observed", "residual", "redundancy", "w-test", "flag"),
        )
        report_frame = ttk.Frame(nb)
        nb.add(report_frame, text="Report")
        self.report_text = tk.Text(report_frame, wrap="none", font=("Consolas", 10))
        self.report_text.pack(fill="both", expand=True)
        plot_frame = ttk.Frame(nb)
        nb.add(plot_frame, text="Plot")
        self.canvas = tk.Canvas(plot_frame, background="#101418")
        self.canvas.pack(fill="both", expand=True)

    def _tree_tab(self, nb, title, columns):
        frame = ttk.Frame(nb)
        nb.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor="center")
        tree.pack(fill="both", expand=True)
        return tree

    # -- actions -----------------------------------------------------------
    def open_project(self):
        path = filedialog.askopenfilename(
            title="Open NetAdjust project",
            filetypes=[("JSON project", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.project = load_project(path)
        except Exception as exc:  # surfaced to the user, not swallowed
            messagebox.showerror("Could not open project", str(exc))
            return
        self.status.config(
            text=f"{self.project.name}: {len(self.project.points)} points, "
            f"{len(self.project.observations)} observations"
        )

    def load_example(self):
        self.project = example_project()
        self.status.config(text=f"Example loaded: {self.project.name}")
        self.run_adjustment()

    def run_adjustment(self):
        if self.project is None:
            messagebox.showinfo("NetAdjust", "Open a project or load the example first.")
            return
        try:
            self.results = []
            if self.project.obs_2d():
                self.results.append(adjust_network_2d(self.project))
            if self.project.obs_1d():
                self.results.append(adjust_level_network(self.project))
        except Exception as exc:
            messagebox.showerror("Adjustment failed", str(exc))
            return
        self._fill_tables()
        self._draw_plot()
        r0 = self.results[0]
        self.status.config(
            text=f"Adjusted: dof={r0.dof}, sigma0="
            f"{'—' if r0.sigma0 is None else f'{r0.sigma0:.3f}'}, "
            f"chi-square {'—' if r0.chi2_pass_95 is None else ('PASS' if r0.chi2_pass_95 else 'FAIL')}"
        )

    def _fill_tables(self):
        for tree in (self.coord_tree, self.resid_tree):
            tree.delete(*tree.get_children())
        report_chunks = []
        for res in self.results:
            report_chunks.append(render_text(res, self.project))
            if res.dimension == "2D":
                for pid, adj in res.adjusted.items():
                    sig = res.point_sigma[pid]
                    a, b, th = res.ellipses[pid]
                    self.coord_tree.insert("", "end", values=(
                        pid, f"{adj['e']:.4f}", f"{adj['n']:.4f}",
                        f"{sig['e']:.4f}", f"{sig['n']:.4f}",
                        f"{a:.4f}", f"{b:.4f}", f"{math.degrees(th):.1f}"))
            else:
                for pid, adj in res.adjusted.items():
                    sig = res.point_sigma[pid]
                    self.coord_tree.insert("", "end", values=(
                        pid, f"{adj['h']:.4f}", "—", f"{sig['h']:.4f}",
                        "—", "—", "—", "—"))
            for o in res.observations:
                resid = (f"{o.residual * ARCSEC_PER_RAD:+.2f}\""
                         if o.kind in ANGULAR else f"{o.residual:+.4f}")
                self.resid_tree.insert("", "end", values=(
                    o.index + 1, o.label, f"{o.observed:.5f}", resid,
                    f"{o.redundancy:.3f}", f"{o.w_test:.2f}",
                    "CHECK" if o.flagged else ""))
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", "\n".join(report_chunks))

    def _draw_plot(self):
        self.canvas.delete("all")
        res = next((r for r in self.results if r.dimension == "2D"), None)
        if res is None or not res.adjusted:
            return
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        es = [a["e"] for a in res.adjusted.values()]
        ns = [a["n"] for a in res.adjusted.values()]
        span_e = max(max(es) - min(es), 1e-9)
        span_n = max(max(ns) - min(ns), 1e-9)
        scale = 0.8 * min(w / span_e, h / span_n)

        def xy(e, n):
            return (40 + (e - min(es)) * scale, h - 40 - (n - min(ns)) * scale)

        for o in self.project.observations:
            frm = getattr(o, "frm", None) or getattr(o, "at", None)
            to = getattr(o, "to", None)
            if frm in res.adjusted and to in res.adjusted:
                x1, y1 = xy(res.adjusted[frm]["e"], res.adjusted[frm]["n"])
                x2, y2 = xy(res.adjusted[to]["e"], res.adjusted[to]["n"])
                self.canvas.create_line(x1, y1, x2, y2, fill="#3d5a73")
        for pid, adj in res.adjusted.items():
            x, y = xy(adj["e"], adj["n"])
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#e8b13c", outline="")
            self.canvas.create_text(x + 8, y - 8, text=pid, fill="#e6edf3", anchor="w")

    def save_report(self):
        if not self.results:
            messagebox.showinfo("NetAdjust", "Run an adjustment first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save report", defaultextension=".txt",
            filetypes=[("Text report", "*.txt")])
        if path:
            text = "\n".join(render_text(r, self.project) for r in self.results)
            Path(path).write_text(text, encoding="utf-8")

    def save_csv(self):
        if not self.results:
            messagebox.showinfo("NetAdjust", "Run an adjustment first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save adjusted coordinates", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")])
        if path:
            Path(path).write_text(adjusted_csv(self.results[0]), encoding="utf-8")


def main() -> None:
    root = tk.Tk()
    NetAdjustApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
