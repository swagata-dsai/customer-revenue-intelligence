#!/usr/bin/env python3
"""
database.py
===========
Builds the project SQLite database from the CLEANED data (Step 3) and the customer-level outputs of Steps 5-9,
using the schema in sql/schema.sql, then validates it against the source files.

    TRANSACTIONAL CORE   locations -> customers -> orders -> order_items <- products
    ANALYTICS LAYER      customer_rfm (-> rfm_segment_definitions), customer_segments (-> ml_clusters),
                         customer_value, revenue_forecasts
    VIEWS                vw_sales_flat (all lines), vw_delivered_sales (revenue rule)

The schema's CHECK and FOREIGN KEY constraints act as a final validation gate: if any source file broke a
business rule, the load would fail.

Run from the project root:
    python sql/load_database.py          (or: python src/database.py)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

SCHEMA_FILE = config.SQL_DIR / "schema.sql"
RFM_FILE = config.PROCESSED_DIR / "customer_rfm_segments.csv"
ML_FILE = config.PROCESSED_DIR / "customer_ml_segments.csv"
CLV_FILE = config.PROCESSED_DIR / "customer_clv.csv"
FORECAST_FILE = config.PROCESSED_DIR / "revenue_forecast.csv"
ML_METADATA_FILE = config.PROJECT_ROOT / "models" / "segmentation_model_metadata.json"
OLD_DB = config.PROCESSED_DIR / "revenue_intelligence.db"      # Step 3 location, superseded in Step 10

LOAD_ORDER = ["locations", "customers", "products", "orders", "order_items", "rfm_segment_definitions",
              "customer_rfm", "ml_clusters", "customer_segments", "customer_value", "revenue_forecasts"]
PRIMARY_KEYS = {"locations": ["location_id"], "customers": ["customer_id"], "products": ["product_id"],
                "orders": ["order_id"], "order_items": ["order_line_id"], "rfm_segment_definitions": ["segment_name"],
                "customer_rfm": ["customer_id"], "ml_clusters": ["cluster_id"], "customer_segments": ["customer_id"],
                "customer_value": ["customer_id"], "revenue_forecasts": ["month", "record_type"]}
FOREIGN_KEYS = [  # child table, child column, parent table, parent column
    ("customers", "location_id", "locations", "location_id"),
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("customer_rfm", "customer_id", "customers", "customer_id"),
    ("customer_rfm", "rfm_segment", "rfm_segment_definitions", "segment_name"),
    ("customer_segments", "customer_id", "customers", "customer_id"),
    ("customer_segments", "cluster_id", "ml_clusters", "cluster_id"),
    ("customer_value", "customer_id", "customers", "customer_id"),
]


# =============================================================================
# 1. SPLIT SOURCE FILES INTO TABLES
# =============================================================================
def check_grain(df: pd.DataFrame) -> None:
    """Order- and customer-level attributes must be single-valued before normalising."""
    order_attrs = df.groupby("Order_ID")[["Customer_ID", "Order_Date", "Payment_Method", "Customer_Type"]].nunique()
    cust_attrs = df.groupby("Customer_ID")[["Customer_Name", "Customer_Age", "Gender", "City"]].nunique()
    problems = int((order_attrs > 1).any(axis=1).sum()) + int((cust_attrs > 1).any(axis=1).sum())
    if problems:
        raise ValueError(f"{problems} orders/customers have conflicting attributes - fix cleaning first.")


def split_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split the flat cleaned table into the five normalised transactional tables."""
    loc = df[["City", "State", "Region"]].drop_duplicates().sort_values(["Region", "State", "City"])
    loc = loc.reset_index(drop=True)
    loc.insert(0, "location_id", loc.index + 1)
    cust = (df.drop_duplicates("Customer_ID")
            .merge(loc, on=["City", "State", "Region"], how="left")
            [["Customer_ID", "Customer_Name", "Customer_Age", "Gender", "location_id"]])
    prod = df.drop_duplicates("Product_ID")[["Product_ID", "Product_Name", "Category", "Sub_Category"]]
    orders = df.drop_duplicates("Order_ID")[["Order_ID", "Customer_ID", "Order_Date", "Payment_Method", "Customer_Type"]]
    items = df[["Order_Line_ID", "Order_ID", "Product_ID", "Quantity", "Unit_Price", "Discount", "Sales", "Cost",
                "Profit", "Order_Status"]]
    lower = lambda t: t.rename(columns=str.lower)  # noqa: E731
    return {"locations": lower(loc), "customers": lower(cust), "products": lower(prod), "orders": lower(orders),
            "order_items": lower(items)}


def analytics_tables() -> dict[str, pd.DataFrame]:
    """Customer-level outputs of Steps 5-9, reshaped to the analytics-layer tables (no recomputation)."""
    import json
    from src.rfm import SEGMENT_RULES
    rfm = pd.read_csv(RFM_FILE, encoding="utf-8-sig")
    ml = pd.read_csv(ML_FILE, encoding="utf-8-sig")
    clv = pd.read_csv(CLV_FILE, encoding="utf-8-sig")
    fc = pd.read_csv(FORECAST_FILE, encoding="utf-8-sig")
    meta_rfm = json.loads((config.PROCESSED_DIR / "customer_rfm_metadata.json").read_text(encoding="utf-8"))
    meta_ml = json.loads(ML_METADATA_FILE.read_text(encoding="utf-8"))
    seg_def = pd.DataFrame([{"segment_name": r[0], "priority": i + 1, "rule_text": r[2], "business_meaning": r[3],
                             "value_activity_group": r[4]} for i, r in enumerate(SEGMENT_RULES)])
    crfm = pd.DataFrame({
        "customer_id": rfm["Customer_ID"], "reference_date": meta_rfm["reference_date"],
        "recency_days": rfm["Recency"], "frequency_orders": rfm["Frequency"], "monetary_revenue": rfm["Monetary"],
        "r_score": rfm["R_Score"], "f_score": rfm["F_Score"], "m_score": rfm["M_Score"],
        "rfm_cell": rfm["RFM_Cell"].astype(str), "rfm_score": rfm["RFM_Score"], "fm_score": rfm["FM_Score"],
        "rfm_segment": rfm["RFM_Segment"], "first_purchase_date": rfm["First_Purchase_Date"].astype(str).str[:10],
        "last_purchase_date": rfm["Last_Purchase_Date"].astype(str).str[:10],
        "acquisition_status": rfm["Acquisition_Status"]})
    clus = (ml[["Cluster_ID", "Cluster_Label"]].drop_duplicates().sort_values("Cluster_ID")
            .rename(columns={"Cluster_ID": "cluster_id", "Cluster_Label": "cluster_label"}))
    clus["model"] = meta_ml.get("model", "KMeans")
    cseg = ml[["Customer_ID", "Cluster_ID", "Silhouette", "PC1", "PC2"]].rename(columns=str.lower)
    flags = ["High_Historical_Value", "High_Estimated_Future_Value", "High_Value_High_Engagement",
             "Potentially_At_Risk_High_Value", "Future_Value_Opportunity"]
    cval = clv[["Customer_ID", "Historical_Revenue_CLV", "Historical_Profit_CLV", "Estimated_12M_Future_Profit",
                "Estimate_Method", "Simplified_12M_Estimate", "Illustrative_3Y_Value"] + flags].copy()
    for f in flags:
        cval[f] = cval[f].astype(str).str.lower().map({"true": 1, "false": 0}).astype(int)
    cval = cval.rename(columns=str.lower)
    fcast = fc.rename(columns={"Month": "month", "Type": "record_type", "Actual_Revenue": "actual_revenue",
                               "Forecast": "forecast_revenue", "Lower_80": "lower_80", "Upper_80": "upper_80",
                               "Lower_95": "lower_95", "Upper_95": "upper_95", "Model": "model"})
    fcast["model"] = fcast["model"].where(fcast["model"].notna() & (fcast["model"].astype(str) != ""), None)
    return {"rfm_segment_definitions": seg_def, "customer_rfm": crfm, "ml_clusters": clus,
            "customer_segments": cseg, "customer_value": cval, "revenue_forecasts": fcast}


# =============================================================================
# 2. BUILD
# =============================================================================
def build_database(csv_path: Path = config.CLEAN_DATA_FILE, db_path: Path = config.DATABASE_FILE) -> dict:
    """Create the database, create tables from schema.sql, load all tables in FK order, save."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    check_grain(df)
    tables = {**split_tables(df), **analytics_tables()}
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        con.execute("PRAGMA foreign_keys = ON")
        for name in LOAD_ORDER:
            tables[name].to_sql(name, con, if_exists="append", index=False)
        con.commit()
    finally:
        con.close()
    if OLD_DB.exists() and OLD_DB != db_path:          # avoid two diverging copies of the database
        OLD_DB.unlink()
    return {"db_path": db_path, "source_rows": {k: len(v) for k, v in tables.items()}, "source": df}


# =============================================================================
# 3. VALIDATE
# =============================================================================
def validate_database(db_path: Path = config.DATABASE_FILE, source: pd.DataFrame | None = None) -> pd.DataFrame:
    """Reconcile the database with the source CSVs (pandas) and check keys, nulls and relationships."""
    src = source if source is not None else pd.read_csv(config.CLEAN_DATA_FILE, encoding="utf-8-sig")
    d = src[src["Order_Status"] == "Delivered"]
    rfm = pd.read_csv(RFM_FILE, encoding="utf-8-sig")
    clv = pd.read_csv(CLV_FILE, encoding="utf-8-sig")
    fc = pd.read_csv(FORECAST_FILE, encoding="utf-8-sig")
    con = sqlite3.connect(db_path)
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    rows = []

    def add(area, check, sql_value, python_value, ok):
        rows.append({"Area": area, "Check": check, "SQL": sql_value, "Python / source": python_value, "Pass": bool(ok)})

    expected = {"locations": src[["City", "State"]].drop_duplicates().shape[0], "customers": src["Customer_ID"].nunique(),
                "products": src["Product_ID"].nunique(), "orders": src["Order_ID"].nunique(), "order_items": len(src),
                "rfm_segment_definitions": 11, "customer_rfm": len(rfm), "ml_clusters": 4,
                "customer_segments": len(rfm), "customer_value": len(clv), "revenue_forecasts": len(fc)}
    for t, e in expected.items():
        n = q(f"SELECT COUNT(*) FROM {t}")
        add("Row counts", f"{t} rows", n, e, n == e)
    add("Row counts", "vw_sales_flat rows = cleaned CSV rows", q("SELECT COUNT(*) FROM vw_sales_flat"), len(src),
        q("SELECT COUNT(*) FROM vw_sales_flat") == len(src))
    add("Uniqueness", "Unique customers with a Delivered order",
        q("SELECT COUNT(DISTINCT customer_id) FROM vw_delivered_sales"), d["Customer_ID"].nunique(),
        q("SELECT COUNT(DISTINCT customer_id) FROM vw_delivered_sales") == d["Customer_ID"].nunique())
    add("Uniqueness", "Unique products", q("SELECT COUNT(DISTINCT product_id) FROM order_items"),
        src["Product_ID"].nunique(), q("SELECT COUNT(DISTINCT product_id) FROM order_items") == src["Product_ID"].nunique())
    for label, sql, py in (("Total revenue (Delivered Sales)", "SELECT SUM(sales) FROM vw_delivered_sales", d["Sales"].sum()),
                           ("Total profit (Delivered)", "SELECT SUM(profit) FROM vw_delivered_sales", d["Profit"].sum()),
                           ("Total cost (Delivered)", "SELECT SUM(cost) FROM vw_delivered_sales", d["Cost"].sum()),
                           ("Total quantity (Delivered)", "SELECT SUM(quantity) FROM vw_delivered_sales", d["Quantity"].sum())):
        v = q(sql)
        add("Totals", label, round(v, 2), round(float(py), 2), abs(v - py) < 0.01)
    for label, sql, py in (("Delivered orders", "SELECT COUNT(DISTINCT order_id) FROM vw_delivered_sales", d["Order_ID"].nunique()),
                           ("All orders", "SELECT COUNT(*) FROM orders", src["Order_ID"].nunique())):
        v = q(sql)
        add("Totals", label, v, py, v == py)
    # nulls in NOT NULL / key columns
    for t in LOAD_ORDER:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})").fetchall() if r[3] == 1 or r[5] > 0]
        n = sum(q(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NULL") for c in cols)
        add("Nulls", f"{t}: NULLs in NOT NULL / key columns", n, 0, n == 0)
    # duplicate primary keys
    for t, pk in PRIMARY_KEYS.items():
        k = ", ".join(pk)
        n = q(f"SELECT COUNT(*) FROM (SELECT {k} FROM {t} GROUP BY {k} HAVING COUNT(*) > 1)")
        add("Primary keys", f"{t}: duplicate ({k})", n, 0, n == 0)
    # orphan foreign keys (explicit LEFT JOIN) + SQLite's own check
    for child, ccol, parent, pcol in FOREIGN_KEYS:
        n = q(f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.{ccol} = p.{pcol} WHERE p.{pcol} IS NULL")
        add("Foreign keys", f"{child}.{ccol} -> {parent}.{pcol}: orphans", n, 0, n == 0)
    n = len(con.execute("PRAGMA foreign_key_check").fetchall())
    add("Foreign keys", "PRAGMA foreign_key_check violations", n, 0, n == 0)
    # cross-step consistency (SQL recomputation vs Python outputs)
    diff = q("""SELECT COUNT(*) FROM customer_rfm r JOIN (SELECT customer_id, SUM(sales) s, COUNT(DISTINCT order_id) n
               FROM vw_delivered_sales GROUP BY customer_id) x USING (customer_id)
               WHERE ABS(r.monetary_revenue - x.s) > 0.01 OR r.frequency_orders <> x.n""")
    add("Cross-step", "Step 5 Monetary / Frequency = SQL recomputation (per customer)", diff, 0, diff == 0)
    diff = q("""SELECT COUNT(*) FROM customer_value v JOIN (SELECT customer_id, SUM(profit) p FROM vw_delivered_sales
               GROUP BY customer_id) x USING (customer_id) WHERE ABS(v.historical_profit_clv - x.p) > 0.01""")
    add("Cross-step", "Step 7 historical profit CLV = SQL recomputation (per customer)", diff, 0, diff == 0)
    diff = q("""SELECT COUNT(*) FROM revenue_forecasts f JOIN (SELECT order_month, SUM(sales) s FROM vw_delivered_sales
               GROUP BY order_month) m ON m.order_month = f.month
               WHERE f.record_type = 'Historical actual' AND ABS(f.actual_revenue - m.s) > 0.01""")
    add("Cross-step", "Step 9 monthly actuals = SQL monthly revenue", diff, 0, diff == 0)
    ml_tab = pd.read_csv(config.TABLES_DIR / "ml_cluster_summary.csv", encoding="utf-8-sig")
    sql_cl = pd.read_sql("""SELECT s.cluster_id, SUM(d.sales) AS rev FROM customer_segments s
                            JOIN vw_delivered_sales d USING (customer_id) GROUP BY s.cluster_id""", con)
    m = sql_cl.merge(ml_tab[["Cluster_ID", "Total_Revenue"]], left_on="cluster_id", right_on="Cluster_ID")
    add("Cross-step", "Step 6 cluster revenue = SQL revenue by cluster", f"{len(m)} clusters", "ml_cluster_summary.csv",
        len(m) == 4 and np.allclose(m["rev"], m["Total_Revenue"], atol=0.01))
    con.close()
    return pd.DataFrame(rows)


def table_catalog(db_path: Path = config.DATABASE_FILE) -> pd.DataFrame:
    """Every table: rows, columns, primary key and foreign keys (from SQLite metadata)."""
    con = sqlite3.connect(db_path)
    out = []
    for t in LOAD_ORDER:
        info = con.execute(f"PRAGMA table_info({t})").fetchall()
        fks = con.execute(f"PRAGMA foreign_key_list({t})").fetchall()
        out.append({"Table": t, "Layer": "Transactional" if LOAD_ORDER.index(t) < 5 else "Analytics",
                    "Rows": con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], "Columns": len(info),
                    "Primary_Key": ", ".join(r[1] for r in sorted(info, key=lambda r: r[5]) if r[5] > 0),
                    "Foreign_Keys": "; ".join(f"{f[3]} -> {f[2]}.{f[4]}" for f in fks) or "-",
                    "Column_Types": ", ".join(f"{r[1]} {r[2]}" for r in info)})
    con.close()
    return pd.DataFrame(out)


if __name__ == "__main__":
    res = build_database()
    v = validate_database(source=res["source"])
    print(f"*** {config.DATASET_LABEL} ***")
    print(f"Database: {res['db_path'].relative_to(config.PROJECT_ROOT)}")
    print(table_catalog()[["Table", "Layer", "Rows", "Primary_Key", "Foreign_Keys"]].to_string(index=False))
    print(f"\nValidation: {int(v['Pass'].sum())}/{len(v)} checks passed")
    if not v["Pass"].all():
        print(v[~v["Pass"]].to_string(index=False))
        raise SystemExit(1)
