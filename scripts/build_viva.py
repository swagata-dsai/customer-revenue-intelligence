"""
build_viva.py - Step 16: build the viva preparation pack.

Every figure quoted in the viva material is read at build time from
outputs/tables/report_facts.json - the same fact pack the report and the
presentation use - so the answers cannot drift from the project.

Usage
-----
    python scripts/build_viva.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
OUT = ROOT / "outputs" / "viva"

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
    """Pre-format every number the viva answers quote."""
    d, kpi, q = F["dataset"], F["kpi"], F["quality"]
    eda, rfm, km = F["eda"], F["rfm"], F["kmeans"]
    clv, pred, fc = F["clv"], F["prediction"], F["forecast"]
    sq, pb, stl = F["sql"], F["powerbi"], F["streamlit"]
    au, code = F["audit"], F["code"]
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    at_risk = row_by(rfm["summary"], "RFM_Segment", "At Risk")
    cant_lose = row_by(rfm["summary"], "RFM_Segment", "Can't Lose Them")
    lost = row_by(rfm["summary"], "RFM_Segment", "Lost")
    loyal = row_by(rfm["summary"], "RFM_Segment", "Loyal Customers")
    hv = km["summary"][0]
    cat = eda["by_category"]
    best_margin = max(cat, key=lambda c: c["profit_margin_pct"])
    reg = eda["by_region"]
    best_reg_margin = max(reg, key=lambda r: r["profit_margin_pct"])
    rep = row_by(eda["repeat"], "customer_group", "Repeat (2+ orders)")
    single = [r for r in eda["repeat"]
              if r["customer_group"] != rep["customer_group"]][0]
    y = eda["by_year"]
    disc = eda["discount_bands"]
    ari = row_by(km["agreement"],
                 "Measure", "Adjusted Rand Index (RFM segment vs cluster)")

    V.update({
        # dataset
        "raw_rows": n(d["raw_rows"]), "raw_cols": d["raw_cols"],
        "clean_rows": n(d["clean_rows"]), "clean_cols": d["clean_cols"],
        "dupes": n(d["duplicates_removed"]),
        "cust_reg": n(d["customers_registered"]),
        "cust_buy": n(d["customers_purchasing"]),
        "products": d["products"], "categories": d["categories"],
        "subcats": d["sub_categories"], "cities": d["cities"],
        "states": d["states"], "regions": d["regions"],
        "region_names": ", ".join(d["region_names"]),
        "cat_names": ", ".join(d["category_names"]),
        "start": d["start"], "end": d["end"], "months": d["months"],
        "orders_all": n(d["orders_all"]), "seed": d["seed"],
        "delivered_lines": n(d["statuses"]["Delivered"]),
        "returned_lines": n(d["statuses"]["Returned"]),
        "cancelled_lines": n(d["statuses"]["Cancelled"]),
        "missing_before": n(q["missing_before"]),
        # KPIs
        "revenue": cr(kpi["revenue"]), "revenue_exact": rs(kpi["revenue"], 2),
        "profit": cr(kpi["profit"]), "cost": cr(kpi["cost"]),
        "margin": pcf(kpi["margin"]), "orders": n(kpi["orders"]),
        "units": n(kpi["units"]), "aov": rs(kpi["aov"], 2),
        "rev_per_cust": rs(kpi["revenue_per_customer"]),
        "profit_per_order": rs(kpi["profit_per_order"]),
        "booked": cr(kpi["booked"]), "lost_value": lakh(kpi["lost"]),
        "lost_share": pcf(kpi["lost_share"]),
        # EDA
        "rev_2023": cr(y[0]["revenue"]), "rev_2025": cr(y[-1]["revenue"]),
        "growth_2024": pc(y[1]["revenue_yoy_growth_pct"], 1),
        "growth_2025": pc(y[-1]["revenue_yoy_growth_pct"], 1),
        "margin_2023": pc(y[0]["profit_margin_pct"]),
        "margin_2025": pc(y[-1]["profit_margin_pct"]),
        "monthly_min": lakh(eda["monthly_min"]),
        "monthly_max": lakh(eda["monthly_max"]),
        "top1": pc(row_by(eda["concentration"], "top_pct", 1)["pct_of_revenue"]),
        "top10": pc(row_by(eda["concentration"], "top_pct", 10)["pct_of_revenue"]),
        "top20": pc(row_by(eda["concentration"], "top_pct", 20)["pct_of_revenue"]),
        "repeat_share_cust": pc(rep["pct_of_customers"], 2),
        "repeat_share_rev": pc(rep["pct_of_revenue"], 2),
        "repeat_avg": rs(rep["avg_revenue_per_customer"]),
        "single_avg": rs(single["avg_revenue_per_customer"]),
        "median_gap": n(eda["interpurchase"]["median_gap_days"]),
        "mean_gap": n(eda["interpurchase"]["mean_gap_days"], 1),
        "top_cat": cat[0]["category"],
        "top_cat_rev": pc(cat[0]["revenue_share_pct"]),
        "top_cat_profit": pc(cat[0]["profit_share_pct"]),
        "top_cat_margin": pc(cat[0]["profit_margin_pct"]),
        "best_margin_cat": best_margin["category"],
        "best_margin": pc(best_margin["profit_margin_pct"]),
        "top_region": reg[0]["region"],
        "top_region_share": pc(reg[0]["revenue_share_pct"]),
        "small_region": reg[-1]["region"],
        "small_region_share": pc(reg[-1]["revenue_share_pct"]),
        "best_margin_region": best_reg_margin["region"],
        "best_region_margin": pc(best_reg_margin["profit_margin_pct"]),
        "region_pairs": eda["region_category_pairs"],
        "region_gaps": eda["region_category_gap"],
        "disc0_margin": pc(disc[0]["profit_margin_pct"]),
        "disc0_band": disc[0]["discount_band"],
        "disc_hi_margin": pc(disc[-1]["profit_margin_pct"]),
        "disc_hi_band": disc[-1]["discount_band"],
        "disc_best_in": eda["zero_discount_best_in"],
        "cats_tested": eda["categories_tested"],
        "flagged_products": eda["products_flagged"],
        # RFM
        "ref_date": rfm["reference_date"],
        "rfm_scored": n(rfm["customers_scored"]),
        "rfm_excluded": rfm["metadata"]["customers_excluded_no_delivered_purchase"],
        "rfm_segments": rfm["segments"],
        "champ_n": n(champ["Customer_Count"]),
        "champ_cust_pct": pc(champ["Customer_%"], 2),
        "champ_rev_pct": pc(champ["Revenue_%"], 2),
        "champ_recency": n(champ["Average_Recency"], 1),
        "champ_freq": n(champ["Average_Frequency"], 2),
        "champ_monetary": rs(champ["Average_Monetary"]),
        "loyal_n": n(loyal["Customer_Count"]),
        "loyal_rev_pct": pc(loyal["Revenue_%"], 2),
        "atrisk_n": n(at_risk["Customer_Count"]),
        "atrisk_rev_pct": pc(at_risk["Revenue_%"], 2),
        "cantlose_n": n(cant_lose["Customer_Count"]),
        "cantlose_rev_pct": pc(cant_lose["Revenue_%"], 2),
        "lost_n": n(lost["Customer_Count"]),
        "lost_rev_pct": pc(lost["Revenue_%"], 2),
        "median_recency": n(rfm["median_recency"]),
        "median_monetary": rs(rfm["median_monetary"]),
        # K-Means
        "k": km["k"], "silhouette": f"{km['overall_silhouette']:.4f}",
        "inertia": n(row_by(km["k_evaluation"], "k", km["k"])["inertia"], 3),
        "ch": n(row_by(km["k_evaluation"], "k", km["k"])["calinski_harabasz"], 1),
        "db": f"{row_by(km['k_evaluation'], 'k', km['k'])['davies_bouldin']:.3f}",
        "ari_stability": f"{row_by(km['k_evaluation'], 'k', km['k'])['stability_ari_mean']:.2f}",
        "min_k": km["selection_rules"]["min_k"],
        "min_share": pcf(km["selection_rules"]["min_cluster_share"], 0),
        "min_ari": f"{km['selection_rules']['min_stability_ari']:.2f}",
        "pc1": pc(km["pca"][0]["Explained_Variance_%"], 2),
        "pc2": pc(km["pca"][1]["Explained_Variance_%"], 2),
        "pca_total": pc(km["pca"][0]["Explained_Variance_%"]
                        + km["pca"][1]["Explained_Variance_%"], 2),
        "ari_vs_rfm": f"{ari['Value']:.4f}",
        "hv_label": hv["Business_Label"], "hv_n": n(hv["Customer_Count"]),
        "hv_cust_pct": pc(hv["Customer_%"], 2),
        "hv_rev_pct": pc(hv["Revenue_%"], 2),
        "cluster_sizes": ", ".join(
            f"{c['Cluster_ID']} {c['Business_Label']} {n(c['Customer_Count'])}"
            for c in km["summary"]),
        "preprocessing": km["metadata"]["preprocessing"],
        # CLV
        "clv_hist_profit": cr(clv["historical_profit_total"]),
        "clv_hist_rev": cr(clv["historical_revenue_total"]),
        "clv_mean": rs(clv["mean_historical_profit"]),
        "clv_median": rs(clv["median_historical_profit"]),
        "clv_model": clv["metadata"]["selected_model"],
        "clv_mae": rs(clv["metadata"]["validation"]["MAE"]),
        "clv_rmse": rs(clv["metadata"]["validation"]["RMSE"]),
        "clv_r2": f"{clv['metadata']['validation']['R2']:.4f}",
        "clv_spearman": f"{clv['metadata']['validation']['Spearman']:.4f}",
        "clv_top20": pc(clv["metadata"]["validation"]["Top20_Capture_%"], 2),
        "clv_features": ", ".join(clv["metadata"]["feature_order"]),
        "clv_train": clv["metadata"]["validation"]["train"],
        "clv_test": clv["metadata"]["validation"]["test"],
        "clv_by_model": n(clv["estimate_methods"]["ML model (active in last 12 months)"]),
        "clv_by_group": n(clv["estimate_methods"]["Group average (no order in last 12 months)"]),
        "clv_est_total": cr(clv["estimated_12m_total"]),
        "clv_at_risk": clv["at_risk"],
        "clv_at_risk_rev": lakh(clv["at_risk_revenue"]),
        "clv_top_driver": clv["feature_importance"][0]["Feature"],
        "clv_drivers": ", ".join(r["Feature"]
                                 for r in clv["feature_importance"][:4]),
        "bgnbd_calib": row_by(clv["bgnbd"], "Item",
                              "Calibration period")["Result"],
        # prediction
        "pred_model": pred["model"], "pred_target": pred["target"],
        "pred_unit": pred["unit"], "pred_features": pred["n_features"],
        "pred_numeric": len(pred["numeric_features"]),
        "pred_categorical": len(pred["categorical_features"]),
        "panel_rows": n(pred["panel_rows"]),
        "train_rows": n(pred["train_rows"]),
        "val_rows": n(pred["val_rows"]),
        "test_rows": n(pred["test_rows"]),
        "train_period": pred["train_period"],
        "val_period": pred["validation_period"],
        "test_period": pred["test_period"],
        "pred_mae": rs(pred["test_metrics"]["MAE"]),
        "pred_rmse": rs(pred["test_metrics"]["RMSE"]),
        "pred_r2": f"{pred['test_metrics']['R2']:.4f}",
        "pred_wape": pc(pred["test_metrics"]["WAPE_%"], 2),
        "pred_spearman": f"{pred['test_metrics']['Spearman']:.4f}",
        "pred_bias": pc(pred["test_metrics"]["Total_Bias_%"], 2),
        "pred_val_rmse": rs(pred["validation_metrics"]["RMSE"]),
        "pred_zero": pcf(pred["zero_actual_share"], 1),
        "pred_rule": pred["selection_rule"],
        "naive_mae": rs(pred["comparison"][0]["MAE"]),
        "naive_r2": f"{pred['comparison'][0]['R2']:.4f}",
        "pred_drivers": ", ".join(r["Feature"]
                                  for r in pred["importance"][:4]),
        # forecast
        "fc_model": fc["model"], "fc_horizon": fc["horizon"],
        "fc_months": f"{fc['months'][0]} to {fc['months'][-1]}",
        "fc_series": fc["series_months"],
        "fc_train": fc["split"]["train"], "fc_val": fc["split"]["validation"],
        "fc_test": fc["split"]["test"],
        "fc_test_mae": rs(fc["metrics"]["test"]["MAE"]),
        "fc_test_mape": pc(fc["metrics"]["test"]["MAPE_%"], 2),
        "fc_test_smape": pc(fc["metrics"]["test"]["sMAPE_%"], 2),
        "fc_backtest": pc(fc["metrics"]["backtest_mean_MAPE_%"], 2),
        "fc_folds": fc["backtest"][0]["Folds"],
        "fc_total": cr(fc["future_total"]),
        "fc_low80": cr(fc["future_lower80"]),
        "fc_high80": cr(fc["future_upper80"]),
        "fc_prev6": cr(fc["prev_6m_actual"]),
        "fc_alpha": f"{fc['parameters']['alpha']:.4f}",
        "adf_p": f"{fc['adf'][0]['p_value']:.4f}",
        "fc_rule": fc["selection_rule"],
        # SQL / BI / app
        "sql_tables": sq["tables"], "sql_views": sq["views"],
        "sql_queries": sq["queries"],
        "sql_analysis": sq["analysis_queries"],
        "sql_business": sq["business_queries"],
        "sql_checks": sq["validation_checks"],
        "sql_quality": sq["quality_checks"],
        "pbi_tables": pb["tables"], "pbi_rels": pb["relationships"],
        "pbi_measures": pb["measures"], "pbi_folders": pb["folders"],
        "pbi_val": pb["validation_rows"], "pbi_matched": pb["validation_matched"],
        "pbi_consistency": pb["consistency_total"],
        "pbi_recs": pb["recommendations"],
        "app_pages": stl["pages"], "app_tests": stl["tests"],
        "app_passed": stl["tests_passed"],
        # project
        "audit_total": au["total"], "audit_pass": au["passed"],
        "audit_fail": au["failed"],
        "py_files": code["python_files"], "py_lines": n(code["python_lines"]),
        "sql_files": code["sql_files"], "notebooks": code["notebooks"],
        "figures": code["figures"], "tables_out": code["tables"],
    })


def write(name: str, text: str):
    path = OUT / name
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


HEADER = """*Generated by `python scripts/build_viva.py` from the project's own
outputs. Every figure below is read from `outputs/tables/report_facts.json`,
the same fact pack used by the report and the presentation. The dataset is
synthetic and is described as such throughout.*"""


def master_summary():
    return f"""
# Project Master Summary

{HEADER}

## Project Title

**Customer Revenue Intelligence: An Interactive Data Science Platform for
Customer Segmentation, Revenue Prediction and Business Growth**

Summer internship project, MBA (Data Science and AI), Apex Institute of
Management, Chandigarh University. Internship carried out at Tutorsuite
Technologies LLP, Kolkata, 1st June to 12th July, under the guidance of
Kuldeep Dubey.

## Business Problem

Retail and e-commerce businesses record transaction data far faster than they
convert it into decisions. Revenue is reported in aggregate — by month, by
category, by region — while the questions that drive growth are customer-level
and forward-looking: which customers matter most, which are going quiet, what
each is likely to spend next quarter, and what total revenue the next two
quarters will bring. Four specific gaps follow: aggregate reporting hides the
customer; value and activity are treated as one thing; planning is
backward-looking; and analysis that lives in notebooks never reaches the
decision-maker.

## Problem Statement

Given a transaction dataset of order lines carrying customer, product,
geography, pricing, discount, cost and order-status attributes over a fixed
window, build one reproducible platform that cleans the records against
explicit business rules, characterises the revenue base, segments every
purchasing customer by two independent methods, separates measured historical
value from estimated forward value, predicts next-quarter customer revenue on
an out-of-time split, forecasts monthly company revenue with prediction
intervals, reconciles the principal metrics against an independent SQL
implementation, and delivers the results through a semantic model and an
interactive application.

The success criterion is not the accuracy of any single model. It is that the
outputs are complete, internally consistent, independently reconciled and
reproducible, and that every limitation is reported alongside the model.

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

All eleven were implemented.

## Dataset

The dataset is **synthetic**, generated by `scripts/generate_dataset.py` with
a fixed seed ({V['seed']}) for academic demonstration. It does not describe
any real company, customer or transaction, including the internship host
organisation.

| Property | Value |
| --- | --- |
| Raw extract | {V['raw_rows']} order lines, {V['raw_cols']} columns |
| Cleaned dataset | {V['clean_rows']} order lines, {V['clean_cols']} columns |
| Duplicates removed | {V['dupes']} |
| Customers | {V['cust_reg']} registered, {V['cust_buy']} with at least one delivered order |
| Products | {V['products']} in {V['categories']} categories ({V['cat_names']}) and {V['subcats']} sub-categories |
| Geography | {V['cities']} cities, {V['states']} states, {V['regions']} regions ({V['region_names']}) |
| Period | {V['start']} to {V['end']} ({V['months']} months) |
| Orders | {V['orders_all']} across all statuses |
| Order lines by status | {V['delivered_lines']} delivered, {V['returned_lines']} returned, {V['cancelled_lines']} cancelled |
| Privacy | Analytical outputs identify customers by `Customer_ID` only |

**One definition governs the whole project:** revenue, profit and order counts
are computed on *delivered* order lines only. Returned and cancelled lines are
retained and analysed separately as lost value.

## Data Preprocessing

Cleaning is rule-driven, not discretionary. Every rule is evaluated on the raw
extract, the count of offending rows is logged, a treatment is applied, and the
rule is re-evaluated on the cleaned dataset. {V['missing_before']} rows failed
at least one rule before treatment; **zero** rules fail after it. The cleaned
dataset carries {V['clean_cols']} columns, of which
{F['dataset']['clean_cols'] - F['dataset']['raw_cols']} are engineered:
calendar attributes, the delivered flag, revenue, profit and margin, discount
and age bands, 1.5×IQR outlier flags, and reconciliation checks confirming each
line's revenue equals its own price, quantity and discount.

Outliers are flagged and inspected, never removed: a large order from a genuine
high-value customer is a fact about the business, not an error.

## EDA

| Indicator | Value |
| --- | --- |
| Delivered revenue | {V['revenue']} ({V['revenue_exact']}) |
| Delivered profit | {V['profit']} |
| Profit margin | {V['margin']} |
| Delivered orders | {V['orders']} |
| Units sold | {V['units']} |
| Average order value | {V['aov']} |
| Revenue per customer | {V['rev_per_cust']} |
| Booked value (all statuses) | {V['booked']} |
| Value lost to returns and cancellations | {V['lost_value']} ({V['lost_share']} of booked) |

Revenue grew from {V['rev_2023']} in 2023 to {V['rev_2025']} in 2025
({V['growth_2024']} then {V['growth_2025']}) while margin rose from
{V['margin_2023']} to {V['margin_2025']} — growth is not being bought with
margin. Monthly revenue ranges from {V['monthly_min']} to {V['monthly_max']};
October is the highest month in all three years.

Value is concentrated: the top 1% of customers produce {V['top1']} of revenue,
the top 10% {V['top10']}, and the top 20% {V['top20']}. Repeat customers are
{V['repeat_share_cust']} of the base and {V['repeat_share_rev']} of revenue,
averaging {V['repeat_avg']} each against {V['single_avg']} for single-order
customers. The median gap between consecutive orders is {V['median_gap']} days.

{V['top_cat']} is the volume leader ({V['top_cat_rev']} of revenue,
{V['top_cat_profit']} of profit) at the lowest margin
({V['top_cat_margin']}); {V['best_margin_cat']} carries the highest margin at
{V['best_margin']}. Revenue is spread evenly across regions
({V['top_region']} {V['top_region_share']} down to {V['small_region']}
{V['small_region_share']}), and of {V['region_pairs']} region-category pairs
tested, {V['region_gaps']} sits more than two percentage points below the
national margin for its category. The {V['disc0_band']} discount band returns a
{V['disc0_margin']} margin against {V['disc_hi_margin']} in the
{V['disc_hi_band']} band, and is the best-margin band in {V['disc_best_in']} of
{V['cats_tested']} categories — an association, not a proven cause.

## RFM

Every customer with at least one delivered order is scored at the reference
date **{V['ref_date']}** (the latest order date plus one day). Recency is days
since the last delivered purchase; Frequency is the count of distinct orders
with at least one delivered line; Monetary is the sum of delivered sales.

Each dimension is scored 1–5 on quintiles (`pd.qcut`), with recency reversed so
a higher score is always better, falling back to a tie-aware percentile rank
where quintile edges are not unique. {V['rfm_scored']} customers are scored
({V['rfm_excluded']} are excluded for having no delivered purchase) and placed
into **{V['rfm_segments']}** named segments by fixed rules — Champions, for
example, requires R of 4–5 and a combined FM score of at least 4.5.

| Segment | Customers | % of base | % of revenue |
| --- | --- | --- | --- |
| Champions | {V['champ_n']} | {V['champ_cust_pct']} | {V['champ_rev_pct']} |
| Loyal Customers | {V['loyal_n']} | — | {V['loyal_rev_pct']} |
| At Risk | {V['atrisk_n']} | — | {V['atrisk_rev_pct']} |
| Can't Lose Them | {V['cantlose_n']} | — | {V['cantlose_rev_pct']} |
| Lost | {V['lost_n']} | — | {V['lost_rev_pct']} |

This stage is **rule-based, not machine learning**.

## K-Means

The same three behavioural variables are clustered without labels, as an
independent check on the rule-based scheme. Preprocessing is a persisted
scikit-learn pipeline: {V['preprocessing']}.

K was **not** chosen after inspecting results. Three rules were fixed in
advance — at least {V['min_k']} clusters, no cluster smaller than
{V['min_share']} of the base, and bootstrap stability ARI of at least
{V['min_ari']} — and among the eligible values the highest silhouette was taken.

| Diagnostic | Value |
| --- | --- |
| Selected K | {V['k']} |
| Silhouette | {V['silhouette']} |
| Inertia | {V['inertia']} |
| Calinski–Harabasz | {V['ch']} |
| Davies–Bouldin | {V['db']} |
| Bootstrap stability (mean ARI) | {V['ari_stability']} |
| PCA (visualisation only) | PC1 {V['pc1']} + PC2 {V['pc2']} = {V['pca_total']} |
| Agreement with RFM segments (ARI) | {V['ari_vs_rfm']} |

Clusters: {V['cluster_sizes']}. Cluster 0 ({V['hv_label']}) is
{V['hv_cust_pct']} of customers and {V['hv_rev_pct']} of revenue — the same
concentration the rule-based scheme found by a different route.

## CLV

Two quantities, kept separate throughout:

**Historical value (measured):** {V['clv_hist_profit']} of delivered profit on
{V['clv_hist_rev']} of revenue; mean {V['clv_mean']}, median {V['clv_median']}
per customer.

**Estimated forward value (predicted):** a supervised model trained out of time
— features from {V['clv_train']}, tested on {V['clv_test']} — on eight
behavioural features ({V['clv_features']}), predicting delivered profit over
the next twelve months. A ridge baseline, a random forest, a gradient-boosted
ensemble, a naive "last-12-month profit repeats" baseline, a simplified
formula and a BG/NBD
variant were compared; the **{V['clv_model'].lower()}** was selected by the
rule fixed in advance (lowest mean 5-fold CV RMSE on the training cutoff).

| Metric | Value |
| --- | --- |
| MAE | {V['clv_mae']} |
| RMSE | {V['clv_rmse']} |
| R² | {V['clv_r2']} |
| Spearman ρ | {V['clv_spearman']} |
| Top-20% capture | {V['clv_top20']} |

The model ranks customers considerably better than it predicts their exact
value, so it is used as a prioritisation instrument, not as a promise of any
individual customer's spend. {V['clv_by_model']} customers were scored by the
model and {V['clv_by_group']} by group average (no order in the feature
window). Principal driver: {V['clv_top_driver']}; top drivers by permutation
importance: {V['clv_drivers']}. {V['clv_at_risk']} high-value customers are
flagged inactive for 180+ days, holding {V['clv_at_risk_rev']} of historical
revenue.

## Revenue Prediction

**Target:** {V['pred_target']}
**Unit:** {V['pred_unit']}

A panel of {V['panel_rows']} customer-quarter rows, each carrying
{V['pred_features']} features ({V['pred_numeric']} numeric,
{V['pred_categorical']} categorical) computed strictly from data available
before the target quarter began. Split is **out-of-time, not random**:
{V['train_rows']} train ({V['train_period']}), {V['val_rows']} validation
({V['val_period']}), {V['test_rows']} test ({V['test_period']}). A leakage
audit recomputes sampled feature rows directly from the transaction table to
confirm no post-cutoff information reaches the model.

Selected model: **{V['pred_model']}**, by the rule fixed in advance —
{V['pred_rule']}.

| Metric (test split) | Value |
| --- | --- |
| MAE | {V['pred_mae']} |
| RMSE | {V['pred_rmse']} |
| R² | {V['pred_r2']} |
| WAPE | {V['pred_wape']} |
| Spearman ρ | {V['pred_spearman']} |
| Total bias | {V['pred_bias']} |

The naive previous-quarter baseline gives MAE {V['naive_mae']} and R²
{V['naive_r2']}, so the model beats every baseline and is **still weak in
absolute terms**. The reason is structural: {V['pred_zero']} of
customer-quarters have a zero actual value, so the target is dominated by
whether a customer orders at all rather than by how much they spend. Top
drivers: {V['pred_drivers']}.

## Sales Forecasting

Company-level monthly delivered revenue over {V['fc_series']} months. The
series was characterised first: the ADF test on the level gives p =
{V['adf_p']}, so the null of a unit root is not rejected and the series is
treated as non-stationary in level.

Candidates: naive and seasonal naive baselines, exponential smoothing (ETS),
ARIMA/SARIMA and Theta. Selection rule fixed in advance: {V['fc_rule']}.
Selected: **{V['fc_model']}** (α = {V['fc_alpha']}).

| Metric | Value |
| --- | --- |
| Test MAE | {V['fc_test_mae']} |
| Test MAPE | {V['fc_test_mape']} |
| Test sMAPE | {V['fc_test_smape']} |
| Backtest mean MAPE ({V['fc_folds']} rolling-origin folds) | {V['fc_backtest']} |

The **backtest mean MAPE**, not the single-split test MAPE, is the figure this
project treats as the honest expectation.

Forecast: {V['fc_horizon']} months ({V['fc_months']}) totalling
{V['fc_total']}, 80% interval {V['fc_low80']} to {V['fc_high80']}, against
{V['fc_prev6']} delivered in the preceding six months. The forecast is
univariate — no price, promotion, holiday or macroeconomic input.

## SQL

A normalised SQLite database of {V['sql_tables']} tables and {V['sql_views']}
views, with primary and foreign keys enforced and indexes on join and filter
columns. {V['sql_queries']} analytical queries ({V['sql_analysis']} analysis +
{V['sql_business']} business) reproduce the principal metrics using window
functions, CTEs, self-joins and conditional aggregation. All
{V['sql_checks']} referential and business-rule checks and {V['sql_quality']}
data-quality checks pass.

This layer exists to be an **independent implementation**: the same definitions
written in a different language, so agreement with the Python pipeline is
evidence rather than tautology.

## Power BI

A star schema of {V['pbi_tables']} tables joined by {V['pbi_rels']}
single-direction relationships, with {V['pbi_measures']} DAX measures in
{V['pbi_folders']} display folders, a marked date dimension, Power Query M
scripts per table and a JSON theme. All {V['pbi_matched']}/{V['pbi_val']}
measure validations match their SQL equivalents and all
{V['pbi_consistency']} cross-surface consistency checks pass.
{V['pbi_recs']} recommendations are carried in the model.

**Power BI Desktop is a Windows application and was unavailable in the Linux
build environment.** The nine page layouts are design mockups rendered from the
real data and are labelled as such everywhere. No Power BI Desktop screenshot
is claimed.

## Streamlit

A working **{V['app_pages']}-page** application: Home, Executive Overview,
Revenue Intelligence, Customer Intelligence, Customer Segmentation, Product
Analytics, Regional Analytics, Revenue Prediction, Sales Forecast, Business
Recommendations, Data Explorer, About. It loads from the SQLite database where
available and falls back to the processed CSVs, caches data and model
artefacts, and loads the persisted `.pkl` models rather than refitting
anything. It computes no metric of its own. Tested headlessly:
{V['app_passed']}/{V['app_tests']} checks pass.

## Major Findings

1. Value is concentrated — top 10% of customers = {V['top10']} of revenue, top
   20% = {V['top20']}.
2. Champions are {V['champ_cust_pct']} of customers but {V['champ_rev_pct']} of
   revenue.
3. Two independent methods (RFM rules, K-Means) identify substantially the same
   high-value group; ARI {V['ari_vs_rfm']}.
4. {V['clv_at_risk']} high-value customers are inactive for 180+ days, holding
   {V['clv_at_risk_rev']} of historical revenue.
5. Repeat customers are {V['repeat_share_cust']} of the base and
   {V['repeat_share_rev']} of revenue.
6. The volume leader ({V['top_cat']}, {V['top_cat_margin']} margin) and the
   margin leader ({V['best_margin_cat']}, {V['best_margin']}) are different
   categories.
7. The zero-discount band is the best-margin band in {V['disc_best_in']} of
   {V['cats_tested']} categories.
8. Growth is not bought with margin: {V['growth_2024']} then
   {V['growth_2025']} growth with margin rising to {V['margin_2025']}.
9. There is no regional margin problem: {V['region_gaps']} of
   {V['region_pairs']} region-category pairs more than 2 pp below national.
10. Company-level forecasting is reliable ({V['fc_backtest']} backtest MAPE);
    individual customer prediction is weak (R² {V['pred_r2']}).

## Recommendations

{V['pbi_recs']} recommendations are generated from the pipeline's own outputs,
each carrying its evidence and analytical source. The principal ones:

| Finding | Implication | Recommendation |
| --- | --- | --- |
| Top 20% = {V['top20']} of revenue | Losing a few large customers costs more than a month of acquisition | Give the top decile a named owner; review monthly |
| {V['clv_at_risk']} high-value customers inactive 180+ days | Value already earned is quietly at risk | Work the list as a contact campaign; record the outcome |
| Champions {V['champ_cust_pct']} of customers, {V['champ_rev_pct']} of revenue | A small group carries the business | Protect and grow Champions before chasing new customers |
| Repeat customers {V['repeat_share_rev']} of revenue | The second order is where value is created | Target first-to-second order conversion |
| {V['top_cat']} {V['top_cat_margin']} margin vs {V['best_margin_cat']} {V['best_margin']} | Volume leader and margin leader are different assets | Manage category mix, not a single revenue target |
| Zero discount best margin in {V['disc_best_in']}/{V['cats_tested']} categories | Discounting is costing margin (association, not proven cause) | Run a controlled discount experiment before changing policy |

## Limitations

1. **Synthetic data.** Methods transfer; the numbers describe no real business.
2. **Short history.** {V['months']} months supports trend analysis but is thin
   for seasonal estimation.
3. **Weak individual prediction.** R² {V['pred_r2']}; usable at portfolio
   level, not per customer.
4. **Univariate forecast.** No price, promotion or holiday input.
5. **Association, not causation.** Every relationship is measured on observed
   orders.
6. **No churn label.** The dataset defines no churn event, so the project
   reports inactivity and never churn.
7. **Power BI not rendered in Desktop.** Model and measures complete and
   validated; page layouts are design mockups.
8. **No user testing** of the dashboard or application.
9. **No production deployment**, no scheduled re-runs, no drift monitoring.

## Future Scope

Validate on real transaction data under a data-protection agreement; define an
operational inactivity label and build a supervised model against it; reframe
next-quarter prediction as a two-stage problem (will they order, and if so how
much); extend the forecast with external regressors; run a controlled discount
experiment; operationalise with scheduled re-runs, drift monitoring and
performance tracking; complete the Power BI build on Windows from the supplied
semantic model and build guide.

## Technologies Used

**Python 3.11** — pandas, NumPy, SciPy, scikit-learn 1.8.0, statsmodels 0.15.0,
joblib, Matplotlib, Seaborn, Plotly.
**SQL** — SQLite ({V['sql_tables']} tables, {V['sql_views']} views,
{V['sql_queries']} queries).
**Power BI** — star schema, DAX ({V['pbi_measures']} measures), Power Query M.
**Streamlit** — {V['app_pages']}-page application.
**Jupyter** — {V['notebooks']} executed notebooks.
**Project size** — {V['py_files']} Python modules ({V['py_lines']} lines),
{V['sql_files']} SQL files, {V['figures']} figures, {V['tables_out']} output
tables; audited by {V['audit_total']} automated checks ({V['audit_pass']}
pass, {V['audit_fail']} fail).
"""


def basic_questions():
    return f"""
# 01 — Basic Viva Questions

{HEADER}

**1. What is your project about?**
It is a customer revenue intelligence platform. It takes raw retail
transaction data and carries it through cleaning, exploratory analysis,
customer segmentation, customer value analysis, revenue prediction and
forecasting, and delivers the results through a Power BI semantic model and a
{V['app_pages']}-page Streamlit application. The dataset is synthetic,
generated for academic demonstration.

**2. Why did you select this topic?**
Because businesses report revenue in aggregate but take decisions at customer
level. I wanted to build the full chain — from a raw transaction file to a
recommendation a manager can act on — rather than a single model in a
notebook, and to do it so that every number is reproducible.

**3. What is Customer Revenue Intelligence?**
It is the practice of converting transaction records into customer-level
understanding and then into forward-looking decisions: who the customer is,
what they are worth, what they are likely to do next, and what that means for
revenue planning.

**4. What is the main business problem?**
Aggregate reporting hides the customer. It cannot distinguish a month carried
by a few large customers from one built on a broad base, it treats value and
activity as one thing, and it gives no forward view — so it cannot guide
retention effort or planning.

**5. What are the objectives?**
Eleven, all implemented: validate and clean the data; exploratory analysis;
RFM scoring; K-Means segmentation; customer value analysis; revenue
prediction; forecasting; independent SQL analytics; a Power BI semantic model;
a Streamlit application; and evidence-linked recommendations.

**6. What type of dataset did you use?**
A **synthetic** e-commerce transaction dataset generated with a fixed seed
({V['seed']}): {V['raw_rows']} raw order lines cleaning to {V['clean_rows']}
validated lines, {V['cust_buy']} purchasing customers, {V['products']}
products in {V['categories']} categories, {V['regions']} regions, covering
{V['start']} to {V['end']} — {V['months']} months.

**7. Why was data preprocessing required?**
The generator deliberately injects the defects a real extract carries: missing
values, non-ISO dates, numbers stored as text, out-of-range discounts, invalid
category labels and duplicate rows. {V['missing_before']} rows failed at least
one business rule before treatment; after cleaning, zero rules fail.

**8. What is EDA?**
Exploratory data analysis: examining distributions, trends, relationships and
outliers to understand the data's structure and quality before modelling,
rather than jumping straight to a model.

**9. Why did you perform EDA?**
To establish the baseline facts the rest of the project builds on — that
revenue is {V['revenue']} at {V['margin']} margin, that the top 20% of
customers produce {V['top20']} of revenue, and that the volume leader and the
margin leader are different categories. It also decided which features were
worth engineering.

**10. What is RFM?**
A behavioural scoring method: each customer is scored on **R**ecency (how
recently they bought), **F**requency (how often) and **M**onetary value (how
much), and the combined score places them in a named segment.

**11. What is Recency?**
Days between the reference date ({V['ref_date']}) and the customer's last
delivered purchase. Lower is better, so the recency score is reversed.

**12. What is Frequency?**
The count of distinct orders with at least one delivered line. Higher is
better.

**13. What is Monetary value?**
The sum of delivered sales in rupees for that customer, after discount.

**14. Why did you use RFM?**
Because it is interpretable and auditable — a business user can see exactly
why a customer landed in a segment — and because recency, frequency and
monetary value carry most of the information needed to rank a customer base.
It is also a rule-based benchmark against which the machine-learning
segmentation can be compared.

**15. What is customer segmentation?**
Dividing the customer base into groups that behave similarly, so that each
group can be managed with a different action rather than treating all
customers alike.

**16. What is K-Means?**
An unsupervised clustering algorithm. It places K centroids, assigns each
point to its nearest centroid, recomputes the centroids as the mean of their
members, and repeats until the assignment stops changing — minimising
within-cluster variance.

**17. Why was K-Means used?**
As an independent check on the rule-based RFM scheme. RFM imposes boundaries I
chose; K-Means finds whatever grouping is actually in the data. The two agree
substantially on the high-value group (ARI {V['ari_vs_rfm']}), which is
stronger evidence than either alone.

**18. What is CLV?**
Customer lifetime value — the total value a customer represents. In this
project it is reported as two separate quantities: **historical** value
({V['clv_hist_profit']} of delivered profit already earned) and **estimated
forward** value (a modelled estimate of the next twelve months' profit). They
are never added together.

**19. What is revenue prediction?**
A supervised regression problem at customer level: given what a customer did
before a cutoff, predict their delivered revenue in the following quarter. In
this project, {V['pred_model']} on {V['pred_features']} features, test R²
{V['pred_r2']}.

**20. What is forecasting?**
A time-series problem at company level: given {V['fc_series']} months of
monthly revenue, project the next {V['fc_horizon']} months with prediction
intervals. Model: {V['fc_model']}, backtest MAPE {V['fc_backtest']}.

**21. What is SQL used for in this project?**
Two things. It stores the cleaned data in a normalised database of
{V['sql_tables']} tables and {V['sql_views']} views, and it independently
reproduces the principal metrics through {V['sql_queries']} analytical
queries, so the Python results can be reconciled against a second
implementation.

**22. Why Power BI?**
Because a business audience needs a self-service semantic model, not a
notebook. The star schema of {V['pbi_tables']} tables and
{V['pbi_measures']} DAX measures lets a manager slice revenue by date,
region, category or segment without asking an analyst. Every measure was
validated against its SQL equivalent ({V['pbi_matched']}/{V['pbi_val']}
match).

**23. Why Streamlit?**
Because the project needed a *working application*, not only a dashboard — one
that loads the actual trained models, runs predictions, lets a user upload a
file and download results. Streamlit does that in Python, so the application
reuses the pipeline's own modules rather than reimplementing them.

**24. What are the major findings?**
Value is concentrated (top 20% = {V['top20']} of revenue); Champions are
{V['champ_cust_pct']} of customers but {V['champ_rev_pct']} of revenue; two
independent methods find the same high-value group; {V['clv_at_risk']}
high-value customers are inactive for 180+ days; the volume leader and margin
leader are different categories; and company-level forecasting is reliable
({V['fc_backtest']} backtest MAPE) while individual customer prediction is
weak (R² {V['pred_r2']}).

**25. What are the limitations?**
Synthetic data; a short {V['months']}-month history; weak individual-level
prediction; a univariate forecast; association not causation; no churn label
in the data; Power BI Desktop unavailable so its pages are design mockups; no
user testing; and no production deployment or monitoring.

**26. Which technologies did you use?**
Python 3.11 (pandas, NumPy, scikit-learn 1.8.0, statsmodels 0.15.0, Plotly,
Matplotlib), SQLite, DAX/Power Query for Power BI, Streamlit, and Jupyter for
the {V['notebooks']} notebooks.

**27. How large is the project?**
{V['py_files']} Python modules ({V['py_lines']} lines), {V['sql_files']} SQL
files, {V['notebooks']} executed notebooks, {V['figures']} figures and
{V['tables_out']} output tables, with an automated audit of
{V['audit_total']} checks ({V['audit_pass']} pass, {V['audit_fail']} fail).

**28. Is your project reproducible?**
Yes. The dataset is generated from seed {V['seed']}, every stage has a single
entry point, each stage reads only the persisted output of the one before it,
and re-running produces identical checksums. The audit script verifies this.

**29. What does "delivered revenue" mean and why does it matter?**
Revenue, profit and order counts are computed only on order lines with status
Delivered. Returned and cancelled lines are kept and analysed separately as
lost value ({V['lost_value']}, {V['lost_share']} of booked value). Applying
this one rule identically in Python, SQL and DAX is what makes the three
implementations reconcilable.

**30. What is the single most useful output of the project?**
The concentration finding, and the working list that follows from it: the top
decile plus the {V['clv_at_risk']} high-value inactive customers is a
short, specific list of accounts worth more attention than a broad acquisition
push.
"""


def intermediate_questions():
    return f"""
# 02 — Intermediate Technical Questions

{HEADER}

## Python

**1. Why Pandas?**
Because the unit of work is a labelled table with mixed types, and pandas
gives vectorised group-by, join, reshape and time handling on exactly that.
The whole pipeline — {V['clean_rows']} rows × {V['clean_cols']} columns —
fits comfortably in memory, so a DataFrame is the right structure.

**2. Why NumPy?**
It is the numerical layer underneath pandas and scikit-learn. I used it
directly for array maths such as the `log1p` transform applied to the skewed
RFM features and the `arcsinh` transform on the skewed customer-value features.

**3. How was the data cleaned?**
Rule by rule, with an audit trail. Every rule is evaluated on the raw extract,
the failing-row count is logged, a treatment is applied, and the rule is
re-evaluated on the cleaned data. A rule that does not return zero after
treatment is treated as a failure of the cleaning stage, not an acceptable
residue. {V['missing_before']} rows failed at least one rule; zero fail after.

**4. How were missing values handled?**
Differently by column, according to what the column means. Some were
recoverable by arithmetic — a missing quantity can be recomputed from sales,
unit price and discount. Others were imputed or labelled `Unknown` where that
is an honest category (payment method, for instance). Nothing was dropped
silently; every treatment is recorded in `data_quality_report.csv`.

**5. How were duplicates identified?**
As exact duplicate rows across the identifying columns. {V['dupes']} were
found and removed, taking {V['raw_rows']} raw lines to {V['clean_rows']}.

**6. Why was feature engineering necessary?**
Because the raw columns answer no business question on their own. The cleaned
dataset carries {F['dataset']['clean_cols'] - F['dataset']['raw_cols']}
engineered columns: calendar attributes for time analysis, the delivered flag
that implements the revenue rule, revenue/profit/margin, discount and age
bands for grouped analysis, outlier flags, and reconciliation checks that
confirm each line's arithmetic.

## Statistics

**7. Mean vs median — why does it matter here?**
Mean historical profit per customer is {V['clv_mean']}; the median is
{V['clv_median']}. The gap is the right-skew caused by a small number of very
large customers. Reporting only the mean would suggest a typical customer who
does not exist.

**8. What is standard deviation?**
The average distance of observations from the mean — a measure of spread. In
this project it matters for scaling: RFM features are standardised before
clustering so that a variable with a larger spread does not dominate the
distance calculation.

**9. What is correlation, and what did it show?**
The strength of a linear relationship between two variables, from −1 to +1. I
computed a correlation matrix over the numeric measures during EDA. It informed
feature selection for the prediction model, where I also checked variance
inflation factors to avoid keeping two features carrying the same information.

**10. What are outliers and how did you treat them?**
Values far from the bulk of the distribution, identified here with the 1.5×IQR
rule. I **flagged** them and inspected them; I did not remove them. A ₹2 lakh
order from a genuine high-value customer is a fact about the business.

**11. What is skewness, and where did it appear?**
Asymmetry in a distribution. Recency, frequency and monetary value are all
heavily right-skewed, which is why the clustering pipeline applies `log1p`
before standardising — otherwise a handful of very large customers would
dominate the geometry.

**12. What are quantiles, and how did you use them?**
Cut points dividing a distribution into equal-sized groups. RFM uses quintiles
(`pd.qcut`, q=5) so each dimension scores 1–5 with roughly 20% of customers per
band.

## RFM

**13. How was the reference date selected?**
As the latest order date in the dataset plus one day: {V['ref_date']}. Using
today's real-world date would make every customer look inactive, because the
data ends at {V['end']}.

**14. Why scores from 1 to 5?**
Five bands are enough to separate behaviour without creating segments too small
to act on, and they map naturally onto quintiles. A higher score always means
a better customer, which is why recency is reversed.

**15. Why use quantiles rather than fixed thresholds?**
Because fixed thresholds would need a business to supply them, and none is
documented here. Quantiles adapt to the distribution. The trade-off, which I
state as a limitation, is that a segment label describes a position *within
this base* rather than an absolute standard.

**16. How were the RFM segments created?**
By fixed rules over the scores. Champions requires R of 4–5 and a combined FM
score of at least 4.5; At Risk is low recency with high historical FM; and so
on for {V['rfm_segments']} segments. The rules are published with the results
so any assignment can be checked by hand.

**17. What happens when quintile edges are not unique?**
`pd.qcut` fails when many customers share the same value. The implementation
falls back to a tie-aware percentile rank in that case, so scoring never
breaks silently.

## K-Means

**18. What is a centroid?**
The mean position of all points assigned to a cluster — the cluster's centre
in feature space. K-Means alternates between assigning points to the nearest
centroid and recomputing centroids.

**19. What is inertia?**
The sum of squared distances from each point to its assigned centroid — the
quantity K-Means minimises. At K = {V['k']} it is {V['inertia']}. Inertia
always falls as K rises, which is why it cannot select K on its own.

**20. What is the elbow method?**
Plotting inertia against K and looking for the point where the improvement
flattens. It is a heuristic, not a rule — the "elbow" is often ambiguous,
which is why I did not rely on it alone.

**21. What is the silhouette score?**
For each point, how much closer it is to its own cluster than to the nearest
other cluster, from −1 to +1. The mean over all points is the silhouette
score: {V['silhouette']} at K = {V['k']}. It is modest, which is honest —
customer data rarely forms well-separated spheres.

**22. Why standardise the features?**
Because K-Means uses Euclidean distance. Monetary value is in rupees and runs
to lakhs; frequency is a count under 50. Without scaling, monetary value would
determine every cluster on its own. The pipeline applies {V['preprocessing']}.

**23. Why use PCA?**
Only to visualise the clusters in two dimensions. PC1 explains {V['pc1']} and
PC2 {V['pc2']} — {V['pca_total']} together — so the picture is faithful. PCA
was **not** used as a model input; clustering runs on all three scaled
features.

**24. What happens if K is too small?**
Distinct groups get merged. At K = 2 the base splits roughly into active and
inactive and the high-value group disappears into the active half, which loses
the distinction the business actually needs.

**25. What happens if K is too large?**
Clusters fragment into groups too small to act on, stability falls, and the
segmentation stops being interpretable. My pre-declared rule that no cluster
may hold less than {V['min_share']} of the base exists to prevent exactly this.

**26. How did you finally choose K?**
Three rules fixed **before** seeing results: K ≥ {V['min_k']}, minimum cluster
share ≥ {V['min_share']}, and bootstrap stability ARI ≥ {V['min_ari']}. Among
the values that satisfied all three, I took the highest silhouette — K =
{V['k']}, silhouette {V['silhouette']}, stability {V['ari_stability']}.

## CLV

**27. What is CLV?**
The value a customer represents over their relationship with the business.
This project reports it as two distinct quantities rather than one number.

**28. Historical vs predictive CLV — what is the difference here?**
Historical value is **measured**: delivered profit already earned,
{V['clv_hist_profit']} across the base. Forward value is **estimated** by a
supervised model trained on {V['clv_train']} and tested on {V['clv_test']},
with MAE {V['clv_mae']} and R² {V['clv_r2']}. I never add them together and
never present the estimate as a guarantee.

**29. Why is CLV useful?**
Because it turns "who is big" into "who is worth attention next". Ranking by
estimated forward value with recency visible produces a short working list —
for example the {V['clv_at_risk']} high-value customers inactive for 180+
days, holding {V['clv_at_risk_rev']} of historical revenue.

**30. What assumptions did the CLV work make?**
That past behaviour in a twelve-month window carries information about the
next twelve months; that the customer base composition is broadly stable; and
that profit is correctly attributed at line level. A BG/NBD probabilistic model
was also fitted for comparison, but it assumes a purchasing process running
until an unobserved dropout — an assumption a {V['months']}-month history
supports poorly, which is why the supervised model was selected instead.

## Prediction

**31. What is the prediction target?**
{V['pred_target']} — at the unit of {V['pred_unit']}.

**32. Why was a temporal split used?**
Because the task is to predict the future from the past. A random split would
let the model learn from quarters that come *after* the ones it is tested on,
which would inflate the score and mean nothing in practice. My split is
{V['train_rows']} train ({V['train_period']}), {V['val_rows']} validation
({V['val_period']}), {V['test_rows']} test ({V['test_period']}).

**33. What is data leakage?**
When information that would not be available at prediction time reaches the
model — directly, or through a feature computed over the target window.

**34. Why must leakage be avoided, and how did you check?**
Because it produces a model that scores well in development and fails in
production. Every feature in my panel is computed strictly from data before
the cutoff, and a leakage audit recomputes sampled feature rows directly from
the transaction table to confirm it. The audit found none.

**35. What is MAE?**
Mean absolute error — the average absolute difference between prediction and
actual, in the same unit as the target. Test MAE is {V['pred_mae']}.

**36. What is RMSE?**
Root mean squared error. Because errors are squared first, it penalises large
misses more heavily than MAE. Test RMSE is {V['pred_rmse']}; it is much larger
than MAE, which tells you the error distribution has a heavy tail.

**37. What is R²?**
The share of variance in the target explained by the model, relative to
predicting the mean. Test R² is {V['pred_r2']} — small. The naive
previous-quarter baseline scores {V['naive_r2']}, so the model is better than
the baseline while still explaining little.

**38. When is MAPE problematic?**
When actual values are at or near zero, because dividing by them explodes or
undefines the percentage. In my prediction panel {V['pred_zero']} of
customer-quarters have a zero actual value, so MAPE is meaningless there — I
report WAPE ({V['pred_wape']}) instead. MAPE is used only in forecasting,
where monthly revenue is never near zero.

**39. Why was a linear regression selected over the ensembles?**
Because the selection rule was fixed in advance: {V['pred_rule']}. The random
forest and gradient boosting bought no material accuracy over the linear model
on validation, so the simpler, interpretable model was kept.

## Forecasting

**40. Prediction vs forecasting — what is the difference?**
Prediction here is cross-sectional and supervised: per customer, per quarter,
using customer features. Forecasting is a univariate time-series task: one
series — company monthly revenue — projected forward from its own history.
Different units, different methods, different error metrics.

**41. What is seasonality?**
A pattern that repeats at a fixed period. October is the highest month in all
three years in this data, but with {V['fc_series']} monthly observations the
Theta seasonality test did not confirm a stable pattern, so no seasonal model
was imposed.

**42. What is trend?**
The long-run direction of the series. Revenue rises across the window —
{V['rev_2023']} in 2023 to {V['rev_2025']} in 2025.

**43. What is stationarity, and is your series stationary?**
A series is stationary when its statistical properties do not change over
time. The ADF test on the revenue level gives p = {V['adf_p']}, so the null of
a unit root is not rejected and the series is treated as non-stationary in
level.

**44. What is backtesting?**
Rolling-origin evaluation: fit on data up to a point, forecast forward, score
against what actually happened, roll the origin forward and repeat. I used
{V['fc_folds']} folds; the mean backtest MAPE is {V['fc_backtest']}.

**45. Why chronological validation rather than cross-validation?**
Because shuffling time destroys the ordering the task depends on. Standard
k-fold would train on the future to predict the past. Rolling-origin
backtesting is the time-series equivalent.

**46. Why is the backtest MAPE higher than the test MAPE?**
Test MAPE is {V['fc_test_mape']} on one favourable six-month window; the
backtest mean over {V['fc_folds']} folds is {V['fc_backtest']}. The backtest
is the honest expectation, and that is the figure the report and the deck
quote.

**47. What do the prediction intervals mean?**
The 80% interval on the {V['fc_horizon']}-month forecast runs from
{V['fc_low80']} to {V['fc_high80']} around a point estimate of
{V['fc_total']}. It is the model's own uncertainty given the history length;
it does not cover a shock from outside the revenue series, because the model
is univariate.
"""


def advanced_questions():
    return f"""
# 03 — Advanced Data Science Questions

{HEADER}

Each answer follows: **definition → why it matters → how it appears in this
project.** Where a technique was not used, that is stated plainly.

**1. Feature leakage**
Using information in a feature that would not exist at prediction time. It
matters because it inflates development scores and fails in production. In this
project every panel feature is computed strictly before its cutoff, and a
leakage audit recomputes sampled rows directly from the transaction table to
verify it; the audit found none.

**2. Temporal leakage**
The time-specific form: training on periods that come after the test period.
It matters because it makes a backward-looking model look forward-looking. I
used a strictly chronological split — train {V['train_period']}, validation
{V['val_period']}, test {V['test_period']} — and rolling-origin backtesting for
the forecast, never random k-fold.

**3. Model generalization**
How well a model performs on data it has not seen. It matters because fitting
the training set is trivial and useless. Here, generalization is measured on an
out-of-time test split: prediction R² {V['pred_r2']}, customer value R²
{V['clv_r2']}, forecast backtest MAPE {V['fc_backtest']}.

**4. Bias–variance trade-off**
High-bias models underfit; high-variance models memorise noise. It matters
because model choice is a position on this trade-off. Here the pre-declared
rule — {V['pred_rule']} — resolved it toward the low-variance end: the
ensembles bought no material validation accuracy over the linear model, so the
simpler model was kept.

**5. Overfitting**
A model that fits training noise. It matters because the resulting score is
fiction. My evidence that it did not happen is the direction of the metrics:
validation RMSE {V['pred_val_rmse']} against test RMSE {V['pred_rmse']} —
degradation consistent with a harder test window, not with a memorised
training set. A linear model with {V['pred_features']} features on
{V['train_rows']} training rows has little capacity to overfit.

**6. Underfitting**
A model too simple to capture the signal. It matters because it wastes
available information. Given R² {V['pred_r2']}, underfitting is a fair
challenge to my prediction model. My answer is that more flexible models were
tested — random forest and gradient boosting — and did not do materially
better, which points to a weak signal rather than an inadequate model.

**7. Cross-validation**
Repeatedly holding out folds to estimate out-of-sample performance. It matters
because a single split is noisy. I used 5-fold CV **within the training
cutoff** to select the customer-value model. I deliberately did **not** use
random k-fold for the time-dependent tasks, because it would leak the future.

**8. Hyperparameter tuning**
Searching over settings not learned from data. It matters because defaults are
rarely optimal. In this project it was limited: a tuned random forest variant
appears in the prediction comparison table, and the customer-value random
forest uses `min_samples_leaf=10, n_estimators=300`. No large grid or Bayesian
search was run — that is an honest limitation, not a claim.

**9. Feature importance**
How much each feature contributes to predictions. It matters for explanation
and for trust. I used **permutation importance**, which measures the increase
in error when a feature is shuffled. Customer value: {V['clv_drivers']}.
Prediction: {V['pred_drivers']}.

**10. Why permutation importance rather than built-in importance?**
Built-in tree importance is biased toward high-cardinality features and is not
comparable across model families. Permutation importance is model-agnostic and
measures what actually degrades when the feature is destroyed.

**11. Model interpretability**
The ability to explain why a model produced an output. It matters because a
business must act on the output. It is one reason the linear model was kept
for prediction, and the reason RFM is reported alongside K-Means — the rules
can be checked by hand. SHAP values were **not** computed; that is an
extension, not part of the pipeline.

**12. Clustering validation**
Assessing a clustering without ground-truth labels. It matters because K-Means
will always return K clusters, valid or not. I used silhouette
({V['silhouette']}), Calinski–Harabasz ({V['ch']}), Davies–Bouldin
({V['db']}), a minimum cluster-share rule, and bootstrap stability
(mean ARI {V['ari_stability']}) — plus external agreement with the RFM scheme
(ARI {V['ari_vs_rfm']}).

**13. What does a silhouette of {V['silhouette']} really tell you?**
That the clusters are real but not well separated — the base is a continuum,
not four distinct populations. I report it rather than hide it. The business
value comes from the cluster profiles and the agreement with RFM, not from a
claim of clean separation.

**14. Dimensionality reduction**
Projecting data into fewer dimensions while retaining structure. It matters for
visualisation and for handling correlated features. I used PCA for
**visualisation only** — PC1 {V['pc1']} + PC2 {V['pc2']} = {V['pca_total']}.
Clustering used all three scaled features. Using PCA as a model input would
have added a second unexplained transformation for no benefit at three
dimensions.

**15. Time-series validation**
Evaluating a forecast with respect to the arrow of time. It matters because
standard CV is invalid on time series. I used a chronological train/validation/
test split ({V['fc_train']} / {V['fc_val']} / {V['fc_test']}) plus
rolling-origin backtesting over {V['fc_folds']} folds.

**16. Confidence intervals vs prediction intervals**
A confidence interval expresses uncertainty about a parameter; a prediction
interval expresses uncertainty about a future observation and is wider. What I
report on the forecast are **prediction intervals**: 80% from {V['fc_low80']}
to {V['fc_high80']}.

**17. Forecasting uncertainty**
The range of outcomes a forecast admits. It matters because a point estimate
presented alone implies precision the model does not have. My interval is wide
because the history is short, and I quote the backtest mean MAPE
({V['fc_backtest']}) rather than the favourable single-split test MAPE
({V['fc_test_mape']}).

**18. Model deployment**
Making a model available to consumers of its output. It matters because a model
in a notebook changes nothing. Here, deployment is local: models are persisted
as `.pkl` artefacts with metadata and loaded by the Streamlit application,
which never refits them. There is **no** cloud deployment, API or container —
that is future scope.

**19. Model reproducibility**
Obtaining the same result from the same inputs. It matters for audit and for
trust. The dataset is generated from seed {V['seed']}; every stage has a single
entry point and reads only the persisted output of the previous stage;
scikit-learn and statsmodels versions are recorded in the model metadata; and
re-running produces identical checksums. The audit script re-derives the
K-Means labels from the persisted scaler and model and reproduces them exactly.

**20. Data drift**
A change in the distribution of the input features over time. It matters
because a model trained on last year's customers may see a different population
this year. No drift monitoring is implemented in this project — it is named in
future scope. The structure that would support it exists: the pipeline is
re-runnable, so distributions could be compared between runs.

**21. Concept drift**
A change in the relationship between features and target, not merely in the
inputs. It matters because the model can become wrong even when the inputs look
unchanged. A discount-policy change would be an example: the mapping from
behaviour to next-quarter revenue would shift. Also not implemented; also named
in future scope.

**22. Model monitoring**
Tracking a deployed model's inputs, outputs and realised accuracy. It matters
because degradation is silent otherwise. This project has **project-level**
monitoring — an automated audit of {V['audit_total']} checks covering
structure, pipeline dependencies, cross-dataset consistency, model
reproducibility, leakage and integration — but no production model monitoring.

**23. Class imbalance / zero inflation**
Here the analogue is zero inflation in the regression target:
{V['pred_zero']} of customer-quarters have a zero actual value. It matters
because the model spends its capacity on whether a customer orders at all
rather than on how much. The correct remedy, stated in future scope, is a
two-stage model — a classifier for "will they order" and a regressor for
"how much, given they do".

**24. Why is Spearman reported alongside R²?**
Because ranking and level are different capabilities. The customer-value model
has R² {V['clv_r2']} but Spearman {V['clv_spearman']} — it ranks customers
much better than it predicts their exact value, which is precisely how it is
used.

**25. Total bias vs individual error**
Bias is the aggregate error; MAE is the typical individual error. Both matter,
separately. My prediction model has a total bias of {V['pred_bias']} — close
to unbiased in aggregate — while individual predictions are poor. That is why
the model is described as usable at portfolio level, not per customer.

**26. Why not use a deep learning model?**
Because the dataset is {V['clean_rows']} rows of tabular data over
{V['months']} months. Neural networks need far more data to beat linear models
and gradient boosting on tabular problems, and would sacrifice the
interpretability the business case requires. It was not tried, and I do not
claim it was.

**27. Ensemble vs single model**
Ensembles average away variance and usually win on tabular data. Here they did
not win by enough to pass the pre-declared 2% rule, so the linear model was
selected for prediction — while an ensemble (random forest) *was* selected for
customer value, where it did win. The rule, not a preference, decided both.

**28. What is the Adjusted Rand Index and why did you use it twice?**
It measures agreement between two partitions, corrected for chance. I used it
for **stability** (clustering bootstrap samples and comparing partitions; mean
{V['ari_stability']}) and for **external agreement** between the RFM segments
and the K-Means clusters ({V['ari_vs_rfm']}).

**29. How do you know the two segmentations agree "substantially" rather than
trivially?**
Because ARI is chance-corrected: a random partition scores about zero.
{V['ari_vs_rfm']} indicates real shared structure — concentrated on the
high-value group — while the disagreement in the middle of the base is itself
informative about where the rule boundaries are arbitrary.

**30. If you had to defend one methodological decision, which would it be?**
Fixing the model-selection rules *before* seeing the results — for K, for the
customer-value model, for the prediction model and for the forecast. It is the
reason the weak prediction result was reported as weak rather than replaced by
a better-looking model chosen after the fact.
"""


def sql_viva():
    return f"""
# 04 — SQL Viva

{HEADER}

The database is SQLite: **{V['sql_tables']} tables and {V['sql_views']}
views**, with {V['sql_queries']} analytical queries
({V['sql_analysis']} in `sql/analysis_queries.sql`, {V['sql_business']} in
`sql/business_queries.sql`), plus {F['sql']['pbi_views']} `pbi_*` views for
the Power BI layer. Core tables: `locations`, `customers`, `products`,
`orders`, `order_items`, and the analytical tables carrying RFM segments,
clusters, customer value, predictions and forecasts.

**1. What is SELECT?**
The clause that chooses which columns a query returns. Every query in the
project starts with it.

**2. What is WHERE?**
A row filter applied before grouping. The project's most important WHERE is the
revenue rule: `WHERE oi.order_status = 'Delivered'`.

**3. What is GROUP BY?**
It collapses rows into groups so aggregate functions return one row per group.
{F['sql']['techniques'][10]['Queries_Using_It']} of the project's queries use
it.

**4. What is HAVING, and how does it differ from WHERE?**
HAVING filters *after* aggregation; WHERE filters *before* it. Two project
queries use HAVING — for example, the most-frequent-customer query keeps only
customers above an order-count threshold:

```sql
SELECT o.customer_id, COUNT(DISTINCT o.order_id) AS orders
FROM   orders o
JOIN   order_items oi ON oi.order_id = o.order_id
WHERE  oi.order_status = 'Delivered'
GROUP  BY o.customer_id
HAVING COUNT(DISTINCT o.order_id) >= 20
ORDER  BY orders DESC;
```

**5. What is ORDER BY?**
It sorts the result set. Used with LIMIT for every top-N query — top customers,
top products.

**6. What is a JOIN?**
It combines rows from two tables on a related column. The project's spine is
`orders` joined to `order_items` on `order_id`, and to `customers` on
`customer_id`.

**7. INNER JOIN vs LEFT JOIN?**
INNER returns only matching rows; LEFT returns all rows from the left table
with NULLs where there is no match. The project uses INNER JOIN in
{F['sql']['techniques'][0]['Queries_Using_It']} queries and LEFT JOIN in
{F['sql']['techniques'][1]['Queries_Using_It']}. LEFT JOIN matters where a
customer or product may have no delivered rows — dropping them would silently
change the denominator.

**8. Give an example of a LEFT JOIN in the project.**
Product profitability keeps products with no delivered sales, so the catalogue
is complete:

```sql
SELECT p.product_id, p.product_name, p.category,
       COALESCE(SUM(oi.sales), 0)      AS revenue,
       COALESCE(SUM(oi.net_profit), 0) AS profit
FROM   products p
LEFT   JOIN order_items oi
       ON oi.product_id = p.product_id AND oi.order_status = 'Delivered'
GROUP  BY p.product_id, p.product_name, p.category
ORDER  BY revenue DESC;
```

**9. What is a CTE?**
A Common Table Expression — a named temporary result defined with `WITH`, used
to break a complex query into readable steps.
{F['sql']['techniques'][3]['Queries_Using_It']} project queries use one.

**10. Show a CTE from the project.**
Year-over-year revenue growth:

```sql
WITH yearly AS (
    SELECT strftime('%Y', o.order_date) AS yr,
           SUM(oi.sales)                AS revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY yr
)
SELECT yr, revenue,
       LAG(revenue) OVER (ORDER BY yr)                       AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY yr))
             / LAG(revenue) OVER (ORDER BY yr), 2)           AS yoy_growth_pct
FROM   yearly
ORDER  BY yr;
```

**11. What is CASE WHEN?**
Conditional logic inside a query.
{F['sql']['techniques'][2]['Queries_Using_It']} project queries use it — for
discount bands, age bands, and conditional aggregation such as counting
returned lines within a single pass.

**12. What are aggregate functions?**
Functions that collapse many rows into one value: `SUM`, `AVG`, `COUNT`, `MIN`,
`MAX`. Revenue is `SUM(oi.sales)`, AOV is `SUM(sales) / COUNT(DISTINCT
order_id)`.

**13. What is a subquery?**
A query nested inside another, in SELECT, FROM or WHERE.
{F['sql']['techniques'][4]['Queries_Using_It']} project queries use one — for
example comparing a customer's revenue against the base-wide average.

**14. What is a window function?**
A function that computes across a set of rows related to the current row
*without* collapsing them. {F['sql']['techniques'][5]['Queries_Using_It']}
project queries use window functions — the most-used advanced technique here.

**15. ROW_NUMBER vs RANK vs DENSE_RANK?**
`ROW_NUMBER` gives a unique sequential number even for ties; `RANK` gives ties
the same number and then skips; `DENSE_RANK` gives ties the same number without
skipping. Top-N customer and product queries use them
({F['sql']['techniques'][6]['Queries_Using_It']} queries use ranking).

**16. Show a ranking query from the project.**

```sql
SELECT customer_id, revenue,
       RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM (
    SELECT o.customer_id, SUM(oi.sales) AS revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY o.customer_id
)
ORDER  BY revenue_rank
LIMIT  10;
```

**17. How did you compute revenue concentration in SQL?**
With a running total over a window frame
({F['sql']['techniques'][7]['Queries_Using_It']} queries use running totals):

```sql
WITH cust AS (
    SELECT o.customer_id, SUM(oi.sales) AS revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY o.customer_id
)
SELECT customer_id, revenue,
       SUM(revenue) OVER (ORDER BY revenue DESC
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
       / SUM(revenue) OVER () * 100 AS cumulative_pct_of_revenue
FROM   cust
ORDER  BY revenue DESC;
```

This is the query behind the finding that the top 20% of customers produce
{V['top20']} of revenue.

**18. What does SUM() OVER () without ORDER BY do?**
It returns the grand total on every row, which is how percentage-of-total
columns are computed without a second pass.
{F['sql']['techniques'][8]['Queries_Using_It']} project queries use it.

**19. What are LAG and LEAD?**
They read the previous or next row within a window — the basis of
period-over-period comparison. {F['sql']['techniques'][9]['Queries_Using_It']}
project queries use them, including the year-over-year and month-over-month
growth queries.

**20. Which date functions did you use?**
SQLite's `strftime` — `strftime('%Y', order_date)` for year,
`'%Y-%m'` for month, and quarter derived from the month.
{F['sql']['techniques'][12]['Queries_Using_It']} queries use date functions.

**21. How is customer-level aggregation done?**
Group `order_items` joined to `orders` by `customer_id`, filtered to delivered
lines, then aggregate: revenue `SUM(sales)`, frequency `COUNT(DISTINCT
order_id)`, recency from `MAX(order_date)` against the reference date
{V['ref_date']}. That is the SQL equivalent of the RFM base table.

**22. What is UNION ALL and where did you use it?**
It stacks two result sets without removing duplicates. One project query (BQ10)
uses it to present two comparable groups in a single table.

**23. Why normalise the database instead of one flat table?**
To remove repetition and enforce integrity: customer attributes live once in
`customers`, product attributes once in `products`, and `order_items` carries
the facts with foreign keys. It also makes the SQL layer a genuinely
independent implementation rather than a copy of the analytical DataFrame.

**24. How did you validate the database?**
{V['sql_checks']} referential and business-rule checks plus
{V['sql_quality']} data-quality checks, all passing — row counts against the
source, foreign-key integrity, no orphan order items, and the revenue totals
matching the Python pipeline.

**25. What is the single most important SQL query in the project?**
The revenue KPI query, because it is the reconciliation anchor: Python, SQL and
DAX must all return {V['revenue']} revenue, {V['profit']} profit,
{V['margin']} margin, {V['orders']} orders and AOV {V['aov']}.

```sql
SELECT COUNT(DISTINCT o.order_id)                        AS orders,
       COUNT(DISTINCT o.customer_id)                     AS customers,
       ROUND(SUM(oi.sales), 2)                           AS revenue,
       ROUND(SUM(oi.net_profit), 2)                      AS profit,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct,
       ROUND(SUM(oi.sales) / COUNT(DISTINCT o.order_id), 2) AS aov
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```
"""


def powerbi_viva():
    return f"""
# 05 — Power BI Viva

{HEADER}

> **State this up front if asked:** Power BI Desktop is a Windows application
> and was not available in the Linux environment this project was built in. The
> semantic model, {V['pbi_measures']} DAX measures, Power Query M scripts,
> theme and build guide are complete and validated
> ({V['pbi_matched']}/{V['pbi_val']} measures match their SQL equivalents).
> The nine page layouts are **design mockups rendered from the real data**, and
> are labelled as mockups everywhere. No Power BI Desktop screenshot is claimed.

**1. What is Power BI?**
Microsoft's business intelligence tool: it imports and models data, defines
measures in DAX, and presents them as interactive reports a business user can
slice without writing code.

**2. Why Power BI for this project?**
Because a manager needs self-service analysis over a governed model — one place
where "revenue" means exactly one thing. The star schema plus
{V['pbi_measures']} measures lets them slice by date, region, category, RFM
segment or cluster without an analyst in the loop.

**3. What is a data model?**
The set of tables and the relationships between them that queries run against.
Mine has {V['pbi_tables']} tables and {V['pbi_rels']} relationships.

**4. What is a star schema?**
A central fact table surrounded by dimension tables. Here `FactSales` is the
fact; `DimDate`, `DimCustomer`, `DimProduct`, `DimGeography`, `DimRFMSegment`
and `DimCluster` are dimensions, with `FactForecast`,
`FactRevenuePrediction`, `PredictionQuarterly`, `ModelMetrics`, `ModelInfo`
and `Recommendations` alongside.

**5. What is a relationship?**
A defined link between a dimension key and a fact key that lets a filter on one
table propagate to the other. All {V['pbi_rels']} of mine are one-to-many with
**single** cross-filter direction.

**6. Why single-direction rather than bidirectional filtering?**
Because bidirectional filters create ambiguous filter paths and unpredictable
results in a multi-fact model. Single direction — dimension filters fact — is
the conservative, debuggable choice.

**7. What is a Date table and why mark it?**
A dedicated table with one row per calendar day. Mine runs 2023-01-01 to
2026-06-30 so it covers both history and the forecast horizon. Marking it as
the date table tells Power BI to use it for time intelligence; without it,
functions like year-to-date behave incorrectly.

**8. What is DAX?**
Data Analysis Expressions — the formula language for Power BI measures and
calculated columns. It evaluates within a filter context supplied by the visual.

**9. Measures vs calculated columns — what is the difference?**
A calculated column is computed row-by-row at refresh and stored in the model.
A measure is computed at query time within the current filter context and
stores nothing. Revenue, margin and AOV are **measures** — they must respond to
whatever the user has sliced.

**10. Give an example of a measure from your model.**
Total revenue carries the project's revenue rule explicitly:

```dax
Total Revenue =
CALCULATE ( SUM ( FactSales[Sales] ), FactSales[Is_Delivered] = TRUE () )
```

Every revenue-derived measure filters on `Is_Delivered`, so the model cannot
silently report a different definition from the pipeline.

**11. How are the measures organised?**
Into {V['pbi_folders']} display folders — revenue, profit, customers,
segmentation, prediction, forecast, time intelligence and so on — so a
{V['pbi_measures']}-measure model stays navigable.

**12. What is CALCULATE?**
The DAX function that modifies filter context. It is the reason a measure can
say "revenue, but only delivered lines" or "revenue, same period last year".

**13. What is a slicer?**
An on-canvas filter control — date range, region, category, segment — that
applies to the visuals on the page.

**14. Slicer vs filter pane?**
A slicer is visible to the user on the page; the filter pane holds filters at
visual, page or report level, which may be applied without being prominent.

**15. What is drill-through?**
A navigation feature: right-click a data point and jump to a detail page
filtered to that value. My specification includes a customer-detail
drill-through page so a manager can move from a segment to one customer's
history.

**16. What are tooltips?**
Contextual information on hover. They keep a chart uncluttered while making
detail available — for example, showing margin and order count behind a
revenue bar.

**17. What are KPI cards and which ones did you specify?**
Single-number tiles for headline metrics. The Executive Overview page carries
revenue {V['revenue']}, profit {V['profit']}, margin {V['margin']}, orders
{V['orders']}, customers {V['cust_buy']} and AOV {V['aov']}.

**18. What principles guided your dashboard design?**
High data-ink ratio, restrained colour, a clear visual hierarchy with headline
KPIs first, and one analytical purpose per visual. The caveat I state openly:
design effectiveness can only be confirmed by user testing, which was outside
this internship's scope.

**19. What is data refresh?**
Re-importing source data so the model reflects current values. Here the sources
are the SQL views, so a refresh re-reads them. In production this would be
scheduled; in this project it is manual.

**20. How did you validate the Power BI layer?**
Every measure was computed independently in SQL and compared:
{V['pbi_matched']}/{V['pbi_val']} match. A further
{V['pbi_consistency']} cross-surface consistency checks compare the Power BI
figures with the Python pipeline and the application.

**21. Power BI vs Streamlit — why both?**
They answer different needs. Power BI is a governed semantic model for
self-service slicing by a business audience. Streamlit is an application: it
loads the actual trained `.pkl` models, runs predictions, accepts a file upload
and returns downloadable output. Power BI cannot load a scikit-learn model;
Streamlit does not give a business user a drag-and-drop model to explore.

**22. What is Power Query / M?**
The data-preparation layer: M scripts define how each table is loaded and
shaped before it reaches the model. The project ships one M script per table.

**23. What is row-level security, and did you use it?**
A model feature restricting which rows a given user can see. It was **not**
implemented — there is no user population for a synthetic academic dataset.

**24. What would you still have to do to finish the Power BI build?**
Open Power BI Desktop on Windows, connect to the supplied SQL views using the
Power Query scripts, paste in the DAX library, create the nine pages from the
build guide, and confirm the rendered figures against the validated measure
table.

**25. If a measure in Power BI disagreed with the Python pipeline, what would
you do?**
Treat it as a defect, not a rounding difference, and trace it to the filter
context — nearly always a missing `Is_Delivered` filter or a relationship
filtering in an unexpected direction. That check is exactly what the
{V['pbi_val']}-measure validation table automates.
"""


def streamlit_viva():
    return f"""
# 06 — Streamlit Viva

{HEADER}

The application is **{V['app_pages']} pages**, tested headlessly with
{V['app_passed']}/{V['app_tests']} checks passing.

**1. What is Streamlit?**
An open-source Python framework for building data applications. You write
ordinary Python; Streamlit re-runs the script on each interaction and renders
the widgets and charts it encounters.

**2. Why use Streamlit here?**
Because the project needed a working application, not only a dashboard. It
loads the actual persisted models, runs predictions, accepts a file upload,
and offers downloads — and it does so in Python, so it reuses the pipeline's
own modules instead of reimplementing the metrics.

**3. How does `app.py` work?**
It sets the page configuration, applies the custom CSS, checks data
availability, renders the header, builds the navigation with `st.navigation`
over a list of `st.Page` objects grouped into four sections, runs the selected
page, and renders the footer.

**4. How are the pages organised?**
One module per page in `pages/` — `home.py`, `executive.py`, `revenue.py`,
`customers.py`, `segmentation.py`, `products.py`, `regional.py`,
`prediction.py`, `forecasting.py`, `recommendations.py`, `data_explorer.py`,
`about.py` — grouped in the sidebar under Overview, Analytics, Intelligence and
Reference.

**5. Why `st.navigation` rather than Streamlit's automatic pages folder?**
Because `st.navigation` gives explicit control over grouping, ordering and page
titles. Using it disables the automatic `pages/` discovery, which is intended
here.

**6. How are the models loaded?**
Through a cached loader that reads the persisted `.pkl` artefacts with joblib —
the K-Means model and its scaler, the customer-value model and preprocessor,
the revenue prediction model and preprocessor, and the forecasting model. The
application **never refits** anything; it reports a per-model status so a
missing artefact degrades one feature instead of crashing the app.

**7. What is caching in Streamlit and why does it matter?**
Because the script re-runs on every interaction, uncached work repeats every
time. `@st.cache_data` caches data loads and `@st.cache_resource` caches
objects like models and database connections, so a filter change does not
reload the database or re-read a model from disk.

**8. Where does the data come from?**
The loader is database-first: it opens the SQLite database and executes the
`pbi_*` view definitions, falling back to the processed CSV files if the
database is absent. The app states which source it is using.

**9. How are the Plotly charts generated?**
Through a shared helper in `src/dashboard_utils.py` that applies one theme,
one colour sequence and consistent axis formatting, then returns the figure to
`st.plotly_chart`. Centralising it is why the charts look like one system
rather than twelve separate styles.

**10. How does file upload work?**
`st.file_uploader` accepts a CSV, the app validates its columns against the
expected schema, reports exactly which columns are missing if validation fails,
and only then runs the requested operation. A sample file is provided so a user
can see the expected format.

**11. How does prediction work in the app?**
The Revenue Prediction page loads the persisted prediction model and
preprocessor, applies them to the prepared customer-quarter features, and shows
the predictions **alongside the model's own accuracy** — test R²
{V['pred_r2']}, MAE {V['pred_mae']} — so a user cannot read the numbers
without seeing how reliable they are.

**12. How does forecasting work in the app?**
The Sales Forecast page loads the persisted {V['fc_model']} model and shows the
{V['fc_horizon']}-month forecast with its 80% and 95% prediction intervals,
together with the backtest position ({V['fc_backtest']} mean MAPE) rather than
only the favourable test-split figure.

**13. How is error handling implemented?**
Three layers: a data-status check at startup; a validation helper that checks a
DataFrame has the expected columns before a page uses it; and a guard that
renders an explanatory message instead of a traceback when an artefact is
missing. The test suite deliberately removes a model file and the database to
confirm the app degrades gracefully, then restores them.

**14. How was the application tested?**
With `streamlit.testing.v1.AppTest`, headlessly: {V['app_tests']} checks
covering app launch, sidebar navigation, every page's load, filters, model
loading, downloads, file-upload validation and graceful degradation. All
{V['app_passed']} pass, with per-page load times recorded.

**15. Why use Streamlit instead of only Power BI?**
Because Power BI cannot load a scikit-learn model or a statsmodels object. Any
page that needs a live model — prediction, forecasting — has to run Python.

**16. Why use Power BI instead of only Streamlit?**
Because a governed semantic model with {V['pbi_measures']} conformed measures
is what makes self-service slicing safe for a business audience. They are
complements, not substitutes.

**17. What is the difference between a dashboard and an application?**
A dashboard presents pre-computed measures for exploration. An application
executes logic — it loads models, accepts input, computes an output and returns
a file. This project ships both, deliberately.

**18. Does the app compute any metric of its own?**
No, and that is a design rule. Every number it displays is read from the
pipeline's outputs or computed by the same shared module the pipeline uses, so
a figure on screen cannot drift from the report.

**19. How would you deploy this application?**
Streamlit Community Cloud or a container behind a reverse proxy, with the data
and model artefacts mounted or fetched from object storage. It is **not**
deployed — it runs locally with `streamlit run app.py`. Deployment is named in
future scope.

**20. What are the limitations of the application?**
It is single-user and local; there is no authentication, no scheduled data
refresh, no model retraining and no monitoring. It was not user-tested. Those
are listed in the report's limitations, not glossed over.

**21. How do I start it?**
`pip install -r requirements.txt`, then `streamlit run app.py`, then open
`http://localhost:8501`. If a page reports a missing artefact, the
corresponding pipeline stage has not been run.

**22. What would a live demo show?**
The Executive Overview KPIs matching the report exactly, then Customer
Segmentation with the at-risk high-value filter producing the
{V['clv_at_risk']}-customer list, then Sales Forecast with its interval, then a
CSV download from the Data Explorer.
"""


def business_questions():
    return f"""
# 07 — Business Questions

{HEADER}

**1. Which customers should receive retention attention?**
Two lists. The top decile, which carries {V['top10']} of revenue. And the
{V['clv_at_risk']} high-value customers with no delivered order for 180+ days,
holding {V['clv_at_risk_rev']} of historical revenue between them — a specific,
workable list, not a statistic.

**2. How can RFM support marketing decisions?**
It converts a flat customer list into {V['rfm_segments']} groups that imply
different actions: Champions ({V['champ_cust_pct']} of customers,
{V['champ_rev_pct']} of revenue) get protection and early access; At Risk
({V['atrisk_rev_pct']} of revenue) get reactivation; Lost
({V['lost_rev_pct']} of revenue) get low-cost, low-effort contact at most.

**3. How can CLV support customer prioritisation?**
By ranking customers on estimated forward twelve-month profit rather than on
what they spent historically. The model's Spearman of {V['clv_spearman']} says
it ranks well even though its R² of {V['clv_r2']} says it predicts levels
poorly — so it is used to order a queue of attention, not to promise a number.

**4. How can revenue prediction support planning?**
At portfolio level. Total bias is {V['pred_bias']}, so aggregated predictions
are close to unbiased and can inform a quarterly expectation. At individual
level it explains little ({V['pred_r2']}), so it must not be used to set a
target for one customer.

**5. How can forecasting support inventory and cash planning?**
The {V['fc_horizon']}-month forecast is {V['fc_total']} with an 80% interval of
{V['fc_low80']} to {V['fc_high80']}. Planning against the interval rather than
the point estimate is the correct use — order to the lower bound for
commitments and to the point estimate for capacity.

**6. How can regional analysis support expansion?**
Mainly by ruling a hypothesis out. Revenue is evenly spread
({V['top_region']} {V['top_region_share']} to {V['small_region']}
{V['small_region_share']}) and {V['region_gaps']} of {V['region_pairs']}
region-category pairs sits more than two points below the national margin. So
there is no regional margin problem to fix; expansion should be argued on
market size, not on a defect in the current footprint.

**7. How can product profitability support product strategy?**
By separating two kinds of asset. {V['top_cat']} is {V['top_cat_rev']} of
revenue at {V['top_cat_margin']} margin; {V['best_margin_cat']} earns
{V['best_margin']}. The implication is mix management — attaching
higher-margin categories to volume orders — not a single revenue target across
both.

**8. How can discount analysis support pricing?**
Carefully. The {V['disc0_band']} band returns {V['disc0_margin']} margin
against {V['disc_hi_margin']} in the {V['disc_hi_band']} band, and is the
best-margin band in {V['disc_best_in']} of {V['cats_tested']} categories. That
is strong enough to justify a **controlled experiment**, not a policy change —
the data cannot say what those orders would have done at a different discount.

**9. How can segmentation support personalised marketing?**
By setting the contact rule per segment: frequency, offer type and channel
differ between a Champion and a customer About to Sleep. The cluster labels add
a second, independent view so a customer sitting on a rule boundary can be
checked.

**10. How can managers use the dashboard day to day?**
Executive Overview for the monthly position; Customer Intelligence sorted by
revenue with recency visible for the top decile review; Customer Segmentation
filtered to at-risk high value for the working list; Sales Forecast for the
planning conversation; Recommendations for the evidence behind each action.

**11. Which single action would you recommend first?**
Give the top revenue decile a named owner and review it monthly. It costs
almost nothing and protects {V['top10']} of revenue.

**12. Is acquisition or retention the better use of money here?**
The data leans to retention: repeat customers are {V['repeat_share_cust']} of
the base and {V['repeat_share_rev']} of revenue, averaging {V['repeat_avg']}
each against {V['single_avg']} for single-order customers. But the project
measured no acquisition cost, so this is a statement about where value sits,
not a computed ROI comparison.

**13. What is the business value of knowing the median inter-purchase gap?**
{V['median_gap']} days is the natural basis for an inactivity threshold. A
customer silent for three or four times that gap is behaving differently from
the base, which is a more defensible trigger than an arbitrary 90-day rule.

**14. How should the business treat the "Lost" segment?**
As low priority. {V['lost_n']} customers carry only {V['lost_rev_pct']} of
revenue. Spending heavily to reactivate them is poor use of effort compared
with protecting Champions.

**15. What does the returns and cancellations figure tell the business?**
{V['lost_value']} of booked value never converts — {V['lost_share']} of
{V['booked']}. That is a concrete operational target: reducing it is equivalent
to winning new revenue at full margin.

**16. Which products deserve management attention?**
{V['flagged_products']} products are flagged by the product analysis for a
combination of weak margin and high return rate. The flag is a prompt to
investigate, not a verdict to delist.

**17. How would you measure whether a recommendation worked?**
By defining the metric before acting — for the at-risk campaign, the share of
the {V['clv_at_risk']} customers placing a delivered order within one
inter-purchase interval — and comparing against a held-back control group.
That measurement is not part of this project.

**18. What is the business case for the platform itself?**
It replaces recomputed, hand-transcribed figures with one reconciled source:
the same {V['revenue']} appears in Python, in SQL, in the Power BI model and in
the application. The value is decisions taken on numbers that agree.

**19. Does the project prove any of these actions will increase revenue?**
No. Every relationship here is measured on observed orders. The
recommendations are evidence-linked, not causally proven, and the discount one
explicitly asks for an experiment before any policy change.

**20. How does seasonality affect planning?**
October is the highest month in all three years, which is a reasonable planning
assumption for stock and staffing. But the formal test on {V['fc_series']}
observations does not confirm a stable seasonal pattern, so it should be
treated as an observed regularity, not an established effect.

**21. How would the business use the two segmentations together?**
Use RFM for communication, because it is explainable to a marketing team. Use
the clusters as a check: where the two disagree, the customer sits near a rule
boundary and deserves a human look.

**22. What would you tell a manager who asks for one number to track?**
Revenue share of the top decile. It moves when the thing that matters most —
concentration — changes, and it is computed the same way in every surface of
the platform.

**23. How could this reduce cost rather than grow revenue?**
By reallocating effort. Knowing that {V['lost_rev_pct']} of revenue sits in the
Lost segment lets a team stop spending there, and knowing there is no regional
margin gap prevents a regional pricing project that the data does not support.

**24. What would change if the business ran a loyalty programme?**
The second-order conversion finding becomes directly actionable — repeat
customers are worth {V['repeat_avg']} against {V['single_avg']} — and the RFM
frequency dimension becomes the natural enrolment and tier criterion.

**25. If the professor asks "so what?", what is the one-sentence answer?**
A small, identifiable group of customers carries most of the revenue, this
platform names them and shows which of them are going quiet, and it does so
with numbers that agree across every surface of the system.
"""


def challenging_questions():
    return f"""
# 08 — Challenging Professor Questions

{HEADER}

These are the questions designed to find the weak point. The answers below are
honest; none of them claims the project is perfect.

**1. Why should I trust your segmentation?**
Because it was validated three ways, not asserted. Internally: silhouette
{V['silhouette']}, Calinski–Harabasz {V['ch']}, Davies–Bouldin {V['db']}.
For stability: bootstrap resampling gives mean ARI {V['ari_stability']}.
Externally: an independent rule-based scheme identifies substantially the same
high-value group, ARI {V['ari_vs_rfm']}. And K was chosen by rules fixed before
I saw the results.

**2. Why K-Means rather than hierarchical clustering or DBSCAN?**
K-Means scales, produces centroids that read directly as business profiles, and
is reproducible from a seed. Hierarchical clustering gives a dendrogram that is
attractive but O(n²) and still needs a cut point chosen by judgement. DBSCAN
finds density-based clusters and labels the rest noise, which does not suit a
base where every customer must land somewhere. Neither was implemented — I
considered them and chose K-Means for those reasons.

**3. A silhouette of {V['silhouette']} is low. Isn't your clustering weak?**
The separation is modest, yes, and I report it rather than hide it. The honest
interpretation is that the customer base is a continuum, not four distinct
populations. The clusters are still useful because the profiles differ
materially — cluster 0 is {V['hv_cust_pct']} of customers and
{V['hv_rev_pct']} of revenue — and because an independent method finds the same
structure.

**4. How do you know your model is not overfitting?**
The split is out-of-time, so the test window is genuinely unseen. Validation
RMSE is {V['pred_val_rmse']} and test RMSE {V['pred_rmse']} — the degradation
is consistent with a harder window, not with memorisation. And a linear model
with {V['pred_features']} features on {V['train_rows']} rows has very little
capacity to overfit in the first place.

**5. Your prediction R² is {V['pred_r2']}. Isn't the model useless?**
At individual level it is close to useless, and I say so in the report. It is
useful in two narrower ways: it beats every baseline including the naive
previous-quarter rule (R² {V['naive_r2']}), and its total bias is
{V['pred_bias']}, so aggregated predictions are usable for portfolio planning.
The structural reason is that {V['pred_zero']} of customer-quarters have a zero
actual value.

**6. Then why present it at all?**
Because the honest finding *is* the result: at this data length, company-level
revenue is forecastable ({V['fc_backtest']} backtest MAPE) and individual
customer revenue is not. Suppressing the weak number would have made the
project look better and taught less.

**7. What if the data distribution changes?**
The model degrades and nothing in the current system would tell you. There is
no drift monitoring — that is a genuine gap, named in future scope. What exists
is a fully re-runnable pipeline, so distributions between runs could be
compared once monitoring is added.

**8. What happens if a new customer has no purchase history?**
RFM cannot score them, the clusters cannot place them, and the prediction model
has no features. In this project, {V['rfm_excluded']} customers with no
delivered purchase are excluded from scoring, and the
{V['clv_by_group']} customers with no order in the feature window are given a
group average rather than a model score. A real cold-start solution would need
demographic or first-session features, which this dataset does not carry.

**9. How would your system work with real-time data?**
It would not, as built. Everything is batch: files are read, models are fitted,
outputs are persisted. Making it real-time would mean a streaming ingestion
layer, an online feature store and a serving API. That is an architectural
change, not a configuration change, and I would not pretend otherwise.

**10. What would you change if you had more data?**
Two things specifically. With a longer history I would revisit seasonality —
{V['fc_series']} months is too short for the Theta test to confirm a stable
pattern. And with more customer-quarters I would test the two-stage prediction
model that addresses the zero inflation, which needs enough positive cases in
each quarter to train the second stage.

**11. What are the weaknesses of your project?**
Synthetic data; a {V['months']}-month history; weak individual prediction; a
univariate forecast; association without causation; no churn label; Power BI
pages that are mockups rather than screenshots; no user testing; and no
deployment or monitoring. That list is in the report, not invented for this
answer.

**12. Why should a company use your system?**
Because it gives one reconciled source of truth — {V['revenue']} means the same
thing in Python, SQL, DAX and the application — and it produces a short,
specific action list rather than a report. Whether the actions pay is an
empirical question the company would have to test.

**13. What is the difference between prediction and forecasting?**
Prediction here is cross-sectional and supervised: customer × quarter, using
customer features. Forecasting is univariate time-series: one company-level
series projected from its own history. Different units, methods and error
metrics — which is why the deck gives them separate slides.

**14. What happens if your forecast is wrong?**
It will be wrong; the question is by how much. The honest expectation is the
backtest mean MAPE of {V['fc_backtest']}, not the favourable test-split
{V['fc_test_mape']}. That is why I publish the 80% interval
({V['fc_low80']} to {V['fc_high80']}) and recommend planning against the
interval rather than the point.

**15. How would you deploy this in production?**
Schedule the pipeline stages; persist models with versioned metadata; expose
prediction through a small API rather than in-process loading; containerise the
Streamlit app behind authentication; and add drift and performance monitoring.
None of that exists today — the application runs locally.

**16. How would you monitor the model after deployment?**
Three things: input distributions against the training distribution; the
prediction distribution over time; and realised accuracy once actuals arrive,
which for a quarterly target means one honest score per quarter. Not
implemented.

**17. Isn't synthetic data a fatal weakness?**
It bounds what can be claimed, and I bound the claims accordingly — the methods
transfer, the numbers describe no real business. What it does not compromise is
the engineering: the generator injects realistic defects, so the cleaning stage
has real work and can be audited against a known ground truth, which a real
extract could not offer.

**18. Your dataset was generated by you. Didn't you just find what you put in?**
Partly, and that is the honest limit. The generator sets skewed customer value,
seasonality, discounting and returns. It does not set the segment structure, the
ARI between two schemes, the silhouette, or how predictable next-quarter
revenue turns out to be — those emerged, and one of them (weak prediction) is
the opposite of what I expected.

**19. Why did a linear regression beat random forest and gradient boosting?**
It did not beat them outright; it tied within the tolerance I had fixed —
{V['pred_rule']}. Given a tie, the simpler and interpretable model wins by
rule. This is a signal-strength result, not a claim that linear models are
better.

**20. Why trust a selection rule you set yourself?**
Because it was set before the results and is published with them, so it can be
checked. It is the same discipline in four places: K selection, customer-value
model, prediction model and forecast model. Without it, I could have chosen
whichever model looked best after the fact.

**21. Could your findings be an artefact of the reference date?**
The reference date {V['ref_date']} is the latest order date plus one day, which
is the standard construction and is documented. Choosing today's real date
instead would make every customer look inactive. Recency-based segments would
shift under a different reference date, and that dependency is stated.

**22. Why is your customer-value R² only {V['clv_r2']}?**
Because twelve-month-ahead individual profit is genuinely hard to predict from
eight behavioural features. The more useful number is Spearman
{V['clv_spearman']} — it ranks customers well — and top-20% capture
{V['clv_top20']}. I use it as a ranking instrument, which is what the metrics
support.

**23. You used ARI twice for different purposes. Isn't that confusing?**
They are different comparisons using the same statistic: stability compares the
clustering against itself on bootstrap resamples ({V['ari_stability']}), while
external agreement compares the clusters against the RFM segments
({V['ari_vs_rfm']}). Both are legitimate; I label which is which.

**24. What if the business disagrees with your segment definitions?**
They should — the thresholds are mine, taken from quintiles, not from their
commercial judgement. The right next step is to replace the quintile cut-offs
with business-supplied thresholds; the code takes them as parameters, so that
is a configuration change.

**25. You claim reconciliation. What exactly did you reconcile?**
Revenue, profit, margin, order count, customer count and AOV across three
implementations — pandas, SQL and DAX — plus
{V['pbi_matched']}/{V['pbi_val']} individual measure comparisons and
{V['pbi_consistency']} cross-surface consistency checks. The whole project
carries {V['audit_total']} automated checks, {V['audit_pass']} passing.

**26. Did your audit ever actually fail?**
Yes, and that is the point of having it. It caught a documentation sentence
that described recency as a churn warning, contradicting the project rule that
no churn event exists; it caught a stale figure quoting an older audit count;
and it caught a filename in the appendix that did not match the persisted
model. All three were fixed at source and the artefacts regenerated.

**27. Why should I believe your leakage audit?**
Because it does not trust the pipeline's own feature code. It samples rows and
recomputes their features directly from the transaction table with independent
logic, then compares. If the pipeline had leaked, the two would disagree.

**28. Your project has no churn model. Isn't churn the standard use case?**
It is, which is exactly why I did not fake one. The dataset defines no churn
event — no contract, no cancellation, no explicit lapse — so any churn label
would have been invented by me and then predicted by me. I report recency-based
**inactivity** instead and never use the word churn to describe a result.

**29. What is the weakest link in the whole project?**
The customer-level prediction model. Everything upstream of it is either
measured or validated; that model is the one component whose output I would not
act on individually.

**30. If you had to defend the project in one sentence?**
Every number in it can be traced to the file that produced it, every model was
chosen by a rule fixed in advance, and the results that came out weak are
reported as weak.
"""


def trick_questions():
    return f"""
# 09 — Trick Questions

{HEADER}

These invite a confident wrong answer. The correct move is nuance.

**1. Why did you use synthetic data — couldn't you get real data?**
It was a deliberate choice for an academic deliverable: no confidentiality
constraint, full reproducibility from seed {V['seed']}, and a known ground
truth to audit the cleaning against. The cost is that the numbers describe no
real business, which I state everywhere.

**2. Can synthetic data represent real customer behaviour?**
Structurally, to a degree — skewed value, seasonality, discounting, returns and
missing fields are all present. Behaviourally, no: it contains no real
motivation, no competitive response, no macroeconomic effect. It is adequate
for demonstrating method, not for drawing conclusions about a market.

**3. Does a high RFM score automatically mean a customer is profitable?**
No. RFM's M is **revenue**, not profit. A customer can buy often and recently
in a low-margin category and contribute less profit than a smaller buyer in a
high-margin one. That is exactly why the project reports margin separately —
{V['top_cat']} is {V['top_cat_rev']} of revenue but only
{V['top_cat_profit']} of profit.

**4. Does correlation imply causation?**
No. The discount finding is the clearest case: the
{V['disc0_band']} band shows {V['disc0_margin']} margin against
{V['disc_hi_margin']} at {V['disc_hi_band']}, but deeper discounts may be
*applied to* lower-margin situations rather than causing them. The
recommendation is therefore a controlled experiment, not a price change.

**5. Is the highest-performing model always the best model?**
No. My prediction model is a linear regression that did not top every metric;
it was selected because it came within 2% of the best validation RMSE and is
simpler and interpretable. Best means best under a stated rule, including
interpretability and stability — not the top row of a leaderboard.

**6. Can K-Means identify the "true" customer segments?**
No. K-Means imposes a partition; it does not discover a truth. It minimises
within-cluster variance given a K you supply and a distance metric you chose,
on features you engineered. A silhouette of {V['silhouette']} says the groups
are real but not cleanly separated. "True segments" is not a thing the data
contains.

**7. Does a forecast guarantee future revenue?**
No. It is a projection of one series from its own history, with an 80% interval
of {V['fc_low80']} to {V['fc_high80']} and an honest expected error of
{V['fc_backtest']}. It has no knowledge of price changes, promotions, or
anything outside the revenue series.

**8. Can R² alone prove a model is good?**
No. R² is relative to predicting the mean and says nothing about bias, about
ranking, or about whether the error distribution has a heavy tail. My
customer-value model has R² {V['clv_r2']} but Spearman {V['clv_spearman']} —
poor at levels, good at ranking. Reporting only one would mislead.

**9. Can Power BI replace Python?**
No. Power BI cannot fit a K-Means model, run scikit-learn, or produce a
statsmodels forecast. It consumes the results. The reverse is also true: Python
does not give a business user governed self-service slicing.

**10. Can Streamlit replace Power BI?**
Not for this audience. Streamlit runs the models, which Power BI cannot; Power
BI gives a conformed semantic model with {V['pbi_measures']} measures for
self-service, which Streamlit does not. They solve different problems, which is
why the project ships both.

**11. Is CLV always accurate?**
No, and mine is not. Historical value is measured and therefore accurate by
construction. Forward value is estimated with MAE {V['clv_mae']} and R²
{V['clv_r2']} — the ranking is usable, the individual number is not a promise.

**12. Can more clusters always improve segmentation?**
No. More clusters always reduce inertia, which is why inertia cannot choose K.
Beyond a point the clusters fragment below the size at which any action is
worth taking, stability falls and interpretability disappears. My rule that no
cluster may hold under {V['min_share']} of the base exists for this.

**13. Your revenue is {V['revenue']}. Is the business doing well?**
The data cannot say. There is no benchmark, no competitor, no target and no
cost of capital in this dataset. What I can say is internal: margin rose from
{V['margin_2023']} to {V['margin_2025']} while revenue grew, so growth is not
being bought with margin.

**14. If Champions are your best customers, should you spend most of your
budget on them?**
Not automatically. They are already buying — the marginal return on contacting
a Champion may be lower than on reactivating an At Risk customer holding
{V['atrisk_rev_pct']} of revenue. The project measures value, not marginal
response, and I would not claim the latter.

**15. You removed {V['dupes']} duplicates. What if they were real repeat
orders?**
They were exact duplicate rows across the identifying columns, including order
ID — a genuine repeat purchase would carry a different order ID and date. The
removal is logged and reversible, and the generator's injection log confirms
they were injected duplicates.

**16. Your model says a customer will spend ₹0 next quarter. Should the
business drop them?**
No. {V['pred_zero']} of customer-quarters are genuinely zero, so "zero" is the
model's most common prediction and carries very little information about any
one customer. At R² {V['pred_r2']} it should not drive an individual decision
at all.

**17. Isn't a 23% margin obviously good?**
Unknowable from this data. Margin norms are industry-specific and this is a
synthetic catalogue. The useful statement is the spread within the business:
{V['top_cat_margin']} in {V['top_cat']} against {V['best_margin']} in
{V['best_margin_cat']}.

**18. You said October is your best month. Is that seasonality?**
It is an observed regularity in all three years, but the formal Theta
seasonality test on {V['fc_series']} observations does not confirm a stable
pattern. Calling it seasonality would overstate what {V['months']} months can
support.

**19. Your top 20% produce {V['top20']} of revenue — isn't that just the Pareto
principle, so nothing new?**
The principle predicts concentration; it does not tell you *who* or *how much*
in this base, and here it is {V['top20']} rather than the proverbial 80%. The
contribution is the named list and the evidence that two independent methods
identify the same group.

**20. If your pipeline is fully automated, what did you actually do?**
Chose the definitions, the rules and the validation. The automation is the
deliverable: deciding that revenue means delivered lines only, that K must pass
three pre-declared tests, that a forecast must beat both naive baselines, and
that every number in the report is read from a file rather than typed — and
then building the audit that checks all of it.

**21. Why didn't you use deep learning?**
Because {V['clean_rows']} rows of tabular data over {V['months']} months is not
where neural networks win, and the project needed interpretability. I did not
try it, and I am not going to claim I did.

**22. Could you have got a better R² by tuning more?**
Possibly a little, and I would not expect much — the ceiling here is set by the
zero inflation, not by hyperparameters. The genuine improvement is structural:
a two-stage model separating "will they order" from "how much". That is future
scope, not a claim.
"""


def mock_easy():
    return f"""
# 10 — Mock Viva 1 (Easy)

{HEADER}

**Professor:** Tell me about your project in one minute.
**Student:** It is a customer revenue intelligence platform built on a
synthetic retail dataset of {V['clean_rows']} validated order lines covering
{V['cust_buy']} customers over {V['months']} months. I clean the data against
explicit business rules, analyse the revenue base, segment customers two ways —
RFM rules and K-Means — estimate customer value, predict next-quarter revenue,
forecast company revenue six months ahead, reproduce everything independently
in SQL, and deliver it through a Power BI model and a
{V['app_pages']}-page Streamlit application. The headline finding is that value
is concentrated: the top 20% of customers produce {V['top20']} of revenue.

**Professor:** What dataset did you use?
**Student:** A synthetic e-commerce transaction dataset I generated with a
fixed seed, {V['seed']}. {V['raw_rows']} raw order lines cleaning to
{V['clean_rows']}, {V['products']} products in {V['categories']} categories,
{V['regions']} regions, {V['start']} to {V['end']}. It is not real customer
data and I say so throughout.

**Professor:** What does RFM stand for?
**Student:** Recency, Frequency and Monetary value. Recency is days since the
last delivered purchase, frequency is the count of distinct delivered orders,
monetary is total delivered sales. Each is scored 1 to 5 on quintiles at the
reference date {V['ref_date']}.

**Professor:** How many segments did you get?
**Student:** {V['rfm_segments']} rule-based segments across
{V['rfm_scored']} scored customers. Champions are {V['champ_n']} customers,
{V['champ_cust_pct']} of the base, carrying {V['champ_rev_pct']} of revenue.

**Professor:** What is K-Means?
**Student:** An unsupervised clustering algorithm that places K centroids and
assigns each customer to the nearest one, iterating until the assignment
stabilises. I used it on the same three RFM features as an independent check on
my rule-based segments.

**Professor:** How many clusters did you choose?
**Student:** K = {V['k']}, with a silhouette of {V['silhouette']}. I fixed
three rules before looking at results — at least {V['min_k']} clusters, no
cluster under {V['min_share']} of the base, and bootstrap stability of at least
{V['min_ari']} ARI — and then took the highest silhouette among the values that
qualified.

**Professor:** What is your total revenue?
**Student:** {V['revenue']} of delivered revenue, {V['profit']} profit, a
{V['margin']} margin, across {V['orders']} delivered orders at an average order
value of {V['aov']}.

**Professor:** Why did you use SQL if you already had Python?
**Student:** To have a second, independent implementation. The same
definitions written in a different language, so when SQL and Python agree on
revenue, profit and margin, that is evidence rather than a copy. It is
{V['sql_tables']} tables, {V['sql_queries']} queries, all
{V['sql_checks']} validation checks passing.

**Professor:** What is your forecast?
**Student:** {V['fc_horizon']} months ahead — {V['fc_months']} — totalling
{V['fc_total']}, with an 80% interval from {V['fc_low80']} to
{V['fc_high80']}. The model is {V['fc_model']} and the honest expected error is
the backtest mean MAPE of {V['fc_backtest']}.

**Professor:** What is the main limitation?
**Student:** The data is synthetic, so the methods transfer but the numbers
describe no real business. After that, the customer-level prediction model is
weak — R² {V['pred_r2']} — and I report it as weak rather than dressing it up.
"""


def mock_medium():
    return f"""
# 11 — Mock Viva 2 (Medium)

{HEADER}

**Professor:** Why did you choose the reference date {V['ref_date']}?
**Student:** It is the latest order date in the data plus one day. If I used
today's real date, every customer would look inactive because the data ends at
{V['end']}, and every recency score would be meaningless.

**Professor:** Your quintile cut-offs are relative to your own dataset. Isn't
that a weakness?
**Student:** Yes, and I state it as one. A segment label describes a position
within this base, not an absolute standard. The fix is business-supplied
thresholds, and the code takes them as parameters, so it is a configuration
change rather than a rewrite.

**Professor:** Why did you transform the features before clustering?
**Student:** Recency, frequency and monetary value are all heavily right-skewed
and on different scales — monetary runs to lakhs, frequency is a count under
50. The persisted pipeline applies {V['preprocessing']}, so distance is not
dominated by monetary value alone.

**Professor:** You used PCA. Why?
**Student:** Only to visualise the clusters in two dimensions. PC1 explains
{V['pc1']} and PC2 {V['pc2']}, {V['pca_total']} together. The clustering itself
runs on all three scaled features — PCA was never a model input.

**Professor:** What does an ARI of {V['ari_vs_rfm']} between your two
segmentations tell you?
**Student:** That there is real shared structure, since ARI is chance-corrected
and a random partition scores about zero. They converge on the high-value group
and diverge in the middle of the base, which tells me where my rule boundaries
are arbitrary.

**Professor:** Explain your prediction target precisely.
**Student:** {V['pred_target']}, at the unit of {V['pred_unit']}. The panel is
{V['panel_rows']} customer-quarter rows, {V['pred_features']} features, all
computed strictly from data before the cutoff.

**Professor:** Why an out-of-time split?
**Student:** Because the task is predicting the future from the past. A random
split would let the model see quarters that come after the test quarters, which
inflates the score and means nothing operationally. My split is
{V['train_rows']} / {V['val_rows']} / {V['test_rows']}, strictly chronological.

**Professor:** How did you check for leakage?
**Student:** With an audit that does not trust the pipeline's own feature code.
It samples rows and recomputes their features directly from the transaction
table with independent logic, then compares. If a feature had used post-cutoff
data the two would disagree. They did not.

**Professor:** Your R² is {V['pred_r2']}. Defend it.
**Student:** It is weak and I do not defend it as strong. It beats every
baseline — the naive previous-quarter rule gives R² {V['naive_r2']} — and total
bias is {V['pred_bias']}, so it is usable in aggregate. The structural reason it
is weak is that {V['pred_zero']} of customer-quarters have a zero actual value,
so the target is dominated by whether someone orders at all.

**Professor:** Why is MAPE not reported for prediction but is for forecasting?
**Student:** Because MAPE divides by the actual value. With {V['pred_zero']}
zeros in the prediction panel it is undefined or explosive, so I report WAPE
({V['pred_wape']}). Monthly company revenue is never near zero, so MAPE is
well-behaved there.

**Professor:** How did you select the forecasting model?
**Student:** By a rule fixed in advance: {V['fc_rule']}. Naive, seasonal naive,
ETS, ARIMA, SARIMA and Theta were all fitted; Theta had the lowest mean
backtest MAPE across {V['fc_folds']} rolling-origin folds and beat both naive
baselines on test MAE.

**Professor:** Is your series stationary?
**Student:** No. The ADF test on the level gives p = {V['adf_p']}, so the null
of a unit root is not rejected and I treat the series as non-stationary in
level.

**Professor:** Why do you quote the backtest MAPE rather than the test MAPE?
**Student:** Because the test MAPE of {V['fc_test_mape']} comes from one
favourable six-month window. The backtest mean of {V['fc_backtest']} over
{V['fc_folds']} folds is the honest expectation, and a single good split is not
evidence of accuracy.

**Professor:** How do the Power BI measures relate to your Python results?
**Student:** Every measure carries an explicit delivered-lines filter and was
compared against its SQL equivalent:
{V['pbi_matched']} of {V['pbi_val']} match, plus
{V['pbi_consistency']} cross-surface consistency checks. So the model reports
the same {V['revenue']} the pipeline computed.

**Professor:** Show me you understand your own weakest result.
**Student:** The customer-level prediction. It is the only component whose
individual output I would not act on. The correct improvement is structural —
a two-stage model, a classifier for whether the customer orders and a regressor
for how much given they do — and that is in future scope, not claimed as done.
"""


def mock_difficult():
    return f"""
# 12 — Mock Viva 3 (Difficult)

{HEADER}

**Professor:** Your entire project rests on data you generated yourself. Why
should I take any of it seriously?
**Student:** Take the method seriously, not the numbers — that is how the
report frames it. The generator sets skewed value, seasonality, discounting and
returns. It does not set the segment structure, the ARI between two independent
schemes, the silhouette, or how predictable next-quarter revenue turned out to
be. One of those emerged as the opposite of what I expected.

**Professor:** Which one?
**Student:** Prediction. I expected moderate accuracy and got R²
{V['pred_r2']}. I reported it as weak and explained the cause rather than
switching to a model that scored better after the fact.

**Professor:** Isn't reporting a weak result just an excuse for a weak model?
**Student:** It would be if I had not tested alternatives. Random forest,
gradient boosting and a tuned forest were all fitted and none was materially
better, which points to a weak signal rather than an inadequate model. And the
selection rule — {V['pred_rule']} — was fixed before I saw any of them.

**Professor:** Anyone can claim a rule was fixed in advance. Prove it.
**Student:** The rules are published with the results in the model metadata and
the report, and the K-selection table shows every K evaluated against all three
rules with an eligibility column — including the values that failed. If I had
chosen after the fact, the failing values would not be in the table.

**Professor:** Your silhouette is {V['silhouette']}. In most textbooks that is
described as weak structure.
**Student:** That is a fair reading, and I do not describe it as strong. The
base is a continuum, not four separated populations. What makes the clustering
usable is not separation — it is that the cluster profiles differ materially,
cluster 0 being {V['hv_cust_pct']} of customers and {V['hv_rev_pct']} of
revenue, and that an independent rule-based method finds the same group.

**Professor:** So if the structure is weak, could a different K give a
completely different story?
**Student:** A different K gives different boundaries, yes. What is stable is
the high-value group — it appears at every eligible K and under the rule-based
scheme too. The middle of the base is where the assignment is sensitive, which
is exactly where I say the rules are arbitrary.

**Professor:** You report {V['audit_total']} automated checks. Isn't that
theatre?
**Student:** It caught three real defects, which is the test of whether it is
theatre. A documentation sentence describing recency as a churn warning, in a
project that defines no churn event; a stale figure quoting an older audit
count; and a filename in the appendix that did not match the persisted model.
All three were fixed at source and the artefacts regenerated.

**Professor:** Your appendix had a wrong filename. What else is wrong that the
audit did not catch?
**Student:** I cannot know by definition. What I can say is what the audit does
not cover: it does not test the *correctness* of a business judgement, it does
not detect drift, and it cannot validate the Power BI pages because Desktop was
unavailable. Those are gaps I would name before someone else does.

**Professor:** On that — you present Power BI work but no Power BI screenshot.
**Student:** Correct, and every caption says so. Desktop is Windows-only and
the project was built on Linux. What is complete and validated is the semantic
model, the {V['pbi_measures']} DAX measures — {V['pbi_matched']} of
{V['pbi_val']} matching SQL — the Power Query scripts, the theme and a build
guide. The page layouts are design mockups rendered from the real data. I would
rather show a labelled mockup than claim a screenshot I do not have.

**Professor:** Suppose I told you the discount finding is spurious.
**Student:** You might be right, and the project cannot rule it out. Deeper
discounts may be applied to situations that are already low-margin rather than
causing low margin. That is why the recommendation is a controlled experiment
rather than a price change, and why the report calls it an association in every
place it appears.

**Professor:** What would that experiment look like?
**Student:** Randomly assign comparable orders or customer groups to discount
levels within a category, hold everything else constant, and compare realised
margin. Without randomisation you are measuring the discount policy, not the
discount effect.

**Professor:** Your forecast interval is enormous — nearly a crore wide. What
use is that?
**Student:** It is honest at this history length. {V['fc_total']} point
estimate against an 80% interval of {V['fc_low80']} to {V['fc_high80']}. The
use is planning: commit against the lower bound, size capacity against the
point. A narrow interval from {V['fc_series']} monthly observations would be a
false claim.

**Professor:** What if the true value falls outside your 95% interval?
**Student:** Then either the model is misspecified or something outside the
revenue series moved — a price change, a promotion, a supply problem. The model
is univariate, so it cannot see any of those. That is a stated limitation, and
the remedy is external regressors, which is future scope.

**Professor:** You have no churn model. Most customer analytics projects have
one.
**Student:** Because this dataset defines no churn event — no contract, no
cancellation, no explicit lapse. Any churn label would have been invented by me
and then predicted by me, which proves nothing. I report recency-based
inactivity and never use the word churn for a result. Building one properly
starts with the business defining the label.

**Professor:** How is your inactivity flag better than an arbitrary rule?
**Student:** It is not "better" — it is grounded. The median gap between
consecutive orders is {V['median_gap']} days, so a customer silent for several
times that is behaving differently from the base. That is more defensible than
90 days chosen because it is a quarter, but it is still a threshold, not a
model.

**Professor:** If I gave you this project to review, what would you criticise?
**Student:** Three things. Hyperparameter search was shallow — a few
configurations, no systematic grid. Interpretability stops at permutation
importance; no SHAP. And there is no deployment or monitoring at all, so
nothing in the system would tell you when it has gone stale.

**Professor:** What is the single claim in your report you are least sure of?
**Student:** That the platform's outputs are complete. Consistent and
reconciled I can evidence with the audit. Complete is a judgement — it means I
believe nothing material is missing, and I cannot prove that.

**Professor:** Final question. Why does this project deserve a good grade?
**Student:** Not because the models are strong — one of them is not. Because
every number in it is traceable to the file that produced it, every model was
chosen by a rule fixed before the results, weak results are reported as weak,
an association is never called causation, and the integration is tested by
{V['audit_total']} automated checks rather than asserted.
"""


def speaking_script():
    return f"""
# Presentation Speaking Script

{HEADER}

This script matches the 22-slide deck at
`outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx`.
Do not read the slides aloud — the slide carries the evidence, you carry the
argument.

---

## Spoken introductions

### Elevator pitch — 15 seconds
"I built a customer revenue intelligence platform: it takes retail transaction
data and turns it into customer segments, value estimates, a revenue forecast
and a working application. The headline finding is that the top 20% of
customers produce {V['top20']} of revenue."

### Elevator pitch — 30 seconds
"My project is a customer revenue intelligence platform, built on a synthetic
retail dataset of {V['clean_rows']} order lines and {V['cust_buy']} customers
over {V['months']} months. It segments customers two independent ways,
estimates their forward value, predicts next-quarter revenue, forecasts company
revenue six months ahead, and delivers all of it through a Power BI model and a
{V['app_pages']}-page Streamlit application. The main finding is
concentration — the top 20% of customers carry {V['top20']} of
{V['revenue']} in revenue."

### 30–45 second answer to "Tell me about your project."
*(Problem → Methodology → Technology → Output → Business value)*

"Businesses report revenue in aggregate but take decisions at customer level,
so the questions that matter — who is valuable, who is going quiet, what will
they spend next — go unanswered. My project builds one platform that answers
them. It cleans a synthetic dataset of {V['clean_rows']} order lines against
explicit business rules, segments customers with RFM and K-Means, estimates
customer value, predicts next-quarter revenue and forecasts company revenue,
then reconciles everything in SQL and delivers it through Power BI and
Streamlit. It is built in Python, SQL and DAX. The output is a
{V['app_pages']}-page application and eighteen evidence-linked
recommendations. The business value is a short, specific list of customers
worth protecting — starting with the top decile, which carries {V['top10']} of
revenue."

### 1 minute
"The problem is that transaction data accumulates faster than it becomes
decisions. My dataset is synthetic, generated with a fixed seed for academic
demonstration — {V['raw_rows']} raw order lines cleaning to
{V['clean_rows']} validated lines, {V['cust_buy']} customers,
{V['products']} products, {V['regions']} regions, {V['months']} months,
{V['revenue']} of delivered revenue.

On analytics: I cleaned the data against business rules that all return zero
failures after treatment, then characterised the revenue base — growth of
{V['growth_2024']} then {V['growth_2025']} with margin rising to
{V['margin_2025']}, and value heavily concentrated.

On machine learning: I scored every customer on RFM into
{V['rfm_segments']} segments and separately clustered them with K-Means at K =
{V['k']}. The two agree on the high-value group with an ARI of
{V['ari_vs_rfm']}.

On prediction and forecasting: a customer-quarter model reaching test R²
{V['pred_r2']} — better than every baseline but weak, and I report it that way
— and a {V['fc_model']} forecast of {V['fc_horizon']} months at
{V['fc_backtest']} backtest MAPE.

On delivery: {V['sql_queries']} SQL queries reconciling the metrics
independently, a Power BI model with {V['pbi_measures']} DAX measures, and a
working {V['app_pages']}-page Streamlit application that loads the real trained
models."

### 2 minutes / 3-minute explanation

**Opening — the problem.** "Retail businesses record transactions far faster
than they convert them into decisions. Revenue gets reported by month, category
and region, but the questions that drive growth are customer-level: which
customers matter most, which are going quiet, what will each spend next
quarter, and what will total revenue be. Four specific gaps follow — aggregate
reporting hides the customer, value and activity get treated as one thing,
planning is backward-looking, and analysis in notebooks never reaches the
decision-maker."

**Data.** "The dataset is synthetic, generated with seed {V['seed']} for
academic demonstration — it describes no real company. {V['raw_rows']} raw
order lines, {V['clean_rows']} after cleaning, {V['cust_buy']} purchasing
customers, {V['products']} products across {V['categories']} categories,
{V['regions']} regions, {V['start']} to {V['end']}. One rule governs
everything: revenue counts delivered lines only."

**Methodology.** "Cleaning is rule-driven with an audit trail —
{V['missing_before']} rows failed a business rule before treatment, zero after.
Then {F['dataset']['clean_cols'] - F['dataset']['raw_cols']} engineered columns
for calendar, revenue, margin, bands, outlier flags and arithmetic
reconciliation."

**Analytics.** "EDA established the baseline: {V['revenue']} revenue at
{V['margin']} margin, the top 20% of customers at {V['top20']} of revenue,
{V['top_cat']} leading volume at {V['top_cat_margin']} margin while
{V['best_margin_cat']} earns {V['best_margin']}, and the zero-discount band
carrying the best margin in {V['disc_best_in']} of {V['cats_tested']}
categories."

**Machine learning.** "Two independent segmentations. RFM scores every customer
on recency, frequency and monetary value at reference date {V['ref_date']} into
{V['rfm_segments']} rule-based segments. K-Means clusters the same features
after a log-and-scale pipeline, with K = {V['k']} chosen by three rules fixed
in advance. They agree on the high-value group at ARI {V['ari_vs_rfm']}."

**Prediction.** "A panel of {V['panel_rows']} customer-quarter rows,
{V['pred_features']} features computed strictly before each cutoff, split out
of time. {V['pred_model']} selected by a pre-declared rule. Test R²
{V['pred_r2']} — better than every baseline but weak, because
{V['pred_zero']} of customer-quarters are zero."

**Forecasting.** "Company-level monthly revenue, {V['fc_series']} months.
{V['fc_model']} selected on rolling-origin backtesting.
{V['fc_horizon']}-month forecast of {V['fc_total']}, 80% interval
{V['fc_low80']} to {V['fc_high80']}, honest expected error {V['fc_backtest']}."

**Deployment.** "{V['sql_queries']} SQL queries reproduce the metrics
independently — all {V['sql_checks']} checks pass. A Power BI star schema with
{V['pbi_measures']} DAX measures, {V['pbi_matched']} of {V['pbi_val']}
validated against SQL. And a {V['app_pages']}-page Streamlit application that
loads the actual persisted models, tested headlessly at
{V['app_passed']}/{V['app_tests']}."

**Outcome.** "Value is concentrated and two independent methods name the same
group. {V['clv_at_risk']} high-value customers are inactive for 180+ days.
Volume leader and margin leader are different categories. And reliability
differs by horizon — the company forecast is usable, individual prediction is
not, and the project says both."

---

## Slide-by-slide script

### Slide 1 — Title
**Shown:** Project title, your details, guide, internship organisation.
**Say:** "Good morning. I am Swagata Das, MBA Data Science and AI at Apex
Institute of Management, Chandigarh University. This is my summer internship
project, carried out at Tutorsuite Technologies LLP, Kolkata, under the
guidance of Kuldeep Dubey."
**Important:** Keep it to fifteen seconds; the content starts on slide 2.
**Follow-up:** "What was your role at the organisation?" — Say plainly what you
built.

### Slide 2 — Introduction
**Shown:** Six points framing the business problem.
**Say:** "The problem is not a shortage of data, it is the gap between data and
decisions. Aggregate reporting cannot tell a month carried by a few large
customers from one built on a broad base — so it cannot tell you where to spend
retention effort."
**Important:** Frame the problem before any technique.
**Follow-up:** "Why customer-level rather than better reporting?" — Because the
decisions are taken at customer level.

### Slide 3 — About the Organization
**Shown:** Internship details; the synthetic-data statement.
**Say:** "The internship was at Tutorsuite Technologies LLP. The dataset is
synthetic — generated for academic demonstration — so nothing here describes
the organisation's real business."
**Important:** Say "synthetic" before anyone asks. It is a strength here: no
confidentiality constraint, full reproducibility, a known ground truth to audit
cleaning against.
**Follow-up:** "Would this work on real data?" — The method transfers; the
numbers do not.

### Slide 4 — About Customer Revenue Intelligence
**Shown:** The pipeline diagram, customer data through to business decisions.
**Say:** "Each arrow is a real module, not a concept. Customer data, then
understanding, then segmentation, value, prediction, forecasting, and finally a
decision."
**Important:** The diagram is generated from the actual pipeline.
**Follow-up:** "Which stage was hardest?" — Prediction, and I will explain why.

### Slide 5 — Review of Related Literature
**Shown:** Six strands with methods and relevance.
**Say:** "None of these techniques is novel and I claim no novelty. What the
literature gave me was discipline — Rousseeuw for choosing K, Hyndman for
insisting a forecast beats a naive benchmark, Gupta for separating measured
historical value from estimated forward value."
**Important:** Every citation is real and appears in the report's 38 references.
**Follow-up:** "Which paper justified your K?" — Silhouette from Rousseeuw,
applied only after stability rules fixed in advance.

### Slide 6 — Research Gap & Significance
**Shown:** The practical gap and the integrated solution.
**Say:** "The gap is integration and traceability, not method. Prior research
has combined several of these; what is rarely shown end to end is one validated
dataset and one revenue definition flowing through every stage, reconciled
against an independent SQL implementation."
**Important:** Do not claim nobody has combined these before.
**Follow-up:** "So what is actually new?" — The auditable integration, tested
by {V['audit_total']} checks.

### Slide 7 — Objectives
**Shown:** Eleven numbered objectives.
**Say:** "All eleven were implemented — none is aspirational, and each is
answered by an identified section of the report."
**Important:** Be ready to point to where each one is answered.
**Follow-up:** "Which objective is weakest?" — Objective 6, and I report it
honestly.

### Slide 8 — Research Methodology
**Shown:** The implementation flowchart with three decision gates.
**Say:** "What makes this a methodology rather than a sequence of scripts is
the gates. No analysis runs until every business rule returns zero failing
rows. No K is accepted unless it passes rules fixed in advance. No forecast
model is accepted unless it beats both naive baselines."
**Important:** The gates are the answer to "how do you know it is right?"
**Follow-up:** "Did a gate ever reject something?" — Yes, K values failing the
minimum-share and stability rules are in the evaluation table.

### Slide 9 — Dataset & Preprocessing
**Shown:** Dataset properties and the before/after rule table.
**Say:** "Every rule is evaluated on the raw data, the failing count is logged,
a treatment is applied, and the rule is re-evaluated. A rule that does not
return zero afterwards is a failure of the cleaning stage, not an acceptable
residue."
**Important:** {V['missing_before']} rows failed before; zero after.
**Follow-up:** "How did you handle missing values?" — By column, by meaning;
some recovered by arithmetic, none dropped silently.

### Slide 10 — Exploratory Data Analysis
**Shown:** Monthly revenue trend; category revenue versus profit.
**Say:** "Each chart answers a business question. The first asks whether the
business is growing and whether it is buying growth with margin — yes and no.
The second separates the volume leader from the margin leader."
**Important:** {V['top_cat']} is {V['top_cat_rev']} of revenue but only
{V['top_cat_profit']} of profit.
**Follow-up:** "Is October seasonality?" — An observed regularity in all three
years; the formal test does not confirm it at {V['fc_series']} observations.

### Slide 11 — Customer Intelligence: RFM & K-Means
**Shown:** Revenue by RFM segment; customers per cluster.
**Say:** "Two independent routes to the same place. RFM is rules I can explain
line by line; K-Means is unsupervised and does not know my rules. They agree on
the high-value group at ARI {V['ari_vs_rfm']} and diverge in the middle, which
tells me where my boundaries are arbitrary."
**Important:** K = {V['k']} was chosen by three rules fixed before the results.
**Follow-up:** "Why is the silhouette only {V['silhouette']}?" — Because the
base is a continuum; I report it rather than hide it.

### Slide 12 — Customer Lifetime Value
**Shown:** Historical value; the forward-value model comparison.
**Say:** "Two quantities that must never be added. Historical value is
measured: {V['clv_hist_profit']} of profit already earned. Forward value is
estimated by a {V['clv_model'].lower()} with R² {V['clv_r2']} and Spearman
{V['clv_spearman']} — it ranks customers much better than it predicts their
exact value, so I use it to order a queue of attention."
**Important:** {V['clv_at_risk']} high-value customers inactive 180+ days,
holding {V['clv_at_risk_rev']}.
**Follow-up:** "Why not BG/NBD?" — Fitted for comparison; its dropout
assumption needs a longer history than {V['months']} months.

### Slide 13 — Revenue Prediction
**Shown:** Target, split, model comparison table, honest reading.
**Say:** "This is the weakest result in the project and I would rather explain
it than dress it up. The model beats every baseline — the naive
previous-quarter rule scores R² {V['naive_r2']} — but reaches only
{V['pred_r2']}, because {V['pred_zero']} of customer-quarters have a zero
actual value. Total bias is {V['pred_bias']}, so it is usable at portfolio
level and not for one customer."
**Important:** Do not oversell. The honesty is worth more than the number.
**Follow-up:** "How would you fix it?" — A two-stage model: will they order,
and if so how much.

### Slide 14 — Sales Forecasting
**Shown:** Actual versus forecast with intervals.
**Say:** "Prediction and forecasting are different tasks — per customer per
quarter versus one company series over time. {V['fc_model']} was selected
because it had the lowest mean backtest error and beat both naive baselines, a
rule set before the results. I quote {V['fc_backtest']} backtest MAPE, not the
favourable single-split {V['fc_test_mape']}."
**Important:** Plan against the interval, not the point estimate.
**Follow-up:** "What if the forecast is wrong?" — It will be; the interval is
the honest statement, and the model is univariate.

### Slide 15 — SQL-Based Business Analytics
**Shown:** Database size, techniques, six findings computed in SQL.
**Say:** "This layer exists to be an independent implementation. Same
definitions, different language — so when SQL and Python agree on revenue,
profit and margin to the paisa, that is evidence rather than a copy."
**Important:** {V['sql_queries']} queries, all {V['sql_checks']} checks pass.
**Follow-up:** "Which window functions?" — ROW_NUMBER and RANK for top-N,
running totals for the concentration curve, LAG for growth.

### Slide 16 — Power BI Executive Dashboard
**Shown:** Star schema stats and one page design.
**Say:** "Say this plainly: Power BI Desktop is Windows-only and was not
available, so what you see is a design mockup rendered from the real data, not
a screenshot. What is complete and validated is the model —
{V['pbi_measures']} DAX measures, {V['pbi_matched']} of {V['pbi_val']} matching
their SQL equivalents — plus the Power Query scripts, the theme and a build
guide."
**Important:** Claiming a screenshot you do not have would undermine the whole
deck.
**Follow-up:** "How long to finish it?" — An afternoon on a Windows machine
with those artefacts.

### Slide 17 — Streamlit Application
**Shown:** A real screenshot of the running app.
**Say:** "This one is a real screenshot, and I am happy to run it live. The
architectural point is that the app is a presentation layer — it loads the same
persisted models and the same outputs the pipeline wrote, and computes no
metric of its own, so a number on screen cannot drift from the report."
**Important:** {V['app_passed']}/{V['app_tests']} headless tests pass.
**Follow-up:** "Is it deployed?" — No. It runs locally; deployment is future
scope.

### Slide 18 — Findings and Suggestions
**Shown:** Six findings with implication and recommendation.
**Say:** "Every row is traceable to an output file, and the full set of
eighteen recommendations is in the application. The one to read carefully is
the discount row — it is an association measured on observed orders, which is
exactly why the recommendation is an experiment rather than a price change."
**Important:** Never call an association a cause.
**Follow-up:** "Which would you do first?" — Give the top decile a named owner;
it costs almost nothing and protects {V['top10']} of revenue.

### Slide 19 — Future scope
**Shown:** Six directions.
**Say:** "Each of these answers a specific weakness named in the report, not a
wish list — real data, a churn label defined by the business, a two-stage
prediction model, external regressors, a discount experiment, and monitoring."
**Important:** Keep future work clearly separate from completed work.
**Follow-up:** "What would you do first with six more months?" — The two-stage
prediction model and drift monitoring.

### Slide 20 — Conclusion
**Shown:** Four closing points.
**Say:** "The through-line is raw transactions in, business decisions out, with
every step reproducible and every number traceable. If you want one outcome:
value is concentrated, two independent methods found the same group, and the
platform names them."
**Important:** End on the finding, not on the technology.
**Follow-up:** "What is the single most valuable outcome?" — The concentration
finding, because it changes where effort goes.

### Slide 21 — References
**Shown:** Eleven of the 38 references.
**Say:** "These are the most load-bearing of the 38 in the report. Every one is
a real publication or official documentation."
**Important:** Be ready to name the reference behind a specific decision.
**Follow-up:** "Which reference shaped the project most?" — Hyndman, for the
rule that a forecast must beat a naive benchmark.

### Slide 22 — Thank You
**Say:** "Thank you. I am happy to take questions, and I can run the
application live if you would like to see it working."
**Important:** Offer the demo; it is real and it works.
"""


def rapid_fire():
    return f"""
# Rapid-Fire Round — 50 Questions

{HEADER}

1. **What is AI?** Systems that perform tasks normally requiring human
   intelligence.
2. **What is ML?** Algorithms that learn patterns from data rather than
   following hand-written rules.
3. **Supervised learning?** Learning from labelled examples — my revenue
   prediction and customer-value models.
4. **Unsupervised learning?** Finding structure without labels — my K-Means
   segmentation.
5. **Clustering?** Grouping similar observations together without labels.
6. **Regression?** Predicting a continuous number — here, rupees of revenue or
   profit.
7. **Classification?** Predicting a category. Not used in this project.
8. **Forecasting?** Projecting a time series forward — {V['fc_horizon']} months
   at {V['fc_backtest']} backtest MAPE.
9. **RFM?** Recency, Frequency, Monetary scoring — {V['rfm_segments']} segments
   over {V['rfm_scored']} customers.
10. **Recency?** Days since the last delivered purchase, at {V['ref_date']}.
11. **Frequency?** Count of distinct delivered orders.
12. **Monetary?** Total delivered sales value for the customer.
13. **CLV?** Customer lifetime value — reported here as measured historical and
    estimated forward, separately.
14. **K-Means?** Partitions data into K clusters minimising within-cluster
    variance. K = {V['k']} here.
15. **Centroid?** The mean position of a cluster's members.
16. **Inertia?** Sum of squared distances to assigned centroids —
    {V['inertia']} at K = {V['k']}.
17. **Elbow method?** Plot inertia against K and look for the flattening point.
    A heuristic, not a rule.
18. **Silhouette score?** How much closer a point is to its own cluster than to
    the next — {V['silhouette']} here.
19. **ARI?** Chance-corrected agreement between two partitions —
    {V['ari_vs_rfm']} between RFM and clusters.
20. **PCA?** Projection into fewer dimensions. Used for visualisation only:
    {V['pca_total']} in two components.
21. **Scaling?** Putting features on a comparable range so distance is not
    dominated by one variable.
22. **StandardScaler?** Centres to mean 0 and scales to unit variance.
23. **log1p?** log(1 + x) — compresses skew and handles zeros safely.
24. **EDA?** Exploratory data analysis — understanding structure before
    modelling.
25. **Feature engineering?** Creating variables that carry business meaning.
    {F['dataset']['clean_cols'] - F['dataset']['raw_cols']} columns added here.
26. **Pandas?** Python library for labelled tabular data.
27. **NumPy?** Python's numerical array library, underneath pandas and
    scikit-learn.
28. **scikit-learn?** Python's general machine-learning library. Version 1.8.0
    here.
29. **statsmodels?** Statistical modelling and time-series library. Version
    0.15.0 here.
30. **SQL?** Language for querying relational databases —
    {V['sql_queries']} queries here.
31. **JOIN?** Combines rows from two tables on a related column.
32. **GROUP BY?** Collapses rows into groups for aggregation.
33. **Window function?** Computes across related rows without collapsing them.
34. **CTE?** A named temporary result defined with WITH.
35. **Power BI?** Microsoft BI tool — {V['pbi_tables']} tables,
    {V['pbi_measures']} DAX measures here.
36. **DAX?** Power BI's formula language, evaluated in filter context.
37. **Measure vs calculated column?** A measure is computed at query time in
    filter context; a column is stored at refresh.
38. **Star schema?** One fact table surrounded by dimensions.
39. **Streamlit?** Python framework for data applications —
    {V['app_pages']} pages here.
40. **MAE?** Mean absolute error — {V['pred_mae']} on prediction.
41. **RMSE?** Root mean squared error — penalises large errors more —
    {V['pred_rmse']}.
42. **R²?** Share of variance explained — {V['pred_r2']} on prediction.
43. **MAPE?** Mean absolute percentage error — {V['fc_test_mape']} on the
    forecast test split.
44. **WAPE?** Weighted absolute percentage error — used where actuals hit zero;
    {V['pred_wape']} here.
45. **Spearman ρ?** Rank correlation — {V['clv_spearman']} for customer value.
46. **Overfitting?** Fitting training noise; the score does not survive unseen
    data.
47. **Underfitting?** Too simple to capture the signal.
48. **Data leakage?** Using information unavailable at prediction time.
49. **Temporal leakage?** Training on periods after the test period. Avoided by
    a chronological split.
50. **Backtesting?** Rolling-origin time-series validation —
    {V['fc_folds']} folds, mean MAPE {V['fc_backtest']}.
"""


def one_line_answers():
    return f"""
# One-Line Answers — Last-Minute Revision

{HEADER}

| Term | One-line answer |
| --- | --- |
| **Customer Revenue Intelligence** | Converting transaction records into customer-level understanding and forward-looking revenue decisions. |
| **RFM** | Scoring each customer 1–5 on Recency, Frequency and Monetary value to place them in a named segment. |
| **Recency** | Days since the customer's last delivered purchase, measured at {V['ref_date']}. |
| **Frequency** | Count of distinct orders with at least one delivered line. |
| **Monetary** | Total delivered sales value for that customer, after discount. |
| **CLV** | Customer lifetime value — here reported as measured historical profit and separately as estimated forward twelve-month profit. |
| **K-Means** | Unsupervised algorithm partitioning customers into K clusters by minimising within-cluster variance; K = {V['k']} here. |
| **Centroid** | The mean position of a cluster's members in feature space. |
| **Silhouette** | How much closer a point is to its own cluster than to the nearest other; {V['silhouette']} here. |
| **ARI** | Chance-corrected agreement between two partitions; {V['ari_vs_rfm']} between my RFM segments and clusters. |
| **PCA** | Projection into fewer dimensions; used here for visualisation only, {V['pca_total']} in two components. |
| **EDA** | Examining distributions, trends, relationships and outliers before modelling. |
| **Feature engineering** | Creating variables that carry business meaning; {F['dataset']['clean_cols'] - F['dataset']['raw_cols']} added to the cleaned dataset. |
| **Revenue Prediction** | Supervised regression of a customer's delivered revenue in the next quarter; {V['pred_model']}, test R² {V['pred_r2']}. |
| **Forecasting** | Projecting company monthly revenue forward from its own history; {V['fc_model']}, {V['fc_horizon']} months, {V['fc_backtest']} backtest MAPE. |
| **Prediction vs forecasting** | Prediction is per customer per quarter using customer features; forecasting is one company series over time. |
| **MAE** | Mean absolute error, same unit as the target; {V['pred_mae']} on prediction. |
| **RMSE** | Root mean squared error; penalises large misses more; {V['pred_rmse']}. |
| **R²** | Share of variance explained relative to predicting the mean; {V['pred_r2']}. |
| **MAPE** | Mean absolute percentage error; unusable near zero actuals; {V['fc_test_mape']} on the forecast test split. |
| **WAPE** | Weighted absolute percentage error; used where actuals hit zero; {V['pred_wape']}. |
| **Spearman ρ** | Rank correlation; {V['clv_spearman']} for the customer-value model. |
| **SQL** | Language for querying relational data; {V['sql_tables']} tables, {V['sql_queries']} queries, all {V['sql_checks']} checks passing. |
| **Window function** | Computes across related rows without collapsing them; used in {F['sql']['techniques'][5]['Queries_Using_It']} project queries. |
| **CTE** | A named temporary result defined with `WITH`; used in {F['sql']['techniques'][3]['Queries_Using_It']} queries. |
| **Power BI** | Microsoft BI tool; star schema of {V['pbi_tables']} tables with {V['pbi_measures']} DAX measures. |
| **DAX** | Power BI's formula language, evaluated within filter context. |
| **Measure vs calculated column** | A measure computes at query time in filter context; a column is computed and stored at refresh. |
| **Star schema** | One central fact table surrounded by dimension tables. |
| **Streamlit** | Python framework for data applications; {V['app_pages']} pages, {V['app_passed']}/{V['app_tests']} tests passing. |
| **Dashboard vs application** | A dashboard presents pre-computed measures; an application executes logic and loads real models. |
| **Data leakage** | Using information at training time that would not exist at prediction time. |
| **Temporal leakage** | Training on periods that come after the test period; avoided with a chronological split. |
| **Overfitting** | Fitting training noise so the score does not survive unseen data. |
| **Underfitting** | A model too simple to capture the available signal. |
| **Backtesting** | Rolling-origin time-series validation; {V['fc_folds']} folds here. |
| **Stationarity** | Statistical properties constant over time; ADF p = {V['adf_p']}, so not stationary in level. |
| **Prediction interval** | The range a future observation is expected to fall in; 80% = {V['fc_low80']} to {V['fc_high80']}. |
| **Delivered revenue** | The project's one revenue rule — delivered order lines only, in Python, SQL and DAX alike. |
| **Inactivity (not churn)** | Recency-based flag; the dataset defines no churn event, so the word churn never describes a result. |

## The ten numbers to know cold

| Number | Value |
| --- | --- |
| Delivered revenue | {V['revenue']} at {V['margin']} margin |
| Cleaned dataset | {V['clean_rows']} lines, {V['cust_buy']} customers, {V['months']} months |
| Top 20% of customers | {V['top20']} of revenue |
| Champions | {V['champ_cust_pct']} of customers, {V['champ_rev_pct']} of revenue |
| K-Means | K = {V['k']}, silhouette {V['silhouette']}, ARI vs RFM {V['ari_vs_rfm']} |
| Customer value model | {V['clv_model']}, R² {V['clv_r2']}, Spearman {V['clv_spearman']} |
| Revenue prediction | {V['pred_model']}, test R² {V['pred_r2']}, MAE {V['pred_mae']} |
| Forecast | {V['fc_model']}, {V['fc_total']} over {V['fc_horizon']} months, {V['fc_backtest']} backtest MAPE |
| Delivery | {V['sql_queries']} SQL queries, {V['pbi_measures']} DAX measures, {V['app_pages']} app pages |
| Project audit | {V['audit_total']} checks, {V['audit_pass']} pass, {V['audit_fail']} fail |
"""


def top20():
    return f"""
# Top 20 Revision Questions

{HEADER}

Each entry gives a short answer for a quick response, a fuller answer if the
examiner presses, and the project-specific evidence.

---

### 1. Tell me about your project.
**Short:** A customer revenue intelligence platform that takes retail
transaction data through segmentation, value analysis, prediction and
forecasting, and delivers it through Power BI and a Streamlit application.
**Detailed:** It runs on a synthetic dataset of {V['clean_rows']} validated
order lines covering {V['cust_buy']} customers over {V['months']} months. Data
is cleaned against explicit business rules, customers are segmented two
independent ways, their value is quantified as measured historical and
estimated forward, next-quarter revenue is predicted and company revenue
forecast, all metrics are reconciled in SQL, and the results reach the user
through a semantic model and a working application.
**Project evidence:** {V['revenue']} delivered revenue at {V['margin']} margin;
{V['audit_total']} automated checks with {V['audit_pass']} passing.

### 2. Why is your dataset synthetic?
**Short:** It was a deliberate choice for an academic deliverable.
**Detailed:** No confidentiality constraint, full reproducibility from seed
{V['seed']}, and a known ground truth to audit the cleaning against. The cost
is that the numbers describe no real business, which the report states in the
abstract and four sections.
**Project evidence:** The generator injects missing values, non-ISO dates,
numbers as text, out-of-range discounts and duplicates, so cleaning has real
work and can be verified against the injection log.

### 3. What is RFM and why did you use it?
**Short:** Scoring customers on Recency, Frequency and Monetary value; used
because it is interpretable and auditable.
**Detailed:** Each dimension is scored 1–5 on quintiles at reference date
{V['ref_date']}, with recency reversed. Fixed rules place customers into
{V['rfm_segments']} named segments. A business user can see exactly why a
customer landed where it did, which a clustering cannot offer.
**Project evidence:** {V['rfm_scored']} customers scored; Champions
{V['champ_n']} customers ({V['champ_cust_pct']}) holding
{V['champ_rev_pct']} of revenue.

### 4. How did you choose K?
**Short:** By three rules fixed before I saw the results, then the highest
silhouette among the values that qualified.
**Detailed:** K ≥ {V['min_k']}; no cluster below {V['min_share']} of the base;
bootstrap stability ARI ≥ {V['min_ari']}. Only then did silhouette decide.
Using the elbow or silhouette alone would have let me read the diagnostic to
suit the answer I wanted.
**Project evidence:** K = {V['k']}, silhouette {V['silhouette']}, stability
{V['ari_stability']}; the evaluation table shows every K tested with its
eligibility against all three rules.

### 5. Why run both RFM and K-Means?
**Short:** As independent checks on each other.
**Detailed:** RFM imposes boundaries I chose; K-Means finds whatever grouping
the data contains. Agreement between them is evidence; disagreement locates
where my rules are arbitrary.
**Project evidence:** ARI {V['ari_vs_rfm']} — substantial agreement on the
high-value group, real divergence in the middle of the base.

### 6. Why did you scale the features before clustering?
**Short:** Because K-Means uses Euclidean distance and the features are on
wildly different scales.
**Detailed:** Monetary value runs to lakhs while frequency is a count under 50,
and all three are right-skewed. Without transformation, monetary value alone
would determine every cluster.
**Project evidence:** The persisted pipeline applies {V['preprocessing']}, and
the audit re-derives the cluster labels from that saved pipeline exactly.

### 7. Historical versus predicted customer value — what is the difference?
**Short:** One is measured, the other estimated, and they are never added.
**Detailed:** Historical value is delivered profit already earned. Forward value
is a model's estimate of the next twelve months, trained out of time and
validated with stated error.
**Project evidence:** Historical {V['clv_hist_profit']} (mean
{V['clv_mean']}, median {V['clv_median']}); forward model MAE {V['clv_mae']},
R² {V['clv_r2']}, Spearman {V['clv_spearman']}.

### 8. What is your prediction target, exactly?
**Short:** {V['pred_target']}.
**Detailed:** The unit is {V['pred_unit']}. The panel carries
{V['panel_rows']} rows with {V['pred_features']} features, all computed
strictly from data available before that quarter began.
**Project evidence:** Split {V['train_rows']} / {V['val_rows']} /
{V['test_rows']}, chronological, test window {V['test_period']}.

### 9. Why an out-of-time split rather than a random one?
**Short:** Because the task is predicting the future from the past.
**Detailed:** A random split would let the model learn from quarters that come
after the ones it is tested on — an inflated score that means nothing in
practice. Chronological splitting is the only honest evaluation for this task.
**Project evidence:** Train {V['train_period']}, validation
{V['val_period']}, test {V['test_period']}, plus a leakage audit that
recomputes sampled features independently from the transaction table.

### 10. Your prediction R² is only {V['pred_r2']}. Explain.
**Short:** It is weak, it beats every baseline, and the cause is structural.
**Detailed:** {V['pred_zero']} of customer-quarters have a zero actual value,
so the target is dominated by whether someone orders at all rather than by how
much. Total bias is {V['pred_bias']}, so the model is usable at portfolio level
and not for an individual customer.
**Project evidence:** Naive previous-quarter baseline R² {V['naive_r2']}, MAE
{V['naive_mae']}; the selected model MAE {V['pred_mae']}. The fix — a two-stage
model — is named in future scope, not claimed as done.

### 11. What is the difference between prediction and forecasting?
**Short:** Different unit, different method, different metric.
**Detailed:** Prediction is cross-sectional and supervised — customer ×
quarter, using customer features. Forecasting is univariate time-series — one
company-level series projected from its own history.
**Project evidence:** Prediction R² {V['pred_r2']} with WAPE
{V['pred_wape']}; forecast {V['fc_backtest']} backtest MAPE over
{V['fc_folds']} folds.

### 12. How did you select the forecasting model?
**Short:** By a rule fixed in advance, on rolling-origin backtesting.
**Detailed:** {V['fc_rule']}. Naive, seasonal naive, ETS, ARIMA, SARIMA and
Theta were all fitted; Theta had the lowest mean backtest MAPE and beat both
naive baselines on test MAE.
**Project evidence:** {V['fc_model']}, α = {V['fc_alpha']}, test MAE
{V['fc_test_mae']}, backtest mean MAPE {V['fc_backtest']}.

### 13. Why do you quote the backtest error rather than the test error?
**Short:** Because a single favourable split is not evidence of accuracy.
**Detailed:** The test MAPE of {V['fc_test_mape']} comes from one six-month
window. The mean over {V['fc_folds']} rolling-origin folds is
{V['fc_backtest']}, and that is what the report, the deck and the application
all quote.
**Project evidence:** The forecast is {V['fc_total']} with an 80% interval of
{V['fc_low80']} to {V['fc_high80']}.

### 14. What does the SQL layer add that Python did not already give you?
**Short:** An independent implementation, so agreement becomes evidence.
**Detailed:** Same definitions, different language. If revenue, profit, margin,
order count and AOV agree between pandas and SQL, that is a genuine check — not
a copy of the same code path.
**Project evidence:** {V['sql_tables']} tables, {V['sql_views']} views,
{V['sql_queries']} queries, {V['sql_checks']}/{V['sql_checks']} validation and
{V['sql_quality']} data-quality checks passing.

### 15. Why both Power BI and Streamlit?
**Short:** One is a governed semantic model, the other runs the models.
**Detailed:** Power BI gives a business audience self-service slicing over
{V['pbi_measures']} conformed measures. It cannot load a scikit-learn or
statsmodels object. Streamlit loads the actual persisted models, runs
predictions, accepts uploads and returns downloads.
**Project evidence:** {V['pbi_matched']}/{V['pbi_val']} DAX measures validated
against SQL; {V['app_passed']}/{V['app_tests']} application tests passing.

### 16. Why is there no Power BI screenshot?
**Short:** Power BI Desktop is Windows-only and the project was built on Linux.
**Detailed:** The semantic model, DAX library, Power Query scripts, theme and
build guide are complete and validated. The nine page layouts are design
mockups rendered from the real data, and every caption says so. No screenshot
is claimed.
**Project evidence:** This is stated in the report's Sections 3.9, 4.9 and 5.3,
on the deck's Power BI slide, and in the validation checklist.

### 17. What are your main findings?
**Short:** Value is concentrated, two independent methods agree on who holds
it, and reliability differs sharply by horizon.
**Detailed:** Top 10% of customers = {V['top10']} of revenue, top 20% =
{V['top20']}; Champions {V['champ_cust_pct']} of customers carry
{V['champ_rev_pct']} of revenue; {V['clv_at_risk']} high-value customers are
inactive 180+ days; volume leader and margin leader are different categories;
company forecasting works, individual prediction does not.
**Project evidence:** Eighteen recommendations, each carrying its evidence and
the analytical stage that produced it.

### 18. Why is the discount finding a recommendation to experiment rather than
to change policy?
**Short:** Because it is an association measured on observed orders.
**Detailed:** Deeper discounts may be applied to situations that are already
low-margin rather than causing low margin. Nothing in observational data can
separate those, so the only honest next step is a controlled test.
**Project evidence:** {V['disc0_band']} band at {V['disc0_margin']} margin
against {V['disc_hi_margin']} at {V['disc_hi_band']}; best-margin band in
{V['disc_best_in']} of {V['cats_tested']} categories.

### 19. Why does your project have no churn model?
**Short:** Because the dataset defines no churn event.
**Detailed:** There is no contract, no cancellation and no explicit lapse, so
any churn label would have been invented by me and then predicted by me. The
project reports recency-based **inactivity** instead and never uses the word
churn to describe a result.
**Project evidence:** The audit includes an automated scan confirming no
document asserts churn; the median inter-purchase gap of {V['median_gap']} days
is the grounded basis for the inactivity threshold.

### 20. What are the limitations of your project?
**Short:** Synthetic data, short history, weak individual prediction, a
univariate forecast, association not causation, no churn label, Power BI not
rendered, no user testing, no deployment.
**Detailed:** Each is stated in the report with the section that reports the
affected result, and each maps to a specific future-scope item rather than
being left as a caveat.
**Project evidence:** The report's Section 5.3 and the validation checklist
both carry the list; the deck repeats it on the Future Scope slide.
"""


def revision_sheet():
    return f"""
# Final Revision Sheet

{HEADER}

Read this on the way to the viva.

## Project in 5 lines

1. A customer revenue intelligence platform: transactions in, business
   decisions out.
2. Synthetic retail dataset, {V['clean_rows']} validated order lines,
   {V['cust_buy']} customers, {V['months']} months, {V['revenue']} delivered
   revenue.
3. Two independent segmentations, customer value, next-quarter prediction and a
   six-month forecast — all on one validated dataset and one revenue
   definition.
4. Delivered through {V['sql_queries']} reconciled SQL queries, a Power BI
   model of {V['pbi_measures']} DAX measures, and a {V['app_pages']}-page
   Streamlit application.
5. Integration tested, not asserted: {V['audit_total']} automated checks,
   {V['audit_pass']} pass, {V['audit_fail']} fail.

## Dataset in 5 lines

1. Synthetic, generated from seed {V['seed']}; describes no real business.
2. {V['raw_rows']} raw order lines → {V['clean_rows']} clean;
   {V['dupes']} duplicates removed.
3. {V['cust_reg']} registered customers, {V['cust_buy']} purchasing;
   {V['products']} products, {V['categories']} categories.
4. {V['cities']} cities, {V['states']} states, {V['regions']} regions;
   {V['start']} to {V['end']}.
5. Revenue counts **delivered lines only**; {V['lost_value']}
   ({V['lost_share']}) of booked value lost to returns and cancellations.

## Methodology in 5 lines

1. Rule-driven cleaning with an audit trail: {V['missing_before']} rows failed a
   rule before treatment, zero after.
2. {F['dataset']['clean_cols'] - F['dataset']['raw_cols']} engineered columns —
   calendar, delivered flag, revenue/profit/margin, bands, outlier flags,
   arithmetic reconciliation.
3. EDA across time, product, geography, discount, payment and customer.
4. Three validation gates: business rules, K-selection, forecast baseline.
5. Every stage a separate module with one entry point, reading only the
   persisted output of the stage before it.

## ML in 5 lines

1. RFM: quintile scores at {V['ref_date']}, {V['rfm_segments']} rule-based
   segments over {V['rfm_scored']} customers.
2. K-Means on the same three features after {V['preprocessing']}.
3. K = {V['k']} by three pre-declared rules, then highest silhouette:
   {V['silhouette']}.
4. Clusters: {V['cluster_sizes']}.
5. Agreement with RFM: ARI {V['ari_vs_rfm']} — same high-value group, divergence
   in the middle.

## Prediction in 5 lines

1. Target: {V['pred_target']}.
2. Panel {V['panel_rows']} customer-quarter rows, {V['pred_features']} features,
   all pre-cutoff.
3. Chronological split {V['train_rows']} / {V['val_rows']} / {V['test_rows']};
   leakage audit found none.
4. {V['pred_model']} selected by rule: {V['pred_rule']}.
5. Test MAE {V['pred_mae']}, R² {V['pred_r2']}, bias {V['pred_bias']} — weak per
   customer, usable at portfolio level, because {V['pred_zero']} of
   customer-quarters are zero.

## Forecasting in 5 lines

1. Company monthly delivered revenue, {V['fc_series']} months.
2. ADF p = {V['adf_p']} — non-stationary in level.
3. Naive, seasonal naive, ETS, ARIMA/SARIMA and Theta tested; {V['fc_model']}
   selected.
4. Test MAE {V['fc_test_mae']}, test MAPE {V['fc_test_mape']}, **backtest mean
   MAPE {V['fc_backtest']}** over {V['fc_folds']} folds — quote the backtest.
5. {V['fc_horizon']} months ({V['fc_months']}): {V['fc_total']}, 80% interval
   {V['fc_low80']}–{V['fc_high80']}, against {V['fc_prev6']} in the previous six
   months.

## Dashboard in 5 lines

1. SQL: {V['sql_tables']} tables, {V['sql_views']} views,
   {V['sql_queries']} queries, all {V['sql_checks']} checks pass.
2. Power BI: star schema, {V['pbi_tables']} tables, {V['pbi_rels']}
   relationships, {V['pbi_measures']} DAX measures in {V['pbi_folders']}
   folders.
3. {V['pbi_matched']}/{V['pbi_val']} measures validated against SQL;
   {V['pbi_consistency']} consistency checks pass.
4. Power BI Desktop unavailable (Windows-only) — the nine pages are labelled
   **design mockups**, not screenshots.
5. Streamlit: {V['app_pages']} pages, loads persisted models, computes no metric
   of its own, {V['app_passed']}/{V['app_tests']} headless tests pass.

## Key findings

- Top 10% of customers = {V['top10']} of revenue; top 20% = {V['top20']}.
- Champions: {V['champ_cust_pct']} of customers, {V['champ_rev_pct']} of
  revenue.
- Two independent methods find the same high-value group (ARI
  {V['ari_vs_rfm']}).
- {V['clv_at_risk']} high-value customers inactive 180+ days, holding
  {V['clv_at_risk_rev']}.
- Repeat customers: {V['repeat_share_cust']} of the base,
  {V['repeat_share_rev']} of revenue ({V['repeat_avg']} vs
  {V['single_avg']} each).
- {V['top_cat']} leads volume ({V['top_cat_rev']}) at the lowest margin
  ({V['top_cat_margin']}); {V['best_margin_cat']} earns {V['best_margin']}.
- Zero-discount band is best-margin in {V['disc_best_in']} of
  {V['cats_tested']} categories — association, not cause.
- Growth is not bought with margin: {V['growth_2024']} then
  {V['growth_2025']}, margin rising to {V['margin_2025']}.
- No regional margin problem: {V['region_gaps']} of {V['region_pairs']} pairs
  below national.
- Company forecasting works ({V['fc_backtest']}); individual prediction does not
  ({V['pred_r2']}).

## Limitations

Synthetic data · {V['months']}-month history · weak individual prediction ·
univariate forecast · association not causation · no churn label in the data ·
Power BI pages are mockups · no user testing · no deployment or monitoring.

## Future scope

Real data under a data-protection agreement · a business-defined inactivity
label and a supervised model for it · two-stage prediction (will they order,
then how much) · external regressors in the forecast · a controlled discount
experiment · scheduled re-runs with drift monitoring · complete the Power BI
build on Windows.

## Technologies

Python 3.11 · pandas · NumPy · SciPy · scikit-learn 1.8.0 · statsmodels 0.15.0 ·
joblib · Matplotlib · Seaborn · Plotly · SQLite · DAX · Power Query M ·
Streamlit · Jupyter ({V['notebooks']} notebooks) ·
{V['py_files']} Python modules, {V['py_lines']} lines.

## If you are stuck

- **A number you cannot recall:** "That value was not something I memorised —
  it is in the report; what I can tell you is the direction and why."
- **A technique you did not use:** "It was considered as a possible extension,
  but it was not part of the implemented pipeline."
- **A result the project does not contain:** "That value was not directly
  measured in this project."

Never invent a number. An honest gap costs one mark; a fabricated figure that
is checked costs the viva.
"""


FILES = [
    ("project_master_summary.md", master_summary),
    ("01_basic_viva_questions.md", basic_questions),
    ("02_intermediate_technical_questions.md", intermediate_questions),
    ("03_advanced_data_science_questions.md", advanced_questions),
    ("04_sql_viva.md", sql_viva),
    ("05_powerbi_viva.md", powerbi_viva),
    ("06_streamlit_viva.md", streamlit_viva),
    ("07_business_questions.md", business_questions),
    ("08_challenging_questions.md", challenging_questions),
    ("09_trick_questions.md", trick_questions),
    ("10_mock_viva_easy.md", mock_easy),
    ("11_mock_viva_medium.md", mock_medium),
    ("12_mock_viva_difficult.md", mock_difficult),
    ("presentation_speaking_script.md", speaking_script),
    ("rapid_fire_questions.md", rapid_fire),
    ("one_line_answers.md", one_line_answers),
    ("top_20_viva_questions.md", top20),
    ("final_revision_sheet.md", revision_sheet),
]


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    build_values()
    OUT.mkdir(parents=True, exist_ok=True)
    total_q = 0
    for name, builder in FILES:
        text = builder()
        path = write(name, text)
        qs = text.count("\n**") + text.count("\n### ")
        total_q += qs
        print(f"  {path.relative_to(ROOT)}  "
              f"({len(text.split()):,} words)")
    print(f"\n{len(FILES)} files written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
