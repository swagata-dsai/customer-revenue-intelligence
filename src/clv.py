#!/usr/bin/env python3
"""
clv.py
======
Step 7 of the Customer Revenue Intelligence project: Customer Lifetime Value (CLV)
analysis and customer-value prediction.

    >>> Works on the SYNTHETIC transaction data cleaned in Step 3. <<<

Two different things are measured and are never mixed up:

    OBSERVED HISTORICAL VALUE   what each customer actually generated, 2023-01-01 .. 2025-12-31
                                (Delivered revenue, cost and profit - facts, not estimates)
    ESTIMATED FUTURE VALUE      what a model estimates a customer may generate in the NEXT
                                12 months, under stated assumptions. It is an estimate.

Pipeline
--------
    load_customer_data()                   cleaned lines + Step 5 RFM + Step 6 clusters
    calculate_customer_tenure()            first / last purchase, tenure, single-purchase flag
    calculate_historical_customer_value()  revenue, cost, profit, orders, AOV ... per customer
    calculate_customer_profitability()     margin, historical revenue CLV, historical profit CLV
    analyze_value_distribution()           totals, mean/median, percentiles, skew, concentration
    check_clv_data_readiness()             can the data support predictive / probabilistic CLV?
    analyze_inactivity_thresholds()        30..365-day inactivity vs. actual repurchase next year
    evaluate_probabilistic_clv()           BG/NBD fitted + tested on a hold-out year; Gamma-Gamma check
    build_predictive_clv_dataset()         time-based panel: 12-month features -> next-12-month profit
    prepare_clv_features()                 feature matrix (history only) and target (future only)
    train_clv_model()                      baseline Ridge vs RandomForest vs GradientBoosting (CV)
    evaluate_clv_model()                   out-of-time test on 2025 + non-ML benchmarks
    calculate_feature_importance()         permutation importance on the test year (+ Ridge coefficients)
    estimate_customer_value()              scores every customer at the reference date
    analyze_clv_by_rfm() / analyze_clv_by_cluster()
    identify_high_value_customers()
    generate_clv_insights()                evidence-based insight table
    validate_clv()                         reconciliation, leakage, time integrity, reproducibility
    save_clv_outputs()                     data, tables, model artefacts, metadata

Main entry point:  python src/clv.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy import stats
from scipy.optimize import minimize
from scipy.special import betaln, gammaln, hyp2f1
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.eda import inr, pct  # noqa: E402
from src.rfm import SEGMENT_ORDER  # noqa: E402

# ----------------------------------------------------------------------------- files
RFM_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_rfm_segments.csv"
ML_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_ml_segments.csv"
RFM_METADATA_FILE = config.PROCESSED_DIR / "customer_rfm_metadata.json"
VALUE_HISTORY_FILE = config.PROCESSED_DIR / "customer_value_history.csv"
CLV_FILE = config.PROCESSED_DIR / "customer_clv.csv"
MODELING_FILE = config.PROCESSED_DIR / "clv_modeling_dataset.csv"
MODELS_DIR = config.PROJECT_ROOT / "models"
MODEL_FILE = MODELS_DIR / "clv_model.pkl"
PREPROCESSOR_FILE = MODELS_DIR / "clv_preprocessor.pkl"
MODEL_METADATA_FILE = MODELS_DIR / "clv_model_metadata.json"
REPORT_FILE = config.REPORTS_DIR / "clv_analysis_report.md"

# ----------------------------------------------------------------------------- design
SEED = config.RANDOM_SEED
DAYS_PER_MONTH = 30.4375
LOOKBACK_MONTHS = 12                     # feature window length
HORIZON_MONTHS = 12                      # target window length
TRAIN_CUTOFF = pd.Timestamp("2024-01-01")    # features 2023      -> target 2024
TEST_CUTOFF = pd.Timestamp("2025-01-01")     # features 2024      -> target 2025 (out-of-time test)
# scoring cutoff = the project reference date (2026-01-01): features 2025 -> estimate for the next 12 months
TENURE_CAP_DAYS = 365                    # the training cutoff only has 12 months of history
INACTIVITY_THRESHOLDS = [30, 60, 90, 180, 270, 365]
AT_RISK_DAYS = 180                       # "potentially at-risk" - justified in analyze_inactivity_thresholds
HIGH_VALUE_QUANTILE = 0.80               # top 20% = "high"
ILLUSTRATIVE_YEARS = 3                   # horizon for the illustrative multi-year value
GG_MAX_ABS_CORR = 0.10                   # Gamma-Gamma needs frequency and spend ~ independent

CANDIDATE_FEATURES = ["Recency_Days", "Frequency", "Revenue", "Profit", "Quantity", "AOV",
                      "Avg_Profit_per_Order", "Profit_Margin", "Avg_Discount", "Categories",
                      "Tenure_Days_Capped", "Purchase_Rate", "Return_Rate"]
SKEWED_FEATURES = ["Recency_Days", "Frequency", "Revenue", "Profit", "Quantity", "AOV",
                   "Avg_Profit_per_Order", "Purchase_Rate"]
# Exact identities: Revenue = AOV x Frequency, Profit = AOV x Frequency x Margin, Profit/order = AOV x Margin.
IDENTITY_FEATURES = {"Revenue": "= AOV x Frequency", "Profit": "= AOV x Frequency x Profit_Margin",
                     "Avg_Profit_per_Order": "= AOV x Profit_Margin"}
PROTECTED_FEATURES = ["Recency_Days", "Frequency", "AOV", "Profit_Margin"]   # the value components; never dropped
MAX_VIF = 5.0
# Result of select_model_features() on the training panel (re-checked in validate_clv):
MODEL_FEATURES = ["Recency_Days", "Frequency", "AOV", "Profit_Margin", "Avg_Discount", "Categories",
                  "Tenure_Days_Capped", "Return_Rate"]
TARGET = "Future_Profit_12M"


# =============================================================================
# 1. DATA
# =============================================================================
def load_customer_data() -> dict:
    """Load the cleaned order lines (Step 3), RFM segments (Step 5) and ML clusters (Step 6)."""
    for p in (config.CLEAN_DATA_FILE, RFM_SEGMENTS_FILE, ML_SEGMENTS_FILE, RFM_METADATA_FILE):
        if not Path(p).exists():
            raise FileNotFoundError(f"{p} not found - run Steps 3, 5 and 6 first.")
    tx = pd.read_csv(config.CLEAN_DATA_FILE, parse_dates=["Order_Date"], encoding="utf-8-sig")
    rfm = pd.read_csv(RFM_SEGMENTS_FILE, parse_dates=["First_Purchase_Date", "Last_Purchase_Date"],
                      encoding="utf-8-sig")
    ml = pd.read_csv(ML_SEGMENTS_FILE, encoding="utf-8-sig")
    meta = json.loads(Path(RFM_METADATA_FILE).read_text(encoding="utf-8"))
    ref = pd.Timestamp(meta["reference_date"])
    return {"tx": tx, "rfm": rfm, "ml": ml, "reference_date": ref,
            "delivered": tx[tx["Is_Delivered"]].copy()}


def _orders(delivered: pd.DataFrame) -> pd.DataFrame:
    """One row per delivered order (an order's date = its first line's date)."""
    return (delivered.groupby(["Customer_ID", "Order_ID"])
            .agg(Order_Date=("Order_Date", "min"), Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
            .reset_index().sort_values(["Customer_ID", "Order_Date"]))


# =============================================================================
# 2. HISTORICAL VALUE
# =============================================================================
def calculate_customer_tenure(delivered: pd.DataFrame, ref: pd.Timestamp,
                              rfm: pd.DataFrame | None = None) -> pd.DataFrame:
    """First / last delivered purchase, tenure to the reference date and active span.

    Customer_Tenure_Days = reference date - first purchase date (length of the observed relationship)
    Active_Span_Days     = last purchase - first purchase (0 for single-purchase customers)
    Tenure is LEFT-CENSORED for customers flagged 'Existing before 2023': their true first purchase
    happened before the data starts, so their tenure here is a minimum.
    """
    g = delivered.groupby("Customer_ID")["Order_Date"]
    t = pd.DataFrame({"First_Purchase_Date": g.min(), "Last_Purchase_Date": g.max()})
    t["Customer_Tenure_Days"] = (ref - t["First_Purchase_Date"]).dt.days
    t["Customer_Tenure_Months"] = (t["Customer_Tenure_Days"] / DAYS_PER_MONTH).round(2)
    t["Active_Span_Days"] = (t["Last_Purchase_Date"] - t["First_Purchase_Date"]).dt.days
    n_orders = delivered.groupby("Customer_ID")["Order_ID"].nunique()
    t["Is_Single_Purchase"] = n_orders.reindex(t.index).eq(1)
    if rfm is not None:
        acq = rfm.set_index("Customer_ID")["Acquisition_Status"]
        t["Acquisition_Status"] = acq.reindex(t.index)
        t["Tenure_Left_Censored"] = t["Acquisition_Status"].eq("Existing before 2023")
    return t


def calculate_historical_customer_value(tx: pd.DataFrame) -> pd.DataFrame:
    """Customer-level OBSERVED value from Delivered lines (the project's revenue rule).

    Returned and Cancelled lines carry no revenue and no profit (Step 3 rule); they are counted
    separately so the return behaviour is still visible.
    """
    d = tx[tx["Is_Delivered"]]
    g = d.groupby("Customer_ID")
    v = pd.DataFrame({
        "Total_Revenue": g["Sales"].sum(),
        "Total_Cost": g["Cost"].sum(),
        "Total_Profit": g["Profit"].sum(),
        "Total_Orders": g["Order_ID"].nunique(),
        "Total_Quantity": g["Quantity"].sum(),
        "Order_Lines": g.size(),
        "Average_Discount": g["Discount"].mean(),
        "Categories_Bought": g["Category"].nunique(),
    })
    v["Average_Order_Value"] = v["Total_Revenue"] / v["Total_Orders"]
    v["Average_Order_Profit"] = v["Total_Profit"] / v["Total_Orders"]
    status = tx.groupby(["Customer_ID", "Order_Status"]).size().unstack(fill_value=0)
    for s, col in (("Returned", "Returned_Lines"), ("Cancelled", "Cancelled_Lines")):
        v[col] = status.get(s, pd.Series(0, index=status.index)).reindex(v.index).fillna(0).astype(int)
    v["Return_Cancel_Rate"] = (v["Returned_Lines"] + v["Cancelled_Lines"]) / (
        v["Order_Lines"] + v["Returned_Lines"] + v["Cancelled_Lines"])
    return v


def calculate_customer_profitability(value: pd.DataFrame, tenure: pd.DataFrame) -> pd.DataFrame:
    """Join value + tenure and derive the two historical CLV measures and value tiers.

    Historical_Revenue_CLV = total Delivered revenue      (observed, 2023-2025)
    Historical_Profit_CLV  = total Delivered profit       (observed; the economically meaningful one)
    """
    h = value.join(tenure, how="left")
    h["Historical_Profit_Margin"] = h["Total_Profit"] / h["Total_Revenue"]
    h["Historical_Revenue_CLV"] = h["Total_Revenue"]
    h["Historical_Profit_CLV"] = h["Total_Profit"]
    # annual profit rate over the observed relationship (tenure floored at 12 months so a customer
    # acquired a few weeks ago is not annualised from a single order)
    h["Historical_Annual_Profit_Rate"] = h["Total_Profit"] / np.maximum(h["Customer_Tenure_Months"], 12) * 12
    h["Historical_Profit_Percentile"] = h["Total_Profit"].rank(pct=True).round(4)
    h["Historical_Value_Decile"] = pd.qcut(h["Total_Profit"].rank(method="first"), 10,
                                           labels=range(10, 0, -1)).astype(int)   # 1 = top 10%
    h.index.name = "Customer_ID"
    return h.reset_index()


def analyze_value_distribution(hist: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Totals, averages, medians, percentiles, skewness and concentration of customer value."""
    rows = []
    for col, name in (("Total_Revenue", "Historical revenue"), ("Total_Profit", "Historical profit")):
        s = hist[col]
        rows.append({"Measure": name, "Customers": len(s), "Total": s.sum(), "Mean": s.mean(),
                     "Median": s.median(), "Std": s.std(), "Min": s.min(), "Max": s.max(),
                     "Mean_to_Median": s.mean() / s.median(), "Skewness": stats.skew(s),
                     "Skewness_log1p": stats.skew(np.log1p(s.clip(lower=0))),
                     "Customers_below_zero": int((s < 0).sum())})
    summary = pd.DataFrame(rows)
    q = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    perc = pd.DataFrame({"Percentile": [f"P{int(x * 100)}" for x in q],
                         "Historical_Revenue": hist["Total_Revenue"].quantile(q).to_numpy(),
                         "Historical_Profit": hist["Total_Profit"].quantile(q).to_numpy(),
                         "Total_Orders": hist["Total_Orders"].quantile(q).to_numpy(),
                         "Customer_Tenure_Days": hist["Customer_Tenure_Days"].quantile(q).to_numpy()})
    conc = []
    for top in (0.01, 0.05, 0.10, 0.20, 0.50):
        n = int(round(top * len(hist)))
        row = {"Top_Customers_%": top * 100, "Customers": n}
        for col, name in (("Total_Revenue", "Revenue"), ("Total_Profit", "Profit")):
            s = hist[col].sort_values(ascending=False)
            row[f"{name}_Share_%"] = 100 * s.iloc[:n].sum() / s.sum()
        conc.append(row)
    conc = pd.DataFrame(conc)
    gini = {}
    for col in ("Total_Revenue", "Total_Profit"):
        s = np.sort(hist[col].clip(lower=0).to_numpy())
        n = len(s)
        gini[col] = float((2 * np.arange(1, n + 1) - n - 1).dot(s) / (n * s.sum()))
    conc.attrs["gini"] = gini
    single = (hist.groupby("Is_Single_Purchase")
              .agg(Customers=("Customer_ID", "count"), Avg_Revenue=("Total_Revenue", "mean"),
                   Median_Revenue=("Total_Revenue", "median"), Avg_Profit=("Total_Profit", "mean"),
                   Median_Profit=("Total_Profit", "median"), Total_Profit=("Total_Profit", "sum"),
                   Avg_Order_Value=("Average_Order_Value", "mean"),
                   Median_Tenure_Days=("Customer_Tenure_Days", "median"),
                   Median_Days_Since_Purchase=("Last_Purchase_Date",
                                               lambda s: (hist["Last_Purchase_Date"].max() - s).dt.days.median()),
                   Share_Existing_Before_2023=("Tenure_Left_Censored", "mean"))
              .reset_index())
    single["Is_Single_Purchase"] = single["Is_Single_Purchase"].map({True: "Single purchase",
                                                                     False: "Repeat purchasers"})
    single["Profit_Share_%"] = 100 * single["Total_Profit"] / single["Total_Profit"].sum()
    single["Customer_Share_%"] = 100 * single["Customers"] / single["Customers"].sum()
    return {"summary": summary, "percentiles": perc, "concentration": conc, "gini": gini,
            "single_purchase": single}


# =============================================================================
# 3. METHODOLOGY EVIDENCE
# =============================================================================
def analyze_inactivity_thresholds(delivered: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """How often do customers who have been inactive for >= N days buy again in the next 12 months?

    Measured at two real cutoffs (2024-01-01 and 2025-01-01) where the following 12 months exist.
    This is what tells us whether 'inactive for N days' can be called churn (it cannot, here).
    """
    o = _orders(delivered)
    gaps = o.groupby("Customer_ID")["Order_Date"].diff().dt.days.dropna()
    gap_stats = pd.DataFrame({"Statistic": ["Repeat intervals", "Mean", "P25", "Median", "P75", "P90", "P95"],
                              "Days": [len(gaps), gaps.mean(), gaps.quantile(.25), gaps.median(),
                                       gaps.quantile(.75), gaps.quantile(.90), gaps.quantile(.95)]})
    rows = []
    for cut in (TRAIN_CUTOFF, TEST_CUTOFF):
        hi = cut + pd.DateOffset(months=HORIZON_MONTHS)
        last = o[o["Order_Date"] < cut].groupby("Customer_ID")["Order_Date"].max()
        rec = (cut - last).dt.days
        buyers = set(o[(o["Order_Date"] >= cut) & (o["Order_Date"] < hi)]["Customer_ID"])
        bought = rec.index.isin(list(buyers))
        max_hist = (cut - o["Order_Date"].min()).days
        for th in INACTIVITY_THRESHOLDS:
            if th >= max_hist:
                continue
            m = rec.to_numpy() >= th
            rows.append({"Cutoff": cut.date().isoformat(), "Threshold_Days": th,
                         "Customers_Inactive_>=_Threshold": int(m.sum()),
                         "Share_of_Customers_%": 100 * m.mean(),
                         "Bought_Again_Next_12M_%": 100 * bought[m].mean() if m.any() else np.nan,
                         "Bought_Again_if_Below_Threshold_%": 100 * bought[~m].mean() if (~m).any() else np.nan})
    return {"gaps": gap_stats, "sensitivity": pd.DataFrame(rows)}


def check_clv_data_readiness(hist: pd.DataFrame, delivered: pd.DataFrame, inactivity: dict) -> pd.DataFrame:
    """Evidence table: does the data support each ingredient of a CLV model?"""
    o = _orders(delivered)
    years = o["Order_Date"].dt.year
    active_by_year = o.groupby(years)["Customer_ID"].nunique()
    orders_by_year = o.groupby(years)["Order_ID"].nunique()
    sens = inactivity["sensitivity"]
    s180 = sens[sens["Threshold_Days"] == AT_RISK_DAYS]
    rows = [
        ("Repeat purchasing", f"{pct(1 - hist['Is_Single_Purchase'].mean())} of customers have 2+ delivered orders",
         "Yes"),
        ("Purchase frequency", f"median {hist['Total_Orders'].median():.0f} orders per customer "
                               f"(P90 {hist['Total_Orders'].quantile(.9):.0f})", "Yes"),
        ("Time period", f"{o['Order_Date'].min().date()} to {o['Order_Date'].max().date()} "
                        f"(36 months) - enough for a 12-month feature window + 12-month target, twice", "Yes"),
        ("Customer tenure", f"measurable from first observed purchase; LEFT-CENSORED for "
                            f"{pct(hist['Tenure_Left_Censored'].mean())} of customers ('Existing before 2023')",
         "Partly"),
        ("Churn / inactivity", f"no churn flag in the data; of customers inactive >= {AT_RISK_DAYS} days, "
                               + ", ".join(f"{r['Bought_Again_Next_12M_%']:.0f}% (cutoff {r['Cutoff']})"
                                           for _, r in s180.iterrows())
                               + " bought again within 12 months", "No - churn cannot be observed"),
        ("Stationarity", "active customers per year " + " / ".join(f"{y}: {v:,}" for y, v in active_by_year.items())
                         + "; orders " + " / ".join(f"{y}: {v:,}" for y, v in orders_by_year.items()),
         "No - activity grows year on year"),
        ("Customer-level history", f"{len(o):,} delivered orders for {hist['Customer_ID'].nunique():,} customers",
         "Yes"),
    ]
    return pd.DataFrame(rows, columns=["Requirement", "Evidence", "Supported"])


# ---------------------------------------------------------------- BG/NBD (implemented with scipy)
def _bgnbd_summary(orders: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Frequency (repeat purchase days), recency t_x and age T in weeks, calibration period only."""
    c = orders[orders["Order_Date"] < cutoff]
    days = c.groupby("Customer_ID")["Order_Date"]
    first, last = days.min(), days.max()
    return pd.DataFrame({"x": days.nunique() - 1,
                         "t_x": (last - first).dt.days / 7.0,
                         "T": (cutoff - first).dt.days / 7.0})


def fit_bgnbd(summary: pd.DataFrame) -> dict:
    """Maximum-likelihood fit of the BG/NBD model (Fader, Hardie & Lee, 2005)."""
    x, tx, T = (summary[c].to_numpy(float) for c in ("x", "t_x", "T"))

    def nll(p):
        r, a, alpha, b = np.exp(p)
        a1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
        a2 = betaln(a, b + x) - betaln(a, b)
        a3 = -(r + x) * np.log(alpha + T)
        a4 = np.where(x > 0, np.log(a) - np.log(np.maximum(b + x - 1, 1e-12)) - (r + x) * np.log(alpha + tx),
                      -np.inf)
        return -(a1 + a2 + np.logaddexp(a3, a4)).sum()

    res = minimize(nll, np.log([1.0, 1.0, 10.0, 1.0]), method="Nelder-Mead",
                   options={"maxiter": 10000, "xatol": 1e-7, "fatol": 1e-7})
    r, a, alpha, b = np.exp(res.x)
    return {"r": r, "alpha": alpha, "a": a, "b": b, "converged": bool(res.success), "neg_log_lik": res.fun}


def bgnbd_expected_purchases(p: dict, summary: pd.DataFrame, t_weeks: float) -> tuple[np.ndarray, np.ndarray]:
    """Conditional expected purchases in the next t weeks and P(alive), per customer."""
    x, tx, T = (summary[c].to_numpy(float) for c in ("x", "t_x", "T"))
    r, a, alpha, b = p["r"], p["a"], p["alpha"], p["b"]
    ratio = ((alpha + T) / (alpha + tx)) ** (r + x)
    den = 1 + (x > 0) * (a / np.maximum(b + x - 1, 1e-12)) * ratio
    term = 1 - ((alpha + T) / (alpha + T + t_weeks)) ** (r + x) * hyp2f1(r + x, b + x, a + b + x - 1,
                                                                          t_weeks / (alpha + T + t_weeks))
    return (a + b + x - 1) / (a - 1) * term / den, 1 / den


def evaluate_probabilistic_clv(delivered: pd.DataFrame) -> dict:
    """Fit BG/NBD on history before 2025, test it on 2025, and check the Gamma-Gamma assumption."""
    o = _orders(delivered)
    hi = TEST_CUTOFF + pd.DateOffset(months=HORIZON_MONTHS)
    summ = _bgnbd_summary(o, TEST_CUTOFF)
    params = fit_bgnbd(summ)
    t_weeks = (hi - TEST_CUTOFF).days / 7.0
    exp_n, p_alive = bgnbd_expected_purchases(params, summ, t_weeks)
    hold = o[(o["Order_Date"] >= TEST_CUTOFF) & (o["Order_Date"] < hi)]
    actual_n = hold.groupby("Customer_ID")["Order_Date"].nunique().reindex(summ.index).fillna(0).to_numpy()
    avg_profit = o[o["Order_Date"] < TEST_CUTOFF].groupby("Customer_ID")["Profit"].mean().reindex(summ.index)
    pred = pd.DataFrame({"Customer_ID": summ.index, "BGNBD_Expected_Orders": exp_n, "BGNBD_P_Alive": p_alive,
                         "Actual_Orders_2025": actual_n,
                         "BGNBD_Profit_Estimate": exp_n * avg_profit.to_numpy()})
    # Gamma-Gamma assumption: spend per order independent of purchase frequency (repeat customers)
    cal = o[o["Order_Date"] < TEST_CUTOFF].groupby("Customer_ID").agg(n=("Order_ID", "nunique"),
                                                                       aov=("Revenue", "mean"))
    rep = cal[cal["n"] > 1]
    pr, pp = stats.pearsonr(rep["n"], rep["aov"])
    sr, sp = stats.spearmanr(rep["n"], rep["aov"])
    gg_ok = abs(pr) <= GG_MAX_ABS_CORR and abs(sr) <= GG_MAX_ABS_CORR
    evaluation = pd.DataFrame([
        ("Calibration period", f"{o['Order_Date'].min().date()} to {(TEST_CUTOFF - pd.Timedelta(days=1)).date()}"),
        ("Hold-out period", f"{TEST_CUTOFF.date()} to {(hi - pd.Timedelta(days=1)).date()}"),
        ("Customers in calibration", f"{len(summ):,}"),
        ("Fitted parameters (r, alpha, a, b)",
         f"{params['r']:.3f}, {params['alpha']:.2f}, {params['a']:.4f}, {params['b']:.3f}"),
        ("Optimiser converged", str(params["converged"])),
        ("Hold-out orders: predicted vs actual", f"{exp_n.sum():,.0f} vs {actual_n.sum():,.0f} "
                                                 f"({exp_n.sum() / actual_n.sum():.1%} of actual)"),
        ("Hold-out orders per customer: MAE", f"{mean_absolute_error(actual_n, exp_n):.2f}"),
        ("Hold-out orders per customer: R²", f"{r2_score(actual_n, exp_n):.3f}"),
        ("Hold-out orders: Spearman rank correlation", f"{stats.spearmanr(actual_n, exp_n)[0]:.3f}"),
        ("Gamma-Gamma check: Pearson r(frequency, avg order value), repeat customers",
         f"{pr:.3f} (p = {pp:.1e}, n = {len(rep):,})"),
        ("Gamma-Gamma check: Spearman rho", f"{sr:.3f} (p = {sp:.1e})"),
        ("Gamma-Gamma usable?", "Yes" if gg_ok else
         f"No - absolute correlation > {GG_MAX_ABS_CORR}: frequency and spend are NOT independent"),
    ], columns=["Item", "Result"])
    return {"params": params, "summary": summ, "predictions": pred, "evaluation": evaluation,
            "gg_ok": gg_ok, "gg_pearson": pr, "gg_spearman": sr,
            "orders_ratio": exp_n.sum() / actual_n.sum(), "orders_r2": r2_score(actual_n, exp_n)}


# =============================================================================
# 4. PREDICTIVE DATASET (time-based: history -> future)
# =============================================================================
def build_predictive_clv_dataset(tx: pd.DataFrame, cutoff: pd.Timestamp, with_target: bool = True) -> pd.DataFrame:
    """One row per customer with >= 1 Delivered order in the 12 months before `cutoff`.

    FEATURES use only lines dated in [cutoff - 12 months, cutoff)   (plus first purchase date, for tenure)
    TARGET   uses only Delivered lines dated in [cutoff, cutoff + 12 months)
    Nothing from the target window is used to build a feature.
    """
    cutoff = pd.Timestamp(cutoff)
    lo = cutoff - pd.DateOffset(months=LOOKBACK_MONTHS)
    hi = cutoff + pd.DateOffset(months=HORIZON_MONTHS)
    past = tx[tx["Order_Date"] < cutoff]
    win = past[past["Order_Date"] >= lo]
    wd = win[win["Is_Delivered"]]
    g = wd.groupby("Customer_ID")
    f = pd.DataFrame({
        "Recency_Days": (cutoff - g["Order_Date"].max()).dt.days,
        "Frequency": g["Order_ID"].nunique(),
        "Revenue": g["Sales"].sum(),
        "Profit": g["Profit"].sum(),
        "Quantity": g["Quantity"].sum(),
        "Avg_Discount": g["Discount"].mean(),
        "Categories": g["Category"].nunique(),
    })
    first_ever = past[past["Is_Delivered"]].groupby("Customer_ID")["Order_Date"].min().reindex(f.index)
    f["Tenure_Days_Capped"] = np.minimum((cutoff - first_ever).dt.days, TENURE_CAP_DAYS)
    f["AOV"] = f["Revenue"] / f["Frequency"]
    f["Avg_Profit_per_Order"] = f["Profit"] / f["Frequency"]
    f["Profit_Margin"] = f["Profit"] / f["Revenue"]
    f["Purchase_Rate"] = f["Frequency"] / np.maximum(f["Tenure_Days_Capped"] / DAYS_PER_MONTH, 1.0)
    f["Return_Rate"] = 1 - win[win["Customer_ID"].isin(f.index)].groupby("Customer_ID")["Is_Delivered"].mean()
    f = f[CANDIDATE_FEATURES]
    f.insert(0, "Cutoff_Date", cutoff.date().isoformat())
    f["Feature_Window"] = f"{lo.date()} to {(cutoff - pd.Timedelta(days=1)).date()}"
    f.attrs["max_feature_date"] = wd["Order_Date"].max()
    if with_target:
        fut = tx[(tx["Order_Date"] >= cutoff) & (tx["Order_Date"] < hi) & tx["Is_Delivered"]]
        fg = fut.groupby("Customer_ID")
        f["Target_Window"] = f"{cutoff.date()} to {(hi - pd.Timedelta(days=1)).date()}"
        f[TARGET] = fg["Profit"].sum().reindex(f.index).fillna(0.0)
        f["Future_Revenue_12M"] = fg["Sales"].sum().reindex(f.index).fillna(0.0)
        f["Future_Orders_12M"] = fg["Order_ID"].nunique().reindex(f.index).fillna(0).astype(int)
        f["Purchased_Next_12M"] = f["Future_Orders_12M"] > 0
        f.attrs["min_target_date"] = fut["Order_Date"].min()
    f.index.name = "Customer_ID"
    return f.reset_index()


def prepare_clv_features(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series | None]:
    """Split a panel into X (historical features only) and y (future profit), if present."""
    X = panel[MODEL_FEATURES].astype(float)
    y = panel[TARGET].astype(float) if TARGET in panel else None
    return X, y


def build_preprocessor(features: list[str] | None = None) -> Pipeline:
    """arcsinh on the right-skewed money/count features (handles the rare negative profit),
    then StandardScaler on everything. arcsinh(x) ~ log(2x) for large x."""
    features = MODEL_FEATURES if features is None else features
    skewed = [c for c in features if c in SKEWED_FEATURES]
    other = [c for c in features if c not in SKEWED_FEATURES]
    ct = ColumnTransformer([("asinh", FunctionTransformer(np.arcsinh, feature_names_out="one-to-one"),
                             skewed),
                            ("keep", "passthrough", other)], verbose_feature_names_out=False)
    return Pipeline([("transform", ct), ("scale", StandardScaler())])


def _vif(X: pd.DataFrame) -> pd.Series:
    """Variance inflation factor of each column (regress it on all the others)."""
    Z = X.to_numpy(float)
    out = {}
    for i, col in enumerate(X.columns):
        y = Z[:, i]
        A = np.c_[np.ones(len(Z)), np.delete(Z, i, axis=1)]
        resid = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
        r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
        out[col] = np.inf if r2 >= 1 else 1 / (1 - r2)
    return pd.Series(out)


def select_model_features(train: pd.DataFrame) -> dict:
    """Evidence-based feature selection on the TRAINING panel (transformed as the model sees it).

    1. Drop exact identities (Revenue, Profit, Profit per order are products of AOV, Frequency, Margin):
       keeping them makes linear coefficients unstable and importances meaningless.
    2. Iteratively drop the non-protected feature with the highest VIF while any VIF > MAX_VIF (5).
    """
    X = pd.DataFrame(build_preprocessor(CANDIDATE_FEATURES).fit_transform(train[CANDIDATE_FEATURES]),
                     columns=CANDIDATE_FEATURES)
    vif_all = _vif(X)
    rows = {f: {"Feature": f, "VIF_All_Candidates": vif_all[f], "Decision": "Kept", "Reason": ""}
            for f in CANDIDATE_FEATURES}
    keep = [f for f in CANDIDATE_FEATURES if f not in IDENTITY_FEATURES]
    for f, why in IDENTITY_FEATURES.items():
        rows[f].update(Decision="Excluded", Reason=f"exact identity {why}")
    while True:
        v = _vif(X[keep])
        cand = v.drop(PROTECTED_FEATURES, errors="ignore")
        if cand.max() <= MAX_VIF:
            break
        worst = cand.idxmax()
        rows[worst].update(Decision="Excluded", Reason=f"VIF {cand.max():.1f} > {MAX_VIF:.0f} (redundant with other features)")
        keep.remove(worst)
    final_vif = _vif(X[keep])
    for f in CANDIDATE_FEATURES:
        rows[f]["VIF_Final_Set"] = final_vif.get(f, np.nan)
        rows[f]["Spearman_with_Target_(train)"] = stats.spearmanr(train[f], train[TARGET])[0]
        if rows[f]["Decision"] == "Kept":
            rows[f]["Reason"] = "value component (always kept)" if f in PROTECTED_FEATURES else f"VIF <= {MAX_VIF:.0f}"
    return {"table": pd.DataFrame(rows.values()), "selected": keep}


def candidate_models() -> dict:
    """Interpretable baseline first, then two stronger non-linear models."""
    return {
        "Ridge regression (baseline)": RidgeCV(alphas=np.logspace(-2, 3, 26)),
        "Random forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=10, random_state=SEED, n_jobs=-1),
        "Gradient boosting": GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.03,
                                                       subsample=0.8, random_state=SEED),
    }


def _metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    nz = y != 0
    top = np.argsort(-p, kind="stable")[: int(round(0.2 * len(p)))]
    return {"MAE": mean_absolute_error(y, p), "RMSE": float(np.sqrt(mean_squared_error(y, p))),
            "R2": r2_score(y, p),
            "WAPE_%": 100 * np.abs(y - p).sum() / np.abs(y).sum(),
            "MAPE_nonzero_%": 100 * np.mean(np.abs((y[nz] - p[nz]) / y[nz])),
            "Spearman": stats.spearmanr(y, p)[0],
            "Top20_Capture_%": 100 * y[top].sum() / y.sum(),
            "Predicted_to_Actual_Total": p.sum() / y.sum()}


def train_clv_model(train: pd.DataFrame) -> dict:
    """5-fold CV on the TRAINING cutoff only (features 2023 -> target 2024) to choose the model.

    Rule: the model with the lowest mean CV RMSE is selected. The test year plays no part in the choice.
    The Ridge baseline is kept alongside as the interpretable reference (coefficients show direction).
    """
    X, y = prepare_clv_features(train)
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    rows = []
    for name, est in candidate_models().items():
        fold = []
        for tr_i, va_i in kf.split(X):
            pre = build_preprocessor().fit(X.iloc[tr_i])
            m = clone(est).fit(pre.transform(X.iloc[tr_i]), y.iloc[tr_i])
            p = np.clip(m.predict(pre.transform(X.iloc[va_i])), 0, None)
            fold.append(_metrics(y.iloc[va_i], p))
        f = pd.DataFrame(fold)
        rows.append({"Model": name, "CV_RMSE": f["RMSE"].mean(), "CV_RMSE_Std": f["RMSE"].std(),
                     "CV_MAE": f["MAE"].mean(), "CV_R2": f["R2"].mean()})
    cv = pd.DataFrame(rows)
    chosen = cv.loc[cv["CV_RMSE"].idxmin(), "Model"]
    cv["Selected"] = cv["Model"].eq(chosen)
    pre = build_preprocessor().fit(X)
    fitted = {n: clone(e).fit(pre.transform(X), y) for n, e in candidate_models().items()}
    return {"cv": cv, "chosen": chosen, "preprocessor": pre, "models": fitted}


def _recency_band(days: pd.Series) -> pd.Series:
    return pd.cut(days, [-1, 30, 90, AT_RISK_DAYS, 10_000],
                  labels=["0-30 d", "31-90 d", f"91-{AT_RISK_DAYS} d", f">{AT_RISK_DAYS} d"])


def simplified_clv_estimate(panel: pd.DataFrame, repeat_prob: pd.Series) -> np.ndarray:
    """Transparent formula:  AOV x Frequency(12M) x Profit margin x P(buys again | recency band).

    AOV x Frequency x margin = last-12-month profit; P(buys again) is the share of customers in the
    same recency band who bought again in the following 12 months at the TRAINING cutoff.
    """
    p = _recency_band(panel["Recency_Days"]).map(repeat_prob).astype(float).to_numpy()
    return (panel["AOV"] * panel["Frequency"] * panel["Profit_Margin"]).to_numpy() * p


def evaluate_clv_model(trained: dict, train: pd.DataFrame, test: pd.DataFrame, bg: dict) -> dict:
    """Out-of-time test: models trained on 2023->2024 are scored on 2024-features -> 2025-target.

    Also scores three non-ML benchmarks on exactly the same customers.
    """
    X, y = prepare_clv_features(test)
    pre = trained["preprocessor"]
    preds = {n: np.clip(m.predict(pre.transform(X)), 0, None) for n, m in trained["models"].items()}
    rp = train.assign(b=_recency_band(train["Recency_Days"])).groupby("b", observed=True)["Purchased_Next_12M"].mean()
    preds["Naive: last-12-month profit repeats"] = test["Profit"].clip(lower=0).to_numpy()
    preds["Simplified formula (AOV x F x margin x P(repeat))"] = np.clip(simplified_clv_estimate(test, rp), 0, None)
    bgp = bg["predictions"].set_index("Customer_ID")["BGNBD_Profit_Estimate"].reindex(test["Customer_ID"])
    preds["BG/NBD orders x avg profit per order"] = np.clip(bgp.to_numpy(), 0, None)
    rows = []
    for name, p in preds.items():
        kind = "ML model" if name in trained["models"] else "Benchmark"
        rows.append({"Model": name, "Type": kind, **_metrics(y, p), "Selected": name == trained["chosen"]})
    comp = pd.DataFrame(rows)
    chosen = trained["chosen"]
    tp = pd.DataFrame({"Customer_ID": test["Customer_ID"], "Actual_Future_Profit_12M": y.to_numpy(),
                       "Predicted_Future_Profit_12M": preds[chosen],
                       "Naive_Benchmark": preds["Naive: last-12-month profit repeats"],
                       "Purchased_Next_12M": test["Purchased_Next_12M"].to_numpy()})
    tp["Predicted_Decile"] = pd.qcut(tp["Predicted_Future_Profit_12M"].rank(method="first"), 10,
                                     labels=range(1, 11)).astype(int)
    calib = (tp.groupby("Predicted_Decile")
             .agg(Customers=("Customer_ID", "count"), Mean_Predicted=("Predicted_Future_Profit_12M", "mean"),
                  Mean_Actual=("Actual_Future_Profit_12M", "mean"),
                  Share_Purchased=("Purchased_Next_12M", "mean")).reset_index())
    return {"comparison": comp, "test_predictions": tp, "calibration": calib, "repeat_prob": rp,
            "metrics": comp[comp["Model"] == chosen].iloc[0].to_dict()}


def calculate_feature_importance(trained: dict, test: pd.DataFrame) -> pd.DataFrame:
    """Permutation importance of the selected model on the TEST year (increase in MAE when a feature
    is shuffled). Also the Ridge standardised coefficients, for direction. Association, not causation."""
    X, y = prepare_clv_features(test)
    Xt = trained["preprocessor"].transform(X)
    model = trained["models"][trained["chosen"]]
    pi = permutation_importance(model, Xt, y, scoring="neg_mean_absolute_error", n_repeats=30,
                                random_state=SEED)
    imp = pd.DataFrame({"Feature": MODEL_FEATURES, "Permutation_MAE_Increase": pi.importances_mean,
                        "Permutation_Std": pi.importances_std})
    ridge = trained["models"]["Ridge regression (baseline)"]
    imp["Ridge_Std_Coefficient"] = ridge.coef_
    imp["Transform"] = ["arcsinh + scale" if f in SKEWED_FEATURES else "scale" for f in MODEL_FEATURES]
    return imp.sort_values("Permutation_MAE_Increase", ascending=False).reset_index(drop=True)


# =============================================================================
# 5. SCORING EVERY CUSTOMER (ESTIMATES)
# =============================================================================
def annual_repeat_rates(delivered: pd.DataFrame) -> pd.DataFrame:
    """Share of customers active in year t who bought again in year t+1 (observed)."""
    o = _orders(delivered)
    yrs = sorted(o["Order_Date"].dt.year.unique())
    rows = []
    for a, b in zip(yrs[:-1], yrs[1:]):
        sa = set(o[o["Order_Date"].dt.year == a]["Customer_ID"])
        sb = set(o[o["Order_Date"].dt.year == b]["Customer_ID"])
        rows.append({"From_Year": a, "To_Year": b, "Active_Customers": len(sa), "Bought_Again": len(sa & sb),
                     "Repeat_Rate": len(sa & sb) / len(sa)})
    r = pd.DataFrame(rows)
    r.attrs["pooled"] = r["Bought_Again"].sum() / r["Active_Customers"].sum()
    return r


def estimate_customer_value(D: dict, hist: pd.DataFrame, final: dict, repeat_prob: pd.Series,
                            rates: pd.DataFrame) -> dict:
    """Estimated future value for every customer at the reference date.

    - Customers with a Delivered order in the last 12 months (the model's population): the final model's
      estimate of profit in the next 12 months.
    - Customers with no order in the last 12 months (outside the model's population): the average
      next-12-month profit OBSERVED for the equivalent group at the 2025 cutoff (bought before 2024,
      not in 2024), applied as a group-level estimate.
    - Illustrative multi-year value = 12-month estimate x (1 + r + r^2), r = observed annual repeat rate.
      Not validated - there is no data after 2025 to test it.
    """
    ref = D["reference_date"]
    score = build_predictive_clv_dataset(D["tx"], ref, with_target=False)
    X, _ = prepare_clv_features(score)
    est = np.clip(final["model"].predict(final["preprocessor"].transform(X)), 0, None)
    s = pd.DataFrame({"Customer_ID": score["Customer_ID"], "Estimated_12M_Future_Profit": est,
                      "Simplified_12M_Estimate": np.clip(simplified_clv_estimate(score, repeat_prob), 0, None),
                      "Estimate_Method": "ML model (active in last 12 months)"})
    # lapsed group: empirical estimate from the 2025 cutoff
    o = _orders(D["delivered"])
    lo = TEST_CUTOFF - pd.DateOffset(months=LOOKBACK_MONTHS)
    before = set(o[o["Order_Date"] < lo]["Customer_ID"])
    in_window = set(o[(o["Order_Date"] >= lo) & (o["Order_Date"] < TEST_CUTOFF)]["Customer_ID"])
    lapsed_2025 = sorted(before - in_window)
    fut = o[(o["Order_Date"] >= TEST_CUTOFF)].groupby("Customer_ID")["Profit"].sum()
    lapsed_outcome = fut.reindex(lapsed_2025).fillna(0)
    lapsed_value = float(lapsed_outcome.mean())
    lapsed_repeat = float((lapsed_outcome > 0).mean())
    rest = hist.loc[~hist["Customer_ID"].isin(s["Customer_ID"]), ["Customer_ID"]].copy()
    rest["Estimated_12M_Future_Profit"] = lapsed_value
    rest["Simplified_12M_Estimate"] = lapsed_value
    rest["Estimate_Method"] = "Group average (no order in last 12 months)"
    s = pd.concat([s, rest], ignore_index=True)
    r = rates.attrs["pooled"]
    factor = sum(r ** k for k in range(ILLUSTRATIVE_YEARS))
    s["Illustrative_3Y_Value"] = s["Estimated_12M_Future_Profit"] * factor
    sens = []
    for label, rr in [(f"{int(rates.iloc[0]['From_Year'])}->{int(rates.iloc[0]['To_Year'])} observed",
                       rates.iloc[0]["Repeat_Rate"]),
                      ("Pooled observed (used)", r),
                      (f"{int(rates.iloc[-1]['From_Year'])}->{int(rates.iloc[-1]['To_Year'])} observed",
                       rates.iloc[-1]["Repeat_Rate"])]:
        f_ = sum(rr ** k for k in range(ILLUSTRATIVE_YEARS))
        sens.append({"Scenario": label, "Annual_Repeat_Rate": rr, "Horizon_Factor": f_,
                     "Total_Illustrative_3Y_Value": s["Estimated_12M_Future_Profit"].sum() * f_})
    return {"scores": s, "scoring_panel": score, "lapsed_value": lapsed_value, "lapsed_repeat": lapsed_repeat,
            "lapsed_n_2025": len(lapsed_2025), "repeat_rate": r, "horizon_factor": factor,
            "horizon_sensitivity": pd.DataFrame(sens)}


def fit_final_model(train: pd.DataFrame, test: pd.DataFrame, chosen: str) -> dict:
    """Refit the SELECTED specification on both labelled cutoffs (2024 and 2025 targets) for scoring.
    Its validation evidence is the out-of-time test of the same specification trained on 2024 only."""
    pooled = pd.concat([train, test], ignore_index=True)
    X, y = prepare_clv_features(pooled)
    pre = build_preprocessor().fit(X)
    model = clone(candidate_models()[chosen]).fit(pre.transform(X), y)
    return {"preprocessor": pre, "model": model, "rows": len(pooled)}


# =============================================================================
# 6. SEGMENT VIEWS
# =============================================================================
def build_customer_clv_table(hist: pd.DataFrame, est: dict, D: dict) -> pd.DataFrame:
    """Historical value + estimates + Step 5 RFM + Step 6 cluster, one row per customer."""
    rfm = D["rfm"][["Customer_ID", "Recency", "Frequency", "Monetary", "R_Score", "F_Score", "M_Score",
                    "RFM_Score", "RFM_Segment", "Value_Activity_Group"]]
    ml = D["ml"][["Customer_ID", "Cluster_ID", "Cluster_Label"]]
    c = hist.merge(rfm, on="Customer_ID", how="left").merge(ml, on="Customer_ID", how="left") \
        .merge(est["scores"], on="Customer_ID", how="left")
    hv = c["Historical_Profit_CLV"].quantile(HIGH_VALUE_QUANTILE)
    ev = c["Estimated_12M_Future_Profit"].quantile(HIGH_VALUE_QUANTILE)
    c["High_Historical_Value"] = c["Historical_Profit_CLV"] >= hv
    c["High_Estimated_Future_Value"] = c["Estimated_12M_Future_Profit"] >= ev
    c["High_Value_High_Engagement"] = c["High_Historical_Value"] & (c["F_Score"] >= 4) & (c["R_Score"] >= 4)
    c["Potentially_At_Risk_High_Value"] = c["High_Historical_Value"] & (c["Recency"] >= AT_RISK_DAYS)
    c["Future_Value_Opportunity"] = c["High_Estimated_Future_Value"] & ~c["High_Historical_Value"]
    c.attrs["thresholds"] = {"historical_profit_p80": hv, "estimated_12m_p80": ev}
    return c


def _value_table(c: pd.DataFrame, key: str) -> pd.DataFrame:
    g = c.groupby(key)
    t = pd.DataFrame({
        "Customer_Count": g.size(),
        "Avg_Historical_Revenue": g["Historical_Revenue_CLV"].mean(),
        "Avg_Historical_Profit_CLV": g["Historical_Profit_CLV"].mean(),
        "Median_Historical_Profit_CLV": g["Historical_Profit_CLV"].median(),
        "Total_Historical_Profit_CLV": g["Historical_Profit_CLV"].sum(),
        "Avg_Estimated_12M_Value": g["Estimated_12M_Future_Profit"].mean(),
        "Total_Estimated_12M_Value": g["Estimated_12M_Future_Profit"].sum(),
        "Avg_Illustrative_3Y_Value": g["Illustrative_3Y_Value"].mean(),
        "Avg_AOV": g["Average_Order_Value"].mean(),
        "Avg_Frequency": g["Total_Orders"].mean(),
        "Avg_Recency_Days": g["Recency"].mean(),
        "Historical_Profit_Margin": g["Total_Profit"].sum() / g["Total_Revenue"].sum(),
        "Avg_Tenure_Months": g["Customer_Tenure_Months"].mean(),
        "Share_Scored_by_Model": g["Estimate_Method"].apply(lambda s: s.str.startswith("ML").mean()),
    })
    t["Customer_%"] = 100 * t["Customer_Count"] / t["Customer_Count"].sum()
    t["Historical_Profit_Share_%"] = 100 * t["Total_Historical_Profit_CLV"] / t["Total_Historical_Profit_CLV"].sum()
    t["Estimated_12M_Value_Share_%"] = 100 * t["Total_Estimated_12M_Value"] / t["Total_Estimated_12M_Value"].sum()
    t["Avg_Historical_Annual_Profit_Rate"] = g["Historical_Annual_Profit_Rate"].mean()
    t["Est_12M_to_Historical_Annual_Rate"] = t["Avg_Estimated_12M_Value"] / t["Avg_Historical_Annual_Profit_Rate"]
    return t


def analyze_clv_by_rfm(c: pd.DataFrame) -> pd.DataFrame:
    """Historical and estimated value per Step 5 RFM segment (fixed segment order)."""
    t = _value_table(c, "RFM_Segment")
    return t.reindex([s for s in SEGMENT_ORDER if s in t.index]).reset_index()


def analyze_clv_by_cluster(c: pd.DataFrame) -> pd.DataFrame:
    """Historical and estimated value per Step 6 K-Means cluster."""
    t = _value_table(c, "Cluster_ID").reset_index()
    lab = c.drop_duplicates("Cluster_ID").set_index("Cluster_ID")["Cluster_Label"]
    t.insert(1, "Cluster_Label", t["Cluster_ID"].map(lab))
    return t


def identify_high_value_customers(c: pd.DataFrame) -> pd.DataFrame:
    """Summary of the high-value groups (definitions are written into the table)."""
    th = c.attrs["thresholds"]
    defs = [
        ("High historical value", "High_Historical_Value",
         f"Historical profit CLV >= P80 ({inr(th['historical_profit_p80'])})"),
        ("High estimated future value", "High_Estimated_Future_Value",
         f"Estimated 12-month profit >= P80 ({inr(th['estimated_12m_p80'])})"),
        ("High value + high engagement", "High_Value_High_Engagement",
         "High historical value AND F_Score >= 4 AND R_Score >= 4 (Step 5 scores)"),
        ("Potentially at-risk high-value", "Potentially_At_Risk_High_Value",
         f"High historical value AND no purchase for >= {AT_RISK_DAYS} days (not 'churned')"),
        ("Future value opportunity", "Future_Value_Opportunity",
         "High estimated future value but NOT high historical value"),
    ]
    tot_h, tot_e = c["Historical_Profit_CLV"].sum(), c["Estimated_12M_Future_Profit"].sum()
    rows = []
    for name, col, rule in defs:
        s = c[c[col]]
        rows.append({"Group": name, "Definition": rule, "Customers": len(s), "Customer_%": 100 * len(s) / len(c),
                     "Historical_Profit": s["Historical_Profit_CLV"].sum(),
                     "Historical_Profit_Share_%": 100 * s["Historical_Profit_CLV"].sum() / tot_h,
                     "Estimated_12M_Value": s["Estimated_12M_Future_Profit"].sum(),
                     "Estimated_12M_Share_%": 100 * s["Estimated_12M_Future_Profit"].sum() / tot_e,
                     "Median_Recency_Days": s["Recency"].median(), "Median_Orders": s["Total_Orders"].median(),
                     "Top_RFM_Segments": "; ".join(f"{k} {v:.0%}" for k, v in
                                                    s["RFM_Segment"].value_counts(normalize=True).head(3).items()),
                     "Top_Clusters": "; ".join(f"{k} {v:.0%}" for k, v in
                                               s["Cluster_Label"].value_counts(normalize=True).head(2).items())})
    return pd.DataFrame(rows)


def analyze_value_drivers(c: pd.DataFrame, test: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """(a) Exact decomposition of historical profit = orders x AOV x margin (log-variance shares);
    (b) Spearman correlation of customer characteristics with historical profit;
    (c) Spearman correlation of cutoff features with FUTURE profit (test year)."""
    pos = c[c["Total_Profit"] > 0]
    lp = np.log(pos["Total_Profit"])
    parts = {"Number of orders": np.log(pos["Total_Orders"]), "Average order value": np.log(pos["Average_Order_Value"]),
             "Profit margin": np.log(pos["Historical_Profit_Margin"])}
    dec = pd.DataFrame([{"Component": k, "Share_of_log_Profit_Variance_%": 100 * np.cov(v, lp)[0, 1] / lp.var()}
                        for k, v in parts.items()])
    dec.attrs["n"] = len(pos)
    chars = {"Total_Orders": "Number of orders", "Average_Order_Value": "Average order value",
             "Categories_Bought": "Categories bought", "Customer_Tenure_Days": "Tenure (days)",
             "Recency": "Recency (days since last purchase)", "Average_Discount": "Average discount",
             "Return_Cancel_Rate": "Return/cancel rate", "Historical_Profit_Margin": "Profit margin"}
    corr = []
    for col, name in chars.items():
        r, p = stats.spearmanr(c[col], c["Historical_Profit_CLV"])
        corr.append({"Characteristic": name, "Spearman_with_Historical_Profit": r, "p_value": p})
    fut = []
    for col in CANDIDATE_FEATURES:
        r, p = stats.spearmanr(test[col], test[TARGET])
        fut.append({"Feature_at_Cutoff": col, "Spearman_with_Future_12M_Profit": r, "p_value": p})
    return {"decomposition": dec, "historical": pd.DataFrame(corr),
            "future": pd.DataFrame(fut).sort_values("Spearman_with_Future_12M_Profit", key=abs, ascending=False)}


# =============================================================================
# 7. INSIGHTS, QUESTIONS, VALIDATION
# =============================================================================
def clv_assumptions(R: dict) -> pd.DataFrame:
    """Every assumption the CLV numbers depend on, in one table."""
    e = R["estimates"]
    rows = [
        ("Revenue rule", "Only Delivered lines count as revenue, cost and profit (Step 3 rule); Returned/Cancelled = 0."),
        ("Customer population", f"{len(R['clv']):,} customers with >= 1 Delivered order; the 16 customers with no "
                                "Delivered order have no value to measure (same population as Step 5)."),
        ("Reference date", f"{R['reference_date'].date()} (latest order date + 1 day, Step 5)."),
        ("Historical CLV", "Observed 2023-2025 totals. Not a forecast; tenure is left-censored for customers "
                           "who existed before 2023, so their historical value is a minimum."),
        ("Future-value target", f"{TARGET}: Delivered profit in the {HORIZON_MONTHS} months after a cutoff."),
        ("Feature window", f"{LOOKBACK_MONTHS} months before the cutoff (same length at every cutoff so the "
                           "training and test features are comparable)."),
        ("Tenure feature", f"Capped at {TENURE_CAP_DAYS} days because the training cutoff only has 12 months of history."),
        ("Model population", "Customers with >= 1 Delivered order in the 12 months before the cutoff."),
        ("Model features", f"{len(MODEL_FEATURES)} features after removing exact identities and VIF > "
                           f"{MAX_VIF:.0f}: " + ", ".join(MODEL_FEATURES) + "."),
        ("Customers outside the model population",
         f"Given the observed average next-12-month profit of the equivalent group at the 2025 cutoff "
         f"({inr(e['lapsed_value'])}, n = {e['lapsed_n_2025']}); a group-level estimate, not customer-specific."),
        ("Stationarity", "The estimate assumes next year behaves like the training years. Activity grew in 2025, "
                         "and the out-of-time test shows the model under-estimates totals (see bias ratio)."),
        ("Illustrative 3-year value", f"12-month estimate x (1 + r + r^2) with r = pooled observed annual repeat "
                                      f"rate {e['repeat_rate']:.3f}; no discounting (no cost of capital is "
                                      "available for the company); NOT validated."),
        ("Inactivity", f">= {AT_RISK_DAYS} days without a purchase = 'potentially at-risk', never 'churned' "
                       "(many such customers bought again - see sensitivity table)."),
        ("Probabilistic models", "BG/NBD fitted and tested as a benchmark; Gamma-Gamma rejected because spend and "
                                 "frequency are correlated."),
        ("Predictions floored at zero", "Negative model outputs are set to ₹0 (a customer's expected purchases cannot be negative)."),
        ("Synthetic data", config.DATASET_LABEL),
    ]
    return pd.DataFrame(rows, columns=["Assumption", "Detail"])


def answer_clv_questions(R: dict) -> pd.DataFrame:
    """The eight Step 7 objective questions, answered from the computed tables."""
    c, dist, hv = R["clv"], R["distribution"], R["high_value"].set_index("Group")
    conc = dist["concentration"].set_index("Top_Customers_%")
    byc, byr = R["by_cluster"], R["by_rfm"]
    m = R["evaluation"]["metrics"]
    s_sum = dist["summary"].set_index("Measure")
    top_c = byc.sort_values("Avg_Historical_Profit_CLV", ascending=False).iloc[0]
    low_c = byc.sort_values("Avg_Historical_Profit_CLV").iloc[0]
    top_r = byr.sort_values("Avg_Historical_Profit_CLV", ascending=False).iloc[0]
    low_r = byr.sort_values("Avg_Historical_Profit_CLV").iloc[0]
    dec = R["drivers"]["decomposition"].set_index("Component")["Share_of_log_Profit_Variance_%"]
    imp = R["importance"].iloc[0]
    rows = [
        ("What is the current/historical value of each customer?",
         f"Stored per customer in customer_value_history.csv. Across {len(c):,} customers: historical revenue "
         f"{inr(s_sum.loc['Historical revenue', 'Total'])}, historical profit {inr(s_sum.loc['Historical profit', 'Total'])}; "
         f"median profit per customer {inr(s_sum.loc['Historical profit', 'Median'])} vs mean "
         f"{inr(s_sum.loc['Historical profit', 'Mean'])}."),
        ("Which customers generate the highest value?",
         f"The top 20% of customers by historical profit ({int(conc.loc[20, 'Customers'])}) generated "
         f"{conc.loc[20, 'Profit_Share_%']:.1f}% of all profit; the top 10% generated {conc.loc[10, 'Profit_Share_%']:.1f}%. "
         f"By RFM segment the top 20% are: {hv.loc['High historical value', 'Top_RFM_Segments']}."),
        ("How does customer value differ across ML clusters?",
         f"Average historical profit ranges from {inr(low_c['Avg_Historical_Profit_CLV'])} "
         f"(Cluster {low_c['Cluster_ID']}: {low_c['Cluster_Label']}) to {inr(top_c['Avg_Historical_Profit_CLV'])} "
         f"(Cluster {top_c['Cluster_ID']}: {top_c['Cluster_Label']}), which holds "
         f"{top_c['Historical_Profit_Share_%']:.1f}% of historical profit and {top_c['Estimated_12M_Value_Share_%']:.1f}% "
         f"of estimated 12-month value."),
        ("How does customer value differ across RFM segments?",
         f"Highest average historical profit: {top_r['RFM_Segment']} ({inr(top_r['Avg_Historical_Profit_CLV'])}); "
         f"lowest: {low_r['RFM_Segment']} ({inr(low_r['Avg_Historical_Profit_CLV'])})."),
        ("What factors are associated with higher customer value?",
         f"Historical profit = orders x AOV x margin; the number of orders accounts for {dec['Number of orders']:.0f}% of the "
         f"variance in log profit, AOV {dec['Average order value']:.0f}%, margin {dec['Profit margin']:.0f}% (margins "
         f"differ little between customers). For FUTURE value, "
         f"the most important model feature is {imp['Feature']} (permutation importance). These are associations, not causes."),
        ("Which customers have high historical value?",
         f"{int(hv.loc['High historical value', 'Customers'])} customers (historical profit >= P80); "
         f"{int(hv.loc['High value + high engagement', 'Customers'])} of them are also frequent and recent; "
         f"{int(hv.loc['Potentially at-risk high-value', 'Customers'])} have not bought for >= {AT_RISK_DAYS} days."),
        ("Which customers may represent future value opportunities?",
         f"{int(hv.loc['Future value opportunity', 'Customers'])} customers are in the top 20% of estimated 12-month value "
         f"without being in the top 20% of historical value (flag Future_Value_Opportunity). The estimate is "
         f"approximate: out-of-time R² {m['R2']:.2f}, and the top 20% predicted captured {m['Top20_Capture_%']:.0f}% of "
         f"actual next-year profit in the test."),
        ("How can CLV support retention and marketing decisions?",
         "Historical profit CLV identifies whom the business depends on today; the estimated 12-month value and the "
         "at-risk flag show where value may be lost or gained next. Both can size and prioritise retention "
         "effort (final recommendations are a later step)."),
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer"])


def generate_clv_insights(R: dict) -> pd.DataFrame:
    """Insight table with the columns required by the brief; every number is computed above."""
    dist, hv = R["distribution"], R["high_value"].set_index("Group")
    conc = dist["concentration"].set_index("Top_Customers_%")
    byr, byc = R["by_rfm"].set_index("RFM_Segment"), R["by_cluster"]
    m, single = R["evaluation"]["metrics"], dist["single_purchase"].set_index("Is_Single_Purchase")
    s = dist["summary"].set_index("Measure")
    ten = R["tenure_value"]
    c0 = byc.sort_values("Avg_Historical_Profit_CLV", ascending=False).iloc[0]
    c_up = byc.sort_values("Est_12M_to_Historical_Annual_Rate", ascending=False).iloc[0]
    top2 = byc.sort_values("Estimated_12M_Value_Share_%", ascending=False).head(2)
    top_r = byr.sort_values("Avg_Estimated_12M_Value", ascending=False).iloc[0]
    slow = byr.sort_values("Est_12M_to_Historical_Annual_Rate").iloc[0]
    cal = R["evaluation"]["calibration"].set_index("Predicted_Decile")
    rows = [
        ("High-Value Customers",
         f"Top 20% of customers generated {conc.loc[20, 'Profit_Share_%']:.1f}% of historical profit",
         f"{int(conc.loc[20, 'Customers'])} customers; Gini (profit) {dist['gini']['Total_Profit']:.2f}; mean/median "
         f"profit ratio {s.loc['Historical profit', 'Mean_to_Median']:.2f}; skewness {s.loc['Historical profit', 'Skewness']:.2f}",
         "Customer value is concentrated: averages overstate the typical customer, so medians and "
         "percentiles are reported alongside means."),
        ("High-Value Customers",
         f"{int(hv.loc['Potentially at-risk high-value', 'Customers'])} high-value customers have not bought "
         f"for >= {AT_RISK_DAYS} days",
         f"They hold {hv.loc['Potentially at-risk high-value', 'Historical_Profit_Share_%']:.1f}% of historical profit; "
         f"median recency {hv.loc['Potentially at-risk high-value', 'Median_Recency_Days']:.0f} days",
         "Potentially at-risk, not churned: at the 2025 cutoff "
         f"{R['inactivity_180_2025']:.0f}% of customers inactive >= {AT_RISK_DAYS} days bought again within 12 months."),
        ("RFM Segments",
         f"{top_r.name} have the highest average estimated 12-month value ({inr(top_r['Avg_Estimated_12M_Value'])}), "
         f"close to their historical annual rate ({inr(top_r['Avg_Historical_Annual_Profit_Rate'])})",
         f"{int(top_r['Customer_Count'])} customers = {top_r['Historical_Profit_Share_%']:.1f}% of historical profit and "
         f"{top_r['Estimated_12M_Value_Share_%']:.1f}% of estimated 12-month value",
         "The segment that generated most past value is also estimated to generate the most near-term value. Its "
         "share is lower on the estimate partly because the model pulls extreme customers toward the average (test top "
         f"decile: predicted {inr(cal.loc[10, 'Mean_Predicted'])} vs actual {inr(cal.loc[10, 'Mean_Actual'])})."),
        ("RFM Segments",
         f"{slow.name}: estimated 12-month value is {slow['Est_12M_to_Historical_Annual_Rate']:.2f}x their historical "
         "annual profit rate - the lowest ratio of any segment",
         f"{int(slow['Customer_Count'])} customers; average historical profit {inr(slow['Avg_Historical_Profit_CLV'])}; "
         f"estimated {inr(slow['Avg_Estimated_12M_Value'])} vs annual rate {inr(slow['Avg_Historical_Annual_Profit_Rate'])}; "
         f"average recency {slow['Avg_Recency_Days']:.0f} days",
         "Historical value alone would overstate what this group is estimated to contribute next year."),
        ("ML Clusters",
         f"Clusters {top2['Cluster_ID'].iloc[0]} and {top2['Cluster_ID'].iloc[1]} hold "
         f"{top2['Estimated_12M_Value_Share_%'].sum():.1f}% of estimated 12-month value",
         "; ".join(f"Cluster {r['Cluster_ID']} ({r['Cluster_Label']}): {r['Customer_%']:.1f}% of customers, "
                   f"{r['Historical_Profit_Share_%']:.1f}% of historical profit, {r['Estimated_12M_Value_Share_%']:.1f}% "
                   "of estimated value" for _, r in top2.iterrows()),
         f"Cluster {c0['Cluster_ID']} has by far the highest value per customer ({inr(c0['Avg_Estimated_12M_Value'])} "
         "estimated); the lapsing mid-value cluster matters because of its size."),
        ("ML Clusters",
         f"Cluster {c_up['Cluster_ID']} ({c_up['Cluster_Label']}) has the highest estimated-to-historical ratio "
         f"({c_up['Est_12M_to_Historical_Annual_Rate']:.2f}x)",
         f"Average estimated 12-month value {inr(c_up['Avg_Estimated_12M_Value'])} vs historical annual rate "
         f"{inr(c_up['Avg_Historical_Annual_Profit_Rate'])}; average tenure {c_up['Avg_Tenure_Months']:.0f} months",
         "Recently active, low-value customers are estimated to be worth more next year than their short history "
         "shows - partly model shrinkage toward the average, so treat as a ranking signal, not a forecast."),
        ("Customer Tenure",
         f"Longer-tenure customers have higher historical profit (Spearman {ten['rho']:.2f})",
         f"Median profit: tenure < 1 year {inr(ten['lt1'])}, 1-2 years {inr(ten['1to2'])}, >= 2 years {inr(ten['ge2'])}; "
         f"{pct(ten['censored'])} of customers have left-censored tenure",
         "Part of this is exposure (more time to buy), so tenure is not by itself evidence of loyalty."),
        ("Customer Tenure",
         f"{int(single.loc['Single purchase', 'Customers'])} single-purchase customers "
         f"({single.loc['Single purchase', 'Customer_Share_%']:.1f}%) hold "
         f"{single.loc['Single purchase', 'Profit_Share_%']:.1f}% of profit",
         f"Median profit {inr(single.loc['Single purchase', 'Median_Profit'])} vs "
         f"{inr(single.loc['Repeat purchasers', 'Median_Profit'])} for repeat purchasers",
         "Most value comes from repeat purchasing; a second purchase is the key step."),
        ("Profitability",
         f"Historical profit margin {pct(s.loc['Historical profit', 'Total'] / s.loc['Historical revenue', 'Total'])} overall",
         f"Historical profit {inr(s.loc['Historical profit', 'Total'])} on revenue {inr(s.loc['Historical revenue', 'Total'])}; "
         f"{int(s.loc['Historical profit', 'Customers_below_zero'])} customers have negative total profit",
         "Profit CLV is the more economically meaningful measure; revenue CLV is kept for comparison."),
        ("Future Value",
         f"Out-of-time test (2024 features -> 2025 profit): R² {m['R2']:.2f}, MAE {inr(m['MAE'])}",
         f"Top 20% predicted captured {m['Top20_Capture_%']:.1f}% of actual 2025 profit; predicted/actual total "
         f"{m['Predicted_to_Actual_Total']:.2f}; Spearman {m['Spearman']:.2f}",
         "Useful for ranking customers by expected value; individual rupee estimates are approximate and "
         "totals are conservative when activity grows."),
    ]
    return pd.DataFrame(rows, columns=["Insight Area", "Observation", "Evidence", "Business Interpretation"])


def validate_clv(R: dict) -> pd.DataFrame:
    """Reconciliation, leakage, time integrity, reproducibility and metric checks."""
    D, h, c = R["data"], R["history"], R["clv"]
    d = D["delivered"]
    checks = []

    def add(name, value, ok):
        checks.append({"Check": name, "Value": value, "Pass": bool(ok)})

    rfm_ids = set(D["rfm"]["Customer_ID"])
    add("One row per customer (no duplicate IDs)", int(h["Customer_ID"].duplicated().sum()),
        not h["Customer_ID"].duplicated().any())
    add("Customers = valid population (>= 1 Delivered order) = Step 5 RFM",
        f"{len(h):,} vs {d['Customer_ID'].nunique():,} vs {len(rfm_ids):,}",
        len(h) == d["Customer_ID"].nunique() == len(rfm_ids) and set(h["Customer_ID"]) == rfm_ids)
    add("Revenue reconciles with cleaned Delivered sales", f"{inr(h['Total_Revenue'].sum())} vs {inr(d['Sales'].sum())}",
        np.isclose(h["Total_Revenue"].sum(), d["Sales"].sum()))
    add("Profit reconciles with cleaned Delivered profit", f"{inr(h['Total_Profit'].sum())} vs {inr(d['Profit'].sum())}",
        np.isclose(h["Total_Profit"].sum(), d["Profit"].sum()))
    add("Revenue - cost = profit for every customer", "all customers",
        np.allclose(h["Total_Revenue"] - h["Total_Cost"], h["Total_Profit"], atol=0.01))
    r = D["rfm"].set_index("Customer_ID").reindex(h["Customer_ID"])
    add("Orders and revenue match Step 5 Frequency / Monetary", "per customer",
        np.array_equal(r["Frequency"].to_numpy(), h["Total_Orders"].to_numpy())
        and np.allclose(r["Monetary"].to_numpy(), h["Total_Revenue"].to_numpy(), atol=0.01))
    add("Tenure non-negative; first <= last <= reference date",
        f"min tenure {h['Customer_Tenure_Days'].min()} d",
        (h["Customer_Tenure_Days"] >= 0).all() and (h["First_Purchase_Date"] <= h["Last_Purchase_Date"]).all()
        and (h["Last_Purchase_Date"] < R["reference_date"]).all())
    tr, te = R["train"], R["test"]
    add("No leakage: every feature date < cutoff (train & test)",
        f"train max {tr.attrs['max_feature_date'].date()}, test max {te.attrs['max_feature_date'].date()}",
        tr.attrs["max_feature_date"] < TRAIN_CUTOFF and te.attrs["max_feature_date"] < TEST_CUTOFF)
    add("Time integrity: target dates >= cutoff; training target window ends before test target window",
        f"train target from {tr.attrs['min_target_date'].date()}, test target from {te.attrs['min_target_date'].date()}",
        tr.attrs["min_target_date"] >= TRAIN_CUTOFF and te.attrs["min_target_date"] >= TEST_CUTOFF
        and TRAIN_CUTOFF + pd.DateOffset(months=HORIZON_MONTHS) <= TEST_CUTOFF)
    banned = {"RFM_Segment", "Cluster_ID", "R_Score", "F_Score", "M_Score", "Monetary", TARGET,
              "Future_Revenue_12M", "Future_Orders_12M", "Customer_ID"}
    add("No leakage: no target, RFM/cluster label or ID among model features", ", ".join(MODEL_FEATURES[:3]) + ", ...",
        not banned & set(MODEL_FEATURES))
    add("Target window exists in the data (no invented future)",
        f"test target ends {(TEST_CUTOFF + pd.DateOffset(months=HORIZON_MONTHS) - pd.Timedelta(days=1)).date()}",
        TEST_CUTOFF + pd.DateOffset(months=HORIZON_MONTHS) <= R["reference_date"])
    fs = R["feature_selection"]
    add("Feature selection reproduces MODEL_FEATURES; final VIF <= 5",
        f"max VIF {fs['table']['VIF_Final_Set'].max():.2f}",
        fs["selected"] == MODEL_FEATURES and fs["table"]["VIF_Final_Set"].max() <= MAX_VIF)
    again = train_clv_model(tr)
    X, _ = prepare_clv_features(te)
    p1 = again["models"][again["chosen"]].predict(again["preprocessor"].transform(X))
    p0 = R["trained"]["models"][R["trained"]["chosen"]].predict(R["trained"]["preprocessor"].transform(X))
    add("Reproducible: refit with fixed random_state gives identical predictions", f"random_state={SEED}",
        again["chosen"] == R["trained"]["chosen"] and np.allclose(p0, p1))
    tp = R["evaluation"]["test_predictions"]
    mm = _metrics(tp["Actual_Future_Profit_12M"], tp["Predicted_Future_Profit_12M"])
    add("Reported metrics recomputed from saved test predictions", f"R² {mm['R2']:.4f}",
        np.isclose(mm["R2"], R["evaluation"]["metrics"]["R2"]) and np.isclose(mm["MAE"], R["evaluation"]["metrics"]["MAE"]))
    add("Every customer has one estimate and a method label; estimates >= 0",
        f"{c['Estimated_12M_Future_Profit'].notna().sum():,} estimates",
        c["Estimated_12M_Future_Profit"].notna().all() and (c["Estimated_12M_Future_Profit"] >= 0).all()
        and c["Estimate_Method"].notna().all() and len(c) == len(h))
    add("CLV by RFM and by cluster reconcile with the customer total",
        inr(c["Historical_Profit_CLV"].sum()),
        np.isclose(R["by_rfm"]["Total_Historical_Profit_CLV"].sum(), c["Historical_Profit_CLV"].sum())
        and np.isclose(R["by_cluster"]["Total_Historical_Profit_CLV"].sum(), c["Historical_Profit_CLV"].sum())
        and np.isclose(R["by_cluster"]["Total_Estimated_12M_Value"].sum(), c["Estimated_12M_Future_Profit"].sum()))
    add("Every assumption documented", f"{len(R['assumptions'])} assumptions in clv_assumptions.csv",
        len(R["assumptions"]) >= 10)
    return pd.DataFrame(checks)


# =============================================================================
# 8. ORCHESTRATION + SAVING
# =============================================================================
def run_clv_analysis() -> dict:
    """Run every analysis step and return a results dictionary R."""
    D = load_customer_data()
    ref = D["reference_date"]
    value = calculate_historical_customer_value(D["tx"])
    tenure = calculate_customer_tenure(D["delivered"], ref, D["rfm"])
    hist = calculate_customer_profitability(value, tenure)
    dist = analyze_value_distribution(hist)
    inact = analyze_inactivity_thresholds(D["delivered"])
    readiness = check_clv_data_readiness(hist, D["delivered"], inact)
    bg = evaluate_probabilistic_clv(D["delivered"])
    train = build_predictive_clv_dataset(D["tx"], TRAIN_CUTOFF)
    test = build_predictive_clv_dataset(D["tx"], TEST_CUTOFF)
    feature_selection = select_model_features(train)
    trained = train_clv_model(train)
    evaluation = evaluate_clv_model(trained, train, test, bg)
    importance = calculate_feature_importance(trained, test)
    rates = annual_repeat_rates(D["delivered"])
    final = fit_final_model(train, test, trained["chosen"])
    estimates = estimate_customer_value(D, hist, final, evaluation["repeat_prob"], rates)
    clv = build_customer_clv_table(hist, estimates, D)
    R = {"data": D, "reference_date": ref, "history": hist, "distribution": dist, "inactivity": inact,
         "readiness": readiness, "bgnbd": bg, "feature_selection": feature_selection, "train": train, "test": test, "trained": trained,
         "evaluation": evaluation, "importance": importance, "rates": rates, "final": final,
         "estimates": estimates, "clv": clv}
    R["by_rfm"] = analyze_clv_by_rfm(clv)
    R["by_cluster"] = analyze_clv_by_cluster(clv)
    R["high_value"] = identify_high_value_customers(clv)
    R["drivers"] = analyze_value_drivers(clv, test)
    t = clv["Customer_Tenure_Days"]
    R["tenure_value"] = {"rho": stats.spearmanr(t, clv["Historical_Profit_CLV"])[0],
                         "lt1": clv.loc[t < 365, "Historical_Profit_CLV"].median(),
                         "1to2": clv.loc[(t >= 365) & (t < 730), "Historical_Profit_CLV"].median(),
                         "ge2": clv.loc[t >= 730, "Historical_Profit_CLV"].median(),
                         "censored": clv["Tenure_Left_Censored"].mean()}
    sens = inact["sensitivity"]
    R["inactivity_180_2025"] = float(sens[(sens["Threshold_Days"] == AT_RISK_DAYS)
                                          & (sens["Cutoff"] == TEST_CUTOFF.date().isoformat())]["Bought_Again_Next_12M_%"].iloc[0])
    R["assumptions"] = clv_assumptions(R)
    R["questions"] = answer_clv_questions(R)
    R["insights"] = generate_clv_insights(R)
    R["validation"] = validate_clv(R)
    return R


def _dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("First_Purchase_Date", "Last_Purchase_Date"):
        if col in df:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
    return df


def save_clv_outputs(R: dict) -> list[Path]:
    """Save customer-level data, tables, model artefacts and metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    hist_cols = ["Customer_ID", "Total_Revenue", "Total_Cost", "Total_Profit", "Total_Orders", "Total_Quantity",
                 "Average_Order_Value", "Average_Order_Profit", "Average_Discount", "First_Purchase_Date",
                 "Last_Purchase_Date", "Customer_Tenure_Days", "Customer_Tenure_Months", "Active_Span_Days",
                 "Is_Single_Purchase", "Acquisition_Status", "Tenure_Left_Censored", "Order_Lines",
                 "Categories_Bought", "Returned_Lines", "Cancelled_Lines", "Return_Cancel_Rate",
                 "Historical_Revenue_CLV", "Historical_Profit_CLV", "Historical_Profit_Margin",
                 "Historical_Annual_Profit_Rate", "Historical_Profit_Percentile", "Historical_Value_Decile"]
    h = _dates(R["history"][hist_cols]).round(4)
    h.to_csv(VALUE_HISTORY_FILE, index=False, encoding="utf-8-sig")
    paths.append(VALUE_HISTORY_FILE)

    clv_cols = ["Customer_ID", "Historical_Revenue_CLV", "Historical_Profit_CLV", "Historical_Profit_Margin",
                "Total_Orders", "Average_Order_Value", "Customer_Tenure_Days", "Recency", "RFM_Segment",
                "Cluster_ID", "Cluster_Label", "Estimate_Method", "Estimated_12M_Future_Profit",
                "Simplified_12M_Estimate", "Illustrative_3Y_Value", "High_Historical_Value",
                "High_Estimated_Future_Value", "High_Value_High_Engagement", "Potentially_At_Risk_High_Value",
                "Future_Value_Opportunity"]
    R["clv"][clv_cols].round(2).to_csv(CLV_FILE, index=False, encoding="utf-8-sig")
    paths.append(CLV_FILE)

    panel = pd.concat([R["train"].assign(Role="train"), R["test"].assign(Role="test (out-of-time)"),
                       R["estimates"]["scoring_panel"].assign(Role="scoring (no target yet)")], ignore_index=True)
    panel.round(4).to_csv(MODELING_FILE, index=False, encoding="utf-8-sig")
    paths.append(MODELING_FILE)

    dist = R["distribution"]
    ev = R["evaluation"]
    tables = {
        "clv_value_distribution.csv": dist["summary"],
        "clv_value_percentiles.csv": dist["percentiles"],
        "clv_value_concentration.csv": dist["concentration"],
        "clv_single_purchase_customers.csv": dist["single_purchase"],
        "clv_data_readiness.csv": R["readiness"],
        "clv_interpurchase_gaps.csv": R["inactivity"]["gaps"],
        "clv_inactivity_threshold_sensitivity.csv": R["inactivity"]["sensitivity"],
        "clv_annual_repeat_rates.csv": R["rates"],
        "clv_bgnbd_evaluation.csv": R["bgnbd"]["evaluation"],
        "clv_feature_selection.csv": R["feature_selection"]["table"],
        "clv_model_cv_selection.csv": R["trained"]["cv"],
        "clv_model_comparison.csv": ev["comparison"],
        "clv_test_predictions.csv": ev["test_predictions"],
        "clv_calibration_by_decile.csv": ev["calibration"],
        "clv_feature_importance.csv": R["importance"],
        "clv_value_drivers.csv": R["drivers"]["historical"],
        "clv_profit_decomposition.csv": R["drivers"]["decomposition"],
        "clv_future_value_correlations.csv": R["drivers"]["future"],
        "clv_horizon_sensitivity.csv": R["estimates"]["horizon_sensitivity"],
        "clv_by_rfm_segment.csv": R["by_rfm"],
        "clv_by_ml_cluster.csv": R["by_cluster"],
        "clv_high_value_groups.csv": R["high_value"],
        "clv_assumptions.csv": R["assumptions"],
        "clv_business_questions.csv": R["questions"],
        "clv_business_insights.csv": R["insights"],
        "clv_validation_checks.csv": R["validation"],
    }
    for name, df in tables.items():
        p = config.TABLES_DIR / name
        df.round(4).to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)

    joblib.dump(R["final"]["preprocessor"], PREPROCESSOR_FILE)
    joblib.dump(R["final"]["model"], MODEL_FILE)
    m = ev["metrics"]
    meta = {
        "dataset": config.DATASET_LABEL,
        "purpose": "Estimate each customer's Delivered PROFIT in the next 12 months (an estimate, not a guarantee)",
        "target": TARGET, "feature_order": MODEL_FEATURES,
        "skewed_features_arcsinh": [f for f in MODEL_FEATURES if f in SKEWED_FEATURES],
        "feature_window_months": LOOKBACK_MONTHS, "target_window_months": HORIZON_MONTHS,
        "population": "customers with >= 1 Delivered order in the 12 months before the cutoff",
        "selected_model": R["trained"]["chosen"],
        "estimator": repr(R["final"]["model"]),
        "selection_rule": "lowest mean 5-fold CV RMSE on the training cutoff (test year not used)",
        "validation": {"type": "out-of-time", "train": "features 2023 -> target 2024",
                       "test": "features 2024 -> target 2025",
                       **{k: round(float(m[k]), 4) for k in ("MAE", "RMSE", "R2", "WAPE_%", "MAPE_nonzero_%",
                                                              "Spearman", "Top20_Capture_%",
                                                              "Predicted_to_Actual_Total")}},
        "final_fit": f"same specification refit on train + test panels ({R['final']['rows']:,} rows) for scoring",
        "scoring_cutoff": R["reference_date"].date().isoformat(),
        "predictions_floored_at_zero": True,
        "sklearn_version": sklearn.__version__,
        "reload_example": ("import joblib, pandas as pd; pre = joblib.load('models/clv_preprocessor.pkl'); "
                           "m = joblib.load('models/clv_model.pkl'); "
                           "X = pd.read_csv('data/processed/clv_modeling_dataset.csv'); "
                           "X = X[X.Role.str.startswith('scoring')]; "
                           "est = m.predict(pre.transform(X[pre.feature_names_in_])).clip(0)"),
    }
    MODEL_METADATA_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    paths += [PREPROCESSOR_FILE, MODEL_FILE, MODEL_METADATA_FILE]
    return paths


def verify_saved_artefacts(R: dict) -> bool:
    """Reload the .pkl files from disk and check they reproduce the saved estimates."""
    pre, model = joblib.load(PREPROCESSOR_FILE), joblib.load(MODEL_FILE)
    X, _ = prepare_clv_features(R["estimates"]["scoring_panel"])
    p = np.clip(model.predict(pre.transform(X)), 0, None)
    s = R["estimates"]["scores"]
    s = s[s["Estimate_Method"].str.startswith("ML")]
    return bool(np.allclose(p, s["Estimated_12M_Future_Profit"].to_numpy()))


def run_clv(make_plots: bool = True, verbose: bool = True) -> dict:
    """Full Step 7 run: analysis -> outputs -> artefact reload check -> figures -> report."""
    R = run_clv_analysis()
    paths = save_clv_outputs(R)
    ok = verify_saved_artefacts(R)
    R["validation"] = pd.concat([R["validation"], pd.DataFrame([{
        "Check": "Saved model + preprocessor (reloaded from models/) reproduce the estimates",
        "Value": "clv_model.pkl, clv_preprocessor.pkl", "Pass": ok}])], ignore_index=True)
    R["validation"].to_csv(config.TABLES_DIR / "clv_validation_checks.csv", index=False, encoding="utf-8-sig")
    R["saved"] = paths
    if make_plots:
        R["figures"] = plot_clv_figures(R)
    R["report"] = write_clv_report(R)
    if verbose:
        m = R["evaluation"]["metrics"]
        print(R["validation"].to_string(index=False))
        print(f"\nSelected model: {R['trained']['chosen']} | out-of-time R² {m['R2']:.3f} | MAE {m['MAE']:,.0f}")
        print(f"Files saved: {len(paths)} | Figures: {len(R.get('figures', []))} | Report: "
              f"{R['report'].relative_to(config.PROJECT_ROOT)}")
    return R


# =============================================================================
# 9. FIGURES
# =============================================================================
def _boxes(ax, groups, labels, color):
    bp = ax.boxplot(groups, vert=False, showfliers=False, widths=0.6, patch_artist=True,
                    medianprops={"color": "#0b0b0b", "linewidth": 1.4})
    for b in bp["boxes"]:
        b.set(facecolor=color, alpha=0.55, edgecolor=color)
    ax.set_yticks(range(1, len(labels) + 1), labels)
    ax.grid(axis="y", visible=False)
    return bp


def plot_clv_figures(R: dict, out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    """All Step 7 charts. Historical (observed) values are blue; estimates are orange."""
    from matplotlib.ticker import FuncFormatter
    from src.eda import PAL, _hbar, _note, _pct_axis, _rupee, _save, _style
    from src.segmentation import CLUSTER_COLORS
    plt = _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    c = R["clv"]
    HIST, EST = PAL["blue"], PAL["orange"]
    kfmt = FuncFormatter(lambda v, _: f"₹{v / 1000:,.0f}k" if abs(v) >= 1000 else f"₹{v:,.0f}")

    # 1 distribution + boxplots ------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13, 6.6), gridspec_kw={"height_ratios": [3, 1.1]})
    for j, (col, name) in enumerate((("Historical_Revenue_CLV", "Historical revenue per customer"),
                                     ("Historical_Profit_CLV", "Historical profit per customer"))):
        v = c[col]
        pos = v[v > 0]
        bins = np.logspace(np.log10(pos.min()), np.log10(pos.max()), 45)
        ax, bx = axes[0, j], axes[1, j]
        ax.hist(pos, bins=bins, color=HIST, edgecolor="white", linewidth=0.5)
        ax.set_xscale("log")
        for val, lab, ls in ((v.median(), "median", "-"), (v.mean(), "mean", "--")):
            ax.axvline(val, color=PAL["text"], linestyle=ls, linewidth=1)
            ax.text(val, ax.get_ylim()[1] * (0.95 if lab == "median" else 0.85), f" {lab} {inr(val)}",
                    fontsize=8.5, color=PAL["text"])
        ax.set_title(f"{name} (₹, log scale)")
        ax.set_ylabel("Customers")
        extra = (f"\n{int((v <= 0).sum())} customers with profit <= 0\nnot shown on the log axis"
                 if (v <= 0).any() else "")
        ax.text(0.02, 0.95, f"skewness {stats.skew(v):.2f}{extra}", transform=ax.transAxes, va="top",
                ha="left", fontsize=8.5, color=PAL["muted"])
        _boxes(bx, [pos], [""], HIST)
        bx.set_xscale("log")
        bx.set_xlim(ax.get_xlim())
        for q in (0.10, 0.50, 0.90, 0.99):
            bx.text(v.quantile(q), 1.42, f"P{int(q * 100)}\n{inr(v.quantile(q))}", ha="center", fontsize=7.5,
                    color=PAL["muted"])
        bx.set_ylim(0.5, 1.9)
        for a_ in (ax, bx):
            a_.xaxis.set_major_formatter(kfmt)
        bx.set_xlabel("₹ per customer, 2023-2025 (box = P25-P75, whiskers = 1.5 IQR)")
    fig.suptitle("Observed customer value is right-skewed: a minority of customers carry most of it",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "clv_distribution.png", out_dir, saved)

    # 2 concentration -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for col, lab, colr in (("Historical_Revenue_CLV", "Revenue", HIST), ("Historical_Profit_CLV", "Profit", EST)):
        v = np.sort(c[col].to_numpy())[::-1]
        x = np.arange(1, len(v) + 1) / len(v)
        y = np.cumsum(v) / v.sum()
        ax.plot(x, y, color=colr, linewidth=2, label=f"{lab} (Gini {R['distribution']['gini']['Total_' + lab]:.2f})")
    ax.plot([0, 1], [0, 1], color=PAL["neutral"], linestyle=":", linewidth=1, label="Equal value per customer")
    conc = R["distribution"]["concentration"].set_index("Top_Customers_%")
    ax.axvline(0.2, color=PAL["muted"], linewidth=0.8, linestyle="--")
    ax.annotate(f"Top 20% of customers:\n{conc.loc[20, 'Revenue_Share_%']:.1f}% of revenue\n"
                f"{conc.loc[20, 'Profit_Share_%']:.1f}% of profit", (0.2, conc.loc[20, 'Profit_Share_%'] / 100),
                xytext=(0.32, 0.38), fontsize=9, arrowprops={"arrowstyle": "-", "color": PAL["muted"]})
    _pct_axis(ax, "x")
    _pct_axis(ax, "y")
    ax.set_xlabel("Share of customers (ranked from highest value)")
    ax.set_ylabel("Cumulative share of historical value")
    ax.set_title("Concentration of historical customer value")
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "clv_value_concentration.png", out_dir, saved)

    # 3 revenue vs profit --------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    neg = c["Historical_Profit_CLV"] < 0
    ax.scatter(c.loc[~neg, "Historical_Revenue_CLV"], c.loc[~neg, "Historical_Profit_CLV"], s=9, alpha=0.45,
               color=HIST, label="Customers", linewidths=0)
    ax.scatter(c.loc[neg, "Historical_Revenue_CLV"], c.loc[neg, "Historical_Profit_CLV"], s=16, color=EST,
               label=f"Negative total profit ({int(neg.sum())})", linewidths=0)
    m_all = c["Historical_Profit_CLV"].sum() / c["Historical_Revenue_CLV"].sum()
    xs = np.array([0, c["Historical_Revenue_CLV"].max()])
    ax.plot(xs, xs * m_all, color=PAL["text"], linestyle="--", linewidth=1, label=f"Overall margin {m_all:.1%}")
    ax.axhline(0, color=PAL["muted"], linewidth=0.8)
    for a_ in ("x", "y"):
        (ax.xaxis if a_ == "x" else ax.yaxis).set_major_formatter(kfmt)
    r_ = stats.spearmanr(c["Historical_Revenue_CLV"], c["Historical_Profit_CLV"])[0]
    ax.set_xlabel("Historical revenue (₹)")
    ax.set_ylabel("Historical profit (₹)")
    ax.set_title(f"Revenue vs profit by customer (Spearman {r_:.2f})")
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "clv_revenue_vs_profit.png", out_dir, saved)

    # 4 tenure vs value ----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (flag, title) in zip(axes, ((False, "Acquired 2023-2025 (tenure fully observed)"),
                                        (True, "Existing before 2023 (tenure left-censored)"))):
        d_ = c[c["Tenure_Left_Censored"] == flag]
        ax.scatter(d_["Customer_Tenure_Months"], d_["Historical_Profit_CLV"], s=8, alpha=0.35, color=HIST,
                   linewidths=0)
        bins = np.arange(0, 39, 3)
        med = d_.groupby(pd.cut(d_["Customer_Tenure_Months"], bins), observed=True)["Historical_Profit_CLV"].median()
        mid = [iv.mid for iv in med.index]
        ax.plot(mid, med.to_numpy(), color=PAL["text"], marker="o", markersize=4, linewidth=1.6,
                label="Median per 3-month tenure band")
        ax.set_title(f"{title}: n = {len(d_):,}")
        ax.set_xlabel("Tenure: months since first observed purchase")
        ax.yaxis.set_major_formatter(kfmt)
        ax.set_ylim(c["Historical_Profit_CLV"].min() * 1.05, c["Historical_Profit_CLV"].quantile(0.995))
        ax.legend(loc="upper left")
    axes[0].set_ylabel("Historical profit (₹)")
    fig.suptitle(f"Customer tenure vs historical profit (Spearman {R['tenure_value']['rho']:.2f})",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, "Y axis cut at P99.5. Tenure for customers existing before 2023 starts at the first purchase in the data, "
               "so it is a minimum.")
    fig.tight_layout()
    _save(fig, "customer_tenure_vs_value.png", out_dir, saved)

    # 5 frequency vs value -------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
    band = c["Total_Orders"].clip(upper=16)
    labels = [str(i) if i < 16 else "16+" for i in range(1, 17)]
    for ax, (col, colr, title) in zip(axes, (("Historical_Profit_CLV", HIST, "Historical profit (observed)"),
                                             ("Estimated_12M_Future_Profit", EST, "Estimated next-12-month profit"))):
        groups = [c.loc[band == i, col].to_numpy() for i in range(1, 17)]
        bp = ax.boxplot(groups, showfliers=False, widths=0.6, patch_artist=True,
                        medianprops={"color": "#0b0b0b", "linewidth": 1.3})
        for b_ in bp["boxes"]:
            b_.set(facecolor=colr, alpha=0.55, edgecolor=colr)
        ax.set_xticks(range(1, 17), labels)
        ax.set_xlabel("Delivered orders, 2023-2025")
        ax.set_title(title)
        ax.yaxis.set_major_formatter(kfmt)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("₹ per customer")
    fig.suptitle("Purchase frequency vs customer value", x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, "Boxes = P25-P75, line = median, whiskers = 1.5 IQR (outliers hidden). Estimates for customers with no "
               "order in the last 12 months are a group average.")
    fig.tight_layout()
    _save(fig, "frequency_vs_clv.png", out_dir, saved)

    # 6 recency vs value ---------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    risk = c["Potentially_At_Risk_High_Value"]
    for ax, (col, colr, title) in zip(axes, (("Historical_Profit_CLV", HIST, "Historical profit (observed)"),
                                             ("Estimated_12M_Future_Profit", EST, "Estimated next-12-month profit"))):
        ax.scatter(c.loc[~risk, "Recency"], c.loc[~risk, col], s=8, alpha=0.35, color=colr, linewidths=0,
                   label="Customers")
        ax.scatter(c.loc[risk, "Recency"], c.loc[risk, col], s=22, facecolors="none", edgecolors=PAL["text"],
                   linewidths=0.9, label=f"Potentially at-risk high-value ({int(risk.sum())})")
        ax.axvline(AT_RISK_DAYS, color=PAL["muted"], linestyle="--", linewidth=1)
        ax.text(AT_RISK_DAYS + 8, ax.get_ylim()[1] * 0.92, f"{AT_RISK_DAYS} days", fontsize=8.5, color=PAL["muted"])
        ax.set_xlabel("Recency: days since last purchase (at 2026-01-01)")
        ax.set_title(title)
        ax.yaxis.set_major_formatter(kfmt)
        ax.legend(loc="upper right")
    axes[0].set_ylabel("₹ per customer")
    fig.suptitle("Recency vs customer value", x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, "Customers with no order in the last 12 months (recency > 365) share one group-average estimate "
               "(horizontal band, right panel).")
    fig.tight_layout()
    _save(fig, "recency_vs_clv.png", out_dir, saved)

    # 7 by RFM segment -----------------------------------------------------------------------
    byr = R["by_rfm"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    lbl = byr["RFM_Segment"].tolist()
    _hbar(axes[0], lbl, byr["Avg_Historical_Profit_CLV"].to_numpy(), color=HIST,
          value_labels=[f"{inr(v)}  ({s_:.1f}% of total)" for v, s_ in
                        zip(byr["Avg_Historical_Profit_CLV"], byr["Historical_Profit_Share_%"])])
    _hbar(axes[1], lbl, byr["Avg_Estimated_12M_Value"].to_numpy(), color=EST,
          value_labels=[f"{inr(v)}  ({r_:.2f}x hist. annual rate)" for v, r_ in
                        zip(byr["Avg_Estimated_12M_Value"], byr["Est_12M_to_Historical_Annual_Rate"])])
    axes[1].set_yticklabels([])
    axes[0].set_title("Average historical profit CLV (observed, 2023-2025)")
    axes[1].set_title("Average estimated next-12-month profit")
    for ax in axes:
        _rupee(ax, "x")
    fig.suptitle("Customer value by RFM segment (Step 5)", x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, "Hist. annual rate = historical profit / tenure in years (tenure floored at 12 months). "
               "Estimates are model outputs under stated assumptions, not guaranteed values.")
    fig.tight_layout()
    _save(fig, "clv_by_rfm_segment.png", out_dir, saved)

    # 8 by ML cluster ------------------------------------------------------------------------
    byc = R["by_cluster"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    lab = [f"C{r['Cluster_ID']}: {r['Cluster_Label']}" for _, r in byc.iterrows()]
    y = np.arange(len(byc))
    h_ = 0.38
    ax = axes[0]
    ax.barh(y - h_ / 2, byc["Avg_Historical_Annual_Profit_Rate"], h_, color=HIST, label="Historical annual profit rate")
    ax.barh(y + h_ / 2, byc["Avg_Estimated_12M_Value"], h_, color=EST, label="Estimated next-12-month profit")
    for i, (a_, b_) in enumerate(zip(byc["Avg_Historical_Annual_Profit_Rate"], byc["Avg_Estimated_12M_Value"])):
        ax.text(a_, i - h_ / 2, f" {inr(a_)}", va="center", fontsize=8.5)
        ax.text(b_, i + h_ / 2, f" {inr(b_)}", va="center", fontsize=8.5)
    ax.set_yticks(y, lab)
    ax.invert_yaxis()
    ax.set_xlim(0, max(byc["Avg_Historical_Annual_Profit_Rate"].max(), byc["Avg_Estimated_12M_Value"].max()) * 1.2)
    _rupee(ax, "x")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("Average per customer")
    ax = axes[1]
    w = 0.26
    for k, (col, name, colr) in enumerate((("Customer_%", "Customers", PAL["neutral"]),
                                           ("Historical_Profit_Share_%", "Historical profit", HIST),
                                           ("Estimated_12M_Value_Share_%", "Estimated 12M value", EST))):
        ax.barh(y + (k - 1) * w, byc[col], w, color=colr, label=name)
        for i, v in enumerate(byc[col]):
            ax.text(v, i + (k - 1) * w, f" {v:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y, [""] * len(y))
    ax.invert_yaxis()
    ax.set_xlim(0, 62)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_xlabel("% of all customers / of total value")
    ax.set_title("Share of total")
    for t_, cid in zip(axes[0].get_yticklabels(), byc["Cluster_ID"]):
        t_.set_color(CLUSTER_COLORS[cid])
    fig.suptitle("Customer value by K-Means cluster (Step 6)", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "clv_by_ml_cluster.png", out_dir, saved)

    # 9 inactivity thresholds ----------------------------------------------------------------
    sens = R["inactivity"]["sensitivity"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for (cut, d_), colr in zip(sens.groupby("Cutoff"), (PAL["violet"], PAL["aqua"])):
        ax.plot(d_["Threshold_Days"], d_["Bought_Again_Next_12M_%"] / 100, marker="o", color=colr,
                label=f"Inactive >= threshold at {cut}")
        ax.plot(d_["Threshold_Days"], d_["Bought_Again_if_Below_Threshold_%"] / 100, marker="o", color=colr,
                linestyle=":", alpha=0.8, label=f"Below threshold at {cut}")
    ax.axvline(AT_RISK_DAYS, color=PAL["muted"], linestyle="--", linewidth=1)
    ax.text(AT_RISK_DAYS + 5, 0.18, f"'potentially at-risk'\nthreshold = {AT_RISK_DAYS} days", fontsize=8.5,
            color=PAL["muted"])
    ax.set_xticks(INACTIVITY_THRESHOLDS)
    ax.set_ylim(0, 1.05)
    _pct_axis(ax, "y")
    ax.set_xlabel("Inactivity threshold (days since last purchase at the cutoff)")
    ax.set_ylabel("Bought again in the next 12 months")
    ax.set_title("Inactive is not churned: many inactive customers came back")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    _save(fig, "clv_inactivity_threshold.png", out_dir, saved)

    # 10 model comparison -------------------------------------------------------------------
    comp = R["evaluation"]["comparison"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
    cols_ = [EST if s_ else (PAL["blue"] if t_ == "ML model" else PAL["neutral"])
             for s_, t_ in zip(comp["Selected"], comp["Type"])]
    names = [n + ("  [selected]" if s_ else "") for n, s_ in zip(comp["Model"], comp["Selected"])]
    _hbar(axes[0], names, comp["R2"].to_numpy(), color=cols_, value_labels=[f"{v:.3f}" for v in comp["R2"]])
    _hbar(axes[1], names, comp["MAE"].to_numpy(), color=cols_, value_labels=[inr(v) for v in comp["MAE"]])
    axes[1].set_yticklabels([])
    axes[0].set_title("R² on the 2025 test year (higher is better)")
    axes[1].set_title("MAE per customer (lower is better)")
    _rupee(axes[1], "x")
    fig.suptitle("Out-of-time test: 2024 behaviour -> 2025 profit (same 1,328 customers for every method)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, "Blue = ML models, grey = non-ML benchmarks, orange = model selected by 5-fold CV on the training year "
               "(the test year was not used to choose).")
    fig.tight_layout()
    _save(fig, "clv_model_comparison.png", out_dir, saved)

    # 11 actual vs predicted ----------------------------------------------------------------
    tp, cal = R["evaluation"]["test_predictions"], R["evaluation"]["calibration"]
    m = R["evaluation"]["metrics"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    ax = axes[0]
    lim = tp["Actual_Future_Profit_12M"].quantile(0.99)
    ax.scatter(tp["Predicted_Future_Profit_12M"], tp["Actual_Future_Profit_12M"], s=9, alpha=0.4, color=EST,
               linewidths=0)
    ax.plot([0, lim], [0, lim], color=PAL["text"], linestyle="--", linewidth=1, label="Perfect prediction")
    ax.set_xlim(0, lim)
    ax.set_ylim(min(0, tp["Actual_Future_Profit_12M"].min()), lim)
    ax.xaxis.set_major_formatter(kfmt)
    ax.yaxis.set_major_formatter(kfmt)
    ax.set_xlabel("Predicted 2025 profit (₹)")
    ax.set_ylabel("Actual 2025 profit (₹)")
    ax.set_title(f"Per customer: R² {m['R2']:.2f}, MAE {inr(m['MAE'])}, Spearman {m['Spearman']:.2f}")
    ax.legend(loc="upper left")
    ax = axes[1]
    x = cal["Predicted_Decile"].to_numpy()
    ax.bar(x - 0.2, cal["Mean_Predicted"], 0.4, color=EST, label="Mean predicted")
    ax.bar(x + 0.2, cal["Mean_Actual"], 0.4, color=HIST, label="Mean actual")
    ax.set_xticks(x)
    ax.set_xlabel("Predicted-value decile (1 = lowest)")
    ax.yaxis.set_major_formatter(kfmt)
    ax.set_title("Calibration by predicted decile")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.suptitle(f"Actual vs predicted next-12-month profit - {R['trained']['chosen']}, 2025 test year",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    _note(fig, f"Left panel axes cut at the 99th percentile of actual profit. Predicted total = "
               f"{m['Predicted_to_Actual_Total']:.0%} of actual total (activity grew in 2025).")
    fig.tight_layout()
    _save(fig, "clv_actual_vs_predicted.png", out_dir, saved)

    # 12 feature importance ------------------------------------------------------------------
    imp = R["importance"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    ax = axes[0]
    yy = np.arange(len(imp))
    ax.barh(yy, imp["Permutation_MAE_Increase"], xerr=imp["Permutation_Std"], color=EST, height=0.6,
            error_kw={"ecolor": PAL["muted"], "capsize": 2})
    ax.set_yticks(yy, imp["Feature"])
    ax.invert_yaxis()
    ax.axvline(0, color=PAL["muted"], linewidth=0.8)
    _rupee(ax, "x")
    ax.set_xlabel("Increase in test MAE when the feature is shuffled (₹)")
    ax.set_title(f"Permutation importance - {R['trained']['chosen']}")
    ax.grid(axis="y", visible=False)
    ax = axes[1]
    coef = imp["Ridge_Std_Coefficient"]
    ax.barh(yy, coef, color=[HIST if v > 0 else PAL["neutral"] for v in coef], height=0.6)
    ax.axvline(0, color=PAL["muted"], linewidth=0.8)
    _rupee(ax, "x")
    ax.set_xlabel("₹ change in estimate per +1 standard deviation (other features fixed)")
    ax.set_title("Direction: Ridge baseline coefficients")
    ax.grid(axis="y", visible=False)
    fig.suptitle("What the model associates with higher next-12-month profit", x=0.01, ha="left", fontsize=13,
                 fontweight="bold")
    _note(fig, "Associations learned from the data, not causal effects. Skewed features enter on the arcsinh scale.")
    fig.tight_layout()
    _save(fig, "clv_feature_importance.png", out_dir, saved)

    # 13 high-value groups -------------------------------------------------------------------
    hv = R["high_value"]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    y = np.arange(len(hv))
    for k, (col, name, colr) in enumerate((("Customer_%", "Customers", PAL["neutral"]),
                                           ("Historical_Profit_Share_%", "Historical profit", HIST),
                                           ("Estimated_12M_Share_%", "Estimated 12M value", EST))):
        ax.barh(y + (k - 1) * 0.26, hv[col], 0.26, color=colr, label=name)
        for i, v in enumerate(hv[col]):
            ax.text(v, i + (k - 1) * 0.26, f" {v:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y, [f"{g} (n = {n})" for g, n in zip(hv["Group"], hv["Customers"])])
    ax.invert_yaxis()
    ax.set_xlim(0, 70)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("High-value customer groups: share of customers, historical profit and estimated value")
    fig.tight_layout()
    _save(fig, "clv_high_value_groups.png", out_dir, saved)
    return saved


# =============================================================================
# 10. REPORT
# =============================================================================
def write_clv_report(R: dict, path: Path = REPORT_FILE) -> Path:
    """Markdown report. Every number is inserted from computed results."""
    from src.eda import _md_table
    c, dist = R["clv"], R["distribution"]
    s_ = dist["summary"].set_index("Measure")
    ev, m = R["evaluation"], R["evaluation"]["metrics"]
    bg, est = R["bgnbd"], R["estimates"]
    sens = R["inactivity"]["sensitivity"]
    gaps = R["inactivity"]["gaps"].set_index("Statistic")["Days"]
    fs = R["feature_selection"]["table"]
    n_tr, n_te = len(R["train"]), len(R["test"])
    n_model = int(c["Estimate_Method"].str.startswith("ML").sum())
    comp = ev["comparison"]
    best_mae = comp.loc[comp["MAE"].idxmin()]
    best_r2 = comp.loc[comp["R2"].idxmax()]

    def f0(x):
        return f"{x:,.0f}"

    def tbl(df, cols, fmt=None):
        d = df[cols].copy()
        for col, fn in (fmt or {}).items():
            d[col] = d[col].map(fn)
        return _md_table(d)

    money = lambda v: inr(v)          # noqa: E731
    p1 = lambda v: f"{v:.1f}%"        # noqa: E731

    L = []
    L.append("# Customer Lifetime Value (CLV) Analysis - Step 7\n")
    L.append(f"> **{config.DATASET_LABEL}.** All numbers come from the synthetic dataset generated in Step 2 (seed 42) "
             "and cleaned in Step 3. They illustrate the method; they are not facts about a real company.\n")
    L.append("Reproduce: `python src/clv.py` (about 20 seconds). Notebook: `notebooks/05_customer_lifetime_value.ipynb`.\n")

    L.append("## 1. Objective\n")
    L.append("Measure what each customer has been worth, estimate what each customer may be worth over the next "
             "12 months, and compare both views across the Step 5 RFM segments and Step 6 K-Means clusters. "
             "Two quantities are kept strictly apart:\n")
    L.append("| | Observed historical value | Estimated future value |")
    L.append("|---|---|---|")
    L.append("| What it is | Delivered revenue / profit actually generated, 2023-01-01 to 2025-12-31 | "
             "Model estimate of Delivered profit in the next 12 months |")
    L.append("| Nature | Fact (reconciles to the transactions) | Estimate under stated assumptions |")
    L.append("| Columns | `Historical_Revenue_CLV`, `Historical_Profit_CLV` | `Estimated_12M_Future_Profit`, "
             "`Illustrative_3Y_Value` |\n")

    L.append("## 2. CLV definition\n")
    L.append("Customer Lifetime Value is the economic value a customer is expected to generate over the relevant "
             "customer relationship period. There are three broad ways to measure it:\n")
    L.append("1. **Historical CLV** - total value already generated (revenue, or better, profit = revenue - cost).")
    L.append("2. **Simplified predictive CLV** - Expected value = Average Order Value x expected purchase frequency x "
             "expected margin x expected lifetime.")
    L.append("3. **Probabilistic / ML CLV** - statistical models of purchasing (BG/NBD + Gamma-Gamma) or supervised "
             "models trained on past behaviour -> later value.\n")
    L.append("This project implements (1) in full, tests (2) and (3) against a real hold-out year, and uses the "
             "best-supported approach for the estimate.\n")

    L.append("## 3. Historical value methodology\n")
    L.append("- Revenue, cost and profit use **Delivered lines only** (project rule since Step 3). Returned and "
             "Cancelled lines carry zero revenue and profit and are counted separately.")
    L.append("- `Historical_Revenue_CLV` = sum of Sales; `Historical_Profit_CLV` = sum of Profit (= Sales - Cost). "
             "Profit CLV is the economically meaningful measure; revenue CLV is kept for comparison.")
    L.append(f"- Tenure = reference date ({R['reference_date'].date()}) - first delivered purchase. For "
             f"{pct(c['Tenure_Left_Censored'].mean())} of customers ('Existing before 2023') the true first purchase is "
             "before the data starts, so tenure and historical value are **minimums** (left-censored).\n")
    L.append("**Aggregate results**\n")
    L.append(tbl(dist["summary"], ["Measure", "Customers", "Total", "Mean", "Median", "Std", "Min", "Max",
                                   "Mean_to_Median", "Skewness", "Customers_below_zero"],
                 {"Total": money, "Mean": money, "Median": money, "Std": money, "Min": money, "Max": money,
                  "Mean_to_Median": lambda v: f"{v:.2f}", "Skewness": lambda v: f"{v:.2f}"}))
    L.append(f"\nHistorical profit margin: {pct(s_.loc['Historical profit', 'Total'] / s_.loc['Historical revenue', 'Total'])}. "
             f"Revenue and profit are both strongly right-skewed (skewness {s_.loc['Historical revenue', 'Skewness']:.2f} and "
             f"{s_.loc['Historical profit', 'Skewness']:.2f}); the mean is {s_.loc['Historical profit', 'Mean_to_Median']:.2f}x "
             "the median for profit, so medians and percentiles are reported alongside means.\n")
    L.append("**Concentration**\n")
    L.append(tbl(dist["concentration"], ["Top_Customers_%", "Customers", "Revenue_Share_%", "Profit_Share_%"],
                 {"Top_Customers_%": lambda v: f"Top {v:g}%", "Revenue_Share_%": p1, "Profit_Share_%": p1}))
    L.append(f"\nGini coefficient: revenue {dist['gini']['Total_Revenue']:.2f}, profit {dist['gini']['Total_Profit']:.2f}.\n")
    L.append("**Percentiles**\n")
    L.append(tbl(dist["percentiles"], ["Percentile", "Historical_Revenue", "Historical_Profit", "Total_Orders",
                                       "Customer_Tenure_Days"],
                 {"Historical_Revenue": money, "Historical_Profit": money, "Total_Orders": lambda v: f"{v:.0f}",
                  "Customer_Tenure_Days": lambda v: f"{v:.0f}"}))
    L.append("\n**Single-purchase customers (investigated separately)**\n")
    L.append(tbl(dist["single_purchase"], ["Is_Single_Purchase", "Customers", "Customer_Share_%", "Median_Profit",
                                           "Avg_Profit", "Profit_Share_%", "Median_Days_Since_Purchase"],
                 {"Customer_Share_%": p1, "Median_Profit": money, "Avg_Profit": money, "Profit_Share_%": p1,
                  "Median_Days_Since_Purchase": lambda v: f"{v:.0f}"}))
    L.append("\nSingle-purchase customers have no repeat interval, so a purchase rate cannot be estimated for them "
             "from their own history; the predictive model uses cross-customer patterns instead.\n")

    L.append("## 4. Can the data support predictive CLV?\n")
    L.append(_md_table(R["readiness"]))
    r180 = sens[sens["Threshold_Days"] == AT_RISK_DAYS]["Bought_Again_Next_12M_%"]
    lo_, hi_ = r180.min(), r180.max()
    L.append("\n**Inactivity is not churn.** The data has no churn flag, so an inactivity threshold was tested "
             "against what customers actually did next (two real cutoffs):\n")
    L.append(tbl(sens, ["Cutoff", "Threshold_Days", "Customers_Inactive_>=_Threshold", "Bought_Again_Next_12M_%",
                        "Bought_Again_if_Below_Threshold_%"],
                 {"Bought_Again_Next_12M_%": p1, "Bought_Again_if_Below_Threshold_%": p1}))
    L.append(f"\nTime between repeat orders: median {gaps['Median']:.0f} days, P75 {gaps['P75']:.0f}, P90 {gaps['P90']:.0f}. "
             f"A **{AT_RISK_DAYS}-day** threshold sits between P75 and P90 of normal repeat gaps, and beyond it the "
             "chance of buying again falls clearly (e.g. "
             + ", ".join(f"{r['Bought_Again_Next_12M_%']:.0f}% vs {r['Bought_Again_if_Below_Threshold_%']:.0f}% at {r['Cutoff']}"
                         for _, r in sens[sens['Threshold_Days'] == AT_RISK_DAYS].iterrows())
             + f"). Because {lo_:.0f}-{hi_:.0f}% of such customers still bought again, they are called **potentially at-risk**, "
             "never churned.\n")
    L.append("**Probabilistic model check (BG/NBD + Gamma-Gamma)**\n")
    L.append("BG/NBD was implemented with scipy (no extra package), fitted on 2023-2024 and tested on 2025:\n")
    L.append(_md_table(bg["evaluation"]))
    L.append(f"\nBG/NBD captures repeat-purchase behaviour reasonably ({bg['orders_ratio']:.0%} of hold-out orders, "
             f"R² {bg['orders_r2']:.2f} on order counts). **Gamma-Gamma was not used**: it requires spend per order to "
             "be independent of purchase frequency, and here they are positively correlated. BG/NBD also assumes a "
             "stable purchase process and a known start of each relationship; activity grew year on year and "
             "tenure is left-censored for many customers. BG/NBD is therefore kept as a **benchmark** in the model "
             "comparison, not as the final method.\n")

    L.append("## 5. Predictive methodology (time-based, no leakage)\n")
    L.append("| Panel | Feature period | Prediction (target) period | Customers | Role |")
    L.append("|---|---|---|---|---|")
    L.append(f"| Train | 2023-01-01 to 2023-12-31 | 2024-01-01 to 2024-12-31 | {n_tr:,} | model fitting + 5-fold CV selection |")
    L.append(f"| Test | 2024-01-01 to 2024-12-31 | 2025-01-01 to 2025-12-31 | {n_te:,} | out-of-time evaluation only |")
    L.append(f"| Scoring | 2025-01-01 to 2025-12-31 | next 12 months after {R['reference_date'].date()} (not in the data) | "
             f"{n_model:,} | estimate |\n")
    L.append(f"- **Target definition:** `{TARGET}` = Delivered profit (₹) in the 12 months after the cutoff "
             "(0 if the customer did not buy).")
    L.append("- **Population:** customers with >= 1 Delivered order in the 12 months before the cutoff. The "
             f"{len(c) - n_model} customers with no order in 2025 are outside this population and receive the "
             f"observed average next-year profit of the equivalent group at the 2025 cutoff: {inr(est['lapsed_value'])} "
             f"({est['lapsed_repeat']:.0%} of that group bought again; n = {est['lapsed_n_2025']}).")
    L.append("- Features only use transactions dated **before** the cutoff; the target only uses transactions "
             "**on or after** it. RFM segments and cluster labels (computed on the full period) are **not** features.\n")

    L.append("## 6. Feature engineering\n")
    L.append("Thirteen candidate features were computed per customer on the 12-month window. Selection was done on "
             "the training panel only:\n")
    L.append(tbl(fs, ["Feature", "Decision", "Reason", "VIF_All_Candidates", "VIF_Final_Set",
                      "Spearman_with_Target_(train)"],
                 {"VIF_All_Candidates": lambda v: f"{v:,.1f}", "VIF_Final_Set": lambda v: "" if pd.isna(v) else f"{v:.2f}",
                  "Spearman_with_Target_(train)": lambda v: f"{v:.2f}"}))
    L.append(f"\nRevenue, Profit and profit per order are exact products of AOV, Frequency and margin; keeping them "
             "made the linear coefficients explode in opposite directions. Skewed features "
             f"({', '.join(f for f in MODEL_FEATURES if f in SKEWED_FEATURES)}) enter on the arcsinh scale "
             "(like log, but defined for zero/negative values), then everything is standardised "
             "(`models/clv_preprocessor.pkl`).\n")

    L.append("## 7. Model selection\n")
    L.append("An interpretable baseline (Ridge regression, alpha chosen by internal CV) was compared with two "
             "non-linear models. **Selection rule:** lowest mean 5-fold CV RMSE on the training panel; the test year "
             "played no part in the choice.\n")
    L.append(tbl(R["trained"]["cv"], ["Model", "CV_RMSE", "CV_RMSE_Std", "CV_MAE", "CV_R2", "Selected"],
                 {"CV_RMSE": f0, "CV_RMSE_Std": f0, "CV_MAE": f0, "CV_R2": lambda v: f"{v:.3f}"}))
    L.append(f"\nSelected: **{R['trained']['chosen']}**. For scoring, the same specification was refit on the train "
             f"and test panels together ({R['final']['rows']:,} rows) so that the most recent year is used; its "
             "validation evidence is the out-of-time test below.\n")

    L.append("## 8. Model validation (out-of-time, 2025)\n")
    L.append(tbl(comp, ["Model", "Type", "MAE", "RMSE", "R2", "WAPE_%", "Spearman", "Top20_Capture_%",
                        "Predicted_to_Actual_Total"],
                 {"MAE": money, "RMSE": money, "R2": lambda v: f"{v:.3f}", "WAPE_%": p1, "Spearman": lambda v: f"{v:.3f}",
                  "Top20_Capture_%": p1, "Predicted_to_Actual_Total": lambda v: f"{v:.2f}"}))
    L.append(f"\n- Selected model: R² **{m['R2']:.3f}**, MAE **{inr(m['MAE'])}**, RMSE **{inr(m['RMSE'])}**, "
             f"WAPE {m['WAPE_%']:.1f}%, Spearman {m['Spearman']:.3f}.")
    L.append(f"- **MAPE is not a headline metric:** {pct((R['test'][TARGET] == 0).mean())} of test customers had "
             f"zero future profit (MAPE undefined). On non-zero actuals only it is {m['MAPE_nonzero_%']:.0f}%, inflated by "
             "small actual values; WAPE (total absolute error / total actual) is reported instead.")
    L.append(f"- Ranking: the top 20% of customers by predicted value captured {m['Top20_Capture_%']:.1f}% of actual "
             "2025 profit.")
    L.append(f"- Bias: predicted total = {m['Predicted_to_Actual_Total']:.0%} of actual. Activity grew in 2025, which a "
             "model trained on 2023->2024 could not anticipate, so estimates are conservative in a growing year.")
    L.append(f"- Every method, including the benchmarks, explains a modest share of the variance (best R² "
             f"{best_r2['R2']:.2f}: {best_r2['Model']}; lowest MAE {inr(best_mae['MAE'])}: {best_mae['Model']}). "
             "Individual next-year profit is noisy; the estimates are best used to **rank** customers.\n")
    L.append("**Calibration by predicted decile (test year)**\n")
    L.append(tbl(ev["calibration"], ["Predicted_Decile", "Customers", "Mean_Predicted", "Mean_Actual", "Share_Purchased"],
                 {"Mean_Predicted": money, "Mean_Actual": money, "Share_Purchased": lambda v: f"{v:.0%}"}))
    L.append("\n**Feature importance** (permutation on the test year; association, not causation)\n")
    L.append(tbl(R["importance"], ["Feature", "Permutation_MAE_Increase", "Permutation_Std", "Ridge_Std_Coefficient"],
                 {"Permutation_MAE_Increase": money, "Permutation_Std": money, "Ridge_Std_Coefficient": f0}))
    L.append("\nThe permutation column shows how much worse the selected model gets when a feature is scrambled; "
             "the Ridge column shows direction (₹ per +1 standard deviation, other features fixed). These describe "
             "patterns in this data; they do not show that changing a feature would change a customer's value.\n")
    L.append("**Illustrative multi-year value (not validated)**\n")
    L.append(f"`Illustrative_3Y_Value` = estimated 12-month profit x (1 + r + r²), r = observed annual repeat rate "
             f"({est['repeat_rate']:.3f} pooled). No discounting is applied because no cost of capital is known for "
             "the company. Sensitivity:\n")
    L.append(tbl(est["horizon_sensitivity"], ["Scenario", "Annual_Repeat_Rate", "Horizon_Factor",
                                               "Total_Illustrative_3Y_Value"],
                 {"Annual_Repeat_Rate": lambda v: f"{v:.3f}", "Horizon_Factor": lambda v: f"{v:.2f}",
                  "Total_Illustrative_3Y_Value": money}))
    L.append("\nThere is no data after 2025 to test this figure; use it only to show scale and sensitivity.\n")

    L.append("## 9. CLV by RFM segment\n")
    L.append(tbl(R["by_rfm"], ["RFM_Segment", "Customer_Count", "Avg_Historical_Revenue", "Avg_Historical_Profit_CLV",
                               "Historical_Profit_Share_%", "Avg_Historical_Annual_Profit_Rate",
                               "Avg_Estimated_12M_Value", "Total_Estimated_12M_Value", "Est_12M_to_Historical_Annual_Rate",
                               "Avg_AOV", "Avg_Frequency", "Avg_Recency_Days"],
                 {"Avg_Historical_Revenue": money, "Avg_Historical_Profit_CLV": money, "Historical_Profit_Share_%": p1,
                  "Avg_Historical_Annual_Profit_Rate": money, "Avg_Estimated_12M_Value": money,
                  "Total_Estimated_12M_Value": money, "Est_12M_to_Historical_Annual_Rate": lambda v: f"{v:.2f}x",
                  "Avg_AOV": money, "Avg_Frequency": lambda v: f"{v:.1f}", "Avg_Recency_Days": f0}))
    L.append("\n`Est_12M_to_Historical_Annual_Rate` compares the estimate with each group's own historical annual "
             "profit rate (profit / tenure in years, tenure floored at 12 months). Below 1 = the model expects "
             "the group to slow down; above 1 = to grow (partly shrinkage toward the average for low-value groups).\n")

    L.append("## 10. CLV by ML cluster\n")
    L.append(tbl(R["by_cluster"], ["Cluster_ID", "Cluster_Label", "Customer_Count", "Customer_%",
                                   "Avg_Historical_Profit_CLV", "Historical_Profit_Share_%",
                                   "Avg_Historical_Annual_Profit_Rate", "Avg_Estimated_12M_Value",
                                   "Estimated_12M_Value_Share_%", "Est_12M_to_Historical_Annual_Rate", "Avg_AOV",
                                   "Avg_Frequency", "Avg_Recency_Days"],
                 {"Customer_%": p1, "Avg_Historical_Profit_CLV": money, "Historical_Profit_Share_%": p1,
                  "Avg_Historical_Annual_Profit_Rate": money, "Avg_Estimated_12M_Value": money,
                  "Estimated_12M_Value_Share_%": p1, "Est_12M_to_Historical_Annual_Rate": lambda v: f"{v:.2f}x",
                  "Avg_AOV": money, "Avg_Frequency": lambda v: f"{v:.1f}", "Avg_Recency_Days": f0}))
    L.append("")

    L.append("## 11. High-value customer analysis\n")
    L.append(tbl(R["high_value"], ["Group", "Definition", "Customers", "Customer_%", "Historical_Profit_Share_%",
                                   "Estimated_12M_Share_%", "Median_Recency_Days", "Top_RFM_Segments"],
                 {"Customer_%": p1, "Historical_Profit_Share_%": p1, "Estimated_12M_Share_%": p1,
                  "Median_Recency_Days": f0}))
    L.append("\nCustomer-level flags are in `data/processed/customer_clv.csv` (Customer_ID only; no names).\n")

    L.append("## 12. Business interpretation\n")
    L.append(_md_table(R["insights"]))
    L.append("\n**The eight Step 7 questions**\n")
    for _, r in R["questions"].iterrows():
        L.append(f"- **{r['Question']}** {r['Answer']}")
    L.append("\nAll estimated values should be read as: *the model estimates an expected next-12-month profit of "
             "approximately ₹X under the defined assumptions and prediction period* - not as what a customer will "
             "generate.\n")

    L.append("## 13. Limitations\n")
    L.append("1. **Synthetic data.** Patterns come from the Step 2 generator, not from a real business.")
    L.append(f"2. **Modest predictive accuracy.** Out-of-time R² {m['R2']:.2f}; per-customer errors are large relative to "
             "typical values. Use for ranking and prioritising, not for exact per-customer rupee figures.")
    rt = R["rates"]
    L.append(f"3. **Non-stationarity.** Active customers grew from {int(rt['Active_Customers'].iloc[0]):,} "
             f"({int(rt['From_Year'].iloc[0])}) to {len(est['scoring_panel']):,} ({int(rt['To_Year'].iloc[-1])}); "
             "the model under-estimated "
             f"the 2025 total ({m['Predicted_to_Actual_Total']:.0%}). A different future year could move either way.")
    L.append("4. **One out-of-time test.** Only one hold-out year exists (2025); results could differ in another year.")
    L.append("5. **Left-censored tenure** for customers existing before 2023; historical value is a minimum for them.")
    L.append("6. **No churn label.** 'Potentially at-risk' is a documented inactivity rule, not observed churn.")
    L.append("7. **Group-level estimate** for customers with no order in the last 12 months (one average value).")
    L.append("8. **12-month horizon only is validated.** The 3-year figure is illustrative, undiscounted and untested.")
    L.append("9. **Associations, not causes.** Feature importance does not show that changing a behaviour changes value.")
    L.append("10. **Gamma-Gamma rejected; BG/NBD not selected** - see section 4.\n")

    L.append("## 14. Next analytical steps\n")
    L.append("- Step 8 (revenue prediction & business driver analysis) can reuse the time-based panel design and the "
             "leakage checks built here.")
    L.append("- Re-validate the CLV model when a new year of data arrives (roll the cutoffs forward by 12 months).")
    L.append("- If real cost-of-capital and retention-cost data become available, add discounting and margin-after-"
             "marketing to the multi-year value.\n")

    L.append("## 15. Validation\n")
    L.append(_md_table(R["validation"]))
    L.append("\n## 16. Assumptions\n")
    L.append(_md_table(R["assumptions"]))
    L.append("\n## 17. Output files\n")
    L.append("- `data/processed/customer_value_history.csv` - observed historical value per customer")
    L.append("- `data/processed/customer_clv.csv` - historical + estimated value, RFM segment, cluster, value flags")
    L.append("- `data/processed/clv_modeling_dataset.csv` - train / test / scoring panels (features + targets)")
    L.append("- `models/clv_model.pkl`, `models/clv_preprocessor.pkl`, `models/clv_model_metadata.json`")
    L.append("- `outputs/tables/clv_*.csv` - " + str(len([p for p in R.get("saved", []) if p.parent == config.TABLES_DIR]))
             + " tables")
    L.append("- `outputs/figures/` - " + ", ".join(p.name for p in R.get("figures", [])))
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    run_clv()
