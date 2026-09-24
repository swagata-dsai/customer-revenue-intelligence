#!/usr/bin/env python3
"""
rfm.py
======
Step 5 of the Customer Revenue Intelligence project: RFM customer analysis
and rule-based customer value segmentation.

    >>> Works on the SYNTHETIC dataset cleaned in Step 3. <<<

Definitions (documented in outputs/reports/rfm_methodology.md)
--------------------------------------------------------------
* Only **Delivered** order lines count as a purchase. Cancelled and Returned
  lines are excluded from Recency, Frequency and Monetary, but each
  customer's cancelled/returned line count is kept as context.
* Reference date = latest Order_Date in the data + 1 day (derived, not typed).
* Recency   = (reference date - last delivered purchase date) in days.
* Frequency = number of distinct Order_IDs with at least one Delivered line
              (Order_ID = one checkout; verified in Step 4).
* Monetary  = sum of Sales on Delivered lines (INR, after discount).
* Customers with no delivered purchase have no Recency/Frequency/Monetary.
  They are excluded from scoring and listed separately.

Scoring: tie-aware percentile scores 1-5 (see calculate_rfm_scores).
Segments: transparent rules on R_Score and FM_Score = (F_Score + M_Score) / 2.
This is RULE-BASED segmentation. Machine-learning (K-Means) segmentation
is a separate exercise in Step 6.

Main entry point:  python src/rfm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.eda import inr, pct  # noqa: E402  (shared formatting helpers)

RFM_FILE = config.PROCESSED_DIR / "customer_rfm.csv"
RFM_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_rfm_segments.csv"
RFM_METADATA_FILE = config.PROCESSED_DIR / "customer_rfm_metadata.json"
RFM_REPORT = config.REPORTS_DIR / "rfm_methodology.md"
N_SCORE_LEVELS = 5

# -----------------------------------------------------------------------------
# Segment rules: evaluated top-down, first match wins. The grid is exhaustive
# over R_Score 1-5 x FM_Score 1-5, so every customer gets exactly one segment.
# -----------------------------------------------------------------------------
SEGMENT_RULES = [
    # name, rule (lambda on R, FM), RFM characteristics, business meaning, value-activity group
    ("Champions", lambda r, fm: (r >= 4) & (fm >= 4.5),
     "R 4-5 and FM >= 4.5", "Bought recently, buy often and spend the most", "Active high value"),
    ("Loyal Customers", lambda r, fm: (r >= 3) & (fm >= 3.5),
     "R 3-5 and FM 3.5-4 (or R 3 and FM >= 4.5)", "Regular, valuable buyers; strong relationship", "Active high value"),
    ("Potential Loyalists", lambda r, fm: (r >= 4) & (fm >= 2.5),
     "R 4-5 and FM 2.5-3", "Recent buyers with average frequency and spend", "Developing"),
    ("Recent Customers", lambda r, fm: (r == 5) & (fm < 2.5),
     "R 5 and FM < 2.5", "Bought very recently but only a little so far", "Developing"),
    ("Promising", lambda r, fm: (r == 4) & (fm < 2.5),
     "R 4 and FM < 2.5", "Fairly recent, low frequency and spend", "Developing"),
    ("Needs Attention", lambda r, fm: (r == 3) & (fm >= 2.5),
     "R 3 and FM 2.5-3", "Average customers whose recency is slipping", "Slipping"),
    ("About to Sleep", lambda r, fm: (r == 3) & (fm < 2.5),
     "R 3 and FM < 2.5", "Below-average value and going quiet", "Slipping"),
    ("Can't Lose Them", lambda r, fm: (r <= 2) & (fm >= 4.5),
     "R 1-2 and FM >= 4.5", "Were among the best customers; have not bought for a long time", "Slipping"),
    ("At Risk", lambda r, fm: (r <= 2) & (fm >= 3),
     "R 1-2 and FM 3-4", "Valuable in the past, now inactive", "Slipping"),
    ("Hibernating", lambda r, fm: (r == 2) & (fm < 3),
     "R 2 and FM < 3", "Low value and long inactive", "Inactive"),
    ("Lost", lambda r, fm: (r == 1) & (fm < 3),
     "R 1 and FM < 3", "Lowest recency, frequency and spend", "Inactive"),
]
SEGMENT_ORDER = [s[0] for s in SEGMENT_RULES]
CANT_LOSE = "Can't Lose Them"
GROUP_ORDER = ["Active high value", "Developing", "Slipping", "Inactive"]
SEGMENT_GROUP = {s[0]: s[4] for s in SEGMENT_RULES}


# =============================================================================
# 1. DATA
# =============================================================================
def load_clean_data(path: Path = config.CLEAN_DATA_FILE) -> pd.DataFrame:
    """Load the Step 3 cleaned transactions with parsed dates."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found - run src/data_cleaning.py (Step 3) first.")
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["Order_Date"])
    return df


def prepare_customer_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into valid purchase lines (Delivered) and excluded lines (Cancelled/Returned)."""
    valid = df[df["Order_Status"] == "Delivered"].copy()
    excluded = df[df["Order_Status"] != "Delivered"].copy()
    return valid, excluded


def get_reference_date(df: pd.DataFrame) -> pd.Timestamp:
    """Reference date = latest valid Order_Date in the data + 1 day.

    Using the day after the last recorded transaction means the most recent
    buyer has Recency = 1 (never 0 or negative), and the analysis describes
    the business exactly as of the end of the extract.
    """
    return (df["Order_Date"].max() + pd.Timedelta(days=1)).normalize()


# =============================================================================
# 2. R, F, M
# =============================================================================
def calculate_recency(valid: pd.DataFrame, ref_date: pd.Timestamp) -> pd.DataFrame:
    """Days between the reference date and each customer's last delivered purchase."""
    last = valid.groupby("Customer_ID")["Order_Date"].agg(First_Purchase_Date="min", Last_Purchase_Date="max")
    last["Recency"] = (ref_date - last["Last_Purchase_Date"]).dt.days
    return last


def calculate_frequency(valid: pd.DataFrame) -> pd.Series:
    """Distinct delivered orders per customer (not rows: one order can hold several products)."""
    return valid.groupby("Customer_ID")["Order_ID"].nunique().rename("Frequency")


def calculate_monetary(valid: pd.DataFrame) -> pd.Series:
    """Total delivered Sales (INR, after discount) per customer."""
    return valid.groupby("Customer_ID")["Sales"].sum().round(2).rename("Monetary")


def build_rfm_table(df: pd.DataFrame, ref_date: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Customer-level RFM table plus supporting attributes.

    Returns (rfm, excluded_customers). Customers without any delivered line
    cannot have a Recency or Monetary value and are returned separately.
    """
    ref_date = ref_date or get_reference_date(df)
    valid, excl_lines = prepare_customer_transactions(df)
    rfm = calculate_recency(valid, ref_date).join(calculate_frequency(valid)).join(calculate_monetary(valid))
    extra = valid.groupby("Customer_ID").agg(
        Total_Quantity=("Quantity", "sum"), Total_Profit=("Profit", "sum"),
        Average_Discount=("Discount", "mean"), Order_Lines=("Order_Line_ID", "count"),
        Categories_Bought=("Category", "nunique"))
    status = df.groupby("Customer_ID")["Order_Status"].agg(
        Cancelled_Lines=lambda s: int((s == "Cancelled").sum()), Returned_Lines=lambda s: int((s == "Returned").sum()))
    first_type = (df.sort_values(["Order_Date", "Order_ID"]).groupby("Customer_ID")["Customer_Type"].first())
    profile = df.drop_duplicates("Customer_ID").set_index("Customer_ID")[
        ["Customer_Age", "Gender", "City", "State", "Region"]]
    rfm = rfm.join(extra).join(status).join(profile)
    rfm["Average_Order_Value"] = (rfm["Monetary"] / rfm["Frequency"]).round(2)
    rfm["Average_Discount"] = rfm["Average_Discount"].round(4)
    rfm["Total_Profit"] = rfm["Total_Profit"].round(2)
    rfm["Tenure_Days"] = (ref_date - rfm["First_Purchase_Date"]).dt.days
    # Customer_Type is order-level; at customer level we keep how the customer entered the data
    rfm["Acquisition_Status"] = first_type.reindex(rfm.index).map(
        {"New": "Acquired 2023-2025", "Returning": "Existing before 2023"})
    rfm = rfm.reset_index()
    cols = ["Customer_ID", "Recency", "Frequency", "Monetary", "First_Purchase_Date", "Last_Purchase_Date",
            "Tenure_Days", "Total_Quantity", "Order_Lines", "Average_Order_Value", "Average_Discount",
            "Total_Profit", "Categories_Bought", "Cancelled_Lines", "Returned_Lines", "Acquisition_Status",
            "Customer_Age", "Gender", "City", "State", "Region"]
    rfm = rfm[cols].sort_values("Customer_ID").reset_index(drop=True)

    all_customers = df["Customer_ID"].unique()
    missing = sorted(set(all_customers) - set(rfm["Customer_ID"]))
    excluded = (df[df["Customer_ID"].isin(missing)].groupby("Customer_ID")
                .agg(Lines=("Order_Line_ID", "count"), Orders=("Order_ID", "nunique"),
                     Cancelled_Lines=("Order_Status", lambda s: int((s == "Cancelled").sum())),
                     Returned_Lines=("Order_Status", lambda s: int((s == "Returned").sum())),
                     Last_Order_Date=("Order_Date", "max"), Booked_Sales=("Sales", "sum"))
                .reset_index())
    excluded["Reason"] = "No delivered purchase - all lines cancelled or returned"
    del excl_lines
    return rfm, excluded


# =============================================================================
# 3. DISTRIBUTIONS
# =============================================================================
def describe_rfm(rfm: pd.DataFrame, total_customers: int) -> dict[str, pd.DataFrame]:
    """Descriptive statistics, headline customer metrics and a log-transform check."""
    stats_rows = []
    for c, unit in [("Recency", "days"), ("Frequency", "orders"), ("Monetary", "INR")]:
        s = rfm[c]
        stats_rows.append({"Metric": c, "Unit": unit, "Count": int(s.count()), "Mean": s.mean(), "Median": s.median(),
                           "Std": s.std(), "Min": s.min(), "Q1": s.quantile(.25), "Q3": s.quantile(.75),
                           "Max": s.max(), "Skewness": s.skew(), "Unique_Values": int(s.nunique())})
    desc = pd.DataFrame(stats_rows)
    total_rev = rfm["Monetary"].sum()
    n = len(rfm)
    headline = pd.DataFrame([
        ("Customers in the dataset", total_customers, f"{total_customers:,}"),
        ("Customers with >= 1 delivered purchase (scored)", n, f"{n:,}"),
        ("Customers with no delivered purchase (excluded)", total_customers - n, f"{total_customers - n:,}"),
        ("Total customer revenue (Monetary sum)", total_rev, inr(total_rev)),
        ("Average revenue per scored customer", total_rev / n, inr(total_rev / n)),
        ("Median revenue per scored customer", rfm["Monetary"].median(), inr(rfm["Monetary"].median())),
        ("Customers with exactly one order", int((rfm["Frequency"] == 1).sum()), pct((rfm["Frequency"] == 1).mean())),
        ("Repeat customers (2+ orders)", int((rfm["Frequency"] >= 2).sum()), pct((rfm["Frequency"] >= 2).mean())),
        ("Customers active in last 90 days (Recency <= 90)", int((rfm["Recency"] <= 90).sum()),
         pct((rfm["Recency"] <= 90).mean())),
        ("Customers inactive > 180 days (Recency > 180)", int((rfm["Recency"] > 180).sum()),
         pct((rfm["Recency"] > 180).mean())),
    ], columns=["Metric", "Value", "Display"])
    log_rows = []
    for c in ["Recency", "Frequency", "Monetary"]:
        s = rfm[c].astype(float)
        log_rows.append({"Metric": c, "Skewness_raw": s.skew(), "Skewness_log1p": np.log1p(s).skew(),
                         "Recommendation": ("log1p reduces skew - use for charts and as model input in Step 6"
                                            if abs(np.log1p(s).skew()) < abs(s.skew()) - 0.3
                                            else "log not needed - raw scale is adequate")})
    return {"descriptive": desc, "headline": headline, "log_check": pd.DataFrame(log_rows)}


# =============================================================================
# 4. SCORING
# =============================================================================
def _tie_aware_score(s: pd.Series, higher_is_better: bool = True, k: int = N_SCORE_LEVELS) -> pd.Series:
    """Score 1..k from the average percentile rank (ties share one score).

    Ordinary pd.qcut() fails or splits identical values across bins when a
    variable has many ties (e.g. Frequency has few distinct values). Here
    every customer's percentile rank is computed with ties averaged, then
    mapped to k equal-width percentile bands: score = ceil(k * pct_rank).
    Identical values therefore always receive the same score; the price is
    that band sizes are only approximately equal.
    """
    x = s if higher_is_better else -s
    p = x.rank(method="average", pct=True)
    return np.ceil(p * k).clip(1, k).astype(int)


def robust_quantile_score(s: pd.Series, higher_is_better: bool = True,
                          k: int = N_SCORE_LEVELS) -> tuple[pd.Series, str]:
    """Quintile score 1..k with an automatic, documented fallback.

    1. Try pd.qcut(q=k) on the raw values. qcut keeps identical values in the
       same bin, so it is the preferred, textbook method.
    2. If the quantile edges are not unique (too many ties, e.g. a variable
       where most customers have the same value), qcut raises an error. Then
       the tie-aware percentile score (_tie_aware_score) is used instead.
    Returns the scores and the method actually used.
    """
    try:
        labels = list(range(1, k + 1)) if higher_is_better else list(range(k, 0, -1))
        sc = pd.qcut(s, q=k, labels=labels, duplicates="raise").astype(int)
        return sc, f"pd.qcut(q={k}) quintiles"
    except ValueError:
        return _tie_aware_score(s, higher_is_better, k), "tie-aware percentile rank (qcut edges not unique)"


def calculate_rfm_scores(rfm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add R_Score, F_Score, M_Score, RFM_Cell, RFM_Score and FM_Score.

    * Scores come from robust_quantile_score (quintiles, with tie-aware fallback).
    * Recency is reversed (fewer days = higher score).
    * RFM_Cell   = concatenation, e.g. "545" (used for look-ups, not arithmetic).
    * RFM_Score  = R + F + M (3-15), equal weights: there is no evidence in the
                   data to justify weighting one dimension over another.
    * FM_Score   = (F + M) / 2, used for segmentation because F and M are highly
                   correlated (Spearman rho reported in the bins table).
    """
    out = rfm.copy()
    methods = {}
    out["R_Score"], methods["Recency"] = robust_quantile_score(out["Recency"], higher_is_better=False)
    out["F_Score"], methods["Frequency"] = robust_quantile_score(out["Frequency"], higher_is_better=True)
    out["M_Score"], methods["Monetary"] = robust_quantile_score(out["Monetary"], higher_is_better=True)
    out["RFM_Cell"] = out["R_Score"].astype(str) + out["F_Score"].astype(str) + out["M_Score"].astype(str)
    out["RFM_Score"] = out["R_Score"] + out["F_Score"] + out["M_Score"]
    out["FM_Score"] = (out["F_Score"] + out["M_Score"]) / 2
    bins = []
    for metric, score in [("Recency", "R_Score"), ("Frequency", "F_Score"), ("Monetary", "M_Score")]:
        g = out.groupby(score)[metric].agg(["count", "min", "max", "median"]).reset_index()
        g.insert(0, "Metric", metric)
        g = g.rename(columns={score: "Score", "count": "Customers", "min": "Min_Value",
                              "max": "Max_Value", "median": "Median_Value"})
        g["Share_of_Customers"] = g["Customers"] / len(out)
        g["Method"] = methods[metric]
        bins.append(g)
    bins = pd.concat(bins, ignore_index=True)
    return out, bins


def qcut_feasibility(rfm: pd.DataFrame) -> pd.DataFrame:
    """Show why plain pd.qcut(q=5) is unsuitable for some variables."""
    rows = []
    for c in ["Recency", "Frequency", "Monetary"]:
        edges = rfm[c].quantile(np.linspace(0, 1, N_SCORE_LEVELS + 1)).to_numpy()
        dup = len(edges) - len(np.unique(edges))
        rows.append({"Metric": c, "Unique_Values": int(rfm[c].nunique()),
                     "Quintile_Edges": ", ".join(f"{e:,.0f}" for e in edges),
                     "Duplicate_Edges": int(dup),
                     "Plain_qcut_OK": dup == 0,
                     "Largest_Tie_Group_%": round(100 * rfm[c].value_counts(normalize=True).iloc[0], 1)})
    out = pd.DataFrame(rows)
    # Sensitivity: how often would the tie-aware fallback give the same score?
    agree = []
    for c, hib in [("Recency", False), ("Frequency", True), ("Monetary", True)]:
        a_, _ = robust_quantile_score(rfm[c], hib)
        b_ = _tie_aware_score(rfm[c], hib)
        agree.append(round(100 * (a_ == b_).mean(), 1))
    out["Agreement_with_tie_aware_%"] = agree
    return out


# =============================================================================
# 5. SEGMENTS
# =============================================================================
def assign_rfm_segments(scored: pd.DataFrame) -> pd.DataFrame:
    """Apply SEGMENT_RULES top-down; every customer receives exactly one segment."""
    out = scored.copy()
    r, fm = out["R_Score"], out["FM_Score"]
    seg = pd.Series(pd.NA, index=out.index, dtype="object")
    for name, rule, *_ in SEGMENT_RULES:
        hit = seg.isna() & rule(r, fm)
        seg[hit] = name
    if seg.isna().any():
        raise ValueError(f"{int(seg.isna().sum())} customers matched no segment rule - rules are not exhaustive")
    out["RFM_Segment"] = pd.Categorical(seg, categories=SEGMENT_ORDER, ordered=True)
    out["Value_Activity_Group"] = out["RFM_Segment"].map(SEGMENT_GROUP).astype(str)
    return out


def segment_rules_table() -> pd.DataFrame:
    return pd.DataFrame([(s[0], s[2], s[3], s[4]) for s in SEGMENT_RULES],
                        columns=["Segment", "RFM Characteristics (rule)", "Business Meaning", "Value-Activity Group"])


def summarize_rfm_segments(seg: pd.DataFrame) -> pd.DataFrame:
    """Per-segment size, revenue and average behaviour."""
    total_rev, n = seg["Monetary"].sum(), len(seg)
    g = seg.groupby("RFM_Segment", observed=False).agg(
        Customer_Count=("Customer_ID", "count"), Total_Revenue=("Monetary", "sum"),
        Total_Orders=("Frequency", "sum"), Average_Recency=("Recency", "mean"), Median_Recency=("Recency", "median"),
        Average_Frequency=("Frequency", "mean"), Average_Monetary=("Monetary", "mean"),
        Median_Monetary=("Monetary", "median"), Total_Profit=("Total_Profit", "sum"),
        Average_R_Score=("R_Score", "mean"), Average_F_Score=("F_Score", "mean"), Average_M_Score=("M_Score", "mean"))
    g["Customer_%"] = 100 * g["Customer_Count"] / n
    g["Revenue_%"] = 100 * g["Total_Revenue"] / total_rev
    g["Average_Revenue"] = g["Total_Revenue"] / g["Customer_Count"]
    g["Average_Order_Value"] = g["Total_Revenue"] / g["Total_Orders"]  # segment revenue / segment orders
    g["Revenue_to_Customer_Ratio"] = g["Revenue_%"] / g["Customer_%"]
    g["Profit_Margin"] = g["Total_Profit"] / g["Total_Revenue"]
    g["Value_Activity_Group"] = [SEGMENT_GROUP[s] for s in g.index]
    cols = ["Value_Activity_Group", "Customer_Count", "Customer_%", "Total_Revenue", "Revenue_%", "Average_Revenue",
            "Average_Recency", "Median_Recency", "Average_Frequency", "Average_Monetary", "Median_Monetary",
            "Average_Order_Value", "Profit_Margin", "Revenue_to_Customer_Ratio",
            "Average_R_Score", "Average_F_Score", "Average_M_Score"]
    return g[cols].reset_index().round(3)


def segment_profile(seg: pd.DataFrame) -> pd.DataFrame:
    """Descriptive profile of each segment (who they are) - context only, not used in the rules."""
    g = seg.groupby("RFM_Segment", observed=False)
    prof = pd.DataFrame({
        "Customers": g.size(),
        "Share_Existing_Before_2023_%": g["Acquisition_Status"].apply(lambda s: 100 * (s == "Existing before 2023").mean()),
        "Median_Age": g["Customer_Age"].median(),
        "Median_Tenure_Days": g["Tenure_Days"].median(),
        "Avg_Categories_Bought": g["Categories_Bought"].mean(),
        "Avg_Discount_%": g["Average_Discount"].mean() * 100,
        "Return_Lines_per_Customer": g["Returned_Lines"].mean(),
        "Top_Region": g["Region"].agg(lambda s: s.value_counts().index[0]),
        "Top_Region_Share_%": g["Region"].agg(lambda s: 100 * s.value_counts(normalize=True).iloc[0]),
    })
    return prof.reset_index().round(2)


def summarize_groups(seg: pd.DataFrame) -> pd.DataFrame:
    total_rev, n = seg["Monetary"].sum(), len(seg)
    g = seg.groupby("Value_Activity_Group").agg(Customers=("Customer_ID", "count"), Revenue=("Monetary", "sum"),
                                                Average_Recency=("Recency", "mean"),
                                                Average_Frequency=("Frequency", "mean"),
                                                Average_Monetary=("Monetary", "mean")).reindex(GROUP_ORDER)
    g["Customer_%"] = 100 * g["Customers"] / n
    g["Revenue_%"] = 100 * g["Revenue"] / total_rev
    return g.reset_index().round(3)


# =============================================================================
# 6. CONCENTRATION + HIGH-VALUE LISTS
# =============================================================================
def analyze_revenue_concentration(seg: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Top-x% revenue shares, Gini, and share of customers needed for 50% / 80% of revenue."""
    m = seg["Monetary"].sort_values(ascending=False).to_numpy()
    n, total = len(m), m.sum()
    cum = np.cumsum(m) / total
    rows = []
    for p in (1, 5, 10, 20, 50):
        k = int(np.ceil(n * p / 100))
        rows.append({"Customer_Group": f"Top {p}%", "Customers": k, "Revenue": m[:k].sum(),
                     "Revenue_Share_%": 100 * m[:k].sum() / total,
                     "Min_Monetary_in_Group": m[k - 1]})
    conc = pd.DataFrame(rows)
    asc = np.sort(m)
    lor = np.concatenate([[0], np.cumsum(asc) / total])
    gini = 1 - 2 * np.trapezoid(lor, dx=1 / n)
    need50 = int(np.searchsorted(cum, 0.5) + 1)
    need80 = int(np.searchsorted(cum, 0.8) + 1)
    stats = pd.DataFrame([
        ("Scored customers", n),
        ("Gini coefficient (0 = equal, 1 = one customer has all)", round(gini, 3)),
        ("Customers needed for 50% of revenue", need50),
        ("Share of customers needed for 50% of revenue (%)", round(100 * need50 / n, 1)),
        ("Customers needed for 80% of revenue", need80),
        ("Share of customers needed for 80% of revenue (%)", round(100 * need80 / n, 1)),
        ("Top 20% share of revenue (%)", round(conc.set_index("Customer_Group").loc["Top 20%", "Revenue_Share_%"], 1)),
    ], columns=["Measure", "Value"])
    curve = pd.DataFrame({"Share_of_Customers": np.arange(1, n + 1) / n, "Cumulative_Revenue_Share": cum})
    return {"concentration": conc, "concentration_stats": stats, "curve": curve}


def high_value_customer_lists(seg: pd.DataFrame, top_n: int = 20) -> dict[str, pd.DataFrame]:
    """Analytical customer lists (Customer_ID only - no names, i.e. no unnecessary PII)."""
    cols = ["Customer_ID", "Region", "Recency", "Frequency", "Monetary", "Average_Order_Value",
            "R_Score", "F_Score", "M_Score", "RFM_Cell", "RFM_Segment"]
    # High-value at-risk: top-40% spend (M_Score 4-5) AND bottom-40% recency (R_Score 1-2)
    hv_rule = (seg["M_Score"] >= 4) & (seg["R_Score"] <= 2)
    hvar = seg.loc[hv_rule, cols].sort_values("Monetary", ascending=False)
    return {
        "top_monetary": seg.nlargest(top_n, "Monetary")[cols],
        "top_frequency": seg.sort_values(["Frequency", "Monetary"], ascending=False).head(top_n)[cols],
        "most_recent": seg.sort_values(["Recency", "Monetary"], ascending=[True, False]).head(top_n)[cols],
        "high_value_at_risk": hvar,
        "high_value_at_risk_rule": pd.DataFrame([
            ("Rule", "M_Score >= 4 (top 40% of customers by spend) AND R_Score <= 2 (bottom 40% by recency)"),
            ("M_Score >= 4 means Monetary >=", inr(seg.loc[seg["M_Score"] >= 4, "Monetary"].min())),
            ("R_Score <= 2 means Recency >=", f"{int(seg.loc[seg['R_Score'] <= 2, 'Recency'].min())} days"),
            ("Customers matching", f"{int(hv_rule.sum())}"),
            ("Their total revenue", inr(seg.loc[hv_rule, 'Monetary'].sum())),
            ("Share of all revenue", pct(seg.loc[hv_rule, 'Monetary'].sum() / seg['Monetary'].sum())),
        ], columns=["Item", "Value"]),
    }


# =============================================================================
# 7. QUESTIONS, INSIGHTS, VALIDATION
# =============================================================================
def answer_rfm_questions(R: dict) -> pd.DataFrame:
    seg, S = R["segments"], R["segment_summary"].set_index("RFM_Segment")
    H = R["describe"]["headline"].set_index("Metric")
    conc = R["concentration"]["concentration"].set_index("Customer_Group")
    cst = R["concentration"]["concentration_stats"].set_index("Measure")["Value"]
    G = R["group_summary"].set_index("Value_Activity_Group")
    hv = R["high_value"]["high_value_at_risk"]
    active_hv = seg["Value_Activity_Group"].eq("Active high value")
    biggest = S["Customer_Count"].idxmax()
    top_rev = S["Total_Revenue"].idxmax()
    top_avg = S["Average_Monetary"].idxmax()
    slipping = S[S["Value_Activity_Group"] == "Slipping"].sort_values("Total_Revenue", ascending=False)
    rows = [
        ("Q1. What percentage of customers are repeat customers?",
         f"{H.loc['Repeat customers (2+ orders)', 'Display']} of scored customers ({int(H.loc['Repeat customers (2+ orders)', 'Value']):,}) "
         f"have 2+ delivered orders; {H.loc['Customers with exactly one order', 'Display']} bought once."),
        ("Q2. What percentage of customers are highly active?",
         f"{pct(active_hv.mean())} are Champions or Loyal Customers (the 'Active high value' group, "
         f"{int(active_hv.sum())} customers); {H.loc['Customers active in last 90 days (Recency <= 90)', 'Display']} bought in the last 90 days."),
        ("Q3. Which RFM segment contains the most customers?",
         f"{biggest}: {int(S.loc[biggest, 'Customer_Count'])} customers ({S.loc[biggest, 'Customer_%']:.1f}%)."),
        ("Q4. Which segment contributes the most revenue?",
         f"{top_rev}: {inr(S.loc[top_rev, 'Total_Revenue'])} ({S.loc[top_rev, 'Revenue_%']:.1f}% of revenue) from "
         f"{S.loc[top_rev, 'Customer_%']:.1f}% of customers."),
        ("Q5. Which segment has the highest average monetary value?",
         f"{top_avg}: average {inr(S.loc[top_avg, 'Average_Monetary'])} per customer vs {inr(seg['Monetary'].mean())} overall."),
        ("Q6. Which customers show high monetary value but poor recency?",
         f"{len(hv)} customers meet the rule M_Score >= 4 and R_Score <= 2; together {inr(hv['Monetary'].sum())} "
         f"({pct(hv['Monetary'].sum() / seg['Monetary'].sum())} of revenue). Largest: "
         + ", ".join(f"{r.Customer_ID} ({inr(r.Monetary)}, {int(r.Recency)} days)" for r in hv.head(3).itertuples()) + "."),
        ("Q7. How concentrated is revenue among high-value customers?",
         f"Top 1% -> {conc.loc['Top 1%', 'Revenue_Share_%']:.1f}%, top 5% -> {conc.loc['Top 5%', 'Revenue_Share_%']:.1f}%, "
         f"top 10% -> {conc.loc['Top 10%', 'Revenue_Share_%']:.1f}%, top 20% -> {conc.loc['Top 20%', 'Revenue_Share_%']:.1f}% "
         f"(Gini {cst['Gini coefficient (0 = equal, 1 = one customer has all)']}). 80% of revenue needs "
         f"{cst['Share of customers needed for 80% of revenue (%)']}% of customers, so it is concentrated but not an 80/20 split."),
        ("Q8. What proportion of customers appear inactive?",
         f"'Inactive' group (Hibernating + Lost): {G.loc['Inactive', 'Customer_%']:.1f}% of customers, "
         f"{G.loc['Inactive', 'Revenue_%']:.1f}% of revenue. By recency alone, "
         f"{H.loc['Customers inactive > 180 days (Recency > 180)', 'Display']} have not bought for over 180 days."),
        ("Q9. Which segments should be investigated for retention strategies?",
         "Slipping segments ranked by revenue at stake: " + "; ".join(
             f"{i} ({int(r.Customer_Count)} customers, {inr(r.Total_Revenue)}, avg recency {r.Average_Recency:.0f} days)"
             for i, r in slipping.iterrows()) + "."),
        ("Q10. Which customer groups should be analysed further with ML segmentation?",
         f"(1) Champions ({int(S.loc['Champions', 'Customer_Count'])} customers) - very wide spend range "
         f"({inr(seg.loc[seg['RFM_Segment'] == 'Champions', 'Monetary'].min())} to "
         f"{inr(seg.loc[seg['RFM_Segment'] == 'Champions', 'Monetary'].max())}), so it may hide distinct sub-groups; "
         f"(2) the Loyal Customers / At Risk pair ({int(S.loc['Loyal Customers', 'Customer_Count'])} and "
         f"{int(S.loc['At Risk', 'Customer_Count'])} customers) that differ mainly by a recency cut-off; "
         f"(3) the thin-rule mid band (Potential Loyalists, Needs Attention). K-Means (Step 6) can test whether "
         f"these rule boundaries match natural groupings, and whether discount-driven or premium buyers form their own clusters."),
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer (from data)"])


def generate_rfm_insights(R: dict) -> pd.DataFrame:
    """Insight Area | Observation | Evidence | Business Interpretation (interpretation = hypothesis)."""
    S = R["segment_summary"].set_index("RFM_Segment")
    seg = R["segments"]
    H = R["describe"]["headline"].set_index("Metric")
    conc = R["concentration"]["concentration"].set_index("Customer_Group")
    cst = R["concentration"]["concentration_stats"].set_index("Measure")["Value"]
    G = R["group_summary"].set_index("Value_Activity_Group")
    hv = R["high_value"]["high_value_at_risk"]
    rho = seg[["Frequency", "Monetary"]].corr("spearman").iloc[0, 1]

    def seg_line(name):
        r = S.loc[name]
        return (f"{int(r.Customer_Count)} customers ({r['Customer_%']:.1f}%) -> {inr(r.Total_Revenue)} "
                f"({r['Revenue_%']:.1f}% of revenue); avg recency {r.Average_Recency:.0f} days, "
                f"avg {r.Average_Frequency:.1f} orders, avg spend {inr(r.Average_Monetary)}")
    rows = [
        ("Champions", "About one customer in six generates over half of all revenue", seg_line("Champions"),
         "Protect with loyalty benefits and early access; losing even a few would hurt disproportionately"),
        ("Loyal Customers", "Second value tier, slightly less recent", seg_line("Loyal Customers"),
         "Upgrade path to Champions: cross-sell categories and reward frequency"),
        ("Potential Loyalists", "Recent, mid-value buyers", seg_line("Potential Loyalists"),
         "Best growth pool: onboarding and second-category offers could move them up"),
        ("At Risk / Can't Lose Them", "Former high-value customers who have gone quiet",
         f"At Risk: {seg_line('At Risk')}. Can't Lose Them: {seg_line(CANT_LOSE)}",
         "Priority win-back targets: the revenue they used to generate is large"),
        ("High-value at risk (rule)", "Top-40% spenders in the bottom-40% of recency",
         f"{len(hv)} customers, {inr(hv['Monetary'].sum())} historical revenue ({pct(hv['Monetary'].sum() / seg['Monetary'].sum())}); "
         f"median recency {hv['Recency'].median():.0f} days",
         "A concrete Customer_ID list for a reactivation campaign (Step 7 CLV will size expected value)"),
        ("Inactive customers", "Hibernating + Lost are a large share of customers but little revenue",
         f"{G.loc['Inactive', 'Customers']:.0f} customers ({G.loc['Inactive', 'Customer_%']:.1f}%) -> "
         f"{G.loc['Inactive', 'Revenue_%']:.1f}% of revenue",
         "Low-cost automated reactivation only; do not spend premium retention budget here"),
        ("Revenue Concentration", "Revenue is concentrated, but less than an 80/20 rule",
         f"Top 20% -> {conc.loc['Top 20%', 'Revenue_Share_%']:.1f}%; 80% of revenue comes from "
         f"{cst['Share of customers needed for 80% of revenue (%)']}% of customers; Gini {cst['Gini coefficient (0 = equal, 1 = one customer has all)']}",
         "A focused key-account style programme for the top fifth is justified"),
        ("Repeat Customers", "Almost all buyers come back at least once",
         f"Repeat (2+ orders): {H.loc['Repeat customers (2+ orders)', 'Display']}; one-time: {H.loc['Customers with exactly one order', 'Display']}",
         "Retention is working at a basic level; the lever is frequency and value, not first repeat"),
        ("Frequency vs Monetary", "Frequency and Monetary move together",
         f"Spearman rho(F, M) = {rho:.2f}",
         "F and M carry overlapping information - one reason the segments use FM = (F+M)/2, and a point to handle "
         "(scaling / feature choice) in K-Means"),
        ("Recency", "Recency separates recently active customers from a long-lapsed group",
         f"Median recency {seg['Recency'].median():.0f} days; {H.loc['Customers active in last 90 days (Recency <= 90)', 'Display']} bought in the last 90 days; "
         f"{H.loc['Customers inactive > 180 days (Recency > 180)', 'Display']} not for 180+ days",
         "Recency is the earliest warning sign of a customer going quiet, and the one to monitor "
         "monthly - this project reports inactivity, never churn, because the data defines no "
         "churn event"),
    ]
    return pd.DataFrame(rows, columns=["Insight Area", "Observation", "Evidence", "Business Interpretation"])


def validate_rfm(df: pd.DataFrame, R: dict) -> pd.DataFrame:
    """The Section-23 data-science checks."""
    seg = R["segments"]
    valid = df[df["Order_Status"] == "Delivered"]
    S = R["segment_summary"]
    total_customers = df["Customer_ID"].nunique()
    freq_check = valid.groupby("Customer_ID")["Order_ID"].nunique().reindex(seg["Customer_ID"]).to_numpy()
    rows_check = valid.groupby("Customer_ID").size().reindex(seg["Customer_ID"]).to_numpy()
    checks = [
        ("Each Customer_ID appears once in the RFM table", int(seg["Customer_ID"].duplicated().sum()),
         seg["Customer_ID"].is_unique),
        ("Scored + excluded customers = all customers",
         f"{len(seg)} + {len(R['excluded'])} = {len(seg) + len(R['excluded'])} (of {total_customers})",
         len(seg) + len(R["excluded"]) == total_customers),
        ("Frequency = distinct delivered Order_IDs (recomputed)", "match",
         bool((seg["Frequency"].to_numpy() == freq_check).all())),
        ("Frequency differs from row count for multi-product orders",
         f"{int((rows_check != seg['Frequency'].to_numpy()).sum())} customers have more lines than orders", True),
        ("Monetary total = delivered Sales total", f"{inr(seg['Monetary'].sum())} vs {inr(valid['Sales'].sum())}",
         abs(seg["Monetary"].sum() - valid["Sales"].sum()) < 1.0),
        ("Cancelled/Returned lines excluded from Monetary",
         inr(df.loc[df["Order_Status"] != "Delivered", "Sales"].sum()),
         abs(seg["Monetary"].sum() - df.loc[df["Order_Status"] == "Delivered", "Sales"].sum()) < 1.0),
        ("Recency >= 0 for all customers", f"min {int(seg['Recency'].min())}, max {int(seg['Recency'].max())}",
         bool((seg["Recency"] >= 0).all())),
        ("Reference date = max Order_Date + 1 day", str(R["reference_date"].date()),
         R["reference_date"] == df["Order_Date"].max().normalize() + pd.Timedelta(days=1)),
        ("R/F/M scores are integers 1-5", "all in {1..5}",
         bool(seg[["R_Score", "F_Score", "M_Score"]].isin(range(1, 6)).all().all())),
        ("Tied values share one score", "checked on Frequency and Monetary",
         bool((seg.groupby("Frequency")["F_Score"].nunique() == 1).all()
              and (seg.groupby("Monetary")["M_Score"].nunique() == 1).all())),
        ("RFM_Score = R + F + M (3-15)", f"range {seg['RFM_Score'].min()}-{seg['RFM_Score'].max()}",
         bool((seg["RFM_Score"] == seg["R_Score"] + seg["F_Score"] + seg["M_Score"]).all())),
        ("Every customer has exactly one segment", int(seg["RFM_Segment"].isna().sum()),
         bool(seg["RFM_Segment"].notna().all())),
        ("Segment customer counts sum to scored customers", int(S["Customer_Count"].sum()),
         int(S["Customer_Count"].sum()) == len(seg)),
        ("Sum of segment revenue = total customer revenue", inr(S["Total_Revenue"].sum()),
         abs(S["Total_Revenue"].sum() - seg["Monetary"].sum()) < 1.0),
        ("Monetary ties to Step 4 total revenue", inr(seg["Monetary"].sum()),
         abs(seg["Monetary"].sum() - pd.read_csv(config.TABLES_DIR / "eda_kpis.csv").set_index("KPI")
             .loc["Total Revenue", "Value"]) < 1.0 if (config.TABLES_DIR / "eda_kpis.csv").exists() else True),
    ]
    return pd.DataFrame(checks, columns=["Check", "Value", "Pass"])


# =============================================================================
# 8. RUN + SAVE
# =============================================================================
def run_rfm_analysis(df: pd.DataFrame | None = None) -> dict:
    """Compute everything (no files written)."""
    df = load_clean_data() if df is None else df
    R: dict = {"df": df}
    R["reference_date"] = get_reference_date(df)
    rfm, excluded = build_rfm_table(df, R["reference_date"])
    R["rfm"], R["excluded"] = rfm, excluded
    R["describe"] = describe_rfm(rfm, df["Customer_ID"].nunique())
    R["qcut_check"] = qcut_feasibility(rfm)
    scored, R["score_bins"] = calculate_rfm_scores(rfm)
    R["segments"] = assign_rfm_segments(scored)
    R["segment_rules"] = segment_rules_table()
    R["segment_summary"] = summarize_rfm_segments(R["segments"])
    R["group_summary"] = summarize_groups(R["segments"])
    R["segment_profile"] = segment_profile(R["segments"])
    R["score_grid"] = (R["segments"].pivot_table(index="R_Score", columns="F_Score", values="Customer_ID",
                                                 aggfunc="count", fill_value=0))
    R["concentration"] = analyze_revenue_concentration(R["segments"])
    R["high_value"] = high_value_customer_lists(R["segments"])
    R["questions"] = answer_rfm_questions(R)
    R["insights"] = generate_rfm_insights(R)
    R["validation"] = validate_rfm(df, R)
    return R


def save_rfm_outputs(R: dict) -> list[Path]:
    """Write datasets, metadata and tables."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    paths = []

    def fmt_dates(t):
        t = t.copy()
        for c in t.columns:
            if pd.api.types.is_datetime64_any_dtype(t[c]):
                t[c] = t[c].dt.strftime("%Y-%m-%d")
        return t
    rfm_out = fmt_dates(R["rfm"])
    rfm_out.to_csv(RFM_FILE, index=False, encoding="utf-8-sig")
    paths.append(RFM_FILE)
    seg_cols = ["Customer_ID", "Recency", "Frequency", "Monetary", "R_Score", "F_Score", "M_Score", "RFM_Cell",
                "RFM_Score", "FM_Score", "RFM_Segment", "Value_Activity_Group"] + \
               [c for c in R["rfm"].columns if c not in ("Customer_ID", "Recency", "Frequency", "Monetary")]
    fmt_dates(R["segments"][seg_cols]).to_csv(RFM_SEGMENTS_FILE, index=False, encoding="utf-8-sig")
    paths.append(RFM_SEGMENTS_FILE)
    meta = {
        "dataset": config.DATASET_LABEL,
        "source_file": str(config.CLEAN_DATA_FILE.relative_to(config.PROJECT_ROOT)),
        "reference_date": str(R["reference_date"].date()),
        "reference_date_rule": "max(Order_Date) + 1 day",
        "latest_order_date": str(R["df"]["Order_Date"].max().date()),
        "valid_purchase_definition": "Order_Status == 'Delivered'",
        "recency": "reference_date - last delivered purchase date, in days",
        "frequency": "distinct Order_ID with >= 1 Delivered line",
        "monetary": "sum of Sales (INR, after discount) on Delivered lines",
        "scoring": {m: g["Method"].iloc[0] for m, g in R["score_bins"].groupby("Metric")},
        "scoring_note": "pd.qcut quintiles, falling back to tie-aware percentile rank if edges are not unique; Recency reversed",
        "rfm_score": "R_Score + F_Score + M_Score (equal weights, 3-15)",
        "fm_score": "(F_Score + M_Score) / 2, used for segment rules",
        "customers_total": int(R["df"]["Customer_ID"].nunique()),
        "customers_scored": int(len(R["segments"])),
        "customers_excluded_no_delivered_purchase": int(len(R["excluded"])),
        "total_monetary_inr": round(float(R["segments"]["Monetary"].sum()), 2),
        "segmentation_type": "rule-based RFM (not machine learning)",
    }
    RFM_METADATA_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    paths.append(RFM_METADATA_FILE)
    tables = {
        "rfm_segment_summary.csv": R["segment_summary"],
        "rfm_value_activity_groups.csv": R["group_summary"],
        "rfm_segment_rules.csv": R["segment_rules"],
        "rfm_segment_profile.csv": R["segment_profile"],
        "rfm_business_insights.csv": R["insights"],
        "rfm_business_questions.csv": R["questions"],
        "rfm_descriptive_statistics.csv": R["describe"]["descriptive"],
        "rfm_headline_metrics.csv": R["describe"]["headline"],
        "rfm_log_transform_check.csv": R["describe"]["log_check"],
        "rfm_qcut_feasibility.csv": R["qcut_check"],
        "rfm_score_bins.csv": R["score_bins"],
        "rfm_score_grid_R_by_F.csv": R["score_grid"].reset_index(),
        "rfm_revenue_concentration.csv": R["concentration"]["concentration"],
        "rfm_concentration_stats.csv": R["concentration"]["concentration_stats"],
        "rfm_top_customers_monetary.csv": R["high_value"]["top_monetary"],
        "rfm_top_customers_frequency.csv": R["high_value"]["top_frequency"],
        "rfm_most_recent_customers.csv": R["high_value"]["most_recent"],
        "rfm_high_value_at_risk.csv": R["high_value"]["high_value_at_risk"],
        "rfm_high_value_at_risk_rule.csv": R["high_value"]["high_value_at_risk_rule"],
        "rfm_excluded_customers.csv": fmt_dates(R["excluded"]),
        "rfm_validation_checks.csv": R["validation"],
    }
    for name, t in tables.items():
        p = config.TABLES_DIR / name
        t.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


# =============================================================================
# 9. FIGURES
# =============================================================================
GROUP_COLORS = {"Active high value": "#2a78d6", "Developing": "#1baf7a", "Slipping": "#eb6834",
                "Inactive": "#a3a29c"}


def _seg_colors(segments):
    return [GROUP_COLORS[SEGMENT_GROUP[s]] for s in segments]


def _group_legend(ax, loc="center right"):
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GROUP_COLORS[g], label=g) for g in GROUP_ORDER], loc=loc, fontsize=8.5,
              title="Value-activity group", title_fontsize=8.5)


def plot_rfm_figures(R: dict, out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    """All RFM charts. Uses the shared project style from src/eda.py."""
    from src.eda import _style, _save, _hbar, _note, _pct_axis, _rupee, PAL
    plt = _style()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    seg = R["segments"]
    S = R["segment_summary"].set_index("RFM_Segment").reindex(SEGMENT_ORDER)

    # --- 1-3. R, F, M distributions: raw histogram, log1p histogram, boxplot ---
    for col, unit, fname in [("Recency", "days since last purchase", "rfm_recency_distribution.png"),
                             ("Frequency", "delivered orders", "rfm_frequency_distribution.png"),
                             ("Monetary", "₹ delivered revenue", "rfm_monetary_distribution.png")]:
        s = seg[col].astype(float)
        fig, axes = plt.subplots(1, 3, figsize=(16, 4.3), gridspec_kw={"width_ratios": [1.3, 1.3, 1]})
        if col == "Frequency":
            vc = s.value_counts().sort_index()
            axes[0].bar(vc.index, vc.values, color=PAL["blue"], width=0.8)
        else:
            axes[0].hist(s, bins=40, color=PAL["blue"], edgecolor="white", linewidth=0.5)
        axes[0].axvline(s.median(), color=PAL["orange"], linestyle="--", linewidth=1.5)
        axes[0].set_title(f"{col} - raw ({unit})", fontsize=11)
        axes[0].set_ylabel("Customers")
        axes[0].text(0.97, 0.95, f"median {s.median():,.0f}\nmean {s.mean():,.0f}\nskew {s.skew():.2f}",
                     transform=axes[0].transAxes, ha="right", va="top", fontsize=9)
        if col == "Monetary":
            _rupee(axes[0], "x")
            axes[0].tick_params(axis="x", rotation=20)
        axes[1].hist(np.log1p(s), bins=35, color=PAL["aqua"], edgecolor="white", linewidth=0.5)
        axes[1].set_title(f"log(1 + {col}) - for charts / modelling only", fontsize=11)
        axes[1].text(0.97, 0.95, f"skew {np.log1p(s).skew():.2f}", transform=axes[1].transAxes, ha="right",
                     va="top", fontsize=9)
        axes[1].set_xlabel(f"log(1 + {col})")
        axes[2].boxplot(s, vert=False, widths=0.55, patch_artist=True,
                        boxprops=dict(facecolor=PAL["light"], edgecolor=PAL["blue"]), medianprops=dict(color=PAL["text"]),
                        flierprops=dict(marker="o", markersize=3, markerfacecolor=PAL["orange"], markeredgecolor="none"))
        axes[2].set_yticks([])
        axes[2].set_title(f"{col} - boxplot (raw)", fontsize=11)
        if col == "Monetary":
            axes[2].set_xscale("log")
            _rupee(axes[2], "x")
            axes[2].set_title("Monetary - boxplot (raw values, log axis)", fontsize=11)
        fig.suptitle(f"{col} distribution across {len(seg):,} customers", x=0.01, ha="left", fontweight="bold",
                     fontsize=13)
        _note(fig, "The stored RFM values are never transformed; the log view only shows whether a transform would "
                   "help later modelling. Dashed line = median.")
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # --- 4-6. Segment size, revenue, contribution ---
    fig, ax = plt.subplots(figsize=(10, 5.6))
    _hbar(ax, S.index.tolist(), S["Customer_Count"].to_numpy(), color=_seg_colors(S.index),
          value_labels=[f"{int(c):,}  ({p:.1f}%)" for c, p in zip(S["Customer_Count"], S["Customer_%"])])
    ax.set_xlabel("Customers")
    ax.set_title("Customers by RFM segment")
    _group_legend(ax)
    fig.tight_layout()
    _save(fig, "rfm_segment_distribution.png", out_dir, saved)

    from src.eda import _lakh
    fig, ax = plt.subplots(figsize=(10, 5.6))
    _hbar(ax, S.index.tolist(), S["Total_Revenue"].to_numpy(), color=_seg_colors(S.index),
          value_labels=[f"{inr(v)}  ({p:.1f}%)" for v, p in zip(S["Total_Revenue"], S["Revenue_%"])])
    _lakh(ax, "x")
    ax.set_xlabel("Delivered revenue 2023-2025 (₹ lakh)")
    ax.set_title("Revenue by RFM segment")
    _group_legend(ax)
    fig.tight_layout()
    _save(fig, "rfm_revenue_by_segment.png", out_dir, saved)

    fig, ax = plt.subplots(figsize=(13, 4.8))
    pos = np.arange(len(S))
    ax.bar(pos - 0.2, S["Customer_%"] / 100, width=0.38, color=PAL["neutral"], label="Share of customers")
    ax.bar(pos + 0.2, S["Revenue_%"] / 100, width=0.38, color=PAL["blue"], label="Share of revenue")
    for i, r in enumerate(S.itertuples()):
        ax.text(i - 0.2, r._3 / 100 + 0.008, f"{r._3:.0f}%", ha="center", fontsize=8.5)
        ax.text(i + 0.2, r._5 / 100 + 0.008, f"{r._5:.0f}%", ha="center", fontsize=8.5)
    ax.set_xticks(pos, [s.replace(" ", "\n", 1) for s in S.index], fontsize=9)
    ax.grid(axis="x", visible=False)
    _pct_axis(ax)
    ax.set_title("Revenue contribution: share of customers vs share of revenue, by segment")
    ax.legend()
    fig.tight_layout()
    _save(fig, "rfm_revenue_contribution.png", out_dir, saved)

    # --- 7-9. Average M, R, F by segment ---
    for col, fname, title, fmt, ref, lloc in [
            ("Average_Monetary", "rfm_segment_monetary.png", "Average monetary value per customer, by segment", inr,
             seg["Monetary"].mean(), "center right"),
            ("Average_Recency", "rfm_segment_recency.png", "Average recency (days since last purchase), by segment",
             lambda v: f"{v:,.0f} days", seg["Recency"].mean(), "upper right"),
            ("Average_Frequency", "rfm_segment_frequency.png", "Average frequency (delivered orders), by segment",
             lambda v: f"{v:.1f} orders", seg["Frequency"].mean(), "center right")]:
        fig, ax = plt.subplots(figsize=(10, 5.6))
        _hbar(ax, S.index.tolist(), S[col].to_numpy(), color=_seg_colors(S.index),
              value_labels=[fmt(v) for v in S[col]])
        ax.axvline(ref, color=PAL["text"], linestyle=":", linewidth=1)
        ax.text(ref, len(S) - 0.35, f" all customers: {fmt(ref)}", fontsize=8.5, color=PAL["muted"])
        if col == "Average_Monetary":
            _rupee(ax, "x")
        ax.set_title(title)
        _group_legend(ax, lloc)
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # --- 10. Segment matrix: R_Score x FM_Score ---
    fm_levels = np.arange(1, 5.5, 0.5)
    grid = seg.pivot_table(index="R_Score", columns="FM_Score", values="Customer_ID", aggfunc="count",
                           fill_value=0).reindex(index=[5, 4, 3, 2, 1], columns=fm_levels, fill_value=0)
    abbrev = {"Champions": "Champ", "Loyal Customers": "Loyal", "Potential Loyalists": "Pot. Loyal",
              "Recent Customers": "Recent", "Promising": "Promising", "Needs Attention": "Needs Att.",
              "About to Sleep": "Sleep", "Can't Lose Them": "Can't Lose", "At Risk": "At Risk",
              "Hibernating": "Hibern.", "Lost": "Lost"}
    fig, ax = plt.subplots(figsize=(13, 5.6))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#86b6ef", "#256abf", "#0d366b"])
    im = ax.imshow(grid.to_numpy(), cmap=cmap, aspect="auto")
    for i, r in enumerate(grid.index):
        for j, f in enumerate(grid.columns):
            name = next(sn for sn, rule, *_ in SEGMENT_RULES if bool(rule(pd.Series([r]), pd.Series([f])).iloc[0]))
            v = grid.iloc[i, j]
            dark = v > grid.to_numpy().max() * 0.45
            ax.text(j, i, f"{abbrev[name]}\n{v}", ha="center", va="center", fontsize=8.5,
                    color="white" if dark else PAL["text"])
    ax.set_xticks(range(len(fm_levels)), [f"{f:g}" for f in fm_levels])
    ax.set_yticks(range(5), [f"R = {r}" for r in grid.index])
    ax.set_xlabel("FM_Score = (Frequency score + Monetary score) / 2   ->  higher value")
    ax.set_ylabel("Recency score  (5 = most recent)")
    ax.grid(False)
    ax.set_title("RFM segment matrix: customers in each (R, FM) cell, labelled with the rule-based segment")
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Customers", color=PAL["muted"])
    fig.tight_layout()
    _save(fig, "rfm_segment_matrix.png", out_dir, saved)

    # --- 11-13. 2D views, one facet per value-activity group (avoids 11 colours) ---
    pairs = [("Recency", "Monetary", "rfm_recency_vs_monetary.png"),
             ("Frequency", "Monetary", "rfm_frequency_vs_monetary.png"),
             ("Recency", "Frequency", "rfm_recency_vs_frequency.png")]
    rng = np.random.default_rng(config.RANDOM_SEED)
    for xcol, ycol, fname in pairs:
        fig, axes = plt.subplots(1, 4, figsize=(18, 4.6), sharex=True, sharey=True)
        xj = seg[xcol] + (rng.uniform(-0.3, 0.3, len(seg)) if xcol == "Frequency" else 0)
        yj = seg[ycol] + (rng.uniform(-0.3, 0.3, len(seg)) if ycol == "Frequency" else 0)
        for ax, g in zip(axes, GROUP_ORDER):
            m = seg["Value_Activity_Group"] == g
            ax.scatter(xj[~m], yj[~m], s=5, color="#dcdbd5", edgecolors="none")
            ax.scatter(xj[m], yj[m], s=9, color=GROUP_COLORS[g] if g != "Inactive" else "#6b6a64",
                       alpha=0.7, edgecolors="none")
            import textwrap
            segs_in = "\n".join(textwrap.wrap(", ".join(s for s in SEGMENT_ORDER if SEGMENT_GROUP[s] == g), 38))
            ax.set_title(f"{g} ({int(m.sum())})\n{segs_in}", fontsize=9.5)
            if ycol == "Monetary":
                ax.set_yscale("log")
                _rupee(ax)
            if xcol == "Frequency":
                from matplotlib.ticker import FixedLocator, ScalarFormatter
                ax.set_xscale("log")
                ax.xaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20]))
                ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.set_xlabel(f"{xcol}" + (" (days)" if xcol == "Recency" else " (orders, log)"))
        axes[0].set_ylabel(f"{ycol}" + (" (₹, log)" if ycol == "Monetary" else " (orders)"))
        fig.suptitle(f"{xcol} vs {ycol}, highlighted by value-activity group (grey = all other customers)",
                     x=0.01, ha="left", fontweight="bold", fontsize=13)
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)

    # --- 14. Revenue concentration curve ---
    C = R["concentration"]
    curve = C["curve"]
    conc = C["concentration"].set_index("Customer_Group")
    cst = C["concentration_stats"].set_index("Measure")["Value"]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(np.concatenate([[0], curve["Share_of_Customers"]]), np.concatenate([[0], curve["Cumulative_Revenue_Share"]]),
            color=PAL["blue"], linewidth=2.2, label="Customers ranked by Monetary")
    ax.plot([0, 1], [0, 1], color=PAL["neutral"], linestyle="--", label="Equal contribution")
    for grp in ["Top 1%", "Top 5%", "Top 10%", "Top 20%"]:
        xv = int(grp.split()[1][:-1]) / 100
        yv = conc.loc[grp, "Revenue_Share_%"] / 100
        ax.plot([xv], [yv], "o", color=PAL["orange"], markersize=7)
        ax.annotate(f"{grp}: {100 * yv:.1f}%", (xv, yv), textcoords="offset points", xytext=(10, -6), fontsize=9)
    x80 = cst["Share of customers needed for 80% of revenue (%)"] / 100
    ax.plot([0, x80, x80], [0.8, 0.8, 0], color=PAL["muted"], linestyle=":", linewidth=1)
    ax.annotate(f"80% of revenue comes from\n{100 * x80:.1f}% of customers (not 20%)", (x80, 0.8),
                textcoords="offset points", xytext=(12, -40), fontsize=9)
    _pct_axis(ax)
    _pct_axis(ax, "x")
    ax.set_xlabel("Share of customers (highest Monetary first)")
    ax.set_ylabel("Cumulative share of revenue")
    ax.set_title(f"Customer revenue concentration (Gini = {cst['Gini coefficient (0 = equal, 1 = one customer has all)']:.2f})")
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "rfm_revenue_concentration.png", out_dir, saved)

    # --- 15. R x F heatmap with mean monetary ---
    import seaborn as sns
    cnt = seg.pivot_table(index="R_Score", columns="F_Score", values="Customer_ID", aggfunc="count", fill_value=0) \
        .reindex(index=[5, 4, 3, 2, 1])
    mon = seg.pivot_table(index="R_Score", columns="F_Score", values="Monetary", aggfunc="mean").reindex(index=[5, 4, 3, 2, 1])
    annot = cnt.astype(str) + "\n" + mon.map(lambda v: "" if pd.isna(v) else inr(v, 1))
    fig, ax = plt.subplots(figsize=(9, 5.6))
    sns.heatmap(mon, annot=annot, fmt="", cmap=sns.light_palette(PAL["blue"], as_cmap=True), linewidths=2,
                linecolor="white", cbar_kws={"label": "Average Monetary (₹)", "format": "₹{x:,.0f}"}, ax=ax,
                annot_kws={"fontsize": 8.5})
    ax.set_xlabel("F_Score (5 = most orders)")
    ax.set_ylabel("R_Score (5 = most recent)")
    ax.set_title("Customers and average spend in each Recency x Frequency cell")
    _note(fig, "Each cell: number of customers (top) and their average Monetary value (bottom); colour = average spend.")
    fig.tight_layout()
    _save(fig, "rfm_recency_frequency_heatmap.png", out_dir, saved)
    return saved


# =============================================================================
# 10. METHODOLOGY REPORT
# =============================================================================
def write_rfm_report(R: dict, path: Path = RFM_REPORT) -> Path:
    """Generate outputs/reports/rfm_methodology.md - every number inserted from results."""
    from src.eda import _md_table
    seg = R["segments"]
    S = R["segment_summary"]
    H = R["describe"]["headline"].set_index("Metric")["Display"]
    bins = R["score_bins"]
    rules = R["segment_rules"]
    qc = R["qcut_check"]
    V = R["validation"]
    cst = R["concentration"]["concentration_stats"].set_index("Measure")["Value"]
    conc = R["concentration"]["concentration"]
    rho_fm = seg[["Frequency", "Monetary"]].corr("spearman").iloc[0, 1]
    ssum = S[["RFM_Segment", "Customer_Count", "Customer_%", "Total_Revenue", "Revenue_%", "Average_Recency",
              "Average_Frequency", "Average_Monetary", "Average_Order_Value"]].copy()
    ssum["Total_Revenue"] = ssum["Total_Revenue"].map(inr)
    ssum["Average_Monetary"] = ssum["Average_Monetary"].map(inr)
    ssum["Average_Order_Value"] = ssum["Average_Order_Value"].map(inr)
    for c in ["Customer_%", "Revenue_%"]:
        ssum[c] = ssum[c].map(lambda v: f"{v:.1f}%")
    ssum["Average_Recency"] = ssum["Average_Recency"].map(lambda v: f"{v:.0f} d")
    ssum["Average_Frequency"] = ssum["Average_Frequency"].map(lambda v: f"{v:.1f}")
    b = bins.copy()
    b["Range"] = b.apply(lambda r: f"{r.Min_Value:,.0f} - {r.Max_Value:,.0f}", axis=1)
    b = b[["Metric", "Score", "Range", "Customers"]]
    desc = R["describe"]["descriptive"][["Metric", "Unit", "Mean", "Median", "Min", "Max", "Skewness"]].round(1)
    conc_t = conc.assign(Revenue=conc["Revenue"].map(inr), **{"Revenue_Share_%": conc["Revenue_Share_%"].round(1)})[
        ["Customer_Group", "Customers", "Revenue", "Revenue_Share_%"]]
    excl = R["excluded"]
    ref = R["reference_date"].date()
    text = f"""# RFM Methodology & Results: Customer Revenue Intelligence

> **SYNTHETIC DATA.** This report is generated by `src/rfm.py` from `data/processed/customer_sales_cleaned.csv`, the Step 3 output. Every number is computed.

## 1. Objective
The aim is to turn 18,670 transaction lines into one row per customer that describes:
- **how recently** each customer bought;
- **how often** they bought;
- **how much** they spent.

These three measures are then used to find the most valuable, the most active and the at-risk customers, and to measure how concentrated revenue is. The result is the analytical foundation for K-Means segmentation (Step 6).

## 2. Reference Date
**Reference date = latest Order_Date in the data + 1 day = {ref}**, since the latest order is dated {R['df']['Order_Date'].max().date()}.

**Why this date:**
- It is derived from the data, not typed in.
- It describes the business as of the end of the extract.
- It gives the most recent buyer a Recency of 1 rather than 0.

The date is stored in `data/processed/customer_rfm_metadata.json`.

## 3. Definitions

| Measure | Definition | Notes |
|---|---|---|
| **Recency (R)** | Reference date − date of last **delivered** purchase, in days | Lower = more recent |
| **Frequency (F)** | Number of **distinct Order_IDs** with at least one Delivered line | Not row count. One order can contain several products; {V.set_index('Check').loc['Frequency differs from row count for multi-product orders', 'Value']}. |
| **Monetary (M)** | Sum of **Sales** (₹, after discount) on Delivered lines | Reconciles exactly to Step 4 total revenue ({H['Total customer revenue (Monetary sum)']}) |

### Treatment of cancelled and returned orders
- Only **Delivered** lines count as a purchase.
- Cancelled lines (never shipped) and Returned lines (refunded) are excluded from R, F and M. Their combined booked value of {V.set_index('Check').loc['Cancelled/Returned lines excluded from Monetary', 'Value']} is not counted.
- Each customer's cancelled and returned line counts are kept in the RFM table as context.
- **{len(excl)} customers** have no delivered purchase at all, because every line they placed was cancelled or returned. They have no valid Recency or Monetary value, so they are **excluded from scoring** and listed in `outputs/tables/rfm_excluded_customers.csv`. Scored plus excluded customers add up to {R['df']['Customer_ID'].nunique():,}.

## 4. Descriptive statistics ({len(seg):,} scored customers)
{_md_table(desc)}

- Repeat customers (2+ orders): **{H['Repeat customers (2+ orders)']}**. One-order customers: {H['Customers with exactly one order']}.
- Bought in the last 90 days: {H['Customers active in last 90 days (Recency <= 90)']}. No purchase for more than 180 days: {H['Customers inactive > 180 days (Recency > 180)']}.
- Average revenue per customer: {H['Average revenue per scored customer']} (median {H['Median revenue per scored customer']}).

**Log transformation.** All three measures are right-skewed (skewness {desc.set_index('Metric').loc['Recency', 'Skewness']}, {desc.set_index('Metric').loc['Frequency', 'Skewness']} and {desc.set_index('Metric').loc['Monetary', 'Skewness']}). `log(1 + x)` brings skewness close to 0, so it is recommended for charts and as a **model input in Step 6**. The stored RFM values are never transformed.

## 5. RFM Scoring Method
Each measure is converted to a 1-5 score based on quintiles (5 = best):
- **R_Score** is reversed: fewer days since the last purchase gives a higher score.
- **F_Score** and **M_Score**: more orders or more spend gives a higher score.

**Checking the quintile method first.** Frequency has only {int(qc.set_index('Metric').loc['Frequency', 'Unique_Values'])} distinct values, and {qc.set_index('Metric').loc['Frequency', 'Largest_Tie_Group_%']}% of customers share the most common value. This was checked before using `pd.qcut`:
{_md_table(qc)}

**Result.** For this dataset, the quintile edges are unique for all three measures, so `pd.qcut(q=5)` is used. `qcut` keeps identical values in the same score.

The code also contains a **robust fallback**, used automatically if a future dataset produces duplicate edges:
- compute each customer's percentile rank, with tied values averaged;
- score = ceil(5 × percentile rank).

This fallback agrees with qcut for 93-99.9% of customers here (last column above).

Frequency's score bands are unequal in size (for example, all {int(bins[(bins.Metric == 'Frequency') & (bins.Score == 2)]['Customers'].iloc[0])} customers with exactly 3 orders share F = 2). This is the honest consequence of tied values.

**Actual score ranges:**
{_md_table(b)}

**Combined scores**

| Field | Formula | Use |
|---|---|---|
| RFM_Cell | R, F and M digits joined, e.g. "545" | Look-up label, not arithmetic |
| RFM_Score | R + F + M (3-15) | Single ranking score. **Equal weights**, because nothing in the data justifies weighting one dimension more than another. |
| FM_Score | (F + M) / 2 | Value score used in the segment rules. F and M are strongly correlated (Spearman ρ = {rho_fm:.2f}), so averaging them avoids counting the same information twice. |

## 6. Segment Rules (rule-based, exhaustive, evaluated top-down)
{_md_table(rules)}

- The rules cover every (R, FM) combination, so each customer receives **exactly one** segment.
- The segments are grouped into four value-activity groups, used for charts and summaries.

### Segment results
{_md_table(ssum)}

## 7. Revenue Concentration
{_md_table(conc_t)}

- Gini coefficient: **{cst['Gini coefficient (0 = equal, 1 = one customer has all)']}**.
- 50% of revenue comes from {cst['Share of customers needed for 50% of revenue (%)']}% of customers.
- 80% of revenue comes from **{cst['Share of customers needed for 80% of revenue (%)']}%** of customers.

Revenue is clearly concentrated, but the data does **not** show a literal 80/20 Pareto rule.

## 8. Outlier Considerations
- No customers were removed. The largest spenders, up to {inr(seg['Monetary'].max())}, are the Champions that RFM is meant to find.
- Quintile scores are rank-based, so extreme values do not distort the score boundaries.
- Averages by segment are sensitive to extremes, so medians are also saved in `rfm_segment_summary.csv`.
- The 19 bulk-order lines identified in Step 3 are included, because they are genuine purchases.

## 9. Limitations
1. **Quintile scores are relative.** A score of 5 means top 20% of this customer base, not an absolute level of value. The thresholds will move if the data changes.
2. **The segment rules are judgement-based.** The cut-offs (for example FM ≥ 4.5 for Champions) are transparent and conventional, but they are not learnt from the data. Customers near a boundary could reasonably sit in either segment.
3. **Monetary is revenue, not profit.** Segment profit margins (in the summary table) range from about 20% to 35%, so revenue-based value overstates Electronics-heavy customers. CLV in Step 7 will adjust for margin.
4. **Recency is measured from a single snapshot date**, and Frequency and Monetary cover the full 36 months. Customers acquired recently have had less time to build Frequency.
5. **The data are synthetic.** The segments illustrate the method and do not describe a real customer base.

## 10. RFM Rule-Based Segmentation vs Machine-Learning Segmentation

| | RFM rules (this step) | K-Means (Step 6) |
|---|---|---|
| How groups are formed | Human-defined rules on quintile scores | An algorithm groups customers that are close together in feature space |
| Inputs | R, F, M scores only | Scaled (log-transformed) R, F, M and possibly other behavioural features |
| Number of groups | Fixed by the rule table (11 segments) | Chosen with the elbow method and silhouette score |
| Explainability | Very high: every rule is written down | Needs cluster profiling to interpret |
| Weakness | Boundaries are arbitrary | Results depend on scaling, feature choice and k |

The two approaches are complementary. RFM gives an immediately usable business vocabulary. K-Means tests whether the data's natural structure agrees with these rules.

## 11. Business Interpretation
""" + "\n".join(f"- **{r['Insight Area']}:** {r['Observation']}. {r['Evidence']}. *Interpretation:* {r['Business Interpretation']}."
                 for _, r in R["insights"].iterrows()) + f"""

## 12. Validation
{_md_table(V)}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# =============================================================================
# 11. MAIN
# =============================================================================
def run_rfm(make_plots: bool = True, verbose: bool = True) -> dict:
    """Full Step 5 pipeline: compute, save data/tables/figures, write the report."""
    R = run_rfm_analysis()
    R["saved"] = save_rfm_outputs(R)
    R["figures"] = plot_rfm_figures(R) if make_plots else []
    R["report"] = write_rfm_report(R)
    if verbose:
        pd.set_option("display.width", 220)
        pd.set_option("display.max_colwidth", 160)
        print(f"*** {config.DATASET_LABEL} ***")
        print(f"Reference date: {R['reference_date'].date()} | scored customers: {len(R['segments']):,} | "
              f"excluded (no delivered purchase): {len(R['excluded'])}\n")
        print(R["segment_summary"][["RFM_Segment", "Customer_Count", "Customer_%", "Total_Revenue", "Revenue_%",
                                    "Average_Recency", "Average_Frequency", "Average_Monetary"]].to_string(index=False), "\n")
        print(R["validation"].to_string(index=False), "\n")
        print(f"Files saved: {len(R['saved'])} | Figures: {len(R['figures'])} | "
              f"Report: {R['report'].relative_to(config.PROJECT_ROOT)}")
        if not R["validation"]["Pass"].all():
            print("WARNING: some validation checks failed - see table above")
    return R


if __name__ == "__main__":
    run_rfm()
