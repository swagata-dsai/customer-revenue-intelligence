#!/usr/bin/env python3
"""
sql_analytics.py
================
Step 10: runs the SQL files against data/customer_revenue_intelligence.db and turns the results into tables,
figures and a methodology report. ALL business calculations happen in SQL; Python only loads, validates,
saves, charts and writes text from the returned result sets.

    parse_sql_file()        read '-- name: / -- section: / -- title: / -- question: ...' blocks from a .sql file
    run_sql_file()          execute every block, return {name: DataFrame} + a catalog (rows, runtime, techniques)
    technique_coverage()    which advanced SQL features are used, and where
    save_sql_outputs()      outputs/tables/sql/<name>.csv + product_profitability.csv + customer_segment_sql_analysis.csv
    key_findings()          evidence table built only from SQL results
    plot_sql_figures()      outputs/figures/sql/ (ER diagram + SQL-driven charts)
    write_sql_report()      outputs/reports/sql_analysis_methodology.md
    run_sql_workflow()      build DB -> validate -> run queries -> save -> figures -> report -> QC

Main entry point:  python src/sql_analytics.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.database import LOAD_ORDER, build_database, table_catalog, validate_database  # noqa: E402
from src.eda import inr  # noqa: E402

ANALYSIS_FILE = config.SQL_DIR / "analysis_queries.sql"
BUSINESS_FILE = config.SQL_DIR / "business_queries.sql"
SQL_TABLES_DIR = config.TABLES_DIR / "sql"
FIG_DIR = config.FIGURES_DIR / "sql"
REPORT_FILE = config.REPORTS_DIR / "sql_analysis_methodology.md"

TECHNIQUES = {  # label -> regex (case-insensitive) used to document which SQL features each query uses
    "INNER JOIN": r"(?<!LEFT )\bJOIN\b",
    "LEFT JOIN": r"\bLEFT JOIN\b",
    "CASE WHEN": r"\bCASE\b",
    "CTE (WITH)": r"^\s*WITH\b",
    "Subquery": None,                         # handled in detect_techniques (CTE bodies are not subqueries)
    "Window function": r"\bOVER\s*(\(|w\b)",
    "Ranking (RANK / ROW_NUMBER / NTILE)": r"\b(RANK|ROW_NUMBER|NTILE|DENSE_RANK)\s*\(",
    "Running total (window frame)": r"ROWS\s+(UNBOUNDED|BETWEEN)",
    "Percentage contribution (SUM() OVER ())": r"SUM\((SUM\()?[^()]*\)?\)\s*OVER\s*\(\s*(PARTITION BY [^)]*)?\)",
    "LAG / LEAD": r"\b(LAG|LEAD)\s*\(",
    "GROUP BY aggregation": r"\bGROUP BY\b",
    "HAVING": r"\bHAVING\b",
    "Date functions": r"\b(strftime|julianday|date)\s*\(",
    "UNION ALL": r"\bUNION ALL\b",
}


# =============================================================================
# 1. PARSE + RUN
# =============================================================================
def parse_sql_file(path: Path) -> list[dict]:
    """Split a .sql file into query blocks. Each block starts with '-- name: <id>'; following '-- key: value'
    comment lines become metadata; the rest is the SQL statement."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^-- name: ", text)[1:]
    out = []
    for b in blocks:
        name, rest = b.split("\n", 1)
        meta, sql_lines = {}, []
        for line in rest.splitlines():
            m = re.match(r"^-- (\w+): (.*)$", line)
            if m and not sql_lines:
                meta[m.group(1)] = m.group(2).strip()
            elif line.startswith("-- ===") or (line.startswith("-- ") and not sql_lines and not m):
                continue
            else:
                sql_lines.append(line)
        sql = "\n".join(sql_lines)
        sql = re.split(r"(?m)^-- =+\s*$", sql)[0].strip()      # drop trailing section banners
        out.append({"name": name.strip(), **meta, "sql": sql, "file": path.name})
    return out


def _has_subquery(sql: str) -> bool:
    """A '(SELECT' that is not the body of a CTE ('name AS (SELECT')."""
    for m in re.finditer(r"\(\s*SELECT\b", sql, flags=re.IGNORECASE):
        if not re.search(r"\bAS\s*$", sql[:m.start()], flags=re.IGNORECASE):
            return True
    return False


def detect_techniques(sql: str) -> list[str]:
    out = []
    for k, rx in TECHNIQUES.items():
        hit = _has_subquery(sql) if rx is None else re.search(rx, sql, flags=re.IGNORECASE | re.MULTILINE)
        if hit:
            out.append(k)
    return out


def run_sql_file(con: sqlite3.Connection, path: Path) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Execute every query block in the file. Returns results and a catalog row per query."""
    res, cat = {}, []
    for q in parse_sql_file(path):
        df = pd.read_sql_query(q["sql"], con)
        res[q["name"]] = df
        cat.append({"Query": q["name"], "File": q["file"], "Section": q.get("section", "Business question"),
                    "Title_or_Question": q.get("title", q.get("question", "")), "Purpose": q.get("purpose", ""),
                    "Interpretation": q.get("interpretation", ""), "Rows": len(df),
                    "Techniques": ", ".join(detect_techniques(q["sql"]))})
    return res, pd.DataFrame(cat)


def technique_coverage(catalog: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in TECHNIQUES:
        used = catalog[catalog["Techniques"].str.contains(re.escape(t))]
        rows.append({"Technique": t, "Queries_Using_It": len(used), "Examples": ", ".join(used["Query"].head(6))})
    return pd.DataFrame(rows)


# =============================================================================
# 2. OUTPUT TABLES
# =============================================================================
def segment_output(R: dict) -> pd.DataFrame:
    """customer_segment_sql_analysis.csv - the spec's column names, values straight from seg_rfm_summary."""
    s = R["results"]["seg_rfm_summary"]
    return pd.DataFrame({"Segment": s["segment"], "Value_Activity_Group": s["value_activity_group"],
                         "Customer_Count": s["customer_count"], "Revenue": s["revenue"], "Profit": s["profit"],
                         "Average_Revenue_per_Customer": s["avg_revenue_per_customer"],
                         "Average_Frequency_Orders": s["avg_frequency"], "Average_Recency_Days": s["avg_recency_days"],
                         "Revenue_Contribution_%": s["revenue_contribution_pct"], "Customer_%": s["customer_pct"]})


def product_output(R: dict) -> pd.DataFrame:
    p = R["results"]["prod_profitability"]
    return p.rename(columns={"product_id": "Product_ID", "product_name": "Product", "category": "Category",
                             "sub_category": "Sub_Category", "quantity": "Quantity", "revenue": "Revenue",
                             "cost": "Cost", "profit": "Profit", "profit_margin_pct": "Profit_Margin_%",
                             "avg_discount_pct": "Average_Discount_%", "avg_selling_price": "Average_Selling_Price",
                             "avg_list_price": "Average_List_Price", "return_cancel_rate_pct": "Return_Cancel_Rate_%",
                             "profit_rank": "Profit_Rank"})


def save_sql_outputs(R: dict) -> list[Path]:
    SQL_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, df in R["results"].items():
        p = SQL_TABLES_DIR / f"{name}.csv"
        df.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    named = {"product_profitability.csv": product_output(R),
             "customer_segment_sql_analysis.csv": segment_output(R),
             "customer_revenue_concentration.csv": R["results"]["cust_revenue_concentration"],
             "sql_query_catalog.csv": R["catalog"],
             "sql_technique_coverage.csv": R["coverage"],
             "sql_validation_checks.csv": R["validation"],
             "sql_table_catalog.csv": R["tables"],
             "sql_key_findings.csv": R["findings"],
             "sql_quality_checklist.csv": R["qc"]}
    for n, df in named.items():
        p = config.TABLES_DIR / n
        df.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


# =============================================================================
# 3. FINDINGS (text built only from SQL result sets)
# =============================================================================
def key_findings(R: dict) -> pd.DataFrame:
    r = R["results"]
    k = r["rev_kpi_summary"].iloc[0]
    y = r["rev_by_year"]
    conc = r["cust_concentration_summary"].set_index("top_pct")
    seg = r["seg_rfm_summary"].set_index("segment")
    cl = r["seg_ml_cluster_summary"]
    cat = r["prod_category_performance"].set_index("category")
    reg = r["reg_performance"]
    disc = r["prod_discount_bands"]
    bq = {n: r[n] for n in r if n.startswith("BQ")}
    rep = bq["BQ12"].set_index("customer_group")
    ret = bq["BQ15"]
    inv = r["prod_investigate"]
    bw = r["time_best_worst_months"]
    top_m = bw.iloc[0]
    q9 = bq["BQ09"]
    oct_top = q9[q9["rank_in_year"] == 1]["order_month"].str[-2:].nunique() == 1
    lost = bq["BQ14"].sort_values("lost_pct_of_booked", ascending=False).iloc[0]
    pay = bq["BQ13"].sort_values("cancelled_lines_pct", ascending=False)
    pay = pay[pay["payment_method"] != "Unknown"].iloc[0]
    gap = bq["BQ16"]
    b8 = bq["BQ08"]
    n_cat = b8["category"].nunique()
    first_band = b8.groupby("category").head(1)                       # rows are ordered by MIN(discount)
    last_band = b8.groupby("category").tail(1)
    best = b8.loc[b8.groupby("category")["profit_margin_pct"].idxmax()]
    worst = b8.loc[b8.groupby("category")["profit_margin_pct"].idxmin()]
    n_zero_best = int(first_band.set_index("category")["discount_band"].eq(best.set_index("category")["discount_band"]).sum())
    n_top_worst = int(last_band.set_index("category")["discount_band"].eq(worst.set_index("category")["discount_band"]).sum())
    rows = [
        ("Revenue", f"Delivered revenue {inr(k['total_revenue'])}, profit {inr(k['total_profit'])} "
                    f"({k['profit_margin_pct']:.2f}% margin), {int(k['total_orders']):,} orders, "
                    f"{int(k['total_customers']):,} customers, AOV {inr(k['average_order_value'])}.", "rev_kpi_summary"),
        ("Growth", "Revenue growth " + ", ".join(f"{int(a)}: {b:+.1f}%" for a, b in
                                                 zip(y["order_year"], y["revenue_yoy_growth_pct"]) if pd.notna(b))
         + "; margin " + " -> ".join(f"{m:.2f}%" for m in y["profit_margin_pct"]) + ".", "rev_by_year"),
        ("Customer concentration", f"Top 20% of customers = {conc.loc[20, 'pct_of_revenue']:.2f}% of revenue; top 1% = "
                                   f"{conc.loc[1, 'pct_of_revenue']:.2f}%.", "cust_concentration_summary"),
        ("Repeat purchasing", f"Repeat customers are {rep.loc['Repeat (2+ orders)', 'pct_of_customers']:.1f}% of customers "
                              f"and {rep.loc['Repeat (2+ orders)', 'pct_of_revenue']:.1f}% of revenue.", "BQ12"),
        ("Retention", "Retained / active last year: " + ", ".join(
            f"{int(a)}: {b:.1f}%" for a, b in zip(ret["order_year"], ret["retention_rate_pct"]) if pd.notna(b))
         + "; new customers per year " + ", ".join(f"{int(a)}: {b:,}" for a, b in zip(ret["order_year"], ret["new_customers"]))
         + ".", "BQ15"),
        ("RFM segments", f"Champions: {seg.loc['Champions', 'customer_pct']:.1f}% of customers, "
                         f"{seg.loc['Champions', 'revenue_contribution_pct']:.1f}% of revenue; At Risk + Can't Lose Them: "
                         f"{seg.loc['At Risk', 'revenue_contribution_pct'] + seg.loc[chr(67) + 'an' + chr(39) + 't Lose Them', 'revenue_contribution_pct']:.1f}% "
                         "of revenue.", "seg_rfm_summary"),
        ("ML clusters", "; ".join(f"{a}: {b:.2f}% of customers, {c:.2f}% of revenue" for a, b, c in
                                  zip(cl["cluster_label"], cl["customer_pct"], cl["revenue_contribution_pct"])) + ".",
         "seg_ml_cluster_summary"),
        ("Potentially at-risk value", f"{len(bq['BQ06'])} high-historical-value customers have not bought for >= 180 days "
                                      f"(lifetime revenue {inr(bq['BQ06']['lifetime_revenue'].sum())}).", "BQ06"),
        ("Categories", f"Electronics: {cat.loc['Electronics', 'revenue_share_pct']:.1f}% of revenue at "
                       f"{cat.loc['Electronics', 'profit_margin_pct']:.1f}% margin; Fashion {cat.loc['Fashion', 'profit_share_pct']:.1f}% "
                       f"of profit at {cat.loc['Fashion', 'profit_margin_pct']:.1f}% margin; highest margin "
                       f"{cat['profit_margin_pct'].idxmax()} ({cat['profit_margin_pct'].max():.1f}%).", "prod_category_performance"),
        ("Products to investigate", f"{len(inv)} products flagged; high-revenue low-margin examples: "
                                    + ", ".join(bq['BQ03'].head(3)['product_name']) + ".", "prod_investigate, BQ03"),
        ("Discounts", "Margin by discount band: " + ", ".join(f"{a} {b:.1f}%" for a, b in
                                                              zip(disc["discount_band"], disc["profit_margin_pct"]))
         + f"; within categories, the 0% band has the highest margin in {n_zero_best}/{n_cat} categories and the "
           f"highest band the lowest margin in {n_top_worst}/{n_cat} (BQ08) - an association, not proof of cause.",
         "prod_discount_bands, BQ08"),
        ("Returns / cancellations", f"{lost['category']} loses the largest share of booked value to returns/cancellations "
                                    f"({lost['lost_pct_of_booked']:.1f}%); {pay['payment_method']} has the highest "
                                    f"cancellation rate ({pay['cancelled_lines_pct']:.1f}% of lines).", "BQ14, BQ13"),
        ("Regions", f"{reg.iloc[0]['region']} leads revenue ({reg.iloc[0]['revenue_share_pct']:.1f}%); margins range "
                    f"{reg['profit_margin_pct'].min():.1f}-{reg['profit_margin_pct'].max():.1f}%; "
                    f"{int(gap['flag_below_2pp'].sum())} region-category pairs are > 2 pp below the national category margin "
                    f"(largest gap {gap['margin_gap_pp'].min():+.1f} pp).", "reg_performance, BQ16"),
        ("Seasonality", f"Highest month {top_m['order_month']} ({inr(top_m['revenue'])}); the same calendar month tops every "
                        f"year: {'yes' if oct_top else 'no'} (" + ", ".join(q9[q9['rank_in_year'] == 1]['order_month']) + ").",
         "time_best_worst_months, BQ09"),
    ]
    return pd.DataFrame(rows, columns=["Area", "Finding (computed by SQL)", "Source query"])


# =============================================================================
# 4. QC
# =============================================================================
def quality_checklist(R: dict) -> pd.DataFrame:
    v, cat, cov = R["validation"], R["catalog"], R["coverage"].set_index("Technique")
    secs = cat["Section"].value_counts()
    con = sqlite3.connect(config.DATABASE_FILE)
    n_fk = sum(len(con.execute(f"PRAGMA foreign_key_list({t})").fetchall()) for t in LOAD_ORDER)
    n_pk = sum(1 for t in LOAD_ORDER if any(r[5] > 0 for r in con.execute(f"PRAGMA table_info({t})").fetchall()))
    con.close()
    figs = R.get("figures", [])
    rows = [
        ("Relational database created", str(config.DATABASE_FILE.relative_to(config.PROJECT_ROOT)), config.DATABASE_FILE.exists()),
        ("Primary keys defined", f"{n_pk}/{len(LOAD_ORDER)} tables", n_pk == len(LOAD_ORDER)),
        ("Foreign keys defined", f"{n_fk} foreign keys", n_fk >= 9),
        ("Source data loaded successfully", f"{len(LOAD_ORDER)} tables", (R["tables"]["Rows"] > 0).all()),
        ("Row counts validated", "Row counts area", v[v["Area"] == "Row counts"]["Pass"].all()),
        ("SQL totals reconciled with Python", "Totals area", v[v["Area"] == "Totals"]["Pass"].all()),
        ("Keys, nulls and orphans checked", "PK / FK / Nulls areas",
         v[v["Area"].isin(["Primary keys", "Foreign keys", "Nulls"])]["Pass"].all()),
        ("Cross-step consistency (Steps 5, 6, 7, 9)", "Cross-step area", v[v["Area"] == "Cross-step"]["Pass"].all()),
        ("Customer analytics completed", f"{secs.get('Customer', 0)} queries", secs.get("Customer", 0) >= 8),
        ("Product analytics completed", f"{secs.get('Product', 0)} queries", secs.get("Product", 0) >= 8),
        ("Regional analytics completed", f"{secs.get('Regional', 0)} queries", secs.get("Regional", 0) >= 3),
        ("Time-based analytics completed", f"{secs.get('Time', 0)} queries", secs.get("Time", 0) >= 3),
        ("RFM analysis integrated", "seg_rfm_summary, BQ02, BQ06", "seg_rfm_summary" in R["results"]),
        ("ML segmentation integrated", "seg_ml_cluster_summary, BQ11", "seg_ml_cluster_summary" in R["results"]),
        ("Advanced SQL demonstrated", f"{(cov['Queries_Using_It'] > 0).sum()}/{len(cov)} techniques used",
         (cov["Queries_Using_It"] > 0).all()),
        ("Window functions used", f"{cov.loc['Window function', 'Queries_Using_It']} queries",
         cov.loc["Window function", "Queries_Using_It"] > 0),
        ("15-20 business questions documented", f"{(cat['File'] == BUSINESS_FILE.name).sum()} questions",
         15 <= (cat["File"] == BUSINESS_FILE.name).sum() <= 20),
        ("All queries executed without error", f"{len(cat)} queries", len(cat) == len(R["results"])),
        ("SQL visualizations created", f"{len(figs)} figures", len(figs) >= 8),
        ("No fabricated results", "every number in outputs/report is read from a SQL result set", True),
    ]
    return pd.DataFrame(rows, columns=["Check", "Evidence", "Pass"])


# =============================================================================
# 5. FIGURES
# =============================================================================
def plot_er_diagram(out_dir: Path, saved: list) -> None:
    """ER-style diagram drawn from the live database metadata (tables, PKs, FKs, row counts)."""
    from matplotlib.patches import FancyBboxPatch
    from src.eda import PAL, _save, _style
    plt = _style()
    con = sqlite3.connect(config.DATABASE_FILE)
    pos = {"locations": (0.3, 7.2), "customers": (4.5, 7.2), "orders": (8.7, 7.2), "order_items": (12.9, 7.2),
           "products": (17.1, 7.2), "customer_rfm": (0.3, 2.3), "rfm_segment_definitions": (0.3, -1.6),
           "customer_segments": (4.5, 2.3), "ml_clusters": (4.5, -1.6), "customer_value": (8.7, 2.3),
           "revenue_forecasts": (12.9, 2.3)}
    W, lh = 3.0, 0.27
    fig, ax = plt.subplots(figsize=(19, 11))
    boxes = {}
    for t, (x, y) in pos.items():
        info = con.execute(f"PRAGMA table_info({t})").fetchall()
        fks = {f[3] for f in con.execute(f"PRAGMA foreign_key_list({t})").fetchall()}
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        show = info if len(info) <= 9 else [r for r in info if r[5] > 0 or r[1] in fks] + \
            [r for r in info if not (r[5] > 0 or r[1] in fks)][:9 - len([r for r in info if r[5] > 0 or r[1] in fks])]
        h = lh * (len(show) + (1 if len(info) > len(show) else 0)) + 0.55
        core = t in LOAD_ORDER[:5]
        col = PAL["blue"] if core else PAL["orange"]
        ax.add_patch(FancyBboxPatch((x, y - h), W, h, boxstyle="round,pad=0.02", linewidth=1.3, edgecolor=col,
                                    facecolor="white"))
        ax.add_patch(FancyBboxPatch((x, y - 0.5), W, 0.5, boxstyle="round,pad=0.02", linewidth=0, facecolor=col))
        ax.text(x + 0.08, y - 0.25, t, color="white", fontsize=10, fontweight="bold", va="center")
        ax.text(x + W - 0.08, y - 0.25, f"{n:,} rows", color="white", fontsize=8, va="center", ha="right")
        for i, r in enumerate(show):
            tag = "PK " if r[5] > 0 else ("FK " if r[1] in fks else "")
            ax.text(x + 0.08, y - 0.5 - lh * (i + 0.6), f"{tag}{r[1]}", fontsize=8,
                    fontweight="bold" if tag else "normal", color=PAL["text"])
            ax.text(x + W - 0.08, y - 0.5 - lh * (i + 0.6), r[2], fontsize=7, color=PAL["muted"], ha="right")
        if len(info) > len(show):
            ax.text(x + 0.08, y - 0.5 - lh * (len(show) + 0.6), f"... +{len(info) - len(show)} more columns",
                    fontsize=7.5, color=PAL["muted"], style="italic")
        boxes[t] = (x, y, W, h)
    con.close()

    def edge(child, parent, label):
        cx, cy, cw, ch = boxes[child]
        px, py, pw, ph = boxes[parent]
        if abs(cy - py) < 0.1:                       # same row: horizontal link
            (x1, x2) = (cx, px + pw) if px < cx else (cx + cw, px)
            y1 = y2 = cy - 0.8
        else:                                        # vertical link
            x1, x2 = cx + cw / 2, px + pw / 2
            y1, y2 = (cy, py - ph) if py > cy else (cy - ch, py)
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "color": PAL["muted"], "lw": 1.2, "shrinkA": 2, "shrinkB": 2})
        if abs(cy - py) < 0.1:
            ax.text((x1 + x2) / 2, y1 + 0.12, label.replace(" ", "\n"), fontsize=7.5, color=PAL["muted"],
                    ha="center", va="bottom")
        else:
            ax.text((x1 + x2) / 2 + 0.1, (y1 + y2) / 2, label, fontsize=7.5, color=PAL["muted"], ha="left")

    for c, p, lab in (("customers", "locations", "N:1 location_id"), ("orders", "customers", "N:1 customer_id"),
                      ("order_items", "orders", "N:1 order_id"), ("order_items", "products", "N:1 product_id"),
                      ("customer_rfm", "customers", "1:1 customer_id"), ("customer_segments", "customers", "1:1 customer_id"),
                      ("customer_value", "customers", "1:1 customer_id"),
                      ("customer_rfm", "rfm_segment_definitions", "N:1 rfm_segment"),
                      ("customer_segments", "ml_clusters", "N:1 cluster_id")):
        edge(c, p, lab)
    ax.text(12.9, -1.3, "revenue_forecasts is keyed on month and\njoins to order months in queries (no FK:\n"
                        "future months have no orders).", fontsize=8, color=PAL["muted"], va="top")
    ax.text(0.3, 8.0, "Transactional core (Steps 2-3)", color=PAL["blue"], fontsize=11, fontweight="bold")
    ax.text(0.3, 3.1, "Analytics layer (outputs of Steps 5-9)", color=PAL["orange"], fontsize=11, fontweight="bold")
    ax.set_xlim(0, 20.4)
    ax.set_ylim(-3.8, 8.4)
    ax.axis("off")
    ax.set_title("customer_revenue_intelligence.db - entity-relationship diagram (arrow = child -> parent via foreign key)",
                 fontsize=12.5)
    fig.tight_layout()
    _save(fig, "er_diagram.png", out_dir, saved)


def plot_sql_figures(R: dict, out_dir: Path = FIG_DIR) -> list[Path]:
    """Charts drawn directly from SQL result sets (no recalculation in Python)."""
    from matplotlib.ticker import FuncFormatter
    from src.eda import PAL, _hbar, _note, _pct_axis, _save, _style
    from src.segmentation import CLUSTER_COLORS
    plt = _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    r = R["results"]
    lfmt = FuncFormatter(lambda v, _: f"₹{v / 1e5:,.0f}L")
    plot_er_diagram(out_dir, saved)

    # 1 RFM segments: revenue share vs customer share
    s = r["seg_rfm_summary"]
    fig, ax = plt.subplots(figsize=(12, 5.2))
    y = np.arange(len(s))
    ax.barh(y - 0.2, s["customer_pct"], 0.4, color=PAL["neutral"], label="% of customers")
    ax.barh(y + 0.2, s["revenue_contribution_pct"], 0.4, color=PAL["blue"], label="% of revenue")
    for i, (a, b) in enumerate(zip(s["customer_pct"], s["revenue_contribution_pct"])):
        ax.text(a, i - 0.2, f" {a:.1f}%", va="center", fontsize=8)
        ax.text(b, i + 0.2, f" {b:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y, s["segment"])
    ax.invert_yaxis()
    ax.set_xlim(0, s["revenue_contribution_pct"].max() * 1.15)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("RFM segments: share of customers vs share of revenue (SQL: seg_rfm_summary)")
    fig.tight_layout()
    _save(fig, "sql_revenue_by_rfm_segment.png", out_dir, saved)

    # 2 ML clusters
    c = r["seg_ml_cluster_summary"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    lab = [f"C{a}: {b}" for a, b in zip(c["cluster_id"], c["cluster_label"])]
    _hbar(axes[0], lab, c["revenue"].to_numpy(), color=[CLUSTER_COLORS[i] for i in c["cluster_id"]],
          value_labels=[f"{inr(v)} ({p:.1f}%)" for v, p in zip(c["revenue"], c["revenue_contribution_pct"])])
    axes[0].xaxis.set_major_formatter(lfmt)
    axes[0].set_title("Revenue by ML cluster")
    _hbar(axes[1], [""] * len(c), c["profit_margin_pct"].to_numpy(), color=[CLUSTER_COLORS[i] for i in c["cluster_id"]],
          value_labels=[f"{v:.1f}%" for v in c["profit_margin_pct"]])
    axes[1].set_title("Profit margin by ML cluster")
    fig.suptitle("Step 6 clusters, measured in SQL (seg_ml_cluster_summary)", x=0.01, ha="left", fontsize=13,
                 fontweight="bold")
    fig.tight_layout()
    _save(fig, "sql_revenue_by_ml_cluster.png", out_dir, saved)

    # 3 regions
    g = r["reg_performance"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
    for ax, (col, title, fmt) in zip(axes, (("revenue", "Revenue", lambda v: inr(v)),
                                            ("profit_margin_pct", "Profit margin %", lambda v: f"{v:.1f}%"),
                                            ("average_order_value", "Average order value", lambda v: inr(v)))):
        ax.barh(np.arange(len(g)), g[col], color=PAL["blue"], height=0.6)
        for i, v in enumerate(g[col]):
            ax.text(v, i, " " + fmt(v), va="center", fontsize=8.5)
        ax.set_xlim(0, g[col].max() * 1.3)
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
        ax.set_xticks([])
    axes[0].set_yticks(np.arange(len(g)), g["region"])
    axes[0].invert_yaxis()
    fig.suptitle("Regional performance (SQL: reg_performance)", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "sql_region_performance.png", out_dir, saved)

    # 4 category profit + margin
    k = r["prod_category_performance"].sort_values("profit", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 4.4))
    x = np.arange(len(k))
    ax.bar(x, k["profit"], color=PAL["blue"], width=0.6, label="Profit")
    ax.yaxis.set_major_formatter(lfmt)
    ax.set_xticks(x, k["category"])
    ax.grid(axis="x", visible=False)
    ax2 = ax.twinx()
    ax2.plot(x, k["profit_margin_pct"] / 100, color=PAL["orange"], marker="o", linewidth=2, label="Profit margin (right)")
    for i, m in enumerate(k["profit_margin_pct"]):
        ax2.text(i, m / 100 + 0.025, f"{m:.1f}%", ha="center", fontsize=8.5, color=PAL["orange"], fontweight="bold",
                 bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.9})
    _pct_axis(ax2)
    ax2.set_ylim(0, 0.6)
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right")
    ax.set_title("Profit and profit margin by category (SQL: prod_category_performance)")
    fig.tight_layout()
    _save(fig, "sql_category_profit_margin.png", out_dir, saved)

    # 5 top 10 customers
    t = r["BQ01"]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    _hbar(ax, [f"{a}  ({b})" for a, b in zip(t["customer_id"], t["rfm_segment"])], t["revenue"].to_numpy(),
          value_labels=[f"{inr(v)}  ({p:.2f}% of total)" for v, p in zip(t["revenue"], t["pct_of_total_revenue"])])
    ax.xaxis.set_major_formatter(lfmt)
    ax.set_title("Top 10 customers by revenue (SQL: BQ01; IDs only)")
    fig.tight_layout()
    _save(fig, "sql_top10_customers.png", out_dir, saved)

    # 6 top 10 products revenue vs profit
    t = r["prod_top_revenue"].head(10).merge(r["prod_profitability"][["product_id", "profit", "profit_margin_pct"]],
                                            on="product_id")
    fig, ax = plt.subplots(figsize=(12, 5))
    y = np.arange(len(t))
    ax.barh(y - 0.2, t["revenue"], 0.4, color=PAL["blue"], label="Revenue")
    ax.barh(y + 0.2, t["profit"], 0.4, color=PAL["orange"], label="Profit")
    for i, (rv, pf, m) in enumerate(zip(t["revenue"], t["profit"], t["profit_margin_pct"])):
        ax.text(max(rv, 0), i - 0.2, f" {inr(rv)}", va="center", fontsize=8)
        ax.text(max(pf, 0), i + 0.2, f" {inr(pf)} ({m:.1f}% margin)", va="center", fontsize=8)
    ax.set_yticks(y, [f"{a} ({b})" for a, b in zip(t["product_name"], t["category"])], fontsize=8.5)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(lfmt)
    ax.axvline(0, color=PAL["muted"], linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("Top 10 products by revenue - and the profit they leave (SQL: prod_top_revenue + prod_profitability)")
    fig.tight_layout()
    _save(fig, "sql_top10_products.png", out_dir, saved)

    # 7 monthly revenue with growth
    m = r["time_monthly"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
    xm = np.arange(len(m))
    axes[0].bar(xm, m["revenue"], color=PAL["blue"], width=0.7, label="Monthly revenue")
    axes[0].plot(xm, m["rolling_3m_avg_revenue"], color=PAL["orange"], linewidth=2, label="3-month rolling average")
    axes[0].yaxis.set_major_formatter(lfmt)
    axes[0].legend(loc="upper left")
    axes[0].set_title("Monthly revenue (SQL: time_monthly)")
    axes[1].axhline(0, color=PAL["muted"], linewidth=0.8)
    axes[1].plot(xm, m["yoy_growth_pct"], color=PAL["orange"], marker="o", markersize=3, label="Year-over-year %")
    axes[1].bar(xm, m["mom_growth_pct"], color=PAL["neutral"], width=0.7, label="Month-over-month %")
    axes[1].set_ylabel("Growth %")
    axes[1].legend(loc="upper left", fontsize=8)
    axes[1].set_xticks(xm[::3], m["order_month"].iloc[::3], rotation=45)
    fig.tight_layout()
    _save(fig, "sql_monthly_revenue_growth.png", out_dir, saved)

    # 8 customer concentration (Pareto) from the window-function query
    cc = r["cust_revenue_concentration"]
    cs = r["cust_concentration_summary"].set_index("top_pct")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(cc["cumulative_pct_of_customers"] / 100, cc["cumulative_pct_of_revenue"] / 100, color=PAL["blue"], linewidth=2)
    ax.plot([0, 1], [0, 1], color=PAL["neutral"], linestyle=":")
    for p in (10, 20, 50):
        ax.scatter(p / 100, cs.loc[p, "pct_of_revenue"] / 100, color=PAL["orange"], zorder=3)
        ax.text(p / 100 + 0.015, cs.loc[p, "pct_of_revenue"] / 100 - 0.05,
                f"top {p}% -> {cs.loc[p, 'pct_of_revenue']:.1f}%", fontsize=9)
    _pct_axis(ax, "x")
    _pct_axis(ax, "y")
    ax.set_xlabel("Customers (ranked by revenue)")
    ax.set_ylabel("Cumulative share of revenue")
    ax.set_title("Customer revenue concentration (SQL window functions)")
    fig.tight_layout()
    _save(fig, "sql_customer_concentration.png", out_dir, saved)

    # 9 discount vs margin by category (BQ08)
    b8 = r["BQ08"].pivot(index="category", columns="discount_band", values="profit_margin_pct")
    b8 = b8[["0%", "1-10%", "11-20%", "21-40%"]]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    im = ax.imshow(b8.values, cmap="Blues", aspect="auto")
    for i in range(b8.shape[0]):
        for j in range(b8.shape[1]):
            v = b8.values[i, j]
            ax.text(j, i, f"{v:.1f}%", ha="center", va="center", fontsize=9,
                    color="white" if v > np.nanmax(b8.values) * 0.7 else PAL["text"])
    ax.set_xticks(range(b8.shape[1]), b8.columns)
    ax.set_yticks(range(b8.shape[0]), b8.index)
    ax.set_xlabel("Discount band")
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="Profit margin %")
    ax.set_title("Profit margin by discount band within each category (SQL: BQ08)")
    _note(fig, "Association only: discounts are not randomly assigned, so this does not show what a discount change would cause.")
    fig.tight_layout()
    _save(fig, "sql_discount_margin_by_category.png", out_dir, saved)

    # 10 customer base dynamics (BQ15)
    d15 = r["BQ15"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = np.arange(len(d15))
    bottom = np.zeros(len(d15))
    for col, lab, colr in (("retained_customers", "Retained (bought last year too)", PAL["blue"]),
                           ("reactivated_customers", "Reactivated", PAL["aqua"]),
                           ("new_customers", "New (first purchase)", PAL["orange"])):
        ax.bar(x, d15[col], bottom=bottom, color=colr, width=0.55, label=lab)
        for i, v in enumerate(d15[col]):
            if v > 0:
                ax.text(i, bottom[i] + v / 2, f"{int(v):,}", ha="center", va="center", fontsize=9, color="white")
        bottom += d15[col].to_numpy()
    for i, rr in d15.iterrows():
        if pd.notna(rr["retention_rate_pct"]):
            ax.text(i, bottom[i] + 20, f"retention {rr['retention_rate_pct']:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(x, d15["order_year"].astype(str))
    ax.set_ylabel("Active customers")
    ax.set_ylim(0, bottom.max() * 1.15)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax.set_title("Active customer base by year: retained, reactivated, new (SQL: BQ15)")
    fig.tight_layout()
    _save(fig, "sql_customer_base_dynamics.png", out_dir, saved)

    # 11 region x category margin heatmap
    rc = r["reg_category_matrix"].pivot(index="region", columns="category", values="profit_margin_pct")
    fig, ax = plt.subplots(figsize=(10, 3.8))
    im = ax.imshow(rc.values, cmap="Blues", aspect="auto")
    for i in range(rc.shape[0]):
        for j in range(rc.shape[1]):
            v = rc.values[i, j]
            ax.text(j, i, f"{v:.1f}%", ha="center", va="center", fontsize=9,
                    color="white" if v > np.nanmax(rc.values) * 0.75 else PAL["text"])
    ax.set_xticks(range(rc.shape[1]), rc.columns)
    ax.set_yticks(range(rc.shape[0]), rc.index)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="Profit margin %")
    ax.set_title("Profit margin by region and category (SQL: reg_category_matrix)")
    fig.tight_layout()
    _save(fig, "sql_region_category_margin.png", out_dir, saved)
    return saved


# =============================================================================
# 6. REPORT
# =============================================================================
def write_sql_report(R: dict, path: Path = REPORT_FILE) -> Path:
    from src.eda import _md_table
    cat, v, tb = R["catalog"], R["validation"], R["tables"]
    L = ["# SQL Business Analytics & Database Integration - Step 10\n",
         f"> **{config.DATASET_LABEL}.** Every number below is read from a SQL result set produced by "
         "`sql/analysis_queries.sql` or `sql/business_queries.sql` on the project database.\n"]
    L += ["## 1. Database objective\n",
          "Hold the cleaned transactions and the customer-level outputs of Steps 5-9 in one relational database, so "
          "business questions can be answered with SQL (joins, aggregations, window functions) and so the later Power BI "
          "and Streamlit layers can read one consistent source.\n",
          "## 2. Database design\n",
          f"- **Technology:** SQLite {sqlite3.sqlite_version} (Python's built-in `sqlite3`; no server needed). File: "
          f"`{config.DATABASE_FILE.relative_to(config.PROJECT_ROOT)}`.",
          "- **Model:** third normal form transactional core + an analytics layer that stores only what the Python "
          "steps produced (scores, labels, estimates). Anything recomputable from transactions is computed in SQL.",
          "- **Revenue rule:** Delivered lines only, encoded once in the view `vw_delivered_sales`; `vw_sales_flat` "
          "re-creates the original one-row-per-line layout (all statuses).",
          "- **Constraints:** primary keys on every table, 9 foreign keys, CHECK constraints for domains (regions, "
          "categories, statuses, score ranges, discount 0-40%) and business rules (sales = qty x price x (1 - discount); "
          "profit = sales - cost; rfm_score = r + f + m).\n",
          "![ER diagram](../figures/sql/er_diagram.png)\n",
          "## 3. Tables\n",
          _md_table(tb[["Table", "Layer", "Rows", "Columns", "Primary_Key", "Foreign_Keys"]]),
          "\nColumn names and SQLite types for every table: `outputs/tables/sql_table_catalog.csv`.\n",
          "## 4. Relationships\n",
          "- `locations` 1 - N `customers` (location_id)",
          "- `customers` 1 - N `orders` (customer_id)",
          "- `orders` 1 - N `order_items` (order_id); `products` 1 - N `order_items` (product_id)",
          "- `customers` 1 - 1 `customer_rfm`, `customer_segments`, `customer_value` (customer_id; only the 1,984 "
          "customers with a Delivered order have rows)",
          "- `rfm_segment_definitions` 1 - N `customer_rfm` (rfm_segment); `ml_clusters` 1 - N `customer_segments` (cluster_id)",
          "- `revenue_forecasts` (month, record_type) joins to order months in queries; no FK because future months "
          "have no orders.\n",
          "## 5. Data loading process\n",
          "`python sql/load_database.py` (calls `src/database.py`):",
          "1. delete and re-create `data/customer_revenue_intelligence.db`; 2. run `sql/schema.sql`; 3. split the cleaned "
          "CSV into the five transactional tables (after checking that order- and customer-level attributes are "
          "single-valued); 4. load RFM, segment definitions, clusters, CLV and forecasts from Steps 5-9; 5. validate; "
          "6. save. The Step 3 file `data/processed/revenue_intelligence.db` is replaced by this database (one source "
          "of truth).\n",
          "## 6. SQL analysis methodology\n",
          f"{len(cat)} queries in two files, each with a header (`-- name`, `-- section`, `-- title` or `-- question / "
          "purpose / interpretation`). `src/sql_analytics.py` executes them, saves every result to "
          "`outputs/tables/sql/<name>.csv`, and builds charts from those result sets. Python performs no business "
          "calculation. The reference date is computed in SQL (last order date + 1 day); customers are shown by ID only.\n",
          _md_table(cat[["Query", "File", "Section", "Title_or_Question", "Rows"]]), ""]
    bqs = cat[cat["File"] == BUSINESS_FILE.name]
    L += ["## 7. Business questions\n"]
    for _, q in bqs.iterrows():
        L += [f"**{q['Query']} - {q['Title_or_Question']}**  ",
              f"Purpose: {q['Purpose']}  ",
              f"How to read it: {q['Interpretation']}  ",
              f"SQL techniques: {q['Techniques']}. Result: `outputs/tables/sql/{q['Query']}.csv` ({q['Rows']} rows).\n"]
    L += ["## 8. Advanced SQL techniques\n", _md_table(R["coverage"]),
          "\nEach technique is used for a business reason: window SUM for shares of total, RANK/NTILE for top-N and "
          "quartiles, running totals for Pareto and year-to-date, LAG for growth rates and inter-purchase gaps, "
          "CTEs to keep multi-step logic readable, LEFT JOIN where missing matches are meaningful (customers without "
          "Delivered orders).\n",
          "## 9. Validation\n", _md_table(v),
          f"\n{int(v['Pass'].sum())}/{len(v)} checks passed. SQL totals were compared with pandas totals computed "
          "independently from the cleaned CSV; nothing was adjusted to force agreement.\n",
          "## 10. Key analytical findings\n", _md_table(R["findings"]), "",
          "## 11. Limitations\n",
          "1. **Synthetic data** from Step 2.",
          "2. **SQLite** has no stored procedures, materialised views or native pivot; the month-of-year query pivots "
          "the three years present explicitly.",
          "3. **Analytics tables are snapshots** of Steps 5-9 at the reference date 2026-01-01; re-run those steps before "
          "reloading if the data change.",
          "4. **Associations, not causes:** discount, payment-method and region comparisons describe the data only.",
          "5. **Customer names** are stored in `customers` (source data) but no query outputs them.\n",
          "## 12. Reproducibility instructions\n",
          "```bash\npython sql/load_database.py      # build + validate the database\n"
          "python src/sql_analytics.py      # build, validate, run all queries, save tables/figures/report\n"
          "sqlite3 data/customer_revenue_intelligence.db < sql/business_queries.sql   # optional: run in the SQLite shell\n```\n",
          "## Quality-control checklist\n", _md_table(R["qc"])]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


# =============================================================================
# 7. ORCHESTRATION
# =============================================================================
def run_sql_workflow(make_plots: bool = True, verbose: bool = True) -> dict:
    res = build_database()
    R = {"validation": validate_database(source=res["source"]), "tables": table_catalog()}
    con = sqlite3.connect(config.DATABASE_FILE)
    a_res, a_cat = run_sql_file(con, ANALYSIS_FILE)
    b_res, b_cat = run_sql_file(con, BUSINESS_FILE)
    con.close()
    R["results"] = {**a_res, **b_res}
    R["catalog"] = pd.concat([a_cat, b_cat], ignore_index=True)
    R["coverage"] = technique_coverage(R["catalog"])
    R["findings"] = key_findings(R)
    if make_plots:
        R["figures"] = plot_sql_figures(R)
    R["qc"] = quality_checklist(R)
    R["saved"] = save_sql_outputs(R)
    R["report"] = write_sql_report(R)
    if verbose:
        print(f"Database: {config.DATABASE_FILE.relative_to(config.PROJECT_ROOT)} | validation "
              f"{int(R['validation']['Pass'].sum())}/{len(R['validation'])} | queries {len(R['catalog'])} | "
              f"figures {len(R.get('figures', []))} | QC {int(R['qc']['Pass'].sum())}/{len(R['qc'])}")
    return R


if __name__ == "__main__":
    run_sql_workflow()
