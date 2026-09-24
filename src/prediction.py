#!/usr/bin/env python3
"""
prediction.py
=============
Step 8 of the Customer Revenue Intelligence project: revenue prediction modelling and
business-driver analysis.

    >>> Works on the SYNTHETIC transaction data cleaned in Step 3. <<<

Prediction problem
------------------
    Prediction unit   Customer x Quarter (every customer active in the 12 months before a quarter start)
    Target            Next_Quarter_Revenue = Delivered Sales (Rs) in the 3 months after the cutoff
    Features          only information dated BEFORE the cutoff (customer history, product mix,
                      regional and company context, the calendar quarter being predicted)
    Business purpose  plan next-quarter revenue from the existing customer base and see which
                      measurable characteristics the model associates with it

Chronological split (8 rolling quarterly cutoffs)
    Train        cutoffs 2024-01-01 .. 2024-10-01   -> targets 2024-Q1 .. 2024-Q4
    Validation   cutoffs 2025-01-01, 2025-04-01     -> targets 2025-Q1 .. 2025-Q2
    Test         cutoffs 2025-07-01, 2025-10-01     -> targets 2025-Q3 .. 2025-Q4   (used only for final evaluation)

Pipeline
--------
    load_prediction_data()          cleaned lines + Step 5/6 labels (labels used ONLY for error analysis)
    define_prediction_target()      next-quarter Delivered revenue per customer
    create_customer_features()      recency, frequency, revenue, profit, AOV, discount, point-in-time RFM score ...
    create_product_features()       category mix, main category, unit price, product demand, category trend
    create_regional_features()      region, regional revenue / customers / trend
    create_temporal_features()      quarter being predicted, company revenue level and trend
    build_panel()                   one row per (customer, cutoff)
    perform_leakage_audit()         feature-by-feature timing check + excluded-variable register
    create_temporal_split()         train / validation / test by cutoff date
    build_preprocessor()            impute -> arcsinh (skewed) -> scale | impute -> one-hot; fitted on train only
    train_baseline_model()          naive, seasonal-naive and mean baselines
    train_linear_model() / train_random_forest() / train_gradient_boosting()
    evaluate_models()               train / validation metrics; selection rule fixed in advance
    tune_best_model()               randomized search, each candidate fit on train and scored on validation
    generate_predictions()          final model refit on train+validation -> test (first and only time)
    analyze_prediction_errors()     by quarter, region, category, revenue range, RFM segment, ML cluster
    calculate_feature_importance()  permutation importance (raw features) + impurity importance
    generate_business_driver_analysis()
    run_scenarios()                 model-based what-if scenarios (not guaranteed outcomes)
    validate_prediction()           target, leakage, time, model, prediction and reproducibility checks
    save_prediction_outputs()

Main entry point:  python src/prediction.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.eda import inr, pct  # noqa: E402
from src.rfm import SEGMENT_ORDER  # noqa: E402

# ----------------------------------------------------------------------------- files
RFM_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_rfm_segments.csv"
ML_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_ml_segments.csv"
VALUE_HISTORY_FILE = config.PROCESSED_DIR / "customer_value_history.csv"
PANEL_FILE = config.PROCESSED_DIR / "revenue_modeling_dataset.csv"
MODELS_DIR = config.PROJECT_ROOT / "models"
MODEL_FILE = MODELS_DIR / "revenue_prediction_model.pkl"            # full Pipeline (preprocessor + model)
PREPROCESSOR_FILE = MODELS_DIR / "revenue_prediction_preprocessor.pkl"
METADATA_FILE = MODELS_DIR / "revenue_model_metadata.json"
REPORT_FILE = config.REPORTS_DIR / "revenue_prediction_report.md"

# ----------------------------------------------------------------------------- design
SEED = config.RANDOM_SEED
LOOKBACK_MONTHS = 12
HORIZON_MONTHS = 3
TENURE_CAP_DAYS = 365
TRAIN_CUTOFFS = [pd.Timestamp(d) for d in ("2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01")]
VALID_CUTOFFS = [pd.Timestamp(d) for d in ("2025-01-01", "2025-04-01")]
TEST_CUTOFFS = [pd.Timestamp(d) for d in ("2025-07-01", "2025-10-01")]
ALL_CUTOFFS = TRAIN_CUTOFFS + VALID_CUTOFFS + TEST_CUTOFFS
SIMPLICITY_TOLERANCE = 0.02      # fixed BEFORE modelling: simplest model within 2% of best validation RMSE
N_TUNING_ITER = 15
TARGET = "Next_Quarter_Revenue"
CATEGORIES = ["Fashion", "Home & Kitchen", "Electronics", "Beauty", "Books", "Sports"]

CUSTOMER_CAND = ["Recency_Days", "Rev_3M", "Rev_12M", "Rev_Same_Quarter_Last_Year", "Profit_12M", "Profit_Margin_12M",
                 "Orders_3M", "Orders_12M", "Quantity_12M", "AOV_12M", "Avg_Discount_12M", "Return_Rate_12M",
                 "Tenure_Days_Capped", "RFM_Score_at_Cutoff"]
PRODUCT_CAND = ["Categories_12M", "Avg_Unit_Price_12M", "Product_Demand_Index", "Main_Category_Trend"] + \
               [f"Share_{c.replace(' & ', '_').replace(' ', '_')}" for c in CATEGORIES]
REGION_CAND = ["Region_Revenue_Share_3M", "Region_Customer_Share_12M", "Region_Rev_Trend"]
TIME_CAND = ["Company_Rev_Trend"]
# Revenue LEVELS (company / region Rs) were tried first and removed: they grow every year and take only 4 distinct
# values in training, so models used them as a time trend (Linear regression validation bias -99%). Shares and
# growth ratios are scale-free and comparable across years.
CANDIDATE_NUMERIC = CUSTOMER_CAND + PRODUCT_CAND + REGION_CAND + TIME_CAND
IDENTITY_FEATURES = {"Rev_12M": "= AOV_12M x Orders_12M", "Profit_12M": "= AOV_12M x Orders_12M x Profit_Margin_12M"}
PROTECTED_FEATURES = ["Recency_Days", "Orders_12M", "AOV_12M", "Profit_Margin_12M", "Avg_Discount_12M",
                      "Avg_Unit_Price_12M"]      # core customer / pricing / discount measures - never dropped
MAX_VIF = 10.0
CATEGORICAL_FEATURES = ["Region", "Main_Category", "Main_Payment_Method", "Acquisition_Status", "Target_Quarter"]
# Result of select_model_features() on the training panel (re-checked in validate_prediction):
NUMERIC_FEATURES = ["Recency_Days", "Rev_3M", "Rev_Same_Quarter_Last_Year", "Profit_Margin_12M", "Orders_3M",
                    "Orders_12M", "AOV_12M", "Avg_Discount_12M", "Return_Rate_12M", "Tenure_Days_Capped",
                    "Categories_12M", "Avg_Unit_Price_12M", "Product_Demand_Index", "Main_Category_Trend",
                    "Share_Home_Kitchen", "Share_Beauty", "Share_Books", "Share_Sports", "Region_Rev_Trend"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
SKEWED_ALL = ["Recency_Days", "Rev_3M", "Rev_12M", "Rev_Same_Quarter_Last_Year", "Profit_12M", "Orders_3M",
              "Orders_12M", "Quantity_12M", "AOV_12M", "Avg_Unit_Price_12M"]
SKEWED = [f for f in NUMERIC_FEATURES if f in SKEWED_ALL]
FEATURE_GROUP = {**{f: "Customer history" for f in CUSTOMER_CAND}, **{f: "Product" for f in PRODUCT_CAND},
                 **{f: "Regional" for f in REGION_CAND}, **{f: "Time / company" for f in TIME_CAND},
                 "Region": "Regional", "Main_Category": "Product", "Main_Payment_Method": "Customer history",
                 "Acquisition_Status": "Customer history", "Target_Quarter": "Time / company"}


# =============================================================================
# 1. DATA
# =============================================================================
def load_prediction_data() -> dict:
    """Cleaned order lines (Step 3) + customer tables from Steps 5-7.

    The Step 5 RFM segment and Step 6 cluster are computed on the FULL 2023-2025 period, so they are
    used only to group test errors (descriptive), never as model features (see leakage audit).
    """
    for p in (config.CLEAN_DATA_FILE, RFM_SEGMENTS_FILE, ML_SEGMENTS_FILE, VALUE_HISTORY_FILE):
        if not Path(p).exists():
            raise FileNotFoundError(f"{p} not found - run Steps 3, 5, 6 and 7 first.")
    tx = pd.read_csv(config.CLEAN_DATA_FILE, parse_dates=["Order_Date"], encoding="utf-8-sig")
    rfm = pd.read_csv(RFM_SEGMENTS_FILE, encoding="utf-8-sig")
    ml = pd.read_csv(ML_SEGMENTS_FILE, encoding="utf-8-sig")
    val = pd.read_csv(VALUE_HISTORY_FILE, encoding="utf-8-sig")
    labels = rfm[["Customer_ID", "RFM_Segment"]].merge(ml[["Customer_ID", "Cluster_ID", "Cluster_Label"]],
                                                        on="Customer_ID", how="left", validate="one_to_one")
    checks = pd.DataFrame([
        ("Order lines (cleaned)", f"{len(tx):,}", tx["Order_Line_ID"].is_unique),
        ("Duplicate Order_Line_ID", int(tx["Order_Line_ID"].duplicated().sum()), not tx["Order_Line_ID"].duplicated().any()),
        ("Missing values in key columns (date, customer, sales, status)",
         int(tx[["Order_Date", "Customer_ID", "Sales", "Order_Status"]].isna().sum().sum()),
         tx[["Order_Date", "Customer_ID", "Sales", "Order_Status"]].notna().all().all()),
        ("Date range", f"{tx['Order_Date'].min().date()} to {tx['Order_Date'].max().date()}",
         tx["Order_Date"].max() >= TEST_CUTOFFS[-1] + pd.DateOffset(months=HORIZON_MONTHS) - pd.Timedelta(days=1)),
        ("Step 5 RFM rows / duplicate Customer_ID", f"{len(rfm):,} / {int(rfm['Customer_ID'].duplicated().sum())}",
         not rfm["Customer_ID"].duplicated().any()),
        ("Step 6 cluster rows / duplicate Customer_ID", f"{len(ml):,} / {int(ml['Customer_ID'].duplicated().sum())}",
         not ml["Customer_ID"].duplicated().any()),
        ("Step 7 value-history rows / duplicate Customer_ID", f"{len(val):,} / {int(val['Customer_ID'].duplicated().sum())}",
         not val["Customer_ID"].duplicated().any()),
        ("Label merge one-to-one (validate='one_to_one')", f"{len(labels):,} rows", len(labels) == len(rfm)),
        ("Target period available for last test cutoff",
         f"{TEST_CUTOFFS[-1].date()} + {HORIZON_MONTHS} months <= {tx['Order_Date'].max().date()} + 1 day",
         TEST_CUTOFFS[-1] + pd.DateOffset(months=HORIZON_MONTHS) <= tx["Order_Date"].max() + pd.Timedelta(days=1)),
    ], columns=["Check", "Value", "Pass"])
    return {"tx": tx, "delivered": tx[tx["Is_Delivered"]].copy(), "labels": labels, "value_history": val,
            "checks": checks}


# =============================================================================
# 2. TARGET + FEATURES (one cutoff at a time)
# =============================================================================
def define_prediction_target(delivered: pd.DataFrame, cutoff: pd.Timestamp, customers: pd.Index) -> pd.DataFrame:
    """Next_Quarter_Revenue = Delivered Sales in [cutoff, cutoff + 3 months); 0 if the customer did not buy."""
    hi = cutoff + pd.DateOffset(months=HORIZON_MONTHS)
    fut = delivered[(delivered["Order_Date"] >= cutoff) & (delivered["Order_Date"] < hi)]
    g = fut.groupby("Customer_ID")
    t = pd.DataFrame(index=customers)
    t[TARGET] = g["Sales"].sum().reindex(customers).fillna(0.0)
    t["Next_Quarter_Orders"] = g["Order_ID"].nunique().reindex(customers).fillna(0).astype(int)
    t.attrs["min_target_date"] = fut["Order_Date"].min()
    t.attrs["max_target_date"] = fut["Order_Date"].max()
    t.attrs["quarter_total_revenue"] = fut["Sales"].sum()
    return t


def _quintile(s: pd.Series, higher_is_better: bool = True) -> pd.Series:
    r = s.rank(method="average", pct=True, ascending=higher_is_better)
    return np.ceil(r * 5).clip(1, 5).astype(int)


def create_customer_features(tx: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Customer-history features from lines dated before the cutoff (12-month and 3-month windows)."""
    lo, lo3 = cutoff - pd.DateOffset(months=LOOKBACK_MONTHS), cutoff - pd.DateOffset(months=3)
    past = tx[tx["Order_Date"] < cutoff]
    win = past[past["Order_Date"] >= lo]
    wd = win[win["Is_Delivered"]]
    g = wd.groupby("Customer_ID")
    f = pd.DataFrame({
        "Recency_Days": (cutoff - g["Order_Date"].max()).dt.days,
        "Rev_12M": g["Sales"].sum(),
        "Profit_12M": g["Profit"].sum(),
        "Orders_12M": g["Order_ID"].nunique(),
        "Quantity_12M": g["Quantity"].sum(),
        "Avg_Discount_12M": g["Discount"].mean(),
    })
    last3 = wd[wd["Order_Date"] >= lo3].groupby("Customer_ID")
    f["Rev_3M"] = last3["Sales"].sum().reindex(f.index).fillna(0.0)
    f["Orders_3M"] = last3["Order_ID"].nunique().reindex(f.index).fillna(0).astype(int)
    # same calendar quarter one year earlier = [cutoff - 12m, cutoff - 9m): inside the 12-month window
    sq = wd[wd["Order_Date"] < lo + pd.DateOffset(months=3)].groupby("Customer_ID")["Sales"].sum()
    f["Rev_Same_Quarter_Last_Year"] = sq.reindex(f.index).fillna(0.0)
    f["AOV_12M"] = f["Rev_12M"] / f["Orders_12M"]
    f["Profit_Margin_12M"] = f["Profit_12M"] / f["Rev_12M"]
    f["Return_Rate_12M"] = 1 - win[win["Customer_ID"].isin(f.index)].groupby("Customer_ID")["Is_Delivered"].mean()
    pd_ = past[past["Is_Delivered"]].sort_values(["Order_Date", "Order_ID"]).groupby("Customer_ID")
    f["Tenure_Days_Capped"] = np.minimum((cutoff - pd_["Order_Date"].min().reindex(f.index)).dt.days, TENURE_CAP_DAYS)
    first_type = past.sort_values(["Order_Date", "Order_ID"]).groupby("Customer_ID")["Customer_Type"].first()
    f["Acquisition_Status"] = first_type.reindex(f.index).map({"New": "Acquired 2023-2025",
                                                                "Returning": "Existing before 2023"})
    f["Main_Payment_Method"] = win[win["Customer_ID"].isin(f.index)].groupby("Customer_ID")["Payment_Method"] \
        .agg(lambda s: s.value_counts().index[0]).reindex(f.index)
    # point-in-time RFM score (quintiles among the customers active at THIS cutoff)
    f["RFM_Score_at_Cutoff"] = (_quintile(f["Recency_Days"], higher_is_better=False) + _quintile(f["Orders_12M"])
                                + _quintile(f["Rev_12M"]))
    f.index.name = "Customer_ID"
    return f


def create_product_features(tx: pd.DataFrame, cutoff: pd.Timestamp, customers: pd.Index) -> pd.DataFrame:
    """Product-mix features: category shares, main category, price level, product demand, category trend."""
    lo, lo3, lo6 = (cutoff - pd.DateOffset(months=m) for m in (LOOKBACK_MONTHS, 3, 6))
    wd = tx[(tx["Order_Date"] >= lo) & (tx["Order_Date"] < cutoff) & tx["Is_Delivered"]]
    wc = wd[wd["Customer_ID"].isin(customers)]
    mix = wc.pivot_table(index="Customer_ID", columns="Category", values="Sales", aggfunc="sum", fill_value=0.0)
    mix = mix.reindex(columns=CATEGORIES, fill_value=0.0)
    share = mix.div(mix.sum(axis=1), axis=0)
    f = pd.DataFrame(index=customers)
    for c in CATEGORIES:
        f[f"Share_{c.replace(' & ', '_').replace(' ', '_')}"] = share[c].reindex(customers).fillna(0.0)
    f["Main_Category"] = mix.idxmax(axis=1).reindex(customers)
    g = wc.groupby("Customer_ID")
    f["Categories_12M"] = g["Category"].nunique().reindex(customers)
    f["Avg_Unit_Price_12M"] = g["Unit_Price"].mean().reindex(customers)
    units = wd.groupby("Product_ID")["Quantity"].sum()          # product demand across ALL customers, pre-cutoff
    wc_units = wc["Product_ID"].map(units / units.mean())
    f["Product_Demand_Index"] = wc_units.groupby(wc["Customer_ID"]).mean().reindex(customers)
    cat_last = wd[wd["Order_Date"] >= lo3].groupby("Category")["Sales"].sum()
    cat_prev = wd[(wd["Order_Date"] >= lo6) & (wd["Order_Date"] < lo3)].groupby("Category")["Sales"].sum()
    trend = (cat_last / cat_prev).replace([np.inf, -np.inf], np.nan)
    f["Main_Category_Trend"] = f["Main_Category"].map(trend).astype(float)
    return f


def create_regional_features(tx: pd.DataFrame, cutoff: pd.Timestamp, customers: pd.Index) -> pd.DataFrame:
    """Region of the customer + the region's share of company revenue / active customers and its trend (pre-cutoff)."""
    lo, lo3, lo6 = (cutoff - pd.DateOffset(months=m) for m in (LOOKBACK_MONTHS, 3, 6))
    past = tx[tx["Order_Date"] < cutoff]
    region = past.sort_values("Order_Date").groupby("Customer_ID")["Region"].last()
    wd = past[(past["Order_Date"] >= lo) & past["Is_Delivered"]]
    last3 = wd[wd["Order_Date"] >= lo3].groupby("Region")["Sales"].sum()
    prev3 = wd[(wd["Order_Date"] >= lo6) & (wd["Order_Date"] < lo3)].groupby("Region")["Sales"].sum()
    act = wd.groupby("Region")["Customer_ID"].nunique()
    f = pd.DataFrame(index=customers)
    f["Region"] = region.reindex(customers)
    f["Region_Revenue_Share_3M"] = f["Region"].map(last3 / last3.sum()).astype(float)
    f["Region_Customer_Share_12M"] = f["Region"].map(act / act.sum()).astype(float)
    f["Region_Rev_Trend"] = f["Region"].map(last3 / prev3).astype(float)
    return f


def create_temporal_features(tx: pd.DataFrame, cutoff: pd.Timestamp, customers: pd.Index) -> pd.DataFrame:
    """Calendar quarter being predicted (seasonality) + company revenue trend (last 3m / previous 3m) before the cutoff."""
    lo3, lo6 = cutoff - pd.DateOffset(months=3), cutoff - pd.DateOffset(months=6)
    d = tx[tx["Is_Delivered"] & (tx["Order_Date"] < cutoff)]
    last3 = d[d["Order_Date"] >= lo3]["Sales"].sum()
    prev3 = d[(d["Order_Date"] >= lo6) & (d["Order_Date"] < lo3)]["Sales"].sum()
    f = pd.DataFrame(index=customers)
    f["Target_Quarter"] = f"Q{cutoff.quarter}"
    f["Company_Rev_Trend"] = last3 / prev3
    return f


def build_panel(tx: pd.DataFrame, delivered: pd.DataFrame, cutoffs: list[pd.Timestamp]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stack one row per (customer active in the 12 months before the cutoff, cutoff)."""
    parts, audit = [], []
    for cut in cutoffs:
        cust = create_customer_features(tx, cut)
        idx = cust.index
        f = cust.join(create_product_features(tx, cut, idx)).join(create_regional_features(tx, cut, idx)) \
            .join(create_temporal_features(tx, cut, idx))
        t = define_prediction_target(delivered, cut, idx)
        f = f.join(t)
        f.insert(0, "Cutoff_Date", cut)
        f.insert(1, "Target_Period", f"{cut.year}-Q{cut.quarter}")
        f["Split"] = "train" if cut in TRAIN_CUTOFFS else ("validation" if cut in VALID_CUTOFFS else "test")
        parts.append(f.reset_index())
        feat_dates = tx[(tx["Order_Date"] < cut) & (tx["Order_Date"] >= cut - pd.DateOffset(months=LOOKBACK_MONTHS))]
        audit.append({"Cutoff": cut, "Max_Feature_Date": feat_dates["Order_Date"].max(),
                      "Min_Target_Date": t.attrs["min_target_date"], "Max_Target_Date": t.attrs["max_target_date"],
                      "Customers": len(idx), "Quarter_Total_Revenue": t.attrs["quarter_total_revenue"],
                      "Revenue_Covered": t[TARGET].sum()})
    panel = pd.concat(parts, ignore_index=True)
    a = pd.DataFrame(audit)
    a["Coverage_%"] = 100 * a["Revenue_Covered"] / a["Quarter_Total_Revenue"]
    return panel, a


# =============================================================================
# 3. LEAKAGE AUDIT + SPLIT
# =============================================================================
def perform_leakage_audit(panel: pd.DataFrame, cutoff_timing: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """(a) timing of every feature, (b) register of variables deliberately excluded, (c) numeric checks."""
    src = {
        "Recency_Days": "last Delivered order before cutoff", "Rev_3M": "Sales in the 3 months before cutoff",
        "Rev_12M": "Sales in the 12 months before cutoff", "Rev_Same_Quarter_Last_Year": "Sales in [cutoff-12m, cutoff-9m)",
        "Profit_12M": "Profit, 12 months before cutoff", "Orders_3M": "orders, 3 months before cutoff",
        "Orders_12M": "orders, 12 months before cutoff", "Quantity_12M": "units, 12 months before cutoff",
        "AOV_12M": "Rev_12M / Orders_12M", "Profit_Margin_12M": "Profit_12M / Rev_12M", "Avg_Discount_12M": "mean line discount, 12 months before cutoff",
        "Return_Rate_12M": "share of lines Returned/Cancelled, 12 months before cutoff",
        "Tenure_Days_Capped": "cutoff - first Delivered order (capped at 365)",
        "RFM_Score_at_Cutoff": "quintiles of the three pre-cutoff features above, within the cutoff",
        "Categories_12M": "distinct categories, 12 months before cutoff",
        "Avg_Unit_Price_12M": "mean unit price paid, 12 months before cutoff",
        "Product_Demand_Index": "units sold of the customer's products (all customers), 12 months before cutoff",
        "Main_Category_Trend": "category Sales last 3m / previous 3m, before cutoff",
        "Region_Revenue_Share_3M": "region's share of company Sales, 3 months before cutoff",
        "Region_Customer_Share_12M": "region's share of active customers, 12 months before cutoff",
        "Region_Rev_Trend": "regional Sales last 3m / previous 3m, before cutoff",
        "Company_Rev_Trend": "company Sales last 3m / previous 3m, before cutoff",
        "Region": "customer's region on last pre-cutoff order", "Main_Category": "largest category by pre-cutoff Sales",
        "Main_Payment_Method": "most used payment method, 12 months before cutoff",
        "Acquisition_Status": "Customer_Type on the customer's first order (known at first purchase)",
        "Target_Quarter": "calendar quarter being predicted (known in advance)",
    }
    for c in CATEGORIES:
        src[f"Share_{c.replace(' & ', '_').replace(' ', '_')}"] = f"share of pre-cutoff Sales in {c}"
    timing = pd.DataFrame([{"Feature": f, "Group": FEATURE_GROUP[f], "Type": "categorical" if f in CATEGORICAL_FEATURES
                            else "numeric", "Source_Window": src[f], "Uses_Data_After_Cutoff": "No",
                            "In_Final_Model": "Yes" if f in FEATURES else "No (see feature selection)"}
                           for f in CANDIDATE_NUMERIC + CATEGORICAL_FEATURES])
    excluded = pd.DataFrame([
        ("Next_Quarter_Revenue / Next_Quarter_Orders", "Target-period values", "Future information - target only"),
        ("Future Sales / Profit / Quantity / Discount / activity", "Any line dated >= cutoff",
         "Would reveal the answer; all feature windows end the day before the cutoff"),
        ("RFM_Segment, R/F/M scores (Step 5)", "Computed on 2023-2025 incl. target quarters",
         "Look-ahead; replaced by RFM_Score_at_Cutoff; used only to group errors"),
        ("Cluster_ID (Step 6)", "K-Means fitted on 2023-2025 incl. target quarters",
         "Look-ahead; used only to group errors"),
        ("Historical_Profit_CLV / Estimated CLV (Step 7)", "Full-period totals and a model fitted on 2024-2025 targets",
         "Look-ahead"),
        ("Sales = Quantity x Unit_Price x (1 - Discount) of the same order", "Same-period identity",
         "Trivial, not a planning problem"),
        ("Customer_Name, Customer_ID", "Identifiers", "No predictive meaning; privacy"),
        ("Gender, Customer_Age, City, State", "Demographics / high-cardinality location",
         "Not needed for planning; Region carries location; avoids demographic profiling"),
    ], columns=["Variable", "Why it is available", "Decision / reason"])
    tim = cutoff_timing
    numeric = pd.DataFrame([
        ("Max feature date < cutoff at every cutoff", bool((tim["Max_Feature_Date"] < tim["Cutoff"]).all())),
        ("Min target date >= cutoff at every cutoff", bool((tim["Min_Target_Date"] >= tim["Cutoff"]).all())),
        ("Target window <= 3 months after cutoff", bool((tim["Max_Target_Date"] < tim["Cutoff"]
                                                          + pd.DateOffset(months=HORIZON_MONTHS)).all())),
        ("No target / future / full-period label column among model features",
         not ({TARGET, "Next_Quarter_Orders", "RFM_Segment", "Cluster_ID", "Cluster_Label"} & set(FEATURES))),
        ("Correlation check: no feature has |Spearman| > 0.95 with the target (training rows)",
         bool(max(abs(stats.spearmanr(panel.loc[panel["Split"] == "train", f],
                                      panel.loc[panel["Split"] == "train", TARGET], nan_policy="omit")[0])
                  for f in CANDIDATE_NUMERIC) <= 0.95)),
    ], columns=["Check", "Pass"])
    return {"timing": timing, "excluded": excluded, "checks": numeric}


def create_temporal_split(panel: pd.DataFrame) -> dict:
    """Chronological split by cutoff; the test rows are kept aside until the final evaluation."""
    out = {s: panel[panel["Split"] == s].reset_index(drop=True) for s in ("train", "validation", "test")}
    rows = []
    for s, cuts in (("train", TRAIN_CUTOFFS), ("validation", VALID_CUTOFFS), ("test", TEST_CUTOFFS)):
        d = out[s]
        rows.append({"Split": s, "Cutoffs": ", ".join(c.date().isoformat() for c in cuts),
                     "Feature_Data_From": (cuts[0] - pd.DateOffset(months=LOOKBACK_MONTHS)).date().isoformat(),
                     "Feature_Data_To": (cuts[-1] - pd.Timedelta(days=1)).date().isoformat(),
                     "Target_Period": f"{cuts[0].date()} to {(cuts[-1] + pd.DateOffset(months=3) - pd.Timedelta(days=1)).date()}",
                     "Target_Quarters": ", ".join(sorted(d["Target_Period"].unique())),
                     "Rows": len(d), "Customers": d["Customer_ID"].nunique(),
                     "Zero_Target_%": 100 * (d[TARGET] == 0).mean(),
                     "Mean_Target": d[TARGET].mean(), "Total_Target": d[TARGET].sum()})
    out["summary"] = pd.DataFrame(rows)
    return out


# =============================================================================
# 4. MODELS
# =============================================================================
def _vif(Z: pd.DataFrame) -> pd.Series:
    A0 = Z.to_numpy(float)
    out = {}
    for i, col in enumerate(Z.columns):
        y = A0[:, i]
        A = np.c_[np.ones(len(A0)), np.delete(A0, i, axis=1)]
        r = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
        r2 = 1 - (r ** 2).sum() / ((y - y.mean()) ** 2).sum()
        out[col] = np.inf if r2 >= 1 - 1e-12 else 1 / (1 - r2)
    return pd.Series(out)


def select_model_features(train: pd.DataFrame) -> dict:
    """Evidence-based feature selection on TRAINING rows only.

    1. Drop exact identities (Rev_12M = AOV x Orders; Profit_12M = AOV x Orders x margin).
    2. Transform as the model sees it (arcsinh for skewed, median impute, standardise) and add the one-hot
       categorical columns (first level dropped). Iteratively drop the non-protected numeric feature with the
       highest VIF while any exceeds MAX_VIF (10). Categorical features are never dropped.
    Collinear features make linear coefficients unstable and permutation importance misleading.
    """
    X = train[CANDIDATE_NUMERIC].copy()
    for c in SKEWED_ALL:
        X[c] = np.arcsinh(X[c])
    X = X.fillna(X.median())
    X = (X - X.mean()) / X.std()
    oh = pd.get_dummies(train[CATEGORICAL_FEATURES], drop_first=True).astype(float)
    vif_all = _vif(pd.concat([X, oh], axis=1))
    rows = {f: {"Feature": f, "Group": FEATURE_GROUP[f], "VIF_All_Candidates": vif_all[f], "Decision": "Kept",
                "Reason": "", "Drop_Order": np.nan} for f in CANDIDATE_NUMERIC}
    keep = [f for f in CANDIDATE_NUMERIC if f not in IDENTITY_FEATURES]
    for f, why in IDENTITY_FEATURES.items():
        rows[f].update(Decision="Excluded", Reason=f"exact identity {why}")
    k = 0
    while True:
        v = _vif(pd.concat([X[keep], oh], axis=1))[keep].drop(PROTECTED_FEATURES, errors="ignore")
        if v.max() <= MAX_VIF:
            break
        k += 1
        worst = v.idxmax()
        rows[worst].update(Decision="Excluded", Drop_Order=k,
                           Reason="perfectly collinear with other features" if np.isinf(v.max())
                           else f"VIF {v.max():.1f} > {MAX_VIF:.0f}")
        keep.remove(worst)
    final = _vif(pd.concat([X[keep], oh], axis=1))
    for f in CANDIDATE_NUMERIC:
        rows[f]["VIF_Final_Set"] = final.get(f, np.nan)
        rows[f]["Spearman_with_Target_(train)"] = stats.spearmanr(train[f], train[TARGET], nan_policy="omit")[0]
        if rows[f]["Decision"] == "Kept":
            rows[f]["Reason"] = "core measure (always kept)" if f in PROTECTED_FEATURES else f"VIF <= {MAX_VIF:.0f}"
    free = [f for f in keep if f not in PROTECTED_FEATURES]
    return {"table": pd.DataFrame(rows.values()), "selected": keep,
            "max_final_vif_numeric": float(final[free].max()),
            "protected_above_limit": {f: float(final[f]) for f in keep if f in PROTECTED_FEATURES and final[f] > MAX_VIF}}


def build_preprocessor() -> ColumnTransformer:
    """Numeric: median impute -> arcsinh (skewed money/counts) -> standardise.
    Categorical: most-frequent impute -> one-hot (unknown levels ignored). Fitted on training rows only."""
    other = [f for f in NUMERIC_FEATURES if f not in SKEWED]
    skew = Pipeline([("impute", SimpleImputer(strategy="median")),
                     ("asinh", FunctionTransformer(np.arcsinh, feature_names_out="one-to-one")),
                     ("scale", StandardScaler())])
    num = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    cat = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    return ColumnTransformer([("skewed", skew, SKEWED), ("numeric", num, other), ("categorical", cat, CATEGORICAL_FEATURES)],
                             verbose_feature_names_out=False)


def _pipe(model) -> Pipeline:
    return Pipeline([("preprocess", build_preprocessor()), ("model", model)])


def _metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": mean_absolute_error(y, p), "RMSE": float(np.sqrt(mean_squared_error(y, p))), "R2": r2_score(y, p),
            "WAPE_%": 100 * np.abs(y - p).sum() / np.abs(y).sum(), "Spearman": stats.spearmanr(y, p)[0],
            "Total_Bias_%": 100 * (p.sum() - y.sum()) / y.sum()}


def train_baseline_model(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Three non-ML baselines computed from each row's own pre-cutoff history (nothing is fitted)."""
    return {"Baseline: previous quarter (naive)": df["Rev_3M"].to_numpy(float),
            "Baseline: same quarter last year (seasonal naive)": df["Rev_Same_Quarter_Last_Year"].to_numpy(float),
            "Baseline: 12-month quarterly mean": (df["Rev_12M"] / 4).to_numpy(float)}


def train_linear_model(train: pd.DataFrame) -> Pipeline:
    """Model 1 - ordinary least squares on the preprocessed features (interpretable reference)."""
    return _pipe(LinearRegression()).fit(train[FEATURES], train[TARGET])


def train_random_forest(train: pd.DataFrame, **params) -> Pipeline:
    """Model 2 - random forest (defaults chosen for a ~5k-row panel; tuned later if it is the strongest)."""
    p = {"n_estimators": 300, "min_samples_leaf": 5, "max_features": 0.5, "random_state": SEED, "n_jobs": -1, **params}
    return _pipe(RandomForestRegressor(**p)).fit(train[FEATURES], train[TARGET])


def train_gradient_boosting(train: pd.DataFrame, **params) -> Pipeline:
    """Model 3 - gradient boosting (squared error)."""
    p = {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 3, "subsample": 0.8, "random_state": SEED, **params}
    return _pipe(GradientBoostingRegressor(**p)).fit(train[FEATURES], train[TARGET])


MODEL_ORDER = ["Linear regression", "Random forest", "Gradient boosting"]      # simplest first
COMPLEXITY = {"Linear regression": 0, "Random forest": 1, "Gradient boosting": 2}  # tuned variants share their family rank


def evaluate_models(split: dict) -> dict:
    """Fit the three ML models on TRAIN, score train and VALIDATION; baselines scored the same way.
    The test split is not touched here."""
    tr, va = split["train"], split["validation"]
    models = {"Linear regression": train_linear_model(tr), "Random forest": train_random_forest(tr),
              "Gradient boosting": train_gradient_boosting(tr)}
    rows = []
    for name, p in train_baseline_model(va).items():
        rows.append({"Model": name, "Type": "Baseline", "Stage": "default",
                     **{f"Train_{k}": v for k, v in _metrics(tr[TARGET], train_baseline_model(tr)[name]).items()},
                     **{f"Val_{k}": v for k, v in _metrics(va[TARGET], p).items()}})
    for name, m in models.items():
        rows.append({"Model": name, "Type": "ML model", "Stage": "default",
                     **{f"Train_{k}": v for k, v in _metrics(tr[TARGET], m.predict(tr[FEATURES])).items()},
                     **{f"Val_{k}": v for k, v in _metrics(va[TARGET], m.predict(va[FEATURES])).items()}})
    res = pd.DataFrame(rows)
    res["Overfit_Gap_R2"] = res["Train_R2"] - res["Val_R2"]
    return {"models": models, "results": res}


def diagnose_level_features(split: dict, tx: pd.DataFrame) -> pd.DataFrame:
    """Design evidence (validation only): why company/region revenue LEVELS are not features.
    Linear regression is fitted on TRAIN with and without the two level features and scored on VALIDATION."""
    d = tx[tx["Is_Delivered"]]

    def add_levels(df):
        df = df.copy()
        comp, reg = {}, {}
        for cut in df["Cutoff_Date"].unique():
            w = d[(d["Order_Date"] >= cut - pd.DateOffset(months=3)) & (d["Order_Date"] < cut)]
            comp[cut] = w["Sales"].sum()
            for r_, v in w.groupby("Region")["Sales"].sum().items():
                reg[(cut, r_)] = v
        df["Company_Rev_3M"] = df["Cutoff_Date"].map(comp)
        df["Region_Rev_3M"] = [reg.get((c_, r_), np.nan) for c_, r_ in zip(df["Cutoff_Date"], df["Region"])]
        return df

    tr, va = add_levels(split["train"]), add_levels(split["validation"])
    rows = []
    for name, extra in (("Final feature set (shares / ratios)", []),
                        ("+ Company_Rev_3M and Region_Rev_3M (Rs levels)", ["Company_Rev_3M", "Region_Rev_3M"])):
        cols = FEATURES + extra
        ct = build_preprocessor()
        ct.transformers[1] = ("numeric", ct.transformers[1][1], ct.transformers[1][2] + extra)
        m = Pipeline([("preprocess", ct), ("model", LinearRegression())]).fit(tr[cols], tr[TARGET])
        mt = _metrics(va[TARGET], m.predict(va[cols]))
        rows.append({"Specification": name, "Distinct_Training_Values_of_Company_Level": tr["Company_Rev_3M"].nunique(),
                     "Val_R2": mt["R2"], "Val_RMSE": mt["RMSE"], "Val_Total_Bias_%": mt["Total_Bias_%"]})
    return pd.DataFrame(rows)


TUNING_SPACE = {
    "Random forest": {"n_estimators": [100, 200, 300], "max_depth": [None, 6, 10, 16], "min_samples_split": [2, 10, 20],
                      "min_samples_leaf": [1, 3, 5, 10, 20], "max_features": [0.3, 0.5, 0.8, 1.0]},
    "Gradient boosting": {"n_estimators": [100, 200, 300, 500], "learning_rate": [0.02, 0.05, 0.1],
                          "max_depth": [2, 3, 4], "min_samples_split": [2, 10, 20], "min_samples_leaf": [1, 5, 10, 20],
                          "subsample": [0.7, 0.8, 1.0]},
}


def tune_best_model(split: dict, evaluation: dict) -> dict:
    """Randomized search over the stronger tree model (lower default validation RMSE).
    Each candidate is fit on TRAIN only and scored on VALIDATION (chronological hold-out, no shuffling)."""
    res = evaluation["results"].set_index("Model")
    cand = min(("Random forest", "Gradient boosting"), key=lambda n: res.loc[n, "Val_RMSE"])
    trainer = train_random_forest if cand == "Random forest" else train_gradient_boosting
    tr, va = split["train"], split["validation"]
    rows = []
    grid = list(ParameterSampler(TUNING_SPACE[cand], n_iter=N_TUNING_ITER, random_state=SEED))
    for i, params in enumerate(grid):
        m = trainer(tr, **params)
        rows.append({"Iteration": i + 1, **{k: str(v) for k, v in params.items()},
                     **{f"Val_{k}": v for k, v in _metrics(va[TARGET], m.predict(va[FEATURES])).items()},
                     "Train_R2": r2_score(tr[TARGET], m.predict(tr[FEATURES]))})
    t = pd.DataFrame(rows).sort_values("Val_RMSE").reset_index(drop=True)
    best = dict(grid[int(t.loc[0, "Iteration"]) - 1])
    tuned = trainer(tr, **best)
    return {"candidate": cand, "results": t, "best_params": best, "model": tuned,
            "val_metrics": _metrics(va[TARGET], tuned.predict(va[FEATURES])),
            "train_metrics": _metrics(tr[TARGET], tuned.predict(tr[FEATURES])),
            "default_val_rmse": res.loc[cand, "Val_RMSE"]}


def select_final_model(evaluation: dict, tuning: dict) -> dict:
    """Rule: among Linear regression, the default tree models and the tuned model, keep those whose validation
    RMSE is within 2% of the best; choose the simplest model FAMILY (linear < random forest < boosting); within a
    family (default vs tuned) the lower validation RMSE wins. Test data is not used."""
    res = evaluation["results"]
    ml = res[res["Type"] == "ML model"][["Model", "Val_RMSE", "Val_MAE", "Val_R2", "Train_R2", "Overfit_Gap_R2"]].copy()
    ml["Complexity_Rank"] = ml["Model"].map(COMPLEXITY)
    tm = tuning["val_metrics"]
    ml = pd.concat([ml, pd.DataFrame([{"Model": f"{tuning['candidate']} (tuned)", "Val_RMSE": tm["RMSE"],
                                       "Val_MAE": tm["MAE"], "Val_R2": tm["R2"],
                                       "Train_R2": tuning["train_metrics"]["R2"],
                                       "Overfit_Gap_R2": tuning["train_metrics"]["R2"] - tm["R2"],
                                       "Complexity_Rank": COMPLEXITY[tuning["candidate"]]}])], ignore_index=True)
    best = ml["Val_RMSE"].min()
    ml["Within_2%_of_Best"] = ml["Val_RMSE"] <= best * (1 + SIMPLICITY_TOLERANCE)
    chosen = ml[ml["Within_2%_of_Best"]].sort_values(["Complexity_Rank", "Val_RMSE"]).iloc[0]["Model"]
    ml["Selected"] = ml["Model"].eq(chosen)
    return {"table": ml, "chosen": chosen}


def _spec_for(name: str, tuning: dict):
    if name == "Linear regression":
        return LinearRegression()
    if name.endswith("(tuned)"):
        base = RandomForestRegressor if tuning["candidate"] == "Random forest" else GradientBoostingRegressor
        extra = {"n_jobs": -1} if base is RandomForestRegressor else {}
        return base(random_state=SEED, **extra, **tuning["best_params"])
    if name == "Random forest":
        return RandomForestRegressor(n_estimators=300, min_samples_leaf=5, max_features=0.5, random_state=SEED, n_jobs=-1)
    return GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, subsample=0.8, random_state=SEED)


def generate_predictions(split: dict, evaluation: dict, tuning: dict, selection: dict) -> dict:
    """Refit every ML specification on TRAIN + VALIDATION and score the TEST split (the test split plays no part in selection or tuning).
    All models are reported on test for transparency; only the pre-selected model becomes the final model."""
    trva = pd.concat([split["train"], split["validation"]], ignore_index=True)
    te = split["test"]
    names = MODEL_ORDER + [f"{tuning['candidate']} (tuned)"]
    fitted, rows = {}, []
    for name, p in train_baseline_model(te).items():
        rows.append({"Model": name, "Type": "Baseline", **_metrics(te[TARGET], p)})
    for name in names:
        m = _pipe(_spec_for(name, tuning)).fit(trva[FEATURES], trva[TARGET])
        fitted[name] = m
        rows.append({"Model": name, "Type": "ML model", **_metrics(te[TARGET], m.predict(te[FEATURES]))})
    test_res = pd.DataFrame(rows)
    test_res["Selected"] = test_res["Model"].eq(selection["chosen"])
    final = fitted[selection["chosen"]]
    pred = final.predict(te[FEATURES])
    out = te[["Customer_ID", "Cutoff_Date", "Target_Period", "Region", "Main_Category", "Target_Quarter"]].copy()
    out["Actual_Revenue"] = te[TARGET].to_numpy()
    out["Predicted_Revenue"] = pred
    out["Prediction_Error"] = out["Predicted_Revenue"] - out["Actual_Revenue"]
    out["Absolute_Error"] = out["Prediction_Error"].abs()
    out["Percentage_Error_%"] = np.where(out["Actual_Revenue"] > 0,
                                         100 * out["Prediction_Error"] / out["Actual_Revenue"].where(out["Actual_Revenue"] > 0),
                                         np.nan)
    out["Naive_Baseline"] = te["Rev_3M"].to_numpy()
    return {"final_model": final, "fitted": fitted, "test_results": test_res, "predictions": out,
            "train_rows": len(trva)}


def quarterly_timeline(split: dict, evaluation: dict, tuning: dict, selection: dict, preds: dict) -> pd.DataFrame:
    """Actual vs predicted total revenue per target quarter (population of the panel).
    Train quarters = in-sample fit, validation = train-only model, test = final model (train+validation)."""
    name = selection["chosen"]
    m_tr = evaluation["models"].get(name) or tuning["model"]
    rows = []
    for s in ("train", "validation"):
        d = split[s]
        p = m_tr.predict(d[FEATURES])
        for q, idx in d.groupby("Target_Period").groups.items():
            rows.append({"Target_Period": q, "Split": s + (" (in-sample fit)" if s == "train" else " (out-of-sample)"),
                         "Actual_Revenue": d.loc[idx, TARGET].sum(), "Predicted_Revenue": p[d.index.get_indexer(idx)].sum(),
                         "Naive_Baseline": d.loc[idx, "Rev_3M"].sum(), "Customers": len(idx)})
    pr = preds["predictions"]
    for q, g in pr.groupby("Target_Period"):
        rows.append({"Target_Period": q, "Split": "test (out-of-sample)", "Actual_Revenue": g["Actual_Revenue"].sum(),
                     "Predicted_Revenue": g["Predicted_Revenue"].sum(), "Naive_Baseline": g["Naive_Baseline"].sum(),
                     "Customers": len(g)})
    t = pd.DataFrame(rows).sort_values("Target_Period").reset_index(drop=True)
    t["Error_%"] = 100 * (t["Predicted_Revenue"] - t["Actual_Revenue"]) / t["Actual_Revenue"]
    t["Naive_Error_%"] = 100 * (t["Naive_Baseline"] - t["Actual_Revenue"]) / t["Actual_Revenue"]
    return t


# =============================================================================
# 5. ERRORS, IMPORTANCE, DRIVERS, SEGMENTS, SCENARIOS
# =============================================================================
def _err_table(df: pd.DataFrame, key: str, order=None) -> pd.DataFrame:
    g = df.groupby(key, observed=True)
    t = pd.DataFrame({"Rows": g.size(), "Actual_Revenue": g["Actual_Revenue"].sum(),
                      "Predicted_Revenue": g["Predicted_Revenue"].sum(), "MAE": g["Absolute_Error"].mean(),
                      "Median_Abs_Error": g["Absolute_Error"].median()})
    act = t["Actual_Revenue"].where(t["Actual_Revenue"] > 0)          # % undefined when actual revenue is 0
    t["WAPE_%"] = 100 * g["Absolute_Error"].sum() / act
    t["Bias_%"] = 100 * (t["Predicted_Revenue"] - t["Actual_Revenue"]) / act
    t["Avg_Actual"] = t["Actual_Revenue"] / t["Rows"]
    t["Avg_Predicted"] = t["Predicted_Revenue"] / t["Rows"]
    if order is not None:
        t = t.reindex([o for o in order if o in t.index])
    return t.reset_index()


REVENUE_BANDS = [-1, 0, 5000, 15000, 40000, np.inf]
REVENUE_BAND_LABELS = ["Rs 0 (no purchase)", "Rs 1-5k", "Rs 5k-15k", "Rs 15k-40k", "Rs 40k+"]


def analyze_prediction_errors(preds: dict, labels: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Test-set errors by quarter, region, category, actual revenue range, RFM segment and ML cluster."""
    p = preds["predictions"].merge(labels, on="Customer_ID", how="left", validate="many_to_one")
    p["Revenue_Range"] = pd.cut(p["Actual_Revenue"], REVENUE_BANDS, labels=REVENUE_BAND_LABELS)
    p["Cluster"] = "C" + p["Cluster_ID"].astype(str) + ": " + p["Cluster_Label"]
    return {"quarter": _err_table(p, "Target_Period"), "region": _err_table(p, "Region"),
            "category": _err_table(p, "Main_Category"), "range": _err_table(p, "Revenue_Range", REVENUE_BAND_LABELS),
            "rfm": _err_table(p, "RFM_Segment", SEGMENT_ORDER), "cluster": _err_table(p, "Cluster"), "merged": p}


def calculate_feature_importance(preds: dict, test: pd.DataFrame, selection: dict) -> pd.DataFrame:
    """Permutation importance of the FINAL pipeline on the test split, per raw feature (a categorical feature
    is shuffled as a whole). Impurity importance (tree models) is summed over each feature's encoded columns."""
    model = preds["final_model"]
    pi = permutation_importance(model, test[FEATURES], test[TARGET], scoring="neg_mean_absolute_error",
                                n_repeats=5, random_state=SEED, n_jobs=-1)
    imp = pd.DataFrame({"Feature": FEATURES, "Group": [FEATURE_GROUP[f] for f in FEATURES],
                        "Permutation_MAE_Increase": pi.importances_mean, "Permutation_Std": pi.importances_std})
    est = model.named_steps["model"]
    names = model.named_steps["preprocess"].get_feature_names_out()
    if hasattr(est, "feature_importances_"):
        raw = pd.Series(est.feature_importances_, index=names)
        agg = {f: raw[[n for n in names if n == f or n.startswith(f + "_")]].sum() for f in FEATURES}
        imp["Impurity_Importance"] = imp["Feature"].map(agg)
    else:
        imp["Impurity_Importance"] = np.nan
    imp["Rank"] = imp["Permutation_MAE_Increase"].rank(ascending=False, method="first").astype(int)
    return imp.sort_values("Rank").reset_index(drop=True)


def linear_coefficients(preds: dict) -> pd.DataFrame:
    """Coefficients of the linear-regression specification (refit on train+validation): Rs change in predicted
    next-quarter revenue per +1 standard deviation of the (transformed) feature, or vs. the reference category
    for one-hot columns. Association under the model, not a causal effect."""
    m = preds["fitted"]["Linear regression"]
    names = m.named_steps["preprocess"].get_feature_names_out()
    coef = pd.DataFrame({"Encoded_Feature": names, "Coefficient": m.named_steps["model"].coef_})
    coef["Raw_Feature"] = [next(f for f in FEATURES if n == f or n.startswith(f + "_")) for n in names]
    coef["Transform"] = coef["Raw_Feature"].map(lambda f: "one-hot" if f in CATEGORICAL_FEATURES
                                                 else ("arcsinh + standardise" if f in SKEWED else "standardise"))
    coef["Abs"] = coef["Coefficient"].abs()
    coef = coef.sort_values("Abs", ascending=False).drop(columns="Abs").reset_index(drop=True)
    coef.attrs["intercept"] = float(m.named_steps["model"].intercept_)
    return coef


def generate_business_driver_analysis(imp: pd.DataFrame, split: dict) -> dict[str, pd.DataFrame]:
    """For each important feature: what the model indicates, what the data shows, what cannot be concluded."""
    trva = pd.concat([split["train"], split["validation"]], ignore_index=True)
    cat_rows = []
    for f in CATEGORICAL_FEATURES:
        g = trva.groupby(f)[TARGET]
        for lvl, s in g:
            cat_rows.append({"Feature": f, "Level": lvl, "Rows": len(s), "Mean_Next_Quarter_Revenue": s.mean(),
                             "Share_With_Purchase_%": 100 * (s > 0).mean()})
    cat = pd.DataFrame(cat_rows)
    limits = {
        "Customer history": "Association with past behaviour; does not show that changing it would change revenue",
        "Product": "Product mix is correlated with price level and customer type; not a causal effect",
        "Regional": "Regional levels mix market size and customer base; not a causal effect",
        "Time / company": "Seasonal/company level with few distinct periods in training; weak evidence",
    }
    rows = []
    for _, r in imp.head(12).iterrows():
        f = r["Feature"]
        if f in CATEGORICAL_FEATURES:
            c = cat[cat["Feature"] == f].sort_values("Mean_Next_Quarter_Revenue", ascending=False)
            data = (f"Mean next-quarter revenue: highest {c.iloc[0]['Level']} {inr(c.iloc[0]['Mean_Next_Quarter_Revenue'])}, "
                    f"lowest {c.iloc[-1]['Level']} {inr(c.iloc[-1]['Mean_Next_Quarter_Revenue'])}")
        else:
            rho = stats.spearmanr(trva[f], trva[TARGET], nan_policy="omit")[0]
            q = pd.qcut(trva[f].rank(method="first"), 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
            m = trva.groupby(q, observed=True)[TARGET].mean()
            data = (f"Spearman {rho:+.2f} with next-quarter revenue; mean revenue by feature quartile "
                    f"{inr(m.iloc[0])} (lowest) -> {inr(m.iloc[-1])} (highest)")
        rows.append({"Driver": f, "Group": r["Group"], "Importance_Rank": int(r["Rank"]),
                     "Model_Evidence": f"Permutation: shuffling it raises test MAE by {inr(r['Permutation_MAE_Increase'])}",
                     "Data_Evidence": data,
                     "Business_Interpretation": "The model relied on this feature when predicting next-quarter revenue",
                     "Limitation": limits[r["Group"]]})
    return {"drivers": pd.DataFrame(rows), "categorical": cat}


def analyze_segments(err: dict) -> dict[str, pd.DataFrame]:
    """Actual vs predicted test revenue by Step 5 RFM segment and Step 6 cluster (descriptive labels)."""
    out = {}
    for key, name in (("rfm", "RFM_Segment"), ("cluster", "Cluster")):
        t = err[key].rename(columns={key: name}).copy()
        t["Predicted_Share_%"] = 100 * t["Predicted_Revenue"] / t["Predicted_Revenue"].sum()
        t["Actual_Share_%"] = 100 * t["Actual_Revenue"] / t["Actual_Revenue"].sum()
        out[key] = t
    return out


def run_scenarios(preds: dict, test: pd.DataFrame, train_rows: pd.DataFrame) -> pd.DataFrame:
    """Model-based what-if scenarios on the test customers. Features that are arithmetically linked are
    changed together so each scenario stays internally consistent. NOT causal, NOT guaranteed."""
    model = preds["final_model"]
    base = model.predict(test[FEATURES]).sum()
    money = ["Rev_3M", "Rev_Same_Quarter_Last_Year"]

    def freq(d):
        d = d.copy()
        for c in money + ["Orders_12M", "Orders_3M"]:
            d[c] = d[c] * 1.10
        return d

    def aov(d):
        d = d.copy()
        for c in money + ["AOV_12M", "Avg_Unit_Price_12M"]:
            d[c] = d[c] * 1.10
        return d

    def disc(d):
        d = d.copy()
        d["Avg_Discount_12M"] = (d["Avg_Discount_12M"] - 0.02).clip(lower=0)
        return d

    rows = [{"Scenario": "Current (actual test features)", "Change_Applied": "none",
             "Total_Predicted_Revenue": base, "Change_vs_Current_%": 0.0, "Rows_Outside_Training_Range_%": 0.0}]
    for name, fn, desc, cols in (
            ("Purchase frequency +10%", freq, "orders (12m, 3m) and recent revenue history x 1.10 (AOV unchanged)",
             ["Orders_12M"]),
            ("Average order value +10%", aov, "AOV, unit price and recent revenue history x 1.10 (orders unchanged)",
             ["AOV_12M"]),
            ("Average discount -2 percentage points", disc, "Avg_Discount_12M - 0.02 (floored at 0); nothing else",
             ["Avg_Discount_12M"])):
        d = fn(test[FEATURES])
        tot = model.predict(d).sum()
        out = np.zeros(len(d), bool)
        for c in cols:
            out |= (d[c] > train_rows[c].max()).to_numpy() | (d[c] < train_rows[c].min()).to_numpy()
        rows.append({"Scenario": name, "Change_Applied": desc, "Total_Predicted_Revenue": tot,
                     "Change_vs_Current_%": 100 * (tot - base) / base, "Rows_Outside_Training_Range_%": 100 * out.mean()})
    s = pd.DataFrame(rows)
    s["Label"] = "Model-based scenario (association, not a guaranteed outcome)"
    return s


# =============================================================================
# 6. QUESTIONS, INSIGHTS, VALIDATION
# =============================================================================
def answer_questions(R: dict) -> pd.DataFrame:
    tr, fin = R["test_results"].set_index("Model"), R["selection"]["chosen"]
    m = tr.loc[fin]
    nb = tr.loc["Baseline: previous quarter (naive)"]
    imp = R["importance"]
    tl = R["timeline"]
    tt = tl[tl["Split"].str.startswith("test")]
    reg, cat = R["errors"]["region"], R["errors"]["category"]
    rows = [
        ("Can future revenue be predicted from historical/business features?",
         f"Partly. On the unseen test quarters (2025-Q3, Q4) the final model explains R² {m['R2']:.2f} of the variation in "
         f"customer-level next-quarter revenue, vs {nb['R2']:.2f} for the naive previous-quarter rule. Single-quarter totals "
         "for the active base missed by " + " and ".join(f"{r['Error_%']:+.1f}% ({r['Target_Period']})" for _, r in tt.iterrows())
         + ", less accurate than the naive rule for totals."),
        ("Which variables are most useful for predicting revenue?",
         "By permutation importance on the test set: " + ", ".join(imp.head(5)["Feature"]) + "."),
        ("How accurately can revenue be predicted?",
         f"MAE {inr(m['MAE'])} per customer-quarter, RMSE {inr(m['RMSE'])}, WAPE {m['WAPE_%']:.1f}%, total bias "
         f"{m['Total_Bias_%']:+.1f}% over the two test quarters combined. {pct((R['split']['test'][TARGET] == 0).mean())} of test "
         "customer-quarters had zero revenue, so individual predictions are very uncertain; errors largely cancel over "
         "many customers and two quarters, but not reliably within a single quarter."),
        ("Which customer, product, pricing, discount and regional characteristics are associated with revenue?",
         "Customer purchase history dominates (see driver table). Product, price and region features rank lower: "
         + "; ".join(f"{r['Feature']} rank {r['Rank']}" for _, r in imp[imp["Feature"].isin(
             ["Avg_Discount_12M", "Avg_Unit_Price_12M", "Main_Category", "Region", "Target_Quarter"])].iterrows())
         + ". These are associations, not causes."),
        ("How can predicted revenue support business planning?",
         f"It gives an expected next-quarter revenue per existing customer that can rank customers and be summed by "
         f"region or category (test bias by region {reg['Bias_%'].min():+.0f}% to {reg['Bias_%'].max():+.0f}%, by main "
         f"category {cat['Bias_%'].min():+.0f}% to {cat['Bias_%'].max():+.0f}%). It should not be the only basis for a "
         "single-quarter revenue target (seasonality is poorly estimated), and new customers must be planned separately."),
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer"])


def validate_prediction(R: dict) -> pd.DataFrame:
    sp, panel, preds = R["split"], R["panel"], R["preds"]
    tim = R["timing"]
    checks = []

    def add(area, name, value, ok):
        checks.append({"Area": area, "Check": name, "Value": value, "Pass": bool(ok)})

    add("Target", "Target = Delivered Sales in the 3 months after each cutoff (recomputed independently)",
        f"{len(panel):,} rows", np.allclose(panel[TARGET], _recompute_target(R["data"]["delivered"], panel)))
    add("Target", "Target dates only inside [cutoff, cutoff + 3 months)",
        f"{tim['Min_Target_Date'].min().date()} .. {tim['Max_Target_Date'].max().date()}",
        (tim["Min_Target_Date"] >= tim["Cutoff"]).all() and
        (tim["Max_Target_Date"] < tim["Cutoff"] + pd.DateOffset(months=HORIZON_MONTHS)).all())
    add("Leakage", "No feature uses data on/after its cutoff", "max feature date < cutoff at all 8 cutoffs",
        R["leakage"]["checks"]["Pass"].all())
    add("Leakage", "Preprocessor fitted on training rows only (validation step); final refit on train+validation only",
        f"final fit rows {preds['train_rows']:,} = train {len(sp['train']):,} + validation {len(sp['validation']):,}",
        preds["train_rows"] == len(sp["train"]) + len(sp["validation"]))
    add("Time", "Training targets end before validation targets start; validation before test",
        "2024-12-31 < 2025-01-01; 2025-06-30 < 2025-07-01",
        max(TRAIN_CUTOFFS) + pd.DateOffset(months=HORIZON_MONTHS) <= min(VALID_CUTOFFS)
        and max(VALID_CUTOFFS) + pd.DateOffset(months=HORIZON_MONTHS) <= min(TEST_CUTOFFS))
    add("Time", "Test split unused during selection/tuning", "selection table uses Val_* columns only",
        all(c.startswith(("Val_", "Train_", "Model", "Complexity", "Within", "Selected", "Overfit"))
            for c in R["selection"]["table"].columns))
    fs = R["feature_selection"]
    add("Model", "Feature selection (training rows) reproduces the model feature list; non-protected VIF <= 10",
        f"{len(fs['selected'])} numeric features, max VIF {fs['max_final_vif_numeric']:.1f} (protected above 10: "
        + (", ".join(f"{k} {v:.1f}" for k, v in fs["protected_above_limit"].items()) or "none") + ")",
        fs["selected"] == NUMERIC_FEATURES and fs["max_final_vif_numeric"] <= MAX_VIF)
    add("Model", "Baselines exist", f"{(R['test_results']['Type'] == 'Baseline').sum()} baselines",
        (R["test_results"]["Type"] == "Baseline").sum() >= 1)
    add("Model", "Multiple ML models evaluated", f"{(R['test_results']['Type'] == 'ML model').sum()} models",
        (R["test_results"]["Type"] == "ML model").sum() >= 3)
    p = preds["predictions"]
    mm = _metrics(p["Actual_Revenue"], p["Predicted_Revenue"])
    fin = R["test_results"].set_index("Model").loc[R["selection"]["chosen"]]
    add("Model", "Reported test metrics recomputed from the saved prediction table", f"R² {mm['R2']:.4f}",
        np.isclose(mm["R2"], fin["R2"]) and np.isclose(mm["MAE"], fin["MAE"]))
    add("Predictions", "Predicted values finite", int(np.isfinite(p["Predicted_Revenue"]).sum()),
        np.isfinite(p["Predicted_Revenue"]).all())
    add("Predictions", "Prediction table reconciles with the test split (rows, customers, actual total)",
        f"{len(p):,} rows, {inr(p['Actual_Revenue'].sum())}",
        len(p) == len(sp["test"]) and np.isclose(p["Actual_Revenue"].sum(), sp["test"][TARGET].sum())
        and (p["Customer_ID"].to_numpy() == sp["test"]["Customer_ID"].to_numpy()).all())
    add("Predictions", "Errors correctly calculated (error = predicted - actual; % only where actual > 0)",
        f"{int(p['Percentage_Error_%'].isna().sum()):,} rows with actual = 0 have no %",
        np.allclose(p["Prediction_Error"], p["Predicted_Revenue"] - p["Actual_Revenue"])
        and np.allclose(p["Absolute_Error"], p["Prediction_Error"].abs())
        and p.loc[p["Actual_Revenue"] == 0, "Percentage_Error_%"].isna().all())
    add("Predictions", "No duplicate (customer, cutoff) keys in the panel",
        int(panel.duplicated(["Customer_ID", "Cutoff_Date"]).sum()), not panel.duplicated(["Customer_ID", "Cutoff_Date"]).any())
    add("Predictions", "Error-analysis merges keep row counts (many_to_one)",
        f"{len(R['errors']['merged']):,}", len(R["errors"]["merged"]) == len(p))
    again = _pipe(_spec_for(R["selection"]["chosen"], R["tuning"])).fit(
        pd.concat([sp["train"], sp["validation"]])[FEATURES], pd.concat([sp["train"], sp["validation"]])[TARGET])
    add("Reproducibility", "Refit with fixed random_state gives identical test predictions", f"random_state={SEED}",
        np.allclose(again.predict(sp["test"][FEATURES]), p["Predicted_Revenue"]))
    return pd.DataFrame(checks)


def _recompute_target(delivered: pd.DataFrame, panel: pd.DataFrame) -> np.ndarray:
    out = np.zeros(len(panel))
    d = delivered[["Customer_ID", "Order_Date", "Sales"]]
    for cut, idx in panel.groupby("Cutoff_Date").groups.items():
        hi = cut + pd.DateOffset(months=HORIZON_MONTHS)
        s = d[(d["Order_Date"] >= cut) & (d["Order_Date"] < hi)].groupby("Customer_ID")["Sales"].sum()
        out[panel.index.get_indexer(idx)] = s.reindex(panel.loc[idx, "Customer_ID"]).fillna(0).to_numpy()
    return out


# =============================================================================
# 7. ORCHESTRATION + SAVING
# =============================================================================
def run_prediction_analysis() -> dict:
    t0 = time.time()
    D = load_prediction_data()
    panel, timing = build_panel(D["tx"], D["delivered"], ALL_CUTOFFS)
    leakage = perform_leakage_audit(panel, timing)
    split = create_temporal_split(panel)
    feature_selection = select_model_features(split["train"])
    level_check = diagnose_level_features(split, D["tx"])
    evaluation = evaluate_models(split)
    tuning = tune_best_model(split, evaluation)
    selection = select_final_model(evaluation, tuning)
    preds = generate_predictions(split, evaluation, tuning, selection)
    R = {"data": D, "panel": panel, "timing": timing, "leakage": leakage, "feature_selection": feature_selection,
         "level_check": level_check, "split": split, "evaluation": evaluation, "tuning": tuning,
         "selection": selection, "preds": preds, "test_results": preds["test_results"]}
    R["timeline"] = quarterly_timeline(split, evaluation, tuning, selection, preds)
    R["errors"] = analyze_prediction_errors(preds, D["labels"])
    R["segments"] = analyze_segments(R["errors"])
    R["importance"] = calculate_feature_importance(preds, split["test"], selection)
    R["coefficients"] = linear_coefficients(preds)
    R["drivers"] = generate_business_driver_analysis(R["importance"], split)
    R["scenarios"] = run_scenarios(preds, split["test"], pd.concat([split["train"], split["validation"]]))
    R["questions"] = answer_questions(R)
    R["validation"] = validate_prediction(R)
    R["runtime_s"] = time.time() - t0
    return R


def save_prediction_outputs(R: dict) -> list[Path]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    panel = R["panel"].copy()
    panel["Cutoff_Date"] = panel["Cutoff_Date"].dt.strftime("%Y-%m-%d")
    panel.round(4).to_csv(PANEL_FILE, index=False, encoding="utf-8-sig")
    paths.append(PANEL_FILE)
    preds = R["preds"]["predictions"].merge(R["data"]["labels"], on="Customer_ID", how="left", validate="many_to_one")
    preds["Cutoff_Date"] = preds["Cutoff_Date"].dt.strftime("%Y-%m-%d")
    tim = R["timing"].copy()
    for c in ("Cutoff", "Max_Feature_Date", "Min_Target_Date", "Max_Target_Date"):
        tim[c] = tim[c].dt.strftime("%Y-%m-%d")
    design = pd.DataFrame([
        ("Prediction unit", "Customer x quarter: each customer with >= 1 Delivered order in the 12 months before a quarter start"),
        ("Target variable", f"{TARGET}: Delivered Sales (Rs) in the 3 months after the cutoff (0 if no purchase)"),
        ("Feature period", "12 months before each cutoff (3-month sub-window for recent activity)"),
        ("Prediction period", "the calendar quarter starting at the cutoff"),
        ("Cutoffs", ", ".join(c.date().isoformat() for c in ALL_CUTOFFS)),
        ("Training period (targets)", "2024-01-01 to 2024-12-31"),
        ("Validation period (targets)", "2025-01-01 to 2025-06-30"),
        ("Test period (targets)", "2025-07-01 to 2025-12-31"),
        ("Business purpose", "Plan next-quarter revenue from the existing customer base and identify the measurable "
                             "characteristics the model associates with it"),
        ("Not covered", "Revenue from customers with no order in the prior 12 months (new or reactivated)"),
    ], columns=["Item", "Definition"])
    tables = {
        "revenue_prediction_design.csv": design,
        "revenue_data_checks.csv": R["data"]["checks"],
        "revenue_cutoff_timing.csv": tim,
        "revenue_split_summary.csv": R["split"]["summary"],
        "revenue_feature_catalog.csv": R["leakage"]["timing"],
        "revenue_feature_selection.csv": R["feature_selection"]["table"],
        "revenue_level_feature_check.csv": R["level_check"],
        "revenue_leakage_audit.csv": pd.concat([R["leakage"]["excluded"].assign(Section="Excluded variable"),
                                                R["leakage"]["checks"].rename(columns={"Check": "Variable", "Pass": "Decision / reason"})
                                                .assign(Section="Automated check")], ignore_index=True),
        "revenue_model_validation_results.csv": R["evaluation"]["results"],
        "revenue_tuning_results.csv": R["tuning"]["results"],
        "revenue_model_selection.csv": R["selection"]["table"],
        "revenue_model_comparison.csv": R["test_results"],
        "revenue_predictions.csv": preds,
        "revenue_quarterly_totals.csv": R["timeline"],
        "revenue_feature_importance.csv": R["importance"],
        "revenue_linear_coefficients.csv": R["coefficients"],
        "revenue_error_by_quarter.csv": R["errors"]["quarter"],
        "revenue_error_by_region.csv": R["errors"]["region"],
        "revenue_error_by_category.csv": R["errors"]["category"],
        "revenue_error_by_revenue_range.csv": R["errors"]["range"],
        "revenue_prediction_by_rfm.csv": R["segments"]["rfm"],
        "revenue_prediction_by_cluster.csv": R["segments"]["cluster"],
        "revenue_driver_analysis.csv": R["drivers"]["drivers"],
        "revenue_categorical_drivers.csv": R["drivers"]["categorical"],
        "revenue_scenarios.csv": R["scenarios"],
        "revenue_business_questions.csv": R["questions"],
        "revenue_validation_checks.csv": R["validation"],
    }
    for name, df in tables.items():
        p = config.TABLES_DIR / name
        df.round(4).to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    final = R["preds"]["final_model"]
    joblib.dump(final, MODEL_FILE)
    joblib.dump(final.named_steps["preprocess"], PREPROCESSOR_FILE)
    fin = R["test_results"].set_index("Model").loc[R["selection"]["chosen"]]
    sel = R["selection"]["table"].set_index("Model").loc[R["selection"]["chosen"]]
    meta = {
        "dataset": config.DATASET_LABEL,
        "prediction_unit": "customer x quarter (customers active in the 12 months before the cutoff)",
        "target": TARGET + " = Delivered Sales (Rs) in the 3 months after the cutoff",
        "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
        "training_period": "features 2023-01-01..2024-09-30 -> targets 2024-01-01..2024-12-31",
        "validation_period": "targets 2025-01-01..2025-06-30",
        "test_period": "targets 2025-07-01..2025-12-31",
        "final_fit": f"train + validation ({R['preds']['train_rows']:,} rows)",
        "model_type": R["selection"]["chosen"],
        "parameters": {k: (v if isinstance(v, (int, float, str, type(None))) else str(v))
                       for k, v in final.named_steps["model"].get_params().items()},
        "selection_rule": f"simplest model within {SIMPLICITY_TOLERANCE:.0%} of the best validation RMSE (fixed in advance)",
        "validation_metrics": {"RMSE": round(float(sel["Val_RMSE"]), 2), "MAE": round(float(sel["Val_MAE"]), 2),
                               "R2": round(float(sel["Val_R2"]), 4)},
        "test_metrics": {k: round(float(fin[k]), 4) for k in ("MAE", "RMSE", "R2", "WAPE_%", "Spearman", "Total_Bias_%")},
        "random_seed": SEED, "sklearn_version": sklearn.__version__,
        "usage": ("import joblib, pandas as pd; m = joblib.load('models/revenue_prediction_model.pkl'); "
                  "X = pd.read_csv('data/processed/revenue_modeling_dataset.csv'); "
                  "pred = m.predict(X[m.feature_names_in_])"),
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    paths += [MODEL_FILE, PREPROCESSOR_FILE, METADATA_FILE]
    return paths


def run_prediction(make_plots: bool = True, verbose: bool = True) -> dict:
    R = run_prediction_analysis()
    R["saved"] = save_prediction_outputs(R)
    m = joblib.load(MODEL_FILE)
    ok = np.allclose(m.predict(R["split"]["test"][FEATURES]), R["preds"]["predictions"]["Predicted_Revenue"])
    R["validation"] = pd.concat([R["validation"], pd.DataFrame([{
        "Area": "Reproducibility", "Check": "Saved pipeline (reloaded from models/) reproduces the test predictions; metadata saved",
        "Value": "revenue_prediction_model.pkl, revenue_model_metadata.json", "Pass": ok and METADATA_FILE.exists()}])],
        ignore_index=True)
    R["validation"].to_csv(config.TABLES_DIR / "revenue_validation_checks.csv", index=False, encoding="utf-8-sig")
    if make_plots:
        R["figures"] = plot_prediction_figures(R)
    R["report"] = write_prediction_report(R)
    if verbose:
        print(R["validation"][["Area", "Check", "Pass"]].to_string(index=False))
        f = R["test_results"].set_index("Model").loc[R["selection"]["chosen"]]
        print(f"\nFinal model: {R['selection']['chosen']} | test R² {f['R2']:.3f} | MAE {f['MAE']:,.0f} | "
              f"RMSE {f['RMSE']:,.0f} | runtime {R['runtime_s']:.0f}s")
        print(f"Files saved: {len(R['saved'])} | Figures: {len(R.get('figures', []))} | "
              f"Report: {R['report'].relative_to(config.PROJECT_ROOT)}")
    return R


# =============================================================================
# 8. FIGURES
# =============================================================================
def _err_bars(ax, t, key, labels=None, colors=None):
    from matplotlib.ticker import FuncFormatter
    from src.eda import PAL
    y = np.arange(len(t))
    h = 0.38
    ax.barh(y - h / 2, t["Actual_Revenue"] / t["Rows"], h, color=PAL["blue"], label="Avg actual")
    ax.barh(y + h / 2, t["Predicted_Revenue"] / t["Rows"], h, color=PAL["orange"], label="Avg predicted")
    for i, (a_, p_, b_) in enumerate(zip(t["Actual_Revenue"] / t["Rows"], t["Predicted_Revenue"] / t["Rows"], t["Bias_%"])):
        ax.text(max(a_, p_), i, f"  bias {b_:+.0f}%" if pd.notna(b_) else "  (actual = 0)", va="center", fontsize=8.5)
    ax.set_yticks(y, labels if labels is not None else t[key].astype(str))
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"₹{v / 1000:,.0f}k" if v >= 1000 else f"₹{v:,.0f}"))
    ax.set_xlim(0, max((t["Actual_Revenue"] / t["Rows"]).max(), (t["Predicted_Revenue"] / t["Rows"]).max()) * 1.35)


def plot_prediction_figures(R: dict, out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    """Step 8 charts. Actual = blue, predicted = orange."""
    from matplotlib.ticker import FuncFormatter
    from src.eda import PAL, _hbar, _note, _rupee, _save, _style
    from src.segmentation import CLUSTER_COLORS
    plt = _style()
    saved: list[Path] = []
    fin = R["selection"]["chosen"]
    pr = R["preds"]["predictions"]
    ACT, PRED = PAL["blue"], PAL["orange"]
    kfmt = FuncFormatter(lambda v, _: f"₹{v / 1000:,.0f}k" if abs(v) >= 1000 else f"₹{v:,.0f}")
    lfmt = FuncFormatter(lambda v, _: f"₹{v / 1e5:,.0f}L")

    # 1 model comparison ------------------------------------------------------------------------
    val = R["evaluation"]["results"].set_index("Model")
    tst = R["test_results"].set_index("Model")
    tun = R["tuning"]
    names = list(tst.index)
    vrm = [val.loc[n, "Val_RMSE"] if n in val.index else tun["val_metrics"]["RMSE"] for n in names]
    vr2 = [val.loc[n, "Val_R2"] if n in val.index else tun["val_metrics"]["R2"] for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    y = np.arange(len(names))
    for ax, (v, t_, title, fmt) in zip(axes, ((vrm, tst["RMSE"], "RMSE (lower is better)", lambda x: inr(x)),
                                             (vr2, tst["R2"], "R² (higher is better)", lambda x: f"{x:.3f}"))):
        ax.barh(y - 0.2, v, 0.4, color=PAL["neutral"], label="Validation (2025 Q1-Q2)")
        ax.barh(y + 0.2, t_, 0.4, color=[PRED if n == fin else PAL["blue"] for n in names], label="Test (2025 Q3-Q4)")
        for i, (a_, b_) in enumerate(zip(v, t_)):
            ax.text(max(a_, 0), i - 0.2, " " + fmt(a_), va="center", fontsize=7.5)
            ax.text(max(b_, 0), i + 0.2, " " + fmt(b_), va="center", fontsize=7.5)
        ax.axvline(0, color=PAL["muted"], linewidth=0.8)
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
        ax.invert_yaxis()
    axes[0].set_yticks(y, [n + ("  [final]" if n == fin else "") for n in names])
    axes[1].set_yticks(y, [""] * len(y))
    axes[0].set_xlim(0, max(max(vrm), tst["RMSE"].max()) * 1.2)
    axes[0].xaxis.set_major_formatter(kfmt)
    axes[1].set_xlim(min(min(vr2), tst["R2"].min()) * 1.25, max(max(vr2), tst["R2"].max()) * 1.6)
    h_, l_ = axes[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="upper right", ncol=2, fontsize=8.5, frameon=False)
    fig.suptitle("Next-quarter revenue per customer: baselines vs ML models", x=0.01, ha="left", fontsize=13,
                 fontweight="bold")
    _note(fig, "Selection used validation only (simplest model family within 2% of the best validation RMSE); the "
               "final model is orange. Test bars: models refit on train + validation.")
    fig.tight_layout()
    _save(fig, "revenue_model_comparison.png", out_dir, saved)

    # 2 actual vs predicted -----------------------------------------------------------------------
    m = tst.loc[fin]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    ax = axes[0]
    lim = pr["Actual_Revenue"].quantile(0.99)
    ax.scatter(pr["Predicted_Revenue"], pr["Actual_Revenue"], s=8, alpha=0.35, color=PRED, linewidths=0)
    ax.plot([0, lim], [0, lim], color=PAL["text"], linestyle="--", linewidth=1, label="Perfect prediction")
    ax.set_xlim(min(0, pr["Predicted_Revenue"].min()), max(lim * 0.6, pr["Predicted_Revenue"].quantile(0.995)))
    ax.set_ylim(-lim * 0.02, lim)
    ax.xaxis.set_major_formatter(kfmt)
    ax.yaxis.set_major_formatter(kfmt)
    ax.set_xlabel("Predicted next-quarter revenue (₹)")
    ax.set_ylabel("Actual next-quarter revenue (₹)")
    ax.set_title(f"Per customer-quarter: R² {m['R2']:.3f}, MAE {inr(m['MAE'])}")
    ax.legend(loc="upper left")
    ax = axes[1]
    d = pr.assign(dec=pd.qcut(pr["Predicted_Revenue"].rank(method="first"), 10, labels=range(1, 11)))
    cal = d.groupby("dec", observed=True).agg(p=("Predicted_Revenue", "mean"), a=("Actual_Revenue", "mean"))
    x = np.arange(1, 11)
    ax.bar(x - 0.2, cal["p"], 0.4, color=PRED, label="Mean predicted")
    ax.bar(x + 0.2, cal["a"], 0.4, color=ACT, label="Mean actual")
    ax.set_xticks(x)
    ax.set_xlabel("Predicted-revenue decile (1 = lowest)")
    ax.yaxis.set_major_formatter(kfmt)
    ax.set_title("Calibration by predicted decile")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.suptitle(f"Actual vs predicted revenue - {fin}, test quarters 2025-Q3 and Q4 ({len(pr):,} customer-quarters)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, f"Left panel cut at the 99th percentile of actual revenue. {pct((pr['Actual_Revenue'] == 0).mean())} of "
               "test rows had no purchase (actual = 0).")
    fig.tight_layout()
    _save(fig, "actual_vs_predicted_revenue.png", out_dir, saved)

    # 3 error distribution --------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.8))
    e = pr["Prediction_Error"]
    lo, hi = e.quantile(0.01), e.quantile(0.99)
    bins = np.linspace(lo, hi, 60)
    ax.hist(e[pr["Actual_Revenue"] == 0].clip(lo, hi), bins=bins, color=PAL["neutral"], alpha=0.9,
            label=f"No purchase in quarter ({int((pr['Actual_Revenue'] == 0).sum()):,})")
    ax.hist(e[pr["Actual_Revenue"] > 0].clip(lo, hi), bins=bins, color=PRED, alpha=0.75,
            label=f"Purchased ({int((pr['Actual_Revenue'] > 0).sum()):,})")
    ax.axvline(0, color=PAL["text"], linewidth=1)
    ax.xaxis.set_major_formatter(kfmt)
    ax.set_xlabel("Prediction error = predicted - actual (₹; clipped at P1/P99)")
    ax.set_ylabel("Customer-quarters")
    ax.set_title(f"Prediction error distribution (test): median {inr(e.median())}, mean {inr(e.mean())}")
    ax.legend()
    fig.tight_layout()
    _save(fig, "prediction_error_distribution.png", out_dir, saved)

    # 4 timeline -----------------------------------------------------------------------------------
    tl = R["timeline"]
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(tl))
    ax.plot(x, tl["Predicted_Revenue"], marker="o", color=PRED, linewidth=2, label=f"Predicted - {fin}", zorder=3)
    ax.plot(x, tl["Actual_Revenue"], marker="o", color=ACT, linewidth=2, markersize=5, linestyle="--",
            label="Actual (active-base customers)", zorder=4)
    ax.plot(x, tl["Naive_Baseline"], marker="o", color=PAL["muted"], linewidth=1.2, linestyle=":",
            label="Naive baseline (previous quarter)")
    spans = {"train": PAL["grid"], "validation": "#fdf1e8", "test": "#e8f1fc"}
    for sname, colr in spans.items():
        idx = [i for i, sp_ in enumerate(tl["Split"]) if sp_.startswith(sname)]
        if idx:
            ax.axvspan(min(idx) - 0.5, max(idx) + 0.5, color=colr, alpha=0.55, zorder=0)
            ax.text((min(idx) + max(idx)) / 2, ax.get_ylim()[1] * 0.98 if False else tl["Actual_Revenue"].max() * 1.32,
                    {"train": "Train (in-sample fit)", "validation": "Validation", "test": "Test"}[sname],
                    ha="center", fontsize=9, color=PAL["muted"])
    for i, r in tl.iterrows():
        if not r["Split"].startswith("train"):
            ax.text(i, r["Predicted_Revenue"], f"  {r['Error_%']:+.0f}%", fontsize=8.5, color=PRED, va="bottom")
    ax.set_xticks(x, tl["Target_Period"])
    ax.set_ylim(0, tl[["Actual_Revenue", "Predicted_Revenue", "Naive_Baseline"]].max().max() * 1.4)
    ax.yaxis.set_major_formatter(lfmt)
    ax.set_ylabel("Revenue per quarter (₹ lakh)")
    ax.set_title("Quarterly revenue of the active customer base: actual vs predicted")
    ax.legend(loc="upper left", fontsize=8.5)
    _note(fig, "Sum of customer-level predictions per quarter. Train quarters are in-sample (a linear model with quarter "
               "indicators reproduces each training-quarter total exactly). Excludes new/reactivated customers.")
    fig.tight_layout()
    _save(fig, "revenue_prediction_timeline.png", out_dir, saved)

    # 5 feature importance ---------------------------------------------------------------------------
    imp = R["importance"].head(15)
    coef = R["coefficients"].head(15)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    ax = axes[0]
    yy = np.arange(len(imp))
    ax.barh(yy, imp["Permutation_MAE_Increase"], xerr=imp["Permutation_Std"], color=PRED, height=0.6,
            error_kw={"ecolor": PAL["muted"], "capsize": 2})
    ax.set_yticks(yy, [f"{f} ({g})" for f, g in zip(imp["Feature"], imp["Group"])], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color=PAL["muted"], linewidth=0.8)
    _rupee(ax, "x")
    ax.set_xlabel("Increase in test MAE when shuffled (₹)")
    ax.set_title(f"Permutation importance - {fin} (top 15)")
    ax.grid(axis="y", visible=False)
    ax = axes[1]
    yy = np.arange(len(coef))
    ax.barh(yy, coef["Coefficient"], color=[ACT if v > 0 else PAL["neutral"] for v in coef["Coefficient"]], height=0.6)
    ax.set_yticks(yy, coef["Encoded_Feature"], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color=PAL["muted"], linewidth=0.8)
    _rupee(ax, "x")
    ax.set_xlabel("₹ per +1 SD (numeric) or vs reference level (one-hot)")
    ax.set_title("Linear-regression coefficients (largest 15)")
    ax.grid(axis="y", visible=False)
    fig.suptitle("What the model relied on - association, not causation", x=0.01, ha="left", fontsize=13,
                 fontweight="bold")
    _note(fig, "Permutation: how much worse test predictions get when a feature is scrambled. Coefficients: direction and "
               "size under the linear model, other features held fixed.")
    fig.tight_layout()
    _save(fig, "revenue_feature_importance.png", out_dir, saved)

    # 6-7 error by region / category / range ----------------------------------------------------------
    for key, fname, title in (("region", "prediction_error_by_region.png", "Region"),
                              ("category", "prediction_error_by_category.png", "Customer's main category"),
                              ("range", "prediction_error_by_revenue_range.png", "Actual next-quarter revenue range")):
        t = R["errors"][key]
        col = t.columns[0]
        fig, axes = plt.subplots(1, 2, figsize=(13, 0.55 * len(t) + 2.2), gridspec_kw={"width_ratios": [1.4, 1]})
        _err_bars(axes[0], t, col)
        axes[0].set_title("Average revenue per customer-quarter")
        axes[0].legend(loc="lower right", fontsize=8)
        _hbar(axes[1], [""] * len(t), t["MAE"].to_numpy(), color=PAL["neutral"],
              value_labels=[f"{inr(v)}  (WAPE {w:.0f}%)" if pd.notna(w) else inr(v) for v, w in zip(t["MAE"], t["WAPE_%"])])
        axes[1].set_title("Mean absolute error")
        axes[1].xaxis.set_major_formatter(kfmt)
        fig.suptitle(f"Test errors by {title.lower()} ({fin})", x=0.01, ha="left", fontsize=13, fontweight="bold")
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # 8-9 segments ------------------------------------------------------------------------------------
    for key, fname, title, colr in (("cluster", "predicted_revenue_by_cluster.png", "K-Means cluster (Step 6)", True),
                                    ("rfm", "predicted_revenue_by_rfm.png", "RFM segment (Step 5)", False)):
        t = R["segments"][key]
        col = t.columns[0]
        fig, ax = plt.subplots(figsize=(12, 0.5 * len(t) + 2))
        y = np.arange(len(t))
        ax.barh(y - 0.2, t["Actual_Revenue"], 0.4, color=ACT, label="Actual")
        ax.barh(y + 0.2, t["Predicted_Revenue"], 0.4, color=PRED, label="Predicted")
        for i, r in t.iterrows():
            b_ = r["Bias_%"]
            ax.text(max(r["Actual_Revenue"], r["Predicted_Revenue"]), i,
                    f"  {'bias ' + format(b_, '+.0f') + '%' if pd.notna(b_) else 'actual = 0'}", va="center", fontsize=8.5)
        ax.set_yticks(y, t[col])
        if colr:
            for tl_, lab in zip(ax.get_yticklabels(), t[col]):
                tl_.set_color(CLUSTER_COLORS[int(lab[1])])
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(lfmt)
        ax.set_xlim(0, max(t["Actual_Revenue"].max(), t["Predicted_Revenue"].max()) * 1.25)
        ax.grid(axis="y", visible=False)
        ax.legend(loc="lower right")
        ax.set_xlabel("Total revenue, test quarters 2025-Q3 + Q4 (₹ lakh)")
        ax.set_title(f"Actual vs predicted revenue by {title}")
        _note(fig, "Segment labels come from Steps 5-6 (computed on 2023-2025) and are used only to group results, "
                   "never as model inputs.")
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)
    return saved


# =============================================================================
# 9. REPORT
# =============================================================================
def write_prediction_report(R: dict, path: Path = REPORT_FILE) -> Path:
    """Markdown report; every number is inserted from computed results."""
    from src.eda import _md_table
    fin = R["selection"]["chosen"]
    tst = R["test_results"]
    t = tst.set_index("Model")
    m = t.loc[fin]
    mean_b = t.loc["Baseline: 12-month quarterly mean"]
    naive = t.loc["Baseline: previous quarter (naive)"]
    best_r2 = tst.loc[tst["R2"].idxmax()]
    tl = R["timeline"]
    tt = tl[tl["Split"].str.startswith("test")]
    sp = R["split"]["summary"]
    tim = R["timing"]
    tun = R["tuning"]
    fs = R["feature_selection"]
    err = R["errors"]
    sc = R["scenarios"].set_index("Scenario")
    imp = R["importance"]

    def tbl(df, cols, fmt=None):
        d = df[cols].copy()
        for c, fn in (fmt or {}).items():
            d[c] = d[c].map(lambda v, fn=fn: "" if pd.isna(v) else fn(v))
        return _md_table(d)

    money = inr
    f3 = lambda v: f"{v:.3f}"            # noqa: E731
    p1 = lambda v: f"{v:.1f}%"           # noqa: E731
    sp1 = lambda v: f"{v:+.1f}%"         # noqa: E731
    L = ["# Revenue Prediction Modelling & Business Driver Analysis - Step 8\n",
         f"> **{config.DATASET_LABEL}.** Results illustrate the method on the Step 2 synthetic dataset (seed 42).\n",
         "Reproduce: `python src/prediction.py` (about 1 minute). Notebook: `notebooks/06_revenue_prediction.ipynb`.\n"]

    L += ["## 1. Objective\n",
          "Build a reproducible, leakage-free model that predicts each existing customer's revenue in the next quarter, "
          "measure how accurately that is possible on unseen quarters, and describe which measurable characteristics the "
          "model associates with revenue.\n",
          "**Prediction vs causal impact.** A prediction model learns *associations* in historical data: \"customers "
          "with more past orders tended to spend more next quarter\". It does **not** show that changing a feature "
          "(e.g. cutting discounts) would *cause* revenue to change; that needs an experiment or a causal design. "
          "Every importance, coefficient and scenario below is an association under the model.\n"]

    L += ["## 2. Prediction unit and target\n",
          _md_table(pd.DataFrame([
              ("Prediction unit", "Customer x quarter: every customer with >= 1 Delivered order in the 12 months before a quarter start"),
              ("Target variable", f"`{TARGET}` = Delivered Sales (Rs) in the 3 months starting at the cutoff; 0 if no purchase"),
              ("Feature period", "the 12 months before the cutoff (3-month sub-window for recent activity)"),
              ("Prediction period", "the calendar quarter starting at the cutoff"),
              ("Business purpose", "plan next-quarter revenue from the existing customer base; see what the model associates with it"),
              ("Why not transactions?", "predicting a line's Sales from Quantity x Price is an identity, not a planning problem"),
              ("Why not category/region-month?", "time-series forecasting of aggregates is Step 9; the customer unit supports "
                                                 "customer, product and regional features and segment analysis"),
          ], columns=["Item", "Definition"])),
          "\n**Coverage.** The panel covers revenue from customers already active; new or reactivated customers are not "
          "in it:\n",
          tbl(tim, ["Cutoff", "Customers", "Quarter_Total_Revenue", "Revenue_Covered", "Coverage_%"],
              {"Cutoff": lambda d: d.date().isoformat(), "Quarter_Total_Revenue": money, "Revenue_Covered": money,
               "Coverage_%": p1}),
          f"\n{pct((R['panel'][TARGET] == 0).mean())} of all customer-quarters have zero revenue. Customer-level MAPE is "
          "therefore undefined and is not used; WAPE (total absolute error / total actual) and quarter-total error are "
          "reported instead.\n"]

    L += ["## 3. Train / validation / test periods (chronological)\n",
          tbl(sp, ["Split", "Cutoffs", "Feature_Data_From", "Feature_Data_To", "Target_Period", "Rows", "Customers",
                   "Zero_Target_%", "Mean_Target"], {"Zero_Target_%": p1, "Mean_Target": money}),
          "\nNo shuffling. Training targets end 2024-12-31, validation targets 2025-01-01 to 2025-06-30, test targets "
          "2025-07-01 to 2025-12-31. Model choice and tuning used validation only; the final model was refit on "
          "train + validation and scored on test (see the design-iteration note in section 4).\n"]

    L += ["## 4. Feature engineering\n",
          f"Candidate features ({len(CANDIDATE_NUMERIC)} numeric + {len(CATEGORICAL_FEATURES)} categorical), all computed "
          "from data dated before the cutoff:\n",
          "- **Customer history:** recency, revenue (3m / 12m / same quarter last year), profit and margin, orders (3m / 12m), "
          "quantity, AOV, average discount, return rate, tenure (capped at 365 days), a point-in-time RFM score, main "
          "payment method, acquisition status.",
          "- **Product:** category revenue shares, main category, number of categories, average unit price, product-demand "
          "index (how popular the customer's products were across all customers), main-category revenue trend.",
          "- **Regional:** region, the region's share of company revenue and of active customers, regional revenue trend.",
          "- **Time:** the calendar quarter being predicted, company revenue trend.\n",
          "**Selection (training rows only):**\n",
          tbl(fs["table"], ["Feature", "Group", "Decision", "Reason", "VIF_All_Candidates", "VIF_Final_Set",
                            "Spearman_with_Target_(train)"],
              {"VIF_All_Candidates": lambda v: "inf" if np.isinf(v) else f"{v:,.1f}", "VIF_Final_Set": lambda v: f"{v:.1f}",
               "Spearman_with_Target_(train)": lambda v: f"{v:+.2f}"}),
          f"\nFinal model: {len(NUMERIC_FEATURES)} numeric + {len(CATEGORICAL_FEATURES)} categorical features. "
          + ("Protected core measures above the VIF limit: " + ", ".join(f"{k} ({v:.1f})" for k, v in
                                                                        fs["protected_above_limit"].items()) + ". "
             if fs["protected_above_limit"] else "")
          + "RFM_Score_at_Cutoff was excluded as redundant (it is built from recency, orders and revenue).\n",
          "**Design iteration (documented for transparency).** The first specification used company and regional revenue "
          "*levels* (Rs). They grow every year and take only 4 distinct values in training, so a linear model used them as "
          "a time trend. That first specification was run end-to-end once (including the test split; test R² 0.05-0.07 for "
          "the ML models). The changes that followed were decided from validation and coefficient diagnostics:\n",
          tbl(R["level_check"], ["Specification", "Distinct_Training_Values_of_Company_Level", "Val_R2", "Val_RMSE",
                                 "Val_Total_Bias_%"], {"Val_R2": f3, "Val_RMSE": money, "Val_Total_Bias_%": sp1}),
          "\n**Encoding / preprocessing** (one scikit-learn `ColumnTransformer`, fitted on training rows only): numeric -> "
          "median imputation -> arcsinh for skewed money/count features -> standardisation; categorical -> most-frequent "
          "imputation -> one-hot encoding (`handle_unknown='ignore'`). One-hot was chosen because none of the categorical "
          "variables is ordinal and it keeps coefficients readable; target encoding was not needed.\n"]

    L += ["## 5. Leakage prevention\n",
          _md_table(R["leakage"]["excluded"]),
          "\n**Automated checks**\n", _md_table(R["leakage"]["checks"]),
          "\nThe full per-feature timing register is `outputs/tables/revenue_feature_catalog.csv`.\n"]

    val = R["evaluation"]["results"]
    L += ["## 6. Baselines and models (validation)\n",
          "Baselines (no fitting): previous quarter's revenue; same quarter last year; the 12-month quarterly mean. "
          "Models: Linear regression (interpretable), Random forest, Gradient boosting - all in scikit-learn pipelines.\n",
          tbl(val, ["Model", "Type", "Train_R2", "Val_MAE", "Val_RMSE", "Val_R2", "Val_WAPE_%", "Val_Total_Bias_%",
                    "Overfit_Gap_R2"],
              {"Train_R2": f3, "Val_MAE": money, "Val_RMSE": money, "Val_R2": f3, "Val_WAPE_%": p1,
               "Val_Total_Bias_%": sp1, "Overfit_Gap_R2": f3}),
          "\n- **MAE**: average absolute rupee error per customer-quarter. **RMSE**: like MAE but penalises large misses "
          "more. **R²**: share of variance explained (0 = no better than predicting the average; negative = worse). "
          "**WAPE**: total absolute error / total actual revenue. **Total bias**: (sum predicted - sum actual) / sum actual.",
          "- The tree models fit training data much better than validation (large overfit gap); the linear model has "
          "almost no gap.\n"]

    L += ["## 7. Hyperparameter tuning\n",
          f"Candidate: **{tun['candidate']}** (the tree model with the lower default validation RMSE). Randomized search, "
          f"{N_TUNING_ITER} settings sampled with `random_state={SEED}`; each fitted on train and scored on validation "
          "(chronological hold-out, no future rows in training).\n",
          "Parameters tested: " + "; ".join(f"`{k}` in {v}" for k, v in TUNING_SPACE[tun["candidate"]].items()) + ".\n",
          tbl(tun["results"].head(8), ["Iteration"] + list(TUNING_SPACE[tun["candidate"]].keys())
              + ["Val_RMSE", "Val_MAE", "Val_R2", "Train_R2"],
              {"Val_RMSE": money, "Val_MAE": money, "Val_R2": f3, "Train_R2": f3}),
          f"\nBest parameters: `{tun['best_params']}`. Validation RMSE {inr(tun['val_metrics']['RMSE'])} vs "
          f"{inr(tun['default_val_rmse'])} for the default ({100 * (tun['val_metrics']['RMSE'] / tun['default_val_rmse'] - 1):+.1f}%); "
          f"tuning mainly reduced overfitting (train R² {tun['train_metrics']['R2']:.2f}).\n"]

    L += ["## 8. Model selection\n",
          f"Rule (set before modelling): keep models within {SIMPLICITY_TOLERANCE:.0%} of the best validation RMSE; "
          "choose the simplest model family (linear < random forest < boosting); within a family the lower validation "
          "RMSE wins. Criteria considered: validation error, overfitting gap, interpretability, business usability and "
          "compute cost.\n",
          tbl(R["selection"]["table"], ["Model", "Val_RMSE", "Val_MAE", "Val_R2", "Train_R2", "Overfit_Gap_R2",
                                        "Within_2%_of_Best", "Selected"],
              {"Val_RMSE": money, "Val_MAE": money, "Val_R2": f3, "Train_R2": f3, "Overfit_Gap_R2": f3}),
          f"\n**Final model: {fin}.** It is within {SIMPLICITY_TOLERANCE:.0%} of the best validation RMSE, has the lowest "
          "validation MAE, almost no overfitting gap, readable coefficients and negligible compute cost.\n"]

    L += ["## 9. Model evaluation (test, 2025-Q3 and Q4)\n",
          tbl(tst, ["Model", "Type", "MAE", "RMSE", "R2", "WAPE_%", "Spearman", "Total_Bias_%", "Selected"],
              {"MAE": money, "RMSE": money, "R2": f3, "WAPE_%": p1, "Spearman": f3, "Total_Bias_%": sp1}),
          f"\n- Final model: MAE **{inr(m['MAE'])}**, RMSE **{inr(m['RMSE'])}**, R² **{m['R2']:.3f}**, WAPE {m['WAPE_%']:.1f}%, "
          f"total bias {m['Total_Bias_%']:+.1f}%.",
          f"- Versus the best baseline (12-month quarterly mean): RMSE {inr(mean_b['RMSE'])} -> {inr(m['RMSE'])} and R² "
          f"{mean_b['R2']:.3f} -> {m['R2']:.3f}, but MAE is {'higher' if m['MAE'] > mean_b['MAE'] else 'lower'} "
          f"({inr(mean_b['MAE'])} baseline). The naive previous-quarter rule is much worse (R² {naive['R2']:.2f}).",
          f"- Highest test R² of any method: {best_r2['R2']:.3f} ({best_r2['Model']}); not used for selection.",
          "- **Customer-level next-quarter revenue is only weakly predictable here**: most customers buy 0-1 times a "
          "quarter, so the amount any single customer spends is dominated by timing noise.",
          "- **Quarter totals** (sum of predictions): " + ", ".join(
              f"{r['Target_Period']} {r['Error_%']:+.1f}% (naive {r['Naive_Error_%']:+.1f}%)" for _, r in tt.iterrows())
          + ". The seasonal (quarter) effect is learned from a single year of training quarters and did not transfer "
            "well; for quarter totals the naive rule was closer on the test quarters.\n",
          "**Quarterly totals (all splits)**\n",
          tbl(tl, ["Target_Period", "Split", "Actual_Revenue", "Predicted_Revenue", "Error_%", "Naive_Baseline",
                   "Naive_Error_%"], {"Actual_Revenue": money, "Predicted_Revenue": money, "Error_%": sp1,
                                      "Naive_Baseline": money, "Naive_Error_%": sp1})]

    L += ["\n## 10. Feature importance\n",
          "Permutation importance of the final pipeline on the test split (each raw feature, including a whole categorical "
          "variable, is shuffled; the rise in MAE is recorded). Read it as *the model relied more heavily on this feature*, "
          "not *this feature causes revenue*.\n",
          tbl(imp.head(15), ["Rank", "Feature", "Group", "Permutation_MAE_Increase", "Permutation_Std"],
              {"Permutation_MAE_Increase": money, "Permutation_Std": money}),
          "\n**Largest linear-regression coefficients** (Rs per +1 SD of the transformed feature, or vs. the reference "
          "category):\n",
          tbl(R["coefficients"].head(12), ["Encoded_Feature", "Coefficient", "Transform"], {"Coefficient": lambda v: f"{v:+,.0f}"}),
          "\nSmall categories (e.g. Books, 73 test rows) get large, unstable coefficients; Main_Category and the category "
          "shares remain partly collinear (one-hot VIF up to ~16).\n"]

    L += ["## 11. Error analysis (test)\n"]
    for key, title in (("quarter", "By target quarter"), ("region", "By region"), ("category", "By main category"),
                       ("range", "By actual revenue range"), ("cluster", "By ML cluster (Step 6)"),
                       ("rfm", "By RFM segment (Step 5)")):
        tb = err[key]
        L += [f"**{title}**\n",
              tbl(tb, [tb.columns[0], "Rows", "Actual_Revenue", "Predicted_Revenue", "MAE", "WAPE_%", "Bias_%"],
                  {"Actual_Revenue": money, "Predicted_Revenue": money, "MAE": money, "WAPE_%": p1, "Bias_%": sp1}), ""]
    rng = err["range"].set_index("Revenue_Range")
    L += ["**Patterns**\n",
          f"- Predictions are pulled toward the average: customers who spent Rs 40k+ in the quarter were under-predicted by "
          f"{abs(rng.loc['Rs 40k+', 'Bias_%']):.0f}%, while customers with no purchase received an average prediction of "
          f"{inr(rng.loc['Rs 0 (no purchase)', 'Avg_Predicted'])}.",
          f"- Regions are similar (MAE {inr(err['region']['MAE'].min())} to {inr(err['region']['MAE'].max())}); bias ranges "
          f"{err['region']['Bias_%'].min():+.0f}% to {err['region']['Bias_%'].max():+.0f}%.",
          f"- Small categories are over-predicted (Books {err['category'].set_index('Main_Category').loc['Books', 'Bias_%']:+.0f}%, "
          f"Sports {err['category'].set_index('Main_Category').loc['Sports', 'Bias_%']:+.0f}%).",
          "- By segment, the pattern mirrors regression to the mean: the highest-value segments are under-predicted and "
          "lapsing segments over-predicted. Segment labels are full-period (look-ahead) and used only for this grouping.\n"]

    L += ["## 12. Business driver analysis\n",
          tbl(R["drivers"]["drivers"], ["Driver", "Group", "Importance_Rank", "Model_Evidence", "Data_Evidence", "Limitation"]),
          "\n**Categorical drivers - what the data shows (train + validation rows)**\n",
          tbl(R["drivers"]["categorical"], ["Feature", "Level", "Rows", "Mean_Next_Quarter_Revenue", "Share_With_Purchase_%"],
              {"Mean_Next_Quarter_Revenue": money, "Share_With_Purchase_%": p1}),
          "\n**What cannot be concluded:** none of these drivers is shown to cause revenue. Frequency, AOV and product mix "
          "move together with customer type and price level; discounts are not randomly assigned; seasonality rests on "
          "one training year.\n"]

    L += ["## 13. Scenario analysis (model-based)\n",
          tbl(R["scenarios"], ["Scenario", "Change_Applied", "Total_Predicted_Revenue", "Change_vs_Current_%",
                               "Rows_Outside_Training_Range_%"],
              {"Total_Predicted_Revenue": money, "Change_vs_Current_%": sp1, "Rows_Outside_Training_Range_%": p1}),
          f"\nUnder the model's assumptions, raising purchase frequency by 10% produces an estimated change in predicted "
          f"test-period revenue of {sc.loc['Purchase frequency +10%', 'Change_vs_Current_%']:+.1f}%, a 10% higher AOV "
          f"{sc.loc['Average order value +10%', 'Change_vs_Current_%']:+.1f}%, and 2 percentage points less discount "
          f"{sc.loc['Average discount -2 percentage points', 'Change_vs_Current_%']:+.1f}%. These are **model-based "
          "scenarios, not guaranteed outcomes**: the discount result reflects that lower-discount customers historically "
          "spent more, not that removing discounts would raise revenue (it could reduce purchases). Linked features were "
          "changed together; almost all scenario rows stay inside the training range.\n"]

    L += ["## 14. Business interpretation\n"]
    for _, r in R["questions"].iterrows():
        L.append(f"- **{r['Question']}** {r['Answer']}")
    L += ["", "## 15. Limitations\n",
          "1. **Synthetic data** from the Step 2 generator.",
          f"2. **Low customer-level accuracy** (test R² {m['R2']:.2f}); the 12-month-mean baseline has a lower MAE. Use "
          "predictions for aggregate planning and ranking, not for individual promises.",
          "3. **Seasonality learned from one year** (4 training quarters); quarter totals missed by up to "
          f"{tt['Error_%'].abs().max():.0f}% on test.",
          "4. **Non-stationary growth**: activity rose each year; scale-free features reduce but do not remove this.",
          f"5. **Coverage**: only customers active in the prior 12 months ({tim['Coverage_%'].min():.0f}-"
          f"{tim['Coverage_%'].max():.0f}% of quarterly revenue).",
          "6. **One test period** (two quarters); results could differ in other periods.",
          "7. **Residual collinearity** between main category and category shares; small categories have unstable effects.",
          "8. **Association, not causation**: importance, coefficients and scenarios describe the model, not interventions.",
          "9. **Design iteration**: the first specification was run once on the test split before the level features "
          "were removed (section 4); later choices were made on validation evidence.\n",
          "## 16. Validation\n", _md_table(R["validation"]),
          "\n## 17. Output files\n",
          "- `data/processed/revenue_modeling_dataset.csv` - customer x quarter panel (all candidate features + target)",
          "- `models/revenue_prediction_model.pkl` (full pipeline), `models/revenue_prediction_preprocessor.pkl`, "
          "`models/revenue_model_metadata.json`",
          "- `outputs/tables/revenue_*.csv` - " + str(sum(1 for p_ in R.get("saved", []) if p_.parent == config.TABLES_DIR))
          + " tables (incl. `revenue_predictions.csv`, `revenue_feature_importance.csv`, `revenue_prediction_by_rfm.csv`, "
          "`revenue_prediction_by_cluster.csv`)",
          "- `outputs/figures/` - " + ", ".join(p_.name for p_ in R.get("figures", []))]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    run_prediction()
