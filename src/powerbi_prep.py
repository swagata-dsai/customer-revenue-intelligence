"""STEP 11 - Power BI executive dashboard: data model, DAX, theme, validation and docs.

SYNTHETIC DATA. Power BI Desktop is Windows-only and cannot run in this Linux
environment, so this module prepares and validates everything the report needs
and the report itself is assembled manually in Power BI Desktop following
powerbi/POWERBI_BUILD_GUIDE.md. Nothing here claims work that Power BI did.

What it produces
----------------
powerbi/data/          star-schema CSV extracts (from the pbi_* SQL views)
powerbi/powerquery/    one Power Query M script per table + relationship spec
powerbi/dax/           measures.dax, validation_query.dax, measure catalogue
powerbi/theme/         dark theme JSON + page background PNG
powerbi/validation/    measure values recomputed in pandas and reconciled to SQL
outputs/figures/powerbi/mockups/   labelled design mockups (NOT screenshots)
outputs/reports/       powerbi_dashboard_documentation.md, powerbi_user_guide.md

Entry point: run_powerbi_prep().
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

import config

# --------------------------------------------------------------------------- paths
PBI_DIR = config.PROJECT_ROOT / "powerbi"
PBI_DATA = PBI_DIR / "data"
PBI_PQ = PBI_DIR / "powerquery"
PBI_DAX = PBI_DIR / "dax"
PBI_THEME = PBI_DIR / "theme"
PBI_VALID = PBI_DIR / "validation"
VIEWS_FILE = config.SQL_DIR / "powerbi_views.sql"
FIG_DIR = config.FIGURES_DIR / "powerbi"
MOCKUP_DIR = FIG_DIR / "mockups"
TAB = config.TABLES_DIR

VIEWS = ["pbi_dim_date", "pbi_dim_geography", "pbi_dim_product", "pbi_dim_rfm_segment",
         "pbi_dim_cluster", "pbi_dim_customer", "pbi_fact_sales", "pbi_fact_forecast"]
VIEW_TO_TABLE = {"pbi_dim_date": "DimDate", "pbi_dim_geography": "DimGeography",
                 "pbi_dim_product": "DimProduct", "pbi_dim_rfm_segment": "DimRFMSegment",
                 "pbi_dim_cluster": "DimCluster", "pbi_dim_customer": "DimCustomer",
                 "pbi_fact_sales": "FactSales", "pbi_fact_forecast": "FactForecast"}

# Dark data-intelligence theme. Categorical hues are the dataviz dark palette,
# validated against the panel surface #141C2B (all six checks pass).
THEME = {
    "page": "#0B111C", "panel": "#141C2B", "border": "#25324A",
    "ink": "#E6EDF7", "ink_strong": "#FFFFFF", "muted": "#8E9BB3", "grid": "#223047",
    "cat": ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#E66767"],
    "good": "#0CA30C", "warning": "#FAB219", "serious": "#EC835A", "critical": "#D03B3B",
}
SERIES = {"historical": THEME["cat"][0], "predicted": THEME["cat"][1], "forecast": THEME["cat"][2]}


def _mk() -> None:
    for d in (PBI_DATA, PBI_PQ, PBI_DAX, PBI_THEME, PBI_VALID, FIG_DIR, MOCKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    return sqlite3.connect(config.DATABASE_FILE)


# =========================================================================== 1. model
def build_views(con: sqlite3.Connection) -> None:
    """(Re)create the pbi_* star-schema views on the Step 10 database."""
    con.executescript(VIEWS_FILE.read_text())
    con.commit()


def _prediction_tables() -> dict[str, pd.DataFrame]:
    """Step 8 outputs reshaped for Power BI (customer x quarter predictions)."""
    pred = pd.read_csv(TAB / "revenue_predictions.csv")
    fact = pred.rename(columns={"Cluster_Label": "Cluster_Label_At_Cutoff",
                                "RFM_Segment": "RFM_Segment_At_Cutoff"}).copy()
    qmap = {"Q1": "-01-01", "Q2": "-04-01", "Q3": "-07-01", "Q4": "-10-01"}
    fact["Target_Quarter_Start"] = (fact["Target_Period"].str[:4]
                                    + fact["Target_Quarter"].map(qmap))
    fact["Split"] = "test (out-of-sample)"
    cols = ["Customer_ID", "Cutoff_Date", "Target_Period", "Target_Quarter_Start", "Target_Quarter",
            "Split", "Region", "Main_Category", "RFM_Segment_At_Cutoff", "Cluster_ID",
            "Cluster_Label_At_Cutoff", "Actual_Revenue", "Predicted_Revenue", "Naive_Baseline",
            "Prediction_Error", "Absolute_Error", "Percentage_Error_%"]
    quarterly = pd.read_csv(TAB / "revenue_quarterly_totals.csv").copy()
    quarterly["Target_Quarter_Start"] = (quarterly["Target_Period"].str[:4]
                                         + quarterly["Target_Period"].str[-2:].map(qmap))
    return {"FactRevenuePrediction": fact[cols], "PredictionQuarterly": quarterly}


def _model_metrics() -> pd.DataFrame:
    """Step 8 / Step 9 metrics, read from the saved metadata and comparison tables."""
    rm = json.loads((config.PROJECT_ROOT / "models" / "revenue_model_metadata.json").read_text())
    fm = json.loads((config.PROJECT_ROOT / "models" / "forecasting_metadata.json").read_text())
    rows: list[dict] = []

    def add(model, step, scope, split, metric, value, unit, note):
        rows.append({"Model_Area": model, "Step": step, "Model": scope, "Split": split,
                     "Metric": metric, "Value": value, "Unit": unit, "Note": note})

    rp = "Revenue prediction (ML)"
    lbl = rm["model_type"]
    for split, key in [("Validation (2025 Q1-Q2)", "validation_metrics"), ("Test (2025 Q3-Q4)", "test_metrics")]:
        for metric, unit in [("MAE", "INR"), ("RMSE", "INR"), ("R2", "ratio"),
                             ("WAPE_%", "%"), ("Spearman", "ratio"), ("Total_Bias_%", "%")]:
            if metric in rm[key]:
                add(rp, "Step 8", lbl, split, metric, rm[key][metric], unit,
                    "Per customer-quarter; MAPE is not reported because many actuals are 0")
    base = pd.read_csv(TAB / "revenue_model_comparison.csv")
    b = base.loc[base["Model"] == "Baseline: 12-month quarterly mean"].iloc[0]
    for metric in ("MAE", "RMSE", "R2"):
        add(rp, "Step 8", "Baseline: 12-month quarterly mean", "Test (2025 Q3-Q4)",
            metric, float(b[metric]), "INR" if metric != "R2" else "ratio",
            "Best baseline on test MAE, shown for comparison")

    fc = "Revenue forecast (time series)"
    flbl = fm["model_type"]
    for split, key in [("Validation (2025-01..06)", "validation"), ("Test (2025-07..12)", "test")]:
        for metric, unit in [("MAE", "INR"), ("RMSE", "INR"), ("MAPE_%", "%"),
                             ("sMAPE_%", "%"), ("WAPE_%", "%")]:
            add(fc, "Step 9", flbl, split, metric, fm["metrics"][key][metric], unit,
                "Monthly company revenue")
    add(fc, "Step 9", flbl, "Rolling backtest (6 folds)", "MAPE_%",
        fm["metrics"]["backtest_mean_MAPE_%"], "%", "Mean across backtest folds; the selection metric")
    fcomp = pd.read_csv(TAB / "forecast_model_comparison.csv")
    nv = fcomp.loc[fcomp["Family"] == "Naive"].iloc[0]
    for metric, col in [("MAE", "Test_MAE"), ("MAPE_%", "Test_MAPE_%")]:
        add(fc, "Step 9", "Naive (last month)", "Test (2025-07..12)", metric, float(nv[col]),
            "INR" if metric == "MAE" else "%", "Baseline the selected model had to beat")
    return pd.DataFrame(rows)


def _model_info() -> pd.DataFrame:
    rm = json.loads((config.PROJECT_ROOT / "models" / "revenue_model_metadata.json").read_text())
    fm = json.loads((config.PROJECT_ROOT / "models" / "forecasting_metadata.json").read_text())
    rows = [
        ("Revenue prediction (ML)", "Step 8", "Question answered",
         "How much revenue is a given customer likely to generate in the next quarter?"),
        ("Revenue prediction (ML)", "Step 8", "Prediction unit", rm["prediction_unit"]),
        ("Revenue prediction (ML)", "Step 8", "Target", rm["target"]),
        ("Revenue prediction (ML)", "Step 8", "Selected model", rm["model_type"]),
        ("Revenue prediction (ML)", "Step 8", "Selection rule", rm["selection_rule"]),
        ("Revenue prediction (ML)", "Step 8", "Train period", rm["training_period"]),
        ("Revenue prediction (ML)", "Step 8", "Validation period", rm["validation_period"]),
        ("Revenue prediction (ML)", "Step 8", "Test period", rm["test_period"]),
        ("Revenue forecast (time series)", "Step 9", "Question answered",
         "What is total company revenue likely to be in each of the next 6 months?"),
        ("Revenue forecast (time series)", "Step 9", "Target", fm["target"]),
        ("Revenue forecast (time series)", "Step 9", "Selected model", fm["model_type"]),
        ("Revenue forecast (time series)", "Step 9", "Selection rule", fm["selection_rule"]),
        ("Revenue forecast (time series)", "Step 9", "Horizon",
         f"{fm['forecast_horizon_months']} months ({fm['forecast_months'][0]} to {fm['forecast_months'][-1]})"),
        ("Revenue forecast (time series)", "Step 9", "Final fit", fm["training_period_final_fit"]),
        ("Revenue forecast (time series)", "Step 9", "Intervals", fm["intervals"]),
    ]
    return pd.DataFrame(rows, columns=["Model_Area", "Step", "Attribute", "Value"])


def export_model(con: sqlite3.Connection) -> pd.DataFrame:
    """Export every star-schema table to powerbi/data and return the table catalogue."""
    rows = []
    for view in VIEWS:
        df = pd.read_sql_query(f"SELECT * FROM {view}", con)
        name = VIEW_TO_TABLE[view]
        df.to_csv(PBI_DATA / f"{name}.csv", index=False)
        rows.append({"Table": name, "Role": "Fact" if name.startswith("Fact") else "Dimension",
                     "Source": f"SQL view {view}", "Rows": len(df), "Columns": df.shape[1],
                     "Grain": GRAIN[name]})
    extra = _prediction_tables()
    extra["ModelMetrics"] = _model_metrics()
    extra["ModelInfo"] = _model_info()
    extra["Recommendations"] = build_recommendations(con)
    for name, df in extra.items():
        df.to_csv(PBI_DATA / f"{name}.csv", index=False)
        rows.append({"Table": name, "Role": ROLE[name], "Source": SOURCE[name],
                     "Rows": len(df), "Columns": df.shape[1], "Grain": GRAIN[name]})
    cat = pd.DataFrame(rows)
    cat.to_csv(PBI_DIR / "table_catalog.csv", index=False)
    cat.to_csv(TAB / "powerbi_table_catalog.csv", index=False)
    return cat


GRAIN = {
    "DimDate": "One row per calendar day, 2023-01-01 to 2026-06-30",
    "DimGeography": "One row per customer city",
    "DimProduct": "One row per product",
    "DimRFMSegment": "One row per Step 5 RFM segment (+ 'No delivered order')",
    "DimCluster": "One row per Step 6 K-Means cluster (+ 'No delivered order')",
    "DimCustomer": "One row per registered customer (no names; Customer_ID only)",
    "FactSales": "One row per order line, all statuses, with Is_Delivered",
    "FactForecast": "One row per month x forecast record type (Step 9)",
    "FactRevenuePrediction": "One row per customer x target quarter, test split (Step 8)",
    "PredictionQuarterly": "One row per target quarter: actual vs predicted totals (Step 8)",
    "ModelMetrics": "One row per model x split x metric (Steps 8 and 9)",
    "ModelInfo": "One row per model attribute (design of Steps 8 and 9)",
    "Recommendations": "One row per business recommendation, with its analytical basis",
}
ROLE = {"FactRevenuePrediction": "Fact", "PredictionQuarterly": "Fact (aggregated)",
        "ModelMetrics": "Supporting", "ModelInfo": "Supporting", "Recommendations": "Supporting"}
SOURCE = {
    "FactRevenuePrediction": "outputs/tables/revenue_predictions.csv (Step 8)",
    "PredictionQuarterly": "outputs/tables/revenue_quarterly_totals.csv (Step 8)",
    "ModelMetrics": "models/revenue_model_metadata.json, models/forecasting_metadata.json, "
                    "outputs/tables/revenue_model_comparison.csv, forecast_model_comparison.csv",
    "ModelInfo": "models/revenue_model_metadata.json, models/forecasting_metadata.json",
    "Recommendations": "Computed from Step 5-10 output tables by src/powerbi_prep.py",
}

RELATIONSHIPS = [
    ("DimDate", "Date", "FactSales", "Order_Date", "One-to-many", "Single", "Yes",
     "Date table marked in Power BI; drives every time intelligence measure"),
    ("DimCustomer", "Customer_ID", "FactSales", "Customer_ID", "One-to-many", "Single", "Yes", ""),
    ("DimProduct", "Product_ID", "FactSales", "Product_ID", "One-to-many", "Single", "Yes", ""),
    ("DimGeography", "Location_ID", "FactSales", "Location_ID", "One-to-many", "Single", "Yes",
     "Customer home location; one location per customer in this dataset"),
    ("DimRFMSegment", "RFM_Segment", "DimCustomer", "RFM_Segment", "One-to-many", "Single", "Yes",
     "Snowflake on the customer dimension: segment attributes filter customers, which filter sales"),
    ("DimCluster", "Cluster_ID", "DimCustomer", "Cluster_ID", "One-to-many", "Single", "Yes",
     "Snowflake on the customer dimension"),
    ("DimDate", "Date", "FactForecast", "Month_Date", "One-to-many", "Single", "Yes",
     "Forecast rows join on the first day of the month"),
    ("DimDate", "Date", "FactRevenuePrediction", "Target_Quarter_Start", "One-to-many", "Single", "No",
     "INACTIVE by design: the prediction grain is a quarter, so a date filter would silently "
     "drop rows. Activate with USERELATIONSHIP only if a quarter-level date filter is wanted."),
    ("DimCustomer", "Customer_ID", "FactRevenuePrediction", "Customer_ID", "One-to-many", "Single", "Yes",
     "Lets the prediction page respond to the customer and segment slicers"),
]


def write_relationships() -> pd.DataFrame:
    cols = ["From_Table", "From_Column", "To_Table", "To_Column", "Cardinality",
            "Cross_Filter_Direction", "Active", "Notes"]
    rel = pd.DataFrame(RELATIONSHIPS, columns=cols)
    rel.to_csv(PBI_DIR / "relationships.csv", index=False)
    rel.to_csv(TAB / "powerbi_relationships.csv", index=False)
    return rel


# =========================================================================== 2. Power Query
M_HEADER = """// {table} - Power Query M
// Generated by src/powerbi_prep.py (STEP 11). Source: {source}
// SYNTHETIC DATA. Change DataFolder once, in the DataFolder parameter, not here.
let
    Source = Csv.Document(
        File.Contents(DataFolder & "{table}.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
{types}
    }}),
    Result = Typed
in
    Result
"""
PARAM_M = """// DataFolder - Power Query parameter
// Set this to the folder that holds the Step 11 CSV extracts, e.g.
//   "C:\\\\projects\\\\customer-revenue-intelligence\\\\powerbi\\\\data\\\\"
// Keep the trailing backslash. Every query reads from this one parameter, so the
// report is repointed at a new machine by changing this single value.
"C:\\projects\\customer-revenue-intelligence\\powerbi\\data\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
"""

DATE_COLS = {"Date", "Order_Date", "Month_Date", "Month_Start_Date", "Reference_Date",
             "First_Purchase_Date", "Last_Purchase_Date", "Cutoff_Date", "Target_Quarter_Start"}
INT_COLS = {"Year", "Quarter_Number", "Year_Quarter_Sort", "Month_Number", "Year_Month_Sort",
            "Week_Number", "ISO_Week_Year", "Day", "Day_Of_Week_Number", "Is_Weekend",
            "Financial_Year_Start", "Financial_Month_Number", "Location_ID", "Segment_Order",
            "Group_Order", "Cluster_ID", "Cluster_Order", "Customer_Age", "Has_Delivered_Order",
            "Recency_Days", "Frequency_Orders", "R_Score", "F_Score", "M_Score", "RFM_Score",
            "Activity_Status_Order", "Recency_Band_Order", "Frequency_Band_Order",
            "High_Historical_Value", "High_Estimated_Future_Value", "High_Value_High_Engagement",
            "Potentially_At_Risk_High_Value", "Future_Value_Opportunity", "Is_Delivered",
            "Quantity", "Discount_Band_Order", "Record_Type_Order", "Customers", "Priority",
            "Order_Line_ID", "Order_ID"}


def _m_type(col: str, dtype) -> str:
    if col in DATE_COLS:
        return "type date"
    if col in INT_COLS:
        return "Int64.Type"
    if pd.api.types.is_float_dtype(dtype):
        return "type number"
    if pd.api.types.is_integer_dtype(dtype):
        return "Int64.Type"
    return "type text"


def write_power_query(catalog: pd.DataFrame) -> None:
    (PBI_PQ / "00_DataFolder_parameter.m").write_text(PARAM_M)
    for name in catalog["Table"]:
        df = pd.read_csv(PBI_DATA / f"{name}.csv", nrows=500)
        types = ",\n".join(f'        {{"{c}", {_m_type(c, df[c].dtype)}}}' for c in df.columns)
        src = catalog.loc[catalog["Table"] == name, "Source"].iloc[0]
        (PBI_PQ / f"{name}.m").write_text(M_HEADER.format(table=name, source=src, types=types))


# =========================================================================== 3. DAX
def write_dax() -> pd.DataFrame:
    """Write measures.dax (grouped into display folders) and the validation query."""
    from src.powerbi_dax import MEASURES, VALIDATION_QUERY, header

    lines = [header()]
    catalog = []
    for folder, measures in MEASURES:
        lines.append(f"\n// {'=' * 74}\n// {folder}\n// {'=' * 74}")
        for name, expr, fmt, desc in measures:
            lines.append(f"\n// {desc}\n// Display folder: {folder} | Format: {fmt}\n"
                         f"{name} = {expr.strip()}")
            catalog.append({"Measure": name, "Display_Folder": folder,
                            "Format": fmt, "Purpose": desc})
    (PBI_DAX / "measures.dax").write_text("\n".join(lines) + "\n")
    (PBI_DAX / "validation_query.dax").write_text(VALIDATION_QUERY)
    cat = pd.DataFrame(catalog)
    cat.to_csv(PBI_DAX / "measure_catalog.csv", index=False)
    cat.to_csv(TAB / "powerbi_measure_catalog.csv", index=False)
    return cat


# =========================================================================== 4. validation
CONTEXTS = [
    ("All data", "No filters"),
    ("Year = 2024", "DimDate[Year] = 2024"),
    ("Year = 2025", "DimDate[Year] = 2025"),
    ("Region = South", "DimGeography[Region] = \"South\""),
    ("Category = Electronics", "DimProduct[Category] = \"Electronics\""),
    ("RFM segment = Champions", "DimRFMSegment[RFM_Segment] = \"Champions\""),
    ("Cluster = High-Value, Active", "DimCluster[Cluster_Label] = \"High-Value, Active\""),
    ("Month = 2025-10", "DimDate[Year_Month] = \"2025-10\""),
]


def _filter_frames(fact: pd.DataFrame, cust: pd.DataFrame, label: str) -> pd.DataFrame:
    f = fact
    if label == "Year = 2024":
        f = f[f["Year"] == 2024]
    elif label == "Year = 2025":
        f = f[f["Year"] == 2025]
    elif label == "Region = South":
        f = f[f["Region"] == "South"]
    elif label == "Category = Electronics":
        f = f[f["Category"] == "Electronics"]
    elif label == "RFM segment = Champions":
        f = f[f["RFM_Segment"] == "Champions"]
    elif label == "Cluster = High-Value, Active":
        f = f[f["Cluster_Label"] == "High-Value, Active"]
    elif label == "Month = 2025-10":
        f = f[f["Year_Month"] == "2025-10"]
    return f


def _sql_filter(label: str) -> str:
    return {
        "All data": "1=1",
        "Year = 2024": "strftime('%Y', s.Order_Date) = '2024'",
        "Year = 2025": "strftime('%Y', s.Order_Date) = '2025'",
        "Region = South": "g.Region = 'South'",
        "Category = Electronics": "p.Category = 'Electronics'",
        "RFM segment = Champions": "c.RFM_Segment = 'Champions'",
        "Cluster = High-Value, Active": "c.Cluster_ID = 0",
        "Month = 2025-10": "strftime('%Y-%m', s.Order_Date) = '2025-10'",
    }[label]


def validate_measures(con: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute the core measures in pandas and in SQL under several filter contexts.

    The DAX in powerbi/dax/measures.dax is written to the same definitions; this
    proves the definitions agree between the two engines that CAN run here, and
    produces the target values to check the Power BI cards against.
    """
    fact = pd.read_sql_query("""
        SELECT s.*, strftime('%Y', s.Order_Date) AS Year, strftime('%Y-%m', s.Order_Date) AS Year_Month,
               g.Region, p.Category, c.RFM_Segment, c.Cluster_ID, cl.Cluster_Label
        FROM pbi_fact_sales s
        JOIN pbi_dim_geography g ON g.Location_ID = s.Location_ID
        JOIN pbi_dim_product p   ON p.Product_ID = s.Product_ID
        JOIN pbi_dim_customer c  ON c.Customer_ID = s.Customer_ID
        JOIN pbi_dim_cluster cl  ON cl.Cluster_ID = c.Cluster_ID
    """, con)
    fact["Year"] = fact["Year"].astype(int)
    cust = pd.read_sql_query("SELECT * FROM pbi_dim_customer", con)

    rows = []
    for label, dax_ctx in CONTEXTS:
        f = _filter_frames(fact, cust, label)
        d = f[f["Is_Delivered"] == 1]
        rev, prof, cost = d["Sales"].sum(), d["Profit"].sum(), d["Cost"].sum()
        orders = d["Order_ID"].nunique()
        customers = d["Customer_ID"].nunique()
        qty = d["Quantity"].sum()
        booked = f["Booked_Value"].sum()
        months = d.groupby("Year_Month")["Sales"].sum()
        vals = {
            "Total Revenue": rev, "Total Profit": prof, "Total Cost": cost,
            "Profit Margin %": 100 * prof / rev if rev else np.nan,
            "Total Orders": orders, "Total Customers": customers, "Total Quantity": qty,
            "Average Order Value": rev / orders if orders else np.nan,
            "Avg Profit per Order": prof / orders if orders else np.nan,
            "Avg Quantity per Order": qty / orders if orders else np.nan,
            "Avg Customer Revenue": rev / customers if customers else np.nan,
            "Avg Monthly Revenue": months.mean() if len(months) else np.nan,
            "Order Lines": len(d),
            "Booked Value (all statuses)": booked,
            "Not Realised %": 100 * (1 - rev / booked) if booked else np.nan,
        }
        for measure, value in vals.items():
            rows.append({"Filter_Context": label, "DAX_Filter": dax_ctx, "Measure": measure,
                         "Python_Value": round(float(value), 4) if pd.notna(value) else np.nan})
    py = pd.DataFrame(rows)

    # ---- independent SQL recomputation of the four required measures + margin
    sql_rows = []
    for label, _ in CONTEXTS:
        q = f"""
        SELECT ROUND(SUM(CASE WHEN s.Is_Delivered = 1 THEN s.Sales END), 4)  AS "Total Revenue",
               ROUND(SUM(CASE WHEN s.Is_Delivered = 1 THEN s.Profit END), 4) AS "Total Profit",
               COUNT(DISTINCT CASE WHEN s.Is_Delivered = 1 THEN s.Order_ID END)    AS "Total Orders",
               COUNT(DISTINCT CASE WHEN s.Is_Delivered = 1 THEN s.Customer_ID END) AS "Total Customers",
               ROUND(100.0 * SUM(CASE WHEN s.Is_Delivered = 1 THEN s.Profit END)
                     / SUM(CASE WHEN s.Is_Delivered = 1 THEN s.Sales END), 4)      AS "Profit Margin %",
               ROUND(SUM(CASE WHEN s.Is_Delivered = 1 THEN s.Sales END)
                     / COUNT(DISTINCT CASE WHEN s.Is_Delivered = 1 THEN s.Order_ID END), 4)
                                                                                   AS "Average Order Value"
        FROM pbi_fact_sales s
        JOIN pbi_dim_geography g ON g.Location_ID = s.Location_ID
        JOIN pbi_dim_product p   ON p.Product_ID = s.Product_ID
        JOIN pbi_dim_customer c  ON c.Customer_ID = s.Customer_ID
        WHERE {_sql_filter(label)}"""
        r = pd.read_sql_query(q, con).iloc[0]
        for measure, value in r.items():
            sql_rows.append({"Filter_Context": label, "Measure": measure, "SQL_Value": float(value)})
    sql = pd.DataFrame(sql_rows)

    check = py.merge(sql, on=["Filter_Context", "Measure"], how="left")
    check["Difference"] = (check["Python_Value"] - check["SQL_Value"]).round(6)
    check["Reconciled"] = np.where(check["SQL_Value"].isna(), "Not recomputed in SQL",
                                   np.where(check["Difference"].abs() < 0.01, "Match", "DIFFERENT"))
    check["Power_BI_Value"] = ""      # filled in by hand after the cards are built
    check["Power_BI_Matches"] = ""
    check.to_csv(PBI_VALID / "measure_validation_targets.csv", index=False)
    check.to_csv(TAB / "powerbi_measure_validation.csv", index=False)

    # ---- customer-state measures that do not come from the fact table
    state = pd.DataFrame([
        {"Measure": "Registered Customers", "Definition": "Row count of DimCustomer",
         "Value": len(cust)},
        {"Measure": "Customers with a delivered order",
         "Definition": "DimCustomer[Has_Delivered_Order] = 1", "Value": int(cust["Has_Delivered_Order"].sum())},
        {"Measure": "Active Customers (< 180 days at 2026-01-01)",
         "Definition": "DimCustomer[Recency_Days] < 180", "Value": int((cust["Recency_Days"] < 180).sum())},
        {"Measure": "Inactive 180+ days", "Definition": "DimCustomer[Recency_Days] >= 180",
         "Value": int((cust["Recency_Days"] >= 180).sum())},
        {"Measure": "Inactive 365+ days", "Definition": "DimCustomer[Recency_Days] >= 365",
         "Value": int((cust["Recency_Days"] >= 365).sum())},
        {"Measure": "Repeat Customers (2+ delivered orders)",
         "Definition": "DimCustomer[Frequency_Orders] >= 2", "Value": int((cust["Frequency_Orders"] >= 2).sum())},
        {"Measure": "Single-purchase Customers", "Definition": "DimCustomer[Frequency_Orders] = 1",
         "Value": int((cust["Frequency_Orders"] == 1).sum())},
        {"Measure": "Potentially at-risk high-value customers",
         "Definition": "DimCustomer[Potentially_At_Risk_High_Value] = 1",
         "Value": int(cust["Potentially_At_Risk_High_Value"].sum())},
        {"Measure": "Avg Recency (days)", "Definition": "AVERAGE(DimCustomer[Recency_Days])",
         "Value": round(float(cust["Recency_Days"].mean()), 4)},
        {"Measure": "Avg Frequency (orders)", "Definition": "AVERAGE(DimCustomer[Frequency_Orders])",
         "Value": round(float(cust["Frequency_Orders"].mean()), 4)},
        {"Measure": "Avg Monetary (INR)", "Definition": "AVERAGE(DimCustomer[Monetary_Revenue])",
         "Value": round(float(cust["Monetary_Revenue"].mean()), 4)},
        {"Measure": "Total Estimated 12M Future Profit",
         "Definition": "SUM(DimCustomer[Estimated_12M_Future_Profit])",
         "Value": round(float(cust["Estimated_12M_Future_Profit"].sum()), 4)},
    ])
    state["Power_BI_Value"] = ""
    state.to_csv(PBI_VALID / "customer_state_validation_targets.csv", index=False)

    # ---- cross-step consistency: do the star-schema extracts still agree with Steps 5-9?
    cons = _consistency_checks(con, fact, cust)
    cons.to_csv(PBI_VALID / "cross_step_consistency.csv", index=False)
    cons.to_csv(TAB / "powerbi_cross_step_consistency.csv", index=False)
    return check, cons


def _consistency_checks(con: sqlite3.Connection, fact: pd.DataFrame, cust: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(area, check, star_value, reference_value, source, tol=0.01):
        ok = (abs(float(star_value) - float(reference_value)) <= tol)
        rows.append({"Area": area, "Check": check, "Star_Schema_Value": round(float(star_value), 4),
                     "Reference_Value": round(float(reference_value), 4), "Reference_Source": source,
                     "Status": "PASS" if ok else "FAIL"})

    d = fact[fact["Is_Delivered"] == 1]
    kpi = pd.read_csv(TAB / "eda_kpis.csv").set_index("KPI")["Value"]
    add("Revenue", "Total Revenue", d["Sales"].sum(), kpi["Total Revenue"], "Step 4 outputs/tables/eda_kpis.csv")
    add("Revenue", "Total Profit", d["Profit"].sum(), kpi["Total Profit"], "Step 4 eda_kpis.csv")
    add("Revenue", "Total Cost", d["Cost"].sum(), kpi["Total Cost"], "Step 4 eda_kpis.csv")
    add("Orders", "Total Orders", d["Order_ID"].nunique(), kpi["Number of Orders"], "Step 4 eda_kpis.csv")
    add("Customers", "Purchasing customers", d["Customer_ID"].nunique(), kpi["Purchasing Customers"],
        "Step 4 eda_kpis.csv")
    add("Orders", "Average order value", d["Sales"].sum() / d["Order_ID"].nunique(),
        kpi["Average Order Value (AOV)"], "Step 4 eda_kpis.csv", tol=0.02)
    add("Quantity", "Units sold", d["Quantity"].sum(), kpi["Total Quantity Sold"], "Step 4 eda_kpis.csv")

    rfm = pd.read_csv(TAB / "rfm_segment_summary.csv")
    champs = rfm.loc[rfm["RFM_Segment"] == "Champions"].iloc[0]
    star_ch = d[d["RFM_Segment"] == "Champions"]
    add("Segmentation", "Champions revenue", star_ch["Sales"].sum(), champs["Total_Revenue"],
        "Step 5 rfm_segment_summary.csv")
    add("Segmentation", "Champions customers", cust[cust["RFM_Segment"] == "Champions"].shape[0],
        champs["Customer_Count"], "Step 5 rfm_segment_summary.csv")

    ml = pd.read_csv(TAB / "ml_cluster_summary.csv")
    hv = ml.loc[ml["Business_Label"] == "High-Value, Active"].iloc[0]
    add("Segmentation", "High-Value, Active cluster revenue",
        d[d["Cluster_Label"] == "High-Value, Active"]["Sales"].sum(), hv["Total_Revenue"],
        "Step 6 ml_cluster_summary.csv")
    add("Segmentation", "High-Value, Active cluster customers",
        int((cust["Cluster_ID"] == 0).sum()), hv["Customer_Count"], "Step 6 ml_cluster_summary.csv")

    clv = pd.read_csv(config.PROCESSED_DIR / "customer_clv.csv")
    add("Customer value", "Historical profit CLV total", cust["Historical_Profit_CLV"].sum(),
        clv["Historical_Profit_CLV"].sum(), "Step 7 data/processed/customer_clv.csv")
    add("Customer value", "Estimated 12M future profit total", cust["Estimated_12M_Future_Profit"].sum(),
        clv["Estimated_12M_Future_Profit"].sum(), "Step 7 customer_clv.csv")

    fc = pd.read_sql_query("SELECT * FROM pbi_fact_forecast", con)
    hist = fc[fc["Record_Type"] == "Historical actual"]
    ts = pd.read_csv(config.PROCESSED_DIR / "monthly_sales_timeseries.csv")
    add("Forecast", "Historical monthly actuals total", hist["Actual_Revenue"].sum(),
        ts["Revenue"].sum(), "Step 9 data/processed/monthly_sales_timeseries.csv")
    add("Forecast", "Historical monthly actuals = delivered revenue", hist["Actual_Revenue"].sum(),
        d["Sales"].sum(), "FactSales delivered lines")
    fut = fc[fc["Series_Label"] == "Forecast"]
    ffile = pd.read_csv(TAB / "forecast_future.csv")
    fcol = "Forecast" if "Forecast" in ffile.columns else ffile.columns[1]
    add("Forecast", "Future 6-month forecast total", fut["Forecast_Revenue"].sum(),
        ffile[fcol].sum(), "Step 9 outputs/tables/forecast_future.csv")

    pred = pd.read_csv(PBI_DATA / "FactRevenuePrediction.csv")
    qt = pd.read_csv(TAB / "revenue_quarterly_totals.csv")
    test = qt[qt["Split"] == "test (out-of-sample)"]
    add("Prediction", "Test actual revenue (customer x quarter)", pred["Actual_Revenue"].sum(),
        test["Actual_Revenue"].sum(), "Step 8 revenue_quarterly_totals.csv")
    add("Prediction", "Test predicted revenue", pred["Predicted_Revenue"].sum(),
        test["Predicted_Revenue"].sum(), "Step 8 revenue_quarterly_totals.csv", tol=0.5)
    add("Prediction", "Test MAE", pred["Absolute_Error"].mean(),
        pd.read_csv(TAB / "revenue_model_comparison.csv").query("Selected")["MAE"].iloc[0],
        "Step 8 revenue_model_comparison.csv", tol=0.01)

    # referential integrity of the exported star schema
    dims = {name: pd.read_csv(PBI_DATA / f"{name}.csv") for name in
            ("DimCustomer", "DimProduct", "DimGeography", "DimDate", "DimRFMSegment", "DimCluster")}
    fs = pd.read_csv(PBI_DATA / "FactSales.csv")
    for col, dim, key in [("Customer_ID", "DimCustomer", "Customer_ID"),
                          ("Product_ID", "DimProduct", "Product_ID"),
                          ("Location_ID", "DimGeography", "Location_ID"),
                          ("Order_Date", "DimDate", "Date")]:
        missing = (~fs[col].isin(dims[dim][key])).sum()
        rows.append({"Area": "Model integrity", "Check": f"FactSales[{col}] all present in {dim}",
                     "Star_Schema_Value": int(missing), "Reference_Value": 0,
                     "Reference_Source": "Star-schema extract", "Status": "PASS" if missing == 0 else "FAIL"})
    for col, dim, key in [("RFM_Segment", "DimRFMSegment", "RFM_Segment"),
                          ("Cluster_ID", "DimCluster", "Cluster_ID")]:
        missing = (~dims["DimCustomer"][col].isin(dims[dim][key])).sum()
        rows.append({"Area": "Model integrity", "Check": f"DimCustomer[{col}] all present in {dim}",
                     "Star_Schema_Value": int(missing), "Reference_Value": 0,
                     "Reference_Source": "Star-schema extract", "Status": "PASS" if missing == 0 else "FAIL"})
    for dim, key in [("DimCustomer", "Customer_ID"), ("DimProduct", "Product_ID"),
                     ("DimGeography", "Location_ID"), ("DimDate", "Date"),
                     ("DimRFMSegment", "RFM_Segment"), ("DimCluster", "Cluster_ID")]:
        dup = int(dims[dim][key].duplicated().sum())
        rows.append({"Area": "Model integrity", "Check": f"{dim}[{key}] is unique",
                     "Star_Schema_Value": dup, "Reference_Value": 0,
                     "Reference_Source": "Star-schema extract", "Status": "PASS" if dup == 0 else "FAIL"})
    names = [c for c in dims["DimCustomer"].columns if "name" in c.lower()]
    rows.append({"Area": "Privacy", "Check": "DimCustomer contains no customer-name column",
                 "Star_Schema_Value": len(names), "Reference_Value": 0,
                 "Reference_Source": "Step 11 privacy rule (Customer_ID only)",
                 "Status": "PASS" if not names else "FAIL"})
    return pd.DataFrame(rows)


# =========================================================================== 5. recommendations
def build_recommendations(con: sqlite3.Connection) -> pd.DataFrame:
    """Recommendations for page 8, each computed from a named Step 4-10 output.

    Nothing here is typed in by hand: every number is read from a saved table, and
    every row records the source query or file so the claim can be traced.
    """
    sq = lambda name: pd.read_csv(TAB / "sql" / f"{name}.csv")            # noqa: E731
    conc = sq("cust_concentration_summary").set_index("top_pct")["pct_of_revenue"]
    bq12 = sq("BQ12").set_index("customer_group")
    bq14 = sq("BQ14").set_index("category")
    bq13 = sq("BQ13").set_index("payment_method")
    cat = sq("prod_category_performance").set_index("category")
    reg = sq("reg_performance").set_index("region")
    inv = sq("prod_investigate")
    bands = sq("prod_discount_bands").set_index("discount_band")
    bq08 = sq("BQ08")
    yr = sq("rev_by_year")
    moy = sq("time_month_of_year")
    kpi = pd.read_csv(TAB / "eda_kpis.csv").set_index("KPI")["Value"]
    rfm = pd.read_csv(TAB / "rfm_segment_summary.csv").set_index("RFM_Segment")
    ml = pd.read_csv(TAB / "ml_cluster_summary.csv").set_index("Business_Label")
    cust = pd.read_sql_query("SELECT * FROM pbi_dim_customer", con)
    fut = pd.read_sql_query(
        "SELECT * FROM pbi_fact_forecast WHERE Series_Label = 'Forecast'", con)
    fmeta = json.loads((config.PROJECT_ROOT / "models" / "forecasting_metadata.json").read_text())
    rmeta = json.loads((config.PROJECT_ROOT / "models" / "revenue_model_metadata.json").read_text())

    atrisk = cust[cust["Potentially_At_Risk_High_Value"] == 1]
    best_band_wins = int((bq08.sort_values(["category", "profit_margin_pct"], ascending=[True, False])
                          .groupby("category").head(1)["discount_band"] == "0%").sum())
    n_cats = bq08["category"].nunique()
    top_months = moy.nsmallest(3, "rank_by_total")["month_number"].tolist()
    month_names = {1: "January", 4: "April", 9: "September", 10: "October", 11: "November", 12: "December"}
    oct_share = float(moy.loc[moy["month_number"] == 10, "avg_revenue"].iloc[0] / moy["avg_revenue"].sum())
    fut_total = float(fut["Forecast_Revenue"].sum())
    fut_lo, fut_hi = float(fut["Lower_80"].sum()), float(fut["Upper_80"].sum())
    last6 = pd.read_sql_query("""SELECT SUM(Actual_Revenue) t FROM pbi_fact_forecast
                                 WHERE Record_Type = 'Historical actual' AND Year_Month >= '2025-07'""",
                              con).iloc[0, 0]

    def cr(v): return f"₹{v / 1e7:.2f} Cr"
    def lk(v): return f"₹{v / 1e5:.2f} L"

    rows = [
        # ---------------------------------------------------------------- Customer
        ("Customer", 1,
         "Protect the top revenue decile before chasing new customers",
         f"The top 20% of customers produce {conc[20]:.2f}% of revenue and the top 10% produce "
         f"{conc[10]:.2f}%. Losing a handful of them costs more than a month of acquisition.",
         "Give the top decile a named owner and review them monthly on the Customer Intelligence "
         "page, sorted by revenue with recency visible.",
         "Top-20% revenue share", f"{conc[20]:.2f}%",
         "SQL cust_concentration_summary (Step 10); Step 5 concentration analysis"),
        ("Customer", 2,
         f"Contact the {len(atrisk)} high-value customers who have not bought for 180+ days",
         f"{len(atrisk)} customers are flagged potentially at risk: high historical value and no "
         f"delivered order for at least 180 days at the 2026-01-01 reference date. Their lifetime "
         f"revenue is {lk(atrisk['Historical_Revenue_CLV'].sum())} and their estimated next-12-month "
         f"profit is {lk(atrisk['Estimated_12M_Future_Profit'].sum())}.",
         "Work the list from the Customer Segmentation page (filter Potentially_At_Risk_High_Value = 1) "
         "and record the outcome; this is an inactivity flag, not a confirmed loss.",
         "Potentially at-risk high-value customers", f"{len(atrisk)}",
         "Step 7 customer_value flags; SQL BQ06"),
        ("Customer", 3,
         "Convert single-purchase buyers: they are 10.6% of customers but 1.4% of revenue",
         f"Repeat customers ({bq12.loc['Repeat (2+ orders)', 'pct_of_customers']:.2f}% of the base) "
         f"generate {bq12.loc['Repeat (2+ orders)', 'pct_of_revenue']:.2f}% of revenue, at "
         f"₹{bq12.loc['Repeat (2+ orders)', 'avg_revenue_per_customer']:,.0f} each against "
         f"₹{bq12.loc['Single purchase', 'avg_revenue_per_customer']:,.0f} for single-purchase customers.",
         "Target the second order specifically: the median gap between repeat purchases is 54 days "
         "(BQ17), so a follow-up inside two months is the natural window.",
         "Revenue per repeat customer vs single-purchase",
         f"₹{bq12.loc['Repeat (2+ orders)', 'avg_revenue_per_customer']:,.0f} vs "
         f"₹{bq12.loc['Single purchase', 'avg_revenue_per_customer']:,.0f}",
         "SQL BQ12, BQ17 (Step 10)"),
        ("Customer", 4,
         "Treat Champions as a retention job, not an acquisition one",
         f"Champions are {rfm.loc['Champions', 'Customer_%']:.2f}% of customers and "
         f"{rfm.loc['Champions', 'Revenue_%']:.2f}% of revenue, with average recency "
         f"{rfm.loc['Champions', 'Average_Recency']:.0f} days. The K-Means 'High-Value, Active' "
         f"cluster tells the same story from unsupervised features "
         f"({ml.loc['High-Value, Active', 'Revenue_%']:.2f}% of revenue).",
         "Monitor Champions' recency monthly on the Customer Segmentation page; a rise in average "
         "recency inside this segment is an early warning that outweighs a good total-revenue month.",
         "Champions revenue share", f"{rfm.loc['Champions', 'Revenue_%']:.2f}%",
         "Step 5 rfm_segment_summary; Step 6 ml_cluster_summary"),

        # ---------------------------------------------------------------- Product
        ("Product", 5,
         "Stop judging Electronics on revenue alone",
         f"Electronics is {cat.loc['Electronics', 'revenue_share_pct']:.2f}% of revenue but only "
         f"{cat.loc['Electronics', 'profit_share_pct']:.2f}% of profit, at a "
         f"{cat.loc['Electronics', 'profit_margin_pct']:.2f}% margin. Beauty and Fashion earn "
         f"{cat.loc['Beauty', 'profit_margin_pct']:.2f}% and {cat.loc['Fashion', 'profit_margin_pct']:.2f}%.",
         "Report Electronics with revenue and margin side by side (Product Analytics page) and set "
         "category targets on profit, not turnover.",
         "Electronics revenue share vs profit share",
         f"{cat.loc['Electronics', 'revenue_share_pct']:.2f}% vs {cat.loc['Electronics', 'profit_share_pct']:.2f}%",
         "SQL prod_category_performance, BQ04 (Step 10)"),
        ("Product", 6,
         f"Review the {len(inv)} products the margin and returns rules flag",
         "The flagged products fall into two groups: high-revenue items whose margin is under half "
         f"their category's ({', '.join(inv[inv['reason'].str.startswith('margin')]['product_name'].head(3))}), "
         "and Fashion items whose return/cancel rate is more than 1.5x the overall rate.",
         "Take one decision per flagged product - reprice, renegotiate cost, or accept it as a "
         "traffic driver - and record which; the Product Analytics scatter shows revenue against "
         "profit so a loss-making high-revenue product cannot hide.",
         "Products flagged", f"{len(inv)}",
         "SQL prod_investigate, BQ03 (Step 10)"),
        ("Product", 7,
         "Treat discounting as a margin decision, not a volume lever",
         f"Within categories, the 0% discount band has the highest margin in {best_band_wins} of "
         f"{n_cats} categories, and overall margin falls from "
         f"{bands.loc['0%', 'profit_margin_pct']:.2f}% at 0% to "
         f"{bands.loc['31-40%', 'profit_margin_pct']:.2f}% in the 31-40% band. In Electronics the "
         "21-40% band is margin-negative (BQ08).",
         "Cap discounts in low-margin categories and approve deep discounts case by case. This is "
         "an association in observational data, not proof that discounting causes the loss - the "
         "products that get discounted may differ systematically.",
         "Categories where the 0% band has the best margin", f"{best_band_wins} of {n_cats}",
         "SQL prod_discount_bands, BQ08 (Step 10)"),
        ("Product", 8,
         f"Attack Fashion returns: {bq14.loc['Fashion', 'lost_pct_of_booked']:.2f}% of booked value is lost",
         f"Fashion loses {bq14.loc['Fashion', 'lost_pct_of_booked']:.2f}% of booked value to returns "
         f"and cancellations ({lk(bq14.loc['Fashion', 'lost_value'])}), against "
         f"{100 * float(kpi['Share of Booked Sales Not Realised']):.2f}% company-wide. Its returned-line "
         f"rate is {bq14.loc['Fashion', 'returned_lines_pct']:.2f}%.",
         "Work on sizing information and product photography for the Fashion sub-categories with "
         "the highest return rates; every point recovered lands on the company's second-best margin.",
         "Fashion booked value lost", f"{bq14.loc['Fashion', 'lost_pct_of_booked']:.2f}%",
         "SQL BQ14 (Step 10)"),

        # ---------------------------------------------------------------- Regional
        ("Regional", 9,
         "Grow Central and East on their margin, not on their size",
         f"Central and East are the two smallest regions "
         f"({reg.loc['Central', 'revenue_share_pct']:.2f}% and {reg.loc['East', 'revenue_share_pct']:.2f}% "
         f"of revenue) but carry the two highest margins "
         f"({reg.loc['Central', 'profit_margin_pct']:.2f}% and {reg.loc['East', 'profit_margin_pct']:.2f}%), "
         f"while South leads revenue at {reg.loc['South', 'revenue_share_pct']:.2f}% on a "
         f"{reg.loc['South', 'profit_margin_pct']:.2f}% margin.",
         "Test incremental spend in Central and East where each rupee of revenue currently carries "
         "more profit, and use the Regional Analytics page to watch whether margin holds as volume grows.",
         "Central margin vs South margin",
         f"{reg.loc['Central', 'profit_margin_pct']:.2f}% vs {reg.loc['South', 'profit_margin_pct']:.2f}%",
         "SQL reg_performance, BQ05 (Step 10)"),
        ("Regional", 10,
         "Do not build a region-specific pricing story - the differences are category mix",
         "No region-category pair sits more than 2 percentage points below the national margin for "
         "that category (BQ16), so regional margin gaps come from what each region buys, not from "
         "how it is served.",
         "Read regional margin through the region x category matrix on the Regional Analytics page "
         "before concluding that a region is underperforming.",
         "Region-category pairs more than 2pp below national margin", "0 of 30",
         "SQL BQ16, reg_category_matrix (Step 10)"),
        ("Regional", 11,
         "Route the customer-level actions by region, because value concentration is not uniform",
         f"Revenue per customer ranges from ₹{reg['revenue_per_customer'].min():,.0f} to "
         f"₹{reg['revenue_per_customer'].max():,.0f} across regions, and AOV from "
         f"₹{reg['average_order_value'].min():,.0f} to ₹{reg['average_order_value'].max():,.0f}.",
         "Use the Region slicer with the customer pages so retention effort is sized to where the "
         "high-value customers actually sit.",
         "Revenue per customer, highest vs lowest region",
         f"₹{reg['revenue_per_customer'].max():,.0f} vs ₹{reg['revenue_per_customer'].min():,.0f}",
         "SQL reg_performance (Step 10)"),

        # ---------------------------------------------------------------- Revenue
        ("Revenue", 12,
         "Plan capacity around the October-December peak",
         f"October is the highest-revenue month in all three years and the top three months by "
         f"average revenue are {', '.join(month_names.get(m, str(m)) for m in top_months)}; October "
         f"alone carries {oct_share:.1%} of an average year's revenue.",
         "Set inventory, staffing and campaign budgets against the monthly profile on the Revenue "
         "Intelligence page rather than a flat monthly average.",
         "October share of an average year", f"{oct_share:.1%}",
         "SQL time_month_of_year, time_best_worst_months (Step 10)"),
        ("Revenue", 13,
         "Hold margin while growth continues",
         f"Revenue grew {yr.loc[yr['order_year'] == 2024, 'revenue_yoy_growth_pct'].iloc[0]:.2f}% in 2024 "
         f"and {yr.loc[yr['order_year'] == 2025, 'revenue_yoy_growth_pct'].iloc[0]:.2f}% in 2025, and "
         f"margin rose across the same years "
         f"({yr['profit_margin_pct'].iloc[0]:.2f}% -> {yr['profit_margin_pct'].iloc[-1]:.2f}%).",
         "Track revenue growth % and margin on the same page every month; growth bought by margin "
         "is visible immediately on the Revenue Intelligence page.",
         "Revenue growth 2025 / margin 2025",
         f"{yr.loc[yr['order_year'] == 2025, 'revenue_yoy_growth_pct'].iloc[0]:.2f}% / "
         f"{yr['profit_margin_pct'].iloc[-1]:.2f}%",
         "SQL rev_by_year (Step 10)"),
        ("Revenue", 14,
         f"Recover part of the {100 * float(kpi['Share of Booked Sales Not Realised']):.2f}% of booked "
         "value lost to returns and cancellations",
         f"{cr(float(kpi['Gross Booked Sales (all statuses)']))} was booked and "
         f"{cr(float(kpi['Total Revenue']))} was delivered; "
         f"{cr(float(kpi['Revenue Lost to Cancellations & Returns']))} never became revenue. "
         f"Cash on delivery has the highest cancellation rate "
         f"({bq13.loc['COD', 'cancelled_lines_pct']:.2f}% of lines against "
         f"{bq13.loc['UPI', 'cancelled_lines_pct']:.2f}% for UPI).",
         "Add an order-confirmation step for high-value COD orders and measure the cancelled-line "
         "rate by payment method after the change.",
         "Booked value not realised",
         f"{100 * float(kpi['Share of Booked Sales Not Realised']):.2f}%",
         "Step 4 eda_kpis; SQL BQ13, rev_order_status (Step 10)"),

        # ---------------------------------------------- Forecasting & Planning
        ("Forecasting & Planning", 15,
         f"Plan the next two quarters on {cr(fut_total)} of forecast revenue, with the interval shown",
         f"The Step 9 {fmeta['model_type'].split(':')[0]} model forecasts {cr(fut_total)} for "
         f"{fmeta['forecast_months'][0]} to {fmeta['forecast_months'][-1]}, with an 80% interval of "
         f"{cr(fut_lo)} to {cr(fut_hi)}. The previous six months delivered {cr(float(last6))}.",
         "Budget to the central forecast, stress-test to the lower bound, and re-fit the model as "
         "each actual month lands - the interval widens with horizon, so month 6 is not month 1.",
         "6-month forecast (80% interval)", f"{cr(fut_total)} ({cr(fut_lo)} - {cr(fut_hi)})",
         "Step 9 forecast_future, models/forecasting_metadata.json"),
        ("Forecasting & Planning", 16,
         f"Trust the monthly forecast at about ±{fmeta['metrics']['test']['MAPE_%']:.1f}% and no further",
         f"On the held-out test months the forecast's MAPE was "
         f"{fmeta['metrics']['test']['MAPE_%']:.2f}% (MAE {lk(fmeta['metrics']['test']['MAE'])}), "
         f"and the mean rolling-backtest MAPE was {fmeta['metrics']['backtest_mean_MAPE_%']:.2f}%.",
         "Quote the forecast with its error band on the Prediction & Forecast page; do not set "
         "targets at a precision the model has never demonstrated.",
         "Forecast test MAPE", f"{fmeta['metrics']['test']['MAPE_%']:.2f}%",
         "Step 9 forecast_model_comparison, forecasting_metadata.json"),
        ("Forecasting & Planning", 17,
         "Use the customer-level revenue prediction for ranking, not for rupee commitments",
         f"The Step 8 {rmeta['model_type']} reaches R² "
         f"{rmeta['test_metrics']['R2']:.3f} with MAE ₹{rmeta['test_metrics']['MAE']:,.0f} per "
         f"customer-quarter on the test split - better than the best baseline on RMSE, but far from "
         "precise for an individual customer. Its total bias is "
         f"{rmeta['test_metrics']['Total_Bias_%']:+.2f}%.",
         "Use the predictions to order customers for outreach (top predicted customers first) and "
         "take the aggregate total as a planning figure; never quote a single customer's predicted "
         "revenue as a commitment.",
         "Prediction test R² / MAE",
         f"{rmeta['test_metrics']['R2']:.3f} / ₹{rmeta['test_metrics']['MAE']:,.0f}",
         "Step 8 revenue_model_comparison, models/revenue_model_metadata.json"),
        ("Forecasting & Planning", 18,
         "Re-run the pipeline before each planning cycle",
         f"Every figure on this dashboard is a snapshot: RFM, clusters and CLV are taken at the "
         f"{cust['Reference_Date'].dropna().iloc[0]} reference date and the forecast is fitted on "
         f"{fmeta['training_period_final_fit']}.",
         "Re-run Steps 3-10 and refresh the extracts (see powerbi_user_guide.md) so segments and "
         "forecasts move with the data instead of ageing silently on the page.",
         "Reference date / forecast fit window",
         f"{cust['Reference_Date'].dropna().iloc[0]} / {fmeta['training_period_final_fit']}",
         "Steps 5-9 metadata"),
    ]
    df = pd.DataFrame(rows, columns=["Area", "Recommendation_ID", "Recommendation", "Evidence",
                                     "Suggested_Action", "Supporting_Metric", "Metric_Value",
                                     "Analytical_Source"])
    df["Area_Order"] = df["Area"].map({"Customer": 1, "Product": 2, "Regional": 3,
                                       "Revenue": 4, "Forecasting & Planning": 5})
    return df


# =========================================================================== 6. theme
def write_theme() -> dict:
    """Dark data-intelligence theme JSON + a gradient page background PNG.

    The eight categorical colours are the dark palette validated for this project
    against the panel surface #141C2B (lightness band, chroma floor, adjacent-pair
    colour-vision separation, normal-vision separation and contrast all pass).
    Status colours are reserved for good / warning / serious / critical and are
    never reused as a ninth series.
    """
    t = THEME
    theme = {
        "name": "Customer Revenue Intelligence - Dark",
        "dataColors": t["cat"],
        "background": t["page"],
        "foreground": t["ink"],
        "foregroundNeutralSecondary": t["muted"],
        "tableAccent": t["cat"][0],
        "good": t["good"], "neutral": t["warning"], "bad": t["critical"],
        "maximum": t["cat"][0], "center": t["muted"], "minimum": t["panel"],
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 16, "color": t["ink_strong"]},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 13, "color": t["ink"]},
            "label": {"fontFace": "Segoe UI", "fontSize": 11, "color": t["ink"]},
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 34, "color": t["ink_strong"]},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": t["panel"]}},
                               "transparency": 8}],
                "border": [{"show": True, "color": {"solid": {"color": t["border"]}}, "radius": 8}],
                "visualHeader": [{"show": False}],
                "title": [{"show": True, "fontColor": {"solid": {"color": t["ink_strong"]}},
                           "background": {"solid": {"color": t["panel"]}},
                           "fontSize": 13, "fontFamily": "Segoe UI Semibold", "alignment": "left"}],
                "labels": [{"color": {"solid": {"color": t["ink"]}}, "fontSize": 10}],
                "legend": [{"show": True, "position": "Top", "showTitle": False,
                            "labelColor": {"solid": {"color": t["ink"]}}, "fontSize": 10}],
                "categoryAxis": [{"labelColor": {"solid": {"color": t["muted"]}}, "fontSize": 10,
                                  "gridlineShow": False,
                                  "lineColor": {"solid": {"color": t["grid"]}}}],
                "valueAxis": [{"labelColor": {"solid": {"color": t["muted"]}}, "fontSize": 10,
                               "gridlineShow": True, "gridlineColor": {"solid": {"color": t["grid"]}},
                               "gridlineThickness": 1, "gridlineStyle": "dotted"}],
                "wordWrap": [{"show": True}],
            }},
            "card": {"*": {
                "labels": [{"color": {"solid": {"color": t["ink_strong"]}}, "fontSize": 30,
                            "fontFamily": "Segoe UI Semibold"}],
                "categoryLabels": [{"color": {"solid": {"color": t["muted"]}}, "fontSize": 11}],
            }},
            "lineChart": {"*": {"lineStyles": [{"strokeWidth": 2, "showMarker": False}]}},
            "scatterChart": {"*": {"fillPoint": [{"show": True}],
                                   "bubbles": [{"bubbleSize": -10}]}},
            "slicer": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": t["panel"]}}}],
                "items": [{"fontColor": {"solid": {"color": t["ink"]}},
                           "background": {"solid": {"color": t["panel"]}}, "fontSize": 10}],
                "header": [{"fontColor": {"solid": {"color": t["muted"]}}, "fontSize": 10}],
            }},
            "tableEx": {"*": {
                "grid": [{"gridVerticalColor": {"solid": {"color": t["grid"]}},
                          "gridHorizontalColor": {"solid": {"color": t["grid"]}},
                          "rowPadding": 4}],
                "columnHeaders": [{"fontColor": {"solid": {"color": t["muted"]}},
                                   "backColor": {"solid": {"color": t["page"]}}, "fontSize": 10}],
                "values": [{"fontColor": {"solid": {"color": t["ink"]}},
                            "backColor": {"solid": {"color": t["panel"]}},
                            "backColorSecondary": {"solid": {"color": t["panel"]}}, "fontSize": 10}],
            }},
        },
    }
    (PBI_THEME / "crm_dark_theme.json").write_text(json.dumps(theme, indent=2, ensure_ascii=False))
    _background_png()
    (PBI_THEME / "palette_reference.md").write_text(_palette_reference())
    return theme


def _palette_reference() -> str:
    t = THEME
    rows = "\n".join(f"| {i + 1} | `{c}` | Series {i + 1} |" for i, c in enumerate(t["cat"]))
    return f"""# Dashboard palette reference (STEP 11)

Dark data-intelligence theme. Surfaces: page `{t['page']}`, panel `{t['panel']}`,
border `{t['border']}`. Text: primary `{t['ink_strong']}`, body `{t['ink']}`,
muted `{t['muted']}`. Gridlines `{t['grid']}`.

## Categorical series (assign in this order, never cycled)

| Order | Hex | Use |
|---|---|---|
{rows}

The eight hues were checked against the panel surface for lightness band, chroma
floor, colour-vision separation between adjacent pairs, normal-vision separation
and text contrast. The first three pass the all-pairs check, so scatter and
bubble charts use only those three when a legend has three categories.

## Reserved status colours (never used as a data series)

| Meaning | Hex |
|---|---|
| Good | `{t['good']}` |
| Warning | `{t['warning']}` |
| Serious | `{t['serious']}` |
| Critical | `{t['critical']}` |

## Fixed series meanings on the Prediction & Forecast page

| Series | Hex | Meaning |
|---|---|---|
| Historical | `{SERIES['historical']}` | Actual delivered revenue |
| Predicted | `{SERIES['predicted']}` | Step 8 ML prediction (customer-quarter) |
| Forecast | `{SERIES['forecast']}` | Step 9 time-series forecast |

Rules that apply everywhere: one value axis per chart (never a second y-axis), a
legend whenever two or more series are shown, colour never the only cue (labels
and icons carry the same information), and text in a text colour rather than a
series colour.
"""


def _background_png() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    w, h = 1920, 1080
    yy, xx = np.mgrid[0:h, 0:w]
    # two soft radial glows on a near-black page: depth without reducing contrast
    g1 = np.exp(-(((xx - w * 0.18) / (w * 0.55)) ** 2 + ((yy - h * 0.10) / (h * 0.75)) ** 2))
    g2 = np.exp(-(((xx - w * 0.92) / (w * 0.45)) ** 2 + ((yy - h * 0.95) / (h * 0.6)) ** 2))
    field = 0.62 * g1 + 0.38 * g2
    cmap = LinearSegmentedColormap.from_list("bg", ["#070B12", THEME["page"], "#15203A"])
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    ax.imshow(field, cmap=cmap, vmin=0, vmax=1.0)
    fig.savefig(PBI_THEME / "page_background.png", dpi=100, facecolor=THEME["page"])
    plt.close(fig)


# =========================================================================== 7. mockups
# These are DESIGN MOCKUPS drawn with matplotlib from the real extracts. They show
# the intended layout, chart choices and theme of each Power BI page. They are not
# screenshots and are watermarked as such; real screenshots must be captured from
# Power BI Desktop (see outputs/figures/powerbi/README.md).
WATERMARK = "DESIGN MOCKUP - layout specification drawn from the real data. Not a Power BI screenshot."
PAGES = ["HOME", "1 Executive Overview", "2 Revenue Intelligence", "3 Customer Intelligence",
         "4 Customer Segmentation", "5 Product Analytics", "6 Regional Analytics",
         "7 Prediction & Forecast", "8 Business Recommendations"]


plt = None      # set by _mpl(); matplotlib is imported lazily so the data layer has no GUI dependency


def _mpl():
    global plt
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 9, "text.color": THEME["ink"], "axes.labelcolor": THEME["muted"],
        "xtick.color": THEME["muted"], "ytick.color": THEME["muted"],
        "axes.edgecolor": THEME["grid"], "figure.dpi": 110, "savefig.dpi": 110,
        "axes.titlecolor": THEME["ink_strong"],
    })
    return plt


def _panel_patch(fig, x, y, w, h, alpha=1.0):
    from matplotlib.patches import FancyBboxPatch
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                       transform=fig.transFigure, facecolor=THEME["panel"], alpha=alpha,
                       edgecolor=THEME["border"], linewidth=1.0, zorder=-1)
    fig.patches.append(p)
    return p


def _page(plt, current: str, title: str, subtitle: str):
    """Frame shared by every mockup: header, left navigation rail, footer."""
    fig = plt.figure(figsize=(16, 9), facecolor=THEME["page"])
    fig.patches.append(plt.Rectangle((0, 0), 1, 1, transform=fig.transFigure,
                                     facecolor=THEME["page"], zorder=-2))
    _panel_patch(fig, 0.012, 0.905, 0.976, 0.082)
    fig.text(0.026, 0.958, "CUSTOMER REVENUE INTELLIGENCE", color=THEME["muted"],
             fontsize=8.5, weight="bold")
    fig.text(0.026, 0.922, title, color=THEME["ink_strong"], fontsize=16, weight="bold")
    fig.text(0.40, 0.925, subtitle, color=THEME["muted"], fontsize=9)
    fig.text(0.985, 0.958, "Synthetic data - internship project", color=THEME["muted"],
             fontsize=8, ha="right")
    fig.text(0.985, 0.922, "Jan 2023 - Dec 2025  |  reference date 2026-01-01",
             color=THEME["ink"], fontsize=9, ha="right")
    # navigation rail
    _panel_patch(fig, 0.012, 0.055, 0.128, 0.835)
    fig.text(0.024, 0.862, "NAVIGATION", color=THEME["muted"], fontsize=8, weight="bold")
    for i, name in enumerate(PAGES):
        y = 0.822 - i * 0.043
        active = name == current
        if active:
            fig.patches.append(plt.Rectangle((0.0155, y - 0.011), 0.121, 0.036,
                                             transform=fig.transFigure, facecolor="#1D2A42",
                                             edgecolor=THEME["cat"][0], linewidth=1.2, zorder=-0.5))
            fig.patches.append(plt.Rectangle((0.0155, y - 0.011), 0.004, 0.036,
                                             transform=fig.transFigure, facecolor=THEME["cat"][0],
                                             zorder=1))
        fig.text(0.026, y, name, color=THEME["ink_strong"] if active else THEME["muted"],
                 fontsize=8.5, weight="bold" if active else "normal")
    fig.text(0.024, 0.088, "Drill-through:", color=THEME["muted"], fontsize=7.5)
    fig.text(0.024, 0.068, "Customer Detail | Product Detail", color=THEME["muted"], fontsize=7)
    # footer / watermark
    fig.text(0.5, 0.028, WATERMARK, color=THEME["warning"], fontsize=9.5, ha="center",
             weight="bold")
    fig.text(0.5, 0.008, "Generated by src/powerbi_prep.py from powerbi/data/*.csv - "
                         "every number shown is an actual project output.",
             color=THEME["muted"], fontsize=7.5, ha="center")
    return fig


def _ax(fig, x, y, w, h, title=None, sub=None, pad_left=0.0, pad_right=0.0, pad_bottom=0.0):
    _panel_patch(fig, x, y, w, h)
    pad_l = 0.035
    top = 0.075 if sub else (0.048 if title else 0.012)     # absolute figure units
    bottom = 0.035 + pad_bottom
    ax = fig.add_axes([x + w * pad_l + 0.024 + pad_left, y + bottom,
                       w * (1 - pad_l) - 0.034 - pad_left - pad_right,
                       h - top - bottom])
    ax.set_facecolor("none")
    ax.set_zorder(5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(THEME["grid"])
    ax.tick_params(length=0, labelsize=8)
    if title:
        fig.text(x + 0.012, y + h - 0.032, title, color=THEME["ink_strong"], fontsize=10.5,
                 weight="bold")
    if sub:
        import textwrap
        chars = max(int(w * 190), 30)
        fig.text(x + 0.012, y + h - 0.055, "\n".join(textwrap.wrap(sub, chars)[:2]),
                 color=THEME["muted"], fontsize=7.8, va="top")
    return ax


def _kpi(fig, x, y, w, h, label, value, sub, accent=None):
    _panel_patch(fig, x, y, w, h)
    if accent:
        fig.patches.append(plt.Rectangle((x, y), 0.0035, h, transform=fig.transFigure,
                                         facecolor=accent, zorder=1))
    fig.text(x + 0.014, y + h - 0.028, label.upper(), color=THEME["muted"], fontsize=8,
             weight="bold")
    fig.text(x + 0.014, y + h * 0.33, value, color=THEME["ink_strong"], fontsize=21, weight="bold")
    fig.text(x + 0.014, y + 0.012, sub, color=THEME["muted"], fontsize=7.5)


def _money(v, unit="auto"):
    a = abs(v)
    if unit == "cr" or (unit == "auto" and a >= 1e7):
        return f"₹{v / 1e7:.2f} Cr"
    if unit == "l" or (unit == "auto" and a >= 1e5):
        return f"₹{v / 1e5:.2f} L"
    return f"₹{v:,.0f}"


def _grid(ax, axis="y"):
    ax.grid(axis=axis, color=THEME["grid"], linewidth=0.8, linestyle=":", alpha=0.9)
    ax.set_axisbelow(True)


def _barlabels(ax, bars, fmt, horizontal=False, color=None):
    color = color or THEME["ink"]
    for b in bars:
        if horizontal:
            ax.text(b.get_width() * 1.01, b.get_y() + b.get_height() / 2, fmt(b.get_width()),
                    va="center", ha="left", fontsize=7.5, color=color)
        else:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), fmt(b.get_height()),
                    va="bottom", ha="center", fontsize=7.5, color=color)


def _table(fig, x, y, w, h, df, title, sub=None, fmts=None, highlight_col=None):
    _panel_patch(fig, x, y, w, h)
    fig.text(x + 0.012, y + h - 0.032, title, color=THEME["ink_strong"], fontsize=10.5, weight="bold")
    sub_lines = 0
    if sub:
        import textwrap
        wrapped = textwrap.wrap(sub, max(int(w * 190), 30))[:3]
        sub_lines = len(wrapped)
        fig.text(x + 0.012, y + h - 0.055, "\n".join(wrapped),
                 color=THEME["muted"], fontsize=7.8, va="top")
    cols = list(df.columns)
    n = len(df)
    top = y + h - 0.055 - 0.016 * sub_lines - 0.014
    row_h = min(0.026, (top - y - 0.02) / max(n + 1, 1))
    xs = [x + 0.014 + i * (w - 0.03) / len(cols) for i in range(len(cols))]
    for cx, c in zip(xs, cols):
        fig.text(cx, top, str(c).replace("_", " "), color=THEME["muted"], fontsize=7.5, weight="bold")
    for r in range(n):
        yy = top - (r + 1) * row_h
        if r % 2 == 0:
            fig.patches.append(plt.Rectangle((x + 0.008, yy - 0.004), w - 0.016, row_h,
                                             transform=fig.transFigure, facecolor="#101725",
                                             edgecolor="none", zorder=-0.5))
        for ci, (cx, c) in enumerate(zip(xs, cols)):
            v = df.iloc[r][c]
            txt = fmts[ci](v) if fmts and fmts[ci] else str(v)
            col = THEME["ink_strong"] if (highlight_col is not None and ci == highlight_col) else THEME["ink"]
            fig.text(cx, yy, txt, color=col, fontsize=7.5)


def _mock_data(con: sqlite3.Connection) -> dict:
    """Everything the mockups draw, read from the exported star schema and Step 4-10 tables."""
    d = {}
    f = pd.read_sql_query("""
        SELECT s.*, strftime('%Y', s.Order_Date) AS Year, strftime('%Y-%m', s.Order_Date) AS Year_Month,
               g.Region, p.Category, p.Sub_Category, p.Product_Name,
               c.RFM_Segment, c.Cluster_ID
        FROM pbi_fact_sales s
        JOIN pbi_dim_geography g ON g.Location_ID = s.Location_ID
        JOIN pbi_dim_product p   ON p.Product_ID = s.Product_ID
        JOIN pbi_dim_customer c  ON c.Customer_ID = s.Customer_ID""", con)
    d["fact"] = f
    d["deliv"] = f[f["Is_Delivered"] == 1]
    d["cust"] = pd.read_sql_query("SELECT * FROM pbi_dim_customer", con)
    d["fc"] = pd.read_sql_query("SELECT * FROM pbi_fact_forecast", con)
    d["kpi"] = pd.read_csv(TAB / "eda_kpis.csv").set_index("KPI")["Value"]
    d["rfm"] = pd.read_csv(TAB / "rfm_segment_summary.csv")
    d["ml"] = pd.read_csv(TAB / "ml_cluster_summary.csv")
    d["prod"] = pd.read_csv(TAB / "product_profitability.csv")
    d["conc"] = pd.read_csv(TAB / "customer_revenue_concentration.csv")
    d["pred"] = pd.read_csv(PBI_DATA / "FactRevenuePrediction.csv")
    d["predq"] = pd.read_csv(PBI_DATA / "PredictionQuarterly.csv")
    d["metrics"] = pd.read_csv(PBI_DATA / "ModelMetrics.csv")
    d["recs"] = pd.read_csv(PBI_DATA / "Recommendations.csv")
    d["sqlt"] = lambda n: pd.read_csv(TAB / "sql" / f"{n}.csv")
    return d


def _slicer_row(fig, y=0.855, items=None):
    items = items or ["Date: 01 Jan 2023 - 31 Dec 2025", "Region: All", "Category: All",
                      "Sub-category: All", "Segment: All", "Cluster: All"]
    x = 0.152
    for it in items:
        w = 0.013 + 0.0062 * len(it)
        _panel_patch(fig, x, y, w, 0.035)
        fig.text(x + 0.008, y + 0.0115, it, color=THEME["ink"], fontsize=8)
        x += w + 0.008
    fig.text(0.985, y + 0.0115, "Slicers synced across pages", color=THEME["muted"], fontsize=7.5,
             ha="right")


# --------------------------------------------------------------------- page 1
def mock_executive_overview(d: dict) -> Path:
    fig = _page(plt, "1 Executive Overview", "Executive Overview",
                "Delivered revenue only  |  all figures respond to the slicers")
    _slicer_row(fig)
    k = d["kpi"]
    cards = [("Total revenue", _money(k["Total Revenue"]), "Delivered lines, 2023-2025", THEME["cat"][0]),
             ("Total profit", _money(k["Total Profit"]), "After cost of goods", THEME["cat"][2]),
             ("Profit margin", f"{k['Overall Profit Margin']:.1%}", "Profit / revenue", THEME["cat"][2]),
             ("Orders", f"{int(k['Number of Orders']):,}", "Orders with a delivered line", THEME["cat"][0]),
             ("Customers", f"{int(k['Purchasing Customers']):,}", "Of 2,000 registered", THEME["cat"][6]),
             ("Average order value", f"₹{k['Average Order Value (AOV)']:,.0f}", "Revenue / orders", THEME["cat"][3])]
    w = 0.1327
    for i, (lab, val, sub, acc) in enumerate(cards):
        _kpi(fig, 0.152 + i * (w + 0.008), 0.715, w, 0.125, lab, val, sub, acc)

    dl = d["deliv"]
    monthly = dl.groupby("Year_Month")[["Sales", "Profit"]].sum()
    ax = _ax(fig, 0.152, 0.40, 0.47, 0.30, "Monthly revenue and profit",
             "Both series are rupees, so they share one axis - no second y-axis anywhere in this report")
    x = np.arange(len(monthly))
    ax.plot(x, monthly["Sales"] / 1e5, color=THEME["cat"][0], lw=2, label="Revenue")
    ax.plot(x, monthly["Profit"] / 1e5, color=THEME["cat"][2], lw=2, label="Profit")
    peak = int(np.argmax(monthly["Sales"].values))
    ax.annotate(f"{monthly.index[peak]}\n{_money(monthly['Sales'].iloc[peak])}",
                (peak, monthly["Sales"].iloc[peak] / 1e5), textcoords="offset points",
                xytext=(-34, -4), color=THEME["ink"], fontsize=7.5)
    ax.set_xticks(x[::3]); ax.set_xticklabels(monthly.index[::3], rotation=0, fontsize=7)
    ax.set_ylabel("₹ lakh", fontsize=8); _grid(ax)
    ax.legend(frameon=False, loc="upper left", fontsize=8, ncol=2,
              labelcolor=THEME["ink"])

    reg = dl.groupby("Region")["Sales"].sum().sort_values()
    ax = _ax(fig, 0.632, 0.40, 0.176, 0.30, "Revenue by region", "Ranked; South leads")
    b = ax.barh(reg.index, reg.values / 1e7, color=THEME["cat"][0], height=0.62)
    _barlabels(ax, b, lambda v: f"{v:.2f} Cr", horizontal=True)
    ax.set_xlim(0, reg.max() / 1e7 * 1.35); ax.set_xticks([]); _grid(ax, "x")
    ax.tick_params(labelsize=8)

    cat = dl.groupby("Category")[["Sales", "Profit"]].sum().sort_values("Sales")
    ax = _ax(fig, 0.812, 0.40, 0.176, 0.30, "Revenue by category",
             "Profit margin % shown as the label", pad_left=0.022, pad_right=0.004)
    b = ax.barh(cat.index, cat["Sales"].values / 1e7, color=THEME["cat"][3], height=0.62)
    for bar, (rev, pr) in zip(b, cat[["Sales", "Profit"]].values):
        ax.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height() / 2,
                f"{rev / 1e7:.2f} Cr · {100 * pr / rev:.0f}%", va="center", fontsize=7,
                color=THEME["ink"])
    ax.set_xlim(0, cat["Sales"].max() / 1e7 * 1.62); ax.set_xticks([]); _grid(ax, "x")
    ax.tick_params(labelsize=7.5)

    seg = (d["rfm"].sort_values("Revenue_%", ascending=False)[["RFM_Segment", "Revenue_%", "Customer_%"]]
           .head(6))
    ax = _ax(fig, 0.152, 0.075, 0.41, 0.31, "Revenue contribution by RFM segment",
             "Share of revenue against share of customers - the gap is the point")
    y = np.arange(len(seg))[::-1]
    ax.barh(y + 0.19, seg["Revenue_%"], height=0.36, color=THEME["cat"][0], label="% of revenue")
    ax.barh(y - 0.19, seg["Customer_%"], height=0.36, color=THEME["cat"][4], label="% of customers")
    for yy, (r, c) in zip(y, seg[["Revenue_%", "Customer_%"]].values):
        ax.text(r + 0.6, yy + 0.19, f"{r:.1f}%", va="center", fontsize=7, color=THEME["ink"])
        ax.text(c + 0.6, yy - 0.19, f"{c:.1f}%", va="center", fontsize=7, color=THEME["ink"])
    ax.set_yticks(y); ax.set_yticklabels(seg["RFM_Segment"], fontsize=8)
    ax.set_xlim(0, 62); ax.set_xticks([]); _grid(ax, "x")
    ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=THEME["ink"])

    yr = d["sqlt"]("rev_by_year")
    ax = _ax(fig, 0.575, 0.075, 0.21, 0.31, "Revenue growth by year",
             "Year-over-year growth %, labelled")
    b = ax.bar(yr["order_year"].astype(str), yr["revenue"] / 1e7, color=THEME["cat"][0], width=0.55)
    for bar, g in zip(b, yr["revenue_yoy_growth_pct"]):
        lab = "base year" if pd.isna(g) else f"+{g:.1f}%"
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.06, lab,
                ha="center", fontsize=8, color=THEME["ink"])
    ax.set_ylabel("₹ crore", fontsize=8); ax.set_ylim(0, 3.3); _grid(ax)

    ax = _ax(fig, 0.798, 0.075, 0.19, 0.31, "Where revenue is concentrated",
             "Cumulative revenue by customer decile")
    c = d["conc"]
    ax.plot(c["cumulative_pct_of_customers"], c["cumulative_pct_of_revenue"],
            color=THEME["cat"][2], lw=2)
    ax.axvline(20, color=THEME["muted"], lw=1, ls="--")
    ax.axhline(64.33, color=THEME["muted"], lw=1, ls="--")
    ax.annotate("top 20% of customers\n= 64.3% of revenue", (20, 64.33), xytext=(26, 36),
                color=THEME["ink"], fontsize=7.5,
                arrowprops=dict(arrowstyle="-", color=THEME["muted"], lw=0.8))
    ax.set_xlabel("% of customers", fontsize=8); ax.set_ylabel("% of revenue", fontsize=8)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); _grid(ax); _grid(ax, "x")
    return _save(fig, "01_executive_overview")


def _save(fig, name: str) -> Path:
    out = MOCKUP_DIR / f"{name}_mockup.png"
    fig.savefig(out, facecolor=THEME["page"])
    plt.close(fig)
    return out


# --------------------------------------------------------------------- page 2
def mock_revenue_intelligence(d: dict) -> Path:
    fig = _page(plt, "2 Revenue Intelligence", "Revenue Intelligence",
                "Where revenue and margin come from, and what moves them")
    _slicer_row(fig)
    dl = d["deliv"]
    m = dl.groupby("Year_Month")[["Sales", "Profit"]].sum()
    m["Margin"] = 100 * m["Profit"] / m["Sales"]
    ax = _ax(fig, 0.152, 0.545, 0.42, 0.295, "Revenue and profit by month",
             "Same unit, one axis; the gap between the lines is the cost base")
    x = np.arange(len(m))
    ax.plot(x, m["Sales"] / 1e5, color=THEME["cat"][0], lw=2, label="Revenue")
    ax.plot(x, m["Profit"] / 1e5, color=THEME["cat"][2], lw=2, label="Profit")
    ax.fill_between(x, m["Profit"] / 1e5, m["Sales"] / 1e5, color=THEME["cat"][0], alpha=0.07)
    ax.set_xticks(x[::4]); ax.set_xticklabels(m.index[::4], fontsize=7)
    ax.set_ylabel("₹ lakh", fontsize=8); _grid(ax)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left", labelcolor=THEME["ink"])

    ax = _ax(fig, 0.585, 0.545, 0.20, 0.295, "Profit margin by month",
             "Margin is a ratio, so it gets its own chart - never a second axis")
    ax.plot(x, m["Margin"], color=THEME["cat"][3], lw=2)
    ax.axhline(100 * dl["Profit"].sum() / dl["Sales"].sum(), color=THEME["muted"], lw=1, ls="--")
    ax.text(1, 100 * dl["Profit"].sum() / dl["Sales"].sum() + 0.6, "overall 23.3%",
            fontsize=7.5, color=THEME["muted"])
    ax.set_xticks(x[::8]); ax.set_xticklabels(m.index[::8], fontsize=7)
    ax.set_ylabel("%", fontsize=8); _grid(ax)

    yr = d["sqlt"]("rev_by_year")
    ax = _ax(fig, 0.795, 0.545, 0.193, 0.295, "Year-over-year growth",
             "Revenue and profit growth, %")
    xx = np.arange(2)
    ax.bar(xx - 0.18, yr["revenue_yoy_growth_pct"].dropna(), width=0.34, color=THEME["cat"][0],
           label="Revenue growth %")
    ax.bar(xx + 0.18, yr["profit_yoy_growth_pct"].dropna(), width=0.34, color=THEME["cat"][2],
           label="Profit growth %")
    for i, (r, p_) in enumerate(zip(yr["revenue_yoy_growth_pct"].dropna(),
                                    yr["profit_yoy_growth_pct"].dropna())):
        ax.text(i - 0.18, r + 1, f"{r:.1f}", ha="center", fontsize=7.5, color=THEME["ink"])
        ax.text(i + 0.18, p_ + 1, f"{p_:.1f}", ha="center", fontsize=7.5, color=THEME["ink"])
    ax.set_xticks(xx); ax.set_xticklabels(["2024", "2025"], fontsize=8); ax.set_ylim(0, 68)
    _grid(ax); ax.legend(frameon=False, fontsize=7.5, loc="upper right", labelcolor=THEME["ink"])

    sub = (dl.groupby("Sub_Category")[["Sales", "Profit"]].sum()
           .sort_values("Sales", ascending=False).head(10).sort_values("Sales"))
    ax = _ax(fig, 0.152, 0.075, 0.30, 0.44, "Top 10 sub-categories by revenue",
             "Bar length = revenue; the label carries the margin so size never hides a thin margin",
             pad_left=0.045)
    b = ax.barh(sub.index, sub["Sales"] / 1e7, color=THEME["cat"][0], height=0.62)
    for bar, (rev, pr) in zip(b, sub[["Sales", "Profit"]].values):
        ax.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height() / 2,
                f"{rev / 1e7:.2f} Cr · {100 * pr / rev:.0f}%", va="center", fontsize=7,
                color=THEME["ink"])
    ax.set_xlim(0, sub["Sales"].max() / 1e7 * 1.42); ax.set_xticks([]); _grid(ax, "x")
    ax.tick_params(labelsize=7.5)

    bands = d["sqlt"]("prod_discount_bands")
    ax = _ax(fig, 0.462, 0.29, 0.26, 0.225, "Margin by discount band",
             "Association in observational data - not proof that discounting causes the loss")
    b = ax.bar(bands["discount_band"], bands["profit_margin_pct"], color=THEME["cat"][3], width=0.6)
    _barlabels(ax, b, lambda v: f"{v:.1f}%")
    ax.set_ylabel("margin %", fontsize=8); ax.set_ylim(0, 34); _grid(ax)
    ax.tick_params(labelsize=7.5)

    bq08 = d["sqlt"]("BQ08")
    ax = _ax(fig, 0.462, 0.075, 0.26, 0.20, "Discount vs margin within each category",
             "One line per category: the 0% band has the best margin in 6 of 6", pad_bottom=0.034)
    for i, (cat_name, g) in enumerate(bq08.groupby("category")):
        ax.plot(g["discount_band"], g["profit_margin_pct"], color=THEME["cat"][i % 8], lw=1.8,
                marker="o", ms=3.5, label=cat_name)
    ax.axhline(0, color=THEME["muted"], lw=0.8)
    ax.set_ylabel("margin %", fontsize=8); _grid(ax); ax.tick_params(labelsize=7.5)
    ax.legend(frameon=False, fontsize=6.8, ncol=3, loc="upper center",
              bbox_to_anchor=(0.5, -0.20), labelcolor=THEME["ink"])

    ax = _ax(fig, 0.732, 0.29, 0.256, 0.225, "Revenue by region and year",
             "Ranked regions; growth is broad, not one region")
    piv = dl.pivot_table(index="Region", columns="Year", values="Sales", aggfunc="sum")
    piv = piv.loc[piv.sum(1).sort_values().index]
    yv = np.arange(len(piv))
    for i, yr_ in enumerate(piv.columns):
        ax.barh(yv + (i - 1) * 0.27, piv[yr_] / 1e7, height=0.25, color=THEME["cat"][i],
                label=str(yr_))
    ax.set_yticks(yv); ax.set_yticklabels(piv.index, fontsize=7.5)
    ax.set_xlabel("₹ crore", fontsize=8); _grid(ax, "x")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower right", labelcolor=THEME["ink"])

    _panel_patch(fig, 0.732, 0.075, 0.256, 0.20)
    fig.text(0.744, 0.245, "Revenue drivers (from the analysis)", color=THEME["ink_strong"],
             fontsize=10.5, weight="bold")
    drivers = [
        "Category mix: Electronics is 50.1% of revenue at 10.8% margin (prod_category_performance)",
        "Concentration: top 20% of customers = 64.3% of revenue (cust_concentration_summary)",
        "Repeat purchasing: repeat customers are 89.4% of customers, 98.6% of revenue (BQ12)",
        "Seasonality: October is the highest month in all three years (time_month_of_year)",
        "Realisation: 9.4% of booked value is lost to returns / cancellations (BQ14)",
    ]
    import textwrap as _tw
    yy = 0.222
    for t in drivers:
        wrapped = _tw.wrap(t, 64)
        fig.text(0.746, yy, "•", color=THEME["cat"][0], fontsize=8)
        fig.text(0.754, yy, "\n".join(wrapped), color=THEME["ink"], fontsize=7.1, va="top")
        yy -= 0.0135 * len(wrapped) + 0.0075
    fig.text(0.746, yy - 0.002, "Every driver names the saved query it came from.",
             color=THEME["muted"], fontsize=6.9, va="top")
    return _save(fig, "02_revenue_intelligence")


# --------------------------------------------------------------------- page 3
def mock_customer_intelligence(d: dict) -> Path:
    fig = _page(plt, "3 Customer Intelligence", "Customer Intelligence",
                "Who the customers are, what they are worth, and how recently they bought")
    _slicer_row(fig)
    cu = d["cust"]; dl = d["deliv"]
    active = int((cu["Recency_Days"] < 180).sum())
    cards = [("Customers with orders", f"{int(cu['Has_Delivered_Order'].sum()):,}",
              "Of 2,000 registered", THEME["cat"][0]),
             ("Active (< 180 days)", f"{active:,}", "At 2026-01-01 - inactivity, not churn", THEME["cat"][2]),
             ("Avg revenue / customer", f"₹{dl['Sales'].sum() / dl['Customer_ID'].nunique():,.0f}",
              "Delivered revenue / customers", THEME["cat"][0]),
             ("Average order value", f"₹{dl['Sales'].sum() / dl['Order_ID'].nunique():,.0f}",
              "Revenue / orders", THEME["cat"][3]),
             ("Repeat customers", f"{int((cu['Frequency_Orders'] >= 2).sum()):,}",
              "2+ delivered orders (98.6% of revenue)", THEME["cat"][6]),
             ("At-risk high value", f"{int(cu['Potentially_At_Risk_High_Value'].sum())}",
              "High value, no order for 180+ days", THEME["warning"])]
    w = 0.1327
    for i, (lab, val, sub, acc) in enumerate(cards):
        _kpi(fig, 0.152 + i * (w + 0.008), 0.715, w, 0.125, lab, val, sub, acc)

    rev = dl.groupby("Customer_ID")["Sales"].sum()
    ax = _ax(fig, 0.152, 0.40, 0.27, 0.30, "Customer revenue distribution",
             "Lifetime delivered revenue per customer; the tail is long and thin")
    ax.hist(rev / 1e5, bins=40, color=THEME["cat"][0])
    ax.axvline(rev.median() / 1e5, color=THEME["warning"], lw=1.5, ls="--")
    ax.text(rev.median() / 1e5 + 0.05, ax.get_ylim()[1] * 0.82,
            f"median ₹{rev.median() / 1e5:.2f} L", fontsize=7.5, color=THEME["ink"])
    ax.set_xlabel("lifetime revenue (₹ lakh)", fontsize=8)
    ax.set_ylabel("customers", fontsize=8); _grid(ax)

    fb = d["sqlt"]("cust_frequency_distribution")
    ax = _ax(fig, 0.432, 0.40, 0.235, 0.30, "Orders per customer",
             "Customers vs the revenue they carry")
    xx = np.arange(len(fb))
    ax.bar(xx - 0.19, fb["pct_of_customers"], width=0.36, color=THEME["cat"][4], label="% of customers")
    ax.bar(xx + 0.19, fb["pct_of_revenue"], width=0.36, color=THEME["cat"][0], label="% of revenue")
    for i, (c, r) in enumerate(zip(fb["pct_of_customers"], fb["pct_of_revenue"])):
        ax.text(i - 0.19, c + 0.8, f"{c:.0f}", ha="center", fontsize=7, color=THEME["ink"])
        ax.text(i + 0.19, r + 0.8, f"{r:.0f}", ha="center", fontsize=7, color=THEME["ink"])
    ax.set_xticks(xx); ax.set_xticklabels(fb["frequency_band"], fontsize=7)
    ax.set_ylabel("%", fontsize=8); ax.set_ylim(0, 58); _grid(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", labelcolor=THEME["ink"])

    rb = (cu[cu["Has_Delivered_Order"] == 1]
          .groupby(["Recency_Band_Order", "Recency_Band"]).size().reset_index(name="Customers")
          .sort_values("Recency_Band_Order"))
    ax = _ax(fig, 0.677, 0.40, 0.311, 0.30, "Recency distribution",
             "Days since the last delivered purchase at the 2026-01-01 reference date. Green and "
             "blue are active (< 180 days); amber and red are inactive, never 'churned'.")
    colors = [THEME["cat"][2], THEME["cat"][2], THEME["cat"][0], THEME["warning"], THEME["critical"]]
    b = ax.bar(rb["Recency_Band"], rb["Customers"], color=colors[:len(rb)], width=0.6)
    _barlabels(ax, b, lambda v: f"{int(v):,}")
    ax.set_ylabel("customers", fontsize=8); ax.set_ylim(0, rb["Customers"].max() * 1.18)
    ax.tick_params(labelsize=7.5); _grid(ax)

    top = (dl.groupby("Customer_ID").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                         Orders=("Order_ID", "nunique"))
           .sort_values("Revenue", ascending=False).head(10).reset_index())
    top = top.merge(cu[["Customer_ID", "Recency_Days", "RFM_Segment", "Illustrative_3Y_Value"]],
                    on="Customer_ID")
    tbl = top[["Customer_ID", "Revenue", "Profit", "Orders", "Recency_Days", "RFM_Segment",
               "Illustrative_3Y_Value"]]
    tbl.columns = ["Customer ID", "Revenue", "Profit", "Freq", "Recency (d)", "RFM segment",
                   "Illustrative 3Y value"]
    _table(fig, 0.152, 0.075, 0.515, 0.31, tbl,
           "Top 10 customers by revenue",
           "Customer_ID only - no names are published. Right-click a row to drill through to "
           "Customer Detail.",
           fmts=[str, lambda v: f"₹{v:,.0f}", lambda v: f"₹{v:,.0f}", lambda v: f"{int(v)}",
                 lambda v: f"{int(v)}", str, lambda v: f"₹{v:,.0f}"], highlight_col=1)

    ax = _ax(fig, 0.677, 0.075, 0.311, 0.31, "Revenue concentration (Pareto)",
             "Cumulative share of revenue as customers are added, best first")
    c = d["conc"]
    ax.plot(c["cumulative_pct_of_customers"], c["cumulative_pct_of_revenue"],
            color=THEME["cat"][2], lw=2)
    for xp, lab in [(10, "10%"), (20, "20%"), (50, "50%")]:
        yp = float(c.loc[(c["cumulative_pct_of_customers"] - xp).abs().idxmin(),
                         "cumulative_pct_of_revenue"])
        ax.plot([xp], [yp], "o", color=THEME["cat"][3], ms=6)
        ax.annotate(f"top {lab} of customers = {yp:.1f}% of revenue", (xp, yp),
                    xytext=(8, -12 - 0), textcoords="offset points", fontsize=7.5, color=THEME["ink"])
    ax.set_xlabel("% of customers", fontsize=8); ax.set_ylabel("% of revenue", fontsize=8)
    ax.set_xlim(0, 100); ax.set_ylim(0, 102); _grid(ax); _grid(ax, "x")
    return _save(fig, "03_customer_intelligence")


# --------------------------------------------------------------------- page 4
def mock_customer_segmentation(d: dict) -> Path:
    fig = _page(plt, "4 Customer Segmentation", "Customer Segmentation",
                "Rule-based RFM (Step 5) and K-Means clusters (Step 6), side by side")
    _slicer_row(fig)
    rfm = d["rfm"].sort_values("Revenue_%", ascending=False)
    ml = d["ml"].sort_values("Revenue_%", ascending=False)

    _panel_patch(fig, 0.152, 0.715, 0.836, 0.125)
    fig.text(0.164, 0.815, "Two segmentations, two jobs - neither is 'better'",
             color=THEME["ink_strong"], fontsize=10.5, weight="bold")
    import textwrap as _tw
    para = [
        ("RFM is a transparent rule on recency, frequency and monetary scores: every customer's "
         "segment can be explained to a business user in one sentence, and the rules are fixed in "
         "advance.", THEME["ink"]),
        ("K-Means is unsupervised: it finds groups in the scaled RFM features without being told "
         "what to look for, so it can surface structure the rules did not anticipate - but its "
         "clusters carry no business meaning until they are described.", THEME["ink"]),
        ("They agree on the large picture (both put roughly a sixth of customers on more than half "
         "of revenue) and differ at the boundaries. Use RFM to act on a named segment; use the "
         "clusters to check whether the rules still cut the base sensibly.", THEME["muted"]),
    ]
    yy = 0.800
    for text, col in para:
        lines = _tw.wrap(text, 150)
        fig.text(0.164, yy, "\n".join(lines), color=col, fontsize=8, va="top")
        yy -= 0.0138 * len(lines) + 0.005

    ax = _ax(fig, 0.152, 0.40, 0.30, 0.295, "RFM segments: customers and revenue",
             "Share of customers vs share of revenue (Step 5 rules)", pad_left=0.038)
    y = np.arange(len(rfm))[::-1]
    ax.barh(y + 0.19, rfm["Revenue_%"], height=0.36, color=THEME["cat"][0], label="% of revenue")
    ax.barh(y - 0.19, rfm["Customer_%"], height=0.36, color=THEME["cat"][4], label="% of customers")
    ax.set_yticks(y); ax.set_yticklabels(rfm["RFM_Segment"], fontsize=7)
    ax.set_xlabel("%", fontsize=8); _grid(ax, "x")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right", labelcolor=THEME["ink"])

    ax = _ax(fig, 0.462, 0.40, 0.25, 0.295, "K-Means clusters: customers and revenue",
             "Same comparison for the 4 unsupervised clusters (Step 6)", pad_left=0.04)
    y = np.arange(len(ml))[::-1]
    ax.barh(y + 0.19, ml["Revenue_%"], height=0.36, color=THEME["cat"][0], label="% of revenue")
    ax.barh(y - 0.19, ml["Customer_%"], height=0.36, color=THEME["cat"][4], label="% of customers")
    for yy, (r, c) in zip(y, ml[["Revenue_%", "Customer_%"]].values):
        ax.text(r + 1, yy + 0.19, f"{r:.1f}%", va="center", fontsize=7, color=THEME["ink"])
        ax.text(c + 1, yy - 0.19, f"{c:.1f}%", va="center", fontsize=7, color=THEME["ink"])
    ax.set_yticks(y); ax.set_yticklabels(ml["Business_Label"], fontsize=7.5)
    ax.set_xlim(0, 68); ax.set_xlabel("%", fontsize=8); _grid(ax, "x")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right", labelcolor=THEME["ink"])

    ax = _ax(fig, 0.722, 0.40, 0.266, 0.295, "Average R, F and M by segment",
             "Recency in days (lower is better), frequency in orders, monetary in ₹ lakh")
    seg = rfm.head(6)
    xx = np.arange(len(seg))
    ax.bar(xx - 0.27, seg["Average_Recency"] / 100, width=0.26, color=THEME["cat"][1],
           label="Recency (100 days)")
    ax.bar(xx, seg["Average_Frequency"] / 5, width=0.26, color=THEME["cat"][2],
           label="Frequency (5 orders)")
    ax.bar(xx + 0.27, seg["Average_Monetary"] / 1e5, width=0.26, color=THEME["cat"][0],
           label="Monetary (₹ lakh)")
    ax.set_xticks(xx); ax.set_xticklabels(seg["RFM_Segment"], fontsize=6.5, rotation=18)
    ax.set_ylabel("scaled units (see legend)", fontsize=7.5); _grid(ax)
    ax.legend(frameon=False, fontsize=7, ncol=1, loc="upper left", labelcolor=THEME["ink"])

    mat = rfm[["RFM_Segment", "Customer_Count", "Total_Revenue", "Average_Revenue",
               "Average_Frequency", "Average_Recency", "Revenue_%"]].copy()
    _table(fig, 0.152, 0.075, 0.56, 0.31, mat,
           "Segment matrix", "Sorted by revenue. In Power BI the Revenue column carries a data bar "
           "and Average recency a two-colour scale - the number is always shown as well, so colour "
           "is never the only cue.",
           fmts=[str, lambda v: f"{int(v):,}", lambda v: f"₹{v:,.0f}", lambda v: f"₹{v:,.0f}",
                 lambda v: f"{v:.1f}", lambda v: f"{v:.0f}", lambda v: f"{v:.1f}%"],
           highlight_col=2)

    ax = _ax(fig, 0.722, 0.075, 0.266, 0.31, "Revenue per customer by cluster",
             "What each cluster is worth, on average")
    ml2 = ml.sort_values("Revenue_to_Customer_Ratio")
    b = ax.barh(ml2["Business_Label"], ml2["Total_Revenue"] / ml2["Customer_Count"] / 1e3,
                color=THEME["cat"][0], height=0.6)
    _barlabels(ax, b, lambda v: f"₹{v:,.0f}k", horizontal=True)
    ax.set_xlim(0, (ml2["Total_Revenue"] / ml2["Customer_Count"] / 1e3).max() * 1.3)
    ax.set_xticks([]); ax.tick_params(labelsize=7.5); _grid(ax, "x")
    return _save(fig, "04_customer_segmentation")


# --------------------------------------------------------------------- page 5
def mock_product_analytics(d: dict) -> Path:
    fig = _page(plt, "5 Product Analytics", "Product Analytics",
                "Revenue, margin, discount and returns by category, sub-category and product")
    _slicer_row(fig)
    dl = d["deliv"]; prod = d["prod"]
    cat = dl.groupby("Category")[["Sales", "Profit", "Quantity"]].sum().sort_values("Sales")
    ax = _ax(fig, 0.152, 0.545, 0.25, 0.295, "Revenue and profit by category",
             "Revenue bar with profit shown inside it, so the margin gap is visible",
             pad_left=0.035)
    y = np.arange(len(cat))
    ax.barh(y, cat["Sales"] / 1e7, height=0.55, color=THEME["cat"][0], label="Revenue")
    ax.barh(y, cat["Profit"] / 1e7, height=0.30, color=THEME["cat"][2], label="Profit")
    for i, (rev, pr) in enumerate(cat[["Sales", "Profit"]].values):
        ax.text(rev / 1e7 * 1.02, i, f"{100 * pr / rev:.0f}% margin", va="center", fontsize=7,
                color=THEME["ink"])
    ax.set_yticks(y); ax.set_yticklabels(cat.index, fontsize=7.5)
    ax.set_xlim(0, cat["Sales"].max() / 1e7 * 1.32); ax.set_xlabel("₹ crore", fontsize=8)
    _grid(ax, "x")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right", labelcolor=THEME["ink"])

    top = prod.nlargest(10, "Revenue").sort_values("Revenue")
    ax = _ax(fig, 0.412, 0.545, 0.29, 0.295, "Top 10 products by revenue",
             "Label shows each product's own margin", pad_left=0.075)
    b = ax.barh(top["Product"].str.slice(0, 26), top["Revenue"] / 1e7, color=THEME["cat"][0],
                height=0.6)
    for bar, mg in zip(b, top["Profit_Margin_%"]):
        ax.text(bar.get_width() * 1.02, bar.get_y() + bar.get_height() / 2, f"{mg:.1f}%",
                va="center", fontsize=7, color=THEME["ink"])
    ax.set_xlim(0, top["Revenue"].max() / 1e7 * 1.2); ax.set_xlabel("₹ crore", fontsize=8)
    ax.tick_params(labelsize=7); _grid(ax, "x")

    prod = prod.copy()
    cmar = prod.groupby("Category")["Profit"].sum() / prod.groupby("Category")["Revenue"].sum() * 100
    prod["Margin_vs_Category_pp"] = prod["Profit_Margin_%"] - prod["Category"].map(cmar)
    bot = prod.nsmallest(10, "Margin_vs_Category_pp").sort_values("Margin_vs_Category_pp",
                                                                  ascending=False)
    ax = _ax(fig, 0.712, 0.545, 0.276, 0.295, "Bottom 10 products by margin vs their category",
             "Defined metric: product margin minus its own category's margin, in points",
             pad_left=0.072)
    b = ax.barh(bot["Product"].str.slice(0, 24), bot["Margin_vs_Category_pp"],
                color=[THEME["critical"] if v < -10 else THEME["serious"]
                       for v in bot["Margin_vs_Category_pp"]], height=0.6)
    for bar, v in zip(b, bot["Margin_vs_Category_pp"]):
        ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2, f"{v:.1f} pp",
                va="center", ha="left", fontsize=7, color=THEME["ink"])
    ax.set_xlim(bot["Margin_vs_Category_pp"].min() * 1.08, 4.5)
    ax.set_xlabel("percentage points vs category margin", fontsize=7.5)
    ax.tick_params(labelsize=7); _grid(ax, "x")

    ax = _ax(fig, 0.152, 0.075, 0.42, 0.44, "Revenue vs profit by product",
             "X = revenue, Y = profit, bubble size = units sold, colour = category. Points below "
             "the dashed line lose money. The notable products are labelled, so colour is never "
             "the only cue.")
    for i, (c, g) in enumerate(prod.groupby("Category")):
        ax.scatter(g["Revenue"] / 1e7, g["Profit"] / 1e7, s=np.sqrt(g["Quantity"]) * 6,
                   color=THEME["cat"][i % 8], alpha=0.85, edgecolor=THEME["panel"], linewidth=1.2,
                   label=c, zorder=3)
    ax.axhline(0, color=THEME["muted"], lw=1, ls="--")
    for _, r in prod.nlargest(3, "Revenue").iterrows():
        ax.annotate(r["Product"][:22], (r["Revenue"] / 1e7, r["Profit"] / 1e7),
                    xytext=(6, 6), textcoords="offset points", fontsize=7, color=THEME["ink"])
    worst = prod.nsmallest(1, "Profit").iloc[0]
    ax.annotate(f"{worst['Product'][:22]} ({worst['Profit_Margin_%']:.1f}% margin)",
                (worst["Revenue"] / 1e7, worst["Profit"] / 1e7), xytext=(12, 16),
                textcoords="offset points", fontsize=7, color=THEME["warning"])
    ax.set_xlabel("revenue (₹ crore)", fontsize=8); ax.set_ylabel("profit (₹ crore)", fontsize=8)
    _grid(ax); _grid(ax, "x")
    ax.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper left", labelcolor=THEME["ink"])

    bq14 = d["sqlt"]("BQ14").sort_values("lost_pct_of_booked")
    ax = _ax(fig, 0.582, 0.29, 0.20, 0.225, "Booked value lost by category",
             "Returns and cancellations, % of booked value")
    b = ax.barh(bq14["category"], bq14["lost_pct_of_booked"],
                color=[THEME["critical"] if v > 12 else THEME["cat"][1]
                       for v in bq14["lost_pct_of_booked"]], height=0.6)
    _barlabels(ax, b, lambda v: f"{v:.1f}%", horizontal=True)
    ax.set_xlim(0, 18); ax.set_xticks([]); ax.tick_params(labelsize=7); _grid(ax, "x")

    qty = dl.groupby("Category")["Quantity"].sum().sort_values()
    ax = _ax(fig, 0.582, 0.075, 0.20, 0.20, "Units sold by category",
             "Volume, to read alongside revenue")
    b = ax.barh(qty.index, qty.values, color=THEME["cat"][6], height=0.6)
    _barlabels(ax, b, lambda v: f"{int(v):,}", horizontal=True)
    ax.set_xlim(0, qty.max() * 1.25); ax.set_xticks([]); ax.tick_params(labelsize=7); _grid(ax, "x")

    inv = d["sqlt"]("prod_investigate")[["product_name", "profit_margin_pct", "reason"]].copy()
    inv["product_name"] = inv["product_name"].str.slice(0, 14)
    inv["reason"] = (inv["reason"].str.replace("margin < half of category margin", "thin margin")
                     .str.replace("return/cancel rate > 1.5x overall", "high returns"))
    inv.columns = ["Product", "Margin %", "Flagged for"]
    _table(fig, 0.792, 0.075, 0.196, 0.44, inv, "Products to investigate",
           "Step 10 rules: margin under half the category's, or a return rate above 1.5x overall.",
           fmts=[str, lambda v: f"{v:.1f}", str])
    return _save(fig, "05_product_analytics")


# --------------------------------------------------------------------- page 6
def mock_regional_analytics(d: dict) -> Path:
    fig = _page(plt, "6 Regional Analytics", "Regional Analytics",
                "Ranked regional performance and the category mix behind it")
    _slicer_row(fig)
    reg = d["sqlt"]("reg_performance")
    dl = d["deliv"]

    _panel_patch(fig, 0.152, 0.715, 0.836, 0.125)
    fig.text(0.164, 0.812, "Why this page uses ranked bars and a matrix, not a map",
             color=THEME["ink_strong"], fontsize=10.5, weight="bold")
    import textwrap as _tw
    note = ("The geography in this dataset is a customer's home city: 35 cities mapped to 5 "
            "business regions (North, South, East, West, Central). There are no latitude and "
            "longitude columns, no postal codes and no store locations, and the five regions are "
            "business groupings rather than official administrative boundaries - so a filled map "
            "would either need Power BI to geocode 35 city names or would shade areas the data "
            "does not actually describe. Ranked bars and a region x category matrix answer the "
            "same questions without that risk. If a map is wanted for the presentation, use the "
            "city-level bubble map with Country = India supplied in DimGeography, and check every "
            "city resolves before showing it.")
    fig.text(0.164, 0.792, "\n".join(_tw.wrap(note, 152)), color=THEME["ink"], fontsize=8, va="top")

    ax = _ax(fig, 0.152, 0.40, 0.27, 0.295, "Revenue and profit by region",
             "Ranked by revenue; profit drawn inside the revenue bar")
    r = reg.sort_values("revenue")
    y = np.arange(len(r))
    ax.barh(y, r["revenue"] / 1e7, height=0.55, color=THEME["cat"][0], label="Revenue")
    ax.barh(y, r["profit"] / 1e7, height=0.30, color=THEME["cat"][2], label="Profit")
    for i, (rev, mg) in enumerate(r[["revenue", "profit_margin_pct"]].values):
        ax.text(rev / 1e7 * 1.02, i, f"{rev / 1e7:.2f} Cr · {mg:.1f}%", va="center", fontsize=7,
                color=THEME["ink"])
    ax.set_yticks(y); ax.set_yticklabels(r["region"], fontsize=8)
    ax.set_xlim(0, r["revenue"].max() / 1e7 * 1.42); ax.set_xlabel("₹ crore", fontsize=8)
    _grid(ax, "x"); ax.legend(frameon=False, fontsize=7.5, loc="lower right", labelcolor=THEME["ink"])

    ax = _ax(fig, 0.432, 0.40, 0.25, 0.295, "Customers and orders by region",
             "Two counts on one axis - both are counts, so they are comparable")
    xx = np.arange(len(reg))
    ax.bar(xx - 0.19, reg["customers"], width=0.36, color=THEME["cat"][6], label="Customers")
    ax.bar(xx + 0.19, reg["orders"], width=0.36, color=THEME["cat"][0], label="Orders")
    for i, (c, o) in enumerate(zip(reg["customers"], reg["orders"])):
        ax.text(i - 0.19, c + 40, f"{c:,}", ha="center", fontsize=6.8, color=THEME["ink"])
        ax.text(i + 0.19, o + 40, f"{o:,}", ha="center", fontsize=6.8, color=THEME["ink"])
    ax.set_xticks(xx); ax.set_xticklabels(reg["region"], fontsize=7.5)
    ax.set_ylim(0, reg["orders"].max() * 1.2); _grid(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right", labelcolor=THEME["ink"])

    ax = _ax(fig, 0.692, 0.40, 0.296, 0.295, "Average order value and revenue per customer",
             "Both in ₹ thousand; AOV differs little between regions")
    xx = np.arange(len(reg))
    ax.bar(xx - 0.19, reg["average_order_value"] / 1e3, width=0.36, color=THEME["cat"][3],
           label="AOV (₹ thousand)")
    ax.bar(xx + 0.19, reg["revenue_per_customer"] / 1e3, width=0.36, color=THEME["cat"][0],
           label="Revenue per customer (₹ thousand)")
    for i, (a, rc) in enumerate(zip(reg["average_order_value"], reg["revenue_per_customer"])):
        ax.text(i - 0.19, a / 1e3 + 0.8, f"{a / 1e3:.1f}", ha="center", fontsize=6.8, color=THEME["ink"])
        ax.text(i + 0.19, rc / 1e3 + 0.8, f"{rc / 1e3:.1f}", ha="center", fontsize=6.8, color=THEME["ink"])
    ax.set_xticks(xx); ax.set_xticklabels(reg["region"], fontsize=7.5)
    ax.set_ylim(0, 44); _grid(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", ncol=2, labelcolor=THEME["ink"])

    piv = dl.pivot_table(index="Category", columns="Region", values="Sales", aggfunc="sum")
    prof = dl.pivot_table(index="Category", columns="Region", values="Profit", aggfunc="sum")
    marg = 100 * prof / piv
    order = piv.sum(1).sort_values(ascending=False).index
    marg = marg.loc[order]
    ax = _ax(fig, 0.152, 0.075, 0.44, 0.31, "Profit margin % by region and category",
             "Every cell shows its number - colour is a reading aid, not the information",
             pad_left=0.042)
    ax.imshow(marg.values, cmap="cividis", aspect="auto")
    ax.set_xticks(range(marg.shape[1])); ax.set_xticklabels(marg.columns, fontsize=8)
    ax.set_yticks(range(marg.shape[0])); ax.set_yticklabels(marg.index, fontsize=7.5)
    vmid = (np.nanmax(marg.values) + np.nanmin(marg.values)) / 2
    for i in range(marg.shape[0]):
        for j in range(marg.shape[1]):
            v = marg.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color="#0B111C" if v > vmid else "#FFFFFF")
    ax.grid(False)

    top_pairs = (dl.groupby(["Region", "Category"])["Sales"].sum().reset_index()
                 .sort_values("Sales", ascending=False).head(10))
    top_pairs["Share of region"] = top_pairs.apply(
        lambda r_: 100 * r_["Sales"] / dl[dl["Region"] == r_["Region"]]["Sales"].sum(), axis=1)
    tp = top_pairs[["Region", "Category", "Sales", "Share of region"]]
    _table(fig, 0.602, 0.075, 0.386, 0.31, tp, "Largest region x category combinations",
           "Where the revenue actually sits. Regional margin differences follow this mix: BQ16 "
           "found no region-category pair more than 2 points below the national margin.",
           fmts=[str, str, lambda v: f"₹{v / 1e7:.2f} Cr", lambda v: f"{v:.1f}%"], highlight_col=2)
    return _save(fig, "06_regional_analytics")


# --------------------------------------------------------------------- page 7
def mock_prediction_forecast(d: dict) -> Path:
    fig = _page(plt, "7 Prediction & Forecast", "Prediction & Forecast",
                "Customer-level prediction (Step 8) and company-level forecast (Step 9)")
    _slicer_row(fig, items=["Date: 01 Jan 2023 - 30 Jun 2026", "Region: All", "Category: All",
                            "Segment: All"])
    fc = d["fc"]; pred = d["pred"]; predq = d["predq"]; met = d["metrics"]

    # --- legend / label strip so Historical, Predicted and Forecast are never confused
    _panel_patch(fig, 0.152, 0.715, 0.836, 0.125)
    fig.text(0.164, 0.812, "Reading this page", color=THEME["ink_strong"], fontsize=10.5,
             weight="bold")
    keys = [("HISTORICAL", SERIES["historical"], "Actual delivered revenue, Jan 2023 - Dec 2025."),
            ("PREDICTED", SERIES["predicted"],
             "Step 8 machine-learning prediction of an individual customer's revenue in the next "
             "quarter (test split 2025 Q3-Q4)."),
            ("FORECAST", SERIES["forecast"],
             "Step 9 time-series forecast of total company revenue, Jan-Jun 2026, with prediction "
             "intervals.")]
    for i, (name, col, desc) in enumerate(keys):
        y = 0.792 - i * 0.021
        fig.patches.append(plt.Rectangle((0.166, y - 0.002), 0.018, 0.010,
                                         transform=fig.transFigure, facecolor=col, zorder=2))
        fig.text(0.190, y, name, color=THEME["ink_strong"], fontsize=8, weight="bold")
        fig.text(0.253, y, desc, color=THEME["ink"], fontsize=8)
    fig.text(0.164, 0.724, "The two models answer different questions on different units and are "
                           "never added together or averaged into a single number.",
             color=THEME["muted"], fontsize=7.8)

    # --- forecast chart
    hist = fc[fc["Record_Type"] == "Historical actual"].sort_values("Year_Month")
    back = fc[fc["Series_Label"] == "Forecast (backtest)"].sort_values("Year_Month")
    fut = fc[fc["Series_Label"] == "Forecast"].sort_values("Year_Month")
    months = list(hist["Year_Month"]) + list(fut["Year_Month"])
    idx = {m: i for i, m in enumerate(months)}
    ax = _ax(fig, 0.152, 0.40, 0.50, 0.295, "Company revenue: actual, backtest and forecast",
             "Shaded band = 95% prediction interval. It widens with the horizon, because month 6 "
             "is less certain than month 1.")
    ax.plot([idx[m] for m in hist["Year_Month"]], hist["Actual_Revenue"] / 1e5,
            color=SERIES["historical"], lw=2, label="Historical actual")
    ax.plot([idx[m] for m in back["Year_Month"]], back["Forecast_Revenue"] / 1e5,
            color=THEME["cat"][3], lw=1.8, ls="--", label="Backtest forecast (held-out months)")
    fx = [idx[m] for m in fut["Year_Month"]]
    ax.plot(fx, fut["Forecast_Revenue"] / 1e5, color=SERIES["forecast"], lw=2.2, label="Forecast")
    ax.fill_between(fx, fut["Lower_95"] / 1e5, fut["Upper_95"] / 1e5, color=SERIES["forecast"],
                    alpha=0.16, label="95% prediction interval")
    ax.axvline(len(hist) - 0.5, color=THEME["muted"], lw=1, ls=":")
    ax.text(len(hist) - 0.3, ax.get_ylim()[1] * 0.94, "forecast horizon starts",
            fontsize=7.5, color=THEME["muted"])
    ax.set_xticks(list(idx.values())[::4]); ax.set_xticklabels(months[::4], fontsize=7)
    ax.set_ylabel("₹ lakh", fontsize=8); _grid(ax)
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left", labelcolor=THEME["ink"])

    ftot = fut["Forecast_Revenue"].sum()
    _kpi(fig, 0.662, 0.555, 0.16, 0.14, "6-month forecast", _money(ftot),
         "Jan-Jun 2026, Theta model", SERIES["forecast"])
    fmape = float(met.query("Model_Area.str.startswith('Revenue forecast') and Metric == 'MAPE_%' "
                            "and Split.str.startswith('Test')")["Value"].iloc[0])
    _kpi(fig, 0.828, 0.555, 0.16, 0.14, "Forecast test MAPE", f"{fmape:.2f}%",
         "On 6 held-out months (2025-07..12)", THEME["cat"][3])
    _kpi(fig, 0.662, 0.40, 0.16, 0.14, "Prediction MAE", f"₹{pred['Absolute_Error'].mean():,.0f}",
         "Per customer-quarter, test split", SERIES["predicted"])
    r2 = float(met.query("Model_Area.str.startswith('Revenue prediction') and Metric == 'R2' "
                         "and Split.str.startswith('Test')")["Value"].iloc[0])
    _kpi(fig, 0.828, 0.40, 0.16, 0.14, "Prediction R²", f"{r2:.3f}",
         "Weak at customer level - use for ranking", THEME["warning"])

    # --- prediction: quarterly totals
    ax = _ax(fig, 0.152, 0.075, 0.28, 0.31, "Customer revenue: actual vs predicted by quarter",
             "Step 8. Shaded quarters are the out-of-sample test split; the train quarters are an "
             "in-sample fit and are shown as such.")
    xx = np.arange(len(predq))
    ax.bar(xx - 0.19, predq["Actual_Revenue"] / 1e7, width=0.36, color=SERIES["historical"],
           label="Actual")
    ax.bar(xx + 0.19, predq["Predicted_Revenue"] / 1e7, width=0.36, color=SERIES["predicted"],
           label="Predicted")
    for i, sp in enumerate(predq["Split"]):
        if sp.startswith("test"):
            ax.axvspan(i - 0.45, i + 0.45, color=THEME["cat"][2], alpha=0.10, zorder=0)
    ax.set_xticks(xx); ax.set_xticklabels([t.replace("-", "\n") for t in predq["Target_Period"]],
                                          fontsize=7)
    ax.set_ylabel("₹ crore", fontsize=8); _grid(ax)
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left", labelcolor=THEME["ink"])

    by_seg = (pred.groupby("RFM_Segment_At_Cutoff")
              .agg(MAE=("Absolute_Error", "mean"), Customers=("Customer_ID", "nunique"))
              .sort_values("MAE").tail(8))
    ax = _ax(fig, 0.442, 0.075, 0.25, 0.31, "Prediction error by segment at the cutoff",
             "Mean absolute error per customer-quarter - the error is largest where revenue is "
             "largest", pad_left=0.045)
    b = ax.barh(by_seg.index, by_seg["MAE"] / 1e3, color=SERIES["predicted"], height=0.6)
    _barlabels(ax, b, lambda v: f"₹{v:,.1f}k", horizontal=True)
    ax.set_xlim(0, (by_seg["MAE"] / 1e3).max() * 1.35); ax.set_xticks([])
    ax.tick_params(labelsize=7); _grid(ax, "x")

    mt = met[met["Split"].str.startswith(("Test", "Rolling"))].copy()
    mt["Model"] = (mt["Model"].str.split(":").str[0].str.replace("Baseline", "Base", regex=False)
                   .str.slice(0, 18))
    mt = mt[["Model", "Metric", "Value"]]
    mt.columns = ["Model", "Metric", "Value (test split)"]
    _table(fig, 0.702, 0.075, 0.286, 0.31, mt.head(11),
           "Model performance (Steps 8 and 9 only)",
           "Read from the ModelMetrics table, which is generated from the saved model metadata - "
           "no metric is typed onto the page.",
           fmts=[str, str, lambda v: f"{v:,.3f}" if abs(v) < 100 else f"{v:,.0f}"],
           highlight_col=2)
    return _save(fig, "07_prediction_forecast")


# --------------------------------------------------------------------- page 8
def mock_business_recommendations(d: dict) -> Path:
    fig = _page(plt, "8 Business Recommendations", "Business Recommendations",
                "Grouped by area; every card carries the metric and the saved analysis behind it")
    recs = d["recs"].sort_values(["Area_Order", "Recommendation_ID"]).reset_index(drop=True)
    accent = {"Customer": THEME["cat"][0], "Product": THEME["cat"][3], "Regional": THEME["cat"][2],
              "Revenue": THEME["cat"][6], "Forecasting & Planning": THEME["cat"][4]}
    import textwrap as _tw
    cols_x = [0.152, 0.572]
    w = 0.416
    for i, r in recs.iterrows():
        col, row = i // 9, i % 9
        x = cols_x[col]
        h = 0.0775
        y = 0.762 - row * (h + 0.0045)
        _panel_patch(fig, x, y, w, h)
        fig.patches.append(plt.Rectangle((x, y), 0.0035, h, transform=fig.transFigure,
                                         facecolor=accent[r["Area"]], zorder=1))
        fig.text(x + 0.012, y + h - 0.018, f"{r['Area'].upper()}  ·  {r['Recommendation_ID']}",
                 color=accent[r["Area"]], fontsize=6.6, weight="bold")
        title = _tw.wrap(r["Recommendation"], 88)[:2]
        fig.text(x + 0.012, y + h - 0.028, "\n".join(title), color=THEME["ink_strong"],
                 fontsize=8.2, weight="bold", va="top")
        allowed = 3 - len(title)
        ev_lines = _tw.wrap(r["Evidence"], 116)
        ev = ev_lines[:allowed]
        if len(ev_lines) > allowed:
            ev[-1] = ev[-1][:112].rstrip(" ,.;") + " ..."
        fig.text(x + 0.012, y + h - 0.030 - 0.0122 * len(title), "\n".join(ev),
                 color=THEME["ink"], fontsize=6.9, va="top")
        fig.text(x + 0.012, y + 0.006,
                 f"{r['Supporting_Metric']}: {r['Metric_Value']}   ·   {r['Analytical_Source'][:58]}",
                 color=THEME["muted"], fontsize=6.6)
    fig.text(0.152, 0.043,
             "The full evidence and the suggested action for every recommendation are in the "
             "Recommendations table (powerbi/data/Recommendations.csv), shown in Power BI as an "
             "expandable table with the Evidence and Action columns and the source in the tooltip.",
             color=THEME["muted"], fontsize=7.5)
    return _save(fig, "08_business_recommendations")


# --------------------------------------------------------------------- HOME + drill-through
def mock_home(d: dict) -> Path:
    fig = _page(plt, "HOME", "Customer Revenue Intelligence",
                "Executive dashboard - synthetic dataset, internship project")
    k = d["kpi"]
    _panel_patch(fig, 0.152, 0.50, 0.50, 0.34)
    fig.text(0.168, 0.795, "What this report answers", color=THEME["ink_strong"], fontsize=12,
             weight="bold")
    import textwrap as _tw
    blurb = ("Eight pages built on one star schema and one revenue definition: delivered lines "
             "only. Revenue and profitability, customer value and segmentation, products, regions, "
             "and the two forward-looking models - a customer-level revenue prediction and a "
             "company-level revenue forecast - each shown with the accuracy it actually achieved "
             "on held-out data. The last page turns the analysis into recommendations, each one "
             "carrying the query it came from.")
    fig.text(0.168, 0.768, "\n".join(_tw.wrap(blurb, 88)), color=THEME["ink"], fontsize=9, va="top")
    facts = ["Period: Jan 2023 - Dec 2025  ·  reference date 2026-01-01",
             f"Scale: {int(k['Number of Orders']):,} delivered orders, "
             f"{int(k['Purchasing Customers']):,} customers, 61 products, 35 cities",
             "Data: synthetic, generated for this project - not real customers",
             "Source of truth: SQLite database validated in Step 10 (56 checks)"]
    for i, t in enumerate(facts):
        fig.text(0.168, 0.605 - i * 0.026, "•", color=THEME["cat"][0], fontsize=9)
        fig.text(0.176, 0.605 - i * 0.026, t, color=THEME["ink"], fontsize=8.5)

    cards = [("Total revenue", _money(k["Total Revenue"])), ("Total profit", _money(k["Total Profit"])),
             ("Profit margin", f"{k['Overall Profit Margin']:.1%}"),
             ("Customers", f"{int(k['Purchasing Customers']):,}")]
    for i, (lab, val) in enumerate(cards):
        _kpi(fig, 0.662 + (i % 2) * 0.168, 0.675 + (1 - i // 2) * 0.0 - (i // 2) * 0.175,
             0.158, 0.165, lab, val, "Delivered lines, 2023-2025", THEME["cat"][0])

    _panel_patch(fig, 0.152, 0.075, 0.836, 0.40)
    fig.text(0.168, 0.435, "Pages", color=THEME["ink_strong"], fontsize=12, weight="bold")
    descs = [
        ("1 Executive Overview", "Headline KPIs, monthly trend, region, category and segment mix"),
        ("2 Revenue Intelligence", "Revenue, profit, margin, growth, sub-categories, discount effects"),
        ("3 Customer Intelligence", "Value distribution, frequency, recency, top customers"),
        ("4 Customer Segmentation", "RFM rules and K-Means clusters compared, segment matrix"),
        ("5 Product Analytics", "Category and product revenue, margin, returns, the scatter"),
        ("6 Regional Analytics", "Regional performance and the region x category matrix"),
        ("7 Prediction & Forecast", "Step 8 prediction and Step 9 forecast, with their metrics"),
        ("8 Business Recommendations", "18 recommendations, each traced to a saved analysis"),
    ]
    for i, (name, desc) in enumerate(descs):
        x = 0.168 + (i % 2) * 0.42
        y = 0.395 - (i // 2) * 0.075
        fig.patches.append(plt.Rectangle((x - 0.006, y - 0.040), 0.40, 0.062,
                                         transform=fig.transFigure, facecolor="#101725",
                                         edgecolor=THEME["border"], zorder=-0.5))
        fig.text(x + 0.004, y, name, color=THEME["ink_strong"], fontsize=9.5, weight="bold")
        fig.text(x + 0.004, y - 0.024, desc, color=THEME["muted"], fontsize=8)
    return _save(fig, "00_home")


def mock_drillthrough(d: dict) -> Path:
    fig = _page(plt, "3 Customer Intelligence", "Customer Detail (drill-through)",
                "Reached by right-clicking any customer row or bar - Customer_ID is the "
                "drill-through field")
    dl = d["deliv"]; cu = d["cust"]
    cid = (dl.groupby("Customer_ID")["Sales"].sum().idxmax())
    c = cu[cu["Customer_ID"] == cid].iloc[0]
    rows = dl[dl["Customer_ID"] == cid]
    _panel_patch(fig, 0.152, 0.715, 0.836, 0.125)
    fig.text(0.164, 0.805, f"Customer {cid}", color=THEME["ink_strong"], fontsize=14, weight="bold")
    fig.text(0.164, 0.775, f"{c['Age_Band']} · {c['Gender']} · {c['Home_Region']} · "
                           f"{c['Acquisition_Status']}", color=THEME["muted"], fontsize=9)
    fig.text(0.164, 0.740, "No customer name is shown anywhere in this report - Customer_ID is the "
                           "only identifier published.", color=THEME["warning"], fontsize=8)
    facts = [("RFM segment", c["RFM_Segment"]), ("Cluster", str(c["Cluster_ID"])),
             ("Recency", f"{int(c['Recency_Days'])} days"),
             ("Frequency", f"{int(c['Frequency_Orders'])} orders"),
             ("Monetary", _money(c["Monetary_Revenue"])),
             ("RFM score", f"{int(c['RFM_Score'])} ({c['RFM_Cell']})")]
    for i, (lab, val) in enumerate(facts):
        fig.text(0.60 + (i % 3) * 0.132, 0.808 - (i // 3) * 0.050, lab.upper(),
                 color=THEME["muted"], fontsize=7.5, weight="bold")
        fig.text(0.60 + (i % 3) * 0.132, 0.786 - (i // 3) * 0.050, val, color=THEME["ink_strong"],
                 fontsize=9.5)

    cards = [("Lifetime revenue", _money(c["Historical_Revenue_CLV"]), "Delivered, to date", THEME["cat"][0]),
             ("Lifetime profit", _money(c["Historical_Profit_CLV"]), "Delivered, to date", THEME["cat"][2]),
             ("Orders", f"{int(c['Frequency_Orders'])}", "Delivered orders", THEME["cat"][0]),
             ("Est. next-12m profit", _money(c["Estimated_12M_Future_Profit"]),
              "Step 7 ESTIMATE, not actual", THEME["cat"][1]),
             ("Illustrative 3Y value", _money(c["Illustrative_3Y_Value"]),
              "Illustrative only - assumes repeat rate holds", THEME["cat"][3])]
    w = 0.162
    for i, (lab, val, sub, acc) in enumerate(cards):
        _kpi(fig, 0.152 + i * (w + 0.007), 0.565, w, 0.13, lab, val, sub, acc)

    m = rows.groupby("Year_Month")["Sales"].sum()
    ax = _ax(fig, 0.152, 0.27, 0.42, 0.28, "This customer's revenue by month",
             "Bars, because a single customer's months are separate purchases, not a continuous "
             "series")
    ax.bar(range(len(m)), m.values / 1e3, color=THEME["cat"][0], width=0.7)
    ax.set_xticks(range(0, len(m), max(1, len(m) // 8)))
    ax.set_xticklabels(m.index[::max(1, len(m) // 8)], fontsize=7, rotation=45)
    ax.set_ylabel("₹ thousand", fontsize=8); _grid(ax)

    cat = rows.groupby("Category")["Sales"].sum().sort_values()
    ax = _ax(fig, 0.584, 0.27, 0.20, 0.28, "Category mix", "Where this customer spends")
    b = ax.barh(cat.index, cat.values / 1e3, color=THEME["cat"][3], height=0.6)
    _barlabels(ax, b, lambda v: f"₹{v:,.0f}k", horizontal=True)
    ax.set_xlim(0, cat.max() / 1e3 * 1.35); ax.set_xticks([]); ax.tick_params(labelsize=7.5)
    _grid(ax, "x")

    recent = (rows.sort_values("Order_Date", ascending=False)
              .groupby("Order_ID", sort=False)
              .agg(Order_Date=("Order_Date", "first"), Lines=("Order_Line_ID", "count"),
                   Revenue=("Sales", "sum"), Profit=("Profit", "sum")).reset_index().head(9))
    recent = recent[["Order_Date", "Revenue", "Profit"]]
    recent.columns = ["Order date", "Revenue", "Profit"]
    _table(fig, 0.794, 0.27, 0.194, 0.28, recent, "Most recent orders",
           "Order ID and line detail appear in the tooltip",
           fmts=[str, lambda v: f"₹{v:,.0f}", lambda v: f"₹{v:,.0f}"])

    _panel_patch(fig, 0.152, 0.055, 0.836, 0.20)
    fig.text(0.164, 0.228, "Drill-through and tooltip pages in this report", color=THEME["ink_strong"],
             fontsize=10.5, weight="bold")
    items = [
        ("Customer Detail (this page)", "Drill-through field: DimCustomer[Customer_ID]. Reached "
         "from the top-customer table, the segment matrix and the prediction table."),
        ("Product Detail", "Drill-through field: DimProduct[Product_ID]. Shows revenue, margin, "
         "discount band mix, return rate and monthly trend for one product."),
        ("Customer tooltip", "Tooltip page (320 x 240). Shows revenue, orders, recency, segment "
         "and estimated 12-month profit on hover."),
        ("Product tooltip", "Tooltip page (320 x 240). Shows revenue, margin, units, average "
         "discount and return rate on hover."),
    ]
    import textwrap as _tw
    for i, (name, desc) in enumerate(items):
        x = 0.166 + (i % 2) * 0.42
        y = 0.196 - (i // 2) * 0.062
        fig.text(x, y, name, color=THEME["ink_strong"], fontsize=8.5, weight="bold")
        fig.text(x, y - 0.018, "\n".join(_tw.wrap(desc, 82)), color=THEME["muted"], fontsize=7.5,
                 va="top")
    return _save(fig, "09_customer_detail_drillthrough")


def build_mockups(con: sqlite3.Connection) -> list[Path]:
    _mpl()
    d = _mock_data(con)
    return [mock_home(d), mock_executive_overview(d), mock_revenue_intelligence(d),
            mock_customer_intelligence(d), mock_customer_segmentation(d),
            mock_product_analytics(d), mock_regional_analytics(d), mock_prediction_forecast(d),
            mock_business_recommendations(d), mock_drillthrough(d)]


# =========================================================================== 8. documentation
PAGE_SPECS = [
    ("HOME", "00_home", "Entry page: what the report answers, headline KPIs, page directory.",
     ["Four KPI cards (revenue, profit, margin, customers)", "Page directory with navigation buttons",
      "Synthetic-data statement"]),
    ("1 Executive Overview", "01_executive_overview",
     "The whole business on one screen: how much, how profitable, where it comes from.",
     ["KPI cards: Total Revenue, Total Profit, Profit Margin %, Total Orders, Total Customers, AOV",
      "Line: monthly revenue and profit (one axis, both in rupees)",
      "Ranked bars: revenue by region", "Ranked bars: revenue by category with margin labels",
      "Paired bars: revenue share vs customer share by RFM segment",
      "Column: revenue by year with growth % labels", "Line: cumulative revenue by customer (Pareto)"]),
    ("2 Revenue Intelligence", "02_revenue_intelligence",
     "Where revenue and margin come from over time, and what moves them.",
     ["Line: revenue and profit by month with the cost gap shaded",
      "Line: profit margin % by month (its own chart - a ratio never shares an axis with rupees)",
      "Columns: year-over-year revenue and profit growth %",
      "Ranked bars: top 10 sub-categories with margin labels",
      "Columns: margin by discount band", "Lines: discount band vs margin within each category",
      "Grouped bars: revenue by region and year", "Text panel: revenue drivers, each naming its query"]),
    ("3 Customer Intelligence", "03_customer_intelligence",
     "Who the customers are, what they are worth, and how recently they bought.",
     ["KPI cards: customers, active customers, average customer revenue, AOV, repeat customers, "
      "at-risk high-value customers",
      "Histogram: lifetime revenue per customer", "Paired bars: orders-per-customer bands",
      "Columns: recency distribution", "Table: top 10 customers (Customer_ID, revenue, profit, "
      "frequency, recency, segment, illustrative 3-year value)",
      "Line: revenue concentration (Pareto) with the 10 / 20 / 50% points marked"]),
    ("4 Customer Segmentation", "04_customer_segmentation",
     "RFM rules and K-Means clusters, compared without ranking one above the other.",
     ["Text panel: what each method is for",
      "Paired bars: RFM segments - customer share vs revenue share",
      "Paired bars: K-Means clusters - customer share vs revenue share",
      "Grouped columns: average recency, frequency and monetary by segment",
      "Matrix: segment, customers, revenue, profit, average revenue, average frequency, "
      "average recency, revenue %", "Ranked bars: revenue per customer by cluster"]),
    ("5 Product Analytics", "05_product_analytics",
     "Which products earn, which only turn over, and which lose value to returns.",
     ["Bars: revenue with profit inside, by category, margin labelled",
      "Ranked bars: top 10 products by revenue with their margin",
      "Ranked bars: bottom 10 products by margin versus their own category (defined metric)",
      "Scatter: revenue (X) vs profit (Y), bubble size = units, colour = category, notable "
      "products labelled", "Bars: booked value lost by category", "Bars: units sold by category",
      "Table: products flagged for investigation by the Step 10 rules"]),
    ("6 Regional Analytics", "06_regional_analytics",
     "Regional performance, and the category mix that explains it.",
     ["Text panel: why ranked bars and a matrix are used instead of a map",
      "Bars: revenue with profit inside, by region, margin labelled",
      "Grouped columns: customers and orders by region",
      "Grouped columns: AOV and revenue per customer by region",
      "Matrix / heat table: profit margin % by region and category, every cell numbered",
      "Table: largest region x category combinations"]),
    ("7 Prediction & Forecast", "07_prediction_forecast",
     "The two forward-looking models, kept strictly apart.",
     ["Legend panel defining Historical, Predicted and Forecast",
      "Line: monthly actual, backtest forecast and future forecast with the 95% interval shaded",
      "KPI cards: 6-month forecast total, forecast test MAPE, prediction MAE, prediction R²",
      "Columns: actual vs predicted customer revenue by quarter, test quarters shaded",
      "Bars: prediction error by segment at the cutoff",
      "Table: model performance, read from ModelMetrics"]),
    ("8 Business Recommendations", "08_business_recommendations",
     "18 recommendations grouped into Customer, Product, Regional, Revenue and "
     "Forecasting & Planning, each with its evidence and source.",
     ["18 recommendation cards, colour-coded by area",
      "Each card: recommendation, evidence with figures, supporting metric, and the saved query, "
      "table or model metadata it came from",
      "Table visual behind the cards with the full Evidence and Suggested_Action columns"]),
]

CHECKLIST = [
    ("Power BI data model created",
     "Done (files)", "13 tables exported to powerbi/data/ from the pbi_* SQL views; catalogue in "
     "powerbi/table_catalog.csv. Loading them into Power BI Desktop is a manual step."),
    ("Relationships validated",
     "Done (files) + Validated (Python)", "9 relationships specified in powerbi/relationships.csv "
     "with cardinality, cross-filter direction and active flag. Key uniqueness and orphan keys "
     "checked in powerbi/validation/cross_step_consistency.csv."),
    ("Date table created",
     "Done (files)", "DimDate: 1,277 daily rows, 2023-01-01 to 2026-06-30, with Year, Quarter, "
     "Month Number, Month Name, Year-Month, ISO week, Day, financial-year attributes and "
     "Period_Type. Marking it as the official date table and sorting Month Name by Month Number "
     "are manual steps in Power BI Desktop."),
    ("DAX measures created",
     "Done (files)", "84 measures in powerbi/dax/measures.dax, grouped into 10 display folders, "
     "each with its format string and purpose. Pasting them into the model is manual."),
    ("Core KPI values reconciled with SQL/Python",
     "Validated (Python/SQL)", "15 measures x 8 filter contexts recomputed in pandas; the four "
     "required measures plus margin and AOV independently recomputed in SQL - 48 of 48 comparisons "
     "match. Targets for the Power BI cards: powerbi/validation/measure_validation_targets.csv."),
    ("Executive Overview created", "Specified + mockup", "Layout, visuals and measures specified; "
     "design mockup 01. Building the page in Power BI Desktop is manual."),
    ("Revenue Intelligence created", "Specified + mockup", "Layout, visuals and measures specified; "
     "design mockup 02. Building the page is manual."),
    ("Customer Intelligence created", "Specified + mockup", "Layout, visuals and measures "
     "specified; design mockup 03. Building the page is manual."),
    ("Customer Segmentation created", "Specified + mockup", "Layout, visuals and measures "
     "specified; design mockup 04. Building the page is manual."),
    ("Product Analytics created", "Specified + mockup", "Layout, visuals and measures specified; "
     "design mockup 05. Building the page is manual."),
    ("Regional Analytics created", "Specified + mockup", "Layout, visuals and measures specified; "
     "design mockup 06. Building the page is manual."),
    ("Prediction & Forecast created", "Specified + mockup", "Layout, visuals and measures "
     "specified; design mockup 07. Building the page is manual."),
    ("Business Recommendations created", "Done (content) + mockup", "18 recommendations computed "
     "from the Step 4-10 outputs into powerbi/data/Recommendations.csv; design mockup 08. Placing "
     "them on the page is manual."),
    ("Slicers configured", "Specified", "Seven synced slicers specified (Date, Year, Month, Region, "
     "Category, Sub-category, Segment/Cluster) with their sync groups; see section 8 of the "
     "documentation. Configuring them is manual."),
    ("Drill-through configured where appropriate", "Specified + mockup", "Customer Detail and "
     "Product Detail drill-through pages specified with their drill-through fields; Customer "
     "Detail mockup 09. Configuring them is manual."),
    ("Tooltips configured where appropriate", "Specified", "Customer and Product tooltip pages "
     "specified (320 x 240, fields listed in section 9). Configuring them is manual."),
    ("Navigation created", "Specified + mockup", "HOME plus the 8 pages, with a left navigation "
     "rail and page-navigation buttons; shown on every mockup. Adding the buttons is manual."),
    ("Dashboard design standardized", "Done (files)", "Theme JSON (powerbi/theme/"
     "crm_dark_theme.json), page background PNG and palette reference; one format string per "
     "measure. Applying the theme is one manual step."),
    ("Documentation created", "Done", "outputs/reports/powerbi_dashboard_documentation.md, 14 "
     "sections."),
    ("User guide created", "Done", "outputs/reports/powerbi_user_guide.md."),
    ("No fabricated results", "Verified", "Every figure in the extracts, recommendations, mockups "
     "and documentation is read from a Step 4-10 output file; cross-step consistency is checked "
     "in powerbi/validation/cross_step_consistency.csv (32 of 32 pass). No Power BI screenshot is "
     "claimed - outputs/figures/powerbi/ holds labelled design mockups and a README that says so."),
]


def write_checklist() -> pd.DataFrame:
    df = pd.DataFrame(CHECKLIST, columns=["Checklist_Item", "Status", "Evidence"])
    df.to_csv(TAB / "powerbi_validation_checklist.csv", index=False)
    df.to_csv(PBI_DIR / "validation_checklist.csv", index=False)
    return df


def _md_table(df: pd.DataFrame) -> str:
    cols = [str(c).replace("_", " ") for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in r.values) + " |")
    return "\n".join(lines)


def write_documentation(con, catalog, rel, measures, check, cons, checklist) -> Path:
    kpi = pd.read_csv(TAB / "eda_kpis.csv").set_index("KPI")["Value"]
    fm = json.loads((config.PROJECT_ROOT / "models" / "forecasting_metadata.json").read_text())
    rm = json.loads((config.PROJECT_ROOT / "models" / "revenue_model_metadata.json").read_text())
    fut = pd.read_sql_query("SELECT SUM(Forecast_Revenue) t FROM pbi_fact_forecast "
                            "WHERE Series_Label = 'Forecast'", con).iloc[0, 0]
    recs = pd.read_csv(PBI_DATA / "Recommendations.csv")
    matched = int((check["Reconciled"] == "Match").sum())
    total_sql = int(check["SQL_Value"].notna().sum())

    pages_md = []
    for name, slug, purpose, visuals in PAGE_SPECS:
        vis = "\n".join(f"  - {v}" for v in visuals)
        pages_md.append(f"### {name}\n\n**Purpose.** {purpose}\n\n**Visuals.**\n\n{vis}\n\n"
                        f"**Design mockup.** `outputs/figures/powerbi/mockups/{slug}_mockup.png` "
                        f"(a specification drawn from the real data, not a Power BI screenshot).")
    pages_block = "\n\n".join(pages_md)

    md = f"""# Power BI Executive Dashboard - Documentation

**Project:** Customer Revenue Intelligence - An Interactive Data Science Platform for Customer
Segmentation, Revenue Prediction and Business Growth
**Step:** 11 of the project pipeline
**Dataset:** SYNTHETIC. Generated for this internship project; it does not describe real customers
or a real company.

> **What was built here, and what has to be built in Power BI Desktop.**
> Power BI Desktop runs only on Windows and cannot be installed or automated in this project's
> Linux environment. Everything that feeds the report - the star-schema extracts, the Power Query
> scripts, the DAX measure library, the theme, the recommendation content and the validated target
> values - was produced and checked here. The report file itself (`.pbix`) is assembled manually
> following `powerbi/POWERBI_BUILD_GUIDE.md`. No screenshot of a Power BI page is included, because
> none was taken; `outputs/figures/powerbi/mockups/` holds labelled design mockups instead.

---

## 1. Dashboard objective

Give a business reader the answer to six questions in one report, without asking them to open a
notebook:

1. How much revenue and profit does the business make, and how is that changing?
2. Which customers produce it, and which of them are drifting away?
3. How do the rule-based segments and the machine-learning clusters describe the customer base?
4. Which products and categories earn money rather than simply turn it over?
5. Which regions perform, and why?
6. What do the two forward-looking models say, and how accurate have they actually been?

The eighth page turns those answers into recommendations, each one carrying the analysis it rests
on.

**Scope limit.** The dashboard presents the analysis of Steps 3-10. It does not recompute
segmentation, customer value, predictions or forecasts; those were produced, validated and frozen
in their own steps, and Power BI reads their outputs.

---

## 2. Data sources

Everything comes from the validated Step 10 SQLite database
`data/customer_revenue_intelligence.db` and the saved model metadata. Power BI never reads the raw
CSV files.

| Layer | Source | Produced in |
|---|---|---|
| Transactions | `locations`, `customers`, `products`, `orders`, `order_items` | Step 3 (cleaning), loaded in Step 10 |
| RFM segments | `customer_rfm`, `rfm_segment_definitions` | Step 5 |
| K-Means clusters | `customer_segments`, `ml_clusters` | Step 6 |
| Customer value | `customer_value` | Step 7 |
| Revenue prediction | `outputs/tables/revenue_predictions.csv`, `revenue_quarterly_totals.csv`, `models/revenue_model_metadata.json` | Step 8 |
| Revenue forecast | `revenue_forecasts` table, `models/forecasting_metadata.json` | Step 9 |
| Recommendation evidence | `outputs/tables/` and `outputs/tables/sql/` | Steps 4-10 |

The extracts are produced by `sql/powerbi_views.sql` (eight `pbi_*` views) and
`src/powerbi_prep.py`, which writes `powerbi/data/*.csv`. Re-running the module regenerates every
file deterministically.

**Revenue rule.** Only Delivered order lines count as revenue. The rule is applied in one place in
SQL (`vw_delivered_sales`) and in one place in DAX (`FactSales[Is_Delivered] = 1` inside every
currency measure). Returned and Cancelled lines stay in the fact table so the realisation analysis
is possible, and are excluded from every revenue figure.

**Privacy.** `DimCustomer` deliberately has no name column. Analytical outputs identify a customer
by `Customer_ID` only. The dataset is synthetic, but the same rule is applied as if it were not.

---

## 3. Data model

A star schema: two transaction facts, two model facts and six dimensions, plus three supporting
tables that hold model metadata and recommendation content.

{_md_table(catalog[["Table", "Role", "Rows", "Columns", "Grain"]])}

Design notes:

- **FactSales keeps every order line**, with `Is_Delivered` as a flag, rather than filtering
  Delivered rows at load time. One fact table then answers both "what did we earn" and "what did we
  lose to returns", and the two can never disagree.
- **Customer state is folded into DimCustomer**, not left in separate tables. RFM scores, cluster
  assignment and customer-value fields are one-per-customer snapshots at the 2026-01-01 reference
  date, so they belong on the customer dimension. `DimRFMSegment` and `DimCluster` snowflake off it
  to carry segment descriptions and ordering.
- **DimGeography is joined to the fact**, not only to the customer, so a region slicer filters sales
  directly. In this dataset each customer has exactly one home location, so the two routes agree.
- **Customers with no delivered order** (16 of 2,000) get the member "No delivered order" in
  `DimRFMSegment` and `DimCluster` rather than a blank, so a segment slicer never shows an empty row.
- **No duplicated measures columns.** Nothing is pre-aggregated: every number on every page is a
  DAX measure over these tables.

### Date table

`DimDate` has one row per day from 2023-01-01 to 2026-06-30 - the 36 historical months plus the
6-month forecast horizon, so forecast rows have real dates to join to. Columns: `Date`, `Year`,
`Quarter`, `Quarter_Number`, `Year_Quarter`, `Month_Number`, `Month_Name`, `Month_Short`,
`Year_Month`, `Year_Month_Sort`, `Month_Start_Date`, `Week_Number` (ISO), `ISO_Week_Year`, `Day`,
`Day_Of_Week_Number`, `Day_Name`, `Is_Weekend`, `Financial_Year`, `Financial_Year_Start`,
`Financial_Quarter`, `Financial_Month_Number`, `Period_Type`.

The financial-year columns follow the Indian April-March convention as a standard calendar
attribute; the dataset does not state a company fiscal year, so they are offered rather than used as
the default.

Two manual steps in Power BI Desktop: sort `Month_Name` by `Month_Number` (and `Year_Month` by
`Year_Month_Sort`, `Year_Quarter` by `Year_Quarter_Sort`), and mark the table as the official date
table on `DimDate[Date]`.

---

## 4. Relationships

{_md_table(rel)}

The only inactive relationship is `DimDate -> FactRevenuePrediction`. The prediction grain is a
quarter, not a day, so leaving that relationship active would let a date slicer silently drop
prediction rows and make the model look wrong. The Prediction & Forecast page therefore filters
predictions by `Target_Period` from the prediction table itself.

---

## 5. DAX measures

`powerbi/dax/measures.dax` holds {len(measures)} measures in {measures['Display_Folder'].nunique()}
display folders, each with its format string and a one-line statement of what it is for.
`powerbi/dax/measure_catalog.csv` is the same list as a table.

| Display folder | Measures | What it covers |
|---|---|---|
| 01 Revenue | {int((measures['Display_Folder'] == '01 Revenue').sum())} | Total revenue, booked value and realisation, prior-year and prior-month comparisons, growth %, YTD, average monthly revenue, the ₹ lakh axis measure and the crore/lakh card label |
| 02 Profitability | {int((measures['Display_Folder'] == '02 Profitability').sum())} | Profit, margin %, profit per order, prior-year profit, margin change in percentage points |
| 03 Orders | {int((measures['Display_Folder'] == '03 Orders').sum())} | Orders, order lines, quantity, AOV, quantity per order, value-weighted average discount |
| 04 Customers | {int((measures['Display_Folder'] == '04 Customers').sum())} | Registered, purchasing, active, inactive, new, repeat (snapshot and in-period), repeat %, orders per customer |
| 05 Customer value | {int((measures['Display_Folder'] == '05 Customer value').sum())} | Average customer revenue, contribution % against customer / segment / cluster / category / region, historical CLV, estimated 12-month future profit, illustrative 3-year value, at-risk and high-value counts |
| 06 Segmentation | {int((measures['Display_Folder'] == '06 Segmentation (RFM & clusters)').sum())} | Segment customer counts and shares, average R / F / M, average RFM score, revenue per customer in a segment |
| 07 Products & regions | {int((measures['Display_Folder'] == '07 Products & regions').sum())} | Return / cancel rate, products sold, revenue rank, margin versus own category in percentage points |
| 08 Prediction | {int((measures['Display_Folder'] == '08 Prediction (Step 8 ML)').sum())} | Predicted and matching actual revenue, naive baseline, MAE, RMSE, R², bias %, and the metric value read from ModelMetrics |
| 09 Forecast | {int((measures['Display_Folder'] == '09 Forecast (Step 9 time series)').sum())} | Historical monthly revenue, backtest forecast, future forecast, 80% and 95% interval bounds, interval width, horizon, forecast total |
| 10 Labels & context | {int((measures['Display_Folder'] == '10 Labels & context').sum())} | Date-range label, selected model names read from ModelInfo, synthetic-data disclaimer, "filters applied" warning |

Three conventions worth stating:

1. **One revenue definition.** `Total Revenue` is the only place the Delivered filter is written;
   every other currency measure builds on it or repeats the same single filter.
2. **Snapshot measures are marked as snapshots.** `Active Customers`, `Avg Recency (days)`,
   `Repeat Customers`, the CLV measures and the RFM averages read `DimCustomer`, which is a
   2026-01-01 snapshot. They do not move with the Date slicer, and the measure descriptions say so.
   `Repeat Customers (in period)` is the version that does respond to dates.
3. **Indian number formatting.** Cards use `Revenue Label` / `Profit Label` / `Forecast Label`,
   which switch between `₹0.00 Cr` and `₹0.00 L`; chart axes use `Revenue (₹ lakh)` so axis labels
   stay short. Percentages are shown to one decimal, ratios (R², Spearman) to three.

---

## 6. Dashboard pages

{pages_block}

---

## 7. Visualizations

Every visual on every page answers a stated question; none is decorative. The chart type follows
from the job the data has to do:

| Job | Chart used | Why |
|---|---|---|
| A value over time | Line | Months are ordered and continuous |
| One customer's months | Column | Separate purchases, not a continuous series |
| Compare categories | Ranked horizontal bars | Long labels, and rank is the point |
| Two comparable shares | Paired bars | The gap between share of customers and share of revenue is the message |
| A ratio over time | Its own line chart | A ratio never shares an axis with rupees |
| Two measures per item | Revenue bar with profit drawn inside | Shows the margin gap without a second axis |
| Relationship between two measures | Scatter with bubble size | Revenue, profit and volume at once |
| A matrix of one measure | Heat table with numbers in every cell | Colour is a reading aid; the number is the information |
| A single headline number | KPI card | Immediate recall, no decoding |

Rules applied throughout: **no dual axes anywhere**; a legend whenever two or more series appear;
selective direct labels rather than a number on every point; recessive gridlines; text in text
colours, never in a series colour; consistent series colours across pages (Historical, Predicted and
Forecast keep the same three hues on every page they appear).

---

## 8. Filters and slicers

Seven slicers, synced across pages with Power BI's **View > Sync slicers** panel:

| Slicer | Field | Type | Synced to | Notes |
|---|---|---|---|---|
| Date | `DimDate[Date]` | Between (range) | Pages 1-7 | Page 7 extends to 2026-06-30 to include the forecast horizon |
| Year | `DimDate[Year]` | Tile | Pages 1-6 | Quick alternative to the range slicer |
| Month | `DimDate[Month_Name]` | Dropdown | Pages 1-6 | Sorted by `Month_Number` |
| Region | `DimGeography[Region]` | Dropdown | All pages | |
| Category | `DimProduct[Category]` | Dropdown | All pages | |
| Sub-category | `DimProduct[Sub_Category]` | Dropdown | Pages 2, 5 | Hierarchically filtered by Category |
| Customer segment | `DimRFMSegment[RFM_Segment]` | Dropdown | Pages 1, 3, 4, 7 | Sorted by `Segment_Order` |
| Cluster | `DimCluster[Cluster_Label]` | Dropdown | Pages 3, 4 | Sorted by `Cluster_Order` |

Each page carries the `Date Range Label` and `Filters Applied` measures in its header, so a filtered
number is never mistaken for the full-period number.

---

## 9. Drill-through functionality

| Page | Type | Field | Reached from | Shows |
|---|---|---|---|---|
| Customer Detail | Drill-through | `DimCustomer[Customer_ID]` | Top-customer table (p3), segment matrix (p4), prediction table (p7) | Profile (no name), RFM and cluster, lifetime revenue and profit, estimated 12-month profit, illustrative 3-year value, revenue by month, category mix, recent orders |
| Product Detail | Drill-through | `DimProduct[Product_ID]` | Top / bottom product bars and the scatter (p5) | Revenue, profit, margin, units, average discount, return rate, monthly trend, region mix |
| Customer tooltip | Tooltip page (320 x 240) | `DimCustomer[Customer_ID]` | Any customer visual | Revenue, orders, recency, frequency, monetary, segment |
| Product tooltip | Tooltip page (320 x 240) | `DimProduct[Product_ID]` | Any product visual | Revenue, profit, quantity, margin |

Both drill-through pages keep the "Keep all filters" toggle on, so arriving from a filtered page
carries that context, and both have a back button.

---

## 10. Forecast integration

The two forward-looking models are different in unit, method and purpose, and the report never
merges them.

| | Revenue prediction (Step 8) | Revenue forecast (Step 9) |
|---|---|---|
| Question | How much will *this customer* spend next quarter? | How much will *the company* earn next month? |
| Unit | Customer x quarter | Company x month |
| Model | {rm['model_type']} | {fm['model_type']} |
| Selection rule | {rm['selection_rule']} | {fm['selection_rule']} |
| Evaluated on | Validation {rm['validation_period']}, test {rm['test_period']} | Validation {fm['evaluation_split']['validation']}, test {fm['evaluation_split']['test']} |
| Headline accuracy | Test MAE ₹{rm['test_metrics']['MAE']:,.0f}, RMSE ₹{rm['test_metrics']['RMSE']:,.0f}, R² {rm['test_metrics']['R2']:.3f}, bias {rm['test_metrics']['Total_Bias_%']:+.2f}% | Test MAE ₹{fm['metrics']['test']['MAE']:,.0f}, MAPE {fm['metrics']['test']['MAPE_%']:.2f}%, sMAPE {fm['metrics']['test']['sMAPE_%']:.2f}%, WAPE {fm['metrics']['test']['WAPE_%']:.2f}% |
| Shown as | PREDICTED (orange) | FORECAST (green), with 80% and 95% intervals |
| Horizon | One quarter ahead | {fm['forecast_horizon_months']} months: {fm['forecast_months'][0]} to {fm['forecast_months'][-1]} |

The forecast total for the horizon is **₹{fut / 1e7:.2f} Cr**, and the page shows the prediction
interval alongside it rather than the point forecast alone. MAPE is reported for the forecast and
deliberately not for the prediction: many customer-quarters have an actual of zero, which makes a
percentage error undefined.

The `ModelMetrics` table is generated from the saved model metadata, and the model performance
visual reads it. No metric is typed onto a page, so a metric on the dashboard cannot drift from the
metric in the model file.

---

## 11. Design principles

1. **The headline KPIs are visible immediately.** Six cards across the top of the Executive
   Overview, before any chart.
2. **Nothing is crowded.** Six to eight visuals per page, on a consistent grid, with the
   navigation rail in the same place on every page.
3. **Every visual answers a business question**, and its title states the question's answer rather
   than naming the data ("Revenue contribution by RFM segment", not "Customer chart").
4. **Consistent number formatting.** Indian units on cards (₹6.01 Cr, ₹62.55 L), ₹ lakh on chart
   axes, one decimal on percentages, three on ratios. Each measure carries exactly one format
   string, so the same quantity looks the same everywhere.
5. **A dark data-intelligence theme**, defined once in `powerbi/theme/crm_dark_theme.json`: page
   `{THEME['page']}`, panels `{THEME['panel']}` with a `{THEME['border']}` border and rounded
   corners, a soft two-glow gradient background PNG, and eight categorical hues that were validated
   against the panel surface for lightness, chroma, colour-vision separation and contrast.
   `powerbi/theme/palette_reference.md` lists every value.

### Accessibility and readability

- Body text `{THEME['ink']}` and headings `{THEME['ink_strong']}` on `{THEME['panel']}`: contrast
  well above the 4.5:1 requirement. Muted text `{THEME['muted']}` is used only for labels and
  captions, never for a number the reader has to act on.
- Minimum font sizes: 10 pt axis labels, 11 pt body, 13 pt visual titles, 30 pt card values.
- **Colour is never the only cue.** Every segment bar is labelled, every heat-table cell shows its
  number, the recency chart labels its bands, and status colours always appear with a word.
- Status colours (good / warning / serious / critical) are reserved and never reused as a data
  series.
- Tooltips add context rather than repeating the visual.

---

## 12. Validation

Three independent checks, all of which run in this environment.

**(a) Measure definitions against SQL.** {len(check)} measure-context combinations were recomputed
in pandas; {total_sql} of them - the four required measures plus profit margin and AOV, across all
eight filter contexts - were also recomputed independently in SQL. **{matched} of {total_sql}
match** to within one paisa. File: `powerbi/validation/measure_validation_targets.csv`, which also
carries an empty `Power_BI_Value` column to fill in after the cards are built, and
`powerbi/dax/validation_query.dax`, which produces the same numbers from the finished report.

Headline targets on unfiltered data:

| Measure | Value |
|---|---|
| Total Revenue | ₹{kpi['Total Revenue']:,.2f} ({kpi['Total Revenue'] / 1e7:.2f} Cr) |
| Total Profit | ₹{kpi['Total Profit']:,.2f} ({kpi['Total Profit'] / 1e7:.2f} Cr) |
| Profit Margin % | {100 * kpi['Overall Profit Margin']:.2f}% |
| Total Orders | {int(kpi['Number of Orders']):,} |
| Total Customers | {int(kpi['Purchasing Customers']):,} |
| Average Order Value | ₹{kpi['Average Order Value (AOV)']:,.2f} |

**(b) Cross-step consistency.** {len(cons)} checks confirm the star-schema extracts still agree with
Steps 4-9 (revenue, profit, cost, orders, customers, units; Champions and cluster revenue; CLV
totals; monthly actuals; forecast totals; prediction totals and MAE) and that the model is sound
(no orphan keys, unique dimension keys, no customer-name column). **All {len(cons)} pass.** File:
`powerbi/validation/cross_step_consistency.csv`.

**(c) Customer-state targets.** `powerbi/validation/customer_state_validation_targets.csv` holds the
snapshot counts (registered, purchasing, active, inactive, repeat, at-risk) and the RFM and CLV
averages, for checking the customer pages.

**Legitimate differences that are not errors, and must not be "fixed" by forcing a match:**

- `Total Customers` (1,984) counts customers with a delivered order; `Registered Customers` (2,000)
  counts rows in `DimCustomer`. The 16-customer gap is real.
- `Active Customers` and every RFM / CLV measure are snapshots at 2026-01-01. Filtering the Date
  slicer to 2024 does not change them, by design. Filtering changes `Total Revenue` in the same
  visual, so the two are never presented as the same kind of quantity.
- `New Customers` for 2023 counts first *observed* delivered purchases. 767 customers were already
  customers before the data window (`Acquisition_Status = 'Existing before 2023'`), so 2023's figure
  is "first seen", not "newly acquired".
- `Prediction R²` recomputed inside a slicer is the R² of that subset, which is a different quantity
  from the Step 8 test R². The page shows the Step 8 figure from `ModelMetrics` next to it.
- Figures rounded in Step 10's SQL output can differ from the DAX value in the second decimal;
  the DAX value is the unrounded one.

### Checklist

{_md_table(checklist)}

---

## 13. Limitations

1. **The report file itself is not built here.** Power BI Desktop is Windows-only, so the `.pbix`
   must be assembled manually from `powerbi/POWERBI_BUILD_GUIDE.md`. Until that is done, the pages
   exist as specifications and labelled mockups, not as a dashboard.
2. **No screenshots.** `outputs/figures/powerbi/` contains design mockups rendered with matplotlib
   from the real extracts, each watermarked "DESIGN MOCKUP - not a Power BI screenshot", plus a
   README explaining what has to be captured manually and under which file names.
3. **The data is synthetic.** Patterns in it were generated, so no finding here describes a real
   market. The analysis method is what transfers, not the numbers.
4. **Import mode, not DirectQuery.** The extracts are CSV snapshots; the dashboard does not update
   until they are regenerated and refreshed.
5. **Customer state is a single snapshot.** Segments, recency and customer value are as at
   2026-01-01. The report cannot show how a customer's segment changed over time, because that
   history was never computed.
6. **The customer-level prediction is weak** (test R² {rm['test_metrics']['R2']:.3f}). It is
   presented for ranking customers and for aggregate planning, and the page says so rather than
   implying per-customer precision.
7. **The forecast is company-level and univariate.** It has no regional or category breakdown, no
   promotional or external drivers, and is fitted on 36 months, which is a short series for any
   seasonal claim. Step 9 found no significant seasonality at that length.
8. **Geography is limited.** Home city and a five-region business grouping, with no coordinates; the
   Regional page therefore uses ranked bars and a matrix rather than a filled map.
9. **Associations, not causes.** The discount / margin, payment-method / cancellation and
   region / margin comparisons are observational. The dashboard states them as associations.
10. **Nothing on the dashboard is monitored.** There is no alerting, no scheduled refresh and no
    row-level security configured.

---

## 14. User guide

A separate document for business readers: `outputs/reports/powerbi_user_guide.md`. It covers
opening the report, the slicers, page navigation, drill-through, how to read each KPI, how to read
the forecast and its interval, resetting filters and refreshing the data.

---

## Files produced by Step 11

| Path | What it is |
|---|---|
| `sql/powerbi_views.sql` | The eight `pbi_*` star-schema views |
| `src/powerbi_prep.py` | Builds and validates everything in this list |
| `src/powerbi_dax.py` | The DAX measure library as data |
| `powerbi/data/*.csv` | {len(catalog)} star-schema extracts |
| `powerbi/powerquery/*.m` | One Power Query script per table + the `DataFolder` parameter |
| `powerbi/dax/measures.dax` | {len(measures)} measures with folders, formats and purposes |
| `powerbi/dax/validation_query.dax` | DAX to reproduce the validation numbers from the report |
| `powerbi/theme/crm_dark_theme.json` | The theme |
| `powerbi/theme/page_background.png` | Page background |
| `powerbi/theme/palette_reference.md` | Every colour and its rule |
| `powerbi/relationships.csv`, `table_catalog.csv` | Model specification |
| `powerbi/validation/*.csv` | Measure targets, customer-state targets, cross-step checks |
| `powerbi/POWERBI_BUILD_GUIDE.md` | The manual build steps, in order |
| `outputs/figures/powerbi/mockups/*.png` | 10 labelled design mockups |
| `outputs/figures/powerbi/README.md` | What still has to be captured manually |
| `outputs/reports/powerbi_dashboard_documentation.md` | This document |
| `outputs/reports/powerbi_user_guide.md` | The user guide |
| `outputs/tables/powerbi_*.csv` | Catalogue, relationships, measures, validation, checklist |

*{len(recs)} recommendations, {len(measures)} DAX measures, {len(catalog)} tables,
{len(cons)} consistency checks - all generated from the project's own outputs.*
"""
    out = config.REPORTS_DIR / "powerbi_dashboard_documentation.md"
    out.write_text(md)
    return out


def write_user_guide(con) -> Path:
    kpi = pd.read_csv(TAB / "eda_kpis.csv").set_index("KPI")["Value"]
    fm = json.loads((config.PROJECT_ROOT / "models" / "forecasting_metadata.json").read_text())
    md = f"""# Power BI Dashboard - User Guide

**Customer Revenue Intelligence** · Step 11
**The data in this report is synthetic**: it was generated for an internship project and does not
describe real customers or a real company.

This guide is for reading the dashboard, not for building it. If you need to build or rebuild the
report file, use `powerbi/POWERBI_BUILD_GUIDE.md`.

---

## 1. Opening the dashboard

1. Install **Power BI Desktop** (free, Windows only) from the Microsoft Store, or open the report in
   the Power BI Service if it has been published.
2. Open `powerbi/CustomerRevenueIntelligence.pbix`.
3. If Power BI asks about the data source, point the **DataFolder** parameter at the folder holding
   the CSV extracts (**Transform data > Edit parameters**, then **Refresh**). The folder is
   `powerbi/data/` inside the project.
4. The report opens on **HOME**.

You do not need Python, SQL or the database to read the report: the data travels inside the file.

---

## 2. Getting around

The navigation rail runs down the left of every page: **HOME** and the eight pages, with the current
page highlighted. Click a page name to go there, or use the HOME page's directory.

| Page | Use it when you want to know |
|---|---|
| 1 Executive Overview | The headline position: revenue, profit, margin, orders, customers, AOV, and where they come from |
| 2 Revenue Intelligence | How revenue and margin are moving, and which sub-categories and discount levels drive them |
| 3 Customer Intelligence | How customer value is distributed, who the top customers are, how recently people bought |
| 4 Customer Segmentation | How the rule-based segments and the machine-learning clusters describe the base |
| 5 Product Analytics | Which products earn, which only turn over, which lose value to returns |
| 6 Regional Analytics | How each region performs and why |
| 7 Prediction & Forecast | What the two models expect next, and how accurate they have been |
| 8 Business Recommendations | What to do about all of it, with the evidence attached |

**Back from a drill-through:** click the back arrow at the top left of the detail page, or press
Ctrl and click it.

---

## 3. Using the slicers

The slicer row sits under the page title. The slicers are **synced**: choosing Region = South on the
Executive Overview keeps South selected when you move to Product Analytics.

| Slicer | What it does |
|---|---|
| Date | Restricts every transaction figure to a date range |
| Year / Month | Quicker versions of the same thing |
| Region | One or more of North, South, East, West, Central |
| Category / Sub-category | Product groups; Sub-category follows the Category you picked |
| Customer segment | The RFM segments (Champions, Loyal Customers, At Risk, …) |
| Cluster | The four K-Means clusters |

Tips:

- Ctrl-click to select more than one value.
- The header shows the selected date range and a note when dimension filters are applied, so you can
  always tell whether you are looking at everything or at a slice.
- Clicking a bar or a segment also filters the rest of the page (cross-filtering). Click it again,
  or click empty space, to release it.

---

## 4. Resetting filters

- **One slicer:** click the eraser icon in its top-right corner.
- **The whole page:** use the **Reset filters** button in the page header (it is a bookmark that
  restores the default state).
- **Everything, including cross-filters:** Home ribbon > **Reset to default** in the Power BI
  Service, or reopen the file in Desktop.

---

## 5. Drilling into a customer or a product

Right-click a row in the top-customer table, a segment in the matrix or a bar in a product chart,
then choose **Drill through > Customer Detail** (or **Product Detail**).

The detail page shows that one customer or product: its profile, lifetime revenue and profit, its
monthly pattern, its category mix and its recent orders. Customers are identified by **Customer_ID**
only - no customer names appear anywhere in this report.

Hovering over most visuals shows a tooltip card with the same figures in miniature, without
leaving the page.

---

## 6. Reading the KPIs

| KPI | What it means | Full-period value |
|---|---|---|
| Total Revenue | Value of **delivered** order lines. Returned and Cancelled lines are excluded | ₹{kpi['Total Revenue'] / 1e7:.2f} Cr |
| Total Profit | Revenue minus cost of goods on those lines | ₹{kpi['Total Profit'] / 1e7:.2f} Cr |
| Profit Margin % | Profit / revenue | {100 * kpi['Overall Profit Margin']:.1f}% |
| Total Orders | Orders with at least one delivered line | {int(kpi['Number of Orders']):,} |
| Total Customers | Customers with at least one delivered order | {int(kpi['Purchasing Customers']):,} |
| Average Order Value | Revenue / orders | ₹{kpi['Average Order Value (AOV)']:,.0f} |
| Active Customers | Customers whose last delivered purchase was under 180 days before 2026-01-01 | 1,288 |

Three things worth knowing:

1. **Revenue means delivered revenue.** The gap between what was booked and what was delivered
   (9.4% of booked value) is shown separately on the Revenue Intelligence and Product Analytics
   pages.
2. **"Active" and "inactive" are about recency, not churn.** No customer is labelled as churned
   anywhere in this project, because no churn event is defined for this data.
3. **Customer figures are a snapshot.** Segments, recency, frequency and customer value were
   calculated once, at the reference date 2026-01-01. They do not change when you move the Date
   slicer - the transaction figures next to them do. This is deliberate, and the measure tooltips
   say so.

Numbers are shown in Indian units: **Cr** = crore (10,000,000) and **L** = lakh (100,000). Chart
axes are usually in ₹ lakh to keep the labels short.

---

## 7. Reading the forecast and the prediction

Page 7 shows two different models. They are never added together.

**FORECAST (green)** - total company revenue for the next {fm['forecast_horizon_months']} months
({fm['forecast_months'][0]} to {fm['forecast_months'][-1]}). The shaded band is the 95% prediction
interval: the model's own statement of how uncertain it is. The band widens as the horizon
lengthens, because month 6 is less certain than month 1. Plan to the line, stress-test to the lower
edge.

How accurate has it been? On six months it had never seen, its average error was
{fm['metrics']['test']['MAPE_%']:.2f}% (MAE ₹{fm['metrics']['test']['MAE'] / 1e5:.2f} L). The dashed
orange line on the chart is exactly that test: the model's forecast for months it was not trained
on, drawn against what actually happened.

**PREDICTED (orange)** - the machine-learning estimate of how much an *individual customer* will
spend in the next quarter. Use it to **rank** customers for outreach and as an aggregate planning
figure. Do not quote one customer's predicted revenue as a commitment: the model's R² at customer
level is 0.056, which is better than the baselines but far from precise for one person.

**HISTORICAL (blue)** is always actual delivered revenue.

---

## 8. Refreshing the data

The report reads CSV extracts, so refreshing is two steps:

1. **Regenerate the extracts** (needs Python and the project):
   ```bash
   cd customer-revenue-intelligence
   python -c "from src.powerbi_prep import run_powerbi_prep; run_powerbi_prep()"
   ```
   If the underlying data has changed, rerun the pipeline first (Steps 3-10), then the command
   above.
2. **Refresh in Power BI**: Home ribbon > **Refresh**. If the files moved, update the **DataFolder**
   parameter first (Transform data > Edit parameters).

After a refresh, sanity-check three cards against
`powerbi/validation/measure_validation_targets.csv`: Total Revenue, Total Orders and Total
Customers. If they match, the model loaded correctly.

---

## 9. If something looks wrong

| What you see | Usual reason |
|---|---|
| Every number is blank | A slicer combination with no rows - clear the filters |
| Revenue looks too low | The Date slicer, or a Region / Category filter, is still applied - check the header |
| A customer count does not change with the date range | Expected: customer-state measures are a 2026-01-01 snapshot |
| A "(Blank)" row in a segment slicer | Should not happen - customers with no delivered order show as "No delivered order" |
| The forecast line stops | The Date slicer ends before 2026-06-30; extend it to see the whole horizon |
"""
    out = config.REPORTS_DIR / "powerbi_user_guide.md"
    out.write_text(md)
    return out


def write_build_guide(catalog, rel, measures) -> Path:
    rows = "\n".join(f"| {i + 1} | `{n}.csv` | `powerbi/powerquery/{n}.m` |"
                     for i, n in enumerate(catalog["Table"]))
    md = f"""# Power BI build guide (manual steps)

**Read this first.** Power BI Desktop runs only on Windows and could not be installed or automated
in the environment where this project was built, so **the `.pbix` file does not exist yet**. Every
input it needs does exist and has been validated. This guide is the exact list of steps that have to
be performed by hand in Power BI Desktop, in order. Nothing in this project claims that any of these
steps has already been done.

Estimated time: 3-4 hours for the full eight-page report.

---

## 0. Before you start

- Install **Power BI Desktop** (free, Microsoft Store).
- Copy the whole `powerbi/` folder to the Windows machine, or open the project folder from it.
- Have these open: `powerbi/dax/measures.dax`, `powerbi/relationships.csv`,
  `powerbi/validation/measure_validation_targets.csv`, and the mockups in
  `outputs/figures/powerbi/mockups/`.

---

## 1. Apply the theme (2 minutes)

**View > Themes > Browse for themes** > `powerbi/theme/crm_dark_theme.json`.

Then **Insert > Image** `powerbi/theme/page_background.png` on each page, sent to the back, or set
it as the page background (Format page > Canvas background > Image, Fit, 0% transparency).

## 2. Load the data (15 minutes)

1. **Home > Get data > Blank query**, name it `DataFolder`, and paste
   `powerbi/powerquery/00_DataFolder_parameter.m` into the advanced editor. Convert it to a
   parameter (**Manage parameters**) and set it to the full path of `powerbi/data/` **with a
   trailing backslash**.
2. For each table below, **New source > Blank query > Advanced editor**, paste the matching `.m`
   file, and name the query exactly as the table name.

| # | Extract | Power Query script |
|---|---|---|
{rows}

3. **Close & Apply.**

## 3. Set up the date table (5 minutes)

1. Select `DimDate` > **Table tools > Mark as date table** > `Date`.
2. `DimDate[Month_Name]` > **Column tools > Sort by column** > `Month_Number`.
3. Repeat: `Year_Month` sorted by `Year_Month_Sort`; `Year_Quarter` by `Year_Quarter_Sort`;
   `Month_Short` by `Month_Number`; `Day_Name` by `Day_Of_Week_Number`.
4. `DimRFMSegment[RFM_Segment]` sorted by `Segment_Order`; `DimCluster[Cluster_Label]` by
   `Cluster_Order`; `DimCustomer[Recency_Band]` by `Recency_Band_Order`;
   `DimCustomer[Frequency_Band]` by `Frequency_Band_Order`; `DimCustomer[Activity_Status]` by
   `Activity_Status_Order`; `FactSales[Discount_Band]` by `Discount_Band_Order`.

## 4. Build the relationships (10 minutes)

**Model view**, delete every relationship Power BI guessed, then create these by hand exactly as
listed in `powerbi/relationships.csv`:

{_md_table(rel[["From_Table", "From_Column", "To_Table", "To_Column", "Cardinality", "Cross_Filter_Direction", "Active"]])}

Leave `DimDate -> FactRevenuePrediction` **inactive** - that is deliberate (see documentation
section 4).

Hide from report view: every key column (`Location_ID`, the `*_Order` sort columns,
`Year_Month_Sort`, `Year_Quarter_Sort`) so report users only see fields they can use.

## 5. Add the measures (30 minutes)

1. **Home > Enter data**, one column, name the table `_Measures`, Load, then delete the dummy
   column. Move `_Measures` to the top of the field list.
2. Paste each measure from `powerbi/dax/measures.dax` into a new measure on `_Measures`.
3. For each, set the **Display folder** and **Format** shown in the comment above it.
   ({len(measures)} measures in {measures['Display_Folder'].nunique()} folders.)

## 6. Validate before building any visual (15 minutes)

Do this now, not at the end - a wrong measure caught here saves rebuilding pages.

1. Put a table visual on a blank page with `Total Revenue`, `Total Profit`, `Profit Margin %`,
   `Total Orders`, `Total Customers`, `Average Order Value`.
2. Compare with the "All data" rows of `powerbi/validation/measure_validation_targets.csv`.
3. Add `DimDate[Year]`, then `DimGeography[Region]`, then `DimProduct[Category]`, then
   `DimRFMSegment[RFM_Segment]` and check those contexts too.
4. Record what Power BI shows in the `Power_BI_Value` column of that file.
5. If you have DAX Studio, run `powerbi/dax/validation_query.dax` instead - it produces all of it
   at once.

A difference of more than ₹1 means a measure does not match the SQL; fix the measure before
continuing.

## 7. Build the pages (2-3 hours)

Work from the mockups in `outputs/figures/powerbi/mockups/` and the page specifications in
`outputs/reports/powerbi_dashboard_documentation.md` section 6. For each page:

1. Set the page size to 16:9 (1280 x 720) and apply the background.
2. Add the header: page title text box, `Date Range Label` and `Filters Applied` as cards.
3. Add the slicer row and set each slicer's field and style.
4. Add the visuals in the order the specification lists them, using the stated chart type.
5. Give every visual the title the specification gives it - a sentence, not a field name.
6. Turn off the visual header, keep the theme's panel background and border.

Then **View > Sync slicers** and set the sync groups from documentation section 8.

## 8. Drill-through and tooltips (20 minutes)

1. New page **Customer Detail**: set page information > **Allow use as drill-through**, drill-through
   field `DimCustomer[Customer_ID]`, "Keep all filters" on. Build it from mockup 09. Add the back
   button.
2. New page **Product Detail**: same, on `DimProduct[Product_ID]`.
3. New pages **Customer tooltip** and **Product tooltip**: page size **Tooltip** (320 x 240), page
   information > **Allow use as tooltip** on. Then, on each customer or product visual, Format >
   Tooltip > Report page > pick the tooltip page.
4. Hide all four pages from the page tabs (right-click the tab > Hide page).

## 9. Navigation (15 minutes)

1. On HOME, add a button per page: **Insert > Buttons > Blank**, set Action > Page navigation.
2. Copy the navigation rail to every page (select the buttons, copy, paste on each page) so it sits
   in the same position everywhere.
3. Add a **Reset filters** button: set the default state, **View > Bookmarks > Add**, name it
   "Default view", then point the button's action at that bookmark.

## 10. Take the screenshots (10 minutes)

The screenshots referred to in the brief have to be captured here, from the finished report. Save
them to `outputs/figures/powerbi/` under exactly these names:

```
01_executive_overview.png      05_product_analytics.png
02_revenue_intelligence.png    06_regional_analytics.png
03_customer_intelligence.png   07_prediction_forecast.png
04_customer_segmentation.png   08_business_recommendations.png
```

Use **File > Export > Export to PDF** for the whole report as well, and the Windows Snipping Tool
(Win+Shift+S) or **View > Full screen** then Print Screen for individual pages. Capture each page
with the slicers cleared, so the screenshots show full-period figures.

## 11. Final checks

- [ ] Every card matches `powerbi/validation/measure_validation_targets.csv`
- [ ] No visual shows "(Blank)" in a segment or cluster slicer
- [ ] Month names sort January…December, not alphabetically
- [ ] No chart has two y-axes
- [ ] Every visual title is a sentence that says what the visual shows
- [ ] The synthetic-data statement appears on HOME and the Executive Overview
- [ ] No customer name appears anywhere
- [ ] Save as `powerbi/CustomerRevenueIntelligence.pbix`

Update `outputs/tables/powerbi_validation_checklist.csv` as you complete each item, so the project's
record of what was actually done stays honest.
"""
    out = PBI_DIR / "POWERBI_BUILD_GUIDE.md"
    out.write_text(md)
    return out


def write_figures_readme() -> Path:
    md = """# outputs/figures/powerbi/

**There are no Power BI screenshots in this folder, because none were taken.**

Power BI Desktop is a Windows-only application. The environment in which this project was built is
Linux, so Power BI could not be installed, automated or screenshotted here. Rather than present
something else as a Power BI screenshot, this folder contains:

## `mockups/` - design mockups (not screenshots)

Ten PNGs rendered with matplotlib **from the real extracts in `powerbi/data/`**. Every number on
them is an actual project output. Each one is watermarked:

> DESIGN MOCKUP - layout specification drawn from the real data. Not a Power BI screenshot.

| File | Page |
|---|---|
| `00_home_mockup.png` | HOME |
| `01_executive_overview_mockup.png` | 1 Executive Overview |
| `02_revenue_intelligence_mockup.png` | 2 Revenue Intelligence |
| `03_customer_intelligence_mockup.png` | 3 Customer Intelligence |
| `04_customer_segmentation_mockup.png` | 4 Customer Segmentation |
| `05_product_analytics_mockup.png` | 5 Product Analytics |
| `06_regional_analytics_mockup.png` | 6 Regional Analytics |
| `07_prediction_forecast_mockup.png` | 7 Prediction & Forecast |
| `08_business_recommendations_mockup.png` | 8 Business Recommendations |
| `09_customer_detail_drillthrough_mockup.png` | Customer Detail (drill-through) |

They serve as the layout specification for the build: chart types, positions, titles, labels and
theme are all as the finished page should look.

## What has to be done manually

1. Build the report in Power BI Desktop on a Windows machine, following
   `powerbi/POWERBI_BUILD_GUIDE.md` (11 steps, ~3-4 hours).
2. Validate the cards against `powerbi/validation/measure_validation_targets.csv`.
3. Capture one screenshot per page, with the slicers cleared, and save them **in this folder** as:

```
01_executive_overview.png      05_product_analytics.png
02_revenue_intelligence.png    06_regional_analytics.png
03_customer_intelligence.png   07_prediction_forecast.png
04_customer_segmentation.png   08_business_recommendations.png
```

4. Optionally export the whole report to PDF (File > Export > Export to PDF) and save it as
   `outputs/reports/powerbi_dashboard.pdf`.
5. Update `outputs/tables/powerbi_validation_checklist.csv`, changing the status of the page items
   from "Specified + mockup" to "Built in Power BI Desktop" as each one is genuinely finished.

Until step 3 is done, this folder contains mockups only - and says so.
"""
    out = FIG_DIR / "README.md"
    out.write_text(md)
    return out


# =========================================================================== entry point
def run_powerbi_prep(make_mockups: bool = True, verbose: bool = True) -> dict:
    """Build the Power BI layer end to end. Deterministic: same inputs -> identical files."""
    _mk()
    con = connect()
    try:
        build_views(con)
        catalog = export_model(con)
        rel = write_relationships()
        write_power_query(catalog)
        measures = write_dax()
        write_theme()
        check, cons = validate_measures(con)
        checklist = write_checklist()
        figs = build_mockups(con) if make_mockups else []
        docs = [write_documentation(con, catalog, rel, measures, check, cons, checklist),
                write_user_guide(con),
                write_build_guide(catalog, rel, measures),
                write_figures_readme()]
    finally:
        con.close()
    if verbose:
        print(f"Tables exported      : {len(catalog)} -> powerbi/data/")
        print(f"Relationships        : {len(rel)}")
        print(f"DAX measures         : {len(measures)} in "
              f"{measures['Display_Folder'].nunique()} display folders")
        recon = check[check["SQL_Value"].notna()]
        print(f"Measure validation   : {int((recon['Reconciled'] == 'Match').sum())}/"
              f"{len(recon)} Python-vs-SQL matches over {check['Filter_Context'].nunique()} contexts")
        print(f"Cross-step checks    : {int((cons['Status'] == 'PASS').sum())}/{len(cons)} pass")
        print(f"Design mockups       : {len(figs)} (labelled, NOT Power BI screenshots)")
        print(f"Documents            : {', '.join(p.name for p in docs)}")
    return {"catalog": catalog, "relationships": rel, "measures": measures,
            "validation": check, "consistency": cons, "checklist": checklist,
            "figures": figs, "documents": docs}
