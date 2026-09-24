"""STEP 14 - collects every number the internship report quotes, from the project's own outputs.

The report builder (scripts/build_report.py) reads only this dictionary, so no figure in the
report can be typed in by hand. Run it directly to print the collected facts:

    python scripts/report_facts.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"


def _csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError):
        return None


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def collect() -> dict:
    f: dict = {}
    clean = pd.read_csv(PROC / "customer_sales_cleaned.csv", parse_dates=["Order_Date"])
    raw = pd.read_csv(ROOT / "data/raw/customer_sales_raw.csv")
    d = clean[clean["Is_Delivered"] == 1]
    kpi = pd.read_csv(TABLES / "eda_kpis.csv").set_index("KPI")["Value"]

    # ---------------------------------------------------------------- dataset
    f["dataset"] = {
        "raw_rows": len(raw), "raw_cols": raw.shape[1],
        "clean_rows": len(clean), "clean_cols": clean.shape[1],
        "duplicates_removed": int(len(raw) - len(clean)),
        "customers_registered": int(clean["Customer_ID"].nunique()),
        "customers_purchasing": int(d["Customer_ID"].nunique()),
        "products": int(clean["Product_ID"].nunique()),
        "categories": int(clean["Category"].nunique()),
        "sub_categories": int(clean["Sub_Category"].nunique()),
        "cities": int(clean["City"].nunique()),
        "states": int(clean["State"].nunique()),
        "regions": int(clean["Region"].nunique()),
        "region_names": sorted(clean["Region"].dropna().unique().tolist()),
        "category_names": sorted(clean["Category"].dropna().unique().tolist()),
        "payment_methods": sorted(clean["Payment_Method"].dropna().unique().tolist()),
        "start": f"{clean['Order_Date'].min():%d %B %Y}",
        "end": f"{clean['Order_Date'].max():%d %B %Y}",
        "months": int(d["Order_Date"].dt.to_period("M").nunique()),
        "orders_all": int(clean["Order_ID"].nunique()),
        "seed": 42,
        "statuses": clean["Order_Status"].value_counts().to_dict(),
    }

    # -------------------------------------------------------------------- KPIs
    f["kpi"] = {
        "revenue": float(kpi["Total Revenue"]), "profit": float(kpi["Total Profit"]),
        "cost": float(kpi["Total Cost"]), "margin": float(kpi["Overall Profit Margin"]),
        "orders": int(kpi["Number of Orders"]), "customers": int(kpi["Purchasing Customers"]),
        "units": int(kpi["Total Quantity Sold"]), "aov": float(kpi["Average Order Value (AOV)"]),
        "revenue_per_customer": float(kpi["Average Revenue per Customer"]),
        "profit_per_order": float(kpi["Average Profit per Order"]),
        "qty_per_order": float(kpi["Average Quantity per Order"]),
        "orders_per_customer": float(kpi["Average Orders per Customer"]),
        "booked": float(kpi["Gross Booked Sales (all statuses)"]),
        "lost": float(kpi["Revenue Lost to Cancellations & Returns"]),
        "lost_share": float(kpi["Share of Booked Sales Not Realised"]),
    }

    # ------------------------------------------------------------- data quality
    dq = _csv(ROOT / "outputs/data_quality_report.csv")
    rules = _csv(TABLES / "cleaning_rule_checks_before_after.csv")
    acc = _csv(TABLES / "cleaning_accuracy_vs_ground_truth.csv")
    f["quality"] = {
        "report": dq.to_dict("records") if dq is not None else [],
        "rules": rules.to_dict("records") if rules is not None else [],
        "accuracy": acc.to_dict("records") if acc is not None else [],
        "missing_before": int(rules.loc[rules["Validation_Rule"] == "missing_value",
                                        "Rows_Before"].iloc[0]) if rules is not None else None,
        "rules_failing_after": int(rules["Rows_After"].sum()) if rules is not None else None,
    }

    # -------------------------------------------------------------------- EDA
    yr = _csv(TABLES / "sql/rev_by_year.csv")
    cat = _csv(TABLES / "sql/prod_category_performance.csv")
    reg = _csv(TABLES / "sql/reg_performance.csv")
    conc = _csv(TABLES / "sql/cust_concentration_summary.csv")
    freq = _csv(TABLES / "sql/cust_frequency_distribution.csv")
    moy = _csv(TABLES / "sql/time_month_of_year.csv")
    best = _csv(TABLES / "sql/time_best_worst_months.csv")
    bands = _csv(TABLES / "sql/prod_discount_bands.csv")
    bq08 = _csv(TABLES / "sql/BQ08.csv")
    bq12 = _csv(TABLES / "sql/BQ12.csv")
    bq13 = _csv(TABLES / "sql/BQ13.csv")
    bq14 = _csv(TABLES / "sql/BQ14.csv")
    bq15 = _csv(TABLES / "sql/BQ15.csv")
    bq16 = _csv(TABLES / "sql/BQ16.csv")
    bq17 = _csv(TABLES / "sql/BQ17.csv")
    inv = _csv(TABLES / "sql/prod_investigate.csv")
    f["eda"] = {
        "by_year": yr.to_dict("records") if yr is not None else [],
        "by_category": cat.to_dict("records") if cat is not None else [],
        "by_region": reg.to_dict("records") if reg is not None else [],
        "concentration": conc.to_dict("records") if conc is not None else [],
        "frequency_bands": freq.to_dict("records") if freq is not None else [],
        "month_of_year": moy.to_dict("records") if moy is not None else [],
        "best_worst_months": best.to_dict("records") if best is not None else [],
        "discount_bands": bands.to_dict("records") if bands is not None else [],
        "repeat": bq12.to_dict("records") if bq12 is not None else [],
        "payment": bq13.to_dict("records") if bq13 is not None else [],
        "lost_by_category": bq14.to_dict("records") if bq14 is not None else [],
        "retention": bq15.to_dict("records") if bq15 is not None else [],
        "region_category_gap": int(bq16["flag_below_2pp"].sum()) if bq16 is not None
                               and "flag_below_2pp" in bq16.columns else None,
        "region_category_pairs": len(bq16) if bq16 is not None else None,
        "interpurchase": bq17.to_dict("records")[0] if bq17 is not None and len(bq17) else {},
        "products_flagged": len(inv) if inv is not None else None,
        "flagged_products": inv.to_dict("records") if inv is not None else [],
        "zero_discount_best_in": int((bq08.sort_values(["category", "profit_margin_pct"],
                                                       ascending=[True, False])
                                      .groupby("category").head(1)["discount_band"] == "0%").sum())
                                 if bq08 is not None else None,
        "categories_tested": int(bq08["category"].nunique()) if bq08 is not None else None,
        "monthly_min": float(d.groupby(d["Order_Date"].dt.strftime("%Y-%m"))["Sales"].sum().min()),
        "monthly_max": float(d.groupby(d["Order_Date"].dt.strftime("%Y-%m"))["Sales"].sum().max()),
    }

    # -------------------------------------------------------------------- RFM
    rfm_meta = _json(PROC / "customer_rfm_metadata.json")
    rfm_sum = _csv(TABLES / "rfm_segment_summary.csv")
    rfm_head = _csv(TABLES / "rfm_headline_metrics.csv")
    rfm_rules = _csv(TABLES / "rfm_segment_rules.csv")
    groups = _csv(TABLES / "rfm_value_activity_groups.csv")
    rfm = pd.read_csv(PROC / "customer_rfm_segments.csv")
    f["rfm"] = {
        "reference_date": rfm_meta.get("reference_date"),
        "customers_scored": len(rfm),
        "segments": int(rfm["RFM_Segment"].nunique()),
        "summary": rfm_sum.to_dict("records") if rfm_sum is not None else [],
        "headline": rfm_head.to_dict("records") if rfm_head is not None else [],
        "rules": rfm_rules.to_dict("records") if rfm_rules is not None else [],
        "groups": groups.to_dict("records") if groups is not None else [],
        "median_recency": float(rfm["Recency"].median()),
        "median_frequency": float(rfm["Frequency"].median()),
        "median_monetary": float(rfm["Monetary"].median()),
        "scoring": rfm_meta.get("scoring") or rfm_meta.get("method"),
        "metadata": rfm_meta,
    }

    # ---------------------------------------------------------------- K-Means
    seg_meta = _json(MODELS / "segmentation_model_metadata.json")
    ml_sum = _csv(TABLES / "ml_cluster_summary.csv")
    k_eval = _csv(TABLES / "ml_k_evaluation.csv")
    sil = _csv(TABLES / "ml_silhouette_by_cluster.csv")
    pca = _csv(TABLES / "ml_pca_summary.csv")
    agree = _csv(TABLES / "rfm_vs_ml_agreement.csv")
    ml = pd.read_csv(PROC / "customer_ml_segments.csv")
    f["kmeans"] = {
        "k": seg_meta.get("selected_k"), "metadata": seg_meta,
        "features": seg_meta.get("feature_order"),
        "preprocessing": seg_meta.get("preprocessing"),
        "selection_rules": seg_meta.get("selection_rules"),
        "summary": ml_sum.to_dict("records") if ml_sum is not None else [],
        "k_evaluation": k_eval.to_dict("records") if k_eval is not None else [],
        "silhouette_by_cluster": sil.to_dict("records") if sil is not None else [],
        "pca": pca.to_dict("records") if pca is not None else [],
        "agreement": agree.to_dict("records") if agree is not None else [],
        "overall_silhouette": float(ml["Silhouette"].mean()) if "Silhouette" in ml.columns else None,
    }

    # -------------------------------------------------------------------- CLV
    clv_meta = _json(MODELS / "clv_model_metadata.json")
    clv = pd.read_csv(PROC / "customer_clv.csv")
    clv_seg = _csv(TABLES / "clv_by_rfm_segment.csv")
    clv_clu = _csv(TABLES / "clv_by_ml_cluster.csv")
    clv_cmp = _csv(TABLES / "clv_model_comparison.csv")
    clv_imp = _csv(TABLES / "clv_feature_importance.csv")
    clv_conc = _csv(TABLES / "clv_value_concentration.csv")
    bgnbd = _csv(TABLES / "clv_bgnbd_evaluation.csv")
    f["clv"] = {
        "metadata": clv_meta,
        "historical_revenue_total": float(clv["Historical_Revenue_CLV"].sum()),
        "historical_profit_total": float(clv["Historical_Profit_CLV"].sum()),
        "mean_historical_profit": float(clv["Historical_Profit_CLV"].mean()),
        "median_historical_profit": float(clv["Historical_Profit_CLV"].median()),
        "estimated_12m_total": float(clv["Estimated_12M_Future_Profit"].sum()),
        "mean_estimated_12m": float(clv["Estimated_12M_Future_Profit"].mean()),
        "illustrative_3y_total": float(clv["Illustrative_3Y_Value"].sum()),
        "at_risk": int(clv["Potentially_At_Risk_High_Value"].sum()),
        "at_risk_revenue": float(clv.loc[clv["Potentially_At_Risk_High_Value"] == 1,
                                         "Historical_Revenue_CLV"].sum()),
        "high_value": int(clv["High_Historical_Value"].sum()),
        "by_segment": clv_seg.to_dict("records") if clv_seg is not None else [],
        "by_cluster": clv_clu.to_dict("records") if clv_clu is not None else [],
        "model_comparison": clv_cmp.to_dict("records") if clv_cmp is not None else [],
        "feature_importance": clv_imp.to_dict("records") if clv_imp is not None else [],
        "concentration": clv_conc.to_dict("records") if clv_conc is not None else [],
        "bgnbd": bgnbd.to_dict("records") if bgnbd is not None else [],
        "estimate_methods": clv["Estimate_Method"].value_counts().to_dict(),
    }

    # ------------------------------------------------------------- prediction
    pmeta = _json(MODELS / "revenue_model_metadata.json")
    pcomp = _csv(TABLES / "revenue_model_comparison.csv")
    pimp = _csv(TABLES / "revenue_feature_importance.csv")
    pq = _csv(TABLES / "revenue_quarterly_totals.csv")
    perr_seg = _csv(TABLES / "revenue_prediction_by_rfm.csv")
    psplit = _csv(TABLES / "revenue_split_summary.csv")
    pfeat = _csv(TABLES / "revenue_feature_selection.csv")
    preds = pd.read_csv(TABLES / "revenue_predictions.csv")
    panel = pd.read_csv(PROC / "revenue_modeling_dataset.csv")
    f["prediction"] = {
        "metadata": pmeta, "model": pmeta.get("model_type"),
        "target": pmeta.get("target"), "unit": pmeta.get("prediction_unit"),
        "selection_rule": pmeta.get("selection_rule"),
        "train_period": pmeta.get("training_period"),
        "validation_period": pmeta.get("validation_period"),
        "test_period": pmeta.get("test_period"), "final_fit": pmeta.get("final_fit"),
        "n_features": len(pmeta.get("numeric_features", []))
                      + len(pmeta.get("categorical_features", [])),
        "numeric_features": pmeta.get("numeric_features", []),
        "categorical_features": pmeta.get("categorical_features", []),
        "test_metrics": pmeta.get("test_metrics", {}),
        "validation_metrics": pmeta.get("validation_metrics", {}),
        "comparison": pcomp.to_dict("records") if pcomp is not None else [],
        "importance": pimp.to_dict("records") if pimp is not None else [],
        "quarterly": pq.to_dict("records") if pq is not None else [],
        "by_segment": perr_seg.to_dict("records") if perr_seg is not None else [],
        "splits": psplit.to_dict("records") if psplit is not None else [],
        "feature_selection": pfeat.to_dict("records") if pfeat is not None else [],
        "panel_rows": len(panel), "test_rows": len(preds),
        "train_rows": int((panel["Split"] == "train").sum()),
        "val_rows": int((panel["Split"] == "validation").sum()),
        "zero_actual_share": float((preds["Actual_Revenue"] == 0).mean()),
    }

    # -------------------------------------------------------------- forecasting
    fmeta = _json(MODELS / "forecasting_metadata.json")
    fcomp = _csv(TABLES / "forecast_model_comparison.csv")
    fback = _csv(TABLES / "forecast_backtest_summary.csv")
    ffut = _csv(TABLES / "forecast_future.csv")
    fadf = _csv(TABLES / "forecast_adf_tests.csv")
    fyear = _csv(TABLES / "forecast_yearly_summary.csv")
    fsel = _csv(TABLES / "forecast_model_selection.csv")
    monthly = pd.read_csv(PROC / "monthly_sales_timeseries.csv")
    fcast = pd.read_csv(PROC / "revenue_forecast.csv")
    tcol = "Type" if "Type" in fcast.columns else "Record_Type"
    fut = fcast[fcast[tcol].astype(str).str.startswith("Future")]
    fcol = "Forecast" if "Forecast" in fcast.columns else "Forecast_Revenue"
    f["forecast"] = {
        "metadata": fmeta, "model": fmeta.get("model_type"),
        "horizon": fmeta.get("forecast_horizon_months"),
        "months": fmeta.get("forecast_months", []),
        "split": fmeta.get("evaluation_split", {}),
        "selection_rule": fmeta.get("selection_rule"),
        "final_fit": fmeta.get("training_period_final_fit"),
        "metrics": fmeta.get("metrics", {}),
        "parameters": fmeta.get("model_parameters", {}),
        "comparison": fcomp.to_dict("records") if fcomp is not None else [],
        "backtest": fback.to_dict("records") if fback is not None else [],
        "future": ffut.to_dict("records") if ffut is not None else [],
        "adf": fadf.to_dict("records") if fadf is not None else [],
        "yearly": fyear.to_dict("records") if fyear is not None else [],
        "selection": fsel.to_dict("records") if fsel is not None else [],
        "series_months": len(monthly),
        "future_total": float(fut[fcol].sum()),
        "future_lower80": float(fut["Lower_80"].sum()),
        "future_upper80": float(fut["Upper_80"].sum()),
        "prev_6m_actual": float(monthly.tail(6)["Revenue"].sum()),
        "future_rows": fut[[c for c in ("Month", "Year_Month") if c in fut.columns][0:1]
                           + [fcol, "Lower_80", "Upper_80", "Lower_95", "Upper_95"]]
                       .to_dict("records"),
    }

    # -------------------------------------------------------------------- SQL
    cat_sql = _csv(TABLES / "sql_table_catalog.csv")
    checks = _csv(TABLES / "sql_validation_checks.csv")
    qcat = _csv(TABLES / "sql_query_catalog.csv")
    cover = _csv(TABLES / "sql_technique_coverage.csv")
    findings = _csv(TABLES / "sql_key_findings.csv")
    qc = _csv(TABLES / "sql_quality_checklist.csv")
    con = sqlite3.connect(ROOT / "data/customer_revenue_intelligence.db")
    tables = pd.read_sql_query("SELECT name, type FROM sqlite_master "
                               "WHERE type IN ('table','view') ORDER BY type, name", con)
    con.close()
    f["sql"] = {
        "tables": int((tables["type"] == "table").sum()),
        "views": int((tables["type"] == "view").sum() - 8),   # 8 pbi_* views are Step 11
        "pbi_views": 8,
        "table_catalog": cat_sql.to_dict("records") if cat_sql is not None else [],
        "validation_checks": len(checks) if checks is not None else None,
        "validation_passed": int(checks.iloc[:, -1].astype(str).str.upper()
                                 .isin(["PASS", "TRUE"]).sum()) if checks is not None else None,
        "queries": len(qcat) if qcat is not None else None,
        "analysis_queries": int((qcat["File"] == "analysis_queries.sql").sum())
                            if qcat is not None and "File" in qcat.columns else None,
        "business_queries": int((qcat["File"] == "business_queries.sql").sum())
                            if qcat is not None and "File" in qcat.columns else None,
        "techniques": cover.to_dict("records") if cover is not None else [],
        "key_findings": findings.to_dict("records") if findings is not None else [],
        "quality_checks": len(qc) if qc is not None else None,
    }

    # --------------------------------------------------------------- Power BI
    pbi_cat = _csv(TABLES / "powerbi_table_catalog.csv")
    pbi_rel = _csv(TABLES / "powerbi_relationships.csv")
    pbi_meas = _csv(TABLES / "powerbi_measure_catalog.csv")
    pbi_val = _csv(TABLES / "powerbi_measure_validation.csv")
    pbi_cons = _csv(TABLES / "powerbi_cross_step_consistency.csv")
    pbi_check = _csv(TABLES / "powerbi_validation_checklist.csv")
    recs = _csv(ROOT / "powerbi/data/Recommendations.csv")
    f["powerbi"] = {
        "tables": len(pbi_cat) if pbi_cat is not None else None,
        "catalog": pbi_cat.to_dict("records") if pbi_cat is not None else [],
        "relationships": len(pbi_rel) if pbi_rel is not None else None,
        "relationship_rows": pbi_rel.to_dict("records") if pbi_rel is not None else [],
        "measures": len(pbi_meas) if pbi_meas is not None else None,
        "folders": int(pbi_meas["Display_Folder"].nunique()) if pbi_meas is not None else None,
        "measure_rows": pbi_meas.to_dict("records") if pbi_meas is not None else [],
        "validation_rows": int(pbi_val["SQL_Value"].notna().sum()) if pbi_val is not None else None,
        "validation_matched": int((pbi_val["Reconciled"] == "Match").sum())
                              if pbi_val is not None else None,
        "consistency_total": len(pbi_cons) if pbi_cons is not None else None,
        "consistency_passed": int((pbi_cons["Status"] == "PASS").sum())
                              if pbi_cons is not None else None,
        "checklist": pbi_check.to_dict("records") if pbi_check is not None else [],
        "recommendations": len(recs) if recs is not None else None,
        "recommendation_rows": recs.to_dict("records") if recs is not None else [],
    }

    # -------------------------------------------------------------- Streamlit
    st_res = _csv(TABLES / "streamlit_test_results.csv")
    st_time = _csv(TABLES / "streamlit_page_load_times.csv")
    st_check = _csv(TABLES / "streamlit_quality_checklist.csv")
    f["streamlit"] = {
        "tests": len(st_res) if st_res is not None else None,
        "tests_passed": int((st_res["status"] == "PASS").sum()) if st_res is not None else None,
        "test_rows": st_res.to_dict("records") if st_res is not None else [],
        "page_times": st_time.to_dict("records") if st_time is not None else [],
        "checklist": st_check.to_dict("records") if st_check is not None else [],
        "pages": 12,
    }

    # ------------------------------------------------------------------ audit
    audit = _csv(TABLES / "audit_summary.csv")
    f["audit"] = {
        "total": len(audit) if audit is not None else None,
        "passed": int((audit["status"] == "PASS").sum()) if audit is not None else None,
        "failed": int((audit["status"] == "FAIL").sum()) if audit is not None else None,
        "by_part": audit.groupby("part").size().to_dict() if audit is not None else {},
    }

    # ------------------------------------------------------------- code stats
    py = [p for p in ROOT.rglob("*.py") if "__pycache__" not in str(p)]
    f["code"] = {
        "python_files": len(py),
        "python_lines": sum(len(p.read_text(errors="ignore").splitlines()) for p in py),
        "sql_files": len(list((ROOT / "sql").glob("*.sql"))),
        "notebooks": len(list((ROOT / "notebooks").glob("*.ipynb"))),
        "figures": len([p for p in (ROOT / "outputs" / "figures").rglob("*.png")]),
        "tables": len([p for p in (ROOT / "outputs" / "tables").rglob("*.csv")]),
        "reports": len(list((ROOT / "outputs" / "reports").glob("*.md"))),
    }
    return f


if __name__ == "__main__":
    facts = collect()
    out = ROOT / "outputs" / "tables" / "report_facts.json"
    out.write_text(json.dumps(facts, indent=1, default=str))
    print(f"Collected facts -> {out.relative_to(ROOT)}")
    for k, v in facts.items():
        n = len(v) if isinstance(v, (dict, list)) else 1
        print(f"  {k:12s} {n} entries")
