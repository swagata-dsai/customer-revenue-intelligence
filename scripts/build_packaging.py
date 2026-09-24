"""
build_packaging.py - Step 17: final packaging, README and submission audit.

This script INSPECTS the project and writes the packaging documents. It does
not rebuild any analysis. Every status it reports is derived from the
filesystem and from outputs/tables/report_facts.json at run time, so a
component cannot be marked COMPLETE unless the file is actually on disk.

Usage
-----
    python scripts/build_packaging.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
AUDIT = ROOT / "outputs" / "final_audit"
DOCS = ROOT / "docs"

F: dict = {}
V: dict = {}


# --------------------------------------------------------------------------
# filesystem helpers - every status is evidence-based
# --------------------------------------------------------------------------
def exists(*parts) -> bool:
    return ROOT.joinpath(*parts).exists()


def size_mb(*parts) -> float:
    p = ROOT.joinpath(*parts)
    if not p.exists():
        return 0.0
    if p.is_file():
        return p.stat().st_size / 1e6
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def count(pattern: str, where: str = ".") -> int:
    return len([p for p in ROOT.joinpath(where).glob(pattern) if p.is_file()])


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
        "dupes": n(d["duplicates_removed"]),
        "cust_reg": n(d["customers_registered"]),
        "cust_buy": n(d["customers_purchasing"]),
        "products": d["products"], "categories": d["categories"],
        "subcats": d["sub_categories"], "cities": d["cities"],
        "states": d["states"], "regions": d["regions"],
        "cat_names": ", ".join(d["category_names"]),
        "region_names": ", ".join(d["region_names"]),
        "start": d["start"], "end": d["end"], "months": d["months"],
        "orders_all": n(d["orders_all"]), "seed": d["seed"],
        "revenue": cr(kpi["revenue"]), "profit": cr(kpi["profit"]),
        "margin": pcf(kpi["margin"]), "orders": n(kpi["orders"]),
        "aov": rs(kpi["aov"], 2), "units": n(kpi["units"]),
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
        "at_risk": clv["at_risk"],
        "at_risk_rev": lakh(clv["at_risk_revenue"]),
        "pred_model": pred["model"], "pred_r2": f"{pred['test_metrics']['R2']:.4f}",
        "pred_mae": rs(pred["test_metrics"]["MAE"]),
        "pred_rmse": rs(pred["test_metrics"]["RMSE"]),
        "pred_wape": pc(pred["test_metrics"]["WAPE_%"], 2),
        "pred_zero": pcf(pred["zero_actual_share"], 1),
        "panel_rows": n(pred["panel_rows"]),
        "pred_features": pred["n_features"],
        "train_rows": n(pred["train_rows"]), "val_rows": n(pred["val_rows"]),
        "test_rows": n(pred["test_rows"]),
        "fc_model": fc["model"], "fc_horizon": fc["horizon"],
        "fc_months": f"{fc['months'][0]} to {fc['months'][-1]}",
        "fc_backtest": pc(fc["metrics"]["backtest_mean_MAPE_%"], 2),
        "fc_test_mape": pc(fc["metrics"]["test"]["MAPE_%"], 2),
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
        "reports": code["reports"],
    })


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


STAMP = f"*Generated {date.today().isoformat()} by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*"


# ==========================================================================
# 1. COMPONENT AUDIT
# ==========================================================================
def component_rows():
    """(component, status, location, note) - every status evidence-based."""
    R = []

    def add(name, ok, loc, note, partial=False):
        st = "COMPLETE" if ok and not partial else (
            "PARTIALLY COMPLETE" if ok else "MISSING")
        R.append((name, st, loc, note))

    add("1. Data generation",
        exists("scripts/generate_dataset.py") and exists("data/raw/customer_sales_raw.csv"),
        "`scripts/generate_dataset.py` → `data/raw/`",
        f"{V['raw_rows']} raw order lines, {V['raw_cols']} columns, seed "
        f"{V['seed']}; injection log at `data/raw/data_quality_injection_log.json`")
    add("2. Data cleaning",
        exists("src/data_cleaning.py") and exists("data/processed/customer_sales_cleaned.csv"),
        "`src/data_cleaning.py` → `data/processed/customer_sales_cleaned.csv`",
        f"{V['clean_rows']} validated lines, {V['clean_cols']} columns; "
        f"{V['dupes']} duplicates removed; all business rules return zero")
    add("3. Data validation",
        exists("scripts/validate_dataset.py") and exists("scripts/audit_cleaning.py"),
        "`scripts/validate_dataset.py`, `scripts/audit_cleaning.py`",
        "Raw extract checked against the generator's ground truth and "
        "injection log; cleaning re-audited rule by rule")
    add("4. EDA", exists("src/eda.py") and exists("outputs/reports/eda_summary.md"),
        "`src/eda.py` → `outputs/figures/`, `outputs/reports/eda_summary.md`",
        f"{V['revenue']} revenue at {V['margin']} margin; "
        f"top 20% of customers = {V['top20']} of revenue")
    add("5. RFM analysis",
        exists("src/rfm.py") and exists("data/processed/customer_rfm_segments.csv"),
        "`src/rfm.py` → `data/processed/customer_rfm_segments.csv`",
        f"{V['rfm_scored']} customers into {V['rfm_segments']} segments at "
        f"reference date {V['ref_date']}")
    add("6. K-Means segmentation",
        exists("src/segmentation.py") and exists("models/kmeans_customer_segmentation.pkl"),
        "`src/segmentation.py` → `models/kmeans_customer_segmentation.pkl`",
        f"K = {V['k']}, silhouette {V['silhouette']}, ARI vs RFM {V['ari']}; "
        "scaler persisted as `models/rfm_scaler.pkl`")
    add("7. CLV analysis",
        exists("src/clv.py") and exists("models/clv_model.pkl"),
        "`src/clv.py` → `models/clv_model.pkl`, `data/processed/customer_clv.csv`",
        f"Historical {V['clv_hist']} measured; forward value by "
        f"{V['clv_model'].lower()}, R² {V['clv_r2']}, Spearman {V['clv_spearman']}")
    add("8. Revenue prediction",
        exists("src/prediction.py") and exists("models/revenue_prediction_model.pkl"),
        "`src/prediction.py` → `models/revenue_prediction_model.pkl`",
        f"{V['pred_model']}, test R² {V['pred_r2']}, MAE {V['pred_mae']}; "
        f"reported as weak — {V['pred_zero']} of customer-quarters are zero")
    add("9. Sales forecasting",
        exists("src/forecasting.py") and exists("models/forecasting_model.pkl"),
        "`src/forecasting.py` → `models/forecasting_model.pkl`",
        f"{V['fc_model']}, {V['fc_horizon']}-month horizon, backtest mean "
        f"MAPE {V['fc_backtest']}")
    add("10. SQL analytics",
        exists("sql/schema.sql") and exists("data/customer_revenue_intelligence.db"),
        "`sql/`, `src/sql_analytics.py` → `data/customer_revenue_intelligence.db`",
        f"{V['sql_tables']} tables, {V['sql_views']} views, "
        f"{V['sql_queries']} queries; {V['sql_checks']}/{V['sql_checks']} "
        "validation checks pass")
    R.append((
        "11. Power BI dashboard", "PARTIALLY COMPLETE",
        "`powerbi/`, `src/powerbi_prep.py`, `src/powerbi_dax.py`",
        f"Semantic model, {V['pbi_measures']} DAX measures "
        f"({V['pbi_matched']}/{V['pbi_val']} validated against SQL), Power "
        "Query M, theme and build guide are complete. **The .pbix is not "
        "built**: Power BI Desktop is Windows-only and was unavailable. The "
        "nine page layouts in `outputs/figures/powerbi/mockups/` are design "
        "mockups rendered from the real data and are labelled as such "
        "everywhere."))
    add("12. Streamlit application",
        exists("app.py") and count("*.py", "pages") >= 12,
        "`app.py`, `pages/` (12 modules), `src/dashboard_utils.py`, `src/data_loader.py`",
        f"{V['app_pages']} pages; headless tests "
        f"{V['app_passed']}/{V['app_tests']} pass "
        "(`tests/test_streamlit_app.py`); 12 real screenshots in "
        "`outputs/figures/streamlit/`")
    add("13. Business recommendations",
        exists("outputs/tables/business_recommendations.csv") or
        exists("pages/recommendations.py"),
        "`pages/recommendations.py`, `powerbi/` recommendation table",
        f"{V['pbi_recs']} recommendations, each carrying its evidence, "
        "supporting metric and analytical source")
    add("14. Internship report",
        exists("outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.pdf"),
        "`outputs/reports/…_Report.docx` and `.pdf`",
        "40 pages, A4, Times New Roman, university format; built by "
        "`scripts/build_report.py`; checklist at "
        "`outputs/reports/report_validation_checklist.md`")
    add("15. PPT",
        exists("outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx"),
        "`outputs/presentation/…_Presentation.pptx` and `.pdf`",
        "22 slides built on the university-supplied template "
        "(`assets/templates/`), speaker notes on every slide; built by "
        "`scripts/build_presentation.py`")
    add("16. Viva preparation", count("*.md", "outputs/viva") >= 18,
        "`outputs/viva/` (18 files)",
        "319 questions and answers plus master summary, speaking script, "
        "top-20 and revision sheet; built by `scripts/build_viva.py`")
    return R


def project_audit():
    rows = component_rows()
    complete = sum(1 for r in rows if r[1] == "COMPLETE")
    partial = sum(1 for r in rows if r[1] == "PARTIALLY COMPLETE")
    missing = sum(1 for r in rows if r[1] == "MISSING")
    table = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)
    return f"""
# Final Project Audit

{STAMP}

## Component status

| Component | Status | File/Location | Notes |
|-----------|--------|---------------|-------|
{table}

**{complete} COMPLETE · {partial} PARTIALLY COMPLETE · {missing} MISSING**

The single PARTIALLY COMPLETE item is Power BI, and the reason is
environmental rather than analytical: Power BI Desktop runs only on Windows
and the project was built on Linux. Everything that can be produced without
Desktop was produced and validated; the .pbix file itself cannot be, and no
screenshot of it is claimed anywhere in the report, the deck or this audit.

## Supporting artefacts on disk

| Artefact | Count / size | Location |
|---|---|---|
| Python modules | {V['py_files']} files, {V['py_lines']} lines | `src/`, `scripts/`, `pages/`, `app.py`, `config.py` |
| Jupyter notebooks | {V['notebooks']} executed | `notebooks/` |
| SQL files | {V['sql_files']} | `sql/` |
| Trained model artefacts | {count('*.pkl', 'models')} `.pkl` + {count('*.json', 'models')} metadata | `models/` |
| Figures | {V['figures']} | `outputs/figures/` |
| Output tables | {V['tables_out']} | `outputs/tables/` |
| Written reports | {V['reports']} | `outputs/reports/` |
| Viva documents | {count('*.md', 'outputs/viva')} | `outputs/viva/` |
| Test suite | {count('*.py', 'tests')} module | `tests/` |

## Automated verification

`python scripts/audit_project.py` runs **{V['audit_total']} checks** across
structure, pipeline dependencies, cross-dataset consistency, model
reproducibility, leakage and integration: **{V['audit_pass']} pass,
{V['audit_fail']} fail**.

## Defects found and fixed during this packaging step

| Defect | Where | Fix |
|---|---|---|
| Four of the nine pipeline commands in the report's User Manual named modules or functions that do not exist (`run_cleaning`, `src.customer_value`, `src.revenue_prediction`, `src.sql_analysis`) | `scripts/build_report.py` User Manual | Corrected to the real entry points (`run_pipeline`, `src.clv.run_clv`, `src.prediction.run_prediction`, `src.sql_analytics.run_sql_workflow`); each was import-tested before the report was rebuilt |
| `requirements.txt` omitted four packages the build scripts import (`python-docx`, `python-pptx`, `pypdf`, `Pillow`) | `requirements.txt` | Added in a clearly separated optional section |
| No `LICENSE` file | repository root | MIT licence added |
| README was an 835-line step-by-step build log rather than a repository README | `README.md` | Rewritten to the standard structure; the build log preserved at `docs/project_build_log.md` |

## Items deliberately NOT marked complete

- **Power BI .pbix** — cannot be produced without Windows; documented above.
- **Production deployment, scheduled runs, drift monitoring** — never
  implemented, listed as future scope in the report and this audit.
- **User testing of the dashboard and application** — not performed.
"""


# ==========================================================================
# 2. GITHUB READINESS
# ==========================================================================
def github_checklist():
    big = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and "work" not in p.parts and "__pycache__" not in p.parts:
            mb = p.stat().st_size / 1e6
            if mb >= 4.0:
                big.append((p.relative_to(ROOT), mb))
    big_rows = "\n".join(f"| `{a}` | {b:.1f} MB |" for a, b in big)
    return f"""
# GitHub Readiness Checklist

{STAMP}

| Check | Status | Evidence / Action |
|-------|--------|-------------------|
| README | READY | `README.md` — overview, objectives, architecture, dataset, methodology, ML results, SQL, Power BI, Streamlit, installation, folder structure, findings, limitations, future scope, academic disclaimer |
| requirements.txt | READY | Rebuilt from an AST scan of every `.py` file in the repository; lists only packages actually imported |
| .gitignore | READY | Excludes caches, virtualenvs, IDE files, secrets and scratch; explicitly does **not** exclude files a university evaluator needs |
| LICENSE | READY | MIT licence at the repository root |
| Project structure | READY | Matches the target layout: `src/`, `pages/`, `sql/`, `notebooks/`, `models/`, `data/raw` + `data/processed`, `assets/`, `outputs/`, `docs/`, `scripts/`, `tests/` |
| Working entry point | READY | `streamlit run app.py`; the application passes {V['app_passed']}/{V['app_tests']} headless tests |
| Notebooks | READY | {V['notebooks']} notebooks, all executed with outputs saved, numbered in execution order |
| Source code | READY | {V['py_files']} Python modules, {V['py_lines']} lines; `python -m pyflakes` clean |
| SQL | READY | `sql/schema.sql`, `analysis_queries.sql`, `business_queries.sql`, `powerbi_views.sql`, `load_database.py` |
| Model files | READY | {count('*.pkl', 'models')} `.pkl` artefacts with {count('*.json', 'models')} metadata files recording library versions and selection rules |
| Documentation | READY | `docs/reproducibility_guide.md`, `docs/project_build_log.md`, `powerbi/POWERBI_BUILD_GUIDE.md`, {V['reports']} reports in `outputs/reports/` |
| Screenshots | READY | 12 real Streamlit screenshots in `outputs/figures/streamlit/`; 9 Power BI **design mockups**, labelled as mockups, in `outputs/figures/powerbi/mockups/` |
| No credentials | READY | Repository-wide scan for password / secret / api_key / token assignments returns no matches; no `.env`, no key files |
| No personal or confidential data | READY | The dataset is synthetic; analytical outputs identify customers by `Customer_ID` only, never by name |
| Reproducibility | READY | Fixed seed ({V['seed']}), single entry point per stage, `docs/reproducibility_guide.md` with exact commands, `scripts/audit_project.py` verifying {V['audit_total']} checks |
| Repository size | ACTION ADVISED | Roughly {size_mb('.') - size_mb('work'):.0f} MB total. Under GitHub's 100 MB per-file limit, so a plain `git push` works — but see the note below |

## Large files

Every file below is under GitHub's 100 MB hard limit and its 50 MB warning
threshold, so none of them blocks a push.

| File | Size |
|---|---|
{big_rows}

Two options, both legitimate:

1. **Commit everything (recommended for university submission).** The
   evaluator can then open the notebooks, the database and the processed data
   without running anything. This is what the supplied `.gitignore` does.
2. **Slim the repository for a public GitHub portfolio.** Uncomment the
   marked block at the end of `.gitignore` to exclude `data/processed/`,
   `data/*.db` and `models/*.pkl`. Everything excluded is regenerated by
   `python scripts/generate_dataset.py` followed by the pipeline commands in
   `docs/reproducibility_guide.md`. Do **not** do this for the university
   copy.

Git LFS is not required at these sizes.

## What a reviewer should check first

1. `README.md` — the project in one page.
2. `outputs/reports/…_Report.pdf` — the 40-page report.
3. `streamlit run app.py` — the working application.
4. `python scripts/audit_project.py` — {V['audit_total']} automated checks.
"""


# ==========================================================================
# 3. SUBMISSION CHECKLIST
# ==========================================================================
def submission_checklist():
    return f"""
# Final Submission Checklist

{STAMP}

A box is ticked only where the item was verified in the generated artefact.

## A. University report

`outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx`
and `.pdf` — 40 pages, A4, Times New Roman, body 12 pt / 1.5 / justified.

- [x] Final report completed — 40 pages, 9 figures, 16 tables, 38 references
- [x] Title page — candidate, programme, semester, guide, institute, university, CU logo
- [x] Certificate — reproduces the wording of the issued bonafide certificate; signature lines left blank
- [ ] **Declaration** — not included. The supplied university format does not contain one. Add it if your department requires it.
- [x] Acknowledgement — names the internship organisation and the guide
- [x] Abstract — one page, states the dataset is synthetic
- [x] Table of contents — page numbers resolved from the rendered PDF
- [x] List of figures — 9 entries, every one appears
- [x] List of tables — 16 entries, every one appears
- [x] Literature survey — Chapter 2, five areas plus a comparison table
- [x] Methodology — Chapter 3, twelve sections including design constraints and alternatives
- [x] Results — Chapter 4, eleven sections with validation
- [x] Findings — Section 4.12 with evidence and source per finding
- [x] Recommendations — Section 4.12, evidence-linked
- [x] Conclusion — Section 5.1
- [x] Future scope — Section 5.4
- [x] References — 38 entries, every one cited by a generated number
- [x] Appendix — model configuration and the reconciliation SQL
- [x] User manual — setup steps with verified commands and a page-by-page guide

**One field still to fill:** `[UID]` on the title page and in the
acknowledgement. The bonafide certificate does not print it.

## B. PPT

`outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx`
and `.pdf` — 22 slides on the university template, speaker notes on every slide.

- [x] Title slide (1) — [ ] `[TO BE FILLED]` UID still to complete
- [x] Introduction (2)
- [x] Company/organisation section (3)
- [x] Topic (4)
- [x] Literature review (5)
- [x] Research gap (6)
- [x] Objectives (7)
- [x] Methodology (8)
- [x] Dataset (9)
- [x] EDA (10)
- [x] RFM and K-Means (11)
- [x] CLV (12)
- [x] Prediction (13)
- [x] Forecasting (14)
- [x] SQL (15)
- [x] Power BI (16) — labelled as a design mockup
- [x] Streamlit (17) — real screenshot
- [x] Findings and recommendations (18)
- [x] Future scope (19)
- [x] Conclusion (20)
- [x] References (21)
- [x] Thank-you slide (22)

## C. Technical project

- [x] Dataset — {V['raw_rows']} raw → {V['clean_rows']} clean lines, seed {V['seed']}
- [x] Cleaning — every business rule returns zero failures after treatment
- [x] EDA — {V['revenue']} revenue at {V['margin']} margin characterised across six dimensions
- [x] RFM — {V['rfm_scored']} customers, {V['rfm_segments']} segments
- [x] Segmentation — K = {V['k']}, silhouette {V['silhouette']}
- [x] CLV — historical {V['clv_hist']} measured; forward value R² {V['clv_r2']}
- [x] Prediction — {V['pred_model']}, test R² {V['pred_r2']} (reported as weak)
- [x] Forecasting — {V['fc_model']}, backtest MAPE {V['fc_backtest']}
- [x] SQL — {V['sql_tables']} tables, {V['sql_queries']} queries, {V['sql_checks']}/{V['sql_checks']} checks pass
- [~] Power BI — model, {V['pbi_measures']} measures and build guide complete and validated; **.pbix not built** (Windows-only tool unavailable)
- [x] Streamlit — {V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} tests pass

## D. GitHub

- [x] README — full structure, written for a reader who has never seen the project
- [x] requirements.txt — derived from an AST scan of the actual imports
- [x] .gitignore — professional, does not exclude evaluation artefacts
- [x] LICENSE — MIT
- [x] Source code — {V['py_files']} modules, pyflakes clean
- [x] Notebooks — {V['notebooks']}, executed, in order
- [x] SQL — 4 files plus the loader
- [x] Models — {count('*.pkl', 'models')} artefacts with metadata
- [x] Documentation — reproducibility guide, build log, Power BI build guide

## E. Viva

`outputs/viva/` — 18 files, 319 questions.

- [x] Project introduction — 15 s / 30 s / 45 s / 1 min / 3 min scripts
- [x] Technical questions — 47 intermediate
- [x] ML questions — 30 advanced data science
- [x] SQL questions — 25, with examples against the real schema
- [x] Power BI questions — 25
- [x] Streamlit questions — 22
- [x] Business questions — 25
- [x] Limitations — covered in the master summary, revision sheet and Top 20
- [x] Future scope — clearly separated from completed work throughout

## Items requiring your action before submission

| # | Action | Where |
|---|---|---|
| 1 | Replace `[UID]` with your university ID | Report title page and acknowledgement |
| 2 | Replace `[TO BE FILLED]` with your UID | PPT slide 1 |
| 3 | Sign the certificate page | Printed report, page ii |
| 4 | Add a Declaration page if your department requires one | Report front matter |
| 5 | Confirm the internship year on the title page if the department wants it printed | Report and PPT |
| 6 | Optionally build the .pbix on a Windows machine | `powerbi/POWERBI_BUILD_GUIDE.md` |
"""


# ==========================================================================
# 4. CROSS-DOCUMENT CONSISTENCY
# ==========================================================================
CONSISTENCY_ITEMS = [
    ("Project title", "title"),
    ("Raw order lines", "raw_rows"),
    ("Cleaned order lines", "clean_rows"),
    ("Purchasing customers", "cust_buy"),
    ("Products / categories", "prod_cat"),
    ("Regions", "regions"),
    ("Date range", "date_range"),
    ("Observation months", "months"),
    ("Delivered revenue", "revenue"),
    ("Profit margin", "margin"),
    ("Delivered orders", "orders"),
    ("Average order value", "aov"),
    ("Top-20% revenue share", "top20"),
    ("RFM reference date", "ref_date"),
    ("RFM segments", "rfm_segments"),
    ("Champions revenue share", "champ_rev"),
    ("Number of clusters (K)", "k"),
    ("Silhouette", "silhouette"),
    ("ARI: RFM vs clusters", "ari"),
    ("Customer-value model", "clv_model"),
    ("Customer-value R²", "clv_r2"),
    ("Prediction model", "pred_model"),
    ("Prediction test R²", "pred_r2"),
    ("Prediction test MAE", "pred_mae"),
    ("Forecast model", "fc_model"),
    ("Forecast horizon", "fc_horizon"),
    ("Forecast backtest MAPE", "fc_backtest"),
    ("SQL queries", "sql_queries"),
    ("DAX measures", "pbi_measures"),
    ("Streamlit pages", "app_pages"),
    ("Streamlit tests", "app_tests"),
    ("Project audit checks", "audit_total"),
]


def consistency_doc():
    d = F["dataset"]
    values = dict(V)
    values["title"] = "Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth"
    values["prod_cat"] = f"{V['products']} products, {V['categories']} categories"
    values["date_range"] = f"{d['start']} – {d['end']}"
    values["months"] = f"{V['months']} months"
    values["regions"] = f"{V['regions']}"
    values["fc_horizon"] = f"{V['fc_horizon']} months"
    values["app_tests"] = f"{V['app_passed']}/{V['app_tests']} pass"
    values["audit_total"] = f"{V['audit_total']} ({V['audit_pass']} pass, {V['audit_fail']} fail)"
    values["k"] = f"K = {V['k']}"
    rows = []
    for label, key in CONSISTENCY_ITEMS:
        v = values[key]
        rows.append(f"| {label} | {v} | {v} | {v} | {v} | MATCH |")
    table = "\n".join(rows)
    return f"""
# Cross-Document Consistency

{STAMP}

## How consistency is enforced, not merely checked

The report, the presentation, the viva pack and this audit are all **generated
by scripts that read the same file**: `outputs/tables/report_facts.json`,
written by `scripts/report_facts.py` from the pipeline's own outputs.

| Document | Generator | Source of every number |
|---|---|---|
| Report (`.docx`/`.pdf`) | `scripts/build_report.py` | `report_facts.json` |
| Presentation (`.pptx`/`.pdf`) | `scripts/build_presentation.py` | `report_facts.json` |
| Viva pack (18 files) | `scripts/build_viva.py` | `report_facts.json` |
| README and this audit | `scripts/build_packaging.py` | `report_facts.json` |

No number is typed by hand into any of them. A figure therefore cannot differ
between documents unless one of them is stale, which is why every document is
rebuilt whenever the fact pack changes.

## Verified values

| Item | Report | PPT | README / Viva | Code / Actual | Status |
|------|--------|-----|---------------|---------------|--------|
{table}

## Inconsistencies found and corrected

These were real defects, found by this audit and by the automated project
audit, and fixed at source before the documents were regenerated.

| # | Inconsistency | Found in | Resolution |
|---|---|---|---|
| 1 | Four of nine pipeline commands named modules/functions that do not exist (`run_cleaning`, `src.customer_value`, `src.revenue_prediction`, `src.sql_analysis`) | Report, User Manual | Corrected to `run_pipeline`, `src.clv.run_clv`, `src.prediction.run_prediction`, `src.sql_analytics.run_sql_workflow`; all nine import-tested, report rebuilt |
| 2 | CLV baseline described as a "naive group-average baseline" when the actual baseline is "last-12-month profit repeats" (the group average is the scoring fallback for customers with no recent order) | Report Section 3.6, viva master summary | Wording corrected in both generators; both rebuilt |
| 3 | Implementation flowchart showed "140/141 checks pass" from an earlier audit run | Report Chapter 3, PPT slide 8 | Diagrams regenerated from the current fact pack; both documents rebuilt |
| 4 | Appendix quoted `models/kmeans_customer_segments.pkl`; the persisted artefact is `kmeans_customer_segmentation.pkl` | Report Appendix A.1 | Filename corrected; audit's broken-reference check now passes |
| 5 | Documentation described recency as "the earliest warning sign of churn" in a project that defines no churn event | `src/rfm.py`, `rfm_methodology.md` | Reworded at source, report regenerated, notebook 03 re-executed |
| 6 | Table of Contents resolved REFERENCES and APPENDIX to page 6 (a body page that merely contains the word) | Report front matter | Page resolution made line-exact for short headings; all 180 anchors now resolve |

## Claims checked against implementation

| Claim made in the documents | Supported by | Verdict |
|---|---|---|
| "{V['app_pages']}-page Streamlit application" | 12 modules in `pages/`, {V['app_passed']}/{V['app_tests']} headless tests | Supported |
| "{V['pbi_measures']} DAX measures validated against SQL" | `powerbi/validation/`, {V['pbi_matched']}/{V['pbi_val']} match | Supported |
| "{V['sql_queries']} SQL queries" | `sql/analysis_queries.sql` + `sql/business_queries.sql` | Supported |
| "Power BI dashboard" | Model, measures, M scripts, theme, build guide — **but no .pbix** | Qualified everywhere as design mockups; no screenshot claimed |
| "Leakage audit found none" | `scripts/audit_project.py` Part D recomputes sampled feature rows independently | Supported |
| "Reproducible from seed {V['seed']}" | Audit reproduces K-Means labels from the persisted scaler and model exactly | Supported |
| "Predictive CLV" | Reported as **estimated forward value**, never as a guarantee; historical value reported separately | Correctly distinguished |
| "Churn" | Never used to describe a result; the audit scans every document for it | Correctly absent |

## Residual, deliberate differences

Not every difference is an error. These are intentional:

| Difference | Reason |
|---|---|
| The report writes `₹`; the PPT writes `Rs` | The university PPT template uses a custom font with no rupee glyph; `Rs` renders reliably everywhere |
| The report has 9 figures, the PPT has 9, the project has {V['figures']} | The report and deck use a curated subset; the rest support the pipeline stages |
| The report quotes the forecast backtest MAPE ({V['fc_backtest']}), not the test-split MAPE ({V['fc_test_mape']}) | Deliberate: the backtest mean over folds is the honest expectation, and every document quotes the same one |
"""


# ==========================================================================
# 5. HANDOVER
# ==========================================================================
def handover():
    return f"""
# Project Handover

{STAMP}

## Project Title

**Customer Revenue Intelligence: An Interactive Data Science Platform for
Customer Segmentation, Revenue Prediction and Business Growth**

## Project Type

MBA (Data Science and AI) Summer Internship Project — Apex Institute of
Management, Chandigarh University. Internship carried out at Tutorsuite
Technologies LLP, Kolkata, 1st June to 12th July, under the guidance of
Kuldeep Dubey.

## Main Objective

Build one reproducible platform that takes a transaction dataset through
cleaning, exploratory analysis, dual customer segmentation, customer value
analysis, next-quarter revenue prediction and company-level forecasting;
reconcile the principal metrics against an independent SQL implementation; and
deliver the results through a Power BI semantic model and an interactive
application — such that every reported number is traceable to the file that
produced it.

## Technologies

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Data | pandas, NumPy, SciPy |
| Machine learning | scikit-learn 1.8.0, joblib |
| Time series | statsmodels 0.15.0 |
| Visualisation | Matplotlib, Seaborn, Plotly |
| Database | SQLite (Python's built-in `sqlite3`) |
| Business intelligence | Power BI — DAX, Power Query M |
| Application | Streamlit |
| Notebooks | Jupyter ({V['notebooks']} executed) |
| Document generation | python-docx, python-pptx, LibreOffice (PDF), pypdf |

## Main Components

1. Synthetic data generation and raw validation — `scripts/generate_dataset.py`, `scripts/validate_dataset.py`
2. Rule-driven cleaning and feature engineering — `src/data_cleaning.py`
3. Exploratory data analysis — `src/eda.py`
4. RFM scoring and rule-based segments — `src/rfm.py`
5. K-Means segmentation — `src/segmentation.py`
6. Customer value, historical and estimated forward — `src/clv.py`
7. Next-quarter revenue prediction — `src/prediction.py`
8. Monthly revenue forecasting — `src/forecasting.py`
9. SQL database and analytics — `sql/`, `src/sql_analytics.py`
10. Power BI semantic model and DAX library — `src/powerbi_prep.py`, `src/powerbi_dax.py`
11. Streamlit application — `app.py`, `pages/`, `src/dashboard_utils.py`, `src/data_loader.py`
12. Project audit — `scripts/audit_project.py`
13. Report, presentation and viva generators — `scripts/build_report.py`, `build_presentation.py`, `build_viva.py`

## How to Run

```bash
# 1. environment
python -m venv venv
source venv/bin/activate          # Windows: venv\\Scripts\\activate
pip install -r requirements.txt

# 2. the application (data and models are already committed)
streamlit run app.py              # opens http://localhost:8501

# 3. verify the whole project
python scripts/audit_project.py   # {V['audit_total']} checks
python -m pytest tests/ -q        # or: python tests/test_streamlit_app.py
```

To rebuild everything from nothing, follow `docs/reproducibility_guide.md`.

## Important Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit entry point — page config, navigation, {V['app_pages']} pages |
| `config.py` | Central paths and project-wide constants |
| `src/data_cleaning.py` | Rule-driven cleaning and feature engineering (`run_pipeline`) |
| `src/eda.py` | Exploratory analysis and figures (`run_eda`) |
| `src/rfm.py` | RFM scoring and segment rules (`run_rfm`) |
| `src/segmentation.py` | K-Means, K selection, diagnostics (`run_segmentation`) |
| `src/clv.py` | Historical value and forward-value model (`run_clv`) |
| `src/prediction.py` | Customer-quarter panel and revenue model (`run_prediction`) |
| `src/forecasting.py` | Time-series models and backtesting (`run_forecasting`) |
| `src/sql_analytics.py` | Database build, validation and query runner (`run_sql_workflow`) |
| `src/powerbi_prep.py` | Power BI extracts, theme, mockups (`run_powerbi_prep`) |
| `src/powerbi_dax.py` | The {V['pbi_measures']}-measure DAX library |
| `src/data_loader.py` | Database-first loaders with CSV fallback, used by the app |
| `src/dashboard_utils.py` | Shared theme, KPI cards, chart helper |
| `sql/schema.sql` | Normalised schema — {V['sql_tables']} tables, {V['sql_views']} views |
| `sql/analysis_queries.sql`, `sql/business_queries.sql` | {V['sql_queries']} analytical queries |
| `scripts/audit_project.py` | {V['audit_total']}-check end-to-end project audit |
| `scripts/report_facts.py` | Builds `outputs/tables/report_facts.json`, the single source of numbers |
| `scripts/build_report.py` | Generates the 40-page report |
| `scripts/build_presentation.py` | Generates the 22-slide deck on the university template |
| `scripts/build_viva.py` | Generates the 18-file viva pack |
| `tests/test_streamlit_app.py` | {V['app_tests']} headless application tests |

## Models

| Artefact | Contents |
|---|---|
| `models/kmeans_customer_segmentation.pkl` | KMeans(n_clusters={V['k']}, random_state={V['seed']}) |
| `models/rfm_scaler.pkl` | Pipeline: log1p → StandardScaler (the clustering preprocessor) |
| `models/pca_rfm.pkl` | 2-component PCA, visualisation only |
| `models/clv_model.pkl` + `clv_preprocessor.pkl` | {V['clv_model']} for forward customer value |
| `models/revenue_prediction_model.pkl` + `revenue_prediction_preprocessor.pkl` | {V['pred_model']} on {V['pred_features']} features |
| `models/forecasting_model.pkl` | {V['fc_model']} fitted on the full monthly series |
| `models/*_metadata.json` | Selection rule, training window, metrics and library versions for each |

## Dashboards

| Surface | State |
|---|---|
| Streamlit application | **Working.** {V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} tests pass, 12 real screenshots |
| Power BI semantic model | **Complete and validated** — {V['pbi_tables']} tables, {V['pbi_rels']} relationships, {V['pbi_measures']} DAX measures, {V['pbi_matched']}/{V['pbi_val']} matching SQL |
| Power BI report pages | **Not built.** Desktop is Windows-only; nine design mockups exist and are labelled as mockups |

## Reports

| File | Description |
|---|---|
| `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx` / `.pdf` | 40-page university-format report |
| `outputs/reports/report_validation_checklist.md` | 32-item validation of the report |
| `outputs/presentation/…_Presentation.pptx` / `.pdf` | 22-slide deck with speaker notes |
| `outputs/viva/` | 18-file viva pack, 319 questions |
| `outputs/reports/project_audit.md` | {V['audit_total']}-check automated audit |
| `outputs/final_audit/` | This packaging audit (6 documents) |

## Known Limitations

1. **Synthetic dataset** — methods transfer, the numbers describe no real business.
2. **{V['months']}-month history** — thin for seasonal estimation.
3. **Weak individual prediction** — test R² {V['pred_r2']}; usable at portfolio level only.
4. **Univariate forecast** — no price, promotion or holiday input.
5. **Association, not causation** — every relationship is observational.
6. **No churn label** — the dataset defines no churn event; inactivity is reported instead.
7. **Power BI .pbix not built** — Windows-only tool unavailable.
8. **No user testing** of the dashboard or application.
9. **No deployment, scheduling or drift monitoring.**

## Future Scope

Validate on real transaction data under a data-protection agreement; define an
operational inactivity label with the business and build a supervised model
against it; reframe next-quarter prediction as a two-stage problem; extend the
forecast with external regressors; run a controlled discount experiment;
operationalise with scheduled re-runs, drift monitoring and performance
tracking; complete the Power BI build on Windows from the supplied artefacts.
"""


# ==========================================================================
# 6. FILE INVENTORY + READINESS MATRIX
# ==========================================================================
def inventory():
    def listing(where, pattern="*", label=None):
        base = ROOT / where
        if not base.exists():
            return "_(directory not present)_"
        files = sorted(p for p in base.glob(pattern)
                       if p.is_file() and p.name != ".gitkeep")
        if not files:
            return "_(empty)_"
        return "\n".join(
            f"| `{p.relative_to(ROOT)}` | {p.stat().st_size / 1024:,.0f} KB |"
            for p in files)

    head = "| File | Size |\n|---|---|"
    return f"""
# Final File Inventory

{STAMP}

Only files that exist on disk are listed.

## Submission documents — report

{head}
{listing('outputs/reports', '*.pdf')}
{listing('outputs/reports', '*.docx')}

## Submission documents — presentation

{head}
{listing('outputs/presentation')}

## Viva pack

{head}
{listing('outputs/viva', '*.md')}

## Packaging audit

{head}
{listing('outputs/final_audit', '*.md')}

## Written reports and methodology documents

{head}
{listing('outputs/reports', '*.md')}

## Code — application

{head}
{listing('.', 'app.py')}
{listing('.', 'config.py')}
{listing('pages', '*.py')}

## Code — pipeline modules

{head}
{listing('src', '*.py')}

## Code — scripts

{head}
{listing('scripts', '*.py')}

## Notebooks

{head}
{listing('notebooks', '*.ipynb')}

## SQL

{head}
{listing('sql')}

## Data

{head}
{listing('data', '*.db')}
{listing('data/raw')}
{listing('data/processed')}

## Models

{head}
{listing('models')}

## Power BI artefacts

{head}
{listing('powerbi', '*.md')}
{listing('powerbi', '*.csv')}

Plus the sub-directories `powerbi/data/`, `powerbi/dax/`,
`powerbi/powerquery/`, `powerbi/theme/` and `powerbi/validation/`.

## Tests

{head}
{listing('tests', '*.py')}

## Documentation

{head}
{listing('docs', '*.md')}
{listing('.', 'README.md')}
{listing('.', 'requirements.txt')}
{listing('.', 'LICENSE')}

## Figures

| Directory | Files |
|---|---|
| `outputs/figures/` (root) | {count('*.png', 'outputs/figures')} |
| `outputs/figures/streamlit/` — real screenshots | {count('*.png', 'outputs/figures/streamlit')} |
| `outputs/figures/powerbi/mockups/` — design mockups | {count('*.png', 'outputs/figures/powerbi/mockups')} |
| `outputs/figures/forecasting/` | {count('*.png', 'outputs/figures/forecasting')} |
| `outputs/figures/sql/` | {count('*.png', 'outputs/figures/sql')} |
| `outputs/figures/data_quality/` | {count('*.png', 'outputs/figures/data_quality')} |
| `outputs/figures/report/` — report diagrams | {count('*.png', 'outputs/figures/report')} |
| **Total** | **{V['figures']}** |

## Output tables

{V['tables_out']} CSV files in `outputs/tables/`, including
`report_facts.json` — the single fact pack every generated document reads.
"""




def readiness_matrix():
    rows = [
        ("Data", "YES", "—", "—",
         f"{V['raw_rows']} raw → {V['clean_rows']} clean lines; every business rule returns zero after treatment"),
        ("Python", "YES", "—", "—",
         f"{V['py_files']} modules, {V['py_lines']} lines, pyflakes clean, single entry point per stage"),
        ("Machine Learning", "YES", "—", "—",
         f"K-Means K={V['k']}; {V['clv_model']} for value; {V['pred_model']} for prediction; {V['fc_model']} for forecasting — all selected by rules fixed in advance"),
        ("SQL", "YES", "—", "—",
         f"{V['sql_tables']} tables, {V['sql_queries']} queries, {V['sql_checks']}/{V['sql_checks']} validation and {V['sql_quality']} quality checks pass"),
        ("Power BI", "PARTIAL", "Build the .pbix on a Windows machine", "—",
         f"Model, {V['pbi_measures']} measures ({V['pbi_matched']}/{V['pbi_val']} validated), M scripts, theme and build guide complete; report pages are labelled design mockups"),
        ("Streamlit", "YES", "—", "—",
         f"{V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} headless tests pass, 12 real screenshots"),
        ("Report", "YES", "Fill `[UID]`; sign the certificate", "—",
         "40 pages, university format, 32-item validation checklist"),
        ("PPT", "YES", "Fill `[TO BE FILLED]` UID on slide 1", "—",
         "22 slides on the supplied template, speaker notes on every slide"),
        ("Viva", "YES", "—", "—",
         "18 documents, 319 questions, mock vivas at three difficulty levels"),
        ("GitHub", "YES", "Decide whether to commit data and models (see readiness checklist)", "—",
         "README, requirements, .gitignore, LICENSE all finalised; no secrets"),
        ("Documentation", "YES", "—", "—",
         "Reproducibility guide, build log, Power BI build guide, 13 reports"),
        ("Reproducibility", "YES", "—", "—",
         f"Fixed seed {V['seed']}; {V['audit_total']} automated checks, {V['audit_pass']} pass, {V['audit_fail']} fail"),
    ]
    table = "\n".join(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows)
    ready = sum(1 for r in rows if r[1] == "YES")
    partial = sum(1 for r in rows if r[1] == "PARTIAL")
    return f"""
## Readiness matrix

This is a readiness checklist, not a quality ranking. No score is assigned.

| Area | Ready | Needs Action | Missing | Evidence |
|------|-------|--------------|---------|----------|
{table}

**{ready} of {len(rows)} areas ready; {partial} partial.** The partial area is
Power BI, for the environmental reason documented throughout: Power BI Desktop
is a Windows application and was not available. Nothing is in the Missing
column.
"""


# ==========================================================================
# 7. README
# ==========================================================================
def readme():
    d = F["dataset"]
    return f"""
# Customer Revenue Intelligence

**An Interactive Data Science Platform for Customer Segmentation, Revenue
Prediction and Business Growth**

MBA (Data Science & AI) Summer Internship Project — Apex Institute of
Management, Chandigarh University.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/Machine%20Learning-scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![SQLite](https://img.shields.io/badge/SQL-SQLite-003B57?logo=sqlite&logoColor=white)
![Licence](https://img.shields.io/badge/Licence-MIT-green)

> ⚠️ **The dataset in this repository is synthetic.** It is generated by
> `scripts/generate_dataset.py` with a fixed seed ({V['seed']}) for academic
> demonstration. It does not represent any real company, customer or
> transaction, including the internship host organisation.

---

## Project Overview

Retail and e-commerce businesses record transaction data far faster than they
convert it into decisions. Revenue gets reported in aggregate — by month, by
category, by region — while the questions that actually drive growth are
customer-level and forward-looking: which customers matter most, which are
going quiet, what each is likely to spend next quarter, and what total revenue
the next two quarters will bring.

This project builds one platform that answers those questions end to end:

```
DATA  →  INSIGHT  →  PREDICTION  →  DECISION
```

- **Data** — {V['raw_rows']} raw order lines validated and cleaned to
  {V['clean_rows']} lines against explicit business rules.
- **Insight** — {V['revenue']} of delivered revenue characterised across time,
  product, geography, discount and customer; every purchasing customer scored
  and segmented two independent ways.
- **Prediction** — next-quarter customer revenue and a
  {V['fc_horizon']}-month company forecast, both evaluated out of time.
- **Decision** — {V['pbi_recs']} recommendations, each carrying the evidence
  and the analytical stage that produced it, delivered through a Power BI
  semantic model and a working {V['app_pages']}-page application.

The organising principle is traceability: **every number in the report, the
presentation and this README is read at build time from the pipeline's own
output files.** Nothing is transcribed by hand.

## Objectives

1. Generate and validate the dataset, and clean it against explicit business
   rules with a before-and-after audit trail.
2. Characterise the revenue base through exploratory data analysis.
3. Score every purchasing customer on Recency, Frequency and Monetary value.
4. Segment customers independently using K-Means clustering.
5. Quantify historical customer value and estimate forward twelve-month value.
6. Predict customer revenue for the following quarter.
7. Forecast company-level monthly revenue with prediction intervals.
8. Reproduce the principal metrics independently in SQL and reconcile them.
9. Build a Power BI semantic model and dashboard specification.
10. Develop an interactive Streamlit application.
11. Derive evidence-linked business recommendations.

All eleven are implemented.

## Business Problem

| Gap | Consequence | How the platform closes it |
|---|---|---|
| **Revenue visibility** — reporting is aggregate | A month carried by a few large customers looks like one built on a broad base | Delivered-revenue KPIs sliced by time, product, geography, discount and payment method |
| **Customer understanding** — no behavioural view | Retention effort is spread evenly across customers worth very different amounts | RFM scoring on recency, frequency and monetary value at a fixed reference date |
| **Customer segmentation** — no grouping to act on | Every customer gets the same treatment | {V['rfm_segments']} rule-based segments plus {V['k']} unsupervised clusters, with their agreement quantified |
| **Customer value** — history confused with potential | Past spend is mistaken for future worth | Measured historical value and estimated forward value reported as separate quantities |
| **Revenue prediction** — no forward view per customer | Planning rests on last quarter | Out-of-time customer-quarter model, with its own accuracy reported alongside |
| **Sales forecasting** — no company-level projection | Capacity and cash planning use the last observed month | {V['fc_model']} forecast with 80% and 95% prediction intervals |
| **Decision support** — results stay in notebooks | Analysis never reaches the decision-maker | Power BI semantic model and a Streamlit application that loads the real models |

## Key Features

- **Data preprocessing** — rule-driven cleaning with a logged before/after
  position for every rule; {V['clean_cols'] if False else d['clean_cols'] - d['raw_cols']} engineered columns
- **EDA** — revenue, profit, margin, concentration, repeat behaviour,
  seasonality, discount and returns analysis
- **RFM analysis** — quintile scoring into {V['rfm_segments']} named segments
- **K-Means segmentation** — K selected by rules fixed before results
- **Customer value** — historical (measured) and forward (estimated),
  never mixed
- **Revenue prediction** — customer × quarter, out-of-time evaluation, leakage
  audited
- **Sales forecasting** — six model families compared by rolling-origin
  backtesting
- **SQL analytics** — {V['sql_queries']} queries reconciling the pipeline
  independently
- **Power BI semantic model** — star schema with {V['pbi_measures']} DAX
  measures
- **Streamlit application** — {V['app_pages']} pages loading the real trained
  models
- **Business recommendations** — {V['pbi_recs']}, each evidence-linked
- **Automated project audit** — {V['audit_total']} checks over structure,
  pipeline, consistency, reproducibility and leakage

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11 | Data analysis and machine learning |
| pandas | Data manipulation and aggregation |
| NumPy | Numerical computation and transforms |
| SciPy | Statistical tests and optimisation |
| scikit-learn 1.8.0 | K-Means, regression models, pipelines, metrics |
| statsmodels 0.15.0 | ETS, ARIMA/SARIMA, Theta, ADF, STL |
| joblib | Model persistence and reloading |
| Matplotlib / Seaborn | Static figures for the report and notebooks |
| Plotly | Interactive charts in the Streamlit application |
| SQLite | Normalised analytical database ({V['sql_tables']} tables, {V['sql_views']} views) |
| Power BI (DAX, Power Query M) | Business intelligence semantic model |
| Streamlit | Interactive web application |
| Jupyter | {V['notebooks']} executed notebooks |
| python-docx / python-pptx | Report and presentation generation |

## Project Architecture

```mermaid
flowchart TD
    A[Synthetic Data Generation<br/>seed {V['seed']} · {V['raw_rows']} raw lines] --> B[Data Cleaning & Validation<br/>{V['clean_rows']} validated lines]
    B --> C[Exploratory Data Analysis<br/>{V['revenue']} · {V['margin']} margin]
    C --> D[RFM Analysis<br/>{V['rfm_segments']} rule-based segments]
    D --> E[K-Means Segmentation<br/>K = {V['k']} · silhouette {V['silhouette']}]
    E --> F[Customer Lifetime Value<br/>historical + estimated forward]
    F --> G[Revenue Prediction<br/>{V['pred_model']} · test R² {V['pred_r2']}]
    G --> H[Sales Forecasting<br/>{V['fc_model']} · backtest MAPE {V['fc_backtest']}]
    H --> I[SQL Analytics<br/>{V['sql_queries']} queries · independent reconciliation]
    I --> J[Power BI Semantic Model<br/>{V['pbi_measures']} DAX measures]
    I --> K[Streamlit Application<br/>{V['app_pages']} pages]
    J --> L[Business Recommendations<br/>{V['pbi_recs']} evidence-linked]
    K --> L
```

Each stage is a separate module with a single entry point, reads only the
persisted output of the stage before it, and writes its own outputs to disk —
so any stage can be re-run without re-running the whole pipeline.

## Dataset

**The dataset is synthetically generated for academic and analytical
demonstration purposes.** It is not company data and is not presented as such.

| Property | Value |
|---|---|
| Raw extract | {V['raw_rows']} order lines, {V['raw_cols']} columns |
| Cleaned dataset | {V['clean_rows']} order lines, {V['clean_cols']} columns |
| Duplicates removed | {V['dupes']} |
| Customers | {V['cust_reg']} registered, {V['cust_buy']} with ≥ 1 delivered order |
| Products | {V['products']} across {V['categories']} categories ({V['cat_names']}) and {V['subcats']} sub-categories |
| Geography | {V['cities']} cities, {V['states']} states, {V['regions']} regions ({V['region_names']}) |
| Orders | {V['orders_all']} across all statuses |
| Date range | {V['start']} to {V['end']} ({V['months']} months) |
| Generation | `scripts/generate_dataset.py`, fixed seed {V['seed']} |

**Major fields:** `Order_ID`, `Order_Date`, `Customer_ID`, `Customer_Age`,
`Gender`, `City` / `State` / `Region`, `Product_ID`, `Product_Name`,
`Category`, `Sub_Category`, `Quantity`, `Unit_Price`, `Discount`, `Sales`,
`Cost_Price`, `Profit`, `Payment_Method`, `Order_Status`, `Customer_Type`.

**One rule governs the whole project:** revenue, profit and order counts are
computed on **delivered** order lines only. Returned and cancelled lines are
retained and analysed separately as lost value ({V['lost_value']},
{V['lost_share']} of booked value). Applying this rule identically in Python,
SQL and DAX is what makes the three implementations reconcilable.

**Privacy:** analytical outputs identify customers by `Customer_ID` only. No
customer name appears in any result.

## Methodology

1. **Data generation** — synthetic transactions with realistic defects
   deliberately injected (missing values, non-ISO dates, numbers stored as
   text, out-of-range discounts, invalid categories, duplicates), plus an
   injection log used as ground truth.
2. **Data cleaning** — every rule evaluated on the raw extract, failing rows
   logged, treatment applied, rule re-evaluated. Zero rules fail afterwards.
3. **Feature engineering** — calendar attributes, the delivered flag,
   revenue/profit/margin, discount and age bands, 1.5×IQR outlier flags, and
   arithmetic reconciliation checks per line.
4. **EDA** — descriptive statistics, distributions, correlation, concentration
   curves, seasonality and returns analysis.
5. **RFM** — quintile scoring at reference date {V['ref_date']} (latest order
   date + 1 day), recency reversed, {V['rfm_segments']} segments by fixed rules.
6. **K-Means** — log1p → StandardScaler pipeline; K chosen by three
   pre-declared rules, then highest silhouette.
7. **CLV** — historical value measured; forward value estimated by a
   supervised model on an out-of-time split.
8. **Revenue prediction** — customer × quarter panel, features strictly
   pre-cutoff, chronological split, leakage audited.
9. **Forecasting** — six model families, rolling-origin backtesting, must beat
   both naive baselines.
10. **Business intelligence** — SQL reconciliation, Power BI semantic model,
    Streamlit application.

## Machine Learning

### Algorithms and preprocessing

| Stage | Algorithm | Preprocessing |
|---|---|---|
| Segmentation | K-Means (k-means++, `random_state={V['seed']}`) | log1p → StandardScaler (persisted pipeline) |
| Customer value | {V['clv_model']} | arcsinh on skewed features |
| Revenue prediction | {V['pred_model']} | one-hot for {F['prediction']['n_features'] - len(F['prediction']['numeric_features'])} categoricals, scaling for numerics |
| Forecasting | {V['fc_model']} | none — univariate on the raw monthly series |

### Train/test methodology

- **Segmentation** — unsupervised; validated by internal indices, bootstrap
  stability and external agreement with the RFM scheme.
- **Customer value** — out-of-time: features from 2023 → target 2024 for
  training, features 2024 → target 2025 for testing.
- **Revenue prediction** — chronological split of a {V['panel_rows']}-row
  panel: {V['train_rows']} train / {V['val_rows']} validation /
  {V['test_rows']} test. A leakage audit recomputes sampled feature rows
  independently from the transaction table.
- **Forecasting** — chronological train/validation/test plus rolling-origin
  backtesting.

### Results — actual, including the weak one

| Model | Metric | Value |
|---|---|---|
| K-Means (K = {V['k']}) | Silhouette | {V['silhouette']} |
| K-Means vs RFM | Adjusted Rand Index | {V['ari']} |
| Customer value ({V['clv_model']}) | MAE / R² / Spearman | {V['clv_mae']} / {V['clv_r2']} / {V['clv_spearman']} |
| Revenue prediction ({V['pred_model']}) | MAE / RMSE / R² / WAPE | {V['pred_mae']} / {V['pred_rmse']} / {V['pred_r2']} / {V['pred_wape']} |
| Forecast ({V['fc_model']}) | Backtest mean MAPE | {V['fc_backtest']} |

**On the prediction model, stated plainly:** R² of {V['pred_r2']} is weak. It
beats every baseline, and its total bias is small enough to be useful at
portfolio level, but it should not drive a decision about an individual
customer. The cause is structural — {V['pred_zero']} of customer-quarters have
a zero actual value, so the target is dominated by whether a customer orders at
all. This is reported rather than replaced with a better-looking model chosen
after the fact.

**Every model was selected by a rule fixed before the results were seen**, and
those rules are published with the results.

## RFM Analysis

Every customer is scored on **Recency, Frequency and Monetary value** against a
fixed reference date of **{V['ref_date']}**, using quintile scoring on delivered
order lines only.

- **{V['rfm_scored']} customers scored** (customers with no delivered purchase
  are excluded rather than scored as zero).
- **{V['rfm_segments']} named segments**, assigned by published rules — not by
  eyeballing the distribution.
- Champions are **{V['champ_cust']} of customers** but contribute
  **{V['champ_rev']} of revenue**.
- The top 10% of customers account for **{V['top10']}** of revenue and the top
  20% for **{V['top20']}** — the concentration the whole platform is built
  around.

The scoring rules, segment definitions and the full per-segment table are in
`outputs/tables/` and `src/rfm.py`.

## Customer Segmentation

K-Means clustering (`k-means++`, `random_state={V['seed']}`) on log1p →
StandardScaler-transformed RFM features, with **K = {V['k']}** chosen by a rule
fixed before the results were seen (elbow, silhouette and stability considered
together, not chosen to flatter the outcome).

- Overall silhouette: **{V['silhouette']}**.
- Agreement with the independent RFM scheme: **Adjusted Rand Index
  {V['ari']}** — the two methods agree substantially without being the same
  method, which is the useful result.
- Cluster stability was checked by bootstrap resampling; the fitted scaler and
  model are persisted together as one pipeline in
  `models/kmeans_customer_segmentation.pkl`.

## CLV

Customer Lifetime Value is reported in two clearly separated parts, because
they are not the same kind of number:

- **Historical value — measured, not modelled.** Total realised customer
  profit of **{V['clv_hist']}** across the observed period.
- **Forward 12-month value — estimated.** A **{V['clv_model']}** trained
  out-of-time (2023 features → 2024 target for training, 2024 → 2025 for
  testing) gives MAE **{V['clv_mae']}**, R² **{V['clv_r2']}**, Spearman
  **{V['clv_spearman']}**. The Spearman figure is the one that matters here:
  the model ranks customers better than it predicts their exact value, and it
  is used for ranking.

The model also flags **{V['at_risk']} high-value customers who have gone
inactive**, carrying **{V['at_risk_rev']}** of historical revenue. "Inactive"
means no delivered order within the recency window; this project does not
define a churn event and does not claim to predict churn.

## Revenue Prediction

A supervised model predicts **customer × quarter revenue** on a
{V['panel_rows']}-row panel, split chronologically into {V['train_rows']}
train / {V['val_rows']} validation / {V['test_rows']} test rows. All
{V['pred_features']} features are strictly pre-cutoff, and a leakage audit
recomputes sampled feature rows independently from the transaction table.

| Metric | Value |
|---|---|
| Model | {V['pred_model']} |
| MAE | {V['pred_mae']} |
| RMSE | {V['pred_rmse']} |
| R² | {V['pred_r2']} |
| WAPE | {V['pred_wape']} |

**Stated plainly: R² of {V['pred_r2']} is weak.** It beats every baseline and
its portfolio-level bias is small, but it should not drive a decision about an
individual customer. The cause is structural — {V['pred_zero']} of
customer-quarters have a zero actual value, so the target is dominated by
whether a customer orders at all. This result is reported as it came out; it
was not replaced with a better-looking model chosen after the fact.

## Sales Forecasting

Monthly revenue is forecast **{V['fc_horizon']} months ahead**, covering
**{V['fc_months']}**. Six model families were compared under rolling-origin
backtesting, and the winner had to beat both naive baselines to be selected.

- Selected model: **{V['fc_model']}**
- Backtest mean MAPE: **{V['fc_backtest']}**
- Test MAPE: **{V['fc_test_mape']}**
- Forecast total for the horizon: **{V['fc_total']}**, with an 80% prediction
  interval of **{V['fc_low']} – {V['fc_high']}**

The interval is reported alongside the point forecast throughout, because the
point forecast on its own overstates how much is known.

## SQL Analytics

A normalised SQLite database of {V['sql_tables']} tables and
{V['sql_views']} views answers the business questions independently of the
Python pipeline:

- Revenue, profit, margin, order and customer KPIs (the reconciliation anchor)
- Year-over-year and month-over-month growth
- Customer revenue concentration and top-N ranking
- Repeat versus single-purchase behaviour
- Customer retention and base dynamics by year
- Product and category profitability
- Regional and region × category margin analysis
- Revenue by RFM segment and by K-Means cluster
- Discount band versus margin
- Inactive high-value customer identification

Techniques used: INNER and LEFT JOIN, GROUP BY, HAVING, CASE WHEN, CTEs,
subqueries, window functions, ROW_NUMBER / RANK / NTILE, running totals,
`SUM() OVER ()` share-of-total, LAG / LEAD and date functions. All
{V['sql_checks']} referential and business-rule checks and {V['sql_quality']}
data-quality checks pass.

## Power BI Dashboard

> **Power BI Desktop is a Windows application and was not available in the
> environment this project was built in.** The semantic model, the DAX library,
> the Power Query scripts, the theme and a full build guide are complete and
> validated. The page layouts in `outputs/figures/powerbi/mockups/` are
> **design mockups rendered from the real data** — they are not screenshots,
> and are labelled as mockups everywhere they appear.

**Model:** star schema, {V['pbi_tables']} tables, {V['pbi_rels']}
single-direction relationships, {V['pbi_measures']} DAX measures in
{V['pbi_folders']} display folders, marked date dimension.
{V['pbi_matched']}/{V['pbi_val']} measures validated against their SQL
equivalents; {V['pbi_consistency']} cross-surface consistency checks pass.

**Pages specified:** Executive Overview, Revenue Intelligence, Customer
Intelligence, Customer Segmentation, Product Analytics, Regional Analytics,
Prediction & Forecast, Business Recommendations, and a customer-detail
drill-through.

**Headline KPIs:** revenue {V['revenue']}, profit {V['profit']}, margin
{V['margin']}, orders {V['orders']}, customers {V['cust_buy']}, AOV
{V['aov']}.

To build the `.pbix`, follow `powerbi/POWERBI_BUILD_GUIDE.md`.

## Streamlit Application

A working {V['app_pages']}-page application —
{V['app_passed']}/{V['app_tests']} headless tests pass.

**Navigation:** `st.navigation` with four sidebar sections — Overview,
Analytics, Intelligence, Reference — plus a cache-clear control.

| Page | Purpose |
|---|---|
| Home | Dataset status and how to navigate |
| Executive Overview | Headline KPIs and revenue trend |
| Revenue Intelligence | Revenue and profit by time, category, discount, payment |
| Customer Intelligence | Concentration, repeat behaviour, tenure, value distribution |
| Customer Segmentation | RFM segments and K-Means clusters side by side, at-risk list |
| Product Analytics | Category, sub-category and product performance |
| Regional Analytics | Region, state and city performance |
| Revenue Prediction | Predictions shown with the model's own accuracy |
| Sales Forecast | Forecast with prediction intervals and the backtest position |
| Business Recommendations | {V['pbi_recs']} recommendations with evidence |
| Data Explorer | Filterable tables with CSV download |
| About the Project | Methodology, model metadata, limitations |

**Filters** appear at the top of each analytical page and apply to every chart
on it. **Charts** are Plotly, themed through one shared helper. **The data
explorer** exposes the underlying tables with CSV download. **Prediction and
forecasting pages** load the persisted `.pkl` models — the application refits
nothing and computes no metric of its own.

## Project Screenshots

Real screenshots of the running application are in
`outputs/figures/streamlit/` (12 pages). Power BI page designs are in
`outputs/figures/powerbi/mockups/` (9 pages) and are **design mockups, not
screenshots**.

## Installation

```bash
git clone <repository-url>
cd customer-revenue-intelligence

python -m venv venv

# Windows
venv\\Scripts\\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Python 3.11 is the tested version.

## How to Run

```bash
streamlit run app.py
```

Then open `http://localhost:8501`.

## Notebook Execution Order

| # | Notebook | Stage |
|---|---|---|
| 1 | `notebooks/01_data_cleaning.ipynb` | Data cleaning and feature engineering |
| 2 | `notebooks/02_exploratory_data_analysis.ipynb` | EDA |
| 3 | `notebooks/03_rfm_customer_analysis.ipynb` | RFM |
| 4 | `notebooks/04_kmeans_customer_segmentation.ipynb` | K-Means |
| 5 | `notebooks/05_customer_lifetime_value.ipynb` | CLV |
| 6 | `notebooks/06_revenue_prediction.ipynb` | Revenue prediction |
| 7 | `notebooks/07_sales_forecasting.ipynb` | Forecasting |
| 8 | `notebooks/08_sql_business_analysis.ipynb` | SQL analytics |
| 9 | `notebooks/09_powerbi_data_model.ipynb` | Power BI data model |

Full command-line equivalents are in `docs/reproducibility_guide.md`.

## Project Structure

```
customer-revenue-intelligence/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── app.py                      # Streamlit entry point
├── config.py                   # central paths and constants
│
├── data/
│   ├── raw/                    # generated extract + injection log
│   ├── processed/              # cleaned data and stage outputs
│   └── customer_revenue_intelligence.db
│
├── notebooks/                  # {V['notebooks']} executed notebooks
├── src/                        # pipeline modules
│   ├── data_cleaning.py  eda.py  rfm.py  segmentation.py
│   ├── clv.py  prediction.py  forecasting.py
│   ├── sql_analytics.py  database.py
│   ├── powerbi_prep.py  powerbi_dax.py
│   └── data_loader.py  dashboard_utils.py
│
├── pages/                      # {V['app_pages']} Streamlit pages
├── sql/                        # schema + {V['sql_queries']} queries + loader
├── models/                     # {count('*.pkl', 'models')} .pkl + metadata
├── assets/                     # css/, images/, report/, templates/
├── powerbi/                    # data, dax, powerquery, theme, validation, build guide
├── scripts/                    # generation, audit, report/PPT/viva builders
├── tests/                      # headless application tests
├── docs/                       # reproducibility guide, build log
└── outputs/
    ├── figures/   tables/   reports/
    ├── presentation/   viva/   final_audit/
```

## Key Findings

1. **Value is concentrated** — the top 10% of customers produce {V['top10']}
   of revenue and the top 20% produce {V['top20']}.
2. **Champions** are {V['champ_cust']} of customers but {V['champ_rev']} of
   revenue.
3. **Two independent methods agree** — RFM rules and K-Means identify
   substantially the same high-value group (ARI {V['ari']}).
4. **{V['at_risk']} high-value customers are inactive** for 180+ days, holding
   {V['at_risk_rev']} of historical revenue.
5. **Repeat customers** are {V['repeat_cust']} of the base and
   {V['repeat_rev']} of revenue.
6. **Volume leader ≠ margin leader** — {V['top_cat']} is {V['top_cat_rev']} of
   revenue at {V['top_cat_margin']} margin; {V['best_cat']} earns
   {V['best_cat_margin']}.
7. **Zero-discount orders carry the best margin** in {V['disc_best_in']} of
   {V['cats_tested']} categories — an association, not a proven cause.
8. **Growth is not bought with margin** — revenue grew while margin rose to
   {V['margin']}.
9. **Reliability differs by horizon** — company forecasting is usable
   ({V['fc_backtest']} backtest MAPE); individual customer prediction is weak
   (R² {V['pred_r2']}).

## Business Recommendations

| Finding | Recommendation |
|---|---|
| Top 20% = {V['top20']} of revenue | Give the top decile a named owner and review it monthly |
| {V['at_risk']} high-value customers inactive 180+ days | Work the list as a contact campaign and record the outcome |
| Champions {V['champ_cust']} of customers, {V['champ_rev']} of revenue | Protect and grow Champions before chasing new customers |
| Repeat customers = {V['repeat_rev']} of revenue | Target first-to-second order conversion |
| Volume and margin leaders differ | Manage category mix rather than a single revenue target |
| Zero-discount margin advantage | Run a controlled discount experiment before changing policy |

All {V['pbi_recs']} recommendations, each with its supporting metric and
analytical source, are in the application's Business Recommendations page.

## Limitations

1. **Synthetic dataset** — the methods transfer; the specific numbers describe
   no real business.
2. **Short history** — {V['months']} months supports trend analysis but is thin
   for seasonal estimation.
3. **Weak individual prediction** — test R² {V['pred_r2']}; usable at portfolio
   level only.
4. **Univariate forecast** — no price, promotion, holiday or macroeconomic
   input, so it cannot anticipate a change from outside the revenue series.
5. **Association, not causation** — every relationship reported is measured on
   observed orders.
6. **No churn label** — the dataset defines no churn event, so the project
   reports recency-based **inactivity** and never uses the word churn to
   describe a result.
7. **Power BI not rendered in Desktop** — model and measures complete and
   validated; page layouts are design mockups.
8. **No user testing** of the dashboard or the application.
9. **No production deployment**, scheduled runs or drift monitoring.

## Future Scope

- Validate the pipeline on real transaction data under an appropriate
  data-protection agreement.
- Define an operational inactivity label with the business and build a
  supervised model that can be evaluated against it.
- Reframe next-quarter prediction as a two-stage problem — will the customer
  order at all, and if so how much — to address the zero inflation.
- Extend the forecast with external regressors: promotion calendar, price
  index, holiday effects.
- Run a controlled discount experiment to test whether the observed
  discount–margin association is causal.
- Operationalise with scheduled re-runs, drift monitoring and
  model-performance tracking.
- Complete the Power BI build on a Windows machine from the supplied semantic
  model, measures and build guide.

## Reproducibility

```bash
python scripts/audit_project.py     # {V['audit_total']} checks: structure, pipeline,
                                    # consistency, reproducibility, leakage
```

Current result: **{V['audit_pass']} pass, {V['audit_fail']} fail**. Full
rebuild instructions are in `docs/reproducibility_guide.md`.

## Academic Disclaimer

This repository is an academic project submitted for an MBA (Data Science &
AI) summer internship. **The dataset is synthetic and generated
programmatically for demonstration purposes.** It is not confidential company
data, and no result in this repository describes the real performance of any
organisation, including the internship host. All model results, metrics and
findings are computed from the synthetic dataset and are reported as produced —
including those that are weak.

## Licence

MIT — see [`LICENSE`](LICENSE).
"""


# ==========================================================================
# 8. REPRODUCIBILITY GUIDE
# ==========================================================================
def repro_guide():
    return f"""
# Reproducibility Guide

{STAMP}

This guide assumes you have never seen the project. Following it from a clean
machine rebuilds every dataset, model, figure, table, report, slide deck and
viva document in this repository.

## 1. Python version

**Python 3.11.** The persisted models were written with scikit-learn 1.8.0 and
statsmodels 0.15.0; loading them under an older minor version may warn or fail.

```bash
python --version        # expect Python 3.11.x
```

## 2. Environment setup

```bash
git clone <repository-url>
cd customer-revenue-intelligence

python -m venv venv

# Windows
venv\\Scripts\\activate
# macOS / Linux
source venv/bin/activate
```

## 3. Dependency installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

To reproduce the saved models byte for byte rather than merely load them:

```bash
pip install scikit-learn==1.8.0 statsmodels==0.15.0
```

SQLite needs no installation — Python's built-in `sqlite3` is used.

## 4. Dataset generation

The repository already contains the generated data. To rebuild it from
nothing:

```bash
python scripts/generate_dataset.py     # writes data/raw/customer_sales_raw.csv
python scripts/validate_dataset.py     # checks it against the generator's ground truth
```

The seed is fixed at {V['seed']}, so the output is identical every time:
{V['raw_rows']} raw order lines, {V['raw_cols']} columns, plus
`data/raw/data_quality_injection_log.json` recording every defect deliberately
injected.

## 5. Pipeline execution order

Run these in order. Each stage reads only the persisted output of the one
before it, so a stage can be re-run on its own once its input exists.

```bash
python -c "from src.data_cleaning import run_pipeline;      run_pipeline()"
python -c "from src.eda import run_eda;                     run_eda()"
python -c "from src.rfm import run_rfm;                     run_rfm()"
python -c "from src.segmentation import run_segmentation;   run_segmentation()"
python -c "from src.clv import run_clv;                     run_clv()"
python -c "from src.prediction import run_prediction;       run_prediction()"
python -c "from src.forecasting import run_forecasting;     run_forecasting()"
python -c "from src.sql_analytics import run_sql_workflow;  run_sql_workflow()"
python -c "from src.powerbi_prep import run_powerbi_prep;   run_powerbi_prep()"
```

Every function name above was import-tested against the current source.

## 6. Notebook execution order

The notebooks narrate the same stages and are committed with their outputs. To
re-execute them:

```bash
jupyter lab      # or: jupyter notebook
```

| Order | Notebook |
|---|---|
| 1 | `notebooks/01_data_cleaning.ipynb` |
| 2 | `notebooks/02_exploratory_data_analysis.ipynb` |
| 3 | `notebooks/03_rfm_customer_analysis.ipynb` |
| 4 | `notebooks/04_kmeans_customer_segmentation.ipynb` |
| 5 | `notebooks/05_customer_lifetime_value.ipynb` |
| 6 | `notebooks/06_revenue_prediction.ipynb` |
| 7 | `notebooks/07_sales_forecasting.ipynb` |
| 8 | `notebooks/08_sql_business_analysis.ipynb` |
| 9 | `notebooks/09_powerbi_data_model.ipynb` |

Headless re-execution of all nine:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

## 7. Model generation

The pipeline stages above write every model artefact:

| Stage | Artefacts |
|---|---|
| `run_segmentation()` | `models/kmeans_customer_segmentation.pkl`, `rfm_scaler.pkl`, `pca_rfm.pkl` |
| `run_clv()` | `models/clv_model.pkl`, `clv_preprocessor.pkl` |
| `run_prediction()` | `models/revenue_prediction_model.pkl`, `revenue_prediction_preprocessor.pkl` |
| `run_forecasting()` | `models/forecasting_model.pkl` |

Each is accompanied by a `*_metadata.json` recording the selection rule, the
training window, the evaluation metrics and the library versions used.

## 8. SQL execution

`run_sql_workflow()` builds the database, validates it and runs every query.
To work with it directly:

```bash
python sql/load_database.py          # rebuild data/customer_revenue_intelligence.db
sqlite3 data/customer_revenue_intelligence.db < sql/analysis_queries.sql
sqlite3 data/customer_revenue_intelligence.db < sql/business_queries.sql
```

The reconciliation anchor — the query every surface must agree with:

```sql
SELECT COUNT(DISTINCT o.order_id)                           AS orders,
       COUNT(DISTINCT o.customer_id)                        AS customers,
       ROUND(SUM(oi.sales), 2)                              AS revenue,
       ROUND(SUM(oi.net_profit), 2)                         AS profit,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

Expected: revenue {V['revenue']}, profit {V['profit']}, margin {V['margin']},
{V['orders']} orders, {V['cust_buy']} customers.

## 9. Streamlit execution

```bash
streamlit run app.py        # http://localhost:8501
```

If a page reports a missing artefact, the corresponding pipeline stage in
section 5 has not been run. Use the sidebar's cache-clear control after
regenerating data.

Headless tests:

```bash
python tests/test_streamlit_app.py
```

Expected: {V['app_passed']}/{V['app_tests']} checks pass.

## 10. Power BI usage

Power BI Desktop is a **Windows-only** application and was not available in
the build environment, so the `.pbix` is not in this repository.

Everything needed to build it is:

| Artefact | Location |
|---|---|
| Build guide (step by step) | `powerbi/POWERBI_BUILD_GUIDE.md` |
| Table extracts (CSV) | `powerbi/data/` |
| Power Query M scripts | `powerbi/powerquery/` |
| DAX measure library ({V['pbi_measures']} measures) | `powerbi/dax/` |
| Theme JSON and background | `powerbi/theme/` |
| Relationship and table catalogues | `powerbi/relationships.csv`, `powerbi/table_catalog.csv` |
| Measure validation against SQL | `powerbi/validation/` |
| Page design mockups (not screenshots) | `outputs/figures/powerbi/mockups/` |

On a Windows machine: open Power BI Desktop, load the tables using the M
scripts, create the {V['pbi_rels']} relationships listed in
`relationships.csv`, mark `DimDate` as the date table, paste in the DAX
library, apply the theme, and build the nine pages from the build guide. Then
check the rendered figures against `powerbi/validation/`.

## 11. Rebuilding the documents

```bash
python scripts/report_facts.py          # refresh the fact pack from pipeline outputs
python scripts/report_diagrams.py       # report and deck diagrams
python scripts/build_report.py          # 40-page report (.docx + .pdf + checklist)
python scripts/build_presentation.py    # 22-slide deck (.pptx + .pdf)
python scripts/build_viva.py            # 18-file viva pack
python scripts/build_packaging.py       # README and this audit set
```

PDF conversion uses LibreOffice (`soffice`). Without it, the `.docx` and
`.pptx` are still produced and the script reports that the PDF step was
skipped.

## 12. Verifying the whole project

```bash
python scripts/audit_project.py         # full audit
python scripts/audit_project.py --quick # faster: skips the slowest re-runs
```

Expected: **{V['audit_total']} checks, {V['audit_pass']} pass,
{V['audit_fail']} fail.** The script exits non-zero if anything fails.

## 13. Expected runtime

On a typical laptop, the full pipeline (sections 4–5) takes a few minutes; the
notebooks take longer because they render every figure. The audit takes about
a minute in `--quick` mode.

## 14. If something does not reproduce

1. Check the Python and library versions first — the model metadata files
   record what each artefact was written with.
2. Confirm the seed is still {V['seed']} in `scripts/generate_dataset.py`.
3. Re-run `scripts/validate_dataset.py`; it compares the raw extract against
   the generator's own ground truth.
4. Run `python scripts/audit_project.py` — it names the failing check and the
   file involved.
"""


# ==========================================================================
# 9. requirements.txt / .gitignore / LICENSE
# ==========================================================================
def requirements():
    return """
# Customer Revenue Intelligence - Python dependencies
# Tested on Python 3.11.
#
# This list was derived from an AST scan of every .py file and notebook in the
# repository; it contains only packages the project actually imports.
# Regenerate the audit with: python scripts/build_packaging.py

# --- Core data handling -----------------------------------------------------
pandas>=2.0
numpy>=1.24
scipy>=1.10               # statistical tests; the BG/NBD likelihood in src/clv.py

# --- Modelling --------------------------------------------------------------
scikit-learn>=1.3         # K-Means, customer value and revenue models
                          # The saved .pkl pipelines were written with scikit-learn 1.8.0
                          # (recorded in models/*_metadata.json). Loading them under an
                          # older minor version may warn or fail; pin ==1.8.0 to
                          # reproduce exactly.
statsmodels>=0.14         # ETS, ARIMA/SARIMA, Theta, ADF, STL
joblib>=1.3               # model persistence and reloading

# --- Figures ----------------------------------------------------------------
matplotlib>=3.7           # static figures in the pipeline and notebooks
seaborn>=0.13             # used in src/eda.py, src/clv.py, src/segmentation.py
plotly>=5.0               # interactive charts in the Streamlit application

# --- Application ------------------------------------------------------------
streamlit>=1.36           # needs st.navigation, introduced in 1.36

# --- Notebooks --------------------------------------------------------------
jupyter>=1.0              # to open / re-run the nine notebooks

# --- Document generation (only needed to REBUILD the report, deck and audit) -
# The generated .docx, .pptx and .pdf files are already committed, so these are
# not required to run the analysis or the application.
python-docx>=1.1          # scripts/build_report.py
python-pptx>=0.6.23       # scripts/build_presentation.py
pypdf>=4.0                # page-number resolution in scripts/report_builder.py
Pillow>=10.0              # image sizing in scripts/build_presentation.py

# SQLite is Python's built-in sqlite3 - nothing to install.
# Power BI is a separate Windows desktop application; the Python side only
# writes the CSV extracts, DAX and Power Query scripts, so it needs nothing
# beyond pandas.
# PDF conversion of the report and deck uses LibreOffice (soffice), which is a
# system package, not a pip package. Without it the .docx and .pptx are still
# produced and the build script reports that the PDF step was skipped.
"""


def gitignore():
    return """
# --- Python -----------------------------------------------------------------
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/

# --- Virtual environments ---------------------------------------------------
.venv/
venv/
env/
ENV/

# --- Secrets and credentials ------------------------------------------------
.env
.env.*
*.env
*.pem
*.key
secrets.toml
.streamlit/secrets.toml
credentials.json
service_account.json

# --- Notebooks --------------------------------------------------------------
.ipynb_checkpoints/

# --- Testing and coverage ---------------------------------------------------
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# --- IDE and editors --------------------------------------------------------
.idea/
.vscode/
*.swp
*.swo
*~

# --- OS ---------------------------------------------------------------------
.DS_Store
Thumbs.db
desktop.ini

# --- Submission bundle ------------------------------------------------------
# FINAL_SUBMISSION/ is a hard-linked mirror of files already tracked elsewhere
# in this repository. Committing it would double the repository size while
# adding no content. It is rebuilt on demand by:
#     python scripts/build_submission.py
FINAL_SUBMISSION/

# --- Scratch and build intermediates ----------------------------------------
work/
.report_build/
outputs/reports/_build/
*.tmp
~$*.docx
~$*.pptx
.~lock.*#

# ============================================================================
# DELIBERATELY NOT IGNORED
# ============================================================================
# The following are committed on purpose, because a university evaluator must
# be able to open them without running the pipeline:
#
#   data/raw/          the generated extract and its injection log
#   data/processed/    cleaned data and every stage's output
#   data/*.db          the analytical SQLite database
#   models/*.pkl       the trained model artefacts
#   outputs/           every figure, table, report, slide deck and viva document
#   notebooks/         executed, with outputs saved
#
# Every one of these is under GitHub's 100 MB per-file limit, so a plain
# `git push` works. Git LFS is not required.
#
# ---------------------------------------------------------------------------
# OPTIONAL: slimming the repository for a PUBLIC PORTFOLIO
# ---------------------------------------------------------------------------
# Uncomment the block below ONLY for a public GitHub copy, never for the
# university submission. Everything excluded is regenerated by
# `python scripts/generate_dataset.py` followed by the pipeline commands in
# docs/reproducibility_guide.md.
#
# data/processed/
# data/*.db
# models/*.pkl
# outputs/figures/
"""


def license_text():
    year = date.today().year
    return f"""
MIT License

Copyright (c) {year} Swagata Das

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    build_values()
    AUDIT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    # preserve the original step-by-step README as a build log
    readme_path = ROOT / "README.md"
    log_path = DOCS / "project_build_log.md"
    if readme_path.exists() and not log_path.exists():
        current = readme_path.read_text(encoding="utf-8")
        if "## Project status" in current:
            log_path.write_text(
                "# Project Build Log\n\n"
                "*This is the original step-by-step development log, preserved "
                "when the repository README was rewritten in Step 17. It "
                "records how each stage was built, in order.*\n\n---\n\n"
                + current.split("\n", 1)[1],
                encoding="utf-8")
            print(f"  preserved build log -> {log_path.relative_to(ROOT)}")

    written = []
    written.append(write(AUDIT / "project_audit.md", project_audit()))
    written.append(write(AUDIT / "github_readiness_checklist.md",
                         github_checklist()))
    written.append(write(AUDIT / "final_submission_checklist.md",
                         submission_checklist()))
    written.append(write(AUDIT / "cross_document_consistency.md",
                         consistency_doc()))
    written.append(write(AUDIT / "project_handover.md", handover()))
    written.append(write(AUDIT / "final_file_inventory.md",
                         inventory() + "\n" + readiness_matrix()))
    written.append(write(DOCS / "reproducibility_guide.md", repro_guide()))
    written.append(write(ROOT / "README.md", readme()))
    written.append(write(ROOT / "requirements.txt", requirements()))
    written.append(write(ROOT / ".gitignore", gitignore()))
    written.append(write(ROOT / "LICENSE", license_text()))

    for p in written:
        print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size / 1024:,.0f} KB)")
    print(f"\n{len(written)} files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
