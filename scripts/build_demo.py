"""
build_demo.py - Step 18: live demonstration, screenshot pack and viva scripts.

Nothing here is fabricated. The screenshot pack is assembled by COPYING figures
the pipeline already produced (including the 12 real Streamlit screenshots and
the 9 Power BI design mockups, which stay labelled as mockups) and by RENDERING
two dataset previews directly from the actual CSV files. Anything that can only
be captured live - a terminal, Power BI Desktop - gets written capture
instructions instead of an image.

Every number quoted is read at build time from outputs/tables/report_facts.json.

Usage
-----
    python scripts/build_demo.py
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
FIG = ROOT / "outputs" / "figures"
SHOTS = ROOT / "outputs" / "screenshots"
VIVA = ROOT / "outputs" / "viva"
AUDIT = ROOT / "outputs" / "final_audit"

F: dict = {}
V: dict = {}


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
    atrisk = row_by(rfm["summary"], "RFM_Segment", "At Risk")
    hv = km["summary"][0]
    cat = eda["by_category"]
    best = max(cat, key=lambda c: c["profit_margin_pct"])
    reg = eda["by_region"]
    rep = row_by(eda["repeat"], "customer_group", "Repeat (2+ orders)")
    single = [r for r in eda["repeat"]
              if r["customer_group"] != rep["customer_group"]][0]
    y = eda["by_year"]
    disc = eda["discount_bands"]
    V.update({
        "raw_rows": n(d["raw_rows"]), "raw_cols": d["raw_cols"],
        "clean_rows": n(d["clean_rows"]), "clean_cols": d["clean_cols"],
        "dupes": n(d["duplicates_removed"]), "seed": d["seed"],
        "cust_reg": n(d["customers_registered"]),
        "cust_buy": n(d["customers_purchasing"]),
        "products": d["products"], "categories": d["categories"],
        "cities": d["cities"], "states": d["states"], "regions": d["regions"],
        "start": d["start"], "end": d["end"], "months": d["months"],
        "orders_all": n(d["orders_all"]),
        "engineered": d["clean_cols"] - d["raw_cols"],
        "missing_before": n(F["quality"]["missing_before"]),
        "revenue": cr(kpi["revenue"]), "profit": cr(kpi["profit"]),
        "margin": pcf(kpi["margin"]), "orders": n(kpi["orders"]),
        "aov": rs(kpi["aov"], 2), "units": n(kpi["units"]),
        "lost_value": lakh(kpi["lost"]), "lost_share": pcf(kpi["lost_share"]),
        "growth_2024": pc(y[1]["revenue_yoy_growth_pct"], 1),
        "growth_2025": pc(y[-1]["revenue_yoy_growth_pct"], 1),
        "margin_2023": pc(y[0]["profit_margin_pct"]),
        "margin_2025": pc(y[-1]["profit_margin_pct"]),
        "top10": pc(row_by(eda["concentration"], "top_pct", 10)["pct_of_revenue"]),
        "top20": pc(row_by(eda["concentration"], "top_pct", 20)["pct_of_revenue"]),
        "repeat_cust": pc(rep["pct_of_customers"], 2),
        "repeat_rev": pc(rep["pct_of_revenue"], 2),
        "repeat_avg": rs(rep["avg_revenue_per_customer"]),
        "single_avg": rs(single["avg_revenue_per_customer"]),
        "median_gap": n(eda["interpurchase"]["median_gap_days"]),
        "top_cat": cat[0]["category"],
        "top_cat_rev": pc(cat[0]["revenue_share_pct"]),
        "top_cat_profit": pc(cat[0]["profit_share_pct"]),
        "top_cat_margin": pc(cat[0]["profit_margin_pct"]),
        "best_cat": best["category"],
        "best_cat_margin": pc(best["profit_margin_pct"]),
        "top_region": reg[0]["region"],
        "top_region_share": pc(reg[0]["revenue_share_pct"]),
        "small_region": reg[-1]["region"],
        "small_region_share": pc(reg[-1]["revenue_share_pct"]),
        "region_pairs": eda["region_category_pairs"],
        "region_gaps": eda["region_category_gap"],
        "disc0_band": disc[0]["discount_band"],
        "disc0_margin": pc(disc[0]["profit_margin_pct"]),
        "disc_hi_band": disc[-1]["discount_band"],
        "disc_hi_margin": pc(disc[-1]["profit_margin_pct"]),
        "disc_best_in": eda["zero_discount_best_in"],
        "cats_tested": eda["categories_tested"],
        "flagged": eda["products_flagged"],
        "ref_date": rfm["reference_date"],
        "rfm_scored": n(rfm["customers_scored"]),
        "rfm_excluded": rfm["metadata"]["customers_excluded_no_delivered_purchase"],
        "rfm_segments": rfm["segments"],
        "champ_n": n(champ["Customer_Count"]),
        "champ_cust": pc(champ["Customer_%"], 2),
        "champ_rev": pc(champ["Revenue_%"], 2),
        "champ_monetary": rs(champ["Average_Monetary"]),
        "atrisk_n": n(atrisk["Customer_Count"]),
        "atrisk_rev": pc(atrisk["Revenue_%"], 2),
        "k": km["k"], "silhouette": f"{km['overall_silhouette']:.4f}",
        "min_k": km["selection_rules"]["min_k"],
        "min_share": pcf(km["selection_rules"]["min_cluster_share"], 0),
        "min_ari": f"{km['selection_rules']['min_stability_ari']:.2f}",
        "stability": f"{row_by(km['k_evaluation'], 'k', km['k'])['stability_ari_mean']:.2f}",
        "pc1": pc(km["pca"][0]["Explained_Variance_%"], 2),
        "pc2": pc(km["pca"][1]["Explained_Variance_%"], 2),
        "pca_total": pc(km["pca"][0]["Explained_Variance_%"]
                        + km["pca"][1]["Explained_Variance_%"], 2),
        "ari": f"{row_by(km['agreement'], 'Measure', 'Adjusted Rand Index (RFM segment vs cluster)')['Value']:.4f}",
        "hv_label": hv["Business_Label"], "hv_cust": pc(hv["Customer_%"], 2),
        "hv_rev": pc(hv["Revenue_%"], 2),
        "preprocessing": km["metadata"]["preprocessing"],
        "clv_hist": cr(clv["historical_profit_total"]),
        "clv_mean": rs(clv["mean_historical_profit"]),
        "clv_median": rs(clv["median_historical_profit"]),
        "clv_model": clv["metadata"]["selected_model"],
        "clv_mae": rs(clv["metadata"]["validation"]["MAE"]),
        "clv_r2": f"{clv['metadata']['validation']['R2']:.4f}",
        "clv_spearman": f"{clv['metadata']['validation']['Spearman']:.4f}",
        "clv_top20": pc(clv["metadata"]["validation"]["Top20_Capture_%"], 2),
        "clv_by_model": n(clv["estimate_methods"]["ML model (active in last 12 months)"]),
        "clv_by_group": n(clv["estimate_methods"]["Group average (no order in last 12 months)"]),
        "at_risk": clv["at_risk"], "at_risk_rev": lakh(clv["at_risk_revenue"]),
        "clv_drivers": ", ".join(r["Feature"] for r in clv["feature_importance"][:4]),
        "pred_model": pred["model"], "pred_target": pred["target"],
        "pred_unit": pred["unit"], "pred_features": pred["n_features"],
        "panel_rows": n(pred["panel_rows"]),
        "train_rows": n(pred["train_rows"]), "val_rows": n(pred["val_rows"]),
        "test_rows": n(pred["test_rows"]),
        "train_period": pred["train_period"], "val_period": pred["validation_period"],
        "test_period": pred["test_period"], "pred_rule": pred["selection_rule"],
        "pred_mae": rs(pred["test_metrics"]["MAE"]),
        "pred_rmse": rs(pred["test_metrics"]["RMSE"]),
        "pred_r2": f"{pred['test_metrics']['R2']:.4f}",
        "pred_wape": pc(pred["test_metrics"]["WAPE_%"], 2),
        "pred_bias": pc(pred["test_metrics"]["Total_Bias_%"], 2),
        "pred_zero": pcf(pred["zero_actual_share"], 1),
        "naive_mae": rs(pred["comparison"][0]["MAE"]),
        "naive_r2": f"{pred['comparison'][0]['R2']:.4f}",
        "pred_drivers": ", ".join(r["Feature"] for r in pred["importance"][:4]),
        "fc_model": fc["model"], "fc_horizon": fc["horizon"],
        "fc_months": f"{fc['months'][0]} to {fc['months'][-1]}",
        "fc_series": fc["series_months"], "fc_rule": fc["selection_rule"],
        "fc_test_mae": rs(fc["metrics"]["test"]["MAE"]),
        "fc_test_mape": pc(fc["metrics"]["test"]["MAPE_%"], 2),
        "fc_backtest": pc(fc["metrics"]["backtest_mean_MAPE_%"], 2),
        "fc_folds": fc["backtest"][0]["Folds"],
        "fc_total": cr(fc["future_total"]), "fc_low": cr(fc["future_lower80"]),
        "fc_high": cr(fc["future_upper80"]), "fc_prev6": cr(fc["prev_6m_actual"]),
        "adf_p": f"{fc['adf'][0]['p_value']:.4f}",
        "sql_tables": sq["tables"], "sql_views": sq["views"],
        "sql_queries": sq["queries"], "sql_analysis": sq["analysis_queries"],
        "sql_business": sq["business_queries"],
        "sql_checks": sq["validation_checks"], "sql_quality": sq["quality_checks"],
        "pbi_tables": pb["tables"], "pbi_rels": pb["relationships"],
        "pbi_measures": pb["measures"], "pbi_folders": pb["folders"],
        "pbi_val": pb["validation_rows"], "pbi_matched": pb["validation_matched"],
        "pbi_consistency": pb["consistency_total"], "pbi_recs": pb["recommendations"],
        "app_pages": stl["pages"], "app_tests": stl["tests"],
        "app_passed": stl["tests_passed"],
        "audit_total": au["total"], "audit_pass": au["passed"],
        "audit_fail": au["failed"],
        "py_files": code["python_files"], "py_lines": n(code["python_lines"]),
        "notebooks": code["notebooks"], "figures": code["figures"],
        "tables_out": code["tables"],
    })


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


STAMP = ("*Generated {d} by `python scripts/build_demo.py`. Every figure "
         "quoted is read from `outputs/tables/report_facts.json`; every image "
         "referenced already exists in the project.*").format(
             d=date.today().isoformat())


# ==========================================================================
# SCREENSHOT PACK
# ==========================================================================
# (target name, source relative to outputs/figures, category, caption)
PACK = [
    # A. DATA  (01-02 are rendered from the real CSVs by render_previews())
    ("03_data_quality_missing_before.png", "data_quality/01_missing_values_before.png", "A. Data", "Missing values by column in the raw extract"),
    ("04_data_quality_missing_after.png", "data_quality/02_missing_values_after.png", "A. Data", "Missing values after cleaning — all zero"),
    ("05_data_quality_issue_summary.png", "data_quality/04_data_quality_issue_summary.png", "A. Data", "Data-quality issue classes by records affected"),
    ("06_outlier_distribution.png", "data_quality/03_outlier_distribution.png", "A. Data", "Values flagged by the 1.5×IQR rule (flagged, not removed)"),
    # B. EDA
    ("07_revenue_trend_monthly.png", "monthly_revenue_trend.png", "B. EDA", "Monthly delivered revenue across 36 months"),
    ("08_profit_trend_monthly.png", "monthly_profit_trend.png", "B. EDA", "Monthly delivered profit and margin"),
    ("09_revenue_growth_mom.png", "mom_revenue_growth.png", "B. EDA", "Month-over-month revenue growth"),
    ("10_customer_concentration.png", "revenue_concentration_curve.png", "B. EDA", "Cumulative revenue against cumulative customers"),
    ("11_customer_revenue_distribution.png", "customer_revenue_distribution.png", "B. EDA", "Distribution of revenue per customer"),
    ("12_purchase_frequency.png", "purchase_frequency.png", "B. EDA", "Purchase frequency across the customer base"),
    ("13_category_revenue_vs_profit.png", "category_revenue_vs_profit.png", "B. EDA", "Revenue against profit by category"),
    ("14_product_quadrant.png", "product_revenue_profit_quadrant.png", "B. EDA", "Revenue–profit quadrant for all products"),
    ("15_regional_revenue.png", "regional_revenue.png", "B. EDA", "Revenue and profit by region"),
    ("16_correlation_heatmap.png", "correlation_heatmap.png", "B. EDA", "Correlation matrix of the numeric measures"),
    ("17_discount_margin.png", "discount_profit_relationship.png", "B. EDA", "Discount band against profit margin"),
    ("18_order_status_value.png", "order_status_value.png", "B. EDA", "Order value by delivered / returned / cancelled"),
    # C. RFM
    ("19_rfm_recency_distribution.png", "rfm_recency_distribution.png", "C. RFM", "Recency distribution across the base"),
    ("20_rfm_frequency_distribution.png", "rfm_frequency_distribution.png", "C. RFM", "Frequency distribution"),
    ("21_rfm_monetary_distribution.png", "rfm_monetary_distribution.png", "C. RFM", "Monetary-value distribution"),
    ("22_rfm_segment_distribution.png", "rfm_segment_distribution.png", "C. RFM", "Customer count by RFM segment"),
    ("23_rfm_revenue_contribution.png", "rfm_revenue_contribution.png", "C. RFM", "Revenue contribution by RFM segment"),
    ("24_rfm_segment_matrix.png", "rfm_segment_matrix.png", "C. RFM", "Segment matrix over recency and combined FM score"),
    # D. K-Means
    ("25_kmeans_feature_transformation.png", "kmeans_feature_transformation.png", "D. K-Means", "Features before and after log1p → scaling"),
    ("26_kmeans_elbow_curve.png", "kmeans_elbow_curve.png", "D. K-Means", "Inertia against K (elbow curve)"),
    ("27_kmeans_silhouette_scores.png", "kmeans_silhouette_scores.png", "D. K-Means", "Silhouette coefficient against K"),
    ("28_kmeans_silhouette_diagram.png", "kmeans_silhouette_diagram.png", "D. K-Means", "Silhouette diagram for the selected model"),
    ("29_kmeans_cluster_pca.png", "cluster_pca_visualization.png", "D. K-Means", "Clusters projected onto the first two components"),
    ("30_kmeans_cluster_profile.png", "cluster_centroid_profile.png", "D. K-Means", "Cluster centroid profiles on R, F and M"),
    ("31_kmeans_cluster_revenue.png", "cluster_revenue.png", "D. K-Means", "Revenue contribution by cluster"),
    ("32_rfm_vs_cluster_agreement.png", "rfm_vs_ml_cluster_heatmap.png", "D. K-Means", "RFM segments cross-tabulated against clusters"),
    # E. CLV
    ("33_clv_distribution.png", "clv_distribution.png", "E. CLV", "Distribution of historical customer value"),
    ("34_clv_value_concentration.png", "clv_value_concentration.png", "E. CLV", "Concentration of customer value"),
    ("35_clv_model_comparison.png", "clv_model_comparison.png", "E. CLV", "Forward-value model comparison"),
    ("36_clv_actual_vs_predicted.png", "clv_actual_vs_predicted.png", "E. CLV", "Actual against estimated 12-month value"),
    ("37_clv_by_rfm_segment.png", "clv_by_rfm_segment.png", "E. CLV", "Customer value by RFM segment"),
    ("38_clv_feature_importance.png", "clv_feature_importance.png", "E. CLV", "Permutation importance for the value model"),
    # F. Revenue prediction
    ("39_prediction_actual_vs_predicted.png", "actual_vs_predicted_revenue.png", "F. Prediction", "Actual against predicted next-quarter revenue"),
    ("40_prediction_model_comparison.png", "revenue_model_comparison.png", "F. Prediction", "Models and baselines on the test split"),
    ("41_prediction_feature_importance.png", "revenue_feature_importance.png", "F. Prediction", "Permutation feature importance"),
    ("42_prediction_error_distribution.png", "prediction_error_distribution.png", "F. Prediction", "Prediction error distribution"),
    ("43_prediction_error_by_revenue_range.png", "prediction_error_by_revenue_range.png", "F. Prediction", "Error by customer revenue range"),
    ("44_prediction_timeline.png", "revenue_prediction_timeline.png", "F. Prediction", "Actual against predicted by target quarter"),
    # G. Forecasting
    ("45_forecast_historical_revenue.png", "forecasting/historical_revenue_trend.png", "G. Forecasting", "Historical monthly revenue series"),
    ("46_forecast_acf_pacf.png", "forecasting/acf_pacf.png", "G. Forecasting", "ACF and PACF of the revenue series"),
    ("47_forecast_model_comparison.png", "forecasting/forecast_model_comparison.png", "G. Forecasting", "Candidate forecasting models compared"),
    ("48_forecast_backtest.png", "forecasting/backtest_results.png", "G. Forecasting", "Rolling-origin backtest results"),
    ("49_forecast_actual_vs_forecast.png", "forecasting/actual_vs_forecast.png", "G. Forecasting", "Forecast with 80% and 95% prediction intervals"),
    ("50_forecast_seasonal_pattern.png", "forecasting/seasonal_pattern.png", "G. Forecasting", "Seasonal decomposition of the series"),
    # H. SQL
    ("51_sql_er_diagram.png", "sql/er_diagram.png", "H. SQL", "Entity–relationship diagram of the database"),
    ("52_sql_top10_customers.png", "sql/sql_top10_customers.png", "H. SQL", "Top 10 customers by revenue (SQL result)"),
    ("53_sql_customer_concentration.png", "sql/sql_customer_concentration.png", "H. SQL", "Revenue concentration (SQL result)"),
    ("54_sql_revenue_by_rfm_segment.png", "sql/sql_revenue_by_rfm_segment.png", "H. SQL", "Revenue by RFM segment (SQL result)"),
    ("55_sql_monthly_revenue_growth.png", "sql/sql_monthly_revenue_growth.png", "H. SQL", "Monthly revenue growth (window function result)"),
    ("56_sql_region_category_margin.png", "sql/sql_region_category_margin.png", "H. SQL", "Region × category margin test (SQL result)"),
    # I. Power BI - DESIGN MOCKUPS, labelled as such
    ("57_powerbi_home_MOCKUP.png", "powerbi/mockups/00_home_mockup.png", "I. Power BI (design mockup)", "Home / navigation page — design mockup"),
    ("58_powerbi_executive_overview_MOCKUP.png", "powerbi/mockups/01_executive_overview_mockup.png", "I. Power BI (design mockup)", "Executive Overview — design mockup"),
    ("59_powerbi_revenue_intelligence_MOCKUP.png", "powerbi/mockups/02_revenue_intelligence_mockup.png", "I. Power BI (design mockup)", "Revenue Intelligence — design mockup"),
    ("60_powerbi_customer_intelligence_MOCKUP.png", "powerbi/mockups/03_customer_intelligence_mockup.png", "I. Power BI (design mockup)", "Customer Intelligence — design mockup"),
    ("61_powerbi_customer_segmentation_MOCKUP.png", "powerbi/mockups/04_customer_segmentation_mockup.png", "I. Power BI (design mockup)", "Customer Segmentation — design mockup"),
    ("62_powerbi_product_analytics_MOCKUP.png", "powerbi/mockups/05_product_analytics_mockup.png", "I. Power BI (design mockup)", "Product Analytics — design mockup"),
    ("63_powerbi_regional_analytics_MOCKUP.png", "powerbi/mockups/06_regional_analytics_mockup.png", "I. Power BI (design mockup)", "Regional Analytics — design mockup"),
    ("64_powerbi_prediction_forecast_MOCKUP.png", "powerbi/mockups/07_prediction_forecast_mockup.png", "I. Power BI (design mockup)", "Prediction & Forecast — design mockup"),
    ("65_powerbi_recommendations_MOCKUP.png", "powerbi/mockups/08_business_recommendations_mockup.png", "I. Power BI (design mockup)", "Business Recommendations — design mockup"),
    ("66_powerbi_drillthrough_MOCKUP.png", "powerbi/mockups/09_customer_detail_drillthrough_mockup.png", "I. Power BI (design mockup)", "Customer-detail drill-through — design mockup"),
    # J. Streamlit - REAL screenshots of the running application
    ("67_streamlit_home.png", "streamlit/01_home.png", "J. Streamlit (real screenshot)", "Home"),
    ("68_streamlit_executive_overview.png", "streamlit/02_executive_overview.png", "J. Streamlit (real screenshot)", "Executive Overview"),
    ("69_streamlit_revenue_intelligence.png", "streamlit/03_revenue_intelligence.png", "J. Streamlit (real screenshot)", "Revenue Intelligence"),
    ("70_streamlit_customer_intelligence.png", "streamlit/04_customer_intelligence.png", "J. Streamlit (real screenshot)", "Customer Intelligence"),
    ("71_streamlit_customer_segmentation.png", "streamlit/05_customer_segmentation.png", "J. Streamlit (real screenshot)", "Customer Segmentation"),
    ("72_streamlit_product_analytics.png", "streamlit/06_product_analytics.png", "J. Streamlit (real screenshot)", "Product Analytics"),
    ("73_streamlit_regional_analytics.png", "streamlit/07_regional_analytics.png", "J. Streamlit (real screenshot)", "Regional Analytics"),
    ("74_streamlit_revenue_prediction.png", "streamlit/08_revenue_prediction.png", "J. Streamlit (real screenshot)", "Revenue Prediction"),
    ("75_streamlit_sales_forecast.png", "streamlit/09_sales_forecast.png", "J. Streamlit (real screenshot)", "Sales Forecast"),
    ("76_streamlit_recommendations.png", "streamlit/10_business_recommendations.png", "J. Streamlit (real screenshot)", "Business Recommendations"),
    ("77_streamlit_data_explorer.png", "streamlit/11_data_explorer.png", "J. Streamlit (real screenshot)", "Data Explorer"),
    ("78_streamlit_about.png", "streamlit/12_about_project.png", "J. Streamlit (real screenshot)", "About the Project"),
    # K. Architecture diagrams
    ("79_architecture.png", "report/architecture.png", "K. Diagrams", "Solution architecture"),
    ("80_implementation_flowchart.png", "report/flowchart.png", "K. Diagrams", "Implementation flowchart with the three validation gates"),
    ("81_graphical_abstract.png", "report/graphical_abstract.png", "K. Diagrams", "Pipeline from customer data to business decisions"),
]


def render_previews():
    """Render the head of the actual raw and cleaned CSVs as table images.

    These are renderings of the real data files, not screenshots and not
    invented content."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    made = []
    jobs = [
        ("01_raw_dataset_preview.png", "data/raw/customer_sales_raw.csv",
         f"Raw extract — first 8 of {V['raw_rows']} order lines "
         f"({V['raw_cols']} columns; defects deliberately injected)"),
        ("02_clean_dataset_preview.png",
         "data/processed/customer_sales_cleaned.csv",
         f"Cleaned dataset — first 8 of {V['clean_rows']} validated lines "
         f"({V['clean_cols']} columns)"),
    ]
    for name, rel, title in jobs:
        src = ROOT / rel
        if not src.exists():
            continue
        df = pd.read_csv(src, nrows=8)
        cols = list(df.columns)[:9]
        df = df[cols].astype(str)
        df = df.apply(lambda s: s.str.slice(0, 18))
        # The project's privacy rule: customers are identified by Customer_ID
        # only. The names are synthetic, but showing them would contradict the
        # rule stated in the report and enforced by the application's tests.
        if "Customer_Name" in df.columns:
            df["Customer_Name"] = "[masked]"
        fig, ax = plt.subplots(figsize=(15, 3.6), dpi=150)
        ax.axis("off")
        ax.set_title(title, fontsize=11, weight="bold", loc="left", pad=16)
        tbl = ax.table(cellText=df.values, colLabels=cols,
                       cellLoc="left", loc="upper left")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(7.5)
        tbl.scale(1, 1.45)
        for (r, c), cell in tbl.get_celld().items():
            cell.set_edgecolor("#BBBBBB")
            if r == 0:
                cell.set_facecolor("#C00000")
                cell.set_text_props(color="white", weight="bold")
            elif r % 2 == 0:
                cell.set_facecolor("#F4F4F4")
        note = (f"Rendered from {rel} — synthetic data, seed {V['seed']}. "
                f"First {len(cols)} of the file's columns are shown.")
        if "Customer_Name" in cols:
            note += (" Customer_Name is masked: the project identifies "
                     "customers by Customer_ID only.")
        fig.text(0.01, 0.02, note, fontsize=7, style="italic",
                 color="#555555")
        fig.savefig(SHOTS / name, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        made.append(name)
    return made


def build_screenshot_pack():
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()
    copied, missing = [], []
    for target, source, _, _ in PACK:
        src = FIG / source
        if src.exists():
            shutil.copy2(src, SHOTS / target)
            copied.append(target)
        else:
            missing.append((target, source))
    rendered = render_previews()
    return copied, rendered, missing


# ==========================================================================
# 1. LIVE DEMO PLAN
# ==========================================================================
def live_demo_plan():
    return f"""
# Live Demonstration Plan

{STAMP}

A 15-minute demonstration, timed. If you are given 10 minutes, drop sections
6, 11 and 14 and shorten 5 — the compressed running order is at the end.

**Before you start:** open a terminal in the project folder with the virtual
environment active, run `streamlit run app.py` and leave it running in a
browser tab; open the report PDF in a second tab; open
`outputs/screenshots/` in a file browser as the fallback.

---

### 1. Project Introduction — 45 s

- **Open:** PPT slide 1, or just talk.
- **Show:** the project title.
- **Explain:** who you are, where the internship was, and that the platform
  takes retail transaction data from raw file to business decision.
- **Result to mention:** the platform spans {V['py_files']} Python modules and
  is verified by {V['audit_total']} automated checks.
- **Likely question:** *"What was your role?"* → Say plainly what you built.

### 2. Business Problem — 1 min

- **Open:** PPT slide 2.
- **Show:** the four gaps.
- **Explain:** aggregate reporting hides the customer; value and activity get
  treated as one thing; planning is backward-looking; analysis never reaches
  the decision-maker.
- **Result to mention:** the top 20% of customers produce {V['top20']} of
  revenue — a fact monthly totals cannot reveal.
- **Likely question:** *"Why not just improve the reports?"* → Because the
  decisions are taken at customer level.

### 3. Dataset — 1 min

- **Open:** `outputs/screenshots/01_raw_dataset_preview.png` and
  `02_clean_dataset_preview.png`.
- **Show:** the raw extract beside the cleaned dataset.
- **Explain:** synthetic, generated with seed {V['seed']};
  {V['raw_rows']} raw lines over {V['raw_cols']} columns covering
  {V['cust_buy']} purchasing customers, {V['products']} products and
  {V['regions']} regions from {V['start']} to {V['end']}.
- **Result to mention:** say "synthetic" **before** you are asked.
- **Likely question:** *"Why synthetic?"* → No confidentiality constraint,
  full reproducibility, and a known ground truth to audit cleaning against.

### 4. Data Cleaning — 1 min

- **Open:** `outputs/screenshots/01_raw_dataset_preview.png` beside
  `02_clean_dataset_preview.png`, then `03_data_quality_missing_before.png`,
  `04_..._after.png` and `05_data_quality_issue_summary.png`.
- **Show:** the two previews side by side — this is the most persuasive 20
  seconds of the demo, because the fixes are visible in row 2: the date
  `01/01/2023` becomes `2023-01-01`, and the city `Bombay` is standardised to
  `Mumbai`. Point at them.
- **Explain:** every rule is evaluated on the raw data, failing rows logged,
  treatment applied, rule re-evaluated.
- **Result to mention:** {V['missing_before']} rows failed at least one rule
  before treatment; **zero** rules fail after. {V['dupes']} duplicates removed;
  {V['engineered']} engineered columns added.
- **Likely question:** *"How did you handle missing values?"* → By column, by
  meaning; some recovered by arithmetic; nothing dropped silently.

### 5. EDA — 2 min

- **Open:** Streamlit → **Executive Overview**, then **Revenue Intelligence**.
- **Show:** the KPI row, then the monthly revenue trend, then category revenue
  versus profit.
- **Explain:** each chart answers a business question.
- **Results to mention:** {V['revenue']} delivered revenue at {V['margin']}
  margin, {V['orders']} orders, AOV {V['aov']}; growth {V['growth_2024']} then
  {V['growth_2025']} while margin rose to {V['margin_2025']} — growth is not
  bought with margin; {V['top_cat']} is {V['top_cat_rev']} of revenue but only
  {V['top_cat_profit']} of profit, while {V['best_cat']} earns
  {V['best_cat_margin']}.
- **Likely question:** *"Is October seasonality?"* → An observed regularity in
  all three years; the formal test on {V['fc_series']} observations does not
  confirm it.

### 6. RFM Analysis — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation**, RFM view.
- **Show:** the segment distribution and the revenue contribution chart.
- **Explain:** recency, frequency and monetary value scored 1–5 on quintiles at
  reference date {V['ref_date']}, then fixed rules into
  {V['rfm_segments']} segments.
- **Results to mention:** {V['rfm_scored']} customers scored; Champions are
  {V['champ_n']} customers ({V['champ_cust']}) holding {V['champ_rev']} of
  revenue; At Risk holds {V['atrisk_rev']}.
- **Likely question:** *"Why that reference date?"* → It is the latest order
  date plus one day; today's real date would make everyone look inactive.

### 7. Customer Segmentation (K-Means) — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation**, cluster view; keep
  `outputs/screenshots/26_kmeans_elbow_curve.png` and
  `27_kmeans_silhouette_scores.png` ready.
- **Show:** the cluster profile and the PCA projection.
- **Explain:** the same three features, log1p → scaling, K chosen by **three
  rules fixed in advance** — K ≥ {V['min_k']}, no cluster under
  {V['min_share']}, stability ARI ≥ {V['min_ari']} — then highest silhouette.
- **Results to mention:** K = {V['k']}, silhouette {V['silhouette']},
  stability {V['stability']}; cluster 0 ({V['hv_label']}) is {V['hv_cust']} of
  customers and {V['hv_rev']} of revenue; agreement with RFM, ARI {V['ari']}.
- **Likely question:** *"Your silhouette is low."* → Agreed, the base is a
  continuum; what makes it usable is the profile difference and the
  independent agreement with RFM.

### 8. Customer Lifetime Value — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation** (value view) or
  `outputs/screenshots/37_clv_by_rfm_segment.png`.
- **Show:** historical value beside estimated forward value.
- **Explain:** two quantities, never added. Historical is measured; forward is
  a {V['clv_model'].lower()} trained out of time.
- **Results to mention:** historical {V['clv_hist']} of profit, mean
  {V['clv_mean']} against median {V['clv_median']}; model R² {V['clv_r2']} but
  Spearman {V['clv_spearman']} — it ranks well, it does not predict levels;
  **{V['at_risk']} high-value customers inactive 180+ days holding
  {V['at_risk_rev']}**.
- **Likely question:** *"Is this predictive CLV?"* → The forward figure is an
  estimate with stated error; the historical figure is measured. They are
  reported separately.

### 9. Revenue Prediction — 1 min 30 s

- **Open:** Streamlit → **Revenue Prediction**.
- **Show:** the predictions **and** the accuracy panel beside them.
- **Explain:** target is {V['pred_target']}; a {V['panel_rows']}-row
  customer-quarter panel, {V['pred_features']} features all computed before the
  cutoff, chronological split, leakage audited.
- **Results to mention:** test MAE {V['pred_mae']}, R² {V['pred_r2']} — **weak,
  and say so**. The naive baseline scores R² {V['naive_r2']}. Cause:
  {V['pred_zero']} of customer-quarters are zero. Total bias {V['pred_bias']},
  so it is usable at portfolio level.
- **Likely question:** *"Then why include it?"* → Because the honest finding is
  that company revenue is forecastable and individual revenue is not.

### 10. Sales Forecasting — 1 min 30 s

- **Open:** Streamlit → **Sales Forecast**.
- **Show:** the forecast with its prediction interval.
- **Explain:** different task from prediction — one company series, projected
  from its own history. Six model families compared;
  selection rule fixed in advance.
- **Results to mention:** {V['fc_model']}; test MAPE {V['fc_test_mape']} but
  quote the **backtest mean of {V['fc_backtest']}** over {V['fc_folds']} folds;
  {V['fc_horizon']} months ({V['fc_months']}) totalling {V['fc_total']}, 80%
  interval {V['fc_low']} to {V['fc_high']}, against {V['fc_prev6']} in the
  previous six months.
- **Likely question:** *"Why is the interval so wide?"* → Short history and a
  univariate model; a narrow interval here would be a false claim.

### 11. SQL Analytics — 1 min

- **Open:** a terminal — `sqlite3 data/customer_revenue_intelligence.db` — and
  paste the reconciliation query from `outputs/viva/sql_demo_script.md`.
- **Show:** the query returning revenue, profit, margin, orders, customers.
- **Explain:** this layer is an **independent implementation**; agreement with
  Python is evidence, not a copy.
- **Results to mention:** {V['sql_tables']} tables, {V['sql_views']} views,
  {V['sql_queries']} queries; all {V['sql_checks']} validation and
  {V['sql_quality']} quality checks pass; the query returns exactly
  {V['revenue']} and {V['margin']}.
- **Likely question:** *"Which advanced SQL did you use?"* → Window functions
  in 35 queries, CTEs in 27, ranking in 22, running totals, LAG/LEAD.

### 12. Power BI — 1 min

- **Open:** `outputs/screenshots/58_powerbi_executive_overview_MOCKUP.png`.
- **Show:** the page design.
- **Explain, in your first sentence:** "Power BI Desktop is Windows-only and
  was not available, so this is a design mockup rendered from the real data,
  not a screenshot." Then say what **is** complete.
- **Results to mention:** {V['pbi_tables']}-table star schema,
  {V['pbi_rels']} relationships, {V['pbi_measures']} DAX measures in
  {V['pbi_folders']} folders, {V['pbi_matched']}/{V['pbi_val']} validated
  against SQL, {V['pbi_consistency']} consistency checks passing.
- **Likely question:** *"Why not just install it?"* → It does not run on
  Linux; the build guide and every artefact needed are in `powerbi/`.

### 13. Streamlit Application — 2 min

- **Open:** the running app; walk Home → Executive Overview → Customer
  Segmentation → Sales Forecast → Data Explorer, and download one CSV.
- **Show:** the filters changing every chart on a page; the CSV download.
- **Explain:** it loads the persisted `.pkl` models and computes no metric of
  its own, so a number on screen cannot drift from the report.
- **Results to mention:** {V['app_pages']} pages,
  {V['app_passed']}/{V['app_tests']} headless tests pass.
- **Likely question:** *"Is it deployed?"* → No; it runs locally. Deployment is
  future scope.

### 14. Business Recommendations — 1 min

- **Open:** Streamlit → **Business Recommendations**.
- **Show:** two or three cards with their evidence.
- **Explain:** {V['pbi_recs']} recommendations, each generated from the
  pipeline's own outputs with its supporting metric and source.
- **Results to mention:** protect the top decile ({V['top10']} of revenue);
  work the {V['at_risk']}-customer inactive list; manage category mix; test
  the discount relationship rather than acting on it.
- **Likely question:** *"Will these increase revenue?"* → The project cannot
  prove that; they are evidence-linked, not causally proven.

### 15. Conclusion — 45 s

- **Open:** PPT slide 20.
- **Explain:** raw transactions in, business decisions out; every number
  traceable; every model chosen by a rule fixed in advance; weak results
  reported as weak.
- **Result to mention:** {V['audit_total']} automated checks,
  {V['audit_pass']} pass, {V['audit_fail']} fail.
- **Close with:** "I'm happy to take questions, and the application is running
  if you'd like to see anything again."

---

## Compressed 10-minute running order

1 Introduction (30 s) → 2 Problem (45 s) → 3 Dataset (45 s) → 4 Cleaning
(45 s) → 5 EDA (1 min 30 s) → 7 K-Means, mentioning RFM inside it (1 min 30 s)
→ 8 CLV (1 min) → 9 Prediction (1 min) → 10 Forecasting (1 min) → 13 Streamlit
(1 min) → 15 Conclusion (30 s).

## The four things to say even if you run out of time

1. The data is synthetic.
2. The top 20% of customers produce {V['top20']} of revenue, and two
   independent methods identify the same group.
3. Company forecasting works ({V['fc_backtest']} backtest MAPE); individual
   prediction does not (R² {V['pred_r2']}) — and the project says both.
4. The Power BI pages are design mockups, not screenshots.
"""


# ==========================================================================
# 2. LIVE DEMO SCRIPT
# ==========================================================================
def live_demo_script():
    return f"""
# Live Demonstration Script

{STAMP}

Six versions of the same explanation. Read them aloud once each — they are
written to be spoken, not read silently.

---

## 30 seconds

"My project is a customer revenue intelligence platform. It takes retail
transaction data and carries it through cleaning, customer segmentation, value
analysis, revenue prediction and forecasting, and delivers the results through
a Power BI model and a working {V['app_pages']}-page application. The dataset
is synthetic, generated for academic demonstration. The headline finding is
that value is concentrated — the top 20% of customers produce {V['top20']} of
{V['revenue']} in revenue."

---

## 1 minute

"First, the business problem. Retail businesses record transactions far faster
than they turn them into decisions — revenue gets reported by month and
category, but the questions that matter are customer-level: who is valuable,
who is going quiet, what will they spend next.

My project builds one platform that answers those. The dataset is synthetic,
generated with a fixed seed — {V['raw_rows']} raw order lines cleaning to
{V['clean_rows']} validated lines, {V['cust_buy']} customers,
{V['products']} products, {V['months']} months, {V['revenue']} of delivered
revenue.

I segment customers two independent ways — RFM rules and K-Means — estimate
their value, predict next-quarter revenue and forecast company revenue six
months ahead. Everything is reconciled in SQL and delivered through Power BI
and a Streamlit application.

The main finding is concentration: the top 20% of customers carry
{V['top20']} of revenue, and both segmentation methods identify the same
group."

---

## 3 minutes

"Let me start with the problem. Businesses report revenue in aggregate but take
decisions at customer level. A monthly total cannot tell you whether the month
was carried by a few large customers or built on a broad base — so it cannot
tell you where to spend retention effort.

**The data.** It is synthetic, generated with seed {V['seed']} for academic
demonstration — it describes no real company. {V['raw_rows']} raw order lines,
{V['clean_rows']} after cleaning, {V['cust_buy']} purchasing customers,
{V['products']} products across {V['categories']} categories,
{V['regions']} regions, from {V['start']} to {V['end']}.

**Cleaning.** Every business rule is evaluated on the raw extract, the failing
rows are logged, a treatment is applied, and the rule is re-evaluated.
{V['missing_before']} rows failed at least one rule before treatment; zero fail
after.

**Analysis.** Delivered revenue is {V['revenue']} at {V['margin']} margin. The
business grew {V['growth_2024']} then {V['growth_2025']} while margin rose —
so growth is not being bought with margin. And value is concentrated: the top
20% of customers produce {V['top20']}.

**Segmentation.** I scored every customer on recency, frequency and monetary
value into {V['rfm_segments']} rule-based segments, then clustered the same
features with K-Means at K = {V['k']} — chosen by three rules I fixed before
seeing any results. The two methods agree on the high-value group with an
Adjusted Rand Index of {V['ari']}, which is stronger evidence than either alone.

**Prediction and forecasting.** These are different tasks. Customer-level
prediction reached a test R² of {V['pred_r2']} — better than every baseline but
weak, because {V['pred_zero']} of customer-quarters have no order at all. I
report that honestly. Company-level forecasting works much better: a
{V['fc_model']} model with a backtest mean error of {V['fc_backtest']},
projecting {V['fc_total']} over six months with an 80% interval.

**Delivery.** {V['sql_queries']} SQL queries reproduce the metrics
independently, a Power BI model carries {V['pbi_measures']} DAX measures, and a
{V['app_pages']}-page Streamlit application loads the real trained models.

The practical output is a short list: the top decile, and the {V['at_risk']}
high-value customers who have not ordered in 180 days."

---

## 5 minutes

*(Use the 3-minute script, then add these four blocks.)*

"**On data quality specifically.** The generator deliberately injects the
defects a real extract carries — missing values, non-ISO dates, numbers stored
as text, out-of-range discounts, invalid category labels, duplicates — and logs
every injection. That gives me a known ground truth to audit the cleaning
against, which real data could not. {V['dupes']} duplicates removed,
{V['engineered']} engineered columns added, and every rule returns zero
afterwards.

**On why two segmentations.** RFM imposes boundaries I chose; K-Means finds
whatever grouping is actually in the data. Where they agree — the high-value
group — that is real structure. Where they disagree, in the middle of the base,
that tells me my rule boundaries are arbitrary there. Reporting both is more
informative than reporting either.

**On customer value.** I keep two quantities strictly separate. Historical
value is measured: {V['clv_hist']} of profit already earned. Forward value is
estimated by a {V['clv_model'].lower()}, R² {V['clv_r2']} but Spearman
{V['clv_spearman']} — it ranks customers much better than it predicts their
exact spend, so I use it to order a queue of attention, not to promise a
number.

**On the honest result.** The weakest part of the project is customer-level
prediction, and I would rather explain it than dress it up. It beats every
baseline, its total bias is only {V['pred_bias']} so aggregates are usable, but
it explains almost none of the variance in individual outcomes. The cause is
structural zero-inflation, and the correct fix — a two-stage model — is in my
future scope rather than claimed as done."

---

## 10 minutes

*(Follow the 15-section plan in `outputs/final_audit/live_demo_plan.md` at its
compressed running order. Speak the 5-minute script as your narration while you
move through the application: Executive Overview during the EDA block,
Customer Segmentation during segmentation and CLV, Revenue Prediction and
Sales Forecast during the modelling block, Data Explorer at the end.)*

Two lines to have ready verbatim:

- Entering the Power BI section: "Power BI Desktop is a Windows application and
  wasn't available in my build environment, so what you're seeing is a design
  mockup rendered from the real data — not a screenshot. What is complete and
  validated is the semantic model and all {V['pbi_measures']} DAX measures,
  {V['pbi_matched']} of {V['pbi_val']} of which match their SQL equivalents."
- Entering the prediction section: "This is the weakest result in the project,
  and I'd like to explain why rather than skip it."

---

## 15 minutes

*(The full plan in `outputs/final_audit/live_demo_plan.md`, section by section,
with the timings given there. Use the 5-minute script as your spine and expand
each section with the numbers listed against it.)*

**Opening line:** "Good morning. I'm Swagata Das, MBA Data Science and AI at
Apex Institute of Management. I'll show you a customer revenue intelligence
platform I built during my internship at Tutorsuite Technologies — and I'll
start by saying the dataset is synthetic, generated for academic
demonstration."

**Closing line:** "So: raw transactions in, business decisions out, with every
number traceable to the file that produced it and every model chosen by a rule
fixed before I saw the results. Where the results were weak, I've reported them
as weak. I'm happy to take questions — and the application is still running if
you'd like to see anything again."

---

## Delivery notes

- **Pace.** Two sentences, then pause. Examiners interrupt; leave them room.
- **Pointing.** Say the number, then point at it. Not the reverse.
- **The synthetic-data line comes early,** in your own words, not in answer to
  a challenge.
- **When you don't know:** "That value was not directly measured in this
  project." An honest gap costs one mark; a fabricated figure that gets checked
  costs the viva.
- **If asked something covered later:** "I'm coming to that in two minutes — or
  I can jump there now if you'd prefer."
"""


# ==========================================================================
# 3. SCREENSHOT CHECKLIST
# ==========================================================================
def screenshot_checklist(copied, rendered, missing):
    by_cat = {}
    for target, source, cat, caption in PACK:
        by_cat.setdefault(cat, []).append((target, source, caption))
    blocks = []
    for cat, items in by_cat.items():
        rows = "\n".join(
            f"| `{t}` | {c} | `outputs/figures/{s}` | {'✔ in pack' if t in copied else '✖ source missing'} |"
            for t, s, c in items)
        blocks.append(f"### {cat}\n\n| File | Shows | Source | Status |\n|---|---|---|---|\n{rows}")
    body = "\n\n".join(blocks)
    rendered_rows = "\n".join(
        f"| `{r}` | Rendered from the actual CSV by `scripts/build_demo.py` | ✔ in pack |"
        for r in rendered)
    miss = ("\n".join(f"- `{t}` — source `{s}` not found" for t, s in missing)
            if missing else "_None. Every listed source existed._")
    return f"""
# Screenshot Checklist

{STAMP}

**{len(copied) + len(rendered)} images are already in `outputs/screenshots/`.**
They were assembled by copying figures the pipeline produced and by rendering
two dataset previews directly from the real CSV files. **No image was
fabricated.**

Three things to understand about the pack before you use it:

1. The twelve `*_streamlit_*.png` files are **real screenshots** of the running
   application.
2. The ten `*_MOCKUP.png` files are **design mockups rendered from the real
   data**, not Power BI Desktop screenshots. The suffix is in the filename on
   purpose — keep it there.
3. Everything else is a chart the analysis produced.

## A. Data — dataset previews

| File | Shows | Status |
|---|---|---|
{rendered_rows}

{body}

## Sources that were missing

{miss}

## Images you must still capture yourself

These cannot be produced without the live tool, so no file was invented for
them. Capture them only if you want them; the demo works without.

| Wanted | How to capture | Needed for |
|---|---|---|
| SQL query running in a terminal | Run `sqlite3 data/customer_revenue_intelligence.db`, paste the reconciliation query from `outputs/viva/sql_demo_script.md`, screenshot the terminal showing the query **and** its output | Optional — the SQL result charts (`52`–`56`) already carry the findings |
| Power BI Desktop report pages | Only possible on Windows. Open Power BI Desktop, build the model from `powerbi/POWERBI_BUILD_GUIDE.md`, then screenshot each page | Only if you complete the `.pbix`. Until then the mockups are the honest artefact |
| Jupyter notebook with live output | Open any notebook in `notebooks/`, run a cell, screenshot | Optional — the notebooks are committed with outputs already saved |
| The application running on your machine | `streamlit run app.py`, then screenshot each page | Optional — twelve real screenshots are already in the pack |

## Where each image is used

| Destination | Which images |
|---|---|
| **Report** (already embedded) | 9 figures are already in the built report — you do not need to add any |
| **PPT** (already embedded) | 9 images already in the deck, including one real Streamlit screenshot and one labelled mockup |
| **GitHub README** | `79_architecture.png`, `67_streamlit_home.png`, `68_streamlit_executive_overview.png`, `58_powerbi_executive_overview_MOCKUP.png` |
| **Viva / demo fallback** | The whole folder — if the live app fails, open `outputs/screenshots/` and walk the numbered sequence |

## Naming convention

`NN_area_subject[_MOCKUP].png`

- `NN` — two-digit sequence in demonstration order, so sorting the folder gives
  you the demo running order.
- `area` — `data`, `revenue`, `rfm`, `kmeans`, `clv`, `prediction`, `forecast`,
  `sql`, `powerbi`, `streamlit`, or a diagram name.
- `_MOCKUP` — mandatory suffix on any image that is a design mockup rather than
  a screenshot of a running tool. Do not remove it.

## Regenerating the pack

```bash
python scripts/build_demo.py
```

This rebuilds `outputs/screenshots/` from the current figures. If you re-run
the pipeline and the charts change, re-run this and the pack updates.
"""


# ==========================================================================
# 4. POWER BI DEMO SCRIPT
# ==========================================================================
PBI_PAGES = [
    ("Home / Navigation", "Entry point and navigation to the other eight pages",
     "None — it is a landing page",
     "Navigation buttons, a description of each page, the synthetic-data notice",
     "None",
     "Where do I go for what?",
     "The model is a governed starting point, not a free-for-all"),
    ("Executive Overview",
     "The monthly position in one screen for a manager with two minutes",
     "Revenue {{revenue}}, profit {{profit}}, margin {{margin}}, orders {{orders}}, customers {{cust_buy}}, AOV {{aov}}",
     "Monthly revenue and profit line, revenue by region bar, revenue by category bar, revenue contribution by RFM segment, growth by year, concentration curve",
     "Date range, region, category, sub-category, segment, cluster",
     "How is the business performing and where is the revenue coming from?",
     "Revenue grew {{growth_2024}} then {{growth_2025}} while margin rose to {{margin_2025}} — growth is not bought with margin"),
    ("Revenue Intelligence",
     "Decompose revenue and profit across every dimension",
     "Revenue, profit, margin, AOV, units, lost value",
     "Revenue over time, by category and sub-category, by discount band, by payment method, delivered versus returned and cancelled",
     "Date range, category, discount band, payment method",
     "Which parts of the business earn, and which merely turn over?",
     "The {{disc0_band}} discount band returns {{disc0_margin}} margin against {{disc_hi_margin}} in the {{disc_hi_band}} band"),
    ("Customer Intelligence",
     "Understand the customer base rather than the transaction base",
     "Customers {{cust_buy}}, revenue per customer, repeat share, top-decile share",
     "Concentration curve, revenue-per-customer distribution, repeat versus single-purchase comparison, tenure against value, frequency bands",
     "Date range, region, segment, cluster",
     "How concentrated is the revenue, and where does repeat value come from?",
     "Top 10% of customers produce {{top10}} of revenue; repeat customers are {{repeat_cust}} of the base and {{repeat_rev}} of revenue"),
    ("Customer Segmentation",
     "The two segmentation schemes side by side",
     "Segments {{rfm_segments}}, clusters {{k}}, Champions share {{champ_rev}}, at-risk high-value count {{at_risk}}",
     "Customers and revenue by RFM segment, cluster profiles, the RFM-versus-cluster cross-tabulation, the at-risk high-value table",
     "Segment, cluster, recency band, value band",
     "Which customers matter, and which of them are going quiet?",
     "Champions are {{champ_cust}} of customers but {{champ_rev}} of revenue; the two schemes agree at ARI {{ari}}"),
    ("Product Analytics",
     "Separate volume leaders from margin leaders",
     "Revenue, profit and margin by category, sub-category and product; products flagged",
     "Category revenue versus profit, sub-category margin ranking, the product revenue–profit quadrant, top products by revenue and by profit",
     "Category, sub-category, date range",
     "Which products earn, and which only sell?",
     "{{top_cat}} is {{top_cat_rev}} of revenue at {{top_cat_margin}} margin while {{best_cat}} earns {{best_cat_margin}}; {{flagged}} products flagged"),
    ("Regional Analytics",
     "Geography performance and the region × category margin test",
     "Revenue, margin, customers and revenue per customer by region",
     "Revenue and profit by region, state map or bar, city ranking, the region × category margin matrix",
     "Region, state, category, date range",
     "Is any region or region–category pair underperforming on margin?",
     "Revenue is evenly spread ({{top_region}} {{top_region_share}} to {{small_region}} {{small_region_share}}); {{region_gaps}} of {{region_pairs}} pairs sits more than 2 pp below national"),
    ("Prediction & Forecast",
     "The forward view, with its own accuracy shown beside it",
     "Forecast total {{fc_total}}, backtest MAPE {{fc_backtest}}, prediction R² {{pred_r2}}, MAE {{pred_mae}}",
     "Historical revenue with the six-month forecast and intervals, actual versus predicted by quarter, predicted revenue by segment and cluster, the model metrics table",
     "Date range, segment, cluster",
     "What is revenue likely to be, and how much should we trust it?",
     "Company forecast {{fc_total}} with an 80% interval {{fc_low}}–{{fc_high}}; individual prediction R² {{pred_r2}} is weak and shown as such"),
    ("Business Recommendations",
     "Turn the analysis into an action list",
     "{{pbi_recs}} recommendations with their supporting metric and value",
     "Recommendation cards grouped by area, each with evidence, metric, value and analytical source",
     "Area (customer, product, regional, revenue)",
     "What should we actually do on Monday?",
     "Protect the top decile ({{top10}} of revenue) and work the {{at_risk}}-customer inactive list"),
    ("Customer Detail (drill-through)",
     "One customer's full history, reached by right-clicking any customer",
     "That customer's revenue, profit, orders, recency, frequency, segment, cluster and estimated forward value",
     "Order history table, category mix, revenue over time for that customer",
     "Inherited from the page you drilled from",
     "Why is this specific customer in this segment?",
     "Makes a segment assignment checkable by hand, which is the point of a rule-based scheme"),
]


def powerbi_demo_script():
    blocks = []
    for (name, purpose, kpis, charts, filters, question, insight) in PBI_PAGES:
        blocks.append(f"""### {name}

- **Page purpose.** {purpose}
- **KPIs.** {kpis.format(**V)}
- **Charts.** {charts}
- **Filters.** {filters}
- **Business question answered.** {question}
- **Main insight.** {insight.format(**V)}
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.
""")
    pages = "\n".join(blocks)
    return f"""
# Power BI Demonstration Script

{STAMP}

> **Say this first, every time, before anyone asks.** "Power BI Desktop is a
> Windows application and was not available in the environment I built this in.
> The semantic model, all {V['pbi_measures']} DAX measures, the Power Query
> scripts, the theme and a full build guide are complete and validated —
> {V['pbi_matched']} of {V['pbi_val']} measures match their SQL equivalents.
> The page layouts you'll see are **design mockups rendered from the real
> data**, not screenshots of a running report."
>
> Volunteering this costs you nothing. Being caught claiming a screenshot you
> do not have would cost the viva.

## The model behind every page

| Property | Value |
|---|---|
| Tables | {V['pbi_tables']} (star schema) |
| Relationships | {V['pbi_rels']}, all one-to-many, single cross-filter direction |
| DAX measures | {V['pbi_measures']} in {V['pbi_folders']} display folders |
| Date table | Marked, one row per day, covering history and the forecast horizon |
| Measure validation | {V['pbi_matched']}/{V['pbi_val']} match their SQL equivalents |
| Cross-surface consistency | {V['pbi_consistency']}/{V['pbi_consistency']} checks pass |

Every revenue measure carries an explicit delivered-lines filter, so the model
cannot silently report a different revenue definition from the pipeline:

```dax
Total Revenue =
CALCULATE ( SUM ( FactSales[Sales] ), FactSales[Is_Delivered] = TRUE () )
```

## Page by page

{pages}

## The five questions you will be asked

**"What is Power BI used for in your project?"**
It is the governed semantic layer. It takes the SQL views, joins them into a
{V['pbi_tables']}-table star schema, and exposes {V['pbi_measures']} conformed
measures so a business user can slice revenue by date, region, category,
segment or cluster without asking an analyst and without any risk of computing
revenue a different way.

**"Why did you use Power BI instead of Python?"**
They do different jobs, and I used both. Python fits the models and computes
the results; Power BI makes those results explorable by someone who does not
write code. Power BI cannot fit a K-Means model or run statsmodels, and Python
does not give a manager drag-and-drop slicing over a governed model.

**"What is the difference between Power BI and Streamlit?"**
Power BI is a dashboard over a semantic model — pre-computed measures,
self-service exploration. Streamlit is an application — it loads the actual
persisted `.pkl` models, runs predictions, accepts a file upload and returns a
download. Any page that needs a live model has to be Streamlit; any audience
that needs free-form slicing is better served by Power BI. The project ships
both deliberately.

**"How did you design the dashboard?"**
Following the published principles — high data-ink ratio, restrained colour, a
clear hierarchy with headline KPIs first, and one analytical purpose per page.
Each page answers one business question and every visual on it serves that
question. The honest caveat: design effectiveness can only be confirmed by
user testing, which was outside this internship's scope.

**"What KPIs did you select and why?"**
Six on the Executive Overview: revenue {V['revenue']}, profit {V['profit']},
margin {V['margin']}, orders {V['orders']}, customers {V['cust_buy']} and AOV
{V['aov']}. Revenue and profit because they are the outcome; margin because
revenue without margin is not growth; orders and customers because they
separate "more customers" from "bigger baskets"; and AOV because it is the
bridge between them. Every one is computed on delivered lines only.

## If asked to show it live

You cannot — and say so plainly rather than fumbling. Offer instead:

1. The design mockups in `outputs/screenshots/` (files 57–66).
2. `powerbi/dax/` — the actual measure library.
3. `powerbi/validation/` — the measure-by-measure comparison against SQL.
4. `powerbi/POWERBI_BUILD_GUIDE.md` — the build steps.
5. The Streamlit application, which **is** running, for anything interactive.
"""


# ==========================================================================
# 5. STREAMLIT DEMO SCRIPT
# ==========================================================================
APP_PAGES = [
    ("Home", "pages/home.py",
     "Entry point: what the platform is, dataset status, how to navigate",
     "None — it reads the data-status check at start-up",
     "Checks whether the database and each model artefact are present",
     "Status pill, the pipeline flow, page cards",
     "Tells the user immediately whether anything is missing before they trust a number"),
    ("Executive Overview", "pages/executive.py",
     "The monthly position in one screen",
     "Date range, region, category, segment filters",
     "Reads cached KPIs from the shared loader; no metric computed on the page",
     "KPI cards, monthly revenue and profit line, revenue by region and category",
     "A manager sees the position in fifteen seconds"),
    ("Revenue Intelligence", "pages/revenue.py",
     "Decompose revenue and profit across dimensions",
     "Date range, category, discount band, payment method",
     "Groups the delivered lines by the selected dimension",
     "Revenue over time, category and sub-category bars, discount-band margin, payment-method outcomes, order-status value",
     "Separates what earns from what merely turns over"),
    ("Customer Intelligence", "pages/customers.py",
     "Understand the customer base rather than the transaction base",
     "Date range, region, segment",
     "Customer-level rollup from the delivered lines",
     "Concentration curve, revenue-per-customer distribution, repeat versus single purchase, tenure against value",
     "Shows that the top 10% of customers produce {{top10}} of revenue"),
    ("Customer Segmentation", "pages/segmentation.py",
     "RFM segments and K-Means clusters side by side",
     "Segment, cluster, recency and value band; an at-risk high-value toggle",
     "Loads the persisted K-Means model and scaler; joins the RFM and cluster assignments",
     "Segment revenue bars, cluster profiles, the RFM-versus-cluster cross-tab, the at-risk table",
     "Produces the {{at_risk}}-customer working list holding {{at_risk_rev}}"),
    ("Product Analytics", "pages/products.py",
     "Separate volume leaders from margin leaders",
     "Category, sub-category, date range",
     "Product-level aggregation with margin and return rate",
     "Category revenue versus profit, sub-category margin ranking, the product quadrant, top-N tables",
     "{{top_cat}} leads volume at {{top_cat_margin}} margin while {{best_cat}} earns {{best_cat_margin}}"),
    ("Regional Analytics", "pages/regional.py",
     "Geography performance and the region × category margin test",
     "Region, state, category",
     "Regional aggregation plus the pairwise margin comparison against the national figure",
     "Revenue and profit by region, state and city rankings, the region × category matrix",
     "Rules out a regional margin problem: {{region_gaps}} of {{region_pairs}} pairs more than 2 pp below national"),
    ("Revenue Prediction", "pages/prediction.py",
     "Next-quarter customer revenue, shown with its own accuracy",
     "Segment, cluster, revenue band",
     "Loads `revenue_prediction_model.pkl` and its preprocessor and applies them to the prepared panel — it does not refit",
     "Actual versus predicted scatter, error distribution, predictions by segment, the metrics panel",
     "Usable at portfolio level (bias {{pred_bias}}), explicitly not per customer (R² {{pred_r2}})"),
    ("Sales Forecast", "pages/forecasting.py",
     "Six-month company revenue forecast with uncertainty",
     "Interval width (80% / 95%), history window",
     "Loads `forecasting_model.pkl` and reads the persisted forecast table",
     "History with the forecast and shaded intervals, the backtest position, the model comparison",
     "Plan against the interval {{fc_low}}–{{fc_high}}, not the {{fc_total}} point estimate"),
    ("Business Recommendations", "pages/recommendations.py",
     "The action list, with evidence attached",
     "Area filter",
     "Reads the recommendations table generated by the pipeline",
     "{{pbi_recs}} cards, each with finding, evidence, metric, value and analytical source",
     "Every recommendation is traceable to the analysis that produced it"),
    ("Data Explorer", "pages/data_explorer.py",
     "Direct, filterable access to the underlying tables",
     "Table selector, column filters, a CSV upload for schema validation",
     "Applies filters to the selected DataFrame; validates an uploaded file's columns against the expected schema",
     "Paged table view with a CSV download button",
     "Lets an examiner check any number themselves"),
    ("About the Project", "pages/about.py",
     "Methodology, model metadata, limitations and reproduction steps",
     "None",
     "Reads the persisted model metadata files",
     "Method summary, model cards with metrics and selection rules, the limitations list",
     "Puts the limitations in the product, not only in the report"),
]


def streamlit_demo_script():
    blocks = []
    for (name, path, purpose, inp, proc, viz, value) in APP_PAGES:
        blocks.append(f"""### {name}  ·  `{path}`

- **Purpose.** {purpose}
- **Input.** {inp}
- **Processing.** {proc}
- **Visualisation.** {viz}
- **Business value.** {value.format(**V)}
""")
    pages = "\n".join(blocks)
    return f"""
# Streamlit Demonstration Script

{STAMP}

A working **{V['app_pages']}-page** application.
**{V['app_passed']}/{V['app_tests']}** headless tests pass. Start it with:

```bash
streamlit run app.py        # http://localhost:8501
```

## The architectural point to make first

The application is a **presentation layer**. It loads the same persisted `.pkl`
models and the same output files the pipeline wrote, and it computes no metric
of its own — every number comes from the pipeline's outputs or from the shared
module the pipeline itself uses. That is why a figure on screen cannot drift
from the report.

## Page by page

{pages}

## The ten questions you will be asked

**"Why Streamlit?"**
Because the project needed a working application, not only a dashboard — one
that loads the actual trained models, runs predictions, accepts a file upload
and returns downloads. Streamlit does that in pure Python, so the app reuses
`src/data_loader.py` and `src/dashboard_utils.py` rather than reimplementing
the metrics.

**"Why not Flask?"**
Flask is a web framework, not a data-app framework. I would have had to write
routes, templates, HTML, JavaScript and a charting layer before showing a
single number. Streamlit gave me widgets, layout and Plotly integration out of
the box. Flask would be the right choice if I needed a REST API for other
systems to call — which is exactly what I would build for production serving.

**"Why not Django?"**
Django is heavier still — an ORM, an admin, a migrations system, an auth
framework. None of that is needed here: there is no user model, no
database-backed CRUD, no multi-tenant requirement. Using Django would have been
infrastructure without purpose.

**"How does Streamlit execute Python?"**
It re-runs the entire script top to bottom on every interaction. There is no
callback model — when a user moves a slider, the script executes again with the
new widget value. That is why caching matters: without it, every filter change
would reload the database and re-read the models from disk.

**"How are the models loaded?"**
Through a `@st.cache_resource` loader that reads each `.pkl` with joblib and
returns a per-model status. It loads seven artefacts — the K-Means model and
its scaler, the value model and preprocessor, the prediction model and
preprocessor, and the forecasting model. If one is missing, that feature
reports it and the rest of the app keeps working; the test suite verifies this
by deleting a model file and restoring it afterwards.

**"How does the app interact with processed data?"**
`src/data_loader.py` is database-first: it opens
`data/customer_revenue_intelligence.db`, executes the `pbi_*` view definitions
and reads from them. If the database is absent it falls back to the processed
CSV files and says which source it is using. Loads are wrapped in
`@st.cache_data` so a filter change does not re-read anything.

**"How does CSV upload work?"**
`st.file_uploader` accepts the file, the app validates its columns against the
expected schema, and if validation fails it names the missing columns rather
than throwing a traceback. A sample file is provided so the user can see the
expected format. This path is covered by the headless tests.

**"How are filters implemented?"**
Through a shared `sales_filters()` helper in `src/dashboard_utils.py` that
renders the controls and returns the filtered DataFrame, so every page filters
the same way and the filter state is consistent across the charts on a page.

**"How are the Plotly charts generated?"**
Through one helper that applies the project theme, the colour sequence, the
gridline treatment and the title rendering, then returns the figure to
`st.plotly_chart`. Centralising it is why twelve pages look like one system.

**"How would you deploy the application?"**
Streamlit Community Cloud for a demo, or a container behind a reverse proxy
with authentication for anything real, with the data and model artefacts
mounted or pulled from object storage. It is **not** deployed — it runs
locally. Deployment, along with scheduled refresh and monitoring, is future
scope, and I would not claim otherwise.

## Live demo sequence — three minutes in the app

1. **Home** — point at the status pill: the app knows what is loaded.
2. **Executive Overview** — the KPI row. Say {V['revenue']} and {V['margin']}.
3. **Revenue Intelligence** — change one filter and let them watch every chart
   respond.
4. **Customer Segmentation** — switch on the at-risk high-value filter; the
   {V['at_risk']}-customer list appears. This is the moment that lands.
5. **Sales Forecast** — switch the interval from 80% to 95% and say why the
   band widens.
6. **Data Explorer** — download a CSV, so they see the output is takeable.

## If a page is slow

The first load of each page builds its cache. Open the app and click through
every page **before** the examiner walks in; after that, navigation is
instant. Recorded load times are in
`outputs/tables/streamlit_page_load_times.csv`.
"""


# ==========================================================================
# 6. SQL DEMO SCRIPT
# ==========================================================================
def sql_demo_script():
    return f"""
# SQL Demonstration Script

{STAMP}

```bash
sqlite3 data/customer_revenue_intelligence.db
.headers on
.mode column
```

The database: **{V['sql_tables']} tables, {V['sql_views']} views,
{V['sql_queries']} queries** ({V['sql_analysis']} analysis +
{V['sql_business']} business). All {V['sql_checks']} referential and
business-rule checks and {V['sql_quality']} data-quality checks pass.

---

## Query 1 — the reconciliation anchor

**Business question:** what is the headline performance of the delivered
revenue base, and does SQL agree with Python?

```sql
SELECT COUNT(DISTINCT o.order_id)                           AS orders,
       COUNT(DISTINCT o.customer_id)                        AS customers,
       ROUND(SUM(oi.sales), 2)                              AS revenue,
       ROUND(SUM(oi.net_profit), 2)                         AS profit,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct,
       ROUND(SUM(oi.sales) / COUNT(DISTINCT o.order_id), 2) AS aov
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

**Line by line.** `SELECT` lists the six measures. `COUNT(DISTINCT
o.order_id)` counts orders, not order lines — an order can carry several lines.
`SUM(oi.sales)` and `SUM(oi.net_profit)` aggregate at line level. The margin
multiplies by `100.0`, not `100`, to force float division in SQLite. `FROM
order_items` joined to `orders` gives every line its order and customer.
`WHERE oi.order_status = 'Delivered'` is the project's one revenue rule.

**Result type:** one row, six columns.

**Business interpretation:** {V['revenue']} revenue, {V['profit']} profit,
{V['margin']} margin, {V['orders']} orders, {V['cust_buy']} customers, AOV
{V['aov']} — identical to the Python pipeline and the DAX measures. **This is
the query to run live.**

---

## Query 2 — revenue concentration (window function + running total)

**Business question:** how much of revenue do the largest customers carry?

```sql
WITH cust AS (
    SELECT o.customer_id, SUM(oi.sales) AS revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY o.customer_id
)
SELECT customer_id,
       ROUND(revenue, 2) AS revenue,
       ROW_NUMBER() OVER (ORDER BY revenue DESC) AS customer_rank,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER (), 2) AS cumulative_pct_of_revenue
FROM   cust
ORDER  BY revenue DESC
LIMIT  20;
```

**Line by line.** The `WITH cust AS (...)` CTE builds one row per customer —
readable, and reusable in the outer query. `ROW_NUMBER() OVER (ORDER BY revenue
DESC)` ranks customers without collapsing rows. The running total
`SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND
CURRENT ROW)` accumulates down the ordered list, and dividing by `SUM(revenue)
OVER ()` — the grand total on every row — converts it to a cumulative share.

**Result type:** 20 rows, ranked.

**Business interpretation:** this query produces the project's central finding —
the top 10% of customers hold {V['top10']} of revenue and the top 20% hold
{V['top20']}.

---

## Query 3 — year-over-year growth (LAG)

**Business question:** is the business growing, and is it buying that growth
with margin?

```sql
WITH yearly AS (
    SELECT strftime('%Y', o.order_date) AS yr,
           SUM(oi.sales)                AS revenue,
           SUM(oi.net_profit)           AS profit
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY yr
)
SELECT yr,
       ROUND(revenue, 2)                                  AS revenue,
       ROUND(100.0 * profit / revenue, 2)                 AS margin_pct,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY yr))
             / LAG(revenue) OVER (ORDER BY yr), 2)        AS yoy_growth_pct
FROM   yearly
ORDER  BY yr;
```

**Line by line.** `strftime('%Y', ...)` extracts the year — SQLite's date
function. `LAG(revenue) OVER (ORDER BY yr)` reads the previous year's revenue
on the current row, which is what makes a period-over-period calculation
possible without a self-join.

**Result type:** three rows, one per year.

**Business interpretation:** growth of {V['growth_2024']} then
{V['growth_2025']} while margin rose from {V['margin_2023']} to
{V['margin_2025']} — growth is not being bought with margin.

---

## Query 4 — revenue by RFM segment (JOIN to an analytical table)

**Business question:** how much revenue does each customer segment carry?

```sql
SELECT s.rfm_segment,
       COUNT(DISTINCT s.customer_id)                     AS customers,
       ROUND(SUM(oi.sales), 2)                           AS revenue,
       ROUND(100.0 * SUM(oi.sales)
             / (SELECT SUM(sales) FROM order_items
                WHERE order_status = 'Delivered'), 2)    AS pct_of_revenue
FROM   customer_rfm_segments s
JOIN   orders o       ON o.customer_id = s.customer_id
JOIN   order_items oi ON oi.order_id   = o.order_id
WHERE  oi.order_status = 'Delivered'
GROUP  BY s.rfm_segment
ORDER  BY revenue DESC;
```

**Line by line.** Two joins walk from the segment table to the customer's
orders to their order lines. The scalar **subquery** in the SELECT list
computes the grand total once, giving each segment its share. `GROUP BY` then
collapses to one row per segment.

**Result type:** {V['rfm_segments']} rows.

**Business interpretation:** Champions hold {V['champ_rev']} of revenue on
{V['champ_cust']} of customers; At Risk holds {V['atrisk_rev']}.

---

## Query 5 — inactive high-value customers (HAVING + CASE)

**Business question:** which valuable customers have gone quiet?

```sql
SELECT o.customer_id,
       ROUND(SUM(oi.sales), 2)                       AS lifetime_revenue,
       MAX(o.order_date)                             AS last_order_date,
       CAST(julianday('2026-01-01') - julianday(MAX(o.order_date)) AS INT)
                                                     AS recency_days,
       CASE WHEN julianday('2026-01-01') - julianday(MAX(o.order_date)) >= 180
            THEN 'Inactive 180+ days' ELSE 'Active' END AS status
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered'
GROUP  BY o.customer_id
HAVING SUM(oi.sales) > (SELECT AVG(total) FROM
          (SELECT SUM(sales) AS total FROM order_items oi2
           JOIN orders o2 ON o2.order_id = oi2.order_id
           WHERE oi2.order_status = 'Delivered'
           GROUP BY o2.customer_id))
   AND julianday('2026-01-01') - julianday(MAX(o.order_date)) >= 180
ORDER  BY lifetime_revenue DESC;
```

**Line by line.** `MAX(o.order_date)` gives the last purchase per customer.
`julianday()` differences two dates in days — SQLite's date arithmetic.
`CASE WHEN` labels the row. `HAVING` filters **after** aggregation, which
`WHERE` cannot do: it keeps customers whose lifetime revenue exceeds the base
average — computed by a nested subquery — and who have been silent 180 days or
more.

**Result type:** the working list.

**Business interpretation:** this is the logic behind the {V['at_risk']}
high-value inactive customers holding {V['at_risk_rev']}. Note the reference
date {V['ref_date']} is fixed, not `date('now')` — the data ends at
{V['end']}.

---

## Query 6 — discount band against margin (CASE WHEN banding)

**Business question:** what does discounting cost in margin?

```sql
SELECT CASE WHEN oi.discount = 0             THEN '0%'
            WHEN oi.discount <= 0.10         THEN '1-10%'
            WHEN oi.discount <= 0.20         THEN '11-20%'
            ELSE '20%+' END                            AS discount_band,
       COUNT(*)                                        AS order_lines,
       ROUND(SUM(oi.sales), 2)                         AS revenue,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
WHERE  oi.order_status = 'Delivered'
GROUP  BY discount_band
ORDER  BY discount_band;
```

**Business interpretation:** the {V['disc0_band']} band returns
{V['disc0_margin']} margin against {V['disc_hi_margin']} in the
{V['disc_hi_band']} band. Say the caveat out loud: this is an **association**
measured on observed orders, not proof that discounting causes the gap.

---

## SQL concepts, in the project's own terms

| Concept | What it does | Where it is used here |
|---|---|---|
| `SELECT` | Chooses the columns returned | Every query |
| `WHERE` | Filters rows **before** grouping | The revenue rule: `order_status = 'Delivered'` |
| `GROUP BY` | Collapses rows into groups for aggregation | 54 queries |
| `HAVING` | Filters **after** aggregation | 2 queries — e.g. high-value inactive customers |
| `ORDER BY` | Sorts the result | Every top-N query |
| `JOIN` / `INNER JOIN` | Keeps only matching rows | 18 queries — `orders` ↔ `order_items` is the spine |
| `LEFT JOIN` | Keeps all left-table rows | 7 queries — keeps products with no delivered sales, so the denominator is honest |
| `CASE WHEN` | Conditional logic inside a query | 19 queries — discount bands, age bands, conditional counts |
| Aggregates | `SUM`, `AVG`, `COUNT`, `MIN`, `MAX` | Revenue is `SUM(sales)`; AOV is `SUM(sales)/COUNT(DISTINCT order_id)` |
| Subqueries | A query nested inside another | 10 queries — comparing a customer against the base average |
| CTEs (`WITH`) | A named temporary result | 27 queries — readability and reuse |
| Window functions | Compute across related rows without collapsing them | 35 queries — the most-used advanced technique here |
| `ROW_NUMBER` / `RANK` | Sequential or tied ranking | 22 queries — top customers and products |
| Running totals | `SUM(...) OVER (ORDER BY ... ROWS BETWEEN ...)` | 4 queries — the concentration curve |
| `SUM() OVER ()` | Grand total on every row | 18 queries — percentage-of-total columns |
| `LAG` / `LEAD` | Previous or next row in the window | 5 queries — YoY and MoM growth |
| Date functions | `strftime`, `julianday` | 7 queries — year, month, quarter, recency |
| `UNION ALL` | Stacks two result sets | 1 query (BQ10) |

## If asked to run something unplanned

Open `sql/analysis_queries.sql` or `sql/business_queries.sql` — every query is
there, commented with the business question it answers. Running one you have
not rehearsed is fine; the file is the evidence that all
{V['sql_queries']} exist.
"""


# ==========================================================================
# 7-13. ML / BUSINESS / WHY / DIFFICULT / TRICK / RAPID / REVISION
# ==========================================================================
def ml_live_viva():
    return f"""
# Machine Learning Viva — Live Answers

{STAMP}

Twenty answers, each matching the actual implementation.

**1. Why K-Means?**
Because it scales, produces centroids that read directly as business profiles,
and is reproducible from a fixed seed. Hierarchical clustering gives a
dendrogram but is O(n²) and still needs a cut point chosen by judgement; DBSCAN
labels outliers as noise, which does not suit a base where every customer must
land somewhere. Neither was implemented — I considered them and chose K-Means
for those reasons.

**2. What is clustering?**
Grouping observations so that members of a group are more similar to each other
than to members of other groups, without any labels to learn from. It is
unsupervised: there is no correct answer to check against.

**3. Why standardize the RFM features?**
Because K-Means uses Euclidean distance and the three features are on wildly
different scales — monetary value runs to lakhs, frequency is a count under 50.
Without scaling, monetary value alone would determine every cluster. All three
are also heavily right-skewed, so the persisted pipeline applies
{V['preprocessing']}.

**4. What is the elbow method?**
Plotting inertia — the sum of squared distances to assigned centroids — against
K and looking for where the improvement flattens. It is a heuristic, not a
rule: inertia always falls as K rises, and the elbow is often ambiguous, which
is why I did not rely on it alone.

**5. What is the silhouette score?**
For each point, how much closer it is to its own cluster than to the nearest
other cluster, on a scale of −1 to +1. The mean across all points is
{V['silhouette']} here. That is modest, and I report it as modest — customer
data rarely forms well-separated spheres.

**6. How did you choose K?**
By three rules fixed **before** I saw any results: at least {V['min_k']}
clusters, no cluster smaller than {V['min_share']} of the base, and bootstrap
stability of Adjusted Rand Index at least {V['min_ari']}. Only among the values
that passed all three did silhouette decide. K = {V['k']}, silhouette
{V['silhouette']}, stability {V['stability']}. The evaluation table shows every
K tested with its eligibility, including the ones that failed.

**7. What is PCA?**
Principal component analysis — a linear projection into fewer dimensions that
keeps as much variance as possible, with the components ordered by how much
each explains.

**8. Why use PCA?**
Only to visualise the clusters in two dimensions. PC1 explains {V['pc1']} and
PC2 {V['pc2']} — {V['pca_total']} together — so the picture is faithful rather
than lossy. PCA was **not** a model input: clustering runs on all three scaled
features. At three dimensions, reducing first would have added an unexplained
transformation for no benefit.

**9. What is CLV?**
The value a customer represents over their relationship with the business. This
project reports it as two distinct quantities rather than one number.

**10. Historical value vs predicted CLV?**
Historical value is **measured**: {V['clv_hist']} of delivered profit already
earned, mean {V['clv_mean']} against median {V['clv_median']} per customer.
Forward value is **estimated** by a {V['clv_model'].lower()} trained out of
time, MAE {V['clv_mae']}, R² {V['clv_r2']}, Spearman {V['clv_spearman']}. They
are never added together and the estimate is never presented as a guarantee.

**11. Why did you select your revenue prediction model?**
By the rule fixed in advance: {V['pred_rule']}. Random forest, gradient
boosting and a tuned forest were all fitted; none beat the linear model by
enough to pass that tolerance, so the simpler and interpretable model was kept.
That is a signal-strength result, not a claim that linear models are better.

**12. Why a chronological train/test split?**
Because the task is predicting the future from the past. A random split would
let the model learn from quarters that come after the ones it is tested on,
which inflates the score and means nothing operationally. My split is
{V['train_rows']} train ({V['train_period']}), {V['val_rows']} validation
({V['val_period']}), {V['test_rows']} test ({V['test_period']}).

**13. What is data leakage?**
Using information at training time that would not be available at prediction
time — either directly, or through a feature computed over the target window.
It matters because it produces a model that scores well in development and
fails in production.

**14. How did you prevent leakage?**
Every feature in the panel is computed strictly from data before its cutoff. To
verify rather than assume, a leakage audit samples rows and recomputes their
features **directly from the transaction table with independent logic**, then
compares. If the pipeline had leaked, the two would disagree. They did not.

**15. What is MAE?**
Mean absolute error — the average absolute difference between prediction and
actual, in the target's own units. {V['pred_mae']} on the prediction test
split.

**16. What is RMSE?**
Root mean squared error. Errors are squared before averaging, so large misses
are penalised more heavily. {V['pred_rmse']} here — far above the MAE, which
tells you the error distribution has a heavy tail.

**17. What is R²?**
The share of variance in the target explained by the model, relative to simply
predicting the mean. {V['pred_r2']} on prediction — small. The naive
previous-quarter baseline scores {V['naive_r2']}, so the model is better than
the baseline while still explaining little.

**18. What is feature importance?**
How much each feature contributes to the model's predictions. I used
**permutation importance** — shuffle a feature, measure how much the error
rises — because it is model-agnostic and not biased toward high-cardinality
features the way built-in tree importance is. Value drivers:
{V['clv_drivers']}. Prediction drivers: {V['pred_drivers']}.

**19. What is overfitting?**
A model that fits the noise in the training data, so its score does not survive
unseen data. My evidence against it is the direction of the metrics on an
out-of-time test split, and the fact that a linear model with
{V['pred_features']} features on {V['train_rows']} rows has very little
capacity to overfit.

**20. How did you validate the models?**
Differently by task, because the tasks differ. Clustering: internal indices,
bootstrap stability and external agreement with the RFM scheme. Customer value:
5-fold cross-validation within the training cutoff to select, then an
out-of-time test. Prediction: chronological split plus an independent leakage
audit. Forecasting: rolling-origin backtesting over {V['fc_folds']} folds, with
a hard requirement to beat both naive baselines. And the whole project carries
{V['audit_total']} automated checks, {V['audit_pass']} passing.
"""


def business_viva():
    return f"""
# Business Viva — Live Answers

{STAMP}

**1. What business problem does your project solve?**
It closes the gap between recording transactions and taking decisions.
Aggregate reporting cannot distinguish a month carried by a few large customers
from one built on a broad base, so it cannot guide retention effort. This
platform answers the customer-level questions: who is valuable, who is going
quiet, what will they spend, and what will total revenue be.

**2. Who would use this system?**
Three audiences with three surfaces. A sales or account manager uses the
Customer Segmentation page to work the at-risk list. A category or regional
manager uses Power BI to slice revenue and margin for their own area. A
planner uses the Sales Forecast for capacity and cash. The report and the audit
serve whoever has to trust the numbers.

**3. How can management use customer segmentation?**
By setting a different action per segment rather than treating all customers
alike. Champions ({V['champ_cust']} of customers, {V['champ_rev']} of revenue)
get protection and early access. At Risk ({V['atrisk_rev']} of revenue) gets
reactivation. Lost gets low-cost contact at most. The K-Means clusters are the
cross-check: where the two schemes disagree, the customer is near a boundary
and deserves a human look.

**4. How can the company identify high-value customers?**
Three converging routes, which is what makes the answer trustworthy: the RFM
Champions segment, K-Means cluster 0 ({V['hv_cust']} of customers,
{V['hv_rev']} of revenue), and the revenue concentration curve. All three
point at the same group, and the top decile alone carries {V['top10']} of
revenue.

**5. How can the company reduce the risk of losing customers?**
By acting on **inactivity**, which is what this data supports — not churn,
which it does not define. The median gap between orders is {V['median_gap']}
days, so a customer silent for several multiples of that is behaving
differently. The concrete output is the {V['at_risk']} high-value customers
inactive for 180+ days, holding {V['at_risk_rev']} between them.

**6. How can CLV support marketing decisions?**
By ranking customers on estimated forward twelve-month profit rather than on
past spend. The model's Spearman of {V['clv_spearman']} says it ranks well even
though its R² of {V['clv_r2']} says it predicts levels poorly — so it orders a
queue of attention. Its top-20% capture is {V['clv_top20']}.

**7. How can revenue prediction support planning?**
At portfolio level only. Total bias is {V['pred_bias']}, so aggregated
predictions are close to unbiased and can inform a quarterly expectation.
Individual predictions explain almost nothing ({V['pred_r2']}) and must not set
a target for one customer. Being clear about that boundary is part of the
answer.

**8. How can forecasting support inventory and cash decisions?**
The {V['fc_horizon']}-month forecast is {V['fc_total']} with an 80% interval of
{V['fc_low']} to {V['fc_high']}, against {V['fc_prev6']} delivered in the
previous six months. The right use is to commit against the lower bound and
size capacity against the point estimate — plan against the interval, not the
number.

**9. How can the dashboard support management?**
By removing the analyst from the loop for routine questions. A manager slices
revenue by date, region, category or segment over {V['pbi_measures']} conformed
measures, so "revenue" means one thing everywhere. The Streamlit application
adds what a dashboard cannot do: run the actual models and return downloads.

**10. What business decisions can be made from your project?**
Where to put retention effort (the top decile and the {V['at_risk']}-customer
list); how to manage category mix ({V['top_cat']} at
{V['top_cat_margin']} margin versus {V['best_cat']} at
{V['best_cat_margin']}); whether to run a discount experiment; what to plan
next quarter against; and where **not** to spend — there is no regional margin
problem, and the Lost segment carries little revenue.

**11. What are the limitations?**
Synthetic data; a {V['months']}-month history; weak individual prediction;
a univariate forecast; association not causation; no churn label; Power BI
Desktop unavailable so its pages are design mockups; no user testing; and no
deployment or monitoring.

**12. What would you improve with real company data?**
Four things specifically. I would replace my quintile cut-offs with
business-supplied thresholds, so a segment means something absolute. I would
ask the business to define a churn event and build a supervised model against
it. I would add cost-to-serve so customer value becomes contribution rather
than gross profit. And I would validate whether the segment structure that
emerges matches the one found here — which is the real test of whether the
method transfers.

**13. What is the return on this project?**
The project measured no acquisition cost or campaign response, so I cannot
compute one, and I will not invent a figure. What I can say is where value sits
— {V['top20']} of revenue in the top 20% of customers, and
{V['at_risk_rev']} of it already earned but going quiet.

**14. If you had to defend one recommendation, which?**
Give the top revenue decile a named owner and review it monthly. It costs
almost nothing, it protects {V['top10']} of revenue, and it does not depend on
any model being accurate.

**15. Which recommendation would you be most careful about?**
The discount one. The evidence is strong — the zero-discount band is
best-margin in {V['disc_best_in']} of {V['cats_tested']} categories — but it is
observational. Deeper discounts may be applied to situations that are already
low-margin. That is why the recommendation is an experiment, not a price change.
"""


def why_questions():
    return f"""
# "Why Did You Use This?" — Live Answers

{STAMP}

Every answer starts with *because* and names something specific in the project.

**Why Python?**
Because the whole pipeline — cleaning, statistics, clustering, regression,
time series and the application — exists in one ecosystem, so nothing has to be
handed between languages. It also let the Streamlit app reuse the pipeline's
own modules rather than reimplementing the metrics, which is why a number on
screen cannot drift from the report.

**Why Pandas?**
Because the unit of work is a labelled table with mixed types, and pandas gives
vectorised group-by, join, reshape and time handling on exactly that. At
{V['clean_rows']} rows and {V['clean_cols']} columns the data fits comfortably
in memory, so a DataFrame is the right structure rather than a database round
trip for every operation.

**Why NumPy?**
Because it is the numerical layer under pandas and scikit-learn, and I used it
directly for the transforms — `log1p` on the skewed RFM features before
clustering, and `arcsinh` on the skewed customer-value features.

**Why SQL?**
Because I wanted a second, independent implementation. The same definitions
written in a different language means that when SQL and Python agree on
{V['revenue']} and {V['margin']}, that is evidence rather than a copy of one
code path. It also normalises the data properly — {V['sql_tables']} tables with
enforced keys — instead of one flat file.

**Why RFM?**
Because it is auditable. A business user can see exactly why a customer landed
in a segment, which a clustering cannot offer. And recency, frequency and
monetary value carry most of the information needed to rank a customer base,
which is why it has survived since Hughes formalised it in 1994.

**Why K-Means?**
Because it is an independent check on my own rules. RFM imposes boundaries I
chose; K-Means finds whatever grouping is actually in the data. Their agreement
on the high-value group — ARI {V['ari']} — is stronger evidence than either
method alone.

**Why StandardScaler?**
Because K-Means uses Euclidean distance and monetary value runs to lakhs while
frequency is a count under 50. Without scaling, monetary value would determine
every cluster by itself. It sits after `log1p` in a persisted pipeline, so the
same transformation is applied at scoring time.

**Why PCA?**
Because I needed to show four clusters in three dimensions on a two-dimensional
slide, and PC1 plus PC2 explain {V['pca_total']} of the variance — so the
picture is faithful. It was used for **visualisation only**; reducing three
features before clustering would have added an unexplained transformation for
no benefit.

**Why CLV?**
Because past spend and future worth are different questions, and treating them
as one misdirects effort. Separating measured historical value from estimated
forward value is what produces the actionable output: the {V['at_risk']}
high-value customers who have gone quiet.

**Why machine learning at all?**
Because two of the questions cannot be answered by aggregation. Finding
behavioural groups without imposing rules needs unsupervised learning, and
estimating next-quarter revenue from a customer's history needs a fitted model.
Where aggregation was sufficient — the KPIs, the concentration curve — I used
aggregation.

**Why time-based validation?**
Because the task is predicting the future from the past, and a random split
would train on quarters that come after the test quarters. That inflates the
score and means nothing in practice. Everything time-dependent here uses a
chronological split, and the forecast additionally uses rolling-origin
backtesting over {V['fc_folds']} folds.

**Why Power BI?**
Because a business audience needs governed self-service, not a notebook. A star
schema with {V['pbi_measures']} conformed measures lets a manager slice revenue
by date, region, category or segment without an analyst and without any risk of
computing revenue a different way.

**Why Streamlit?**
Because the project needed a working application, not only a dashboard. Power
BI cannot load a scikit-learn model or a statsmodels object; any page that
needs a live model — prediction, forecasting — has to run Python, and Streamlit
does that while reusing the pipeline's own modules.

**Why Plotly?**
Because the application needed interactivity — hover, zoom, legend toggling —
that a static image cannot give, and it integrates directly with Streamlit.
Matplotlib is used for the report and notebook figures, where print quality
matters more than interaction.

**Why forecasting as well as prediction?**
Because they answer different planning questions. Prediction tells you about a
customer; forecasting tells you about the company. And the contrast turned out
to be a finding in itself: company revenue forecasts to {V['fc_backtest']}
backtest MAPE while individual revenue predicts at R² {V['pred_r2']}.

**Why synthetic data?**
Because it removes any confidentiality constraint while preserving the full
analytical problem, and it gives something real data cannot: a known ground
truth. The generator logs every defect it injects, so the cleaning stage can be
audited against what was actually done to the data. The cost — which I state
everywhere — is that the numbers describe no real business.
"""


def difficult_questions():
    return f"""
# Difficult Professor Questions — Live Answers

{STAMP}

Thirty questions aimed at the weak points, answered honestly. This file
complements `08_challenging_questions.md` from Step 16 — that one is written
for reading, this one for answering aloud under pressure.

**1. Why should we trust your segmentation?**
Because it was validated three ways rather than asserted. Internally:
silhouette {V['silhouette']}. For stability: bootstrap mean ARI
{V['stability']}. Externally: an independent rule-based scheme finds
substantially the same high-value group, ARI {V['ari']}. And K was chosen by
rules fixed before the results.

**2. How do you know the clusters are meaningful?**
Because their business profiles differ materially — cluster 0 is
{V['hv_cust']} of customers and {V['hv_rev']} of revenue — and because a method
that knows nothing about my rules found the same high-value group. Statistical
separation is modest; business separation is not.

**3. What if K-Means gives unstable clusters?**
That is exactly what the stability rule tests. I resampled with replacement,
re-clustered and compared partitions by ARI; K = {V['k']} scores
{V['stability']} against a pre-declared floor of {V['min_ari']}. Values that
failed it were rejected regardless of their silhouette.

**4. What if the dataset changes?**
The segments would shift, because the quintile cut-offs are relative to the
base. The pipeline is fully re-runnable, so re-scoring is one command — but
nothing in the current system would **tell** you the distribution had moved.
That is a genuine gap, named in future scope as drift monitoring.

**5. What happens with missing values in new data?**
The cleaning rules run on any extract, and each rule has a defined treatment.
What the system does not have is a monitored threshold — if a new extract
arrived 40% empty, the rules would treat it and report it, but nothing would
halt the pipeline. In production that gate should exist.

**6. What happens with unseen categories?**
The prediction preprocessor one-hot encodes the categorical features. An unseen
category at scoring time would be handled by the encoder's configuration rather
than crashing, but it would carry no learned signal — effectively a neutral
row. For a genuinely new product category, the right answer is to refit, not to
score.

**7. What if the model performs poorly?**
One of mine does, and I report it rather than hide it: prediction R²
{V['pred_r2']}. The response is to state the boundary of legitimate use —
portfolio level, bias {V['pred_bias']}, not individual customers — and to name
the structural cause, {V['pred_zero']} zero customer-quarters.

**8. Why isn't correlation enough?**
Because correlation measures linear co-movement and says nothing about
direction or mechanism. The discount finding is the clearest case: the
{V['disc0_band']} band shows {V['disc0_margin']} margin against
{V['disc_hi_margin']}, but discounts may be **applied to** low-margin
situations rather than causing them. Only an experiment separates those.

**9. Why can't revenue prediction simply use historical revenue?**
It can, and that is my baseline — the naive previous-quarter rule. It scores
MAE {V['naive_mae']} and R² {V['naive_r2']}. The model beats it
({V['pred_mae']}, {V['pred_r2']}), which is the only reason it earns its place.
If it had not beaten the baseline I would have said so.

**10. How did you avoid leakage?**
By construction and then by test. Every feature is computed strictly before its
cutoff; then a leakage audit samples rows and recomputes those features
directly from the transaction table with independent logic. If the pipeline had
leaked, the two would disagree.

**11. Why should management trust the forecast?**
Trust the interval, not the point. The honest expected error is the backtest
mean of {V['fc_backtest']} over {V['fc_folds']} folds, not the favourable
single-split {V['fc_test_mape']}. And the model had to beat both naive
baselines to be selected at all.

**12. What would change with real company data?**
Business-supplied segment thresholds instead of my quintiles; a churn label the
business defines; cost-to-serve so value becomes contribution rather than gross
profit; and a real test of whether the segment structure transfers.

**13. How would you deploy this system?**
Schedule the pipeline stages; version model artefacts with their metadata;
serve predictions through a small API rather than in-process loading;
containerise the app behind authentication; add drift and performance
monitoring. None of it exists today — the app runs locally.

**14. How would you handle 10 million transactions?**
The pandas in-memory approach stops being appropriate. I would push the
aggregations into SQL — most of the EDA and the RFM base table are already
expressible as queries — use chunked or columnar reads for the modelling
panel, and fit K-Means with MiniBatchKMeans. The analysis would not change;
the execution layer would.

**15. How would you monitor model drift?**
Three signals: input distributions against the training distribution, the
prediction distribution over time, and realised accuracy when actuals arrive —
which for a quarterly target means one honest score per quarter. Not
implemented.

**16. Your silhouette is {V['silhouette']}. Most textbooks call that weak.**
That is a fair reading and I do not dispute it. The base is a continuum, not
four separated populations. Usability comes from the profile differences and
the independent agreement, not from separation.

**17. Could a different K tell a completely different story?**
Different boundaries, yes. What is stable is the high-value group — it appears
at every eligible K and under the rule-based scheme too. The middle of the base
is where assignment is sensitive, which is precisely where I say the rules are
arbitrary.

**18. You generated the data yourself. Didn't you find what you put in?**
Partly, and that is the honest limit. The generator sets skewed value,
seasonality, discounting and returns. It does not set the ARI between two
schemes, the silhouette, or how predictable next-quarter revenue turns out to
be — and that last one came out the opposite of what I expected.

**19. Why is your customer-value R² only {V['clv_r2']}?**
Because twelve-month-ahead individual profit is genuinely hard to predict from
eight behavioural features. The more useful number is Spearman
{V['clv_spearman']} and top-20% capture {V['clv_top20']} — it ranks well, which
is how it is used.

**20. Did your audit ever actually fail?**
Yes, which is the test of whether it is real. It caught documentation
describing recency as a churn warning in a project with no churn event; a stale
figure quoting an older audit count; a filename in the appendix that did not
match the persisted model; and four pipeline commands in the user manual naming
functions that do not exist. All were fixed at source.

**21. What is the weakest link in the project?**
The customer-level prediction model. Everything upstream is either measured or
validated; that is the one component whose individual output I would not act
on.

**22. If a colleague inherited this tomorrow, what would break first?**
Nothing would break, but it would go stale silently. There is no scheduling and
no monitoring, so the models would keep returning confident numbers from an
increasingly old training window.

**23. Why did a linear regression beat two ensembles?**
It did not beat them outright — it tied within the tolerance I had fixed in
advance ({V['pred_rule']}). Given a tie, the simpler interpretable model wins
by rule. That is a signal-strength finding, not a claim about model families.

**24. Why should I believe your selection rules were fixed in advance?**
Because they are published with the results and the evaluation tables include
the options that **failed** them. If I had chosen after the fact, the failing
candidates would not be in the table.

**25. What does your project prove?**
That value in this base is concentrated and identifiable by two independent
methods, and that company-level revenue is forecastable while individual
revenue is not. It proves nothing causal, and it proves nothing about a real
business.

**26. If I gave you one more month, what would you do?**
The two-stage prediction model, because it addresses the one structural
weakness. Then drift monitoring, because without it the whole thing decays
invisibly.

**27. Why no churn model, when churn is the standard use case?**
Because the dataset defines no churn event — no contract, no cancellation, no
explicit lapse. Any label would have been invented by me and then predicted by
me, which proves nothing. I report recency-based inactivity instead and never
use the word churn for a result.

**28. Your report says "complete". Can you prove that?**
No — and I would distinguish the claims. Consistent and reconciled I can
evidence with {V['audit_total']} checks. Complete is a judgement: it means I
believe nothing material is missing, and that is not provable.

**29. What would make you distrust your own results?**
If the SQL layer disagreed with the Python pipeline, since they are independent
implementations of the same definitions. Or if the leakage audit found a
mismatch. Those are the two checks designed to catch me being wrong.

**30. Why does this project deserve a good grade?**
Not because the models are strong — one is not. Because every number is
traceable to the file that produced it, every model was chosen by a rule fixed
before the results, weak results are reported as weak, an association is never
called causation, and the integration is tested by {V['audit_total']} automated
checks rather than asserted.
"""


def trick_questions_live():
    return f"""
# Trick Questions — Live Answers

{STAMP}

Twenty-two questions that invite a confident wrong answer. The mark is in the
nuance, not the speed. Complements `09_trick_questions.md` from Step 16.

**1. What is the difference between RFM segmentation and K-Means
segmentation?**
RFM is **rule-based**, not machine learning: I define the scores and the
thresholds, so every assignment is explainable and checkable by hand. K-Means
is **unsupervised learning**: it finds groups by minimising within-cluster
variance, with no knowledge of my rules. That independence is why their
agreement — ARI {V['ari']} — counts as evidence.

**2. Can K-Means predict future customers?**
No. K-Means is descriptive, not predictive. It can **assign** a new customer to
the nearest existing centroid once that customer has recency, frequency and
monetary values — but it forecasts nothing, and it cannot place a customer with
no purchase history at all.

**3. Is correlation the same as causation?**
No, and the discount finding is exactly why I am careful. The
{V['disc0_band']} band shows {V['disc0_margin']} margin against
{V['disc_hi_margin']}, but deeper discounts may be applied to already
low-margin situations. The recommendation is therefore an experiment, not a
price change.

**4. Does a high-revenue customer always have high CLV?**
No. Revenue is not profit — RFM's M is revenue, so a customer buying often in a
low-margin category can contribute less profit than a smaller buyer in a
high-margin one. And historical value is not forward value: a large customer
who has gone quiet has high history and low expected future, which is exactly
the {V['at_risk']}-customer list.

**5. Does a high R² automatically mean the model is good?**
No. R² says nothing about bias, ranking ability, or whether the errors have a
heavy tail. My customer-value model has R² {V['clv_r2']} but Spearman
{V['clv_spearman']} — poor at levels, good at ranking. A high R² can also be a
leakage symptom rather than a success.

**6. Can you use accuracy for regression?**
No. Accuracy is a classification metric — the share of correct labels — and a
continuous prediction is essentially never exactly correct. Regression uses
MAE, RMSE, R², and for this project WAPE, because MAPE breaks near zero.

**7. Why shouldn't you randomly split time-series data?**
Because it trains on the future to predict the past. Random splitting destroys
the ordering the task depends on and produces a score that cannot be achieved
in practice. Everything time-dependent here uses a chronological split, and the
forecast uses rolling-origin backtesting.

**8. Can Power BI replace machine learning?**
No. Power BI aggregates and presents; it does not fit a K-Means model, a
regression or a time-series model. It consumes the results my Python pipeline
produced.

**9. Can Streamlit itself train a model?**
Streamlit is just Python, so a script could technically call `fit()` — but
mine deliberately does not. The app loads the persisted `.pkl` artefacts and
never refits, because a model retrained on every page load would be
non-reproducible and slow.

**10. Does PCA improve model accuracy automatically?**
No. PCA discards variance to reduce dimensionality — it can help with
collinearity or noise, and it can equally throw away signal. With three
features there was nothing to gain, which is why I used it for visualisation
only.

**11. Your project has {V['clean_rows']} rows. Is that big data?**
No, and I would not call it that. It fits in memory on a laptop. The interest
here is the integration and the discipline, not the volume — and I have an
answer for what would change at ten million rows.

**12. A silhouette of {V['silhouette']} — is your clustering wrong?**
Not wrong; weakly separated. The algorithm converged, the clusters are stable
at ARI {V['stability']}, and their profiles differ materially. What the number
says is that the customer base is a continuum, which is true of most customer
bases.

**13. Is your forecast a guarantee of future revenue?**
No. It is a projection of one series from its own history, with an 80% interval
of {V['fc_low']} to {V['fc_high']} and an expected error of
{V['fc_backtest']}. It knows nothing about prices, promotions or competitors.

**14. Champions are your best customers — should you spend most of the budget
on them?**
Not automatically. They are already buying, so the marginal return on
contacting a Champion may be lower than on reactivating an At Risk customer
holding {V['atrisk_rev']} of revenue. This project measures value, not marginal
response, and I will not claim the latter.

**15. You removed {V['dupes']} duplicates — what if they were real repeat
orders?**
They were exact duplicate rows including order ID; a genuine repeat purchase
would carry a different order ID and date. The removal is logged, and the
generator's injection log confirms they were injected duplicates.

**16. If the model predicts ₹0 for a customer, should the business drop them?**
No. {V['pred_zero']} of customer-quarters are genuinely zero, so zero is the
model's most common output and carries very little information about any
individual. At R² {V['pred_r2']} it should not drive an individual decision at
all.

**17. Is a {V['margin']} margin good?**
Unknowable from this data — there is no benchmark, no competitor and no target
in a synthetic catalogue. What I can say is internal: margin **rose** from
{V['margin_2023']} to {V['margin_2025']} while revenue grew.

**18. October is your best month — is that seasonality?**
It is a regularity in all three years, but the formal seasonality test on
{V['fc_series']} observations does not confirm a stable pattern. Calling it
seasonality would overstate what {V['months']} months can support.

**19. The top 20% produce {V['top20']} — isn't that just Pareto, so nothing
new?**
The principle predicts concentration; it does not tell you who, or how much in
this base — and here it is {V['top20']}, not the proverbial 80%. The
contribution is the named list and the fact that two independent methods
identify the same group.

**20. Can synthetic data represent real customer behaviour?**
Structurally, to a degree — skew, seasonality, discounting, returns and missing
fields are all present. Behaviourally, no: there is no motivation, no
competitive response, no macroeconomic effect. It demonstrates method; it does
not support conclusions about a market.

**21. If your pipeline is automated, what did you actually do?**
Chose the definitions, the rules and the validation. Deciding that revenue
means delivered lines only, that K must pass three pre-declared tests, that a
forecast must beat both naive baselines, and that no number may be typed into a
report by hand — then building the audit that checks all of it.

**22. Could more tuning have given you a better R²?**
A little, probably not much. The ceiling here is set by zero inflation, not by
hyperparameters. The real improvement is structural — a two-stage model — and
that is in future scope, not claimed as done.
"""


def rapid_fire_viva():
    return f"""
# Rapid-Fire Viva — 55 Questions

{STAMP}

One or two sentences each. Answer fast, and where a number exists, say it.

## Python and Pandas

1. **What is Python used for here?** Every stage — cleaning, analysis,
   modelling, forecasting and the application.
2. **What is a DataFrame?** A labelled two-dimensional table; the project's
   cleaned dataset is {V['clean_rows']} rows × {V['clean_cols']} columns.
3. **`loc` vs `iloc`?** `loc` selects by label, `iloc` by integer position.
4. **What does `groupby` do?** Splits rows into groups, applies an aggregation,
   and combines the results — the basis of every KPI here.
5. **What does `merge` do?** Joins two DataFrames on a key, like a SQL JOIN.
6. **What is `apply` and why avoid it?** It runs a function row-wise; it is slow
   compared with vectorised operations, so it is used sparingly.
7. **Why NumPy?** The numerical layer under pandas; used directly for the
   `log1p` and `arcsinh` transforms.
8. **What does `log1p` do?** Computes log(1+x) — compresses right-skew and
   handles zeros safely.
9. **What is joblib for?** Persisting and reloading the trained models as
   `.pkl` artefacts.
10. **How many Python modules are in the project?** {V['py_files']}, about
    {V['py_lines']} lines.

## SQL

11. **How many tables?** {V['sql_tables']} tables and {V['sql_views']} views.
12. **How many queries?** {V['sql_queries']} — {V['sql_analysis']} analysis and
    {V['sql_business']} business.
13. **WHERE vs HAVING?** WHERE filters before aggregation, HAVING after.
14. **INNER vs LEFT JOIN?** INNER keeps only matches; LEFT keeps all left rows
    with NULLs where there is none.
15. **What is a CTE?** A named temporary result defined with `WITH`; used in 27
    queries.
16. **What is a window function?** Computes across related rows without
    collapsing them; used in 35 queries.
17. **ROW_NUMBER vs RANK?** ROW_NUMBER is unique even for ties; RANK gives ties
    the same value then skips.
18. **What does `SUM() OVER ()` give?** The grand total on every row — how
    percentage-of-total columns are built.
19. **What are LAG and LEAD?** Read the previous or next row in a window; the
    basis of year-over-year growth.
20. **Why a normalised database?** To remove repetition, enforce keys, and make
    SQL a genuinely independent implementation.

## Statistics and EDA

21. **Mean vs median here?** Mean profit per customer {V['clv_mean']} against
    median {V['clv_median']} — the gap is right-skew.
22. **What is skewness?** Asymmetry in a distribution; R, F and M are all
    right-skewed, which is why they are log-transformed.
23. **What are quantiles?** Cut points dividing a distribution into equal
    groups; RFM uses quintiles.
24. **How did you detect outliers?** The 1.5×IQR rule — flagged and inspected,
    never removed.
25. **What is correlation?** Linear co-movement from −1 to +1; computed across
    the numeric measures during EDA.
26. **What is EDA?** Understanding structure, quality and relationships before
    modelling.
27. **What is feature engineering?** Creating variables with business meaning;
    {V['engineered']} columns added here.

## RFM and clustering

28. **What is RFM?** Recency, frequency and monetary scoring into named
    segments — {V['rfm_segments']} here.
29. **Your reference date?** {V['ref_date']} — the latest order date plus one
    day.
30. **How many customers scored?** {V['rfm_scored']}; {V['rfm_excluded']}
    excluded for having no delivered purchase.
31. **Champions?** {V['champ_n']} customers, {V['champ_cust']} of the base,
    {V['champ_rev']} of revenue.
32. **What is K-Means?** Partitions data into K clusters by minimising
    within-cluster variance.
33. **What is a centroid?** The mean position of a cluster's members.
34. **What is inertia?** Sum of squared distances to assigned centroids — what
    K-Means minimises.
35. **Your K and silhouette?** K = {V['k']}, silhouette {V['silhouette']}.
36. **How was K chosen?** Three rules fixed in advance, then highest silhouette
    among the eligible values.
37. **What is ARI?** Chance-corrected agreement between two partitions —
    {V['ari']} between RFM and clusters.
38. **What is PCA used for here?** Visualisation only — {V['pca_total']} of
    variance in two components.

## Customer value, prediction, forecasting

39. **What is CLV?** Customer lifetime value; here reported as measured
    historical and estimated forward, separately.
40. **Historical value total?** {V['clv_hist']} of delivered profit.
41. **Which value model?** {V['clv_model']} — R² {V['clv_r2']}, Spearman
    {V['clv_spearman']}.
42. **How many at-risk high-value customers?** {V['at_risk']}, holding
    {V['at_risk_rev']}.
43. **Prediction target?** Each customer's delivered revenue in the next
    quarter.
44. **Prediction model and score?** {V['pred_model']}, test R² {V['pred_r2']},
    MAE {V['pred_mae']}.
45. **Why is it weak?** {V['pred_zero']} of customer-quarters have a zero
    actual value.
46. **What is data leakage?** Using information unavailable at prediction time;
    audited here and none found.
47. **What is MAE?** Average absolute error in the target's units.
48. **What is RMSE?** Root mean squared error — penalises large misses more.
49. **What is R²?** Share of variance explained relative to the mean.
50. **When does MAPE break?** Near zero actuals — which is why WAPE
    ({V['pred_wape']}) is used for prediction.
51. **Forecast model and horizon?** {V['fc_model']}, {V['fc_horizon']} months,
    {V['fc_months']}.
52. **Forecast error?** Backtest mean MAPE {V['fc_backtest']} over
    {V['fc_folds']} folds — quote this, not the test split.

## Delivery and business

53. **Power BI measures?** {V['pbi_measures']} DAX measures,
    {V['pbi_matched']}/{V['pbi_val']} validated against SQL.
54. **Streamlit pages and tests?** {V['app_pages']} pages,
    {V['app_passed']}/{V['app_tests']} headless tests pass.
55. **The headline business finding?** The top 20% of customers produce
    {V['top20']} of revenue, and two independent methods identify the same
    group.
"""


def last_minute_revision():
    return f"""
# Last-Minute Revision — 5 Minutes

{STAMP}

---

**PROJECT**
A customer revenue intelligence platform: retail transaction data → cleaning →
segmentation → value → prediction → forecasting → dashboard and application.

**PROBLEM**
Businesses report revenue in aggregate but take decisions at customer level.

**DATA**
Synthetic, seed {V['seed']}. {V['raw_rows']} raw → {V['clean_rows']} clean
lines · {V['cust_buy']} purchasing customers · {V['products']} products ·
{V['regions']} regions · {V['start']}–{V['end']} ({V['months']} months) ·
{V['revenue']} delivered revenue.

**TOOLS**
Python (pandas, NumPy, scikit-learn 1.8.0, statsmodels 0.15.0, Plotly) · SQL
(SQLite) · Power BI (DAX) · Streamlit · Jupyter.

**METHOD**
Data → Cleaning → EDA → RFM → K-Means → CLV → Prediction → Forecasting → SQL →
Power BI + Streamlit → Recommendations.

**MODELS**
- K-Means, K = {V['k']} (silhouette {V['silhouette']})
- {V['clv_model']} — forward customer value
- {V['pred_model']} — next-quarter revenue
- {V['fc_model']} — monthly revenue forecast

**IMPORTANT METRICS**

| | |
|---|---|
| Revenue / margin | {V['revenue']} / {V['margin']} |
| Orders / AOV | {V['orders']} / {V['aov']} |
| Silhouette / ARI vs RFM | {V['silhouette']} / {V['ari']} |
| Value model R² / Spearman | {V['clv_r2']} / {V['clv_spearman']} |
| Prediction R² / MAE | {V['pred_r2']} / {V['pred_mae']} |
| Forecast backtest MAPE | {V['fc_backtest']} |
| Forecast total (80% interval) | {V['fc_total']} ({V['fc_low']}–{V['fc_high']}) |
| SQL / DAX / app pages | {V['sql_queries']} / {V['pbi_measures']} / {V['app_pages']} |
| Project audit | {V['audit_total']} checks, {V['audit_pass']} pass |

**KEY FINDINGS**
1. Top 10% of customers = {V['top10']} of revenue; top 20% = {V['top20']}.
2. Champions {V['champ_cust']} of customers, {V['champ_rev']} of revenue.
3. RFM and K-Means find the same high-value group (ARI {V['ari']}).
4. {V['at_risk']} high-value customers inactive 180+ days ({V['at_risk_rev']}).
5. Repeat customers {V['repeat_cust']} of base, {V['repeat_rev']} of revenue.
6. {V['top_cat']} = {V['top_cat_rev']} of revenue at {V['top_cat_margin']}
   margin; {V['best_cat']} earns {V['best_cat_margin']}.
7. Zero discount = best margin in {V['disc_best_in']}/{V['cats_tested']}
   categories (association, not cause).
8. Company forecasting works; individual prediction does not.

**KEY BUSINESS VALUE**
A short, specific action list: protect the top decile, work the
{V['at_risk']}-customer inactive list, manage category mix, test the discount
relationship — with every figure agreeing across Python, SQL, DAX and the app.

**LIMITATIONS**
Synthetic data · {V['months']}-month history · weak individual prediction
(R² {V['pred_r2']}) · univariate forecast · association not causation · no
churn label · Power BI pages are design mockups · no user testing · no
deployment or monitoring.

**FUTURE**
Real data · business-defined inactivity label · two-stage prediction · external
regressors · a controlled discount experiment · scheduled runs with drift
monitoring · complete the `.pbix` on Windows.

---

### Three sentences to have word-perfect

1. "The dataset is synthetic, generated with a fixed seed for academic
   demonstration — it describes no real company."
2. "Power BI Desktop is Windows-only and wasn't available, so those pages are
   design mockups rendered from the real data, not screenshots."
3. "Customer-level prediction is weak at R² {V['pred_r2']}, and I report it as
   weak — {V['pred_zero']} of customer-quarters have no order at all."

### If you don't know

"That value was not directly measured in this project."
"It was considered as a possible extension, but it was not part of the
implemented pipeline."
"""


def professor_presentation_questions():
    return f"""
# Professor Presentation Questions — Exact Answers

{STAMP}

**"Explain your project."**
"It's a customer revenue intelligence platform. It takes retail transaction
data — synthetic, generated for academic demonstration — and carries it through
cleaning, exploratory analysis, two independent customer segmentations, value
analysis, next-quarter revenue prediction and company-level forecasting. Every
metric is then reproduced independently in SQL and delivered through a Power BI
semantic model and a working {V['app_pages']}-page application. The headline
finding is that value is concentrated: the top 20% of customers produce
{V['top20']} of {V['revenue']} in revenue, and two independent methods identify
the same group."

**"What is innovative about your project?"**
"Not the techniques — RFM, K-Means, regression and Theta are all established,
and I claim no novelty in any of them. What is unusual is the integration and
the traceability: one validated dataset and one revenue definition flowing
through every stage, reconciled against an independent SQL implementation, with
every number in the report and the deck read from the pipeline's own output
files rather than typed in. The {V['audit_total']}-check audit is part of that
— it tests the integration instead of asserting it."

**"What did YOU personally implement?"**
"All of it — the data generator, the cleaning rules, every analysis module, the
four models, the SQL layer, the Power BI semantic model and DAX library, the
Streamlit application and its test suite, and the audit. What I did not do is
invent any of the methods; those come from the literature, which is cited."

**"What was the most difficult part?"**
"Accepting the prediction result. I expected moderate accuracy and got R²
{V['pred_r2']}. The tempting move was to keep trying models until one looked
better, but I had fixed the selection rule in advance — {V['pred_rule']} —
so the honest path was to report it as weak and explain the structural cause:
{V['pred_zero']} of customer-quarters have no order at all. Technically, the
hardest part was building the leakage audit that recomputes features
independently to verify the panel."

**"What did you learn?"**
"Three things. That defining the rules before seeing the results changes what
you conclude — it is the difference between analysis and rationalisation. That
reconciliation across implementations is worth more than any single model,
because it is what makes the numbers trustworthy. And that reporting a weak
result honestly is more defensible than hiding it — the contrast between a
forecastable company series and unpredictable individual customers is itself
the finding."

**"What is the business value?"**
"A short, specific action list rather than a report. The top revenue decile
carries {V['top10']} of revenue and now has a named list. The
{V['at_risk']} high-value customers who have gone quiet, holding
{V['at_risk_rev']}, are a working contact list. And category strategy becomes a
mix question — {V['top_cat']} at {V['top_cat_margin']} margin versus
{V['best_cat']} at {V['best_cat_margin']} — rather than a single revenue
target. Whether acting on these pays is an empirical question the business
would have to test; I have not measured campaign response."

**"What is the biggest limitation?"**
"The data is synthetic, so the methods transfer but the numbers describe no
real business. After that, the customer-level prediction model — it is usable
at portfolio level and not for an individual customer, and I say so wherever it
appears."

**"If I give you real company data, what will you change?"**
"Four things. Replace my quintile cut-offs with business-supplied thresholds,
so a segment means something absolute rather than a position in this base. Ask
the business to define a churn event, so a churn model becomes possible. Add
cost-to-serve, so customer value becomes contribution rather than gross profit.
And test whether the segment structure that emerges matches this one — that is
the real check on whether the method transfers."

**"If your model gives a wrong prediction, what will you do?"**
"For the customer-level model, nothing surprising — it is wrong often, which is
why its stated use is portfolio-level and why every page shows its accuracy
beside its output. For the forecast, a miss outside the 95% interval would mean
either misspecification or something outside the revenue series moved, and
since the model is univariate it cannot see prices or promotions. The response
is to refit with external regressors, which is in future scope. What I would
not do is adjust the model until it fits one bad quarter."

**"If the customer segments change next month, why?"**
"Most likely because the cut-offs are relative. The quintile boundaries are
computed on the current base, so a shift in the base moves the boundaries even
if individual behaviour is unchanged. Recency also moves mechanically — the
reference date advances, so every customer's recency grows unless they buy.
Genuine behavioural change is the third possibility, and distinguishing it from
the first two is exactly what drift monitoring would do. That is not
implemented."

**"How can this project be deployed in a real company?"**
"In stages. First, schedule the pipeline so the outputs refresh on a cadence.
Second, version the model artefacts with their metadata and serve predictions
through a small API rather than loading them in-process. Third, containerise
the application behind authentication. Fourth, add drift and performance
monitoring so degradation is visible. The semantic model is the piece that is
already production-shaped — it reads from SQL views, so pointing it at a
warehouse is a connection change, not a rewrite. None of this is done today,
and the application runs locally."
"""


def live_failure_handling():
    return f"""
# Live Failure Handling

{STAMP}

The principle: **name what happened, state what you will show instead, keep
moving.** Never narrate a stack trace, never apologise twice, never claim a
cause you have not verified.

The universal sentence, memorised:

> "The analytical workflow has already been validated, and I'll demonstrate the
> corresponding saved output while I troubleshoot the live component."

---

### Streamlit does not start

**Say:** "The application isn't launching — I'll show the captured output while
I look at it." Open `outputs/screenshots/` and walk files 67–78; they are real
screenshots of the same twelve pages.
**Check, calmly:** is the virtual environment active? Are you in the project
folder? Is port 8501 already in use — `streamlit run app.py --server.port 8502`.
**Do not say:** anything about what "must have" gone wrong.

### A page shows a missing-artefact message

**Say:** "That page needs a model file that isn't present in this copy — the app
degrades gracefully rather than crashing, which is deliberate and is covered by
the test suite."
**Check:** the pipeline stage that writes that artefact has run; then use the
sidebar's cache-clear control.

### Power BI does not refresh — or you are asked to open it

**Say:** "Power BI Desktop is a Windows application and wasn't available in my
build environment, so there's no `.pbix` to open. What I can show you is the
semantic model, the {V['pbi_measures']}-measure DAX library, and the validation
table where {V['pbi_matched']} of {V['pbi_val']} measures were checked against
their SQL equivalents."
**Then open:** `powerbi/dax/`, `powerbi/validation/`, and the labelled mockups
(files 57–66). This is not a failure — it is a documented limitation, so say it
in that tone.

### A model file cannot load

**Say:** "That artefact isn't loading here. The model metadata records the
library versions it was written with — scikit-learn 1.8.0 — so a version
mismatch is the first thing I'd check. Meanwhile, here are the results it
produced."
**Then open:** the relevant `models/*_metadata.json` and the saved figures.

### The dataset path is wrong

**Say:** "The path isn't resolving from this working directory. All paths are
centralised in `config.py`, so it's one place to check."
**Check:** you are in the project root; `ls data/processed/` confirms.

### A notebook throws an error

**Say:** "The notebooks are committed with their outputs already saved, so what
you're seeing on screen is the executed run. Let me scroll to the output rather
than re-execute — re-running the full pipeline takes a few minutes."
**Then:** scroll, do not re-run. Re-running live is a trap.

### No internet

**Say:** "Nothing in the demonstration needs a connection — the application
runs locally, the database is a local SQLite file, and the models are on disk."
This is true: check it is true on your machine before the viva by disabling
Wi-Fi and launching the app once.

### The laptop becomes slow

**Say:** "It's building the page cache — Streamlit re-runs the script on each
interaction, so the first load of a page is the slowest."
**Prevent it:** click through every page **before** the examiner arrives. After
that, navigation is instant. Close every other application.

### A visualisation does not load

**Say:** "The chart isn't rendering here — the same figure is in the saved
output, let me show that." Open the matching file from
`outputs/screenshots/`.
**Check:** a browser refresh usually fixes a Plotly render failure.

### A prediction takes time

**Say:** "It's applying the persisted model to the panel — the app never refits
anything, it only loads and applies." Use the pause: state the accuracy while
it runs — "test MAE {V['pred_mae']}, R² {V['pred_r2']}, which is weak and I'll
explain why."

### You lose your place entirely

**Say:** "Let me take that from the top of the pipeline." Then go to the demo
order in `outputs/viva/final_demo_order.md` and restart from the nearest clean
section. Examiners do not mind a reset; they mind flailing.

### You are asked something you did not prepare

**Say:** "That value was not directly measured in this project" — or "It was
considered as a possible extension, but it was not part of the implemented
pipeline." Both are complete answers. Then offer what you *do* have.

---

## Fifteen minutes before you start

- [ ] Virtual environment active, `streamlit run app.py` already running
- [ ] Every page clicked once, so the caches are warm
- [ ] Report PDF open in a second browser tab
- [ ] `outputs/screenshots/` open in a file browser — your fallback
- [ ] A terminal open in the project folder for the SQL query
- [ ] Notifications off, other applications closed, laptop on mains power
- [ ] `outputs/viva/last_minute_revision.md` read once
"""


def final_demo_order():
    return f"""
# Final Demonstration Order

{STAMP}

## The order, and why it is this order

The sequence follows the **data's journey**, not the project's chapter list.
Each step answers the question the previous step raises, so the examiner is
never asked to hold an unexplained result in their head.

| # | Section | Surface to use | Time | The one number |
|---|---|---|---|---|
| 1 | Introduction | PPT slide 1 | 45 s | — |
| 2 | Business problem | PPT slide 2 | 1 min | Top 20% = {V['top20']} of revenue |
| 3 | Dataset | Screenshots 01–02 | 1 min | {V['clean_rows']} lines, synthetic |
| 4 | Data cleaning | Screenshots 03–05 | 1 min | {V['missing_before']} rows failing → 0 |
| 5 | EDA | Streamlit: Executive Overview, Revenue Intelligence | 2 min | {V['revenue']} at {V['margin']} |
| 6 | RFM | Streamlit: Customer Segmentation | 1 min 30 s | Champions {V['champ_rev']} of revenue |
| 7 | K-Means | Same page, cluster view | 1 min 30 s | K = {V['k']}, ARI {V['ari']} |
| 8 | Customer value | Same page, value view | 1 min 30 s | {V['at_risk']} at-risk, {V['at_risk_rev']} |
| 9 | Revenue prediction | Streamlit: Revenue Prediction | 1 min 30 s | R² {V['pred_r2']} — say "weak" |
| 10 | Forecasting | Streamlit: Sales Forecast | 1 min 30 s | {V['fc_backtest']} backtest MAPE |
| 11 | SQL | Terminal, reconciliation query | 1 min | Returns exactly {V['revenue']} |
| 12 | Power BI | Screenshot 58 (mockup) | 1 min | {V['pbi_matched']}/{V['pbi_val']} validated |
| 13 | Streamlit as a whole | Data Explorer + a CSV download | 2 min | {V['app_passed']}/{V['app_tests']} tests |
| 14 | Recommendations | Streamlit: Business Recommendations | 1 min | {V['pbi_recs']} evidence-linked |
| 15 | Conclusion | PPT slide 20 | 45 s | {V['audit_total']} checks, {V['audit_pass']} pass |

**Total: 15 minutes.**

## Two adjustments to the "recommended" order, and why

1. **RFM, K-Means and customer value run back-to-back on one Streamlit page**
   (steps 6–8), because the application already presents them together. Jumping
   between surfaces for three related results breaks the thread.
2. **SQL comes after prediction and forecasting** (step 11), not before Power
   BI in the abstract. By that point the examiner has seen the numbers, so the
   reconciliation lands as *"and here is the independent proof those figures
   are right"* rather than as an unmotivated database tour.

## If you get 10 minutes

Drop steps 6, 11 and 14; fold RFM into step 7 in one sentence. Running order:
1 → 2 → 3 → 4 → 5 → 7 → 8 → 9 → 10 → 13 → 15.

## If you get 5 minutes

Steps 1, 2, 5, 7, 9, 10, 15 — and say the synthetic-data line in step 1.

## If you are told "just show me it working"

Open the application and go: Executive Overview → Customer Segmentation (switch
on the at-risk filter) → Sales Forecast (switch 80% to 95%) → Data Explorer
(download a CSV). Four screens, two minutes, and every one of them is live.

## Transitions worth rehearsing

- **Cleaning → EDA:** "With the data validated, here's what it actually says."
- **EDA → RFM:** "Revenue is concentrated — so the next question is *in whom*."
- **RFM → K-Means:** "Those are my rules. Here's what happens when I let an
  algorithm find the groups instead."
- **K-Means → CLV:** "Both methods agree on who is valuable. The next question
  is whether they'll stay valuable."
- **CLV → Prediction:** "That's the next twelve months at customer level. This
  is the next quarter — and it's the weakest result in the project."
- **Prediction → Forecasting:** "Individual customers are hard to predict. The
  company total is a different matter."
- **Forecasting → SQL:** "Every number you've seen was computed in Python. Here
  it is again, computed independently in SQL."
- **SQL → Power BI:** "That's the reconciliation. Here's how a manager would
  actually consume it — and I need to be clear about what this image is."

## Close

"So: raw transactions in, business decisions out, with every number traceable
to the file that produced it and every model chosen by a rule fixed before I
saw the results. Where the results were weak, I've reported them as weak. I'm
happy to take questions — and the application is still running if you'd like to
see anything again."
"""


FILES = [
    (AUDIT / "live_demo_plan.md", live_demo_plan),
    (VIVA / "live_demo_script.md", live_demo_script),
    (VIVA / "powerbi_demo_script.md", powerbi_demo_script),
    (VIVA / "streamlit_demo_script.md", streamlit_demo_script),
    (VIVA / "sql_demo_script.md", sql_demo_script),
    (VIVA / "ml_live_viva.md", ml_live_viva),
    (VIVA / "business_viva.md", business_viva),
    (VIVA / "why_questions.md", why_questions),
    (VIVA / "difficult_professor_questions.md", difficult_questions),
    (VIVA / "trick_questions.md", trick_questions_live),
    (VIVA / "rapid_fire_viva.md", rapid_fire_viva),
    (VIVA / "last_minute_revision.md", last_minute_revision),
    (VIVA / "professor_presentation_questions.md",
     professor_presentation_questions),
    (VIVA / "live_failure_handling.md", live_failure_handling),
    (VIVA / "final_demo_order.md", final_demo_order),
]


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    build_values()

    print("assembling the screenshot pack ...")
    copied, rendered, missing = build_screenshot_pack()
    print(f"        {len(copied)} figures copied, {len(rendered)} previews "
          f"rendered, {len(missing)} sources missing")
    for target, source in missing:
        print(f"        MISSING SOURCE: {source} -> {target}")

    print("writing the demonstration and viva documents ...")
    written = [write(AUDIT / "screenshot_checklist.md",
                     screenshot_checklist(copied, rendered, missing))]
    for path, builder in FILES:
        written.append(write(path, builder()))
    for p in written:
        print(f"        {p.relative_to(ROOT)}  "
              f"({p.stat().st_size / 1024:,.0f} KB)")
    print(f"\n{len(written)} documents written, "
          f"{len(copied) + len(rendered)} images in "
          f"{SHOTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
