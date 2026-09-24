"""STEP 14 - the four diagrams drawn specifically for the internship report.

Print-oriented: white background, dark text, no decorative elements. Saved to
outputs/figures/report/.

    python scripts/report_diagrams.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "figures" / "report"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#111111"
MUTED = "#555555"
LINE = "#333333"
FILL_DATA = "#EAF0F8"
FILL_ANALYSIS = "#E7F1EA"
FILL_MODEL = "#FBEFE3"
FILL_BI = "#EFEAF6"
FILL_OUT = "#F3F3F3"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "FreeSerif", "Liberation Serif"],
    "font.size": 9, "text.color": INK, "axes.edgecolor": LINE,
    "figure.dpi": 200, "savefig.dpi": 200,
})


def box(ax, x, y, w, h, text, fill, fontsize=9, weight="bold", ec=LINE, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                facecolor=fill, edgecolor=ec, linewidth=lw, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            weight=weight, color=INK, zorder=3, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, style="-|>", lw=1.1, color=LINE, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=11,
                                 linewidth=lw, color=color, linestyle=ls, zorder=1,
                                 shrinkA=1, shrinkB=1))


def canvas(w, h):
    fig = plt.figure(figsize=(w, h), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


# ------------------------------------------------------------ 1. graphical abstract
def graphical_abstract(facts: dict) -> Path:
    fig, ax = canvas(7.2, 9.4)
    k, ds = facts["kpi"], facts["dataset"]
    stages = [
        ("CUSTOMER DATA", f"{ds['raw_rows']:,} raw order lines · {ds['customers_registered']:,} "
                          f"customers\nSynthetic dataset, {ds['start'][-4:]}-{ds['end'][-4:]}", FILL_DATA),
        ("DATA CLEANING", f"{ds['clean_rows']:,} validated lines · "
                          f"{ds['duplicates_removed']} duplicates removed", FILL_DATA),
        ("EXPLORATORY DATA ANALYSIS", f"Revenue ₹{k['revenue'] / 1e7:.2f} Cr · profit "
                                      f"₹{k['profit'] / 1e7:.2f} Cr · margin {100 * k['margin']:.1f}%",
         FILL_ANALYSIS),
        ("RFM ANALYSIS", f"{facts['rfm']['customers_scored']:,} customers scored into "
                         f"{facts['rfm']['segments']} segments", FILL_ANALYSIS),
        ("K-MEANS SEGMENTATION", f"K = {facts['kmeans']['k']} clusters · silhouette "
                                 f"{facts['kmeans']['overall_silhouette']:.3f}", FILL_ANALYSIS),
        ("CUSTOMER LIFETIME VALUE", "Historical value + modelled 12-month\nfuture profit estimate",
         FILL_ANALYSIS),
        ("REVENUE PREDICTION", f"{facts['prediction']['model']} · test MAE "
                               f"₹{facts['prediction']['test_metrics']['MAE']:,.0f}", FILL_MODEL),
        ("SALES FORECASTING", f"{str(facts['forecast']['model']).split(':')[0]} · "
                              f"{facts['forecast']['horizon']}-month horizon · test MAPE "
                              f"{facts['forecast']['metrics']['test']['MAPE_%']:.2f}%", FILL_MODEL),
        ("SQL ANALYTICS", f"{facts['sql']['tables']} tables · {facts['sql']['queries']} queries · "
                          f"{facts['sql']['validation_passed']}/{facts['sql']['validation_checks']} "
                          f"validation checks", FILL_BI),
        ("POWER BI", f"Star schema · {facts['powerbi']['measures']} DAX measures · "
                     f"8 dashboard pages", FILL_BI),
        ("STREAMLIT", f"{facts['streamlit']['pages']}-page interactive application · "
                      f"{facts['streamlit']['tests_passed']}/{facts['streamlit']['tests']} tests pass",
         FILL_BI),
        ("BUSINESS DECISIONS", f"{facts['powerbi']['recommendations']} recommendations, each "
                               f"traced to a named analysis", FILL_OUT),
    ]
    n = len(stages)
    top, bottom = 0.965, 0.022
    gap = 0.020
    h = (top - bottom - gap * (n - 1)) / n
    x, w = 0.085, 0.83
    for i, (title, sub, fill) in enumerate(stages):
        y = top - (i + 1) * h - i * gap
        box(ax, x, y, w, h, "", fill)
        ax.text(x + 0.022, y + h * 0.63, title, ha="left", va="center", fontsize=9.6,
                weight="bold", color=INK, zorder=3)
        ax.text(x + 0.022, y + h * 0.27, sub, ha="left", va="center", fontsize=7.6,
                color=MUTED, zorder=3, linespacing=1.3)
        if i < n - 1:
            arrow(ax, x + w / 2, y - 0.0015, x + w / 2, y - gap + 0.0015)
    fig.savefig(OUT / "graphical_abstract.png", facecolor="white", bbox_inches="tight",
                pad_inches=0.06)
    plt.close(fig)
    return OUT / "graphical_abstract.png"


# ------------------------------------------------------------ 2. architecture
def architecture(facts: dict) -> Path:
    fig, ax = canvas(7.4, 9.0)
    layers = [
        ("DATA LAYER", FILL_DATA, [
            ("Data source", "Synthetic transaction generator (seed 42)\nscripts/generate_dataset.py"),
            ("Data ingestion", "Raw CSV + data-quality injection log\ndata/raw/"),
            ("Data cleaning", "Missing values, duplicates, types,\nbusiness-rule repair · src/data_cleaning.py"),
            ("Feature engineering", "Order, customer and time features\n51 columns in the cleaned table"),
        ]),
        ("ANALYTICS LAYER", FILL_ANALYSIS, [
            ("Exploratory data analysis", "KPIs, distributions, outliers,\ncorrelations · src/eda.py"),
            ("RFM analysis", "Recency, frequency, monetary scoring\nand rule-based segments · src/rfm.py"),
            ("K-Means segmentation", "log1p + StandardScaler, K selection,\nPCA view · src/segmentation.py"),
            ("Customer lifetime value", "Historical value and modelled\n12-month future profit · src/clv.py"),
        ]),
        ("PREDICTIVE LAYER", FILL_MODEL, [
            ("Revenue prediction", "Customer x quarter panel, temporal split,\nmodel selection · src/prediction.py"),
            ("Sales forecasting", "Monthly series, ETS / ARIMA / Theta,\nrolling backtest · src/forecasting.py"),
        ]),
        ("INTELLIGENCE LAYER", FILL_BI, [
            ("SQL analytics", "Normalised SQLite database, views,\n57 queries · src/database.py, src/sql_analytics.py"),
            ("Power BI dashboard", "Star schema, DAX measures,\n8 pages · src/powerbi_prep.py"),
            ("Streamlit application", "12 interactive pages, model integration\napp.py, pages/, src/data_loader.py"),
        ]),
        ("DECISION LAYER", FILL_OUT, [
            ("Business decision support", "18 recommendations: finding, implication\nand action, each traced to an analysis"),
        ]),
    ]
    # layout computed up front so nothing overflows the canvas
    n_items = sum(len(i) for _, _, i in layers)
    n_inner = n_items - len(layers)
    pad, inner_gap, layer_gap = 0.013, 0.010, 0.030
    top, bottom = 0.985, 0.015
    h = (top - bottom - n_inner * inner_gap - 2 * pad * len(layers)
         - layer_gap * (len(layers) - 1)) / n_items
    label_x, bx, bw = 0.052, 0.155, 0.80
    y = top
    for li, (name, fill, items) in enumerate(layers):
        block_h = len(items) * h + (len(items) - 1) * inner_gap + 2 * pad
        ax.add_patch(FancyBboxPatch((0.016, y - block_h), 0.968, block_h,
                                    boxstyle="round,pad=0.003,rounding_size=0.008",
                                    facecolor="#FAFAFA", edgecolor="#BBBBBB", linewidth=0.8,
                                    zorder=0))
        ax.text(label_x, y - block_h / 2, name, ha="center", va="center",
                fontsize=8 if len(items) > 1 else 6.4,
                weight="bold", color=MUTED, rotation=90, zorder=3)
        for j, (title, sub) in enumerate(items):
            by = y - pad - (j + 1) * h - j * inner_gap
            box(ax, bx, by, bw, h, "", fill)
            ax.text(bx + 0.018, by + h * 0.68, title, ha="left", va="center", fontsize=8.8,
                    weight="bold", zorder=3)
            ax.text(bx + 0.018, by + h * 0.28, sub, ha="left", va="center", fontsize=6.7,
                    color=MUTED, zorder=3, linespacing=1.25)
            if j < len(items) - 1:
                arrow(ax, bx + bw / 2, by - 0.0005, bx + bw / 2, by - inner_gap + 0.0005, lw=0.8)
        y -= block_h
        if li < len(layers) - 1:
            arrow(ax, 0.5, y - 0.002, 0.5, y - layer_gap + 0.002, lw=1.5)
            y -= layer_gap
    fig.savefig(OUT / "architecture.png", facecolor="white", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return OUT / "architecture.png"


# ------------------------------------------------------------ 3. flowchart
def flowchart(facts: dict) -> Path:
    """Lifecycle flowchart. The layout is computed from the node list, so nothing overflows."""
    ds = facts["dataset"]
    nodes = [
        ("term", "START", FILL_OUT),
        ("proc", f"Generate synthetic dataset (seed {ds['seed']})\n{ds['raw_rows']:,} raw order lines",
         FILL_DATA),
        ("proc", "Validate raw data against the generator's\nground truth and injection log", FILL_DATA),
        ("proc", f"Clean: duplicates, missing values, types,\nbusiness rules → {ds['clean_rows']:,} lines",
         FILL_DATA),
        ("proc", "Exploratory data analysis:\nKPIs, distributions, correlations, outliers", FILL_ANALYSIS),
        ("proc", f"RFM scoring at reference date {facts['rfm']['reference_date']}\n"
                 f"→ {facts['rfm']['segments']} rule-based segments", FILL_ANALYSIS),
        ("dec", "K-Means: does a K satisfy K ≥ 3,\nminimum cluster ≥ 5% and ARI ≥ 0.90?", None),
        ("proc", "Customer lifetime value: historical value +\n12-month future profit model",
         FILL_ANALYSIS),
        ("proc", f"Build customer × quarter panel and audit for\ntemporal leakage "
                 f"({facts['prediction']['panel_rows']:,} rows)", FILL_MODEL),
        ("proc", f"Revenue prediction: baselines vs models on a\ntemporal split → "
                 f"{facts['prediction']['model']}", FILL_MODEL),
        ("proc", f"Forecasting: ETS / ARIMA / Theta with rolling\nbacktest → "
                 f"{str(facts['forecast']['model']).split(':')[0]}, "
                 f"{facts['forecast']['horizon']}-month horizon", FILL_MODEL),
        ("proc", f"Load the SQLite database and run\n{facts['sql']['queries']} SQL analyses", FILL_BI),
        ("dec", f"Do SQL, Python and Power BI totals\nreconcile? "
                f"({facts['powerbi']['validation_matched']}/{facts['powerbi']['validation_rows']} "
                f"measures)", None),
        ("proc", "Build the Power BI star schema, DAX library\nand dashboard specification", FILL_BI),
        ("proc", f"Build the Streamlit application ({facts['streamlit']['pages']} pages)\n"
                 f"and test it headlessly", FILL_BI),
        ("proc", f"Audit the whole project\n({facts['audit']['passed']}/{facts['audit']['total']} "
                 f"checks pass)", FILL_OUT),
        ("proc", f"Publish {facts['powerbi']['recommendations']} business recommendations\n"
                 f"(finding → implication → action)", FILL_OUT),
        ("term", "END", FILL_OUT),
    ]
    heights = {"term": 0.6, "proc": 1.0, "dec": 1.55}
    units = sum(heights[t] for t, _, _ in nodes)
    fig, ax = canvas(7.4, 10.4)
    top, bottom, gap = 0.988, 0.012, 0.0085
    unit = (top - bottom - gap * (len(nodes) - 1)) / units
    cx, w = 0.255, 0.49
    y = top
    for i, (kind, text, fill) in enumerate(nodes):
        h = heights[kind] * unit
        by = y - h
        if kind == "term":
            ax.add_patch(FancyBboxPatch((cx + 0.10, by), w - 0.20, h,
                                        boxstyle="round,pad=0.003,rounding_size=0.02",
                                        facecolor=fill, edgecolor=LINE, linewidth=1.1, zorder=2))
            ax.text(cx + w / 2, by + h / 2, text, ha="center", va="center", fontsize=9,
                    weight="bold", zorder=3)
        elif kind == "proc":
            box(ax, cx, by, w, h, text, fill, fontsize=8.1, weight="normal")
        else:
            ax.add_patch(plt.Polygon([[cx + w / 2, by + h], [cx + w, by + h / 2],
                                      [cx + w / 2, by], [cx, by + h / 2]],
                                     facecolor="#FFF8E1", edgecolor=LINE, linewidth=1.0, zorder=2))
            ax.text(cx + w / 2, by + h / 2, text, ha="center", va="center", fontsize=7.5,
                    weight="bold", zorder=3, linespacing=1.3)
            if "K-Means" in text:
                ax.text(cx + w + 0.014, by + h / 2, f"Yes → K = {facts['kmeans']['k']}",
                        fontsize=7.2, color=MUTED, va="center")
                ax.text(cx - 0.014, by + h / 2, "No → test\nthe next K", fontsize=7.2,
                        color=MUTED, va="center", ha="right", linespacing=1.2)
                lx = cx - 0.085
                arrow(ax, cx, by + h / 2, lx, by + h / 2, lw=0.85)
                arrow(ax, lx, by + h / 2, lx, y + gap + unit * 0.5, lw=0.85)
                arrow(ax, lx, y + gap + unit * 0.5, cx, y + gap + unit * 0.5, lw=0.85)
            else:
                ax.text(cx + w + 0.014, by + h / 2, "Yes", fontsize=7.2, color=MUTED, va="center")
                ax.text(cx - 0.014, by + h / 2, "No → correct\nthe measure", fontsize=7.2,
                        color=MUTED, va="center", ha="right", linespacing=1.2)
        if i < len(nodes) - 1:
            arrow(ax, cx + w / 2, by - 0.0008, cx + w / 2, by - gap + 0.0008)
        y = by - gap
    fig.savefig(OUT / "flowchart.png", facecolor="white", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return OUT / "flowchart.png"


# ------------------------------------------------------------ 4. project timeline
def timeline(facts: dict) -> Path:
    fig, ax = canvas(7.4, 4.6)
    phases = [
        ("Phase 1", "Setup and data", "Steps 1-3", "Project structure, synthetic dataset design,\n"
                                                   "generation, validation and cleaning", FILL_DATA),
        ("Phase 2", "Descriptive analytics", "Steps 4-5", "Exploratory data analysis and\n"
                                                          "RFM customer segmentation", FILL_ANALYSIS),
        ("Phase 3", "Machine learning", "Steps 6-7", "K-Means clustering and\n"
                                                     "customer lifetime value modelling", FILL_ANALYSIS),
        ("Phase 4", "Predictive modelling", "Steps 8-9", "Revenue prediction and\n"
                                                         "time-series sales forecasting", FILL_MODEL),
        ("Phase 5", "Business intelligence", "Steps 10-11", "SQL analytics database and\n"
                                                            "Power BI executive dashboard", FILL_BI),
        ("Phase 6", "Application and QA", "Steps 12-14", "Streamlit application, project audit\n"
                                                         "and final report", FILL_OUT),
    ]
    n = len(phases)
    y0, y1 = 0.80, 0.22
    ax.plot([0.06, 0.94], [0.50, 0.50], color=LINE, lw=1.2, zorder=1)
    for i, (ph, title, steps, desc, fill) in enumerate(phases):
        x = 0.06 + (0.88) * (i + 0.5) / n
        up = i % 2 == 0
        ax.plot([x], [0.50], "o", color=LINE, ms=6, zorder=3)
        by = y0 if up else y1 - 0.14
        bh = 0.20
        box(ax, x - 0.068, by, 0.136, bh, "", fill)
        ax.text(x, by + bh * 0.80, ph, ha="center", va="center", fontsize=7.4, weight="bold",
                color=MUTED, zorder=3)
        ax.text(x, by + bh * 0.58, title, ha="center", va="center", fontsize=8.4, weight="bold",
                zorder=3)
        ax.text(x, by + bh * 0.39, steps, ha="center", va="center", fontsize=7.2, color=MUTED,
                zorder=3)
        ax.text(x, by + bh * 0.18, desc, ha="center", va="center", fontsize=6.4, color=INK,
                zorder=3, linespacing=1.25)
        ax.plot([x, x], [0.50, by if up else by + bh], color=LINE, lw=0.9, zorder=1)
    ax.text(0.5, 0.045, "Sequential execution: each phase consumes the validated output of the "
                        "phase before it.", ha="center", fontsize=7.6, color=MUTED)
    fig.savefig(OUT / "timeline.png", facecolor="white", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return OUT / "timeline.png"


def build_all() -> dict:
    facts = json.loads((ROOT / "outputs/tables/report_facts.json").read_text())
    paths = {"graphical_abstract": graphical_abstract(facts), "architecture": architecture(facts),
             "flowchart": flowchart(facts), "timeline": timeline(facts)}
    return paths


if __name__ == "__main__":
    for name, path in build_all().items():
        print(f"{name:20s} -> {path.relative_to(ROOT)}")
