#!/usr/bin/env python3
"""
segmentation.py
===============
Step 6 of the Customer Revenue Intelligence project: K-Means customer
segmentation (unsupervised machine learning).

    >>> Works on the SYNTHETIC customer RFM table produced in Step 5. <<<

Pipeline
--------
    load_rfm_data()                    validated customer-level RFM file (1 row per customer)
    select_segmentation_features()     evidence for which features enter the model
    validate_model_data()              missing / inf / duplicates / negatives / dtypes / outliers
    analyze_feature_distributions()    skewness before and after log1p
    transform_features() + scale_features()
                                       log1p -> StandardScaler, saved as ONE sklearn Pipeline
    evaluate_k_values()                K = 2..10: inertia, silhouette, CH, DB, size, seed stability
    select_k()                         transparent, written selection rule
    train_kmeans() / assign_clusters() KMeans(random_state=42, n_init="auto")
    profile_clusters()                 business metrics per cluster (original units)
    label_clusters()                   labels derived from measured profiles, AFTER profiling
    cluster_centroids()                centres converted back to days / orders / rupees
    generate_pca_projection()          2-D PCA for visualisation only
    compare_rfm_and_ml_segments()      cross-tab, row/column %, ARI / NMI
    generate_cluster_insights()        evidence-based insight table
    save_segmentation_outputs()        data, tables, models, metadata

Main entry point:  python src/segmentation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                             normalized_mutual_info_score, silhouette_samples, silhouette_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.eda import inr, pct  # noqa: E402

RFM_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_rfm_segments.csv"
ML_SEGMENTS_FILE = config.PROCESSED_DIR / "customer_ml_segments.csv"
MODELS_DIR = config.PROJECT_ROOT / "models"
PREPROCESSOR_FILE = MODELS_DIR / "rfm_scaler.pkl"            # log1p + StandardScaler pipeline
KMEANS_FILE = MODELS_DIR / "kmeans_customer_segmentation.pkl"
PCA_FILE = MODELS_DIR / "pca_rfm.pkl"
MODEL_METADATA_FILE = MODELS_DIR / "segmentation_model_metadata.json"
REPORT_FILE = config.REPORTS_DIR / "kmeans_model_report.md"

CORE_FEATURES = ["Recency", "Frequency", "Monetary"]
CANDIDATE_FEATURES = CORE_FEATURES + ["Average_Order_Value", "Total_Quantity", "Average_Discount",
                                      "Categories_Bought", "Tenure_Days"]
K_RANGE = range(2, 11)
SEED = config.RANDOM_SEED
N_STABILITY_SEEDS = 10
# Selection rule thresholds (documented in the report)
MIN_K_FOR_BUSINESS = 3          # k=2 can only say "high vs low"; need >= 3 to separate value from recency
MIN_CLUSTER_SHARE = 0.05        # every cluster must hold >= 5% of customers to be actionable
MIN_STABILITY_ARI = 0.90        # mean ARI vs 10 other seeds: the partition must be reproducible
SKEW_THRESHOLD = 1.0            # |skew| > 1 = strongly skewed -> test log1p


# =============================================================================
# 1. DATA
# =============================================================================
def load_rfm_data(path: Path = RFM_SEGMENTS_FILE) -> pd.DataFrame:
    """Load the validated Step 5 customer table (RFM values, scores, rule-based segment)."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found - run src/rfm.py (Step 5) first.")
    return pd.read_csv(path, encoding="utf-8-sig", parse_dates=["First_Purchase_Date", "Last_Purchase_Date"])


def validate_model_data(df: pd.DataFrame, features: list[str] = CANDIDATE_FEATURES) -> pd.DataFrame:
    """Data-quality checks on the modelling table. Nothing is removed silently."""
    num = df[features]
    rows = [
        ("Rows (customers)", len(df), True, "Input population"),
        ("Duplicate Customer_ID", int(df["Customer_ID"].duplicated().sum()), df["Customer_ID"].is_unique,
         "Each customer must occur exactly once"),
        ("Missing values in candidate features", int(num.isna().sum().sum()), not num.isna().any().any(), ""),
        ("Infinite values", int(np.isinf(num.to_numpy(dtype=float)).sum()),
         not np.isinf(num.to_numpy(dtype=float)).any(), ""),
        ("Non-numeric candidate features", int(sum(not pd.api.types.is_numeric_dtype(df[c]) for c in features)),
         all(pd.api.types.is_numeric_dtype(df[c]) for c in features), ""),
        ("Recency < 1 day", int((df["Recency"] < 1).sum()), bool((df["Recency"] >= 1).all()),
         "Reference date is max date + 1, so minimum is 1"),
        ("Frequency < 1 order", int((df["Frequency"] < 1).sum()), bool((df["Frequency"] >= 1).all()),
         "Only customers with a delivered purchase were scored"),
        ("Monetary <= 0", int((df["Monetary"] <= 0).sum()), bool((df["Monetary"] > 0).all()), "log1p needs >= 0"),
        ("Average_Discount outside 0-0.40", int((~df["Average_Discount"].between(0, 0.40)).sum()),
         bool(df["Average_Discount"].between(0, 0.40).all()), ""),
    ]
    for c in CORE_FEATURES:
        q1, q3 = df[c].quantile([.25, .75])
        n_out = int((df[c] > q3 + 3 * (q3 - q1)).sum())
        rows.append((f"Extreme values in {c} (> Q3 + 3 IQR)", n_out, True,
                     "Kept: genuine customers; log1p limits their pull on the centroids"))
    return pd.DataFrame(rows, columns=["Check", "Value", "Pass", "Note"])


# =============================================================================
# 2. FEATURES
# =============================================================================
def _prepare_matrix(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = df[cols].astype(float).copy()
    for c in cols:
        if c != "Average_Discount":   # discount is a bounded ratio (0-0.40) and not strongly skewed
            X[c] = np.log1p(X[c])
    return StandardScaler().fit_transform(X)


def _k_metrics(Xs: np.ndarray, k: int, n_init="auto") -> dict:
    km = KMeans(n_clusters=k, random_state=SEED, n_init=n_init).fit(Xs)
    lab = km.labels_
    return {"k": k, "inertia": km.inertia_, "silhouette": silhouette_score(Xs, lab),
            "calinski_harabasz": calinski_harabasz_score(Xs, lab), "davies_bouldin": davies_bouldin_score(Xs, lab),
            "min_cluster_share": np.bincount(lab).min() / len(lab)}


def select_segmentation_features(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Evidence for the final feature list.

    1. Redundancy: Spearman correlation of each candidate with the core RFM features.
    2. Separation: cluster-quality metrics for alternative feature sets at the same K values.
    """
    rho = df[CANDIDATE_FEATURES].corr("spearman")
    reasons = {
        "Recency": ("Include", "Core RFM: how recently the customer bought (activity / churn signal)"),
        "Frequency": ("Include", "Core RFM: how often the customer buys (loyalty)"),
        "Monetary": ("Include", "Core RFM: how much the customer spends (value)"),
        "Average_Order_Value": ("Exclude from model, keep for profiling",
                                "= Monetary / Frequency, so it is a function of two included features; adding it lowered "
                                "separation (see feature-set comparison)"),
        "Total_Quantity": ("Exclude", "Near-duplicate of Frequency (Spearman rho shown) - would double-weight frequency"),
        "Average_Discount": ("Exclude from model, keep for profiling",
                             "Weakly related to RFM, but adding it lowered separation at every K compared (3-5); "
                             "used to describe clusters instead"),
        "Categories_Bought": ("Exclude", "Near-duplicate of Frequency (buying more often = more categories)"),
        "Tenure_Days": ("Exclude", "Measured from Jan 2023 for customers who existed earlier (truncated), so not a true tenure"),
    }
    rows = []
    for c in CANDIDATE_FEATURES:
        others = [o for o in CORE_FEATURES if o != c]
        max_rho = rho.loc[c, others].abs().max()
        rows.append({"Feature": c, "Skewness": round(df[c].skew(), 2),
                     "Max_abs_Spearman_with_core_RFM": round(max_rho, 2),
                     "Most_correlated_core_feature": rho.loc[c, others].abs().idxmax(),
                     "Decision": reasons[c][0], "Reason": reasons[c][1]})
    sets = {"A: R, F, M (selected)": CORE_FEATURES,
            "B: R, F, M + Average_Order_Value": CORE_FEATURES + ["Average_Order_Value"],
            "C: R, F, M + Average_Discount": CORE_FEATURES + ["Average_Discount"],
            "D: R, F, Average_Order_Value": ["Recency", "Frequency", "Average_Order_Value"]}
    comp = []
    for name, cols in sets.items():
        Xs = _prepare_matrix(df, cols)
        for k in (3, 4, 5):
            m = _k_metrics(Xs, k)
            comp.append({"Feature_Set": name, "k": k, "Silhouette": round(m["silhouette"], 3),
                         "Davies_Bouldin": round(m["davies_bouldin"], 3),
                         "Calinski_Harabasz": round(m["calinski_harabasz"], 0)})
    return {"feature_decisions": pd.DataFrame(rows), "feature_set_comparison": pd.DataFrame(comp),
            "candidate_correlation": rho.round(3)}


def analyze_feature_distributions(df: pd.DataFrame, features: list[str] = CORE_FEATURES) -> pd.DataFrame:
    """Skewness before/after log1p and the transformation decision for each feature."""
    rows = []
    for c in features:
        s = df[c].astype(float)
        sk, lsk = s.skew(), np.log1p(s).skew()
        use_log = abs(sk) > SKEW_THRESHOLD and abs(lsk) < abs(sk)
        rows.append({"Feature": c, "Min": s.min(), "Median": s.median(), "Mean": s.mean(), "Max": s.max(),
                     "Max_to_Median": s.max() / s.median(), "Skewness_raw": round(sk, 3),
                     "Skewness_log1p": round(lsk, 3), "Apply_log1p": use_log,
                     "Reason": (f"|skew| {sk:.2f} > {SKEW_THRESHOLD} and log1p reduces it to {lsk:.2f}"
                                if use_log else "Not strongly skewed - keep raw")})
    return pd.DataFrame(rows)


def transform_features(df: pd.DataFrame, features: list[str] = CORE_FEATURES) -> pd.DataFrame:
    """log1p of the model features (a copy - the original columns are never changed)."""
    return np.log1p(df[features].astype(float)).add_prefix("log_")


def build_preprocessor() -> Pipeline:
    """log1p -> StandardScaler as one reproducible sklearn Pipeline (saved to models/rfm_scaler.pkl)."""
    return Pipeline([
        ("log1p", FunctionTransformer(np.log1p, inverse_func=np.expm1, validate=True, feature_names_out="one-to-one")),
        ("scale", StandardScaler()),
    ])


def scale_features(df: pd.DataFrame, features: list[str] = CORE_FEATURES) -> tuple[np.ndarray, Pipeline]:
    """Fit the preprocessing pipeline and return the scaled matrix (mean 0, std 1 per feature).

    Scaling is essential: K-Means uses Euclidean distance, and on raw values
    Monetary (hundreds to lakhs of rupees) would dominate Frequency (1-29 orders).
    """
    pre = build_preprocessor()
    Xs = pre.fit_transform(df[features].astype(float))
    return Xs, pre


# =============================================================================
# 3. CHOOSING K
# =============================================================================
def calculate_silhouette_scores(Xs: np.ndarray, labels_by_k: dict[int, np.ndarray]) -> pd.Series:
    return pd.Series({k: silhouette_score(Xs, lab) for k, lab in labels_by_k.items()}, name="silhouette")


def evaluate_k_values(Xs: np.ndarray, k_range=K_RANGE) -> pd.DataFrame:
    """For each K: inertia, silhouette, Calinski-Harabasz, Davies-Bouldin, smallest cluster share,
    and seed stability (mean Adjusted Rand Index against 10 other random seeds)."""
    rows = []
    for k in k_range:
        m = _k_metrics(Xs, k)
        base = KMeans(n_clusters=k, random_state=SEED, n_init="auto").fit(Xs).labels_
        aris = [adjusted_rand_score(base, KMeans(n_clusters=k, random_state=s, n_init="auto").fit(Xs).labels_)
                for s in range(1, N_STABILITY_SEEDS + 1)]
        m.update({"stability_ari_mean": float(np.mean(aris)), "stability_ari_min": float(np.min(aris))})
        rows.append(m)
    ev = pd.DataFrame(rows)
    # Elbow: normalised distance of each point from the straight line joining first and last K (kneedle idea)
    x = (ev["k"] - ev["k"].min()) / (ev["k"].max() - ev["k"].min())
    y = (ev["inertia"] - ev["inertia"].min()) / (ev["inertia"].max() - ev["inertia"].min())
    ev["elbow_distance"] = (1 - x) - y
    ev["inertia_drop_%"] = -ev["inertia"].pct_change() * 100
    return ev


def select_k(ev: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    """Transparent selection rule (no single metric decides):

    1. Business usefulness: K >= 3 (K = 2 can only separate high from low value).
    2. Actionability: every cluster holds >= 5% of customers.
    3. Reproducibility: mean ARI across 10 seeds >= 0.90.
    4. Among the K values passing 1-3, pick the highest silhouette; report
       Davies-Bouldin, Calinski-Harabasz and the elbow as supporting evidence.
    """
    t = ev.copy()
    t["Rule1_K>=3"] = t["k"] >= MIN_K_FOR_BUSINESS
    t["Rule2_min_size>=5%"] = t["min_cluster_share"] >= MIN_CLUSTER_SHARE
    t["Rule3_stable_ARI>=0.90"] = t["stability_ari_mean"] >= MIN_STABILITY_ARI
    t["Eligible"] = t[["Rule1_K>=3", "Rule2_min_size>=5%", "Rule3_stable_ARI>=0.90"]].all(axis=1)
    if not t["Eligible"].any():
        raise ValueError("No K satisfies the selection rules - revisit features")
    k = int(t.loc[t["Eligible"]].sort_values("silhouette", ascending=False)["k"].iloc[0])
    t["Selected"] = t["k"] == k
    return k, t


# =============================================================================
# 4. MODEL
# =============================================================================
def train_kmeans(Xs: np.ndarray, k: int) -> KMeans:
    """Fit K-Means with a fixed seed (k-means++ initialisation, n_init='auto')."""
    return KMeans(n_clusters=k, random_state=SEED, n_init="auto").fit(Xs)


def assign_clusters(df: pd.DataFrame, model: KMeans, pre: Pipeline, features=CORE_FEATURES) -> pd.DataFrame:
    """Predict Cluster_ID for every customer with the saved preprocessing + model."""
    out = df.copy()
    out["Cluster_ID"] = model.predict(pre.transform(out[features].astype(float)))
    return out


def profile_clusters(seg: pd.DataFrame) -> pd.DataFrame:
    """Business metrics per cluster, in ORIGINAL units (days, orders, rupees)."""
    total_rev, n = seg["Monetary"].sum(), len(seg)
    g = seg.groupby("Cluster_ID").agg(
        Customer_Count=("Customer_ID", "count"), Average_Recency=("Recency", "mean"),
        Median_Recency=("Recency", "median"), Average_Frequency=("Frequency", "mean"),
        Median_Frequency=("Frequency", "median"), Average_Monetary=("Monetary", "mean"),
        Median_Monetary=("Monetary", "median"), Total_Revenue=("Monetary", "sum"), Total_Orders=("Frequency", "sum"),
        Average_Quantity=("Total_Quantity", "mean"), Average_Discount=("Average_Discount", "mean"),
        Total_Profit=("Total_Profit", "sum"), Average_Categories=("Categories_Bought", "mean"),
        Average_Returned_Lines=("Returned_Lines", "mean"), Median_Age=("Customer_Age", "median"),
        Average_RFM_Score=("RFM_Score", "mean"),
        Share_Existing_Before_2023=("Acquisition_Status", lambda s: (s == "Existing before 2023").mean()))
    g["Customer_%"] = 100 * g["Customer_Count"] / n
    g["Revenue_%"] = 100 * g["Total_Revenue"] / total_rev
    g["Average_Order_Value"] = g["Total_Revenue"] / g["Total_Orders"]
    g["Profit_Margin"] = g["Total_Profit"] / g["Total_Revenue"]
    g["Revenue_to_Customer_Ratio"] = g["Revenue_%"] / g["Customer_%"]
    g["Share_Recency_over_180d"] = seg.groupby("Cluster_ID")["Recency"].apply(lambda s: (s > 180).mean())
    cols = ["Customer_Count", "Customer_%", "Average_Recency", "Median_Recency", "Average_Frequency",
            "Median_Frequency", "Average_Monetary", "Median_Monetary", "Total_Revenue", "Revenue_%",
            "Average_Order_Value", "Average_Quantity", "Average_Discount", "Profit_Margin", "Average_Categories",
            "Average_Returned_Lines", "Median_Age", "Average_RFM_Score", "Share_Existing_Before_2023",
            "Share_Recency_over_180d", "Revenue_to_Customer_Ratio", "Total_Revenue", "Total_Profit"]
    cols = list(dict.fromkeys(cols))
    return g[cols].reset_index()


def label_clusters(profile: pd.DataFrame, seg: pd.DataFrame) -> pd.DataFrame:
    """Business labels derived from measured profiles - applied only AFTER profiling.

    Two measurable dimensions, using the population's own quintile cut-offs:
      * Value   - cluster median Monetary vs. all-customer Monetary terciles
                  (High >= 67th pct, Low < 33rd pct, else Mid)
      * Activity- cluster median Recency: Active <= 83 days (R_Score 4-5 range),
                  Lapsing 84-253 days (R_Score 2-3), Inactive >= 254 days (R_Score 1)
    The label combines both, e.g. "High-Value, Active". Frequency is reported
    alongside but not used, because it moves with Monetary (rho 0.84).
    """
    m33, m67 = seg["Monetary"].quantile([1 / 3, 2 / 3])
    r_active = seg.loc[seg["R_Score"] >= 4, "Recency"].max()      # upper edge of R_Score 4
    r_inactive = seg.loc[seg["R_Score"] == 1, "Recency"].min()    # lower edge of R_Score 1
    rows = []
    for r in profile.itertuples():
        value = "High-Value" if r.Median_Monetary >= m67 else "Low-Value" if r.Median_Monetary < m33 else "Mid-Value"
        act = ("Active" if r.Median_Recency <= r_active else "Inactive" if r.Median_Recency >= r_inactive
               else "Lapsing")
        freq = f"median {r.Median_Frequency:.0f} orders"
        rows.append({"Cluster_ID": r.Cluster_ID, "Value_Level": value, "Activity_Level": act,
                     "Business_Label": f"{value}, {act}",
                     "Basis": (f"median Monetary {inr(r.Median_Monetary)} (terciles {inr(m33)} / {inr(m67)}); "
                               f"median Recency {r.Median_Recency:.0f} days (Active <= {r_active:.0f}, "
                               f"Inactive >= {r_inactive:.0f}); {freq}")})
    lab = pd.DataFrame(rows)
    # If two clusters receive the same label, disambiguate by frequency (measured, not invented)
    dup = lab["Business_Label"].duplicated(keep=False)
    if dup.any():
        for lbl, grp in lab[dup].groupby("Business_Label"):
            order = profile.set_index("Cluster_ID").loc[grp["Cluster_ID"], "Median_Frequency"].sort_values()
            for i, cid in enumerate(order.index):
                lab.loc[lab["Cluster_ID"] == cid, "Business_Label"] = f"{lbl} ({'lower' if i == 0 else 'higher'} frequency)"
    return lab


def cluster_centroids(model: KMeans, pre: Pipeline, seg: pd.DataFrame, features=CORE_FEATURES) -> pd.DataFrame:
    """Cluster centres in three views: scaled (model space), log, and ORIGINAL units.

    Original units = expm1(inverse StandardScaler(centre)). Because the model
    works in log space, this is a geometric-mean-type centre - it is shown next
    to the actual cluster medians so the two are not confused.
    """
    scaler = pre.named_steps["scale"]
    centers_scaled = model.cluster_centers_
    centers_log = scaler.inverse_transform(centers_scaled)
    centers_orig = np.expm1(centers_log)
    rows = []
    med = seg.groupby("Cluster_ID")[features].median()
    for cid in range(len(centers_scaled)):
        row = {"Cluster_ID": cid}
        for j, f in enumerate(features):
            row[f"{f}_scaled_centre"] = round(centers_scaled[cid, j], 3)
            row[f"{f}_centre_original_units"] = round(centers_orig[cid, j], 1)
            row[f"{f}_cluster_median"] = med.loc[cid, f]
        rows.append(row)
    c = pd.DataFrame(rows)

    def prof(z, f):
        word = "very high" if z >= 1 else "high" if z >= 0.3 else "low" if z <= -0.3 else "average"
        if z <= -1:
            word = "very low"
        if f == "Recency":   # low recency value = recent
            word = {"very high": "very long ago", "high": "long ago", "average": "average",
                    "low": "recent", "very low": "very recent"}[word]
        return word
    c["Recency_Profile"] = [f"{prof(z, 'Recency')} (~{d:.0f} days)" for z, d in
                            zip(c["Recency_scaled_centre"], c["Recency_centre_original_units"])]
    c["Frequency_Profile"] = [f"{prof(z, 'Frequency')} (~{v:.1f} orders)" for z, v in
                              zip(c["Frequency_scaled_centre"], c["Frequency_centre_original_units"])]
    c["Monetary_Profile"] = [f"{prof(z, 'Monetary')} (~{inr(v)})" for z, v in
                             zip(c["Monetary_scaled_centre"], c["Monetary_centre_original_units"])]
    return c


def generate_pca_projection(Xs: np.ndarray, n_components: int = 2) -> tuple[pd.DataFrame, PCA, pd.DataFrame]:
    """2-D PCA of the scaled feature matrix - for visualisation only (clustering uses all features)."""
    pca = PCA(n_components=n_components, random_state=SEED).fit(Xs)
    comps = pca.transform(Xs)
    ev = pd.DataFrame({"Component": [f"PC{i + 1}" for i in range(n_components)] + ["Total (PC1+PC2)"],
                       "Explained_Variance_%": list(100 * pca.explained_variance_ratio_) +
                       [100 * pca.explained_variance_ratio_.sum()]})
    loadings = pd.DataFrame(pca.components_.T, index=[f"log_{f}" for f in CORE_FEATURES],
                            columns=[f"PC{i + 1}" for i in range(n_components)]).round(3)
    proj = pd.DataFrame(comps, columns=[f"PC{i + 1}" for i in range(n_components)])
    return proj, pca, pd.concat([ev, loadings.reset_index().rename(columns={"index": "Loading_of"})], axis=0,
                                ignore_index=True)


# =============================================================================
# 5. RFM vs ML
# =============================================================================
def compare_rfm_and_ml_segments(seg: pd.DataFrame, labels: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Cross-tabulate rule-based RFM segments against K-Means clusters (same customers)."""
    from src.rfm import SEGMENT_ORDER
    name = labels.set_index("Cluster_ID")["Business_Label"]
    ct = pd.crosstab(pd.Categorical(seg["RFM_Segment"], categories=SEGMENT_ORDER, ordered=True), seg["Cluster_ID"])
    ct.index.name = "RFM_Segment"
    ct.columns = [f"Cluster {c}" for c in ct.columns]
    row_pct = (ct.div(ct.sum(axis=1), axis=0) * 100).round(1)
    col_pct = (ct.div(ct.sum(axis=0), axis=1) * 100).round(1)
    rows = []
    for s_name, r in ct.iterrows():
        n = r.sum()
        top = r.idxmax()
        n_sig = int((r / n >= 0.10).sum())
        rows.append({"RFM_Segment": s_name, "Customers": int(n), "Dominant_Cluster": top,
                     "Dominant_Cluster_Label": name[int(top.split()[1])], "Share_in_Dominant_%": round(100 * r.max() / n, 1),
                     "Clusters_with_>=10%": n_sig,
                     "Pattern": "Mostly one cluster" if r.max() / n >= 0.8 else f"Splits across {n_sig} clusters"})
    seg_view = pd.DataFrame(rows)
    crows = []
    for col in ct.columns:
        c = ct[col]
        top3 = (c / c.sum()).sort_values(ascending=False).head(3)
        crows.append({"Cluster": col, "Business_Label": name[int(col.split()[1])], "Customers": int(c.sum()),
                      "RFM_Segments_with_>=10%": int((c / c.sum() >= 0.10).sum()),
                      "Composition (top 3)": "; ".join(f"{i} {v * 100:.0f}%" for i, v in top3.items())})
    clus_view = pd.DataFrame(crows)
    agree = pd.DataFrame([
        ("Adjusted Rand Index (RFM segment vs cluster)", adjusted_rand_score(seg["RFM_Segment"], seg["Cluster_ID"])),
        ("Normalized Mutual Information", normalized_mutual_info_score(seg["RFM_Segment"], seg["Cluster_ID"])),
        ("ARI (RFM value-activity group vs cluster)",
         adjusted_rand_score(seg["Value_Activity_Group"], seg["Cluster_ID"])),
        ("Customers compared", len(seg)),
    ], columns=["Measure", "Value"])
    grp = pd.crosstab(seg["Value_Activity_Group"], seg["Cluster_ID"])
    grp.columns = [f"Cluster {c}" for c in grp.columns]
    return {"crosstab": ct, "row_pct": row_pct, "col_pct": col_pct, "by_segment": seg_view,
            "by_cluster": clus_view, "agreement": agree, "group_crosstab": grp}


# =============================================================================
# 6. QUESTIONS, INSIGHTS, VALIDATION
# =============================================================================
def answer_ml_questions(R: dict) -> pd.DataFrame:
    P = R["profile"].set_index("Cluster_ID")
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    ev = R["k_eval"].set_index("k")
    k = R["k"]
    cmp_ = R["comparison"]
    agree = cmp_["agreement"].set_index("Measure")["Value"]

    def nm(c):
        return f"Cluster {c} ({L[c]})"
    hi_m = P["Average_Monetary"].idxmax()
    hi_f = P["Average_Frequency"].idxmax()
    rec = P["Median_Recency"].idxmin()
    hi_rev = P["Total_Revenue"].idxmax()
    lapsed_val = P[(P["Median_Monetary"] >= R["segments"]["Monetary"].median()) &
                   (P["Median_Recency"] > R["segments"]["Recency"].median())]
    Lv = R["labels"].set_index("Cluster_ID")
    low_value = P[P["Median_Monetary"] < R["segments"]["Monetary"].quantile(1 / 3)]
    # low engagement = low value AND not recently active (both measured)
    low = low_value[Lv.loc[low_value.index, "Activity_Level"] != "Active"]
    low_active = low_value[Lv.loc[low_value.index, "Activity_Level"] == "Active"]
    ct = cmp_["crosstab"]
    from src.rfm import CANT_LOSE as CL
    splits = cmp_["by_segment"][cmp_["by_segment"]["Pattern"] != "Mostly one cluster"]
    rows = [
        ("Q1. How many ML customer clusters were selected?",
         f"K = {k}. It passed all three rules (K >= 3, smallest cluster {pct(ev.loc[k, 'min_cluster_share'])} >= 5%, "
         f"seed stability ARI {ev.loc[k, 'stability_ari_mean']:.2f} >= 0.90) and has the highest silhouette among eligible K "
         f"({ev.loc[k, 'silhouette']:.3f}); it also has the lowest Davies-Bouldin of all K tested ({ev.loc[k, 'davies_bouldin']:.3f})."),
        ("Q2. What characteristics define each cluster?",
         " | ".join(f"{nm(c)}: {int(r.Customer_Count)} customers, median recency {r.Median_Recency:.0f} d, "
                    f"median {r.Median_Frequency:.0f} orders, median spend {inr(r.Median_Monetary)}"
                    for c, r in P.iterrows())),
        ("Q3. Which clusters have the highest monetary value?",
         f"{nm(hi_m)}: average {inr(P.loc[hi_m, 'Average_Monetary'])}, median {inr(P.loc[hi_m, 'Median_Monetary'])} "
         f"per customer."),
        ("Q4. Which clusters have the highest purchase frequency?",
         f"{nm(hi_f)}: average {P.loc[hi_f, 'Average_Frequency']:.1f} orders (median {P.loc[hi_f, 'Median_Frequency']:.0f})."),
        ("Q5. Which clusters have the most recent purchases?",
         f"{nm(rec)}: median recency {P.loc[rec, 'Median_Recency']:.0f} days "
         f"({pct(1 - P.loc[rec, 'Share_Recency_over_180d'])} bought within 180 days)."),
        ("Q6. Which clusters contribute the most revenue?",
         f"{nm(hi_rev)}: {inr(P.loc[hi_rev, 'Total_Revenue'])} ({P.loc[hi_rev, 'Revenue_%']:.1f}%) from "
         f"{P.loc[hi_rev, 'Customer_%']:.1f}% of customers."),
        ("Q7. Are there clusters containing high-value but less-recent customers?",
         ("Yes: " + "; ".join(f"{nm(c)} - median spend {inr(r.Median_Monetary)} (above the all-customer median "
                              f"{inr(R['segments']['Monetary'].median())}) with median recency {r.Median_Recency:.0f} days "
                              f"(above the median {R['segments']['Recency'].median():.0f}); it holds {r['Revenue_%']:.1f}% of "
                              f"revenue and absorbs {int(ct.loc['At Risk', f'Cluster {c}'])} of "
                              f"{int(ct.loc['At Risk'].sum())} RFM 'At Risk' and {int(ct.loc[CL, f'Cluster {c}'])} of "
                              f"{int(ct.loc[CL].sum())} 'Can't Lose Them' customers"
                              for c, r in lapsed_val.iterrows()))
         if len(lapsed_val) else "No cluster combines above-median spend with above-median recency."),
        ("Q8. Are there clusters dominated by low-engagement customers?",
         (("Yes: " + "; ".join(f"{nm(c)} - median spend {inr(r.Median_Monetary)}, median {r.Median_Frequency:.0f} orders, "
                               f"{pct(r.Share_Recency_over_180d)} inactive > 180 days, {r['Revenue_%']:.1f}% of revenue"
                               for c, r in low.iterrows())) if len(low) else "No cluster combines low value with inactivity.")
         + ("" if not len(low_active) else ". By contrast, " + "; ".join(
             f"{nm(c)} is also low value (median {inr(r.Median_Monetary)}) but recently active (median recency "
             f"{r.Median_Recency:.0f} days) - early-stage rather than disengaged" for c, r in low_active.iterrows()) + ".")),
        ("Q9. How do ML clusters differ from the RFM rule-based segments?",
         f"Agreement is moderate (ARI {agree['Adjusted Rand Index (RFM segment vs cluster)']:.2f}, NMI "
         f"{agree['Normalized Mutual Information']:.2f}). K-Means finds {k} broad groups where the rules draw 11 segments; "
         f"{len(splits)} RFM segments split across two or more clusters (e.g. "
         + ", ".join(f"{r.RFM_Segment} -> {r['Clusters_with_>=10%']} clusters" for _, r in splits.head(3).iterrows()) + ")."),
        ("Q10. What customer groups should later be considered when building CLV and predictive models?",
         f"Use Cluster_ID as a candidate feature and a reporting dimension: the high-value clusters "
         f"({', '.join(nm(c) for c in P.index[P['Median_Monetary'] >= R['segments']['Monetary'].quantile(2 / 3)])}) drive "
         f"most revenue, and the lapsing / inactive clusters are where CLV is most uncertain. Note: clusters are built "
         f"on full-period RFM, so for Step 8 prediction they must be re-derived on the observation window to avoid leakage."),
    ]
    return pd.DataFrame(rows, columns=["Question", "Answer (from data)"])


def generate_cluster_insights(R: dict) -> pd.DataFrame:
    """Cluster | Customer Profile | Evidence | Business Interpretation (tied to measured values)."""
    P = R["profile"].set_index("Cluster_ID")
    L = R["labels"].set_index("Cluster_ID")
    by_c = R["comparison"]["by_cluster"].set_index("Cluster")
    rows = []
    overall_disc = R["segments"]["Average_Discount"].mean()
    for c, r in P.iterrows():
        lab = L.loc[c, "Business_Label"]
        profile = (f"{lab}: median {r.Median_Frequency:.0f} orders, median spend {inr(r.Median_Monetary)}, "
                   f"median recency {r.Median_Recency:.0f} days")
        evidence = (f"{int(r.Customer_Count)} customers ({r['Customer_%']:.1f}%) -> {inr(r.Total_Revenue)} "
                    f"({r['Revenue_%']:.1f}% of revenue, {r.Revenue_to_Customer_Ratio:.2f}x their customer share); "
                    f"AOV {inr(r.Average_Order_Value)}; avg discount {100 * r.Average_Discount:.1f}% "
                    f"(all customers {100 * overall_disc:.1f}%); {pct(r.Share_Recency_over_180d)} inactive > 180 days; "
                    f"RFM mix: {by_c.loc[f'Cluster {c}', 'Composition (top 3)']}")
        v, a = L.loc[c, "Value_Level"], L.loc[c, "Activity_Level"]
        if v == "High-Value" and a == "Active":
            interp = "Core revenue base - retention and service quality matter most; small in count, large in value"
        elif v in ("High-Value", "Mid-Value") and a != "Active":
            interp = "Proven spenders whose activity has dropped - measurable win-back opportunity; size it with CLV (Step 7)"
        elif a == "Active":
            interp = "Recently active but not yet high value - development / cross-sell potential"
        else:
            interp = "Low spend and long inactive - low priority for paid retention; low-cost reactivation only"
        rows.append({"Cluster": f"Cluster {c}", "Customer Profile": profile, "Evidence": evidence,
                     "Business Interpretation": interp})
    return pd.DataFrame(rows)


def validate_segmentation(R: dict) -> pd.DataFrame:
    seg, P = R["segments"], R["profile"]
    rfm_in = R["input"]
    meta_features = list(R["preprocessor"].feature_names_in_)
    re_pred = R["model"].predict(R["preprocessor"].transform(seg[CORE_FEATURES].astype(float)))
    refit = KMeans(n_clusters=R["k"], random_state=SEED, n_init="auto").fit(R["X_scaled"]).labels_
    checks = [
        ("One row per customer / no duplicate IDs", int(seg["Customer_ID"].duplicated().sum()), seg["Customer_ID"].is_unique),
        ("Customers in = customers out (none removed)", f"{len(rfm_in)} -> {len(seg)}", len(rfm_in) == len(seg)),
        ("No missing / infinite model inputs", int(np.isnan(R["X_scaled"]).sum() + np.isinf(R["X_scaled"]).sum()),
         bool(np.isfinite(R["X_scaled"]).all())),
        ("No leakage: identifiers / scores / labels not used as features", ", ".join(meta_features),
         meta_features == CORE_FEATURES),
        ("Feature order preserved (preprocessor = model = metadata)", " -> ".join(meta_features),
         meta_features == CORE_FEATURES and R["model"].n_features_in_ == len(CORE_FEATURES)),
        ("Scaled features have mean 0 and std 1", f"means {np.round(R['X_scaled'].mean(0), 6).tolist()}",
         bool(np.allclose(R["X_scaled"].mean(0), 0, atol=1e-9) and np.allclose(R["X_scaled"].std(0), 1, atol=1e-9))),
        ("Fixed random seed; refit reproduces the same clusters", f"random_state={SEED}",
         bool((refit == seg["Cluster_ID"].to_numpy()).all())),
        ("Multiple K values evaluated", f"K = {min(K_RANGE)}..{max(K_RANGE)}", len(R["k_eval"]) >= 5),
        ("Every customer has exactly one cluster", int(seg["Cluster_ID"].isna().sum()), bool(seg["Cluster_ID"].notna().all())),
        ("Saved model + preprocessor reproduce the assignments", "predict() on saved objects",
         bool((re_pred == seg["Cluster_ID"].to_numpy()).all())),
        ("Cluster counts reconcile", int(P["Customer_Count"].sum()), int(P["Customer_Count"].sum()) == len(seg)),
        ("Sum of cluster revenue = total customer revenue", f"{inr(P['Total_Revenue'].sum())} vs {inr(seg['Monetary'].sum())}",
         abs(P["Total_Revenue"].sum() - seg["Monetary"].sum()) < 1.0),
        ("Cluster profile averages reconcile with customer data", "recomputed",
         bool(np.allclose(P.set_index("Cluster_ID")["Average_Monetary"],
                          seg.groupby("Cluster_ID")["Monetary"].mean()))),
        ("RFM vs ML comparison uses the same customers", int(R["comparison"]["crosstab"].to_numpy().sum()),
         int(R["comparison"]["crosstab"].to_numpy().sum()) == len(seg)),
        ("Revenue ties back to Step 5 / Step 4 total", inr(seg["Monetary"].sum()),
         abs(seg["Monetary"].sum() - rfm_in["Monetary"].sum()) < 1.0),
    ]
    return pd.DataFrame(checks, columns=["Check", "Value", "Pass"])


# =============================================================================
# 7. RUN + SAVE
# =============================================================================
def run_segmentation_analysis() -> dict:
    """Compute everything in memory (no files written)."""
    R: dict = {}
    df = load_rfm_data()
    R["input"] = df
    R["data_quality"] = validate_model_data(df)
    R["feature_selection"] = select_segmentation_features(df)
    R["distribution"] = analyze_feature_distributions(df)
    R["transformed"] = transform_features(df)
    R["X_scaled"], R["preprocessor"] = scale_features(df)
    R["k_eval"] = evaluate_k_values(R["X_scaled"])
    R["k"], R["k_selection"] = select_k(R["k_eval"])
    R["model"] = train_kmeans(R["X_scaled"], R["k"])
    R["model_n_init10_inertia"] = KMeans(n_clusters=R["k"], random_state=SEED, n_init=10).fit(R["X_scaled"]).inertia_
    seg = assign_clusters(df, R["model"], R["preprocessor"])
    seg["Silhouette"] = silhouette_samples(R["X_scaled"], seg["Cluster_ID"])
    R["profile"] = profile_clusters(seg)
    R["labels"] = label_clusters(R["profile"], seg)
    seg = seg.merge(R["labels"][["Cluster_ID", "Business_Label"]], on="Cluster_ID", how="left") \
        .rename(columns={"Business_Label": "Cluster_Label"})
    R["segments"] = seg
    R["profile"] = R["profile"].merge(R["labels"][["Cluster_ID", "Business_Label"]], on="Cluster_ID")
    R["centroids"] = cluster_centroids(R["model"], R["preprocessor"], seg)
    R["pca_proj"], R["pca"], R["pca_summary"] = generate_pca_projection(R["X_scaled"])
    seg[["PC1", "PC2"]] = R["pca_proj"].to_numpy()
    R["comparison"] = compare_rfm_and_ml_segments(seg, R["labels"])
    sil = seg.groupby("Cluster_ID")["Silhouette"].agg(["mean", "min", lambda s: (s < 0).mean()])
    sil.columns = ["Mean_Silhouette", "Min_Silhouette", "Share_Negative_Silhouette"]
    R["silhouette_by_cluster"] = sil.reset_index()
    R["final_metrics"] = pd.DataFrame([
        ("Selected K", R["k"]),
        ("Inertia (within-cluster sum of squares)", round(R["model"].inertia_, 2)),
        ("Inertia with n_init=10 (check)", round(R["model_n_init10_inertia"], 2)),
        ("Silhouette score", round(silhouette_score(R["X_scaled"], seg["Cluster_ID"]), 4)),
        ("Calinski-Harabasz score", round(calinski_harabasz_score(R["X_scaled"], seg["Cluster_ID"]), 1)),
        ("Davies-Bouldin score", round(davies_bouldin_score(R["X_scaled"], seg["Cluster_ID"]), 4)),
        ("Seed stability (mean ARI, 10 seeds)", round(R["k_eval"].set_index("k").loc[R["k"], "stability_ari_mean"], 3)),
        ("Smallest cluster share", round(seg["Cluster_ID"].value_counts(normalize=True).min(), 4)),
        ("Customers with negative silhouette", int((seg["Silhouette"] < 0).sum())),
        ("PC1 + PC2 explained variance (%)", round(R["pca"].explained_variance_ratio_.sum() * 100, 2)),
        ("scikit-learn version", sklearn.__version__),
    ], columns=["Metric", "Value"])
    R["questions"] = answer_ml_questions(R)
    R["insights"] = generate_cluster_insights(R)
    R["validation"] = validate_segmentation(R)
    return R


def save_segmentation_outputs(R: dict) -> list[Path]:
    """Save the ML segment dataset, model artefacts, metadata and tables."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    seg = R["segments"].copy()
    tf = R["transformed"]
    for c in tf.columns:
        seg[c] = tf[c].to_numpy()
    scaled = pd.DataFrame(R["X_scaled"], columns=[f"scaled_log_{f}" for f in CORE_FEATURES])
    for c in scaled.columns:
        seg[c] = scaled[c].to_numpy()
    for c in ["First_Purchase_Date", "Last_Purchase_Date"]:
        seg[c] = seg[c].dt.strftime("%Y-%m-%d")
    lead = ["Customer_ID", "Recency", "Frequency", "Monetary", "R_Score", "F_Score", "M_Score", "RFM_Cell",
            "RFM_Score", "FM_Score", "RFM_Segment", "Value_Activity_Group", "Cluster_ID", "Cluster_Label",
            "Silhouette", "PC1", "PC2"] + list(tf.columns) + list(scaled.columns)
    seg = seg[lead + [c for c in seg.columns if c not in lead]]
    seg["Silhouette"] = seg["Silhouette"].round(4)
    seg[["PC1", "PC2"] + list(tf.columns) + list(scaled.columns)] = \
        seg[["PC1", "PC2"] + list(tf.columns) + list(scaled.columns)].round(5)
    seg.to_csv(ML_SEGMENTS_FILE, index=False, encoding="utf-8-sig")
    paths.append(ML_SEGMENTS_FILE)

    joblib.dump(R["preprocessor"], PREPROCESSOR_FILE)
    joblib.dump(R["model"], KMEANS_FILE)
    joblib.dump(R["pca"], PCA_FILE)
    meta = {
        "dataset": config.DATASET_LABEL,
        "input_file": str(RFM_SEGMENTS_FILE.relative_to(config.PROJECT_ROOT)),
        "feature_order": CORE_FEATURES,
        "preprocessing": "log1p -> StandardScaler (sklearn Pipeline saved in rfm_scaler.pkl)",
        "model": f"KMeans(n_clusters={R['k']}, random_state={SEED}, n_init='auto')",
        "selected_k": R["k"],
        "selection_rules": {"min_k": MIN_K_FOR_BUSINESS, "min_cluster_share": MIN_CLUSTER_SHARE,
                            "min_stability_ari": MIN_STABILITY_ARI, "then": "highest silhouette"},
        "cluster_labels": R["labels"].set_index("Cluster_ID")["Business_Label"].to_dict(),
        "pca": "2 components on the scaled matrix - visualisation only",
        "sklearn_version": sklearn.__version__,
        "reload_example": ("import joblib, pandas as pd; pre = joblib.load('models/rfm_scaler.pkl'); "
                           "km = joblib.load('models/kmeans_customer_segmentation.pkl'); "
                           "X = df[['Recency','Frequency','Monetary']]; clusters = km.predict(pre.transform(X))"),
    }
    MODEL_METADATA_FILE.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    paths += [PREPROCESSOR_FILE, KMEANS_FILE, PCA_FILE, MODEL_METADATA_FILE]

    summ_cols = ["Cluster_ID", "Business_Label", "Customer_Count", "Customer_%", "Average_Recency", "Median_Recency",
                 "Average_Frequency", "Median_Frequency", "Average_Monetary", "Median_Monetary", "Total_Revenue",
                 "Revenue_%", "Average_Order_Value", "Average_Quantity", "Average_Discount", "Profit_Margin",
                 "Average_Categories", "Average_Returned_Lines", "Median_Age", "Average_RFM_Score",
                 "Share_Existing_Before_2023", "Share_Recency_over_180d", "Revenue_to_Customer_Ratio", "Total_Profit"]
    cmp_ = R["comparison"]
    tables = {
        "ml_cluster_summary.csv": R["profile"][summ_cols].round(4),
        "ml_cluster_insights.csv": R["insights"],
        "ml_cluster_label_mapping.csv": R["labels"],
        "ml_cluster_centroids.csv": R["centroids"],
        "ml_k_evaluation.csv": R["k_selection"].round(4),
        "ml_final_model_metrics.csv": R["final_metrics"],
        "ml_silhouette_by_cluster.csv": R["silhouette_by_cluster"].round(4),
        "ml_feature_selection.csv": R["feature_selection"]["feature_decisions"],
        "ml_feature_set_comparison.csv": R["feature_selection"]["feature_set_comparison"],
        "ml_feature_distribution_check.csv": R["distribution"].round(3),
        "ml_data_quality_checks.csv": R["data_quality"],
        "ml_pca_summary.csv": R["pca_summary"].round(3),
        "rfm_vs_ml_cluster.csv": cmp_["crosstab"].reset_index(),
        "rfm_vs_ml_cluster_row_pct.csv": cmp_["row_pct"].reset_index(),
        "rfm_vs_ml_cluster_col_pct.csv": cmp_["col_pct"].reset_index(),
        "rfm_vs_ml_by_segment.csv": cmp_["by_segment"],
        "rfm_vs_ml_by_cluster.csv": cmp_["by_cluster"],
        "rfm_vs_ml_agreement.csv": cmp_["agreement"],
        "ml_business_questions.csv": R["questions"],
        "ml_validation_checks.csv": R["validation"],
    }
    for name, t in tables.items():
        p = config.TABLES_DIR / name
        t.to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


# =============================================================================
# 8. FIGURES
# =============================================================================
CLUSTER_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def plot_elbow_curve(R: dict, out_dir: Path, saved: list) -> None:
    """K vs inertia, with the selected K and the elbow-distance peak marked."""
    from src.eda import _style, _save, _note, PAL
    plt = _style()
    ev = R["k_selection"]
    k = R["k"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(ev["k"], ev["inertia"], color=PAL["blue"], marker="o", linewidth=2, markersize=6)
    sel = ev[ev["k"] == k].iloc[0]
    ax.plot([k], [sel["inertia"]], "o", markersize=13, markerfacecolor="none", markeredgecolor=PAL["orange"],
            markeredgewidth=2)
    ax.annotate(f"Selected K = {k}\ninertia {sel['inertia']:,.0f}\n({sel['inertia_drop_%']:.1f}% drop from K={k - 1})",
                (k, sel["inertia"]), textcoords="offset points", xytext=(18, 18), fontsize=9,
                arrowprops=dict(arrowstyle="-", color=PAL["muted"], linewidth=0.8))
    knee = int(ev.loc[ev["elbow_distance"].idxmax(), "k"])
    for r in ev.itertuples():
        ax.text(r.k, r.inertia + ev["inertia"].max() * 0.02, f"{r.inertia:,.0f}", ha="center", fontsize=8,
                color=PAL["muted"])
    ax.set_xticks(ev["k"])
    ax.set_xlabel("Number of clusters (K)")
    ax.set_ylabel("Inertia (within-cluster sum of squares)")
    ax.set_title("Elbow method: inertia by K (log1p + standard-scaled R, F, M)")
    _note(fig, f"The elbow (largest distance from the straight line joining K=2 and K=10) is at K = {knee}. "
               "Inertia always falls as K rises, so the elbow is supporting evidence, not the decision rule.")
    fig.tight_layout()
    _save(fig, "kmeans_elbow_curve.png", out_dir, saved)


def plot_k_metrics(R: dict, out_dir: Path, saved: list) -> None:
    """Silhouette, Davies-Bouldin, Calinski-Harabasz and seed stability by K."""
    from src.eda import _style, _save, _note, PAL
    plt = _style()
    ev = R["k_selection"]
    k = R["k"]
    specs = [("silhouette", "Silhouette (higher = better separated)", None),
             ("davies_bouldin", "Davies-Bouldin (lower = better)", None),
             ("calinski_harabasz", "Calinski-Harabasz (higher = better)", None),
             ("stability_ari_mean", "Seed stability: mean ARI vs 10 seeds", MIN_STABILITY_ARI)]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.3))
    for ax, (col, title, thr) in zip(axes, specs):
        colors = [PAL["orange"] if kk == k else (PAL["blue"] if el else PAL["neutral"])
                  for kk, el in zip(ev["k"], ev["Eligible"])]
        ax.bar(ev["k"], ev[col], color=colors, width=0.7)
        for kk, v in zip(ev["k"], ev[col]):
            ax.text(kk, v, f"{v:.2f}" if col != "calinski_harabasz" else f"{v:,.0f}", ha="center", va="bottom",
                    fontsize=7.5)
        if thr is not None:
            ax.axhline(thr, color=PAL["text"], linestyle=":", linewidth=1)
            ax.text(2, thr + 0.02, f"threshold {thr}", va="bottom", fontsize=8)
        ax.set_xticks(ev["k"])
        ax.set_xlabel("K")
        ax.set_title(title, fontsize=10.5)
        ax.grid(axis="x", visible=False)
        lo = ev[col].min()
        ax.set_ylim(lo * 0.85 if col != "stability_ari_mean" else 0, ev[col].max() * 1.1)
    n_elig = int(ev["Eligible"].sum())
    fig.suptitle(f"Cluster-quality metrics by K (orange = selected K = {k}; grey = other K; "
                 f"{n_elig} of {len(ev)} K values pass all selection rules)", x=0.01, ha="left",
                 fontweight="bold", fontsize=12.5)
    _note(fig, "Rules: K >= 3, every cluster >= 5% of customers, mean ARI >= 0.90 across 10 random seeds; "
               "then the highest silhouette. K = 2 has a higher silhouette but only splits high vs low value.")
    fig.tight_layout()
    _save(fig, "kmeans_silhouette_scores.png", out_dir, saved)


def plot_silhouette_diagram(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _note, PAL
    plt = _style()
    seg = R["segments"]
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    avg = seg["Silhouette"].mean()
    fig, ax = plt.subplots(figsize=(9, 6))
    y0 = 0
    for c in sorted(seg["Cluster_ID"].unique()):
        vals = np.sort(seg.loc[seg["Cluster_ID"] == c, "Silhouette"].to_numpy())
        ax.fill_betweenx(np.arange(y0, y0 + len(vals)), 0, vals, color=CLUSTER_COLORS[c], alpha=0.85, linewidth=0)
        ax.text(-0.02, y0 + len(vals) / 2, f"Cluster {c}\n{L[c]}\n(n={len(vals)})", ha="right", va="center",
                fontsize=8.5)
        y0 += len(vals) + 25
    ax.axvline(avg, color=PAL["text"], linestyle="--", linewidth=1)
    ax.text(avg, y0, f" average {avg:.3f}", fontsize=9)
    ax.set_yticks([])
    ax.set_xlabel("Silhouette coefficient per customer")
    ax.set_title(f"Silhouette diagram, K = {R['k']}")
    _note(fig, f"Values near 1 = customer sits well inside its cluster; near 0 = on a boundary; below 0 = closer to "
               f"another cluster ({int((seg['Silhouette'] < 0).sum())} of {len(seg):,} customers).")
    ax.set_xlim(-0.45, 0.75)
    fig.tight_layout()
    _save(fig, "kmeans_silhouette_diagram.png", out_dir, saved)


def plot_cluster_bars(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _hbar, _rupee, _lakh, PAL
    plt = _style()
    P = R["profile"].sort_values("Cluster_ID")
    labels = [f"Cluster {c}: {lbl}" for c, lbl in zip(P["Cluster_ID"], P["Business_Label"])]
    colors = [CLUSTER_COLORS[c] for c in P["Cluster_ID"]]
    seg = R["segments"]
    specs = [
        ("Customer_Count", "cluster_distribution.png", "Customers per cluster", None,
         [f"{int(v):,}  ({p:.1f}%)" for v, p in zip(P["Customer_Count"], P["Customer_%"])], "Customers"),
        ("Total_Revenue", "cluster_revenue.png", "Revenue per cluster (Delivered, 2023-2025)", "lakh",
         [f"{inr(v)}  ({p:.1f}% of revenue, {c:.1f}% of customers)" for v, p, c in
          zip(P["Total_Revenue"], P["Revenue_%"], P["Customer_%"])], "Revenue (₹ lakh)"),
        ("Average_Monetary", "cluster_monetary.png", "Average monetary value per customer", "rupee",
         [f"{inr(v)}  (median {inr(m)})" for v, m in zip(P["Average_Monetary"], P["Median_Monetary"])],
         "Average Monetary (₹)"),
        ("Average_Frequency", "cluster_frequency.png", "Average purchase frequency", None,
         [f"{v:.1f} orders  (median {m:.0f})" for v, m in zip(P["Average_Frequency"], P["Median_Frequency"])],
         "Average delivered orders"),
        ("Average_Recency", "cluster_recency.png", "Average recency (days since last purchase; lower = more recent)",
         None, [f"{v:.0f} days  (median {m:.0f})" for v, m in zip(P["Average_Recency"], P["Median_Recency"])],
         "Average days since last purchase"),
    ]
    overall = {"Average_Monetary": seg["Monetary"].mean(), "Average_Frequency": seg["Frequency"].mean(),
               "Average_Recency": seg["Recency"].mean()}
    for col, fname, title, fmt, vlabels, xlabel in specs:
        fig, ax = plt.subplots(figsize=(10.5, 3.6))
        _hbar(ax, labels, P[col].to_numpy(), color=colors, value_labels=vlabels)
        if fmt == "lakh":
            _lakh(ax, "x")
        elif fmt == "rupee":
            _rupee(ax, "x")
        if col in overall:
            ax.axvline(overall[col], color=PAL["text"], linestyle=":", linewidth=1)
            ax.text(overall[col], -0.62, f" all customers: {overall[col]:,.0f}", fontsize=8, color=PAL["muted"])
        ax.set_xlabel(xlabel)
        ax.set_title(title)
        fig.tight_layout()
        _save(fig, fname, out_dir, saved)


def plot_cluster_scatter(R: dict, out_dir: Path, saved: list) -> None:
    """Recency vs Monetary and Frequency vs Monetary, one highlighted facet per cluster
    (avoids overplotting four colours on top of each other)."""
    from src.eda import _style, _save, _rupee, _note
    from matplotlib.ticker import FixedLocator, ScalarFormatter
    plt = _style()
    seg = R["segments"]
    k = R["k"]
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    rng = np.random.default_rng(SEED)
    fj = seg["Frequency"] * np.exp(rng.uniform(-0.08, 0.08, len(seg)))
    fig, axes = plt.subplots(2, k, figsize=(4.6 * k, 8.4), sharey=True)
    for j in range(k):
        m = seg["Cluster_ID"] == j
        for i, (x, xl) in enumerate([(seg["Recency"], "Recency (days)"), (fj, "Frequency (orders, log)")]):
            ax = axes[i, j]
            ax.scatter(x[~m], seg.loc[~m, "Monetary"], s=5, color="#dcdbd5", edgecolors="none")
            ax.scatter(x[m], seg.loc[m, "Monetary"], s=9, color=CLUSTER_COLORS[j], alpha=0.75, edgecolors="none")
            ax.set_yscale("log")
            _rupee(ax)
            if i == 1:
                ax.set_xscale("log")
                ax.xaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20]))
                ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.set_xlabel(xl)
            if i == 0:
                ax.set_title(f"Cluster {j}: {L[j]}\n({int(m.sum())} customers)", fontsize=10.5)
        axes[0, j].set_ylabel("Monetary (₹, log)") if j == 0 else None
        axes[1, j].set_ylabel("Monetary (₹, log)") if j == 0 else None
    fig.suptitle("K-Means clusters in RFM space (top: Recency vs Monetary; bottom: Frequency vs Monetary; "
                 "grey = other clusters)", x=0.01, ha="left", fontweight="bold", fontsize=13)
    _note(fig, "Axes show ORIGINAL values (log-scaled axes for readability). Frequency has slight jitter so "
               "customers with the same order count are visible.")
    fig.tight_layout()
    _save(fig, "cluster_rfm_scatter.png", out_dir, saved)


def plot_pca(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _note, PAL
    plt = _style()
    seg = R["segments"]
    k = R["k"]
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    ev = R["pca"].explained_variance_ratio_ * 100
    cent = R["pca"].transform(R["model"].cluster_centers_)
    load = R["pca"].components_.T
    fig, axes = plt.subplots(1, k + 1, figsize=(4.4 * (k + 1), 4.8), sharex=True, sharey=True)
    ax0 = axes[0]
    ax0.scatter(seg["PC1"], seg["PC2"], s=4, color="#c9c8c2", edgecolors="none")
    nudge = {"Recency": (0.0, 0.18), "Frequency": (0.15, -0.28), "Monetary": (0.15, 0.22)}
    for j, f in enumerate(CORE_FEATURES):
        ax0.annotate("", xy=(load[j, 0] * 1.8, load[j, 1] * 1.8), xytext=(0, 0),
                     arrowprops=dict(arrowstyle="->", color=PAL["text"], linewidth=1.3))
        dx, dy = nudge[f]
        ax0.text(load[j, 0] * 1.8 + dx, load[j, 1] * 1.8 + dy, f"log {f}", fontsize=8.5,
                 ha="left" if f != "Recency" else "center", fontweight="bold",
                 bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1))
    for c in range(k):
        ax0.text(cent[c, 0], cent[c, 1], str(c), fontsize=12, fontweight="bold", color="white", ha="center",
                 va="center", bbox=dict(boxstyle="circle,pad=0.3", facecolor=CLUSTER_COLORS[c], edgecolor="white"))
    ax0.set_title("All customers: feature directions\nand cluster centres (numbered)", fontsize=10.5)
    for c in range(k):
        ax = axes[c + 1]
        m = seg["Cluster_ID"] == c
        ax.scatter(seg.loc[~m, "PC1"], seg.loc[~m, "PC2"], s=4, color="#dcdbd5", edgecolors="none")
        ax.scatter(seg.loc[m, "PC1"], seg.loc[m, "PC2"], s=8, color=CLUSTER_COLORS[c], alpha=0.75, edgecolors="none")
        ax.plot(cent[c, 0], cent[c, 1], marker="X", markersize=11, color=PAL["text"], markeredgecolor="white")
        ax.set_title(f"Cluster {c}: {L[c]}\n({int(m.sum())} customers)", fontsize=10.5)
    for ax in axes:
        ax.set_xlabel(f"PC1 ({ev[0]:.1f}% of variance)")
    axes[0].set_ylabel(f"PC2 ({ev[1]:.1f}% of variance)")
    fig.suptitle(f"PCA projection of the scaled features (PC1 + PC2 = {ev.sum():.1f}% of variance) - "
                 "visualisation only", x=0.01, ha="left", fontweight="bold", fontsize=13)
    _note(fig, "PCA compresses the 3 scaled features into 2 axes for plotting. Clustering was done on all 3 "
               "features, so a 2-D view cannot show every separation exactly. X = cluster centre.")
    fig.tight_layout()
    _save(fig, "cluster_pca_visualization.png", out_dir, saved)


def plot_rfm_vs_ml_heatmap(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _note, PAL
    import seaborn as sns
    plt = _style()
    ct = R["comparison"]["crosstab"]
    rp = R["comparison"]["row_pct"]
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    annot = rp.map(lambda v: f"{v:.0f}%") + "\n(" + ct.astype(str) + ")"
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.heatmap(rp, annot=annot, fmt="", cmap=sns.light_palette(PAL["blue"], as_cmap=True), vmin=0, vmax=100,
                linewidths=2, linecolor="white", cbar_kws={"label": "% of the RFM segment"}, ax=ax,
                annot_kws={"fontsize": 8.5})
    ax.set_xticklabels([f"{c}\n{L[int(c.split()[1])]}" for c in ct.columns], rotation=0, fontsize=9)
    ax.set_ylabel("Rule-based RFM segment (Step 5)")
    ax.set_xlabel("K-Means cluster (Step 6)")
    agree = R["comparison"]["agreement"].set_index("Measure")["Value"]
    ax.set_title(f"Where each RFM segment's customers landed in K-Means "
                 f"(ARI {agree['Adjusted Rand Index (RFM segment vs cluster)']:.2f}, "
                 f"NMI {agree['Normalized Mutual Information']:.2f})")
    _note(fig, "Each row sums to 100% (count in brackets). Same 1,984 customers in both methods. Differences show "
               "where predefined rules and data-driven similarity disagree - neither is 'correct' by definition.")
    fig.tight_layout()
    _save(fig, "rfm_vs_ml_cluster_heatmap.png", out_dir, saved)


def plot_centroid_heatmap(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _note
    import seaborn as sns
    plt = _style()
    c = R["centroids"]
    L = R["labels"].set_index("Cluster_ID")["Business_Label"]
    z = c[[f"{f}_scaled_centre" for f in CORE_FEATURES]].to_numpy()
    orig = c[[f"{f}_centre_original_units" for f in CORE_FEATURES]].to_numpy()
    annot = np.empty(z.shape, dtype=object)
    for i in range(z.shape[0]):
        annot[i, 0] = f"{z[i, 0]:+.2f}\n~{orig[i, 0]:.0f} days"
        annot[i, 1] = f"{z[i, 1]:+.2f}\n~{orig[i, 1]:.1f} orders"
        annot[i, 2] = f"{z[i, 2]:+.2f}\n~{inr(orig[i, 2])}"
    favour = z * np.array([-1, 1, 1])   # colour by favourability: fewer days since purchase = better
    fig, ax = plt.subplots(figsize=(9, 4.4))
    sns.heatmap(pd.DataFrame(favour, columns=["Recency", "Frequency", "Monetary"],
                             index=[f"Cluster {i}: {L[i]}" for i in c["Cluster_ID"]]),
                annot=annot, fmt="", cmap=sns.diverging_palette(12, 250, s=75, l=50, as_cmap=True), center=0,
                vmin=-2, vmax=2, linewidths=2, linecolor="white",
                cbar_kws={"label": "Favourability vs average customer (std units)"},
                ax=ax, annot_kws={"fontsize": 9})
    ax.set_title("Cluster centres: scaled value (top) and back-transformed original units (bottom)")
    _note(fig, "Numbers: scaled centre (std units from the average customer, log scale) and original units = "
               "expm1(inverse-scaled centre). Colour: blue = more favourable than average (more recent, more orders, "
               "more spend), red = less favourable.")
    fig.tight_layout()
    _save(fig, "cluster_centroid_profile.png", out_dir, saved)


def plot_feature_transformation(R: dict, out_dir: Path, saved: list) -> None:
    from src.eda import _style, _save, _note, PAL
    plt = _style()
    df = R["input"]
    D = R["distribution"].set_index("Feature")
    fig, axes = plt.subplots(2, 3, figsize=(15, 6.6))
    for j, f in enumerate(CORE_FEATURES):
        axes[0, j].hist(df[f], bins=40, color=PAL["neutral"], edgecolor="white")
        axes[0, j].set_title(f"{f} - raw (skew {D.loc[f, 'Skewness_raw']:.2f})", fontsize=10.5)
        axes[1, j].hist(np.log1p(df[f]), bins=40, color=PAL["blue"], edgecolor="white")
        axes[1, j].set_title(f"log(1 + {f}) - model input (skew {D.loc[f, 'Skewness_log1p']:.2f})", fontsize=10.5)
    axes[0, 0].set_ylabel("Customers")
    axes[1, 0].set_ylabel("Customers")
    fig.suptitle("Why log1p: raw RFM values are strongly right-skewed; the log scale is close to symmetric",
                 x=0.01, ha="left", fontweight="bold", fontsize=13)
    _note(fig, "The model uses log1p values, then standard scaling. Original values are kept in the dataset for all "
               "business reporting.")
    fig.tight_layout()
    _save(fig, "kmeans_feature_transformation.png", out_dir, saved)


def plot_segmentation_figures(R: dict, out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for fn in (plot_feature_transformation, plot_elbow_curve, plot_k_metrics, plot_silhouette_diagram,
               plot_cluster_bars, plot_cluster_scatter, plot_pca, plot_centroid_heatmap, plot_rfm_vs_ml_heatmap):
        fn(R, out_dir, saved)
    return saved


# =============================================================================
# 9. REPORT
# =============================================================================
def write_model_report(R: dict, path: Path = REPORT_FILE) -> Path:
    """outputs/reports/kmeans_model_report.md - every number inserted from the results."""
    from src.eda import _md_table
    k = R["k"]
    ev = R["k_selection"]
    P = R["profile"]
    FM = R["final_metrics"].set_index("Metric")["Value"]
    agree = R["comparison"]["agreement"].set_index("Measure")["Value"]
    fs = R["feature_selection"]
    evt = ev[["k", "inertia", "inertia_drop_%", "silhouette", "davies_bouldin", "calinski_harabasz",
              "min_cluster_share", "stability_ari_mean", "Eligible", "Selected"]].copy()
    evt["inertia"] = evt["inertia"].round(1)
    evt["inertia_drop_%"] = evt["inertia_drop_%"].round(1)
    evt["silhouette"] = evt["silhouette"].round(3)
    evt["davies_bouldin"] = evt["davies_bouldin"].round(3)
    evt["calinski_harabasz"] = evt["calinski_harabasz"].round(0)
    evt["min_cluster_share"] = (evt["min_cluster_share"] * 100).round(1).astype(str) + "%"
    evt["stability_ari_mean"] = evt["stability_ari_mean"].round(3)
    prof = P[["Cluster_ID", "Business_Label", "Customer_Count", "Customer_%", "Median_Recency", "Median_Frequency",
              "Median_Monetary", "Average_Monetary", "Total_Revenue", "Revenue_%", "Average_Order_Value",
              "Average_Discount"]].copy()
    prof["Customer_%"] = prof["Customer_%"].map(lambda v: f"{v:.1f}%")
    prof["Revenue_%"] = prof["Revenue_%"].map(lambda v: f"{v:.1f}%")
    for c in ["Median_Monetary", "Average_Monetary", "Total_Revenue", "Average_Order_Value"]:
        prof[c] = prof[c].map(inr)
    prof["Average_Discount"] = (prof["Average_Discount"] * 100).map(lambda v: f"{v:.1f}%")
    cen = R["centroids"][["Cluster_ID", "Recency_Profile", "Frequency_Profile", "Monetary_Profile"]]
    pcs = R["pca_summary"]
    pc_ev = pcs[pcs["Component"].notna()][["Component", "Explained_Variance_%"]].round(2)
    pc_ld = pcs[pcs["Loading_of"].notna()][["Loading_of", "PC1", "PC2"]]
    dist = R["distribution"][["Feature", "Median", "Mean", "Max", "Skewness_raw", "Skewness_log1p", "Apply_log1p"]].round(2)
    by_seg = R["comparison"]["by_segment"]
    by_clu = R["comparison"]["by_cluster"]
    sil_c = R["silhouette_by_cluster"].round(3)
    text = f"""# K-Means Customer Segmentation: Model Report

> **SYNTHETIC DATA.** This report is generated by `src/segmentation.py`. Every number is computed from `data/processed/customer_rfm_segments.csv` (Step 5).

## 1. Objective
The aim is to discover naturally occurring customer groups with **K-Means**, an **unsupervised learning** method. There is no target variable and no "right answer" to train against. The algorithm places customers who are close together in feature space into the same group.

The ML clusters are then profiled in business terms and compared with the rule-based RFM segments from Step 5.

## 2. Input Features
- **Population:** {len(R['input']):,} customers, one row each. These are all the customers scored in Step 5. None were removed.
- **Final model features, in this order:** `{', '.join(CORE_FEATURES)}`.

**Feature selection evidence**
{_md_table(fs['feature_decisions'][['Feature', 'Skewness', 'Max_abs_Spearman_with_core_RFM', 'Most_correlated_core_feature', 'Decision', 'Reason']])}

Adding extra features **lowered** cluster separation at every K compared (K = 3, 4 and 5):
{_md_table(fs['feature_set_comparison'])}

**Not used:** Customer_ID, names, R/F/M scores and RFM segment labels (these would re-encode the Step 5 rules), and any future-period target.

## 3. Preprocessing and Data Quality
{_md_table(R['data_quality'])}

Extreme values are genuine customers, so they were kept. The log transform limits their influence.

## 4. Transformation
{_md_table(dist)}

- All three features are strongly right-skewed (|skew| > 1), and `log1p` brings each close to symmetric. K-Means uses squared distances, so without the transform a handful of very large spenders would pull the centroids.
- **Original values are kept** in `customer_ml_segments.csv` for all business reporting. Transformed values are used **only for modelling**.

## 5. Scaling
- **Method:** `StandardScaler`, so each feature has mean 0 and standard deviation 1 after the log transform.
- **Why:** K-Means relies on Euclidean distance. Without scaling, Monetary (hundreds to lakhs of rupees) would dominate Frequency (1-29 orders) and Recency (1-1,096 days).
- **Saved as:** one sklearn `Pipeline` (log1p → StandardScaler) in `models/rfm_scaler.pkl`, with the fixed feature order `{CORE_FEATURES}`.

## 6. K Values Tested, Elbow and Silhouette Results
- **K values tested:** 2 to 10.
- **Model:** `KMeans(random_state={SEED}, n_init="auto")` (k-means++ initialisation, scikit-learn {sklearn.__version__}).
- **Stability check:** each K was also refitted with 10 other random seeds and compared using the Adjusted Rand Index (ARI).

{_md_table(evt)}

- **Elbow:** the largest distance from the straight line joining K = 2 and K = 10 is at **K = {int(ev.loc[ev['elbow_distance'].idxmax(), 'k'])}**. Going from K = {k - 1} to K = {k} cuts inertia by {ev.set_index('k').loc[k, 'inertia_drop_%']:.1f}%. The next step, to K = {k + 1}, cuts it by only {ev.set_index('k').loc[k + 1, 'inertia_drop_%']:.1f}%.
- **Silhouette:** highest at K = 2 ({ev.set_index('k').loc[2, 'silhouette']:.3f}), then K = {k} ({ev.set_index('k').loc[k, 'silhouette']:.3f}).

## 7. Selected K = {k}

**Selection rule**, written down before looking at the cluster profiles. No single metric decides.

| Rule | Reason | Result |
|---|---|---|
| 1. K ≥ {MIN_K_FOR_BUSINESS} | K = 2 can only separate "higher" from "lower" value, and cannot tell recent from lapsed. | Excludes K = 2 |
| 2. Every cluster ≥ {MIN_CLUSTER_SHARE:.0%} of customers | Very small clusters are not actionable | All K pass |
| 3. Mean seed-stability ARI ≥ {MIN_STABILITY_ARI} | The partition must be reproducible, not an artefact of one random start | Only K = 2 and K = {k} pass |
| 4. Highest silhouette among eligible K | Best-separated remaining option | **K = {k}** |

**Supporting evidence.**
- K = {k} has the **lowest Davies-Bouldin score of all K tested** ({ev.set_index('k').loc[k, 'davies_bouldin']:.3f}).
- It has the second-highest Calinski-Harabasz score.
- It coincides with the elbow.
- Its clusters are all reasonably large: the smallest holds {evt.set_index('k').loc[k, 'min_cluster_share']} of customers.

**Final model metrics**
{_md_table(R['final_metrics'])}

`n_init="auto"` runs a single k-means++ initialisation in this scikit-learn version. A check with `n_init=10` gives almost identical inertia ({FM['Inertia with n_init=10 (check)']} against {FM['Inertia (within-cluster sum of squares)']}), so a single initialisation is sufficient here.

**Silhouette by cluster**
{_md_table(sil_c)}

## 8. Cluster Sizes and Profiles (original units)
{_md_table(prof)}

**Cluster centres, converted back to days, orders and rupees.** The conversion is expm1 of the inverse-scaled centre, which gives a geometric-mean-type centre. It should be read next to the medians above.
{_md_table(cen)}

**How the labels were assigned.** Labels were attached **after** profiling, using two measured dimensions:
- **Value:** the cluster's median Monetary compared with the all-customer Monetary terciles.
- **Activity:** the cluster's median Recency compared with the Step 5 recency-score cut-offs: Active ≤ 83 days, Inactive ≥ 255 days, Lapsing in between.
{_md_table(R['labels'])}

## 9. PCA Results (visualisation only)
{_md_table(pc_ev)}

**Loadings:**
{_md_table(pc_ld)}

- PC1 is driven by Frequency and Monetary together with lower Recency, so it reads as an overall value-and-activity axis.
- PC2 is dominated by Recency.
- Two components retain {FM['PC1 + PC2 explained variance (%)']}% of the variance, so the 2-D plot is a faithful but not perfect picture.
- The clustering itself used all three scaled features, not the PCA components.

## 10. Comparison with the Rule-Based RFM Segments
- **Same customers in both methods:** {int(agree['Customers compared']):,}.
- **Adjusted Rand Index:** {agree['Adjusted Rand Index (RFM segment vs cluster)']:.3f}.
- **Normalized Mutual Information:** {agree['Normalized Mutual Information']:.3f}.
- **ARI against the four Step 5 value-activity groups:** {agree['ARI (RFM value-activity group vs cluster)']:.3f}.

{_md_table(by_seg)}

{_md_table(by_clu)}

**The two methods answer different questions.**
- RFM segmentation applies **predefined analytical rules** to quintile scores.
- K-Means groups customers by **similarity in the transformed feature space**.

Where they disagree, that shows where the rule boundaries do not match the data's natural structure. It does not make either method wrong.

## 11. Limitations
1. **Choices shape the result.** K-Means assumes compact, roughly spherical clusters of similar spread. The result depends on the log transform, the scaling and the choice of K.
2. **Customers near a boundary are ambiguous.** {int(FM['Customers with negative silhouette'])} customers have a negative silhouette, meaning they are closer to a neighbouring cluster than to their own.
3. **Only behaviour is used.** The clusters use three behavioural features (R, F, M). Margin, category mix and discount sensitivity are profiled afterwards but do not shape the clusters.
4. **Full-period data.** The features cover all 36 months, so the clusters describe *past* behaviour. For the revenue prediction in Step 8, cluster membership would have to be re-derived on the observation window to avoid leakage.
5. **Relative labels.** The business labels (High / Mid / Low value; Active / Lapsing / Inactive) are relative to this customer base.
6. **The data are synthetic.** The clusters illustrate the method, not a real market.

## 12. Business Interpretation
""" + "\n".join(f"- **{r['Cluster']}.** {r['Customer Profile']}. *Evidence:* {r['Evidence']}. *Interpretation:* "
                 f"{r['Business Interpretation']}." for _, r in R["insights"].iterrows()) + f"""

### Answers to the business questions
{_md_table(R['questions'])}

## 13. Validation
{_md_table(R['validation'])}

## 14. Reloading the Model
```python
import joblib, pandas as pd
pre = joblib.load("models/rfm_scaler.pkl")                    # log1p -> StandardScaler
km  = joblib.load("models/kmeans_customer_segmentation.pkl")  # KMeans(n_clusters={k})
pca = joblib.load("models/pca_rfm.pkl")                        # 2-D PCA (visualisation)
X = df[{CORE_FEATURES}]                                        # same feature order as training
df["Cluster_ID"] = km.predict(pre.transform(X))
```
The feature order, scikit-learn version and cluster labels are recorded in `models/segmentation_model_metadata.json`.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# =============================================================================
# 10. MAIN
# =============================================================================
def run_segmentation(make_plots: bool = True, verbose: bool = True) -> dict:
    R = run_segmentation_analysis()
    R["saved"] = save_segmentation_outputs(R)
    # Reload the artefacts from disk and confirm they reproduce every assignment
    pre, km = joblib.load(PREPROCESSOR_FILE), joblib.load(KMEANS_FILE)
    reloaded = km.predict(pre.transform(R["segments"][CORE_FEATURES].astype(float)))
    ok = bool((reloaded == R["segments"]["Cluster_ID"].to_numpy()).all())
    R["validation"].loc[R["validation"]["Check"] == "Saved model + preprocessor reproduce the assignments",
                        ["Value", "Pass"]] = ["reloaded .pkl files from models/", ok]
    R["validation"].to_csv(config.TABLES_DIR / "ml_validation_checks.csv", index=False, encoding="utf-8-sig")
    R["figures"] = plot_segmentation_figures(R) if make_plots else []
    R["report"] = write_model_report(R)
    if verbose:
        pd.set_option("display.width", 220)
        print(f"*** {config.DATASET_LABEL} ***")
        print(R["k_selection"][["k", "inertia", "silhouette", "davies_bouldin", "calinski_harabasz",
                                "min_cluster_share", "stability_ari_mean", "Eligible", "Selected"]].round(3)
              .to_string(index=False), "\n")
        print(R["final_metrics"].to_string(index=False), "\n")
        print(R["profile"][["Cluster_ID", "Business_Label", "Customer_Count", "Customer_%", "Median_Recency",
                            "Median_Frequency", "Median_Monetary", "Revenue_%"]].round(1).to_string(index=False), "\n")
        print(R["validation"][["Check", "Pass"]].to_string(index=False), "\n")
        print(f"Files saved: {len(R['saved'])} | Figures: {len(R['figures'])} | "
              f"Report: {R['report'].relative_to(config.PROJECT_ROOT)}")
        if not R["validation"]["Pass"].all():
            print("WARNING: some validation checks failed")
    return R


if __name__ == "__main__":
    run_segmentation()
