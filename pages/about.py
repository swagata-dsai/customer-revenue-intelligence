"""ABOUT PROJECT - what this is, how it was built, and what it is not."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("About this project",
               "Customer Revenue Intelligence - an MBA Data Science internship project.", "ℹ️")

meta = dl.load_metadata() or {}
models = dl.load_models()
sales = dl.load_sales()
customers = dl.load_customers()

c1, c2 = st.columns([1.3, 1], gap="medium")
with c1:
    ui.panel(
        '<h4>Project title</h4>'
        '<p>Customer Revenue Intelligence: An Interactive Data Science Platform for Customer '
        'Segmentation, Revenue Prediction and Business Growth</p>'
        '<h4 style="margin-top:0.9rem">Objective</h4>'
        '<p>Transform customer transaction data into actionable business intelligence using '
        'analytics, machine learning, customer segmentation, customer value modelling, revenue '
        'prediction and time-series forecasting - and deliver it in a form a business user can '
        'actually use.</p>'
        '<h4 style="margin-top:0.9rem">Dataset</h4>'
        '<p><strong>The data is synthetic.</strong> It was generated for this project with a '
        'fixed seed, then deliberately degraded with realistic data-quality issues so the '
        'cleaning step had something to do. It does not describe a real company or real '
        'customers, and no finding here is a claim about a real market. The method is what '
        'transfers; the numbers are a demonstration.</p>')
with c2:
    if sales is not None:
        k = dl.kpis(sales)
        ui.panel(
            f'<h4>Scale</h4>'
            f'<p>{len(sales):,} order lines · {k["orders"]:,} delivered orders</p>'
            f'<p>{k["customers"]:,} purchasing customers'
            f'{f" of {len(customers):,} registered" if customers is not None else ""}</p>'
            f'<p>{sales["Product_ID"].nunique()} products · '
            f'{sales["City"].nunique()} cities · {sales["Region"].nunique()} regions</p>'
            f'<p>{sales["Order_Date"].min():%b %Y} to {sales["Order_Date"].max():%b %Y} '
            f'({k["months"]} months)</p>'
            f'<p class="note">Customer snapshot (RFM, clusters, customer value): '
            f'{dl.REFERENCE_DATE}</p>')

# --------------------------------------------------------------- methodology
ui.section("Methodology", "Each stage is a completed, validated pipeline step")
STEPS = [
    ("1-2", "Project setup & dataset design", "Structure, config, synthetic data generator "
     "(seed 42), data dictionary"),
    ("3", "Data cleaning", "Duplicates, missing values, type and rule repair; every correction "
     "logged and audited against ground truth"),
    ("4", "Exploratory data analysis", "KPIs, distributions, outlier classification, "
     "correlations, 41 figures"),
    ("5", "RFM analysis", "Recency, frequency, monetary scoring and 11 rule-based segments at a "
     "fixed reference date"),
    ("6", "K-Means segmentation", "Log-transformed, scaled features; K chosen on elbow and "
     "silhouette; clusters described from their centroids"),
    ("7", "Customer lifetime value", "Historical value, a time-based model for the next 12 "
     "months' profit, BG/NBD checked and Gamma-Gamma rejected on its own assumption test"),
    ("8", "Revenue prediction", "Customer x quarter panel, leakage audit, temporal split, "
     "baselines, model selection rule fixed in advance"),
    ("9", "Sales forecasting", "Monthly series, stationarity tests, ETS / ARIMA / Theta, rolling "
     "backtest, prediction intervals"),
    ("10", "SQL business analytics", "Normalised database, 57 queries, 20 business questions, "
     "56 validation checks"),
    ("11", "Power BI dashboard", "Star schema, 84 DAX measures, validated against SQL and Python"),
    ("12", "Streamlit application", "This application"),
]
for start in range(0, len(STEPS), 2):
    for col, (num, title, note) in zip(st.columns(2, gap="medium"), STEPS[start:start + 2]):
        with col:
            ui.panel(f'<h4 style="font-size:0.95rem">'
                     f'<span style="color:{ui.THEME["cat"][0]}">Step {num}</span> · {title}</h4>'
                     f'<p class="note">{note}</p>')

st.markdown(
    f'<div class="cri-panel"><p style="font-family:monospace;font-size:0.82rem;'
    f'line-height:1.9;color:{ui.THEME["ink"]};margin:0">'
    'Data Collection → Data Cleaning → EDA → RFM Analysis → K-Means Segmentation → CLV<br>'
    '&nbsp;&nbsp;&nbsp;&nbsp;→ Revenue Prediction → Sales Forecasting → SQL Analytics '
    '→ Power BI → Streamlit'
    '</p></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------- stack
ui.section("Technology stack", "Only what the project actually uses")
STACK = [
    ("Python 3.11", "Every pipeline step"),
    ("pandas · NumPy", "Data handling and aggregation"),
    ("scikit-learn", "K-Means, linear / tree models, preprocessing pipelines"),
    ("statsmodels", "ETS, ARIMA, Theta, ADF and STL for the forecast"),
    ("SciPy", "BG/NBD likelihood, statistical tests"),
    ("SQLite + SQL", "Normalised database, 57 analysis and business queries"),
    ("Power BI", "Star-schema executive dashboard (Step 11)"),
    ("Streamlit", "This interactive application"),
    ("Plotly", "Interactive charts in this application"),
    ("Matplotlib", "Static figures in the notebooks and reports"),
    ("joblib", "Model persistence"),
    ("Jupyter", "Nine executed notebooks documenting each step"),
]
for start in range(0, len(STACK), 4):
    for col, (tech, note) in zip(st.columns(4, gap="small"), STACK[start:start + 4]):
        with col:
            ui.panel(f'<h4 style="font-size:0.9rem">{tech}</h4><p class="note">{note}</p>')

# ------------------------------------------------------------------- models
ui.section("Models in this application", "Loaded from `models/` at runtime")
rows = []
for key, entry in models.items():
    rows.append({"Model": entry["description"], "File": f"models/{entry['file']}",
                 "Status": {"loaded": "Loaded", "missing": "Not found",
                            "error": "Could not be loaded"}[entry["status"]]})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

rp, fc = meta.get("revenue_prediction"), meta.get("forecasting")
c1, c2 = st.columns(2, gap="medium")
with c1:
    if rp:
        t = rp.get("test_metrics", {})
        ui.panel(
            f'<h4>Revenue prediction (Step 8)</h4>'
            f'<p>{rp.get("model_type")} · target: {rp.get("target")}</p>'
            f'<p>Test MAE {ui.format_currency(t.get("MAE"), unit="inr")} · '
            f'RMSE {ui.format_currency(t.get("RMSE"), unit="inr")} · R² {t.get("R2"):.3f}</p>'
            f'<p class="note">Reported as it is: useful for ranking customers and for aggregate '
            f'planning, not for per-customer commitments.</p>')
with c2:
    if fc:
        t = (fc.get("metrics") or {}).get("test", {})
        ui.panel(
            f'<h4>Sales forecasting (Step 9)</h4>'
            f'<p>{fc.get("model_type")} · {fc.get("forecast_horizon_months")}-month horizon</p>'
            f'<p>Test MAE {ui.format_currency(t.get("MAE"))} · '
            f'MAPE {t.get("MAPE_%"):.2f}% · WAPE {t.get("WAPE_%"):.2f}%</p>'
            f'<p class="note">Company-level and univariate, fitted on 36 months, with the '
            f'model\'s own prediction intervals.</p>')

# -------------------------------------------------------------- limitations
ui.section("What this project does not claim")
ui.panel(
    '<p>· <strong>Synthetic data.</strong> No finding describes a real market.</p>'
    '<p>· <strong>No churn label.</strong> Customers are described as active or inactive by '
    'recency; no churn event is defined for this data, so none is asserted.</p>'
    '<p>· <strong>Associations, not causes.</strong> The discount, payment-method and regional '
    'comparisons are observational.</p>'
    '<p>· <strong>Snapshots age.</strong> Segments, customer value and the forecast are as at '
    'their reference dates and must be re-run as new data arrives.</p>'
    '<p>· <strong>A weak customer-level model is reported as weak.</strong> The Step 8 R² is '
    '0.056 on held-out data and the application says so wherever the model appears.</p>')

# ------------------------------------------------------------------ reports
ui.section("Where to read more")
DOCS = [
    ("outputs/reports/eda_summary.md", "Exploratory analysis (Step 4)"),
    ("outputs/reports/rfm_methodology.md", "RFM method and segment rules (Step 5)"),
    ("outputs/reports/kmeans_model_report.md", "K-Means model report (Step 6)"),
    ("outputs/reports/clv_analysis_report.md", "Customer lifetime value (Step 7)"),
    ("outputs/reports/revenue_prediction_report.md", "Revenue prediction (Step 8)"),
    ("outputs/reports/forecasting_methodology.md", "Forecasting methodology (Step 9)"),
    ("outputs/reports/sql_analysis_methodology.md", "SQL analytics (Step 10)"),
    ("outputs/reports/powerbi_dashboard_documentation.md", "Power BI dashboard (Step 11)"),
    ("outputs/reports/streamlit_testing_report.md", "This application's test report (Step 12)"),
]
import config  # noqa: E402
rows = [{"Document": label, "Path": path,
         "Available": "Yes" if (config.PROJECT_ROOT / path).exists() else "Not generated yet"}
        for path, label in DOCS]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption("Customer Revenue Intelligence · MBA Data Science Internship Project · "
           "synthetic dataset. Built with Python, SQL, Power BI and Streamlit.")
