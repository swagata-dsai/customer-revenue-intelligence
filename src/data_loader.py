"""STEP 12 - data and model loading for the Streamlit application.

One rule: the app never recomputes an analysis. It reads what Steps 3-11 already
produced and validated, and presents it. The only arithmetic done here is
aggregation of the fact table (sums, counts, means) so the pages can respond to
filters.

Source of truth, in order of preference:
  1. `data/customer_revenue_intelligence.db` through the Step 11 `pbi_*` star-schema
     views (created on connect from `sql/powerbi_views.sql`, so they always exist).
  2. The Step 3-7 processed CSVs, if the database is not there.

Every loader returns `None` instead of raising when its source file is missing;
the pages turn that into a readable message (see dashboard_utils.validate_dataframe).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

import config

PROC = config.PROCESSED_DIR
TABLES = config.TABLES_DIR
MODELS = config.PROJECT_ROOT / "models"
PBI_DATA = config.PROJECT_ROOT / "powerbi" / "data"
VIEWS_SQL = config.SQL_DIR / "powerbi_views.sql"

REFERENCE_DATE = "2026-01-01"          # the Step 5-7 snapshot date
DATASET_LABEL = getattr(config, "DATASET_LABEL",
                        "SYNTHETIC DATA - generated for an internship project")


# --------------------------------------------------------------------- helpers
def _db_available() -> bool:
    return config.DATABASE_FILE.exists()


@st.cache_resource(show_spinner=False)
def _connection() -> sqlite3.Connection | None:
    """Read-only-ish connection with the pbi_* views guaranteed to exist."""
    if not _db_available():
        return None
    try:
        con = sqlite3.connect(config.DATABASE_FILE, check_same_thread=False)
        if VIEWS_SQL.exists():
            con.executescript(VIEWS_SQL.read_text())
            con.commit()
        return con
    except Exception:                                             # noqa: BLE001
        return None


def _read_sql(query: str) -> pd.DataFrame | None:
    con = _connection()
    if con is None:
        return None
    try:
        return pd.read_sql_query(query, con)
    except Exception:                                             # noqa: BLE001
        return None


def _read_csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None


@st.cache_data(show_spinner=False)
def load_table(name: str, subdir: str = "") -> pd.DataFrame | None:
    """Any saved table from `outputs/tables/` (or `outputs/tables/sql/`)."""
    path = TABLES / subdir / f"{name}.csv" if subdir else TABLES / f"{name}.csv"
    return _read_csv(path)


@st.cache_data(show_spinner=False)
def load_json(path_str: str) -> dict | None:
    try:
        return json.loads(Path(path_str).read_text())
    except (OSError, json.JSONDecodeError):
        return None


# ----------------------------------------------------------------- sales fact
@st.cache_data(show_spinner="Loading transactions…")
def load_sales() -> pd.DataFrame | None:
    """Order-line fact with its dimensions joined on. All statuses, `Is_Delivered` flagged.

    Every revenue figure in the app filters `Is_Delivered == 1`, which is the
    project's revenue rule from Step 3 onwards.
    """
    df = _read_sql("""
        SELECT s.Order_Line_ID, s.Order_ID, s.Order_Date, s.Customer_ID, s.Product_ID,
               s.Payment_Method, s.Customer_Type, s.Order_Status, s.Is_Delivered,
               s.Quantity, s.Unit_Price, s.Discount, s.Discount_Band, s.Discount_Band_Order,
               s.Booked_Value, s.Sales, s.Cost, s.Profit,
               g.Region, g.State, g.City,
               p.Product_Name, p.Category, p.Sub_Category,
               c.RFM_Segment, c.Cluster_ID, c.Age_Band, c.Gender, c.Acquisition_Status,
               cl.Cluster_Label
        FROM pbi_fact_sales s
        JOIN pbi_dim_geography g ON g.Location_ID = s.Location_ID
        JOIN pbi_dim_product  p  ON p.Product_ID  = s.Product_ID
        JOIN pbi_dim_customer c  ON c.Customer_ID = s.Customer_ID
        JOIN pbi_dim_cluster  cl ON cl.Cluster_ID = c.Cluster_ID
    """)
    if df is None:                                     # fall back to the cleaned CSV
        raw = _read_csv(config.CLEAN_DATA_FILE)
        if raw is None:
            return None
        keep = ["Order_Line_ID", "Order_ID", "Order_Date", "Customer_ID", "Product_ID",
                "Payment_Method", "Customer_Type", "Order_Status", "Is_Delivered", "Quantity",
                "Unit_Price", "Discount", "Discount_Band", "Sales", "Cost", "Profit",
                "Region", "State", "City", "Product_Name", "Category", "Sub_Category",
                "Age_Band", "Gender"]
        df = raw[[c for c in keep if c in raw.columns]].copy()
        df["Booked_Value"] = (df["Quantity"] * df["Unit_Price"] * (1 - df["Discount"])).round(2)
        seg = _read_csv(PROC / "customer_ml_segments.csv")
        if seg is not None:
            df = df.merge(seg[["Customer_ID", "RFM_Segment", "Cluster_ID", "Cluster_Label",
                               "Acquisition_Status"]], on="Customer_ID", how="left")
        for col, fill in [("RFM_Segment", "No delivered order"),
                          ("Cluster_Label", "No delivered order"), ("Cluster_ID", -1)]:
            if col in df.columns:
                df[col] = df[col].fillna(fill)

    df["Order_Date"] = pd.to_datetime(df["Order_Date"])
    df["Is_Delivered"] = df["Is_Delivered"].astype(int)
    df["Year"] = df["Order_Date"].dt.year
    df["Year_Month"] = df["Order_Date"].dt.strftime("%Y-%m")
    df["Month_Start"] = df["Order_Date"].values.astype("datetime64[M]")
    df["Quarter"] = df["Order_Date"].dt.year.astype(str) + "-Q" + \
        df["Order_Date"].dt.quarter.astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_customers() -> pd.DataFrame | None:
    """One row per registered customer: RFM, cluster and customer-value snapshot.

    No customer names: the project publishes `Customer_ID` only.
    """
    df = _read_sql("""
        SELECT c.*, cl.Cluster_Label
        FROM pbi_dim_customer c
        JOIN pbi_dim_cluster cl ON cl.Cluster_ID = c.Cluster_ID
    """)
    if df is None:
        seg = _read_csv(PROC / "customer_ml_segments.csv")
        clv = _read_csv(PROC / "customer_clv.csv")
        if seg is None:
            return None
        df = seg[["Customer_ID", "Recency", "Frequency", "Monetary", "R_Score", "F_Score",
                  "M_Score", "RFM_Cell", "RFM_Score", "RFM_Segment", "Cluster_ID",
                  "Cluster_Label", "PC1", "PC2", "Acquisition_Status", "Customer_Age",
                  "Gender", "Region", "First_Purchase_Date", "Last_Purchase_Date"]].copy()
        df = df.rename(columns={"Recency": "Recency_Days", "Frequency": "Frequency_Orders",
                                "Monetary": "Monetary_Revenue", "Region": "Home_Region"})
        df["Has_Delivered_Order"] = 1
        if clv is not None:
            df = df.merge(clv.drop(columns=[c for c in ("RFM_Segment", "Cluster_ID",
                                                        "Cluster_Label", "Recency",
                                                        "Average_Order_Value")
                                            if c in clv.columns]),
                          on="Customer_ID", how="left")
    # PC1 / PC2 live in the Step 6 output, not in the star schema
    if "PC1" not in df.columns:
        seg = _read_csv(PROC / "customer_ml_segments.csv")
        if seg is not None and "PC1" in seg.columns:
            df = df.merge(seg[["Customer_ID", "PC1", "PC2", "Silhouette"]],
                          on="Customer_ID", how="left")
    return df


@st.cache_data(show_spinner=False)
def load_forecast() -> pd.DataFrame | None:
    """Step 9 monthly series: historical actuals, backtest forecasts, future forecast."""
    df = _read_sql("SELECT * FROM pbi_fact_forecast ORDER BY Year_Month, Record_Type_Order")
    if df is None:
        df = _read_csv(PROC / "revenue_forecast.csv")
        if df is None:
            return None
        df = df.rename(columns={"Month": "Year_Month", "Type": "Record_Type",
                                "Forecast": "Forecast_Revenue",
                                "Lower_80": "Lower_80", "Upper_80": "Upper_80",
                                "Lower_95": "Lower_95", "Upper_95": "Upper_95"})
        label = {"Historical actual": "Historical",
                 "Future forecast (fit on all 36 months)": "Forecast"}
        df["Series_Label"] = df["Record_Type"].map(label).fillna("Forecast (backtest)")
    df["Month_Date"] = pd.to_datetime(df["Year_Month"] + "-01") if "Month_Date" not in df.columns \
        else pd.to_datetime(df["Month_Date"])
    return df


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame | None:
    """Step 8 customer x quarter predictions on the held-out test split."""
    df = _read_csv(PBI_DATA / "FactRevenuePrediction.csv")
    if df is None:
        df = _read_csv(TABLES / "revenue_predictions.csv")
        if df is not None:
            df = df.rename(columns={"RFM_Segment": "RFM_Segment_At_Cutoff",
                                    "Cluster_Label": "Cluster_Label_At_Cutoff"})
    return df


@st.cache_data(show_spinner=False)
def load_prediction_quarters() -> pd.DataFrame | None:
    return _read_csv(TABLES / "revenue_quarterly_totals.csv")


@st.cache_data(show_spinner=False)
def load_modeling_dataset() -> pd.DataFrame | None:
    """The Step 8 customer x quarter panel - the only valid input for the what-if tool."""
    return _read_csv(PROC / "revenue_modeling_dataset.csv")


@st.cache_data(show_spinner=False)
def load_recommendations() -> pd.DataFrame | None:
    """Step 11 recommendations, each computed from a named Step 4-10 output."""
    return _read_csv(PBI_DATA / "Recommendations.csv")


@st.cache_data(show_spinner=False)
def load_model_metrics() -> pd.DataFrame | None:
    return _read_csv(PBI_DATA / "ModelMetrics.csv")


# --------------------------------------------------------------------- models
MODEL_FILES = {
    "revenue_prediction": ("revenue_prediction_model.pkl",
                           "Step 8 revenue prediction (customer x quarter)"),
    "forecasting": ("forecasting_model.pkl", "Step 9 monthly revenue forecast"),
    "kmeans": ("kmeans_customer_segmentation.pkl", "Step 6 K-Means customer segmentation"),
    "rfm_scaler": ("rfm_scaler.pkl", "Step 6 log1p + StandardScaler pipeline"),
    "pca": ("pca_rfm.pkl", "Step 6 PCA (visualisation only)"),
    "clv": ("clv_model.pkl", "Step 7 customer-value model (next-12-month profit)"),
    "clv_preprocessor": ("clv_preprocessor.pkl", "Step 7 preprocessing pipeline"),
}
METADATA_FILES = {
    "revenue_prediction": "revenue_model_metadata.json",
    "forecasting": "forecasting_metadata.json",
    "segmentation": "segmentation_model_metadata.json",
    "clv": "clv_model_metadata.json",
}


@st.cache_resource(show_spinner="Loading models…")
def load_models() -> dict:
    """Load every saved model that exists. A missing or unreadable file is reported,
    never faked, and never stops the app."""
    import joblib
    out: dict[str, dict] = {}
    for key, (fname, desc) in MODEL_FILES.items():
        path = MODELS / fname
        entry = {"file": fname, "description": desc, "object": None,
                 "status": "missing", "message": ""}
        if not path.exists():
            entry["message"] = (f"`models/{fname}` was not found. The features that need "
                                f"this model are unavailable until the step that trains it "
                                f"is re-run.")
        else:
            try:
                entry["object"] = joblib.load(path)
                entry["status"] = "loaded"
                entry["message"] = f"Loaded from `models/{fname}`."
            except Exception as exc:                              # noqa: BLE001
                entry["status"] = "error"
                entry["message"] = (f"`models/{fname}` exists but could not be loaded "
                                    f"({type(exc).__name__}). It may have been saved with a "
                                    f"different library version.")
        out[key] = entry
    return out


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    """Saved model metadata. Every metric shown in the app is read from here."""
    return {key: load_json(str(MODELS / fname)) for key, fname in METADATA_FILES.items()}


# ---------------------------------------------------------------- aggregation
def delivered(df: pd.DataFrame) -> pd.DataFrame:
    """The revenue rule, in one place: Delivered lines only."""
    return df[df["Is_Delivered"] == 1]


def kpis(df: pd.DataFrame) -> dict:
    """Headline figures for whatever slice of the fact table is passed in."""
    d = delivered(df)
    revenue = float(d["Sales"].sum())
    profit = float(d["Profit"].sum())
    orders = int(d["Order_ID"].nunique())
    customers = int(d["Customer_ID"].nunique())
    quantity = float(d["Quantity"].sum())
    booked = float(df["Booked_Value"].sum())
    months = d.groupby("Year_Month")["Sales"].sum()
    return {
        "revenue": revenue, "profit": profit, "cost": float(d["Cost"].sum()),
        "margin": (profit / revenue) if revenue else float("nan"),
        "orders": orders, "customers": customers, "quantity": quantity,
        "order_lines": int(len(d)),
        "aov": (revenue / orders) if orders else float("nan"),
        "profit_per_order": (profit / orders) if orders else float("nan"),
        "qty_per_order": (quantity / orders) if orders else float("nan"),
        "revenue_per_customer": (revenue / customers) if customers else float("nan"),
        "orders_per_customer": (orders / customers) if customers else float("nan"),
        "avg_monthly_revenue": float(months.mean()) if len(months) else float("nan"),
        "booked": booked,
        "not_realised": (1 - revenue / booked) if booked else float("nan"),
        "months": int(len(months)),
    }


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Delivered revenue / profit / orders / customers by month."""
    d = delivered(df)
    if d.empty:
        return pd.DataFrame(columns=["Year_Month", "Revenue", "Profit", "Orders",
                                     "Customers", "Margin_%"])
    g = (d.groupby("Year_Month")
           .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                Orders=("Order_ID", "nunique"), Customers=("Customer_ID", "nunique"))
           .reset_index())
    g["Margin_%"] = 100 * g["Profit"] / g["Revenue"]
    g["AOV"] = g["Revenue"] / g["Orders"]
    return g.sort_values("Year_Month")


def by_dimension(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Delivered revenue, profit, margin, orders, customers and units by any dimension."""
    d = delivered(df)
    if d.empty or dimension not in d.columns:
        return pd.DataFrame()
    g = (d.groupby(dimension)
           .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                Quantity=("Quantity", "sum"), Orders=("Order_ID", "nunique"),
                Customers=("Customer_ID", "nunique"))
           .reset_index())
    g["Margin_%"] = 100 * g["Profit"] / g["Revenue"]
    g["AOV"] = g["Revenue"] / g["Orders"]
    total = g["Revenue"].sum()
    g["Revenue_Share_%"] = 100 * g["Revenue"] / total if total else float("nan")
    return g.sort_values("Revenue", ascending=False)


def customer_rollup(df: pd.DataFrame) -> pd.DataFrame:
    """Per-customer revenue, profit and orders for the current slice."""
    d = delivered(df)
    if d.empty:
        return pd.DataFrame(columns=["Customer_ID", "Revenue", "Profit", "Orders", "Quantity"])
    return (d.groupby("Customer_ID")
              .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                   Orders=("Order_ID", "nunique"), Quantity=("Quantity", "sum"),
                   Last_Order=("Order_Date", "max"))
              .reset_index()
              .sort_values("Revenue", ascending=False))


def data_status() -> dict:
    """What the app actually managed to load - drives the header status indicator."""
    sales = load_sales()
    status = {
        "sales": sales is not None and not sales.empty,
        "customers": (load_customers() is not None),
        "forecast": (load_forecast() is not None),
        "predictions": (load_predictions() is not None),
        "recommendations": (load_recommendations() is not None),
        "database": _db_available(),
    }
    models = load_models()
    status["models_loaded"] = sum(1 for m in models.values() if m["status"] == "loaded")
    status["models_total"] = len(models)
    status["ok"] = status["sales"] and status["customers"] and status["forecast"]
    return status
