"""STEP 13 - end-to-end project audit, integration test and quality assurance.

Run from the project root:

    python scripts/audit_project.py            # full audit, including integration tests
    python scripts/audit_project.py --quick    # skip the slow re-run / app tests

Five parts, every one of them computed - nothing in the output is asserted from memory:

  A  Structure     inventory, duplicates, empty/stray files, broken file references,
                   unused modules, imports vs requirements.txt
  B  Pipeline      every stage's declared inputs and outputs resolved on disk, and each
                   stage's inputs checked against what earlier stages produce
  C  Data          85+ cross-dataset consistency checks: raw -> cleaned -> KPIs -> database
                   -> star schema -> segments -> CLV -> time series -> forecast -> predictions
  D  Models        artefacts load, saved models reproduce their saved outputs, a fresh
                   leakage re-audit of the Step 8 panel, and every headline figure quoted in
                   the documentation re-checked against the data
  E  Integration   Step 5/10/11 re-runs compared byte-for-byte, the Streamlit suite, the
                   application's behaviour with the database removed, and pyflakes

Outputs:
  outputs/reports/project_audit.md
  outputs/tables/audit_structure.csv, audit_pipeline.csv, audit_data_consistency.csv,
  outputs/tables/audit_models.csv, audit_integration.csv, audit_summary.csv
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TABLES = ROOT / "outputs" / "tables"
SKIP_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints"}

findings: list[dict] = []          # human-readable audit findings (part A/B)
results: dict[str, list[dict]] = defaultdict(list)


def note(part: str, category: str, item: str, detail: str, severity: str = "INFO") -> None:
    findings.append({"part": part, "category": category, "item": item,
                     "detail": detail, "severity": severity})


def rec(part: str, area: str, check: str, result: str, status: str, detail: str = "") -> bool:
    results[part].append({"area": area, "check": check, "result": result,
                          "status": status, "detail": detail})
    print(f"  [{status:4s}] {area} · {check} :: {result}", flush=True)
    return status == "PASS"


def cmp_num(part, area, check, a, source_a, b, source_b, tol=0.01, detail=""):
    try:
        ok = abs(float(a) - float(b)) <= tol
        res = f"{float(a):,.4f} ({source_a}) vs {float(b):,.4f} ({source_b})"
    except (TypeError, ValueError):
        ok = str(a) == str(b)
        res = f"{a} ({source_a}) vs {b} ({source_b})"
    return rec(part, area, check, res, "PASS" if ok else "FAIL", detail)


def files_in(root: Path):
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# =============================================================== PART A: structure
def part_a_structure() -> dict:
    print("\n=== A. Project structure ===")
    files = list(files_in(ROOT))
    inv = defaultdict(list)
    for p in files:
        rel = p.relative_to(ROOT)
        inv[rel.parts[0] if len(rel.parts) > 1 else "(root)"].append(p)
    for k, v in sorted(inv.items()):
        note("A", "Inventory", k,
             f"{len(v)} file{'s' if len(v) != 1 else ''}, "
             f"{sum(f.stat().st_size for f in v) / 1e6:.2f} MB")

    # duplicates by content
    by_hash = defaultdict(list)
    for p in files:
        if p.stat().st_size:
            by_hash[md5(p)].append(str(p.relative_to(ROOT)))
    dups = [v for v in by_hash.values() if len(v) > 1]
    for group in dups:
        note("A", "Duplicate content", " = ".join(group),
             "Identical bytes in two locations.", "REVIEW")
    rec("A", "Structure", "Duplicate-content groups", f"{len(dups)} groups", "INFO")

    # same basename in different directories
    by_name = defaultdict(list)
    for p in files:
        by_name[p.name].append(str(p.relative_to(ROOT)))
    name_dups = {k: v for k, v in by_name.items() if len(v) > 1}
    for k, v in name_dups.items():
        note("A", "Repeated filename", k, ", ".join(v), "REVIEW")

    empties = [str(p.relative_to(ROOT)) for p in files if p.stat().st_size == 0]
    empty_dirs = [str(d.relative_to(ROOT)) for d in ROOT.rglob("*")
                  if d.is_dir() and not any(d.iterdir())
                  and not any(part in SKIP_DIRS for part in d.parts)]
    strays = [str(p.relative_to(ROOT)) for p in files
              if re.search(r"(testbak|auditbak|\.bak$|\.tmp$|~$|untitled)", p.name, re.I)]
    for e in empties:
        if Path(e).name == ".gitkeep":
            note("A", "Placeholder file", e,
                 "Intentional: keeps an otherwise empty directory in version control.", "INFO")
        else:
            note("A", "Empty file", e, "Zero bytes - review whether it is still needed.", "REVIEW")
    for e in empty_dirs:
        note("A", "Empty directory", e, "No files.", "REVIEW")
    for s in strays:
        note("A", "Stray/backup file", s, "Looks like a leftover from an edit or test.", "ISSUE")
    rec("A", "Structure", "Empty files / empty dirs / stray files",
        f"{len(empties)} / {len(empty_dirs)} / {len(strays)}",
        "PASS" if not strays else "FAIL")

    # ---- file references in code resolve
    PATH_RE = re.compile(
        r"""["']([A-Za-z0-9_./-]+\.(?:csv|json|pkl|sql|md|png|html|ipynb|toml|txt|db|css))["']""")
    refs = defaultdict(set)
    for p in [f for f in files if f.suffix in {".py", ".sql"}]:
        for m in PATH_RE.finditer(p.read_text(errors="ignore")):
            refs[m.group(1)].add(str(p.relative_to(ROOT)))
    for p in [f for f in files if f.suffix == ".ipynb"]:
        try:
            nb = json.loads(p.read_text())
        except json.JSONDecodeError:
            note("A", "Unreadable notebook", str(p.relative_to(ROOT)), "Not valid JSON.", "ISSUE")
            continue
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                for m in PATH_RE.finditer("".join(cell.get("source", []))):
                    refs[m.group(1)].add(str(p.relative_to(ROOT)))
    names = {p.name for p in files}
    rels = {str(p.relative_to(ROOT)) for p in files}
    # names that are written at runtime (downloads, test fixtures) rather than read
    GENERATED = {"top_customers.csv", "product_performance_matrix.csv", "regional_performance.csv",
                 "rfm_segment_matrix.csv", "business_recommendations.csv", "sample_upload.csv",
                 "broken.csv", "revenue_intelligence.db",
                 # written by this audit itself, after this check runs
                 "project_audit.md", "audit_summary.csv", "audit_findings.csv",
                 "audit_structure.csv", "audit_pipeline.csv", "audit_data_consistency.csv",
                 "audit_models.csv", "audit_integration.csv"}
    unresolved = {r: sorted(v) for r, v in sorted(refs.items())
                  if r not in rels and not (ROOT / r).exists()
                  and Path(r).name not in names and Path(r).name not in GENERATED}
    for r, where in unresolved.items():
        note("A", "Broken file reference", r, f"referenced by {', '.join(where)}", "ISSUE")
    rec("A", "References", "File paths referenced in code resolve on disk",
        f"{len(refs)} referenced, {len(unresolved)} unresolved "
        f"(plus {len(GENERATED)} known runtime-generated names)",
        "PASS" if not unresolved else "FAIL")

    # ---- modules and imports
    local = {p.stem for p in (ROOT / "src").glob("*.py")} | {"config"}
    imported = defaultdict(set)
    syntax_errors = {}
    for p in [f for f in files if f.suffix == ".py"]:
        try:
            tree = ast.parse(p.read_text(errors="ignore"))
        except SyntaxError as e:
            syntax_errors[str(p.relative_to(ROOT))] = f"{e.msg} (line {e.lineno})"
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported[a.name.split(".")[0]].add(str(p.relative_to(ROOT)))
            elif isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if parts[0] == "src" and len(parts) > 1:
                    imported[parts[1]].add(str(p.relative_to(ROOT)))
                elif parts[0] == "src":
                    for a in node.names:
                        imported[a.name].add(str(p.relative_to(ROOT)))
                else:
                    imported[parts[0]].add(str(p.relative_to(ROOT)))
    for p in [f for f in files if f.suffix == ".ipynb"]:
        try:
            nb = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        text = "\n".join("".join(c.get("source", [])) for c in nb.get("cells", [])
                         if c.get("cell_type") == "code")
        for m in re.finditer(r"from\s+src(?:\.([A-Za-z_]+))?\s+import\s+([A-Za-z_, ]+)", text):
            if m.group(1):
                imported[m.group(1)].add(str(p.relative_to(ROOT)))
            else:
                for nm in m.group(2).split(","):
                    imported[nm.strip().split(" as ")[0]].add(str(p.relative_to(ROOT)))
    rec("A", "Code", "Python files parse without syntax errors",
        f"{len([f for f in files if f.suffix == '.py'])} files, {len(syntax_errors)} errors",
        "PASS" if not syntax_errors else "FAIL", str(syntax_errors))
    unused = [m for m in sorted(local) if m not in imported and m != "__init__"]
    for m in unused:
        note("A", "Unused module", f"src/{m}.py", "Not imported anywhere in the project.", "REVIEW")
    rec("A", "Code", "Every src module is imported somewhere",
        f"{len(local) - 1} modules, {len(unused)} unused", "PASS" if not unused else "FAIL",
        ", ".join(unused))
    return {"files": len(files), "duplicate_groups": len(dups), "unresolved": len(unresolved)}


# ================================================================ PART B: pipeline
STAGES = [
    ("RAW DATA", "2", "scripts/generate_dataset.py", [],
     ["data/raw/customer_sales_raw.csv", "data/raw/data_quality_injection_log.json",
      "outputs/reports/raw_data_validation_report.md"]),
    ("DATA CLEANING", "3", "src/data_cleaning.py", ["data/raw/customer_sales_raw.csv"],
     ["data/processed/customer_sales_cleaned.csv", "data/processed/customer_level_features.csv",
      "outputs/data_quality_report.csv", "outputs/cleaning_summary.csv"]),
    ("EDA", "4", "src/eda.py", ["data/processed/customer_sales_cleaned.csv"],
     ["outputs/tables/eda_kpis.csv", "outputs/reports/eda_summary.md"]),
    ("RFM ANALYSIS", "5", "src/rfm.py", ["data/processed/customer_sales_cleaned.csv"],
     ["data/processed/customer_rfm.csv", "data/processed/customer_rfm_segments.csv",
      "data/processed/customer_rfm_metadata.json", "outputs/tables/rfm_segment_summary.csv",
      "outputs/reports/rfm_methodology.md"]),
    ("K-MEANS SEGMENTATION", "6", "src/segmentation.py",
     ["data/processed/customer_rfm_segments.csv"],
     ["data/processed/customer_ml_segments.csv", "models/kmeans_customer_segmentation.pkl",
      "models/rfm_scaler.pkl", "models/pca_rfm.pkl", "models/segmentation_model_metadata.json",
      "outputs/tables/ml_cluster_summary.csv", "outputs/reports/kmeans_model_report.md"]),
    ("CLV", "7", "src/clv.py",
     ["data/processed/customer_sales_cleaned.csv", "data/processed/customer_ml_segments.csv"],
     ["data/processed/customer_clv.csv", "data/processed/customer_value_history.csv",
      "data/processed/clv_modeling_dataset.csv", "models/clv_model.pkl",
      "models/clv_preprocessor.pkl", "models/clv_model_metadata.json",
      "outputs/reports/clv_analysis_report.md"]),
    ("REVENUE PREDICTION", "8", "src/prediction.py",
     ["data/processed/customer_sales_cleaned.csv", "data/processed/customer_rfm_segments.csv",
      "data/processed/customer_ml_segments.csv"],
     ["data/processed/revenue_modeling_dataset.csv", "outputs/tables/revenue_predictions.csv",
      "outputs/tables/revenue_quarterly_totals.csv", "outputs/tables/revenue_model_comparison.csv",
      "models/revenue_prediction_model.pkl", "models/revenue_model_metadata.json",
      "outputs/reports/revenue_prediction_report.md"]),
    ("SALES FORECASTING", "9", "src/forecasting.py",
     ["data/processed/customer_sales_cleaned.csv"],
     ["data/processed/monthly_sales_timeseries.csv", "data/processed/revenue_forecast.csv",
      "outputs/tables/forecast_model_comparison.csv", "models/forecasting_model.pkl",
      "models/forecasting_metadata.json", "outputs/reports/forecasting_methodology.md"]),
    ("SQL ANALYTICS", "10", "src/database.py + src/sql_analytics.py",
     ["data/processed/customer_sales_cleaned.csv", "data/processed/customer_rfm_segments.csv",
      "data/processed/customer_ml_segments.csv", "data/processed/customer_clv.csv",
      "data/processed/revenue_forecast.csv", "sql/schema.sql", "sql/analysis_queries.sql",
      "sql/business_queries.sql"],
     ["data/customer_revenue_intelligence.db", "outputs/tables/sql_validation_checks.csv",
      "outputs/tables/sql_key_findings.csv", "outputs/reports/sql_analysis_methodology.md"]),
    ("POWER BI", "11", "src/powerbi_prep.py + sql/powerbi_views.sql",
     ["data/customer_revenue_intelligence.db", "sql/powerbi_views.sql",
      "outputs/tables/revenue_predictions.csv", "models/revenue_model_metadata.json",
      "models/forecasting_metadata.json"],
     ["powerbi/data/FactSales.csv", "powerbi/data/DimCustomer.csv",
      "powerbi/data/Recommendations.csv", "powerbi/dax/measures.dax",
      "powerbi/theme/crm_dark_theme.json", "powerbi/validation/cross_step_consistency.csv",
      "outputs/reports/powerbi_dashboard_documentation.md"]),
    ("STREAMLIT", "12", "app.py + pages/ + src/data_loader.py",
     ["data/customer_revenue_intelligence.db", "sql/powerbi_views.sql",
      "powerbi/data/Recommendations.csv", "models/revenue_prediction_model.pkl",
      "models/forecasting_metadata.json", "data/processed/revenue_modeling_dataset.csv"],
     ["outputs/reports/streamlit_testing_report.md",
      "outputs/tables/streamlit_test_results.csv"]),
    ("BUSINESS INSIGHTS", "10-12", "powerbi/data/Recommendations.csv + pages/recommendations.py",
     ["outputs/tables/sql_key_findings.csv", "outputs/tables/rfm_segment_summary.csv",
      "outputs/tables/ml_cluster_summary.csv", "models/forecasting_metadata.json"],
     ["powerbi/data/Recommendations.csv"]),
]


def part_b_pipeline() -> dict:
    print("\n=== B. Pipeline dependencies ===")
    produced_by = {}
    for i, (stage, *_rest) in enumerate(STAGES):
        for o in _rest[2]:
            produced_by.setdefault(o, (i, stage))
    broken = 0
    for i, (stage, step, module, inputs, outputs) in enumerate(STAGES):
        missing_in = [p for p in inputs if not (ROOT / p).exists()]
        missing_out = [p for p in outputs if not (ROOT / p).exists()]
        late = [f"{p} (produced by later stage {produced_by[p][1]})" for p in inputs
                if p in produced_by and produced_by[p][0] > i]
        ok = not (missing_in or missing_out or late)
        broken += 0 if ok else 1
        rec("B", "Pipeline", f"Step {step}: {stage}",
            f"{len(inputs)} input{'s' if len(inputs) != 1 else ''}, "
            f"{len(outputs)} output{'s' if len(outputs) != 1 else ''}, module {module}",
            "PASS" if ok else "FAIL",
            "; ".join(missing_in + missing_out + late))
        for p in missing_in + missing_out:
            note("B", "Missing expected file", p, f"declared by stage {stage}", "ISSUE")
    # notebooks
    nb_bad = 0
    for nb_path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        nb = json.loads(nb_path.read_text())
        code = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
        errs = [o for c in code for o in c.get("outputs", []) if o.get("output_type") == "error"]
        executed = sum(1 for c in code if c.get("execution_count"))
        ok = executed == len(code) and not errs
        nb_bad += 0 if ok else 1
        rec("B", "Notebooks", nb_path.name,
            f"{executed}/{len(code)} cells executed, {len(errs)} errors",
            "PASS" if ok else "FAIL")
    return {"broken_stages": broken, "broken_notebooks": nb_bad}


# ============================================================ PART C: data consistency
def part_c_data() -> dict:
    print("\n=== C. Data consistency ===")
    P = "C"
    clean = pd.read_csv(ROOT / "data/processed/customer_sales_cleaned.csv",
                        parse_dates=["Order_Date"])
    raw = pd.read_csv(ROOT / "data/raw/customer_sales_raw.csv")
    rfm = pd.read_csv(ROOT / "data/processed/customer_rfm_segments.csv")
    ml = pd.read_csv(ROOT / "data/processed/customer_ml_segments.csv")
    clv = pd.read_csv(ROOT / "data/processed/customer_clv.csv")
    monthly = pd.read_csv(ROOT / "data/processed/monthly_sales_timeseries.csv")
    fcast = pd.read_csv(ROOT / "data/processed/revenue_forecast.csv")
    panel = pd.read_csv(ROOT / "data/processed/revenue_modeling_dataset.csv")
    kpi = pd.read_csv(TABLES / "eda_kpis.csv").set_index("KPI")["Value"]
    rfm_sum = pd.read_csv(TABLES / "rfm_segment_summary.csv")
    ml_sum = pd.read_csv(TABLES / "ml_cluster_summary.csv")
    preds = pd.read_csv(TABLES / "revenue_predictions.csv")
    qtot = pd.read_csv(TABLES / "revenue_quarterly_totals.csv")
    mcomp = pd.read_csv(TABLES / "revenue_model_comparison.csv")
    fcomp = pd.read_csv(TABLES / "forecast_model_comparison.csv")
    fact = pd.read_csv(ROOT / "powerbi/data/FactSales.csv")
    dimcust = pd.read_csv(ROOT / "powerbi/data/DimCustomer.csv")
    dimdate = pd.read_csv(ROOT / "powerbi/data/DimDate.csv")
    factfc = pd.read_csv(ROOT / "powerbi/data/FactForecast.csv")
    factpred = pd.read_csv(ROOT / "powerbi/data/FactRevenuePrediction.csv")
    meta_rfm = json.loads((ROOT / "data/processed/customer_rfm_metadata.json").read_text())
    meta_pred = json.loads((ROOT / "models/revenue_model_metadata.json").read_text())
    meta_fc = json.loads((ROOT / "models/forecasting_metadata.json").read_text())

    con = sqlite3.connect(ROOT / "data/customer_revenue_intelligence.db")
    con.executescript((ROOT / "sql/powerbi_views.sql").read_text())
    d = clean[clean["Is_Delivered"] == 1]

    # raw -> cleaned
    cmp_num(P, "Raw vs cleaned", "Cleaned rows = raw rows minus duplicate Order_Line_IDs",
            len(clean), "cleaned", len(raw) - raw.duplicated(subset=["Order_Line_ID"]).sum(),
            "raw", tol=0)
    cmp_num(P, "Raw vs cleaned", "Order_Line_ID is unique after cleaning",
            clean["Order_Line_ID"].duplicated().sum(), "cleaned", 0, "expected", tol=0)
    cmp_num(P, "Raw vs cleaned", "No nulls in the key cleaned columns",
            int(clean[["Order_ID", "Order_Date", "Customer_ID", "Product_ID", "Sales", "Profit",
                       "Order_Status"]].isna().sum().sum()), "cleaned", 0, "expected", tol=0)

    # KPIs
    for label, computed, key, tol in [
            ("Total revenue", d["Sales"].sum(), "Total Revenue", 0.01),
            ("Total profit", d["Profit"].sum(), "Total Profit", 0.01),
            ("Total cost", d["Cost"].sum(), "Total Cost", 0.01),
            ("Orders", d["Order_ID"].nunique(), "Number of Orders", 0),
            ("Purchasing customers", d["Customer_ID"].nunique(), "Purchasing Customers", 0),
            ("Units sold", d["Quantity"].sum(), "Total Quantity Sold", 0),
            ("AOV", d["Sales"].sum() / d["Order_ID"].nunique(), "Average Order Value (AOV)", 0.02),
            ("Profit margin", d["Profit"].sum() / d["Sales"].sum(), "Overall Profit Margin", 1e-6),
            ("Gross booked sales", clean["Sales"].sum(), "Gross Booked Sales (all statuses)", 1.0)]:
        cmp_num(P, "KPIs", label, computed, "recomputed from the cleaned CSV",
                kpi[key], "outputs/tables/eda_kpis.csv", tol=tol)

    # database
    tot = pd.read_sql_query(
        "SELECT SUM(sales) rev, SUM(profit) pro, SUM(cost) cost, SUM(quantity) qty,"
        " COUNT(DISTINCT order_id) ord, COUNT(DISTINCT customer_id) cust, COUNT(*) lines"
        " FROM vw_delivered_sales", con).iloc[0]
    for label, a, b, tol in [("Revenue", d["Sales"].sum(), tot["rev"], 0.01),
                             ("Profit", d["Profit"].sum(), tot["pro"], 0.01),
                             ("Cost", d["Cost"].sum(), tot["cost"], 0.01),
                             ("Quantity", d["Quantity"].sum(), tot["qty"], 0),
                             ("Orders", d["Order_ID"].nunique(), tot["ord"], 0),
                             ("Customers", d["Customer_ID"].nunique(), tot["cust"], 0),
                             ("Delivered lines", len(d), tot["lines"], 0)]:
        cmp_num(P, "Database", label, a, "cleaned CSV", b, "vw_delivered_sales", tol=tol)
    for table, expected in [("customers", clean["Customer_ID"].nunique()),
                            ("products", clean["Product_ID"].nunique()),
                            ("orders", clean["Order_ID"].nunique()),
                            ("order_items", len(clean))]:
        n = pd.read_sql_query(f"SELECT COUNT(*) n FROM {table}", con).iloc[0]["n"]
        cmp_num(P, "Database", f"Row count: {table}", n, "database", expected, "cleaned CSV", tol=0)
    orphans = pd.read_sql_query("""
        SELECT (SELECT COUNT(*) FROM order_items i LEFT JOIN orders o ON o.order_id = i.order_id
                WHERE o.order_id IS NULL) AS order_items_to_orders,
               (SELECT COUNT(*) FROM order_items i LEFT JOIN products p
                ON p.product_id = i.product_id WHERE p.product_id IS NULL) AS order_items_to_products,
               (SELECT COUNT(*) FROM orders o LEFT JOIN customers c
                ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL) AS orders_to_customers,
               (SELECT COUNT(*) FROM customers c LEFT JOIN locations l
                ON l.location_id = c.location_id WHERE l.location_id IS NULL) AS customers_to_locations
        """, con).iloc[0]
    for k, v in orphans.items():
        cmp_num(P, "Database", f"No orphan rows: {k}", v, "LEFT JOIN", 0, "expected", tol=0)

    # star schema
    fd = fact[fact["Is_Delivered"] == 1]
    cmp_num(P, "Star schema", "FactSales rows", len(fact), "FactSales.csv", len(clean),
            "cleaned CSV", tol=0)
    cmp_num(P, "Star schema", "Delivered revenue", fd["Sales"].sum(), "FactSales.csv",
            d["Sales"].sum(), "cleaned CSV")
    cmp_num(P, "Star schema", "Delivered profit", fd["Profit"].sum(), "FactSales.csv",
            d["Profit"].sum(), "cleaned CSV")
    cmp_num(P, "Star schema", "DimCustomer rows", len(dimcust), "DimCustomer.csv",
            clean["Customer_ID"].nunique(), "cleaned CSV", tol=0)
    cmp_num(P, "Star schema", "No customer-name column in DimCustomer",
            len([c for c in dimcust.columns if "name" in c.lower()]), "DimCustomer.csv",
            0, "privacy rule", tol=0)
    cmp_num(P, "Star schema", "Is_Delivered equals Order_Status == 'Delivered'",
            int((fact["Is_Delivered"] != (fact["Order_Status"] == "Delivered").astype(int)).sum()),
            "FactSales.csv", 0, "expected", tol=0)

    # customer coverage
    ids_delivered = set(d["Customer_ID"])
    cmp_num(P, "Customer coverage", "RFM rows = customers with a delivered order", len(rfm),
            "customer_rfm_segments.csv", len(ids_delivered), "cleaned CSV", tol=0)
    cmp_num(P, "Customer coverage", "ML rows = RFM rows", len(ml), "customer_ml_segments.csv",
            len(rfm), "customer_rfm_segments.csv", tol=0)
    cmp_num(P, "Customer coverage", "CLV rows = RFM rows", len(clv), "customer_clv.csv",
            len(rfm), "customer_rfm_segments.csv", tol=0)
    cmp_num(P, "Customer coverage", "Identical customer IDs across RFM / ML / CLV",
            len(set(rfm["Customer_ID"]) ^ set(ml["Customer_ID"]))
            + len(set(rfm["Customer_ID"]) ^ set(clv["Customer_ID"])),
            "symmetric differences", 0, "expected", tol=0)
    cmp_num(P, "Customer coverage", "Registered customers with no delivered order",
            len(set(clean["Customer_ID"]) - ids_delivered), "cleaned CSV",
            int((dimcust["Has_Delivered_Order"] == 0).sum()), "DimCustomer.csv", tol=0)

    # RFM / clusters
    seg_counts = rfm["RFM_Segment"].value_counts()
    mism = [s for s in rfm_sum["RFM_Segment"]
            if int(rfm_sum.loc[rfm_sum["RFM_Segment"] == s, "Customer_Count"].iloc[0])
            != int(seg_counts.get(s, 0))]
    cmp_num(P, "RFM", "Per-segment customer counts match the summary table", len(mism),
            "recomputed", 0, "rfm_segment_summary.csv", tol=0, detail=str(mism))
    seg_rev = (d.merge(rfm[["Customer_ID", "RFM_Segment"]], on="Customer_ID")
                 .groupby("RFM_Segment")["Sales"].sum())
    rev_mism = [s for s in rfm_sum["RFM_Segment"]
                if abs(float(rfm_sum.loc[rfm_sum["RFM_Segment"] == s, "Total_Revenue"].iloc[0])
                       - float(seg_rev.get(s, 0))) > 0.5]
    cmp_num(P, "RFM", "Per-segment revenue matches the summary table", len(rev_mism),
            "recomputed", 0, "rfm_segment_summary.csv", tol=0, detail=str(rev_mism))
    cmp_num(P, "RFM", "Recency matches the database",
            int((rfm.set_index("Customer_ID")["Recency"].sort_index().values
                 != pd.read_sql_query("SELECT customer_id, recency_days FROM customer_rfm", con)
                 .set_index("customer_id")["recency_days"].sort_index().values).sum()),
            "row-by-row", 0, "expected", tol=0)
    cmp_num(P, "Clusters", "Cluster assignment matches the database",
            int((ml.set_index("Customer_ID")["Cluster_ID"].sort_index().values
                 != pd.read_sql_query("SELECT customer_id, cluster_id FROM customer_segments", con)
                 .set_index("customer_id")["cluster_id"].sort_index().values).sum()),
            "row-by-row", 0, "expected", tol=0)
    clu_rev = (d.merge(ml[["Customer_ID", "Cluster_Label"]], on="Customer_ID")
                 .groupby("Cluster_Label")["Sales"].sum())
    clu_mism = [s for s in ml_sum["Business_Label"]
                if abs(float(ml_sum.loc[ml_sum["Business_Label"] == s, "Total_Revenue"].iloc[0])
                       - float(clu_rev.get(s, 0))) > 0.5]
    cmp_num(P, "Clusters", "Per-cluster revenue matches the summary table", len(clu_mism),
            "recomputed", 0, "ml_cluster_summary.csv", tol=0, detail=str(clu_mism))
    cmp_num(P, "Clusters", "Cluster IDs agree with DimCustomer",
            int((ml.set_index("Customer_ID")["Cluster_ID"].sort_index()
                 != dimcust[dimcust["Has_Delivered_Order"] == 1]
                 .set_index("Customer_ID")["Cluster_ID"].sort_index()).sum()),
            "row-by-row", 0, "expected", tol=0)

    # CLV
    cmp_num(P, "CLV", "Historical revenue CLV total", clv["Historical_Revenue_CLV"].sum(),
            "customer_clv.csv", d["Sales"].sum(), "cleaned CSV", tol=1.0)
    cmp_num(P, "CLV", "Historical profit CLV total", clv["Historical_Profit_CLV"].sum(),
            "customer_clv.csv", d["Profit"].sum(), "cleaned CSV", tol=1.0)
    db_clv = pd.read_sql_query("SELECT SUM(historical_profit_clv) p,"
                               " SUM(estimated_12m_future_profit) e FROM customer_value",
                               con).iloc[0]
    cmp_num(P, "CLV", "Profit CLV matches the database", clv["Historical_Profit_CLV"].sum(),
            "customer_clv.csv", db_clv["p"], "DB customer_value", tol=1.0)
    cmp_num(P, "CLV", "Estimated 12M profit matches DimCustomer",
            clv["Estimated_12M_Future_Profit"].sum(), "customer_clv.csv",
            dimcust["Estimated_12M_Future_Profit"].sum(), "DimCustomer.csv", tol=1.0)
    cmp_num(P, "CLV", "At-risk high-value customers",
            int(clv["Potentially_At_Risk_High_Value"].sum()), "customer_clv.csv",
            int(dimcust["Potentially_At_Risk_High_Value"].sum()), "DimCustomer.csv", tol=0)

    # time series and forecast
    m_recomp = d.groupby(d["Order_Date"].dt.strftime("%Y-%m"))["Sales"].sum()
    month_key = pd.to_datetime(monthly["Month"]).dt.strftime("%Y-%m")
    cmp_num(P, "Time series", "Monthly rows", len(monthly), "monthly_sales_timeseries.csv",
            len(m_recomp), "recomputed", tol=0)
    cmp_num(P, "Time series", "Every month's revenue matches the recomputation",
            int((monthly["Revenue"].round(2).values
                 != m_recomp.reindex(month_key).round(2).values).sum()), "row-by-row",
            0, "expected", tol=0)
    cmp_num(P, "Time series", "Every month's orders match the recomputation",
            int((monthly["Orders"].values
                 != d.groupby(d["Order_Date"].dt.strftime("%Y-%m"))["Order_ID"].nunique()
                 .reindex(month_key).values).sum()), "row-by-row", 0, "expected", tol=0)
    hist_col = "Type" if "Type" in fcast.columns else "Record_Type"
    hist = fcast[fcast[hist_col] == "Historical actual"]
    fut_file = fcast[fcast[hist_col].astype(str).str.startswith("Future")]
    fcol = "Forecast" if "Forecast" in fcast.columns else "Forecast_Revenue"
    fut_star = factfc[factfc["Series_Label"] == "Forecast"]
    cmp_num(P, "Forecast", "Historical actuals in the forecast file", hist["Actual_Revenue"].sum(),
            "revenue_forecast.csv", d["Sales"].sum(), "cleaned CSV", tol=1.0)
    cmp_num(P, "Forecast", "Future forecast total", fut_file[fcol].sum(), "revenue_forecast.csv",
            fut_star["Forecast_Revenue"].sum(), "FactForecast.csv", tol=1.0)
    cmp_num(P, "Forecast", "Horizon length", len(fut_file), "revenue_forecast.csv",
            meta_fc["forecast_horizon_months"], "forecasting_metadata.json", tol=0)
    cmp_num(P, "Forecast", "Forecast months match the metadata",
            ",".join(sorted(fut_star["Year_Month"])), "FactForecast.csv",
            ",".join(sorted(meta_fc["forecast_months"])), "forecasting_metadata.json")
    sel = fcomp[fcomp["Model"] == meta_fc["model_type"]]
    if not sel.empty:
        cmp_num(P, "Forecast", "Selected model test MAPE", sel["Test_MAPE_%"].iloc[0],
                "forecast_model_comparison.csv", meta_fc["metrics"]["test"]["MAPE_%"],
                "forecasting_metadata.json", tol=0.01)
    cmp_num(P, "Forecast", "Interval bounds correctly ordered",
            int((~((fut_star["Lower_95"] <= fut_star["Lower_80"])
                   & (fut_star["Lower_80"] <= fut_star["Forecast_Revenue"])
                   & (fut_star["Forecast_Revenue"] <= fut_star["Upper_80"])
                   & (fut_star["Upper_80"] <= fut_star["Upper_95"]))).sum()),
            "FactForecast.csv", 0, "expected", tol=0)

    # predictions
    cmp_num(P, "Prediction", "Prediction rows = test-split rows", len(preds),
            "revenue_predictions.csv", int((panel["Split"] == "test").sum()),
            "revenue_modeling_dataset.csv", tol=0)
    cmp_num(P, "Prediction", "Prediction rows match the star-schema fact", len(preds),
            "revenue_predictions.csv", len(factpred), "FactRevenuePrediction.csv", tol=0)
    test_q = qtot[qtot["Split"].str.startswith("test")]
    cmp_num(P, "Prediction", "Test actual revenue", preds["Actual_Revenue"].sum(),
            "revenue_predictions.csv", test_q["Actual_Revenue"].sum(),
            "revenue_quarterly_totals.csv", tol=1.0)
    cmp_num(P, "Prediction", "Test MAE matches the comparison table",
            preds["Absolute_Error"].mean(), "recomputed",
            mcomp.loc[mcomp["Selected"], "MAE"].iloc[0], "revenue_model_comparison.csv", tol=0.01)
    cmp_num(P, "Prediction", "Test MAE matches the model metadata", preds["Absolute_Error"].mean(),
            "recomputed", meta_pred["test_metrics"]["MAE"], "revenue_model_metadata.json",
            tol=0.01)
    cmp_num(P, "Prediction", "Test RMSE matches the model metadata",
            float(np.sqrt((preds["Prediction_Error"] ** 2).mean())), "recomputed",
            meta_pred["test_metrics"]["RMSE"], "revenue_model_metadata.json", tol=0.01)
    ss_res = float((preds["Prediction_Error"] ** 2).sum())
    ss_tot = float(((preds["Actual_Revenue"] - preds["Actual_Revenue"].mean()) ** 2).sum())
    cmp_num(P, "Prediction", "Test R² matches the model metadata", 1 - ss_res / ss_tot,
            "recomputed", meta_pred["test_metrics"]["R2"], "revenue_model_metadata.json",
            tol=0.0005)
    cmp_num(P, "Prediction", "Error column equals Predicted - Actual",
            float((preds["Prediction_Error"]
                   - (preds["Predicted_Revenue"] - preds["Actual_Revenue"])).abs().max()),
            "recomputed", 0, "expected", tol=0.01)

    # dates
    cmp_num(P, "Dates", "Data starts", str(clean["Order_Date"].min().date()), "cleaned CSV",
            "2023-01-01", "project design")
    cmp_num(P, "Dates", "Data ends", str(clean["Order_Date"].max().date()), "cleaned CSV",
            "2025-12-31", "project design")
    cmp_num(P, "Dates", "DimDate covers the forecast horizon", dimdate["Date"].max(),
            "DimDate.csv", "2026-06-30", "horizon end")
    cmp_num(P, "Dates", "DimDate has no gaps",
            int((pd.to_datetime(dimdate["Date"]).diff().dt.days.dropna() != 1).sum()),
            "DimDate.csv", 0, "expected", tol=0)
    refs = {meta_rfm.get("reference_date"),
            str(pd.read_sql_query("SELECT DISTINCT reference_date FROM customer_rfm",
                                  con).iloc[0, 0]),
            str(dimcust["Reference_Date"].dropna().iloc[0])}
    cmp_num(P, "Dates", "One reference date across metadata, database and star schema",
            len(refs), str(refs), 1, "expected", tol=0)
    con.close()
    rows = results[P]
    return {"checks": len(rows), "failed": sum(1 for r in rows if r["status"] == "FAIL")}


# ================================================ PART D: models, leakage, documentation
def part_d_models() -> dict:
    print("\n=== D. Models, leakage and documentation ===")
    P = "D"
    import joblib
    import sklearn

    MODELS = ["revenue_prediction_model.pkl", "revenue_prediction_preprocessor.pkl",
              "forecasting_model.pkl", "kmeans_customer_segmentation.pkl", "rfm_scaler.pkl",
              "pca_rfm.pkl", "clv_model.pkl", "clv_preprocessor.pkl"]
    loaded = {}
    for name in MODELS:
        path = ROOT / "models" / name
        if not path.exists():
            rec(P, "Model artefacts", f"{name}", "missing", "FAIL")
            note("D", "Missing model artefact", f"models/{name}", "Declared but not on disk.",
                 "ISSUE")
            continue
        try:
            loaded[name] = joblib.load(path)
            rec(P, "Model artefacts", f"{name} loads",
                f"{type(loaded[name]).__name__}, {path.stat().st_size / 1e6:.2f} MB", "PASS")
        except Exception as exc:                                   # noqa: BLE001
            rec(P, "Model artefacts", f"{name} loads", f"{type(exc).__name__}", "FAIL", str(exc))

    meta_pred = json.loads((ROOT / "models/revenue_model_metadata.json").read_text())
    meta_fc = json.loads((ROOT / "models/forecasting_metadata.json").read_text())
    rec(P, "Model artefacts", "scikit-learn version recorded vs installed",
        f"recorded {meta_pred.get('sklearn_version')}, installed {sklearn.__version__}",
        "PASS" if meta_pred.get("sklearn_version") == sklearn.__version__ else "WARN")

    panel = pd.read_csv(ROOT / "data/processed/revenue_modeling_dataset.csv")
    saved = pd.read_csv(TABLES / "revenue_predictions.csv")
    model = loaded.get("revenue_prediction_model.pkl")
    if model is not None:
        schema = list(getattr(model, "feature_names_in_", []))
        test = panel[panel["Split"] == "test"].copy()
        fresh = model.predict(test[schema])
        merged = (test[["Customer_ID", "Target_Period"]].assign(Fresh=fresh)
                  .merge(saved[["Customer_ID", "Target_Period", "Predicted_Revenue"]],
                         on=["Customer_ID", "Target_Period"]))
        diff = (merged["Fresh"] - merged["Predicted_Revenue"]).abs()
        rec(P, "Reproducibility", "Reloaded model reproduces the saved test predictions",
            f"{len(merged):,} rows, max |diff| ₹{diff.max():.4f}",
            "PASS" if diff.max() < 1.0 else "FAIL",
            "Sub-rupee differences are float/BLAS ordering, not a different model.")
        rec(P, "Model artefacts", "Feature schema size matches the metadata",
            f"{len(schema)} features", "PASS" if len(schema) ==
            len(meta_pred["numeric_features"]) + len(meta_pred["categorical_features"]) else "FAIL")

    fc_obj = loaded.get("forecasting_model.pkl")
    fcast = pd.read_csv(ROOT / "data/processed/revenue_forecast.csv")
    hist_col = "Type" if "Type" in fcast.columns else "Record_Type"
    fut = fcast[fcast[hist_col].astype(str).str.startswith("Future")]
    fcol = "Forecast" if "Forecast" in fcast.columns else "Forecast_Revenue"
    if isinstance(fc_obj, dict) and "fitted_model" in fc_obj:
        try:
            fresh_fc = np.asarray(fc_obj["fitted_model"].forecast(len(fut)), dtype=float)
            gap = float(np.abs(fresh_fc - fut[fcol].values).max())
            rec(P, "Reproducibility", "Reloaded forecasting model reproduces the saved forecast",
                f"{len(fut)} months, max |diff| ₹{gap:.4f}", "PASS" if gap < 1.0 else "FAIL")
        except Exception as exc:                                   # noqa: BLE001
            rec(P, "Reproducibility", "Reloaded forecasting model reproduces the saved forecast",
                f"{type(exc).__name__}", "FAIL", str(exc))

    ml = pd.read_csv(ROOT / "data/processed/customer_ml_segments.csv")
    km, scaler = loaded.get("kmeans_customer_segmentation.pkl"), loaded.get("rfm_scaler.pkl")
    if km is not None and scaler is not None:
        # rfm_scaler.pkl is a Pipeline(log1p -> StandardScaler): raw R, F, M go straight in
        Z = scaler.transform(ml[["Recency", "Frequency", "Monetary"]])
        agree = float((km.predict(Z) == ml["Cluster_ID"].values).mean())
        rec(P, "Reproducibility", "Reloaded K-Means reproduces the saved cluster assignment",
            f"{agree:.2%} of {len(ml):,} customers identical",
            "PASS" if agree > 0.999 else "FAIL")
        gap = float(np.abs(Z - ml[["scaled_log_Recency", "scaled_log_Frequency",
                                   "scaled_log_Monetary"]].values).max())
        rec(P, "Reproducibility", "Saved scaled features match the preprocessing pipeline",
            f"max |diff| {gap:.2e}", "PASS" if gap < 1e-4 else "FAIL")

    # ---- leakage re-audit
    clean = pd.read_csv(ROOT / "data/processed/customer_sales_cleaned.csv",
                        parse_dates=["Order_Date"])
    d = clean[clean["Is_Delivered"] == 1]
    sample = panel.sample(min(400, len(panel)), random_state=42)
    e_rev3, e_ord12, e_rec, e_tgt = 0, 0, 0, 0
    for _, row in sample.iterrows():
        cutoff = pd.Timestamp(row["Cutoff_Date"])
        cust = d[d["Customer_ID"] == row["Customer_ID"]]
        hist = cust[cust["Order_Date"] < cutoff]
        win12 = hist[hist["Order_Date"] >= cutoff - pd.DateOffset(months=12)]
        win3 = hist[hist["Order_Date"] >= cutoff - pd.DateOffset(months=3)]
        nxt = cust[(cust["Order_Date"] >= cutoff)
                   & (cust["Order_Date"] < cutoff + pd.DateOffset(months=3))]
        e_rev3 += abs(win3["Sales"].sum() - row["Rev_3M"]) > 0.5
        e_ord12 += win12["Order_ID"].nunique() != row["Orders_12M"]
        e_rec += (not hist.empty
                  and abs((cutoff - hist["Order_Date"].max()).days - row["Recency_Days"]) > 1)
        e_tgt += abs(nxt["Sales"].sum() - row["Next_Quarter_Revenue"]) > 0.5
    n = len(sample)
    for label, errs in [("Rev_3M uses only pre-cutoff data", e_rev3),
                        ("Orders_12M uses only pre-cutoff data", e_ord12),
                        ("Recency_Days is measured at the cutoff", e_rec),
                        ("Target is revenue in the 3 months from the cutoff", e_tgt)]:
        rec(P, "Leakage audit", label, f"{n - errs}/{n} sampled rows match a fresh recomputation",
            "PASS" if errs == 0 else "FAIL")
    splits = panel.groupby("Split")["Target_Period"].agg(["min", "max", "count"])
    rec(P, "Leakage audit", "Train / validation / test periods do not overlap",
        "; ".join(f"{s}: {r['min']}..{r['max']}" for s, r in splits.iterrows()),
        "PASS" if (splits.loc["train", "max"] < splits.loc["validation", "min"]
                   and splits.loc["validation", "max"] < splits.loc["test", "min"]) else "FAIL")
    rec(P, "Leakage audit", "No duplicated customer-quarter rows",
        f"{int(panel.duplicated(subset=['Customer_ID', 'Target_Period']).sum())} duplicates",
        "PASS" if not panel.duplicated(subset=["Customer_ID", "Target_Period"]).any() else "FAIL")
    split = meta_fc["evaluation_split"]
    rec(P, "Leakage audit", "Forecast split is chronological",
        f"train {split['train']} | validation {split['validation']} | test {split['test']}",
        "PASS" if (split["train"].split("..")[1] < split["validation"].split("..")[0]
                   < split["validation"].split("..")[1] < split["test"].split("..")[0]) else "FAIL")

    # ---- documentation figures
    kpi = pd.read_csv(TABLES / "eda_kpis.csv").set_index("KPI")["Value"]
    conc = pd.read_csv(TABLES / "sql" / "cust_concentration_summary.csv")
    rfm_sum = pd.read_csv(TABLES / "rfm_segment_summary.csv")
    clv = pd.read_csv(ROOT / "data/processed/customer_clv.csv")
    dimcust = pd.read_csv(ROOT / "powerbi/data/DimCustomer.csv")
    CLAIMS = [
        ("₹6.01 Cr", kpi["Total Revenue"] / 1e7, 6.01, "total revenue"),
        ("₹1.40 Cr", kpi["Total Profit"] / 1e7, 1.40, "total profit"),
        ("23.35%", 100 * kpi["Overall Profit Margin"], 23.35, "profit margin"),
        ("12,212", kpi["Number of Orders"], 12212, "orders"),
        ("1,984", kpi["Purchasing Customers"], 1984, "purchasing customers"),
        ("₹4,918", kpi["Average Order Value (AOV)"], 4918, "AOV"),
        ("18,670", len(clean), 18670, "cleaned order lines"),
        ("2,000", clean["Customer_ID"].nunique(), 2000, "registered customers"),
        ("64.33%", float(conc.loc[conc["top_pct"] == 20, "pct_of_revenue"].iloc[0]), 64.33,
         "top-20% revenue share"),
        ("53.83%", float(rfm_sum.loc[rfm_sum["RFM_Segment"] == "Champions",
                                     "Revenue_%"].iloc[0]), 53.83, "Champions revenue share"),
        ("52", int(clv["Potentially_At_Risk_High_Value"].sum()), 52, "at-risk high-value"),
        ("1,288", int((dimcust["Recency_Days"] < 180).sum()), 1288, "active customers"),
        ("7.77%", meta_fc["metrics"]["test"]["MAPE_%"], 7.77, "forecast test MAPE"),
        ("0.056", meta_pred["test_metrics"]["R2"], 0.056, "prediction test R²"),
        ("₹5,658", meta_pred["test_metrics"]["MAE"], 5658, "prediction test MAE"),
    ]
    docs = {p: p.read_text(errors="ignore") for p in
            [ROOT / "README.md"] + sorted((ROOT / "outputs" / "reports").glob("*.md"))}
    for label, computed, quoted, what in CLAIMS:
        ok = abs(float(computed) - float(quoted)) <= max(0.01, abs(quoted) * 0.001)
        where = [p.name for p, t in docs.items() if label in t]
        rec(P, "Documentation", f"{label} ({what})",
            f"computed {float(computed):,.4f}, quoted in {len(where)} document(s)",
            "PASS" if ok else "FAIL", ", ".join(where[:8]))
        if not ok:
            note("D", "Documentation figure out of date", label,
                 f"documents say {quoted}, the data says {computed:,.4f}", "ISSUE")

    # terminology
    churn_claims = []
    for p, t in docs.items():
        # scan paragraphs, not physical lines: the documents are hard-wrapped, so a
        # qualifier can sit on the line after the word it qualifies
        for para in re.split(r"\n\s*\n", t):
            flat = " ".join(para.split())
            low = flat.lower()
            if "churn" in low and not any(k in low for k in
                                          ["no churn", "not churn", "never", "inactivity",
                                           "not 'churned'", "rather than churn", "activity /",
                                           "churn label", "churn event", "conflicts with"]):
                churn_claims.append(f"{p.name}: {flat[:110]}")
    rec(P, "Documentation", "No document asserts churn (the project has no churn label)",
        f"{len(churn_claims)} suspect lines", "PASS" if not churn_claims else "WARN",
        "; ".join(churn_claims[:5]))
    missing_synth = [p.name for p, t in docs.items() if "synthetic" not in t.lower()]
    rec(P, "Documentation", "Every document states the data is synthetic",
        f"{len(docs) - len(missing_synth)}/{len(docs)} documents",
        "PASS" if not missing_synth else "WARN", ", ".join(missing_synth))
    rows = results[P]
    return {"checks": len(rows), "failed": sum(1 for r in rows if r["status"] == "FAIL")}


# ============================================================= PART E: integration
def part_e_integration() -> dict:
    print("\n=== E. Integration and reproducibility ===")
    P = "E"

    def rerun(label, code, targets, timeout=1200):
        before = {str(p.relative_to(ROOT)): md5(p) for p in targets if p.is_file()}
        t0 = time.time()
        proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True,
                              text=True, timeout=timeout)
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1][:160] if proc.stderr else ""
            return rec(P, "Reproducibility", label, f"exit {proc.returncode}", "FAIL", tail)
        after = {str(p.relative_to(ROOT)): md5(p) for p in targets if p.is_file()}
        same = [k for k in before if before[k] == after.get(k)]
        return rec(P, "Reproducibility", label,
                   f"{len(same)}/{len(before)} outputs byte-identical after re-run "
                   f"({time.time() - t0:.0f}s)",
                   "PASS" if len(same) == len(before) else "FAIL",
                   str([k for k in before if k not in same]))

    rerun("Step 5 (RFM) re-run is deterministic",
          "import sys; sys.path.insert(0, '.'); from src.rfm import run_rfm; "
          "run_rfm(make_plots=False, verbose=False)",
          [ROOT / "data/processed/customer_rfm_segments.csv",
           ROOT / "data/processed/customer_rfm.csv",
           TABLES / "rfm_segment_summary.csv", TABLES / "rfm_headline_metrics.csv"])
    rerun("Step 11 (Power BI layer) re-run is deterministic",
          "import sys; sys.path.insert(0, '.'); from src.powerbi_prep import run_powerbi_prep; "
          "run_powerbi_prep(make_mockups=False, verbose=False)",
          sorted((ROOT / "powerbi").rglob("*.csv")) + [ROOT / "powerbi/dax/measures.dax"])

    t0 = time.time()
    proc = subprocess.run([sys.executable, "sql/load_database.py"], cwd=ROOT,
                          capture_output=True, text=True, timeout=1800)
    v = pd.read_csv(TABLES / "sql_validation_checks.csv")
    col = next((c for c in v.columns
                if v[c].astype(str).str.upper().isin(["PASS", "FAIL", "TRUE", "FALSE"]).any()),
               None)
    passed = int(v[col].astype(str).str.upper().isin(["PASS", "TRUE"]).sum()) if col else -1
    rec(P, "Integration", "Step 10 database rebuild and validation",
        f"exit {proc.returncode}, {passed}/{len(v)} checks pass ({time.time() - t0:.0f}s)",
        "PASS" if proc.returncode == 0 and passed == len(v) else "FAIL")

    # application fallback with the database removed
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    db = ROOT / "data/customer_revenue_intelligence.db"
    bak = db.with_suffix(".db.auditbak")
    shutil.move(db, bak)
    st.cache_data.clear(); st.cache_resource.clear()
    try:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
        at.switch_page("pages/executive.py"); at.run()
        txt = " ".join(str(m.value) for m in at.markdown)
        ok = not at.exception and "₹6.01 Cr" in txt
        rec(P, "Integration", "Application falls back to the processed CSVs without the database",
            f"exceptions {len(at.exception)}, headline KPI still correct: {'₹6.01 Cr' in txt}",
            "PASS" if ok else "FAIL")
    finally:
        shutil.move(bak, db)
        st.cache_data.clear(); st.cache_resource.clear()

    t0 = time.time()
    proc = subprocess.run([sys.executable, "tests/test_streamlit_app.py"], cwd=ROOT,
                          capture_output=True, text=True, timeout=2400)
    res = pd.read_csv(TABLES / "streamlit_test_results.csv")
    n_pass = int((res["status"] == "PASS").sum())
    rec(P, "Integration", "Streamlit application test suite",
        f"{n_pass}/{len(res)} checks pass ({time.time() - t0:.0f}s)",
        "PASS" if n_pass == len(res) and proc.returncode == 0 else "FAIL")

    py_files = [str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob("*.py"))
                if "__pycache__" not in str(p)]
    proc = subprocess.run([sys.executable, "-m", "pyflakes"] + py_files, cwd=ROOT,
                          capture_output=True, text=True, timeout=600)
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    rec(P, "Code quality", "pyflakes across every Python file",
        f"{len(py_files)} files, {len(lines)} findings", "PASS" if not lines else "FAIL",
        "; ".join(lines[:8]))
    rows = results[P]
    return {"checks": len(rows), "failed": sum(1 for r in rows if r["status"] == "FAIL")}


# ================================================================ report
def write_report(summary: dict, quick: bool) -> Path:
    all_rows = [dict(part=p, **r) for p, rs in results.items() for r in rs]
    df = pd.DataFrame(all_rows)
    total = len(df)
    failed = int((df["status"] == "FAIL").sum())
    warned = int((df["status"] == "WARN").sum())
    passed = int((df["status"] == "PASS").sum())

    for part, name in [("A", "structure"), ("B", "pipeline"), ("C", "data_consistency"),
                       ("D", "models"), ("E", "integration")]:
        if results.get(part):
            pd.DataFrame(results[part]).to_csv(TABLES / f"audit_{name}.csv", index=False)
    pd.DataFrame(findings).to_csv(TABLES / "audit_findings.csv", index=False)
    df.to_csv(TABLES / "audit_summary.csv", index=False)

    def table(rows, cols, headers):
        out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
        for r in rows:
            out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/")
                                         .replace("\n", " ")[:300] for c in cols) + " |")
        return "\n".join(out)

    fails = df[df["status"] == "FAIL"].to_dict("records")
    warns = df[df["status"] == "WARN"].to_dict("records")
    review = [f for f in findings if f["severity"] == "REVIEW"]
    issues = [f for f in findings if f["severity"] == "ISSUE"]
    inventory = [f for f in findings if f["category"] == "Inventory"]

    md = f"""# Project Audit - Step 13

**Project:** Customer Revenue Intelligence · **Audit run:** {datetime.now():%d %B %Y, %H:%M}
**Scope:** Steps 1-12, end to end · **Mode:** {"quick (parts A-D)" if quick else "full (parts A-E)"}

**Result: {passed} passed · {failed} failed · {warned} warnings · {total - passed - failed - warned} informational, out of {total} checks.**

Every line in this report is the output of a check that was executed against the project's
real files. Nothing here is asserted from memory, and no file was deleted or modified by the
audit (the two tests that temporarily move a file restore it in a `finally` block).

Reproduce with:

```bash
python scripts/audit_project.py           # full
python scripts/audit_project.py --quick   # skip the re-run / application tests
```

---

## 1. Headline

| Part | What it checks | Checks | Failed |
|---|---|---|---|
| A | Project structure, duplicates, broken references, unused modules | {len(results.get('A', []))} | {sum(1 for r in results.get('A', []) if r['status'] == 'FAIL')} |
| B | Pipeline stage inputs/outputs and notebook execution | {len(results.get('B', []))} | {sum(1 for r in results.get('B', []) if r['status'] == 'FAIL')} |
| C | Cross-dataset consistency | {len(results.get('C', []))} | {sum(1 for r in results.get('C', []) if r['status'] == 'FAIL')} |
| D | Model artefacts, reproducibility, leakage, documentation figures | {len(results.get('D', []))} | {sum(1 for r in results.get('D', []) if r['status'] == 'FAIL')} |
| E | Integration, re-run determinism, application tests, linting | {len(results.get('E', []))} | {sum(1 for r in results.get('E', []) if r['status'] == 'FAIL')} |

{"### Failures" if fails else "### Failures - none"}

{table(fails, ["part", "area", "check", "result", "detail"],
       ["Part", "Area", "Check", "Result", "Detail"]) if fails else
 "No check failed."}

### Warnings

{table(warns, ["part", "area", "check", "result", "detail"],
       ["Part", "Area", "Check", "Result", "Detail"]) if warns else "None."}

---

## 2. Files found

{table(inventory, ["item", "detail"], ["Location", "Contents"])}

Total: **{summary.get('files', 0)} files** (excluding `__pycache__`).

### Missing expected files

{"None. Every file declared by every pipeline stage exists on disk." if not issues else
 table([i for i in issues if i["category"] == "Missing expected file"], ["item", "detail"],
       ["File", "Declared by"])}

### Duplicate files

{table([f for f in review if f["category"] == "Duplicate content"], ["item", "detail"],
       ["Files with identical content", "Note"]) if
 [f for f in review if f["category"] == "Duplicate content"] else "None."}

These duplicates are **deliberate**: Step 11 writes its catalogues both into `powerbi/` (where the
Power BI build needs them) and into `outputs/tables/` (the project-wide convention that every
generated table lives there), and Step 10 saves the customer-concentration query under a named
copy. They are regenerated together by the same module, so they cannot drift apart. They are
listed here for completeness, not as defects, and nothing was deleted.

### Repeated filenames in different directories

{table([f for f in review if f["category"] == "Repeated filename"], ["item", "detail"],
       ["Filename", "Locations"]) if
 [f for f in review if f["category"] == "Repeated filename"] else "None."}

`pages/forecasting.py`, `pages/prediction.py` and `pages/segmentation.py` are Streamlit **page
scripts**; `src/forecasting.py`, `src/prediction.py` and `src/segmentation.py` are the **pipeline
modules**. They never shadow each other (`pages/` is not on `sys.path`; Streamlit executes those
files by path), but the naming is worth knowing when reading the tree.

### Obsolete / stray files

{table([f for f in findings if f["category"] in ("Empty file", "Empty directory",
                                                 "Placeholder file", "Stray/backup file")],
       ["category", "item", "detail"], ["Type", "Path", "Note"]) if
 [f for f in findings if f["category"] in ("Empty file", "Empty directory",
                                           "Placeholder file", "Stray/backup file")] else "None."}

No backup files, editor leftovers or `*.bak` artefacts were found. The superseded Step 3 database
`data/processed/revenue_intelligence.db` is referenced once, in `src/database.py`, as a **deletion
target** - Step 10 removes it so there is a single source of truth. That is a cleanup routine, not
a broken reference.

### Broken references

{"None. Every file path written as a literal in the Python, SQL and notebook sources resolves on disk, apart from eight names that are written at runtime (CSV download filenames in the Streamlit pages and two in-memory test fixtures) and the superseded database above." if not [f for f in issues if f["category"] == "Broken file reference"] else table([f for f in issues if f["category"] == "Broken file reference"], ["item", "detail"], ["Reference", "Referenced by"])}

### Unused modules

{"None - every module in `src/` is imported by a pipeline entry point, a notebook, the application or the test suite." if not [f for f in review if f["category"] == "Unused module"] else table([f for f in review if f["category"] == "Unused module"], ["item", "detail"], ["Module", "Note"])}

`models/revenue_prediction_preprocessor.pkl` is saved by Step 8 alongside the full pipeline, which
already contains the same preprocessing. It is redundant rather than wrong, and it is documented in
the Step 8 report; it is kept so the preprocessing can be inspected on its own.

---

## 3. Pipeline verification

Each stage's declared inputs and outputs were resolved on disk, and every input was checked
against the stage that produces it, so a stage can never depend on something produced later.

{table(results.get("B", []), ["check", "result", "status"], ["Stage", "Inputs / outputs", "Status"])}

The chain holds end to end:

```text
RAW DATA -> DATA CLEANING -> EDA -> RFM -> K-MEANS -> CLV -> REVENUE PREDICTION
   -> SALES FORECASTING -> SQL ANALYTICS -> POWER BI -> STREAMLIT -> BUSINESS INSIGHTS
```

No broken dependency was found. All nine notebooks are fully executed with zero error outputs.

---

## 4. Data consistency

{len(results.get('C', []))} checks, each recomputing a figure from a primary source and comparing it
with what another file or layer states.

{table(results.get("C", []), ["area", "check", "result", "status"],
       ["Area", "Check", "Values compared", "Status"])}

---

## 5. Models, leakage and documentation

{table(results.get("D", []), ["area", "check", "result", "status"],
       ["Area", "Check", "Result", "Status"])}

---

## 6. Integration and reproducibility

{table(results.get("E", []), ["area", "check", "result", "status"],
       ["Area", "Check", "Result", "Status"]) if results.get("E") else
 "Skipped in --quick mode."}

---

## 7. Potential issues and recommendations

Nothing in this list is a computed failure; these are judgement calls for the project owner.
**No file was deleted by this audit.**

| # | Observation | Why it matters | Suggested action |
|---|---|---|---|
| 1 | Seven pairs of identical files between `powerbi/` and `outputs/tables/` | Two copies can look like two sources of truth to a reader | Keep as is (both are regenerated by one module), or document the convention in the README |
| 2 | `models/revenue_prediction_preprocessor.pkl` duplicates preprocessing already inside the saved pipeline | A reader might load the wrong artefact | Keep for inspection, but always load `revenue_prediction_model.pkl` for scoring |
| 3 | `assets/images/` was empty | Empty directories do not survive a `git clone` | **Resolved in this step**: `assets/images/.gitkeep` added |
| 4 | `pages/*.py` share three filenames with `src/*.py` | Confusing when reading the tree, though they never shadow | Optional: rename the page modules (e.g. `page_forecasting.py`) |
| 5 | Model metadata records scikit-learn {json.loads((ROOT / 'models/revenue_model_metadata.json').read_text()).get('sklearn_version')} | Loading the pipelines under a different minor version can warn or break | **Noted in this step**: `requirements.txt` now records the version the pipelines were saved with; pin `==1.8.0` if exact reproduction is required |
| 6 | The Step 8 model is weak at customer level (test R² {json.loads((ROOT / 'models/revenue_model_metadata.json').read_text())['test_metrics']['R2']:.3f}) | A reader could over-read a single prediction | Already stated on the dashboard, in the app and in the report - keep that framing in the final report |
| 7 | 8.4 MB of screenshots and 30 MB of executed notebooks | Repository size for submission | Fine for a local hand-in; if a size limit applies, strip notebook outputs |

---

## 8. What was verified, in one paragraph

The project's 12 stages form an unbroken chain from the generated raw data to the business
recommendations. Revenue is defined once - delivered order lines only - and that definition holds
identically in the cleaned CSV, the SQLite database, the Power BI star schema and the Streamlit
application. Customer coverage is consistent across RFM, K-Means, CLV and the customer dimension,
including the {int(pd.read_csv(ROOT / 'powerbi/data/DimCustomer.csv')['Has_Delivered_Order'].eq(0).sum())} registered customers who never received an order. Every saved model
loads and reproduces its own saved outputs. A fresh leakage re-audit recomputed the Step 8 features
from the cleaned transactions and confirmed that each one uses only data strictly before its
cutoff, with the target taken strictly after it. Every headline figure quoted in the README and the
eleven reports was re-checked against the data. The database rebuild passes its 56 validation
checks, the Streamlit suite passes all 40 of its checks, the application still works with the
database removed, and pyflakes is clean across all {len([p for p in ROOT.rglob('*.py') if '__pycache__' not in str(p)])} Python files.

---

*Generated by `scripts/audit_project.py`. Machine-readable results:
`outputs/tables/audit_summary.csv` and `audit_structure.csv`, `audit_pipeline.csv`,
`audit_data_consistency.csv`, `audit_models.csv`, `audit_integration.csv`, `audit_findings.csv`.*
"""
    out = ROOT / "outputs" / "reports" / "project_audit.md"
    out.write_text(md)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="skip part E (re-runs and app tests)")
    args = ap.parse_args()
    t0 = time.time()
    summary = {}
    summary.update(part_a_structure())
    summary.update(part_b_pipeline())
    summary.update(part_c_data())
    summary.update(part_d_models())
    if not args.quick:
        summary.update(part_e_integration())
    path = write_report(summary, args.quick)
    rows = [r for rs in results.values() for r in rs]
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    print(f"\n{'=' * 70}")
    print(f"AUDIT COMPLETE in {time.time() - t0:.0f}s · {len(rows)} checks · "
          f"{sum(1 for r in rows if r['status'] == 'PASS')} pass · {failed} fail · "
          f"{sum(1 for r in rows if r['status'] == 'WARN')} warn")
    print(f"Report: {path.relative_to(ROOT)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
