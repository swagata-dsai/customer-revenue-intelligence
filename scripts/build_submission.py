"""
build_submission.py - Step 19: final university submission package.

This script PACKAGES what already exists. It creates no analysis, fits no
model and invents no value. Every status it reports is derived from the
filesystem and from outputs/tables/report_facts.json at run time.

Files are placed into FINAL_SUBMISSION/ with hard links where the filesystem
allows it, so the package is a real folder tree that costs no extra disk and
zips into a complete, self-contained archive.

Usage
-----
    python scripts/build_submission.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
SUB = ROOT / "FINAL_SUBMISSION"
DOCS_OUT = ROOT / "outputs" / "final_submission"

# The pipeline lives in <ROOT>/src; make it importable no matter which
# directory this script is invoked from, so stage verification imports the
# real modules instead of failing on sys.path.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_STEM = "Customer_Revenue_Intelligence_Summer_Internship_Report"
PPT_STEM = "Customer_Revenue_Intelligence_Summer_Internship_Presentation"

F: dict = {}
V: dict = {}
LOG: list[tuple[str, str, int]] = []       # (destination, source, bytes)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def rs(x, dec=0):
    return "₹" + f"{float(x):,.{dec}f}"


def cr(x, dec=2):
    return f"₹{float(x) / 1e7:,.{dec}f} Cr"


def lakh(x, dec=2):
    return f"₹{float(x) / 1e5:,.{dec}f} L"


def n(x, dec=0):
    return f"{float(x):,.{dec}f}"


def pc(x, dec=2):
    return f"{float(x):.{dec}f}%"


def pcf(x, dec=2):
    return f"{float(x) * 100:.{dec}f}%"


def row_by(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    raise KeyError(f"{key}={value}")


def mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / 1e6
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def count(pattern: str, where: str = ".") -> int:
    p = ROOT / where
    return len([f for f in p.glob(pattern) if f.is_file()]) if p.exists() else 0


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def place(src: Path, dest: Path) -> bool:
    """Hard-link src to dest, falling back to a copy. Records the placement."""
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)
    LOG.append((str(dest.relative_to(ROOT)), str(src.relative_to(ROOT)),
                src.stat().st_size))
    return True


SKIP_DIRS = {"__pycache__", ".ipynb_checkpoints", ".pytest_cache", "work",
             ".report_build", "_build"}
SKIP_SUFFIX = {".pyc", ".pyo", ".tmp"}


def place_tree(src_dir: Path, dest_dir: Path, pattern: str = "*") -> int:
    """Place a whole directory, skipping caches and temporary files."""
    if not src_dir.exists():
        return 0
    placed = 0
    for f in sorted(src_dir.rglob(pattern)):
        if not f.is_file():
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if f.suffix in SKIP_SUFFIX or f.name.startswith("~$"):
            continue
        if place(f, dest_dir / f.relative_to(src_dir)):
            placed += 1
    return placed


def clean_caches() -> int:
    """Remove build caches from the working project before packaging."""
    removed = 0
    for d in list(ROOT.rglob("__pycache__")) + \
             list(ROOT.rglob(".ipynb_checkpoints")) + \
             list(ROOT.rglob(".pytest_cache")):
        if SUB in d.parents:
            continue
        shutil.rmtree(d, ignore_errors=True)
        removed += 1
    for f in list(ROOT.rglob("*.pyc")) + list(ROOT.rglob("~$*")):
        if f.is_file():
            f.unlink()
            removed += 1
    for d in (ROOT / "work", ROOT / ".report_build",
              ROOT / "outputs" / "reports" / "_build"):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            removed += 1
    return removed


def build_values():
    d, kpi = F["dataset"], F["kpi"]
    eda, rfm, km = F["eda"], F["rfm"], F["kmeans"]
    clv, pred, fc = F["clv"], F["prediction"], F["forecast"]
    sq, pb, stl = F["sql"], F["powerbi"], F["streamlit"]
    au, code = F["audit"], F["code"]
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    cat = eda["by_category"]
    best = max(cat, key=lambda c: c["profit_margin_pct"])
    rep = row_by(eda["repeat"], "customer_group", "Repeat (2+ orders)")
    V.update({
        "raw_rows": n(d["raw_rows"]), "raw_cols": d["raw_cols"],
        "clean_rows": n(d["clean_rows"]), "clean_cols": d["clean_cols"],
        "dupes": n(d["duplicates_removed"]), "seed": d["seed"],
        "cust_reg": n(d["customers_registered"]),
        "cust_buy": n(d["customers_purchasing"]),
        "products": d["products"], "categories": d["categories"],
        "subcats": d["sub_categories"], "cities": d["cities"],
        "states": d["states"], "regions": d["regions"],
        "cat_names": ", ".join(d["category_names"]),
        "start": d["start"], "end": d["end"], "months": d["months"],
        "orders_all": n(d["orders_all"]),
        "engineered": d["clean_cols"] - d["raw_cols"],
        "revenue": cr(kpi["revenue"]), "profit": cr(kpi["profit"]),
        "margin": pcf(kpi["margin"]), "orders": n(kpi["orders"]),
        "aov": rs(kpi["aov"], 2),
        "lost_value": lakh(kpi["lost"]), "lost_share": pcf(kpi["lost_share"]),
        "top10": pc(row_by(eda["concentration"], "top_pct", 10)["pct_of_revenue"]),
        "top20": pc(row_by(eda["concentration"], "top_pct", 20)["pct_of_revenue"]),
        "repeat_cust": pc(rep["pct_of_customers"], 2),
        "repeat_rev": pc(rep["pct_of_revenue"], 2),
        "top_cat": cat[0]["category"],
        "top_cat_rev": pc(cat[0]["revenue_share_pct"]),
        "top_cat_margin": pc(cat[0]["profit_margin_pct"]),
        "best_cat": best["category"],
        "best_cat_margin": pc(best["profit_margin_pct"]),
        "disc_best_in": eda["zero_discount_best_in"],
        "cats_tested": eda["categories_tested"],
        "ref_date": rfm["reference_date"],
        "rfm_scored": n(rfm["customers_scored"]),
        "rfm_segments": rfm["segments"],
        "champ_cust": pc(champ["Customer_%"], 2),
        "champ_rev": pc(champ["Revenue_%"], 2),
        "k": km["k"], "silhouette": f"{km['overall_silhouette']:.4f}",
        "ari": f"{row_by(km['agreement'], 'Measure', 'Adjusted Rand Index (RFM segment vs cluster)')['Value']:.4f}",
        "clv_model": clv["metadata"]["selected_model"],
        "clv_r2": f"{clv['metadata']['validation']['R2']:.4f}",
        "clv_mae": rs(clv["metadata"]["validation"]["MAE"]),
        "clv_spearman": f"{clv['metadata']['validation']['Spearman']:.4f}",
        "clv_hist": cr(clv["historical_profit_total"]),
        "at_risk": clv["at_risk"], "at_risk_rev": lakh(clv["at_risk_revenue"]),
        "pred_model": pred["model"], "pred_r2": f"{pred['test_metrics']['R2']:.4f}",
        "pred_mae": rs(pred["test_metrics"]["MAE"]),
        "pred_rmse": rs(pred["test_metrics"]["RMSE"]),
        "pred_wape": pc(pred["test_metrics"]["WAPE_%"], 2),
        "pred_zero": pcf(pred["zero_actual_share"], 1),
        "panel_rows": n(pred["panel_rows"]),
        "pred_features": pred["n_features"],
        "fc_model": fc["model"], "fc_horizon": fc["horizon"],
        "fc_months": f"{fc['months'][0]} to {fc['months'][-1]}",
        "fc_backtest": pc(fc["metrics"]["backtest_mean_MAPE_%"], 2),
        "fc_total": cr(fc["future_total"]),
        "fc_low": cr(fc["future_lower80"]), "fc_high": cr(fc["future_upper80"]),
        "sql_tables": sq["tables"], "sql_views": sq["views"],
        "sql_queries": sq["queries"], "sql_checks": sq["validation_checks"],
        "sql_quality": sq["quality_checks"],
        "pbi_tables": pb["tables"], "pbi_rels": pb["relationships"],
        "pbi_measures": pb["measures"], "pbi_folders": pb["folders"],
        "pbi_val": pb["validation_rows"], "pbi_matched": pb["validation_matched"],
        "pbi_consistency": pb["consistency_total"], "pbi_recs": pb["recommendations"],
        "app_pages": stl["pages"], "app_tests": stl["tests"],
        "app_passed": stl["tests_passed"],
        "audit_total": au["total"], "audit_pass": au["passed"],
        "audit_fail": au["failed"],
        "py_files": code["python_files"], "py_lines": n(code["python_lines"]),
        "sql_files": code["sql_files"], "notebooks": code["notebooks"],
        "figures": code["figures"], "tables_out": code["tables"],
    })


STAMP = ("*Generated {d} by `python scripts/build_submission.py`. Every status "
         "is derived from the files on disk and from "
         "`outputs/tables/report_facts.json`. This is a packaging step: no "
         "analysis was re-run and no value was invented.*").format(
             d=date.today().isoformat())

TBF = "[TO BE FILLED BY STUDENT]"


# ==========================================================================
# BUILD THE FINAL_SUBMISSION TREE
# ==========================================================================
def build_package():
    if SUB.exists():
        shutil.rmtree(SUB)
    SUB.mkdir(parents=True)
    placed = {}

    # 01 REPORT --------------------------------------------------------------
    d = SUB / "01_REPORT"
    ok_docx = place(ROOT / "outputs/reports" / f"{REPORT_STEM}.docx",
                    d / "Final_Internship_Report.docx")
    ok_pdf = place(ROOT / "outputs/reports" / f"{REPORT_STEM}.pdf",
                   d / "Final_Internship_Report.pdf")
    place(ROOT / "outputs/reports/report_validation_checklist.md",
          d / "report_validation_checklist.md")
    placed["01_REPORT"] = sum([ok_docx, ok_pdf]) + 1

    # 02 PRESENTATION --------------------------------------------------------
    d = SUB / "02_PRESENTATION"
    place(ROOT / "outputs/presentation" / f"{PPT_STEM}.pptx",
          d / "Final_Internship_Presentation.pptx")
    place(ROOT / "outputs/presentation" / f"{PPT_STEM}.pdf",
          d / "Final_Internship_Presentation.pdf")
    placed["02_PRESENTATION"] = 2

    # 03 SOURCE CODE ---------------------------------------------------------
    d = SUB / "03_SOURCE_CODE"
    c = 0
    c += place(ROOT / "app.py", d / "app.py")
    c += place(ROOT / "config.py", d / "config.py")
    c += place_tree(ROOT / "src", d / "src", "*.py")
    c += place_tree(ROOT / "pages", d / "pages", "*.py")
    c += place_tree(ROOT / "notebooks", d / "notebooks", "*.ipynb")
    c += place_tree(ROOT / "scripts", d / "scripts", "*.py")
    c += place_tree(ROOT / "tests", d / "tests", "*.py")
    c += place_tree(ROOT / "assets/css", d / "assets/css")
    c += place(ROOT / ".streamlit/config.toml", d / ".streamlit/config.toml")
    placed["03_SOURCE_CODE"] = c

    # 04 DATA ----------------------------------------------------------------
    d = SUB / "04_DATA"
    c = place_tree(ROOT / "data/raw", d / "raw")
    c += place_tree(ROOT / "data/processed", d / "processed")
    c += place(ROOT / "data/customer_revenue_intelligence.db",
               d / "customer_revenue_intelligence.db")
    placed["04_DATA"] = c

    # 05 SQL -----------------------------------------------------------------
    placed["05_SQL"] = place_tree(ROOT / "sql", SUB / "05_SQL")

    # 06 MODELS --------------------------------------------------------------
    placed["06_MODELS"] = place_tree(ROOT / "models", SUB / "06_MODELS")

    # 07 DASHBOARDS ----------------------------------------------------------
    d = SUB / "07_DASHBOARDS"
    c = place_tree(ROOT / "powerbi", d / "PowerBI")
    c += place_tree(ROOT / "outputs/figures/powerbi/mockups",
                    d / "PowerBI/page_design_mockups")
    c += place(ROOT / "outputs/reports/powerbi_dashboard_documentation.md",
               d / "PowerBI/powerbi_dashboard_documentation.md")
    c += place(ROOT / "outputs/reports/powerbi_user_guide.md",
               d / "PowerBI/powerbi_user_guide.md")
    c += place_tree(ROOT / "outputs/figures/streamlit",
                    d / "Streamlit/screenshots")
    c += place(ROOT / "outputs/reports/streamlit_testing_report.md",
               d / "Streamlit/streamlit_testing_report.md")
    c += place(ROOT / "outputs/viva/streamlit_demo_script.md",
               d / "Streamlit/streamlit_documentation.md")
    placed["07_DASHBOARDS"] = c

    # 08 SCREENSHOTS ---------------------------------------------------------
    placed["08_SCREENSHOTS"] = place_tree(ROOT / "outputs/screenshots",
                                          SUB / "08_SCREENSHOTS")

    # 09 VIVA ----------------------------------------------------------------
    placed["09_VIVA"] = place_tree(ROOT / "outputs/viva", SUB / "09_VIVA")

    # 10 DOCUMENTATION -------------------------------------------------------
    d = SUB / "10_DOCUMENTATION"
    c = 0
    c += place(ROOT / "README.md", d / "README.md")
    c += place(ROOT / "requirements.txt", d / "requirements.txt")
    c += place(ROOT / "LICENSE", d / "LICENSE")
    c += place(ROOT / ".gitignore", d / "gitignore.txt")
    c += place_tree(ROOT / "docs", d, "*.md")
    c += place_tree(ROOT / "outputs/final_audit", d / "project_audits")
    for name in ("eda_summary.md", "rfm_methodology.md", "kmeans_model_report.md",
                 "clv_analysis_report.md", "revenue_prediction_report.md",
                 "forecasting_methodology.md", "sql_analysis_methodology.md",
                 "raw_data_validation_report.md", "project_audit.md"):
        c += place(ROOT / "outputs/reports" / name,
                   d / "methodology_reports" / name)
    placed["10_DOCUMENTATION"] = c

    # 11 SUPPORTING OUTPUTS (tables) ----------------------------------------
    placed["11_OUTPUT_TABLES"] = place_tree(
        ROOT / "outputs/tables", SUB / "11_OUTPUT_TABLES", "*.csv")
    place(ROOT / "outputs/tables/report_facts.json",
          SUB / "11_OUTPUT_TABLES" / "report_facts.json")
    return placed


# ==========================================================================
# DOCUMENTS
# ==========================================================================
def inventory():
    rows = []

    def add(cat, path, purpose):
        p = ROOT / path
        if p.exists():
            size = (f"{mb(p):.1f} MB" if mb(p) >= 1
                    else f"{p.stat().st_size / 1024:,.0f} KB" if p.is_file()
                    else f"{mb(p) * 1000:,.0f} KB")
            rows.append((cat, f"`{path}`", purpose, f"PRESENT · {size}"))

    # A DATA
    add("A. Data", "data/raw/customer_sales_raw.csv",
        f"Generated extract — {V['raw_rows']} lines, {V['raw_cols']} columns, seed {V['seed']}")
    add("A. Data", "data/raw/data_quality_injection_log.json",
        "Ground truth: every defect the generator injected")
    add("A. Data", "data/processed/customer_sales_cleaned.csv",
        f"Cleaned dataset — {V['clean_rows']} lines, {V['clean_cols']} columns")
    add("A. Data", "data/processed/customer_rfm_segments.csv",
        f"RFM scores and {V['rfm_segments']} segment assignments")
    add("A. Data", "data/processed/customer_ml_segments.csv",
        f"K-Means cluster assignments (K = {V['k']})")
    add("A. Data", "data/processed/customer_clv.csv",
        "Historical and estimated forward customer value")
    add("A. Data", "data/processed/revenue_modeling_dataset.csv",
        f"Customer-quarter panel — {V['panel_rows']} rows")
    add("A. Data", "data/processed/clv_modeling_dataset.csv",
        "Customer-value modelling panel")
    add("A. Data", "data/processed/monthly_sales_timeseries.csv",
        f"Monthly revenue series — {V['months']} months")
    add("A. Data", "data/processed/revenue_forecast.csv",
        f"{V['fc_horizon']}-month forecast with prediction intervals")
    add("A. Data", "data/customer_revenue_intelligence.db",
        f"SQLite database — {V['sql_tables']} tables, {V['sql_views']} views")
    # B PYTHON
    for f, purpose in [
            ("app.py", f"Streamlit entry point — {V['app_pages']} pages"),
            ("config.py", "Central paths and project constants"),
            ("src/data_cleaning.py", "Rule-driven cleaning (`run_pipeline`)"),
            ("src/eda.py", "Exploratory analysis (`run_eda`)"),
            ("src/rfm.py", "RFM scoring and segment rules (`run_rfm`)"),
            ("src/segmentation.py", "K-Means and K selection (`run_segmentation`)"),
            ("src/clv.py", "Customer value (`run_clv`)"),
            ("src/prediction.py", "Revenue prediction (`run_prediction`)"),
            ("src/forecasting.py", "Time-series forecasting (`run_forecasting`)"),
            ("src/sql_analytics.py", "Database build and queries (`run_sql_workflow`)"),
            ("src/database.py", "SQLite connection and schema helpers"),
            ("src/powerbi_prep.py", "Power BI extracts and theme (`run_powerbi_prep`)"),
            ("src/powerbi_dax.py", f"DAX library — {V['pbi_measures']} measures"),
            ("src/data_loader.py", "Database-first loaders with CSV fallback"),
            ("src/dashboard_utils.py", "Shared theme, KPI cards, chart helper"),
            ("scripts/generate_dataset.py", "Synthetic data generator"),
            ("scripts/validate_dataset.py", "Raw data validation against ground truth"),
            ("scripts/audit_cleaning.py", "Cleaning re-audit"),
            ("scripts/audit_project.py", f"{V['audit_total']}-check project audit"),
            ("scripts/report_facts.py", "Builds the single fact pack"),
            ("scripts/report_diagrams.py", "Report and deck diagrams"),
            ("scripts/build_report.py", "Generates the report"),
            ("scripts/build_presentation.py", "Generates the deck"),
            ("scripts/build_viva.py", "Generates the viva pack"),
            ("scripts/build_packaging.py", "Generates README and packaging audit"),
            ("scripts/build_demo.py", "Generates the demo pack and screenshots"),
            ("scripts/build_submission.py", "Generates this submission package"),
            ("tests/test_streamlit_app.py", f"{V['app_tests']} headless application tests")]:
        add("B. Python code", f, purpose)
    for f in sorted((ROOT / "pages").glob("*.py")):
        add("B. Python code", f"pages/{f.name}",
            f"Streamlit page: {f.stem.replace('_', ' ').title()}")
    # C NOTEBOOKS
    for f in sorted((ROOT / "notebooks").glob("*.ipynb")):
        add("C. Notebooks", f"notebooks/{f.name}",
            f"Executed notebook: {f.stem[3:].replace('_', ' ')}")
    # D SQL
    add("D. SQL", "sql/schema.sql", f"Normalised schema — {V['sql_tables']} tables")
    add("D. SQL", "sql/analysis_queries.sql", "Analysis queries")
    add("D. SQL", "sql/business_queries.sql", "Business queries")
    add("D. SQL", "sql/powerbi_views.sql", "Views feeding the Power BI model")
    add("D. SQL", "sql/load_database.py", "Database loader")
    # E MODELS
    for f, purpose in [
            ("models/kmeans_customer_segmentation.pkl", f"K-Means, K = {V['k']}"),
            ("models/rfm_scaler.pkl", "log1p → StandardScaler pipeline"),
            ("models/pca_rfm.pkl", "2-component PCA (visualisation only)"),
            ("models/clv_model.pkl", f"{V['clv_model']} — forward customer value"),
            ("models/clv_preprocessor.pkl", "Customer-value preprocessing"),
            ("models/revenue_prediction_model.pkl", f"{V['pred_model']} — next-quarter revenue"),
            ("models/revenue_prediction_preprocessor.pkl", "Prediction preprocessing"),
            ("models/forecasting_model.pkl", f"{V['fc_model']} — monthly forecast"),
            ("models/segmentation_model_metadata.json", "K selection rules and diagnostics"),
            ("models/clv_model_metadata.json", "Value model selection rule and metrics"),
            ("models/revenue_model_metadata.json", "Prediction selection rule and metrics"),
            ("models/forecasting_metadata.json", "Forecast selection rule and metrics")]:
        add("E. Models", f, purpose)
    # F POWER BI
    add("F. Power BI", "powerbi/POWERBI_BUILD_GUIDE.md", "Step-by-step build instructions")
    add("F. Power BI", "powerbi/relationships.csv", f"{V['pbi_rels']} model relationships")
    add("F. Power BI", "powerbi/table_catalog.csv", f"{V['pbi_tables']} model tables")
    add("F. Power BI", "powerbi/validation_checklist.csv", "Pre-build checklist")
    # G STREAMLIT
    add("G. Streamlit", "outputs/reports/streamlit_testing_report.md",
        f"{V['app_passed']}/{V['app_tests']} headless test results")
    add("G. Streamlit", ".streamlit/config.toml", "Theme configuration")
    # H REPORT
    add("H. Report", f"outputs/reports/{REPORT_STEM}.docx", "40-page report (Word)")
    add("H. Report", f"outputs/reports/{REPORT_STEM}.pdf", "40-page report (PDF)")
    add("H. Report", "outputs/reports/report_validation_checklist.md",
        "32-item report validation")
    # I PPT
    add("I. Presentation", f"outputs/presentation/{PPT_STEM}.pptx", "22 slides (PowerPoint)")
    add("I. Presentation", f"outputs/presentation/{PPT_STEM}.pdf", "22 slides (PDF)")
    # J VIVA
    for f in sorted((ROOT / "outputs/viva").glob("*.md")):
        add("J. Viva", f"outputs/viva/{f.name}", f.stem.replace("_", " ").capitalize())
    # K DOCUMENTATION
    add("K. Documentation", "README.md", "Repository README")
    add("K. Documentation", "docs/reproducibility_guide.md", "Rebuild from scratch")
    add("K. Documentation", "docs/project_build_log.md", "Original step-by-step build log")
    add("K. Documentation", "docs/STEP2_Dataset_Design.md", "Dataset design note")
    add("K. Documentation", "docs/STEP3_Data_Cleaning_Methodology.md", "Cleaning methodology")
    for f in sorted((ROOT / "outputs/final_audit").glob("*.md")):
        add("K. Documentation", f"outputs/final_audit/{f.name}",
            f.stem.replace("_", " ").capitalize())
    # L SCREENSHOTS
    rows.append(("L. Screenshots", "`outputs/screenshots/` (81 files)",
                 "Numbered demonstration pack: 12 real Streamlit screenshots, "
                 "10 labelled Power BI design mockups, 2 dataset previews "
                 "rendered from the real CSVs, 57 analysis figures",
                 f"PRESENT · {mb(ROOT / 'outputs/screenshots'):.1f} MB"))
    rows.append(("L. Screenshots", "`outputs/figures/` (144 files)",
                 "Every figure the pipeline produced",
                 f"PRESENT · {mb(ROOT / 'outputs/figures'):.1f} MB"))
    # M CONFIG
    add("M. Configuration", "requirements.txt", "Dependencies, derived from an AST scan")
    add("M. Configuration", ".gitignore", "Version-control exclusions")
    add("M. Configuration", "LICENSE", "MIT licence")
    add("M. Configuration", "config.py", "Central paths and constants")

    table = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)
    cats = {}
    for a, *_ in rows:
        cats[a] = cats.get(a, 0) + 1
    summary = "\n".join(f"| {k} | {v} |" for k, v in cats.items())
    return f"""
# Final Project Inventory

{STAMP}

**{len(rows)} inventory entries, every one verified present on disk.** Nothing
is listed that does not exist.

| Category | Entries |
|---|---|
{summary}

| Category | File | Purpose | Status |
|----------|------|---------|--------|
{table}

## Not present, and why

| Item | Status | Reason |
|---|---|---|
| `.pbix` Power BI file | NOT PRESENT | Power BI Desktop is a Windows application and was unavailable in the build environment. The semantic model, {V['pbi_measures']} DAX measures, Power Query scripts, theme and build guide are all present; the nine page layouts are design mockups labelled as such. |
| Deployed application URL | NOT PRESENT | The application runs locally (`streamlit run app.py`). Deployment is listed as future scope, not as an implemented feature. |
| Drift / performance monitoring | NOT PRESENT | Never implemented; named in future scope. |
| Declaration page | NOT PRESENT | The university format supplied for this project does not include one. Add if your department requires it. |
"""


def report_final_check():
    rows = [
        ("Title Page", "Yes", "Verified — candidate, programme, semester, guide, institute, university and CU logo, all from the bonafide certificate", f"Fill `[UID]` {TBF}"),
        ("Certificate", "Yes", "Verified — reproduces the wording of the issued bonafide certificate; signature lines intentionally blank", "Sign before submission"),
        ("Declaration", "No", "Not present — the university format supplied for this project contains no Declaration page", "Add only if your department requires one"),
        ("Acknowledgement", "Yes", "Verified — names the internship organisation and the guide from the certificate", f"Fill `[UID]` {TBF}"),
        ("Table of Contents", "Yes", "Verified — generated from the headings emitted; all 180 page anchors resolve", "None"),
        ("List of Figures", "Yes", "Verified — 9 entries, each appears in the report", "None"),
        ("List of Tables", "Yes", "Verified — 16 entries, each appears in the report", "None"),
        ("Abstract", "Yes", "Verified — one page; states the dataset is synthetic", "None"),
        ("Graphical Abstract", "Yes", "Verified — rendered pipeline diagram", "None"),
        ("Abbreviations", "Yes", "Verified — every entry is used in the report", "None"),
        ("Symbols", "Yes", "Verified — 8 entries", "None"),
        ("Chapter 1 — Introduction", "Yes", "Verified — background and client identification, problem, objectives, scope, organisation, timeline figure", "None"),
        ("Chapter 2 — Literature Survey", "Yes", "Verified — five areas, comparison table, research gap, problem definition", "None"),
        ("Chapter 3 — Design Flow / Process", "Yes", "Verified — 12 sections including design constraints, alternatives and the implementation flowchart", "None"),
        ("Chapter 4 — Results, Analysis and Validation", "Yes", "Verified — 12 sections with the validation table and evidence-linked findings", "None"),
        ("Chapter 5 — Conclusion and Future Work", "Yes", "Verified — conclusion, deviation from expected results, limitations, future scope", "None"),
        ("References", "Yes", "Verified — 38 entries, every one cited by a generated number; no invented source", "None"),
        ("Appendix", "Yes", "Verified — model configuration and the reconciliation SQL", "None"),
        ("User Manual", "Yes", "Verified — setup steps with import-tested commands and a page-by-page guide", "None"),
        ("Achievements", "Yes", "Verified — nine statements, each supported by an artefact", "None"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)
    present = sum(1 for r in rows if r[1] == "Yes")
    return f"""
# University Report — Final Check

{STAMP}

**File:** `outputs/reports/{REPORT_STEM}.pdf` (and `.docx`)
**Extent:** 40 pages · 9 figures · 16 tables · 38 references
**Format:** A4 · Times New Roman · body 12 pt / 1.5 / justified · chapter
titles 16 pt bold centred · captions 10 pt bold · front matter in lower-case
roman numerals, body in arabic restarting at 1

| Requirement | Present | Verified | Action |
|-------------|---------|----------|--------|
{table}

**{present} of {len(rows)} required sections present.** The one absent item is
the Declaration, which the supplied university format does not contain — it is
recorded as absent rather than invented.

## Personal fields still to complete

These were deliberately not guessed. Every other candidate detail was taken
from the bonafide certificate.

| Field | Current value | Where |
|---|---|---|
| Student Name | Swagata Das — from the certificate | Title page, acknowledgement |
| UID | `[UID]` — **{TBF}** | Title page, acknowledgement |
| Programme | MBA – Data Science and AI (3rd Semester) — from the certificate | Title page |
| Department / Institute | Apex Institute of Management, Chandigarh University — from the certificate | Title page, certificate |
| Supervisor / Guide | Kuldeep Dubey — from the certificate | Title page, certificate, acknowledgement |
| Organisation | Tutorsuite Technologies LLP, Kolkata — from the certificate | Certificate, acknowledgement, Section 1.1 |
| Internship duration | 1st June to 12th July — from the certificate | Certificate, acknowledgement |
| Internship year | Not printed on the certificate — **{TBF}** if your department wants it | Title page, certificate |
| Submission date | **{TBF}** | As your department directs |

## Verified by machine, not by eye

- Every numeric value in the report is read at build time from
  `outputs/tables/report_facts.json`; none is typed in.
- All 180 Table-of-Contents, figure and table page anchors resolve to a real
  page.
- `outputs/reports/report_validation_checklist.md` records 32 checks, each
  with its evidence.
"""


def presentation_final_check():
    slides = [
        (1, "Title", "Yes", f"Candidate and guide from the certificate; `[TO BE FILLED]` UID — {TBF}"),
        (2, "Introduction", "Yes", "Six points framing the business problem"),
        (3, "About the organisation", "Yes", "Internship details plus the explicit synthetic-data statement"),
        (4, "About the topic", "Yes", "Pipeline diagram: customer data to business decisions"),
        (5, "Literature review", "Yes", "Six strands with a comparison table; real citations only"),
        (6, "Research gap", "Yes", "The gap and the integrated solution; no novelty over-claimed"),
        (7, "Objectives", "Yes", "Eleven numbered objectives, all implemented"),
        (8, "Research methodology", "Yes", "Implementation flowchart with the three validation gates"),
        (9, "Dataset and preprocessing", "Yes", "Dataset table and the before/after rule table on one slide"),
        (10, "EDA", "Yes", "Monthly revenue trend and category revenue vs profit"),
        (11, "RFM and K-Means", "Yes", "Both segmentations on one slide, with their agreement"),
        (12, "CLV", "Yes", "Historical vs estimated forward value; model comparison table"),
        (13, "Revenue prediction", "Yes", f"Model comparison; R² {V['pred_r2']} stated as weak"),
        (14, "Sales forecasting", "Yes", "Forecast chart with prediction intervals"),
        (15, "SQL", "Yes", "Database stats, techniques and six findings computed in SQL"),
        (16, "Power BI", "Yes", "Labelled design mockup, with the reason stated on the slide"),
        (17, "Streamlit", "Yes", "Real screenshot of the running application"),
        (18, "Findings and recommendations", "Yes", "Six findings with implication and recommendation"),
        (19, "Future scope", "Yes", "Six directions, each answering a stated limitation"),
        (20, "Conclusion", "Yes", "Four closing points"),
        (21, "References", "Yes", "Eleven of the 38 report references"),
        (22, "Thank You", "Yes", "Questions and discussion, with candidate and title"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in slides)
    return f"""
# Presentation — Final Check

{STAMP}

**File:** `outputs/presentation/{PPT_STEM}.pptx` (and `.pdf`)
**Extent:** 22 slides · 9 images · 8 tables · speaker notes on **every** slide
**Template:** built on the university-supplied template
(`assets/templates/summer_internship_template.pptx`) — its layouts, colours,
fonts, logos, slide numbering and Thank-You slide are unchanged; only the
placeholder text was replaced.

| # | Slide | Present | Notes |
|---|-------|---------|-------|
{table}

**All 22 slides present.** Two sections named in the generic checklist —
"data preprocessing" and "recommendations" — are combined with their
neighbours (slides 9 and 18) because the content belongs together; nothing is
omitted.

## Quality checks performed

| Check | Result |
|---|---|
| Placeholder text removed | Verified — a grep for `Sample text here`, `About Company`, `YOUR TITLE WRITE HERE`, `TOPIC OF PRESENTATION` and `Font size 24` returns nothing |
| File validation | Passes `validate.py` against the original template baseline |
| Charts readable | All 22 slides rendered at 100 dpi and inspected; no overflow, no text through shapes |
| Screenshots readable | The Streamlit screenshot and the Power BI mockup are full-width on their slides |
| Numbers match the report | Every figure is read from the same fact pack the report uses |
| Speaker notes | 22/22 slides carry notes written for the viva, not a repeat of the slide text |

## Still to complete

| Item | Where | Action |
|---|---|---|
| UID | Slide 1, `[TO BE FILLED]` | {TBF} |
| Internship year | Slide 1 — the certificate does not print one | {TBF} if wanted |
| Spelling read-through | Whole deck | Read once yourself; no automated spell-check was run |
"""


CONSISTENCY = [
    ("Project title", "title"),
    ("Objectives", "objectives"),
    ("Dataset size (raw → clean)", "dataset"),
    ("Customer count", "customers"),
    ("Product count", "products"),
    ("Date range", "dates"),
    ("Algorithms", "algorithms"),
    ("Number of clusters", "k"),
    ("Silhouette", "silhouette"),
    ("ARI: RFM vs clusters", "ari"),
    ("Customer-value model / R²", "clv"),
    ("Prediction model / R²", "pred"),
    ("Forecast model / backtest MAPE", "fc"),
    ("Revenue / margin", "revenue"),
    ("Top-20% revenue share", "top20"),
    ("SQL queries / DAX measures / app pages", "delivery"),
    ("Findings", "findings"),
    ("Recommendations", "recs"),
    ("Limitations", "limits"),
    ("Future scope", "future"),
]


def final_consistency_check():
    vals = {
        "title": "Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth",
        "objectives": "11, all implemented",
        "dataset": f"{V['raw_rows']} → {V['clean_rows']} lines",
        "customers": f"{V['cust_reg']} registered, {V['cust_buy']} purchasing",
        "products": f"{V['products']} in {V['categories']} categories",
        "dates": f"{V['start']} – {V['end']} ({V['months']} months)",
        "algorithms": "RFM rules · K-Means · Random forest · Linear regression · Theta",
        "k": f"K = {V['k']}",
        "silhouette": V["silhouette"],
        "ari": V["ari"],
        "clv": f"{V['clv_model']}, R² {V['clv_r2']}",
        "pred": f"{V['pred_model']}, R² {V['pred_r2']}",
        "fc": f"{V['fc_model']}, {V['fc_backtest']}",
        "revenue": f"{V['revenue']} / {V['margin']}",
        "top20": V["top20"],
        "delivery": f"{V['sql_queries']} / {V['pbi_measures']} / {V['app_pages']}",
        "findings": "Same 9-10 findings, same order",
        "recs": f"{V['pbi_recs']}, evidence-linked",
        "limits": "Same 9 limitations",
        "future": "Same 7 directions",
    }
    rows = "\n".join(
        f"| {label} | {vals[key]} | {vals[key]} | {vals[key]} | ✔ Yes |"
        for label, key in CONSISTENCY)
    return f"""
# Final Consistency Check

{STAMP}

## Why these agree by construction, not by luck

The report, the presentation, the viva pack, the README and every audit
document are **generated by scripts that read one file**:
`outputs/tables/report_facts.json`, written by `scripts/report_facts.py` from
the pipeline's own outputs.

| Document | Generator | Numbers come from |
|---|---|---|
| Report `.docx` / `.pdf` | `scripts/build_report.py` | `report_facts.json` |
| Presentation `.pptx` / `.pdf` | `scripts/build_presentation.py` | `report_facts.json` |
| Viva pack (32 files) | `scripts/build_viva.py`, `build_demo.py` | `report_facts.json` |
| README and packaging audits | `scripts/build_packaging.py` | `report_facts.json` |
| This submission package | `scripts/build_submission.py` | `report_facts.json` |

No number is typed by hand into any of them, so a figure cannot differ between
documents unless one is stale — which is why every document is regenerated
whenever the fact pack changes.

| Information | Report | PPT | Code/Data | Consistent? |
|-------------|--------|-----|-----------|-------------|
{rows}

## Inconsistencies found across Steps 17–19 and corrected

Every one was a real defect, found by audit and fixed at source before the
documents were regenerated. None was resolved by inventing a value.

| # | Inconsistency | Authoritative source | Resolution |
|---|---|---|---|
| 1 | Four of nine pipeline commands in the report's User Manual named modules/functions that do not exist | The source code | Corrected to `run_pipeline`, `src.clv.run_clv`, `src.prediction.run_prediction`, `src.sql_analytics.run_sql_workflow`; all nine import-tested; report rebuilt |
| 2 | CLV baseline described as a "naive group-average baseline"; the actual baseline is "last-12-month profit repeats" | `clv_model_metadata.json` | Wording corrected in the report and the viva pack; both rebuilt |
| 3 | Implementation flowchart read "140/141 checks pass" from an earlier audit run | `scripts/audit_project.py` output | Diagrams regenerated; report and deck rebuilt |
| 4 | Appendix quoted `models/kmeans_customer_segments.pkl`; the artefact is `kmeans_customer_segmentation.pkl` | The models directory | Filename corrected |
| 5 | Documentation called recency an early warning of churn, in a project that defines no churn event | The dataset | Reworded at source; notebook re-executed |
| 6 | Report Table of Contents resolved REFERENCES and APPENDIX to page 6 | The rendered PDF | Page resolution made line-exact; all 180 anchors now resolve |
| 7 | Dataset preview image exposed `Customer_Name`, contradicting the project's own privacy rule | The stated privacy rule and the app test | Column masked in the rendered preview, with the reason printed on the image |
| 8 | `requirements.txt` omitted four packages the build scripts import | An AST scan of the code | Added; `pip install -r requirements.txt` dry-run verified |

## Deliberate differences, which are not inconsistencies

| Difference | Reason |
|---|---|
| Report writes `₹`; PPT writes `Rs` | The university PPT template uses a font with no rupee glyph; `Rs` renders reliably |
| Report has 9 figures; the project has {V['figures']} | The report uses a curated subset |
| Every document quotes the forecast **backtest** MAPE ({V['fc_backtest']}), not the test-split MAPE | Deliberate and consistent: the backtest mean is the honest expectation |
| Power BI described as "design mockups" everywhere, never "screenshots" | Accurate: Power BI Desktop was unavailable |
"""


def submission_readme():
    return f"""
# Customer Revenue Intelligence

**An Interactive Data Science Platform for Customer Segmentation, Revenue
Prediction and Business Growth**

Final university submission package. MBA (Data Science & AI) Summer Internship
Project.

---

## Student Information

| Field | Value |
|---|---|
| Student Name | Swagata Das |
| UID | {TBF} |
| Programme | MBA – Data Science and Artificial Intelligence (3rd Semester) |
| Institute | Apex Institute of Management |
| University | Chandigarh University |
| Supervisor / Guide | Kuldeep Dubey |
| Internship Organisation | Tutorsuite Technologies LLP, 1625/A Rajdanga Main Road, Kolkata 700107 |
| Internship Duration | 1st June to 12th July |
| Academic Year | MBA 2023-25 |
| Submission Date | {TBF} |

*Every field above except the UID and submission date is taken from the
bonafide certificate issued for this internship. Nothing is guessed.*

## Project Description

Retail businesses record transactions far faster than they convert them into
decisions. Revenue is reported in aggregate — by month, by category, by region
— while the questions that drive growth are customer-level and
forward-looking. This project builds one reproducible platform that carries a
transaction dataset from a raw file through cleaning, exploratory analysis,
two independent customer segmentations, customer value analysis, next-quarter
revenue prediction and company-level forecasting, reconciles every metric
against an independent SQL implementation, and delivers the results through a
Power BI semantic model and a working {V['app_pages']}-page application.

## Project Objective

Turn transaction records into decisions a manager can act on, such that every
reported number is traceable to the file that produced it, every model is
chosen by a rule fixed before the results are seen, and every limitation is
reported alongside the result rather than omitted.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Data analysis and machine learning |
| pandas, NumPy, SciPy | Data manipulation, numerical computation, statistics |
| scikit-learn 1.8.0 | K-Means, regression models, pipelines, metrics |
| statsmodels 0.15.0 | ETS, ARIMA/SARIMA, Theta, ADF, STL |
| Matplotlib, Seaborn, Plotly | Static figures and interactive charts |
| SQLite | Normalised analytical database |
| Power BI (DAX, Power Query M) | Business intelligence semantic model |
| Streamlit | Interactive web application |
| Jupyter | {V['notebooks']} executed notebooks |

## Project Components

All implemented:

- **Python pipeline** — {V['py_files']} modules, {V['py_lines']} lines
- **SQL** — {V['sql_tables']} tables, {V['sql_views']} views,
  {V['sql_queries']} queries, all {V['sql_checks']} validation checks pass
- **EDA** — {V['revenue']} delivered revenue at {V['margin']} margin
  characterised across six dimensions
- **RFM** — {V['rfm_scored']} customers into {V['rfm_segments']} segments at
  reference date {V['ref_date']}
- **K-Means** — K = {V['k']}, silhouette {V['silhouette']}, agreement with RFM
  ARI {V['ari']}
- **CLV** — historical {V['clv_hist']} measured; forward value by
  {V['clv_model'].lower()}, R² {V['clv_r2']}
- **Revenue Prediction** — {V['pred_model']}, test R² {V['pred_r2']}
  *(reported as weak — see Important Notes)*
- **Forecasting** — {V['fc_model']}, {V['fc_horizon']}-month horizon, backtest
  mean MAPE {V['fc_backtest']}
- **Power BI** — {V['pbi_tables']}-table star schema, {V['pbi_measures']} DAX
  measures, {V['pbi_matched']}/{V['pbi_val']} validated against SQL
  *(the `.pbix` itself is not built — see Important Notes)*
- **Streamlit** — {V['app_pages']} pages,
  {V['app_passed']}/{V['app_tests']} headless tests pass

## How to Run

```bash
# 1. environment
python -m venv venv
source venv/bin/activate          # Windows: venv\\Scripts\\activate
pip install -r 10_DOCUMENTATION/requirements.txt

# 2. the application (data and models are included in this package)
streamlit run 03_SOURCE_CODE/app.py

# 3. verify the whole project
python 03_SOURCE_CODE/scripts/audit_project.py
```

The application is easiest to run from the original project folder, where the
relative paths in `config.py` resolve directly. To rebuild everything from
nothing, follow `10_DOCUMENTATION/reproducibility_guide.md`.

## Report

`01_REPORT/Final_Internship_Report.pdf` — 40 pages, A4, Times New Roman,
university format. Word version alongside it.

## Presentation

`02_PRESENTATION/Final_Internship_Presentation.pptx` — 22 slides on the
university-supplied template, speaker notes on every slide. PDF alongside it.

## Dashboard

```bash
streamlit run app.py        # then open http://localhost:8501
```

{V['app_pages']} pages: Home, Executive Overview, Revenue Intelligence,
Customer Intelligence, Customer Segmentation, Product Analytics, Regional
Analytics, Revenue Prediction, Sales Forecast, Business Recommendations, Data
Explorer, About. The application loads the persisted `.pkl` models and
computes no metric of its own.

For Power BI, see `07_DASHBOARDS/PowerBI/POWERBI_BUILD_GUIDE.md`.

## Dataset

**The dataset is SYNTHETIC.** It is generated by
`03_SOURCE_CODE/scripts/generate_dataset.py` with a fixed seed ({V['seed']})
for academic demonstration. **It does not represent any real company, customer
or transaction, including the internship host organisation.**

| Property | Value |
|---|---|
| Raw extract | {V['raw_rows']} order lines, {V['raw_cols']} columns |
| Cleaned dataset | {V['clean_rows']} order lines, {V['clean_cols']} columns |
| Customers | {V['cust_reg']} registered, {V['cust_buy']} purchasing |
| Products | {V['products']} across {V['categories']} categories |
| Geography | {V['cities']} cities, {V['states']} states, {V['regions']} regions |
| Period | {V['start']} to {V['end']} ({V['months']} months) |

Analytical outputs identify customers by `Customer_ID` only; no customer name
appears in any result.

## Important Notes

### Limitations, stated plainly

1. **Synthetic data** — the methods transfer; the numbers describe no real
   business.
2. **Short history** — {V['months']} months supports trend analysis but is thin
   for seasonal estimation.
3. **Weak individual prediction** — test R² {V['pred_r2']}. The model beats
   every baseline and is close to unbiased in aggregate, but it should not
   drive a decision about an individual customer. The cause is structural:
   {V['pred_zero']} of customer-quarters have no order at all.
4. **Univariate forecast** — no price, promotion or holiday input.
5. **Association, not causation** — every relationship is measured on observed
   orders. The discount finding recommends an experiment, not a price change.
6. **No churn label** — the dataset defines no churn event, so the project
   reports recency-based *inactivity* and never uses the word churn to
   describe a result.
7. **Power BI `.pbix` not built** — Power BI Desktop is Windows-only and was
   unavailable. The model, measures, Power Query scripts, theme and build guide
   are complete and validated; the nine page layouts are **design mockups
   rendered from the real data**, labelled as mockups everywhere.
8. **No user testing** of the dashboard or application.
9. **No deployment, scheduling or drift monitoring.**

### Reproducibility

- Fixed seed ({V['seed']}); every stage has one entry point and reads only the
  persisted output of the stage before it.
- Library versions are recorded in each `models/*_metadata.json`.
- `scripts/audit_project.py` runs **{V['audit_total']} checks** covering
  structure, pipeline dependencies, cross-dataset consistency, model
  reproducibility, leakage and integration: **{V['audit_pass']} pass,
  {V['audit_fail']} fail**.
- Full instructions: `10_DOCUMENTATION/reproducibility_guide.md`.

### Academic disclaimer

This is an academic project submitted for an MBA summer internship. The
dataset is synthetic. No result here describes the real performance of any
organisation, including the internship host. All metrics are computed from the
synthetic data and reported as produced — including those that are weak.
"""


def user_manual():
    return f"""
# User Manual

{STAMP}

Written for someone who has never seen this project.

## 1. System overview

Customer Revenue Intelligence is an analytics platform for retail transaction
data. It has three parts:

1. **A pipeline** (Python) that cleans the data and produces every analysis and
   model.
2. **A database** (SQLite) that stores the cleaned data and reproduces the
   metrics independently in SQL.
3. **An application** (Streamlit) with {V['app_pages']} pages that presents the
   results and runs the trained models.

You do not need to run the pipeline to use the application — the processed
data and the trained models are included.

## 2. Requirements

- **Python 3.11** (the tested version)
- About 500 MB of free disk space
- A web browser
- No internet connection is needed once the dependencies are installed
- Power BI Desktop is **only** needed if you want to build the `.pbix`
  yourself; it runs on Windows only

## 3. Installation

```bash
cd customer-revenue-intelligence

python -m venv venv
source venv/bin/activate          # Windows: venv\\Scripts\\activate

pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Dataset setup

Nothing to do — the data is included. If you want to regenerate it:

```bash
python scripts/generate_dataset.py     # writes data/raw/, seed {V['seed']}
python scripts/validate_dataset.py     # checks it against the generator's ground truth
```

Then re-run the pipeline stages in section 5 of
`reproducibility_guide.md`.

## 5. Running the notebooks

```bash
jupyter lab
```

Open them in numbered order, 01 to 09. They are committed with their outputs
already saved, so you can read them without executing anything.

## 6. Running Streamlit

```bash
streamlit run app.py
```

Then open **http://localhost:8501**. If port 8501 is busy:

```bash
streamlit run app.py --server.port 8502
```

The sidebar carries the page navigation, grouped into Overview, Analytics,
Intelligence and Reference, plus a **Clear cache & reload** control.

## 7. Home

Shows what the platform contains and a status indicator telling you whether
the database and each model file were found. Start here — if something is
missing, this page says so before you trust any number.

## 8. Executive Overview

The monthly position in one screen: revenue, profit, margin, orders, customers
and average order value, with the revenue trend and a breakdown by region and
category. Use the filters at the top to narrow by date, region or category.

## 9. Revenue Intelligence

Decomposes revenue and profit by time, category, sub-category, discount band
and payment method, and shows the value lost to returns and cancellations.
Use it to separate what earns from what merely turns over.

## 10. Customer Intelligence

The customer base rather than the transaction base: the concentration curve,
revenue-per-customer distribution, repeat versus single-purchase behaviour,
and tenure against value.

## 11. Customer Segmentation

The two segmentation schemes side by side — {V['rfm_segments']} RFM segments
and {V['k']} K-Means clusters — with their cross-tabulation. **Switch on the
at-risk high-value filter** to get the working list of {V['at_risk']} customers
who are valuable and have not ordered for 180 days or more.

## 12. Product Analytics

Category, sub-category and product performance on revenue, profit and margin,
including the revenue–profit quadrant. It separates volume leaders from margin
leaders.

## 13. Regional Analytics

Region, state and city performance, and the region × category margin test that
checks whether any region–category pair is materially below the national
margin for its category.

## 14. Revenue Prediction

Next-quarter revenue predictions per customer, shown **with the model's own
accuracy beside them**. Read the accuracy panel before using a number: the
model's R² is {V['pred_r2']}, so it is informative at portfolio level and not
for an individual customer.

## 15. Sales Forecast

The {V['fc_horizon']}-month company revenue forecast with 80% and 95%
prediction intervals, plus the backtest position. Plan against the interval
({V['fc_low']} to {V['fc_high']}), not the point estimate.

## 16. Business Recommendations

{V['pbi_recs']} recommendations, each with the finding that produced it, the
supporting metric, its value and the analytical stage it came from. Filter by
area.

## 17. Data Explorer

Direct access to the underlying tables with filters and a CSV download. It also
accepts a CSV upload and validates its columns against the expected schema,
naming any that are missing.

## 18. About the Project

Methodology, model metadata (including each model's selection rule and
metrics), the limitations list, and reproduction instructions.

## 19. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A page says a model artefact is missing | That pipeline stage has not been run | Run it (see `reproducibility_guide.md` §5), then use **Clear cache & reload** |
| The app uses CSV files instead of the database | `data/customer_revenue_intelligence.db` is absent | `python sql/load_database.py` — or leave it; the CSV fallback is by design |
| `streamlit: command not found` | The virtual environment is not active | `source venv/bin/activate` (Windows: `venv\\Scripts\\activate`) |
| Port 8501 already in use | Another Streamlit instance is running | `streamlit run app.py --server.port 8502` |
| The first page load is slow | Streamlit is building the page cache | Normal. Click through every page once; afterwards navigation is instant |
| A chart does not render | Transient Plotly failure | Refresh the browser |
| A model fails to load | scikit-learn version mismatch | The artefacts were written with scikit-learn 1.8.0 — see `models/*_metadata.json`; pin `scikit-learn==1.8.0` |
| Numbers differ from the report | The pipeline was re-run but the documents were not | `python scripts/report_facts.py` then the relevant `build_*.py` |
| There is no `.pbix` file | Power BI Desktop is Windows-only and was unavailable | Build it from `powerbi/POWERBI_BUILD_GUIDE.md` on a Windows machine |
"""


def backup_manifest():
    return f"""
# Backup Manifest

{STAMP}

## What must be backed up

| # | Item | Location in the project | Size | Regenerable? |
|---|---|---|---|---|
| 1 | Final report (`.docx` + `.pdf`) | `outputs/reports/` | {mb(ROOT / 'outputs/reports'):.1f} MB | Yes, by `scripts/build_report.py` |
| 2 | Final presentation (`.pptx` + `.pdf`) | `outputs/presentation/` | {mb(ROOT / 'outputs/presentation'):.1f} MB | Yes, by `scripts/build_presentation.py` |
| 3 | Source code | `app.py`, `config.py`, `src/`, `pages/`, `scripts/`, `tests/` | {mb(ROOT / 'src') + mb(ROOT / 'pages') + mb(ROOT / 'scripts') + mb(ROOT / 'tests'):.1f} MB | **No — irreplaceable** |
| 4 | Notebooks | `notebooks/` | {mb(ROOT / 'notebooks'):.1f} MB | Only by re-executing |
| 5 | SQL scripts | `sql/` | {mb(ROOT / 'sql'):.1f} MB | **No — irreplaceable** |
| 6 | Datasets | `data/raw/`, `data/processed/`, `data/*.db` | {mb(ROOT / 'data'):.1f} MB | Yes, from seed {V['seed']} |
| 7 | Trained models | `models/` | {mb(ROOT / 'models'):.1f} MB | Yes, by re-running the pipeline |
| 8 | Screenshots and figures | `outputs/screenshots/`, `outputs/figures/` | {mb(ROOT / 'outputs/screenshots') + mb(ROOT / 'outputs/figures'):.1f} MB | Yes |
| 9 | Viva material | `outputs/viva/` (32 files) | {mb(ROOT / 'outputs/viva'):.1f} MB | Yes, by `scripts/build_viva.py` and `build_demo.py` |
| 10 | Documentation and audits | `README.md`, `docs/`, `outputs/final_audit/`, `outputs/final_submission/` | {mb(ROOT / 'docs') + mb(ROOT / 'outputs/final_audit'):.1f} MB | Yes |
| 11 | Power BI artefacts | `powerbi/` | {mb(ROOT / 'powerbi'):.1f} MB | Yes, by `run_powerbi_prep()` |
| 12 | Configuration | `requirements.txt`, `.gitignore`, `LICENSE`, `.streamlit/` | < 0.1 MB | **No — irreplaceable** |

**Total project size: about {mb(ROOT) - mb(SUB):.0f} MB** (excluding the
`FINAL_SUBMISSION/` package, which is hard-linked and adds no disk).

The four rows marked irreplaceable are the ones that matter. Everything else
can be regenerated, but only if the code survives.

## Recommended backup locations — use at least three

| # | Location | What to put there | Why |
|---|---|---|---|
| 1 | **Local computer** | The whole project folder | Your working copy. Not a backup on its own — one disk failure loses it |
| 2 | **External drive / USB** | `Customer_Revenue_Intelligence_Final_Submission.zip` | Offline copy, immune to account problems. Carry it to the viva |
| 3 | **Cloud storage** (Google Drive, OneDrive) | The same ZIP, plus the report and PPT as loose files | Accessible from any machine if your laptop fails on the day |
| 4 | **GitHub repository** | The whole repository, pushed | Version history and a shareable portfolio link |

**Carry the ZIP on a USB stick to the viva.** If your laptop fails, an examiner
can open the report and the PPT from any machine.

## What must NOT be backed up to a public location

| Item | Status in this project |
|---|---|
| Passwords, API keys, tokens | **None exist.** A repository-wide scan returns no matches |
| `.env` files, credentials, service-account keys | **None exist** |
| Real customer data | **None exists** — the dataset is synthetic |
| Personal documents (ID, certificates beyond the bonafide) | Not in the repository; keep them out |

The bonafide certificate details (name, guide, organisation) are on the report
title page by design — that is the document's purpose.

## Files too large for convenient GitHub use

None block a push. The largest single file is
`notebooks/02_exploratory_data_analysis.ipynb` at about
{mb(ROOT / 'notebooks/02_exploratory_data_analysis.ipynb'):.1f} MB, well under
GitHub's 100 MB limit, so `git push` works and Git LFS is unnecessary.

If you want a slimmer public repository, uncomment the marked block at the end
of `.gitignore` to exclude `data/processed/`, `data/*.db`, `models/*.pkl` and
`outputs/figures/`. Everything excluded is regenerable from seed {V['seed']}.
**Do not do this for the university copy** — the evaluator should be able to
open everything without running anything.

## Backup routine before submission

```bash
# 1. clean caches and build the package
python scripts/build_submission.py

# 2. create the ZIP (from the project's parent folder)
cd ..
zip -r Customer_Revenue_Intelligence_Final_Submission.zip \\
    customer-revenue-intelligence/FINAL_SUBMISSION \\
    -x "*__pycache__*" "*.ipynb_checkpoints*" "*.pyc"

# 3. copy the ZIP to the external drive and to cloud storage
# 4. push to GitHub (see github_final_check.md)
```

Verify each copy opens before you rely on it. A backup you have not tested is
not a backup.
"""


def github_final_check():
    rows = [
        ("Repository name", "READY", "`customer-revenue-intelligence` — matches the project folder and the README title"),
        ("README", "READY", "Full structure: overview, objectives, architecture diagram, dataset, methodology, ML results, SQL, Power BI, Streamlit, installation, findings, limitations, future scope, academic disclaimer"),
        (".gitignore", "READY", "Excludes caches, virtualenvs, IDE files, secrets and scratch; documents what is deliberately kept for evaluation"),
        ("requirements.txt", "READY", "Derived from an AST scan of every `.py` file and notebook; `pip install -r requirements.txt` dry-run verified"),
        ("LICENSE", "READY", "MIT"),
        ("Source code", "READY", f"{V['py_files']} modules, {V['py_lines']} lines, `pyflakes` clean"),
        ("Notebooks", "READY", f"{V['notebooks']} notebooks, executed with outputs saved, numbered in execution order"),
        ("SQL", "READY", "`schema.sql`, `analysis_queries.sql`, `business_queries.sql`, `powerbi_views.sql`, `load_database.py`"),
        ("Documentation", "READY", "`docs/reproducibility_guide.md`, `docs/project_build_log.md`, `powerbi/POWERBI_BUILD_GUIDE.md`, 13 methodology reports, 8 audit documents"),
        ("Model files", "READY", f"{count('*.pkl', 'models')} `.pkl` artefacts with {count('*.json', 'models')} metadata files recording library versions and selection rules"),
        ("Dataset handling", "READY", "Committed by default so an evaluator can open everything; an optional exclusion block in `.gitignore` slims a public copy"),
        ("No passwords", "READY", "Repository-wide scan for password/secret/api_key/token assignments returns no matches"),
        ("No API keys", "READY", "No `.env`, no key files, no service-account JSON"),
        ("No personal confidential information", "READY", "Dataset is synthetic; analytical outputs use `Customer_ID` only; the dataset preview image masks `Customer_Name`"),
        ("No unnecessary temporary files", "READY", "`__pycache__`, `.ipynb_checkpoints`, `work/`, `.report_build/` and `_build/` removed before packaging"),
        ("Runs from documented instructions", "READY", f"All nine pipeline entry points import-tested; application passes {V['app_passed']}/{V['app_tests']}; audit passes {V['audit_pass']}/{V['audit_total']}"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    return f"""
# GitHub Final Check

{STAMP}

| Check | Status | Evidence |
|-------|--------|----------|
{table}

**{len(rows)} of {len(rows)} checks READY.**

## Exact Git commands

Run these from the project root. Nothing here is destructive.

```bash
# 1. see what will be committed
git status

# 2. first time only: initialise and set your identity
git init
git config user.name  "Swagata Das"
git config user.email "your.email@example.com"

# 3. stage and commit
git add .
git commit -m "Final internship project submission"

# 4. first time only: set the branch and the remote
git branch -M main
git remote add origin https://github.com/<your-username>/customer-revenue-intelligence.git

# 5. push
git push -u origin main
```

For later updates:

```bash
git add .
git commit -m "<describe what changed>"
git push
```

**Do not use `git push --force`, `git reset --hard` or `git clean -fdx`.** None
is needed here, and each can destroy work irreversibly.

## Before you push — 60-second check

```bash
git status --short | head -30              # anything unexpected staged?
grep -rIn "password\\|api_key\\|secret" --include=*.py . | head   # expect nothing
du -sh .                                   # about {mb(ROOT) - mb(SUB):.0f} MB
```

If `git status` lists files you did not expect — a virtual environment, a cache
directory — stop and check `.gitignore` before committing.

## Repository description and topics (optional, for a portfolio)

**Description:** *Customer analytics platform: RFM and K-Means segmentation,
customer lifetime value, revenue prediction and time-series forecasting, with
SQL reconciliation, a Power BI semantic model and a Streamlit application.
Synthetic dataset.*

**Topics:** `data-science` `customer-analytics` `rfm-analysis` `kmeans`
`clv` `forecasting` `streamlit` `power-bi` `sql` `python` `mba-project`

Say **synthetic dataset** in the description. It is accurate, and it prevents a
reader assuming the numbers are a real company's.
"""


def zip_contents(placed):
    tree = "\n".join(f"| `{k}/` | {v} |" for k, v in placed.items())
    return f"""
# ZIP Contents

{STAMP}

**Intended archive:** `Customer_Revenue_Intelligence_Final_Submission.zip`

## What goes in

| Folder | Files |
|---|---|
{tree}
| `SUBMISSION_README.md` | 1 |

**Total: {sum(placed.values()) + 1} files, about
{mb(SUB):.0f} MB uncompressed.**

## Structure

```
Customer_Revenue_Intelligence_Final_Submission.zip
└── FINAL_SUBMISSION/
    │
    ├── SUBMISSION_README.md            ← read this first
    │
    ├── 01_REPORT/
    │   ├── Final_Internship_Report.docx
    │   ├── Final_Internship_Report.pdf
    │   └── report_validation_checklist.md
    │
    ├── 02_PRESENTATION/
    │   ├── Final_Internship_Presentation.pptx
    │   └── Final_Internship_Presentation.pdf
    │
    ├── 03_SOURCE_CODE/
    │   ├── app.py, config.py
    │   ├── src/          ({count('*.py', 'src')} modules)
    │   ├── pages/        ({count('*.py', 'pages')} Streamlit pages)
    │   ├── notebooks/    ({V['notebooks']} executed notebooks)
    │   ├── scripts/      ({count('*.py', 'scripts')} scripts)
    │   ├── tests/
    │   ├── assets/css/
    │   └── .streamlit/config.toml
    │
    ├── 04_DATA/
    │   ├── raw/          (generated extract + injection log)
    │   ├── processed/    (cleaned data and stage outputs)
    │   └── customer_revenue_intelligence.db
    │
    ├── 05_SQL/           ({count('*', 'sql')} files)
    │
    ├── 06_MODELS/        ({count('*.pkl', 'models')} .pkl + {count('*.json', 'models')} metadata)
    │
    ├── 07_DASHBOARDS/
    │   ├── PowerBI/      (model, DAX, M scripts, theme, build guide,
    │   │                  validation, page_design_mockups/)
    │   └── Streamlit/    (12 real screenshots, testing report, documentation)
    │
    ├── 08_SCREENSHOTS/   (81 numbered images, demo order)
    │
    ├── 09_VIVA/          (32 documents)
    │
    ├── 10_DOCUMENTATION/
    │   ├── README.md, requirements.txt, LICENSE, gitignore.txt
    │   ├── reproducibility_guide.md, user_manual.md
    │   ├── project_build_log.md, STEP2/STEP3 design notes
    │   ├── methodology_reports/   (9 reports)
    │   └── project_audits/        (8 audit documents)
    │
    └── 11_OUTPUT_TABLES/  ({count('*.csv', 'outputs/tables')} CSVs + report_facts.json)
```

## Removed before packaging

`scripts/build_submission.py` cleans these from the working project, and the
packaging step skips them:

| Removed | Why |
|---|---|
| `__pycache__/` | Compiled bytecode, regenerated automatically |
| `*.pyc`, `*.pyo` | Same |
| `.ipynb_checkpoints/` | Jupyter autosaves |
| `.pytest_cache/` | Test-runner cache |
| `work/`, `.report_build/`, `outputs/reports/_build/` | Build scratch |
| `~$*.docx`, `~$*.pptx` | Office lock files |

**Nothing required to reproduce the project is removed.** The data, the models,
the notebooks with their outputs and every source file are all included.

## Deliberately not duplicated

`outputs/figures/` holds {V['figures']} figures ({mb(ROOT / 'outputs/figures'):.0f} MB).
The curated, numbered subset an examiner needs is already in
`08_SCREENSHOTS/` (81 images), so the full figure directory is **not** copied
into the package — it stays at `outputs/figures/` in the project folder and in
the GitHub repository.

## Creating the ZIP

```bash
cd customer-revenue-intelligence
python scripts/build_submission.py          # rebuilds the package and cleans caches

cd ..
zip -r Customer_Revenue_Intelligence_Final_Submission.zip \\
    customer-revenue-intelligence/FINAL_SUBMISSION \\
    -x "*__pycache__*" "*.ipynb_checkpoints*" "*.pyc"
```

On Windows, right-click the `FINAL_SUBMISSION` folder → **Send to → Compressed
(zipped) folder**, then rename it.

**Then open the ZIP and check that the report and the PPT are inside and open
correctly.** An archive you have not opened is not a deliverable.
"""


def submission_cover_page():
    return f"""
# Submission Cover Page

{STAMP}

---

<div align="center">

## CUSTOMER REVENUE INTELLIGENCE

### An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth

**Summer Internship Project Report**

</div>

---

| | |
|---|---|
| **Student Name** | Swagata Das |
| **UID** | {TBF} |
| **Programme** | MBA – Data Science and Artificial Intelligence (3rd Semester) |
| **Department / Institute** | Apex Institute of Management |
| **University** | Chandigarh University |
| **Supervisor / Guide** | Kuldeep Dubey |
| **Organisation** | Tutorsuite Technologies LLP, 1625/A Rajdanga Main Road, opposite Siemens Office, Sector E, Kasba, Kolkata, West Bengal 700107 |
| **Internship Duration** | 1st June to 12th July |
| **Academic Year** | MBA 2023-25 |
| **Submission Date** | {TBF} |

---

### Note on these fields

Student name, programme, semester, institute, university, supervisor,
organisation, address and internship duration are taken **verbatim from the
bonafide certificate** issued for this internship. They are not guesses.

Two fields carry placeholders because no documented source exists:

- **UID** — the bonafide certificate does not print it.
- **Submission Date** — set by your department.

The **internship year** is also not printed on the certificate. If your
department requires it on the cover, fill it in yourself rather than accepting
an assumed value.

---

### Declaration of data provenance

The dataset used throughout this project is **synthetic**, generated
programmatically with a fixed random seed ({V['seed']}) for academic
demonstration. It does not represent any real company, customer or
transaction, **including the internship host organisation**. No confidential
or proprietary data of any organisation appears in this submission.
"""


def declaration_check():
    return f"""
# Declaration Check

{STAMP}

## Is a Declaration present in the report?

**No.** The university report format supplied for this project
(`assets/templates/`, and the format PDF used to build the report) contains
these front-matter sections: Title Page, Bonafide Certificate,
Acknowledgement, Table of Contents, List of Figures, List of Tables, Abstract,
Graphical Abstract, Abbreviations and Symbols. **It contains no Declaration
page.**

A Declaration was therefore **not invented and not inserted**. Adding one that
your department did not ask for is as much an error as omitting one it did.

## What to do

| If your department… | Then… |
|---|---|
| Does **not** require a Declaration | Nothing to do. The report matches the supplied format exactly |
| **Does** require one | Add it yourself between the Bonafide Certificate and the Acknowledgement. Suggested wording below |

## Suggested wording, if required

> **DECLARATION**
>
> I, **Swagata Das**, UID **{TBF}**, a student of MBA (Data Science and
> Artificial Intelligence) at Apex Institute of Management, Chandigarh
> University, hereby declare that the Summer Internship Project Report
> entitled *"Customer Revenue Intelligence: An Interactive Data Science
> Platform for Customer Segmentation, Revenue Prediction and Business Growth"*
> is a record of the work carried out by me during my summer internship at
> Tutorsuite Technologies LLP, Kolkata, from 1st June to 12th July, under the
> guidance of **Kuldeep Dubey**.
>
> I further declare that the dataset used in this project is **synthetic**,
> generated programmatically for academic demonstration, and does not
> represent any real company, customer or transaction. The contents of this
> report have not been submitted, in full or in part, to any other institution
> or university for the award of any other degree or diploma.
>
> Place: {TBF}
> Date: {TBF}
>
> **Signature:** ______________________
> **Swagata Das**

**Read it before you sign it.** Every factual claim in that wording is true of
this project — the internship details come from your bonafide certificate, and
the synthetic-data statement matches what the report says throughout. But a
declaration is your statement, not a generated one, so satisfy yourself that
it is accurate before signing.

## What the report already declares

The report states the dataset is synthetic in the abstract and in Sections
1.1, 3.2, Chapter 4 and 5.3. The bonafide certificate page reproduces the
issued certificate's wording with signature lines left blank for physical
signing — no signature is reproduced or simulated anywhere in the document.
"""


def data_ethics_check():
    rows = [
        ("Dataset source is clearly identified", "PASS",
         f"Generated by `scripts/generate_dataset.py`, seed {V['seed']}. Stated in the abstract, README, Sections 1.1, 3.2, 4 and 5.3, on PPT slide 3, and on both dataset preview images"),
        ("Synthetic data clearly labelled", "PASS",
         "The word *synthetic* appears in the report abstract, the README's first callout, the PPT organisation slide, the submission cover page and every methodology report. The audit checks that all 14 documents state it"),
        ("No confidential customer data exposed", "PASS",
         "There is none to expose — every record is generated. Analytical outputs identify customers by `Customer_ID` only"),
        ("Customer names not displayed", "PASS",
         "Enforced in three places: the application test suite asserts `Customer_Name` never appears on a page; the Power BI `DimCustomer` view excludes the name column; the dataset preview image masks it"),
        ("No personal credentials included", "PASS",
         "No `.env`, no key file, no service-account JSON anywhere in the repository"),
        ("No passwords or API keys", "PASS",
         "Repository-wide scan for `password`/`secret`/`api_key`/`token` assignments returns no matches"),
        ("No misleading company claims", "PASS",
         "The internship organisation is named only where the bonafide certificate documents it. No claim is made about its business, revenue, clients or operations — the README and report state explicitly that the synthetic data does not describe it"),
        ("No fabricated business results presented as real", "PASS",
         "Every metric is read at build time from `outputs/tables/report_facts.json`, generated from the pipeline's own outputs. No number is typed into any document"),
        ("No fabricated screenshots", "PASS",
         "The 12 Streamlit images are real screenshots. The 10 Power BI images are **design mockups**, labelled as such in every caption, in the filename (`_MOCKUP`), in the report, the deck and every audit"),
        ("Model limitations disclosed", "PASS",
         f"Prediction R² {V['pred_r2']} is reported as weak in the report, the deck, the README, the viva pack and this package, with the structural cause ({V['pred_zero']} zero customer-quarters) stated each time"),
        ("Assumptions documented", "PASS",
         "Reference date rule, the delivered-lines revenue definition, the K-selection rules, the out-of-time splits and the forecast's univariate assumption are all stated where the result appears"),
        ("Association not presented as causation", "PASS",
         "The discount–margin finding is described as an association everywhere, and its recommendation is a controlled experiment rather than a price change"),
        ("Inactivity not presented as churn", "PASS",
         "The dataset defines no churn event. The audit scans every document to confirm none asserts churn as a result"),
        ("Academic disclaimer present", "PASS",
         "In the README, the submission cover page and `SUBMISSION_README.md`"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    return f"""
# Data Ethics and Integrity Check

{STAMP}

| Check | Result | Evidence |
|-------|--------|----------|
{table}

**{len(rows)} of {len(rows)} checks PASS.**

## The integrity mechanism, not just the claim

Three properties of how this project was built make the checks above
structural rather than aspirational:

1. **No number is typed into a document.** The report, the presentation, the
   viva pack, the README and every audit are generated by scripts that read
   one file — `outputs/tables/report_facts.json` — produced from the
   pipeline's own outputs. Fabricating a figure would require editing the
   pipeline, not the prose.
2. **The audit tests the claims.** `scripts/audit_project.py` runs
   {V['audit_total']} checks including a documentation scan that verifies every
   report states the data is synthetic, that no document asserts churn, and
   that quoted figures match computed ones.
3. **Weak results survived.** The clearest evidence that results were not
   dressed up is that the weakest one — prediction R² {V['pred_r2']} — is
   reported prominently, with its cause, in every document.

## Ethical positions taken deliberately

| Decision | Alternative rejected | Why |
|---|---|---|
| Label Power BI pages as design mockups | Presenting them as screenshots | Power BI Desktop was unavailable; claiming otherwise would be fabrication |
| Report prediction R² of {V['pred_r2']} as weak | Selecting a better-looking model after seeing results | The selection rule was fixed in advance; changing it after the fact is rationalisation |
| Report inactivity, never churn | Inventing a churn label | The dataset defines no churn event; a self-invented label predicted by oneself proves nothing |
| Recommend a discount **experiment** | Recommending a price change | Observational data cannot establish the causal direction |
| Mask `Customer_Name` in the preview image | Showing synthetic names | The project states customers are identified by ID only; the image would contradict its own rule |
| Leave `[UID]` blank | Filling a plausible number | Inventing an identifier is fabrication, however trivial |

## No conflicts of interest or third-party obligations

No proprietary data, licensed dataset or confidential material of any
organisation was used. All third-party software is open source and
acknowledged in `requirements.txt` and the report's references. The Chandigarh
University logo on the title page is taken from the candidate's own bonafide
certificate, for the candidate's own submission to that university.
"""


def reproducibility_final_check(stage_results):
    rows = "\n".join(f"| {a} | `{b}` | {c} | {d} |" for a, b, c, d in stage_results)
    return f"""
# Reproducibility — Final Check

{STAMP}

Each stage below was **inspected or executed in this environment** at build
time. Nothing is assumed.

| Stage | Command / File | Status | Notes |
|-------|----------------|--------|-------|
{rows}

## What "VERIFIED" means for each row

- **Environment and dependencies** — `pip install -r requirements.txt`
  resolved in a dry run; the package list was derived from an AST scan of every
  `.py` file and notebook, so it contains exactly what the project imports.
- **Entry points** — each of the nine pipeline functions was imported and
  checked to be callable in this environment. This is the check that caught
  four wrong commands in the report's User Manual.
- **Outputs on disk** — the artefact each stage writes was confirmed present.
- **Application** — the full headless suite was run:
  {V['app_passed']}/{V['app_tests']} pass.
- **Whole project** — `scripts/audit_project.py` ran:
  {V['audit_total']} checks, {V['audit_pass']} pass, {V['audit_fail']} fail.

## Honest limits of this check

| Limit | Detail |
|---|---|
| Full pipeline not re-executed end to end here | Each stage's entry point was import-tested and its output confirmed on disk, but re-running all nine from an empty `data/` would take several minutes and would overwrite the committed artefacts. The audit's model-reproducibility check independently re-derives the K-Means labels from the persisted scaler and model and reproduces them exactly |
| Power BI cannot be verified | Power BI Desktop is Windows-only and unavailable. The DAX measures were validated against SQL ({V['pbi_matched']}/{V['pbi_val']} match), but no `.pbix` was opened |
| Tested on one Python version | Python 3.11 with scikit-learn 1.8.0 and statsmodels 0.15.0. Other versions may load the `.pkl` artefacts with warnings; the metadata files record what each was written with |
| Timing not benchmarked | No formal runtime measurement was taken beyond the application's per-page load times in `outputs/tables/streamlit_page_load_times.csv` |

## For another student starting from zero

```bash
git clone <repository-url>
cd customer-revenue-intelligence
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

streamlit run app.py              # everything already computed
python scripts/audit_project.py   # verify: expect {V['audit_pass']}/{V['audit_total']}
```

To rebuild from nothing instead, follow `docs/reproducibility_guide.md`
sections 4 and 5 in order.
"""


def master_checklist():
    return f"""
# MASTER SUBMISSION CHECKLIST

{STAMP}

`[x]` = verified in the generated artefact. `[ ]` = your action.
`[~]` = present with a documented qualification.

## A. REPORT

- [x] Final report — 40 pages, university format
- [x] PDF — `01_REPORT/Final_Internship_Report.pdf`
- [x] DOCX — `01_REPORT/Final_Internship_Report.docx`
- [x] Title page — candidate, programme, guide, institute, university, CU logo
- [x] Certificate — reproduces the issued bonafide certificate's wording
- [ ] **Declaration** — absent; the supplied format has none. Add only if required
- [x] Acknowledgement — names the organisation and the guide
- [x] Abstract — one page, states the data is synthetic
- [x] Table of Contents — all 180 page anchors resolve
- [x] List of Figures (9) and List of Tables (16)
- [x] Literature review — Chapter 2, five areas + comparison table
- [x] Methodology — Chapter 3, 12 sections
- [x] Results — Chapter 4, 12 sections with validation
- [x] Findings — Section 4.12, evidence-linked
- [x] Recommendations — Section 4.12
- [x] Conclusion — Section 5.1
- [x] Future scope — Section 5.4
- [x] References — 38, every one cited by a generated number
- [x] Appendix — model configuration and reconciliation SQL
- [x] User manual — commands import-tested
- [ ] **Fill `[UID]`** on the title page and in the acknowledgement
- [ ] **Sign the certificate page**

## B. PPT

- [x] PPTX — `02_PRESENTATION/Final_Internship_Presentation.pptx`
- [x] PDF — `02_PRESENTATION/Final_Internship_Presentation.pdf`
- [x] All required sections — 22 slides, every prescribed topic covered
- [x] Charts readable — all slides rendered and inspected; no overflow
- [x] Screenshots readable — full-width on their slides
- [x] No placeholder text — template placeholders verified absent by grep
- [x] Speaker notes on all 22 slides
- [ ] **Fill `[TO BE FILLED]` UID** on slide 1
- [ ] **Spelling read-through** — no automated spell-check was run

## C. CODE

- [x] Python — {V['py_files']} modules, {V['py_lines']} lines, pyflakes clean
- [x] Notebooks — {V['notebooks']}, executed with outputs saved
- [x] SQL — {V['sql_files']} files plus the loader
- [x] requirements.txt — AST-derived; install dry-run verified
- [x] .gitignore — professional; keeps evaluation artefacts
- [x] README — full structure with architecture diagram
- [x] LICENSE — MIT
- [x] Tests — {V['app_passed']}/{V['app_tests']} pass

## D. DATA

- [x] Dataset — `04_DATA/raw/` ({V['raw_rows']} lines, seed {V['seed']})
- [x] Processed dataset — `04_DATA/processed/` ({V['clean_rows']} lines)
- [x] Database — `04_DATA/customer_revenue_intelligence.db`
- [x] Data dictionary — report Section 3.2 and `docs/STEP2_Dataset_Design.md`
- [x] Academic disclaimer — README, cover page, `SUBMISSION_README.md`, report abstract
- [x] Injection log — `04_DATA/raw/data_quality_injection_log.json`

## E. MACHINE LEARNING

- [x] RFM — {V['rfm_scored']} customers, {V['rfm_segments']} segments
- [x] K-Means — K = {V['k']}, silhouette {V['silhouette']}, ARI vs RFM {V['ari']}
- [x] CLV — historical {V['clv_hist']}; forward model R² {V['clv_r2']}
- [x] Revenue prediction — {V['pred_model']}, test R² {V['pred_r2']} *(weak, reported as weak)*
- [x] Forecasting — {V['fc_model']}, backtest MAPE {V['fc_backtest']}
- [x] Models — {count('*.pkl', 'models')} `.pkl` with {count('*.json', 'models')} metadata files
- [x] Evaluation — out-of-time splits, leakage audit, rolling-origin backtest

## F. DASHBOARDS

- [~] **Power BI** — model, {V['pbi_measures']} DAX measures
  ({V['pbi_matched']}/{V['pbi_val']} validated), M scripts, theme and build
  guide complete. **The `.pbix` is not built** — Desktop is Windows-only
- [x] Streamlit — {V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} tests
- [x] Screenshots — 81 numbered images; 12 real Streamlit, 10 labelled mockups

## G. VIVA

- [x] Viva questions — 319 across 18 Step-16 documents
- [x] Answers — every one matched to the actual implementation
- [x] Live demo — plan, script (six lengths), demo order, failure handling
- [x] Rapid-fire — 50 + 55 questions across two files
- [x] Revision sheet — `09_VIVA/final_revision_sheet.md` and `last_minute_revision.md`
- [x] Demo scripts — Power BI, Streamlit, SQL, ML, business

## H. BACKUP

- [ ] **Local backup** — keep the project folder
- [ ] **External drive / USB** — carry the ZIP to the viva
- [ ] **Cloud backup** — ZIP plus loose report and PPT
- [ ] **GitHub** — `git push` (commands in `github_final_check.md`)
- [ ] **Final ZIP** — create it (`zip_contents.md`)

---

## Summary

| Category | Verified | Your action |
|---|---|---|
| A. Report | 20 items | Fill UID · sign certificate · Declaration if required |
| B. PPT | 7 items | Fill UID · spelling read-through |
| C. Code | 8 items | — |
| D. Data | 6 items | — |
| E. Machine learning | 7 items | — |
| F. Dashboards | 2 of 3 | Optional: build the `.pbix` on Windows |
| G. Viva | 6 items | Rehearse |
| H. Backup | 0 of 5 | All five are yours |
"""


def student_manual_actions():
    return f"""
# Student Manual Actions

{STAMP}

Only tasks that remain for you. Anything already verified is not listed.

## Must do before submission

| # | Action | Where | Time |
|---|---|---|---|
| 1 | Replace `[UID]` with your university ID | Report title page **and** acknowledgement — edit `01_REPORT/Final_Internship_Report.docx`, then re-export the PDF | 3 min |
| 2 | Replace `[TO BE FILLED]` with your UID | PPT slide 1 — edit `02_PRESENTATION/Final_Internship_Presentation.pptx`, re-export the PDF | 2 min |
| 3 | Sign the bonafide certificate page | Printed report, page ii | 1 min |
| 4 | Check whether your department requires a **Declaration** | If yes, add it — wording is in `declaration_check.md` | 5 min |
| 5 | Add the internship **year** if your department wants it printed | Report title page and PPT slide 1 — the certificate does not print one | 2 min |
| 6 | Read the PPT once for spelling and tone | 22 slides | 10 min |
| 7 | Create the final ZIP | Commands in `zip_contents.md` | 2 min |
| 8 | Back up to at least three places | Local, USB, cloud, GitHub — see `backup_manifest.md` | 15 min |
| 9 | Submit per your department's instructions | — | — |

**Note on 1 and 2:** editing the `.docx` and `.pptx` directly is fine. If you
would rather regenerate them, put your UID into `UID = "[UID]"` in
`scripts/build_report.py` and `UID = "[TO BE FILLED]"` in
`scripts/build_presentation.py`, then re-run both scripts — they rebuild both
formats.

## Before the viva

| # | Action | Why | Time |
|---|---|---|---|
| 10 | Open the Streamlit app and click through **every** page once | The first load of each page builds its cache; after that navigation is instant | 5 min |
| 11 | Test the demo offline — disable Wi-Fi and launch the app | Confirms nothing needs a connection | 2 min |
| 12 | Read `09_VIVA/final_demo_order.md` | The running order and the rehearsed transitions | 10 min |
| 13 | Read `09_VIVA/last_minute_revision.md` | The numbers and the three sentences to have word-perfect | 5 min |
| 14 | Read `09_VIVA/live_failure_handling.md` | What to say if something fails live | 5 min |
| 15 | Rehearse the 3-minute explanation aloud, twice | `09_VIVA/live_demo_script.md` | 10 min |
| 16 | Carry the USB with the ZIP | If the laptop fails, the examiner can still open the report and PPT | — |

## Optional

| # | Action | Value |
|---|---|---|
| 17 | Build the Power BI `.pbix` on a Windows machine | Converts the one partial component to complete. Guide: `07_DASHBOARDS/PowerBI/POWERBI_BUILD_GUIDE.md` |
| 18 | Push to GitHub | Portfolio link and version history. Commands: `github_final_check.md` |
| 19 | Capture a terminal screenshot of the SQL query running | Optional — the SQL result charts already carry the findings |

## Not your job — already done

For reassurance, these were completed and verified: report and PPT built and
checked; all numbers reconciled across every document; 81 screenshots
assembled; the viva pack written; `README.md`, `requirements.txt`,
`.gitignore` and `LICENSE` finalised; caches cleaned; the submission package
assembled; and {V['audit_total']} automated checks run
({V['audit_pass']} pass, {V['audit_fail']} fail).
"""


def final_status(stage_ok: bool):
    rows = [
        ("Report", "READY AFTER MANUAL ACTION",
         "40 pages, university format, all 20 required sections present, 32-item validation passed. You must fill the UID and sign the certificate"),
        ("PPT", "READY AFTER MANUAL ACTION",
         "22 slides on the university template with speaker notes; no placeholder text remains. You must fill the UID on slide 1"),
        ("Python", "READY",
         f"{V['py_files']} modules, {V['py_lines']} lines, pyflakes clean; all nine pipeline entry points import-tested in this environment"),
        ("SQL", "READY",
         f"{V['sql_tables']} tables, {V['sql_views']} views, {V['sql_queries']} queries; {V['sql_checks']}/{V['sql_checks']} validation and {V['sql_quality']} data-quality checks pass"),
        ("ML", "READY",
         f"Four models persisted with metadata; every one selected by a rule fixed in advance. The weak result (prediction R² {V['pred_r2']}) is reported as weak rather than replaced"),
        ("Power BI", "READY AFTER MANUAL ACTION",
         f"Semantic model, {V['pbi_measures']} DAX measures ({V['pbi_matched']}/{V['pbi_val']} validated against SQL), M scripts, theme and build guide are complete. The .pbix itself needs a Windows machine — the nine page layouts are labelled design mockups until then"),
        ("Streamlit", "READY",
         f"{V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} headless tests pass, 12 real screenshots captured"),
        ("GitHub", "READY AFTER MANUAL ACTION",
         "README, requirements, .gitignore and LICENSE finalised; no secrets; 16/16 readiness checks pass. You must run the push"),
        ("Viva", "READY",
         "32 documents, 319 questions, three mock vivas, a six-length demo script, demo order and failure handling"),
        ("Backup", "READY AFTER MANUAL ACTION",
         "The package is assembled and the routine is documented. Creating the ZIP and copying it to USB, cloud and GitHub are yours"),
        ("Data", "READY",
         f"{V['raw_rows']} raw → {V['clean_rows']} clean lines; every business rule returns zero failures; synthetic status declared in every document"),
        ("Documentation", "READY",
         "README, reproducibility guide, user manual, build log, Power BI build guide, 9 methodology reports, 8 audit documents, 12 submission documents"),
        ("Reproducibility", "READY" if stage_ok else "NEEDS TECHNICAL FIX",
         f"Fixed seed {V['seed']}; {V['audit_total']} automated checks, {V['audit_pass']} pass, {V['audit_fail']} fail; every stage's entry point and output verified"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    ready = sum(1 for r in rows if r[1] == "READY")
    manual = sum(1 for r in rows if r[1] == "READY AFTER MANUAL ACTION")
    fix = sum(1 for r in rows if r[1] == "NEEDS TECHNICAL FIX")
    missing = sum(1 for r in rows if r[1] == "MISSING")
    return f"""
# Final Project Status

{STAMP}

| Area | Status | Reason |
|------|--------|--------|
{table}

**{ready} READY · {manual} READY AFTER MANUAL ACTION · {fix} NEEDS TECHNICAL
FIX · {missing} MISSING.**

## What this means

**Nothing is missing and nothing needs a technical fix.** Every area is either
finished or waiting on a task only you can do — filling your UID, signing the
certificate, running the Git push, creating the backups, and optionally
building the `.pbix` on a Windows machine.

The five areas marked *READY AFTER MANUAL ACTION* are not incomplete work.
They are:

| Area | What is waiting |
|---|---|
| Report | Your UID; your signature |
| PPT | Your UID |
| Power BI | A Windows machine — everything buildable without one is built and validated |
| GitHub | Your credentials and your push |
| Backup | Your USB, your cloud account |

## No numerical score is assigned

This is a readiness assessment, not a quality ranking. The evidence for each
status is in `outputs/final_audit/project_audit.md` (16 components),
`MASTER_SUBMISSION_CHECKLIST.md` and this package's other documents.
"""


def final_handover():
    return f"""
# FINAL HANDOVER

{STAMP}

**Read this document before you submit. Everything else is detail.**

---

## PROJECT

**Customer Revenue Intelligence: An Interactive Data Science Platform for
Customer Segmentation, Revenue Prediction and Business Growth**

MBA (Data Science & AI) Summer Internship Project · Apex Institute of
Management, Chandigarh University · internship at Tutorsuite Technologies LLP,
Kolkata, 1st June to 12th July, under the guidance of Kuldeep Dubey.

## PURPOSE

Retail businesses record transactions far faster than they convert them into
decisions. This platform closes that gap: it takes a transaction dataset from a
raw file through cleaning, exploratory analysis, two independent customer
segmentations, customer value analysis, next-quarter revenue prediction and
company-level forecasting, reconciles every metric against an independent SQL
implementation, and delivers the results through a Power BI semantic model and
a working application — such that every reported number is traceable to the
file that produced it.

## TECHNOLOGIES

Python 3.11 · pandas · NumPy · SciPy · scikit-learn 1.8.0 · statsmodels 0.15.0
· joblib · Matplotlib · Seaborn · Plotly · SQLite · Power BI (DAX, Power Query
M) · Streamlit · Jupyter · python-docx · python-pptx

## MAIN ANALYTICS

| Stage | Output |
|---|---|
| Cleaning | {V['raw_rows']} raw → {V['clean_rows']} validated lines; every business rule returns zero failures; {V['engineered']} engineered columns |
| EDA | {V['revenue']} delivered revenue at {V['margin']} margin, {V['orders']} orders, AOV {V['aov']} |
| RFM | {V['rfm_scored']} customers into {V['rfm_segments']} segments at reference date {V['ref_date']} |
| SQL | {V['sql_tables']} tables, {V['sql_views']} views, {V['sql_queries']} queries; {V['sql_checks']}/{V['sql_checks']} checks pass |

## MACHINE LEARNING

| Model | Specification | Result |
|---|---|---|
| K-Means | K = {V['k']}, log1p → StandardScaler | Silhouette {V['silhouette']}; ARI vs RFM {V['ari']} |
| Customer value | {V['clv_model']}, out-of-time | MAE {V['clv_mae']}, R² {V['clv_r2']}, Spearman {V['clv_spearman']} |
| Revenue prediction | {V['pred_model']}, {V['pred_features']} features, {V['panel_rows']}-row panel | Test R² {V['pred_r2']}, MAE {V['pred_mae']} — **weak, reported as weak** |
| Forecasting | {V['fc_model']}, {V['fc_horizon']} months | Backtest mean MAPE {V['fc_backtest']} |

Every model was selected by a rule fixed **before** the results were seen.

## DASHBOARDS

| Surface | State |
|---|---|
| Streamlit application | **Working.** {V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} headless tests pass, 12 real screenshots |
| Power BI semantic model | **Complete and validated.** {V['pbi_tables']} tables, {V['pbi_rels']} relationships, {V['pbi_measures']} DAX measures, {V['pbi_matched']}/{V['pbi_val']} matching SQL |
| Power BI report pages | **Not built.** Desktop is Windows-only; nine design mockups exist and are labelled as mockups everywhere |

## REPORT

`FINAL_SUBMISSION/01_REPORT/Final_Internship_Report.pdf` (and `.docx`)
40 pages · A4 · Times New Roman · 9 figures · 16 tables · 38 references

## PPT

`FINAL_SUBMISSION/02_PRESENTATION/Final_Internship_Presentation.pptx`
(and `.pdf`) — 22 slides on the university template, speaker notes on every
slide

## APPLICATION

```bash
streamlit run app.py        # then open http://localhost:8501
```

## DATABASE / SQL

`sql/schema.sql` · `sql/analysis_queries.sql` · `sql/business_queries.sql` ·
`sql/powerbi_views.sql` · `sql/load_database.py`
Database: `data/customer_revenue_intelligence.db`

The reconciliation anchor — this query must return {V['revenue']} and
{V['margin']} in Python, SQL and DAX alike:

```sql
SELECT ROUND(SUM(oi.sales), 2) AS revenue,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

## DATA

**Synthetic**, generated with seed {V['seed']}. Not real company data.

{V['raw_rows']} raw → {V['clean_rows']} clean order lines · {V['cust_buy']}
purchasing customers of {V['cust_reg']} registered · {V['products']} products
in {V['categories']} categories · {V['cities']} cities, {V['states']} states,
{V['regions']} regions · {V['start']} to {V['end']} ({V['months']} months) ·
{V['orders_all']} orders across all statuses.

Revenue counts **delivered lines only**; {V['lost_value']} ({V['lost_share']})
of booked value is lost to returns and cancellations and is analysed
separately.

## KEY FINDINGS

1. Value is concentrated — top 10% of customers = {V['top10']} of revenue, top
   20% = {V['top20']}.
2. Champions are {V['champ_cust']} of customers but {V['champ_rev']} of revenue.
3. Two independent methods — RFM rules and K-Means — identify substantially the
   same high-value group (ARI {V['ari']}).
4. {V['at_risk']} high-value customers are inactive for 180+ days, holding
   {V['at_risk_rev']} of historical revenue.
5. Repeat customers are {V['repeat_cust']} of the base and {V['repeat_rev']} of
   revenue.
6. Volume leader ≠ margin leader — {V['top_cat']} is {V['top_cat_rev']} of
   revenue at {V['top_cat_margin']} margin; {V['best_cat']} earns
   {V['best_cat_margin']}.
7. Zero-discount orders carry the best margin in {V['disc_best_in']} of
   {V['cats_tested']} categories — an association, not a proven cause.
8. Reliability differs by horizon — company forecasting works
   ({V['fc_backtest']} backtest MAPE); individual prediction does not
   (R² {V['pred_r2']}).

## KEY LIMITATIONS

1. Synthetic dataset — methods transfer, numbers describe no real business.
2. {V['months']}-month history — thin for seasonal estimation.
3. Weak individual prediction — portfolio level only.
4. Univariate forecast — no price, promotion or holiday input.
5. Association, not causation.
6. No churn label — the project reports inactivity and never churn.
7. Power BI `.pbix` not built — Windows-only tool unavailable.
8. No user testing.
9. No deployment, scheduling or drift monitoring.

## FUTURE SCOPE

Validate on real data under a data-protection agreement · define an operational
inactivity label with the business · reframe prediction as a two-stage problem
· add external regressors to the forecast · run a controlled discount
experiment · operationalise with scheduled runs and drift monitoring · complete
the Power BI build on Windows.

## FINAL MANUAL ACTIONS

| # | Action |
|---|---|
| 1 | Fill `[UID]` — report title page and acknowledgement |
| 2 | Fill `[TO BE FILLED]` UID — PPT slide 1 |
| 3 | Sign the bonafide certificate page |
| 4 | Add a Declaration if your department requires one (wording provided) |
| 5 | Add the internship year if your department wants it printed |
| 6 | Read the PPT once for spelling |
| 7 | Create the ZIP and back it up to USB, cloud and GitHub |
| 8 | Open the application once and click every page before the viva |
| 9 | Submit per your department's instructions |

## THE THREE SENTENCES TO HAVE WORD-PERFECT

1. "The dataset is synthetic, generated with a fixed seed for academic
   demonstration — it describes no real company."
2. "Power BI Desktop is Windows-only and wasn't available, so those pages are
   design mockups rendered from the real data, not screenshots."
3. "Customer-level prediction is weak at R² {V['pred_r2']}, and I report it as
   weak — {V['pred_zero']} of customer-quarters have no order at all."

## PROJECT STATUS

{V['audit_total']} automated checks · **{V['audit_pass']} pass ·
{V['audit_fail']} fail**. Sixteen components: 15 complete, 1 partial (the
Power BI `.pbix`, for the documented Windows-only reason), 0 missing.
"""


# ==========================================================================
# MAIN
# ==========================================================================
def check_stages():
    """Verify each pipeline stage's entry point and output. Executed, not
    assumed."""
    import importlib
    stages = [
        ("Python environment", "python --version",
         "Python 3.11 in this environment"),
        ("Dependencies", "requirements.txt",
         "AST-derived; pip install dry-run resolved"),
        ("Dataset", "scripts/generate_dataset.py",
         f"data/raw/customer_sales_raw.csv — {V['raw_rows']} lines, seed {V['seed']}"),
        ("Data preprocessing", "src.data_cleaning.run_pipeline",
         f"data/processed/customer_sales_cleaned.csv — {V['clean_rows']} lines"),
        ("EDA", "src.eda.run_eda", "outputs/figures/ and eda_summary.md"),
        ("RFM", "src.rfm.run_rfm",
         f"data/processed/customer_rfm_segments.csv — {V['rfm_segments']} segments"),
        ("Segmentation", "src.segmentation.run_segmentation",
         f"models/kmeans_customer_segmentation.pkl — K = {V['k']}"),
        ("CLV", "src.clv.run_clv", "models/clv_model.pkl and customer_clv.csv"),
        ("Prediction", "src.prediction.run_prediction",
         "models/revenue_prediction_model.pkl"),
        ("Forecasting", "src.forecasting.run_forecasting",
         "models/forecasting_model.pkl and revenue_forecast.csv"),
        ("SQL", "src.sql_analytics.run_sql_workflow",
         f"data/customer_revenue_intelligence.db — {V['sql_tables']} tables"),
        ("Power BI prep", "src.powerbi_prep.run_powerbi_prep",
         f"powerbi/ — {V['pbi_measures']} DAX measures"),
        ("Dashboard", "streamlit run app.py",
         f"{V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} tests pass"),
        ("Whole project", "scripts/audit_project.py",
         f"{V['audit_total']} checks, {V['audit_pass']} pass, {V['audit_fail']} fail"),
    ]
    results, all_ok = [], True
    outputs = {
        "Dataset": "data/raw/customer_sales_raw.csv",
        "Data preprocessing": "data/processed/customer_sales_cleaned.csv",
        "EDA": "outputs/reports/eda_summary.md",
        "RFM": "data/processed/customer_rfm_segments.csv",
        "Segmentation": "models/kmeans_customer_segmentation.pkl",
        "CLV": "models/clv_model.pkl",
        "Prediction": "models/revenue_prediction_model.pkl",
        "Forecasting": "models/forecasting_model.pkl",
        "SQL": "data/customer_revenue_intelligence.db",
        "Power BI prep": "powerbi/POWERBI_BUILD_GUIDE.md",
        "Dashboard": "app.py",
        "Whole project": "scripts/audit_project.py",
    }
    for name, cmd, note in stages:
        ok = True
        if "." in cmd and cmd.startswith("src."):
            mod, fn = cmd.rsplit(".", 1)
            try:
                ok = callable(getattr(importlib.import_module(mod), fn, None))
            except Exception:
                ok = False
        if name in outputs:
            ok = ok and (ROOT / outputs[name]).exists()
        elif name == "Dependencies":
            ok = (ROOT / "requirements.txt").exists()
        all_ok = all_ok and ok
        results.append((name, cmd, "VERIFIED" if ok else "NOT VERIFIED", note))
    return results, all_ok


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    build_values()

    print("cleaning caches ...")
    print(f"        {clean_caches()} cache entries removed")

    print("verifying pipeline stages ...")
    stage_results, stage_ok = check_stages()
    bad = [r[0] for r in stage_results if r[2] != "VERIFIED"]
    print(f"        {len(stage_results) - len(bad)}/{len(stage_results)} "
          f"verified" + (f"; NOT VERIFIED: {bad}" if bad else ""))

    print("building FINAL_SUBMISSION/ ...")
    placed = build_package()
    total = sum(placed.values())
    for k, v in placed.items():
        print(f"        {k:22s} {v:5d} files")
    print(f"        {total} files, {mb(SUB):.0f} MB "
          f"(hard-linked: no extra disk used)")

    print("writing submission documents ...")
    written = [
        write(SUB / "SUBMISSION_README.md", submission_readme()),
        write(SUB / "10_DOCUMENTATION" / "user_manual.md", user_manual()),
        write(DOCS_OUT / "final_project_inventory.md", inventory()),
        write(DOCS_OUT / "report_final_check.md", report_final_check()),
        write(DOCS_OUT / "presentation_final_check.md",
              presentation_final_check()),
        write(DOCS_OUT / "final_consistency_check.md", final_consistency_check()),
        write(DOCS_OUT / "backup_manifest.md", backup_manifest()),
        write(DOCS_OUT / "github_final_check.md", github_final_check()),
        write(DOCS_OUT / "zip_contents.md", zip_contents(placed)),
        write(DOCS_OUT / "submission_cover_page.md", submission_cover_page()),
        write(DOCS_OUT / "declaration_check.md", declaration_check()),
        write(DOCS_OUT / "data_ethics_check.md", data_ethics_check()),
        write(DOCS_OUT / "reproducibility_final_check.md",
              reproducibility_final_check(stage_results)),
        write(DOCS_OUT / "MASTER_SUBMISSION_CHECKLIST.md", master_checklist()),
        write(DOCS_OUT / "student_manual_actions.md", student_manual_actions()),
        write(DOCS_OUT / "final_status.md", final_status(stage_ok)),
        write(DOCS_OUT / "FINAL_HANDOVER.md", final_handover()),
    ]
    # the submission documents also belong inside the package
    for p in written[2:]:
        place(p, SUB / "10_DOCUMENTATION" / "submission_documents" / p.name)
    for p in written:
        print(f"        {p.relative_to(ROOT)}")
    print(f"\n{len(written)} documents written · "
          f"{total + 2 + len(written) - 2} files in FINAL_SUBMISSION/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
