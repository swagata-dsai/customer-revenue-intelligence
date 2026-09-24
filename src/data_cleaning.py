#!/usr/bin/env python3
"""
data_cleaning.py
================
Step 3 of the Customer Revenue Intelligence project: data cleaning,
validation and feature engineering.

    >>> Works on SYNTHETIC DATA generated in Step 2. <<<

Pipeline (each step is a function, so the notebook can call them one by one)

    load_data()               read the raw CSV exactly as stored (all text)
    audit_data()              measure every data-quality issue BEFORE changes
    remove_duplicates()       drop exact duplicate rows only
    standardize_types()       dates, numbers (e.g. '₹1,299' -> 1299.0), IDs
    standardize_categories()  one spelling per category / region / city ...
    validate_numeric_fields() apply business ranges; bad values -> NaN + flag
    handle_missing_values()   business-rule recovery first, statistics last
    validate_business_rules() Sales and Profit formulas: report, then correct
    detect_outliers()         IQR, z-score, business thresholds (flag only)
    create_features()         date, revenue, margin and band features
    build_customer_features() customer-level table (no RFM scores yet)
    save_clean_data()         CSVs, quality report, summary, charts

Principles
----------
* Nothing is changed silently: every correction writes a code into the
  `DQ_Flags` column of the affected row and is counted in the cleaning log.
* Data are removed only when they are genuine duplicates.
* The injection log from Step 2 is NEVER read here. Cleaning relies only on
  the data itself plus general business rules, as it would on a real extract.

Run from the project root:
    python src/data_cleaning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

# =============================================================================
# Reference rules (general business knowledge, not taken from the generator)
# =============================================================================
NUMERIC_COLS = ["Customer_Age", "Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit"]
ID_COLS = ["Order_Line_ID", "Order_ID", "Customer_ID", "Product_ID"]
DATE_COLS = ["Order_Date"]
CATEGORICAL_COLS = ["Customer_Name", "Gender", "City", "State", "Region", "Product_Name",
                    "Category", "Sub_Category", "Payment_Method", "Order_Status", "Customer_Type"]
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]  # ISO first; Indian day-first variants

GENDER_MAP = {"m": "Male", "male": "Male", "f": "Female", "female": "Female",
              "o": "Other", "other": "Other"}
PAYMENT_MAP = {"upi": "UPI", "card": "Card", "creditdebitcard": "Card", "creditcard": "Card",
               "debitcard": "Card", "cod": "COD", "cashondelivery": "COD",
               "netbanking": "Net Banking", "wallet": "Wallet", "ewallet": "Wallet"}
# Former / informal Indian place names -> current official names
CITY_ALIASES = {"Bangalore": "Bengaluru", "Bombay": "Mumbai", "Calcutta": "Kolkata",
                "Madras": "Chennai", "Gurgaon": "Gurugram", "Trivandrum": "Thiruvananthapuram",
                "Mysore": "Mysuru", "Vizag": "Visakhapatnam", "Poona": "Pune",
                "Baroda": "Vadodara", "Cochin": "Kochi"}
STATE_ALIASES = {"Orissa": "Odisha", "Tamilnadu": "Tamil Nadu", "Up": "Uttar Pradesh",
                 "Uttarpradesh": "Uttar Pradesh", "W. Bengal": "West Bengal",
                 "Wb": "West Bengal", "Chattisgarh": "Chhattisgarh", "Nct Of Delhi": "Delhi"}

OUTLIER_NOTES = {
    "Sales": "Right-skewed: a minority of premium-product lines sit above the fence",
    "Profit": "Both tails: large profits on premium items, losses on deep discounts",
    "Quantity": "IQR rule degenerate (Q1 = Q3 = 1, so every line with 2+ units is 'outside'); "
                "use z-score / business threshold (>= 10 units) instead",
    "Unit_Price": "Reflects the product price list (Rs 291 - Rs 98k); extremes are premium products",
}
BULK_QTY_THRESHOLD = 10          # business threshold: 10+ units in one line = bulk purchase
ALLOWED_PAYMENT_AFTER_CLEANING = config.VALID_PAYMENT_METHODS + ["Unknown"]
ALLOWED_GENDER_AFTER_CLEANING = config.VALID_GENDERS + ["Unknown"]


# =============================================================================
# Helpers
# =============================================================================
def _parse_dates(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Parse each known format explicitly. Returns (datetimes, format label)."""
    s = s.astype("string").str.strip()
    parsed = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    fmt_used = pd.Series(pd.NA, index=s.index, dtype="string")
    for fmt in DATE_FORMATS:
        todo = parsed.isna() & s.notna()
        attempt = pd.to_datetime(s[todo], format=fmt, errors="coerce")
        parsed.loc[attempt.index] = attempt
        fmt_used.loc[attempt.dropna().index] = fmt
    return parsed, fmt_used


def _to_number(s: pd.Series) -> pd.Series:
    """'₹1,299' -> 1299.0 ; blanks stay NaN ; anything unparseable -> NaN."""
    cleaned = s.astype("string").str.replace(r"[₹,\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _add_flag(df: pd.DataFrame, mask: pd.Series, code: str) -> None:
    """Append a correction code to DQ_Flags for the rows in mask."""
    mask = mask.fillna(False).astype(bool)
    current = df.loc[mask, "DQ_Flags"]
    df.loc[mask, "DQ_Flags"] = np.where(current == "", code, current + ";" + code)


def _mode(s: pd.Series):
    m = s.dropna().mode()
    return m.iloc[0] if len(m) else np.nan


def rule_violations(df: pd.DataFrame, cleaned: bool = False) -> pd.DataFrame:
    """
    One boolean column per business rule (True = row breaks the rule).
    Works on raw text data and on cleaned data, so before/after counts are
    measured with exactly the same yardstick.
    """
    # After cleaning, "Unknown" is the documented label for unrecoverable values.
    payment_allowed = ALLOWED_PAYMENT_AFTER_CLEANING if cleaned else config.VALID_PAYMENT_METHODS
    gender_allowed = ALLOWED_GENDER_AFTER_CLEANING if cleaned else config.VALID_GENDERS
    num = pd.DataFrame({c: _to_number(df[c]) for c in NUMERIC_COLS})
    dates = df["Order_Date"]
    if not pd.api.types.is_datetime64_any_dtype(dates):
        iso = pd.to_datetime(dates.astype("string"), format="%Y-%m-%d", errors="coerce")
    else:
        iso = dates
    v = pd.DataFrame(index=df.index)
    v["missing_value"] = df[config.EXPECTED_COLUMNS].isna().any(axis=1)
    v["non_iso_or_invalid_date"] = iso.isna()
    strict = {c: pd.to_numeric(df[c], errors="coerce") for c in NUMERIC_COLS}  # no ₹/comma stripping
    v["non_numeric_value"] = pd.concat(
        [df[c].notna() & strict[c].isna() for c in NUMERIC_COLS], axis=1).any(axis=1)
    v["quantity_not_positive"] = num["Quantity"] <= 0
    v["price_not_positive"] = num["Unit_Price"] <= 0
    v["discount_out_of_range"] = (num["Discount"] < 0) | (num["Discount"] > config.MAX_DISCOUNT)
    v["negative_sales_or_cost"] = (num["Sales"] < 0) | (num["Cost"] < 0)
    exp_sales = num["Quantity"] * num["Unit_Price"] * (1 - num["Discount"])
    v["revenue_mismatch"] = (num["Sales"] - exp_sales).abs() > config.CONSISTENCY_TOLERANCE_INR
    v["profit_mismatch"] = (num["Profit"] - (num["Sales"] - num["Cost"])).abs() > config.CONSISTENCY_TOLERANCE_INR
    lo, hi = config.VALID_AGE_RANGE
    v["age_out_of_range"] = (num["Customer_Age"] < lo) | (num["Customer_Age"] > hi)
    domains = {"Category": config.VALID_CATEGORIES, "Region": config.VALID_REGIONS,
               "Gender": gender_allowed, "Payment_Method": payment_allowed,
               "Order_Status": config.VALID_ORDER_STATUS, "Customer_Type": config.VALID_CUSTOMER_TYPES}
    v["invalid_category_value"] = pd.concat(
        [df[c].notna() & ~df[c].isin(allowed) for c, allowed in domains.items()], axis=1).any(axis=1)
    return v.fillna(False).astype(bool)


# =============================================================================
# 1. LOAD
# =============================================================================
def load_data(path: Path = config.RAW_DATA_FILE) -> pd.DataFrame:
    """Load the raw CSV with every column as text, so nothing is coerced before the audit."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/generate_dataset.py first.")
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=True)
    missing_cols = [c for c in config.EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Raw file is missing columns: {missing_cols}")
    return df


def describe_raw(df: pd.DataFrame) -> dict:
    """Shape, head/tail, inferred dtypes, statistics and column roles for the raw file."""
    inferred = pd.read_csv(config.RAW_DATA_FILE, encoding="utf-8-sig", nrows=None)  # pandas' own inference
    return {
        "shape": df.shape,
        "head": df.head(10),
        "tail": df.tail(10),
        "inferred_dtypes": inferred.dtypes.astype(str),
        "numeric_stats": inferred.describe().T.round(2),
        "text_stats": inferred.describe(include=["object", "string"]).T[["count", "unique", "top", "freq"]],
        "roles": pd.DataFrame({
            "Column": config.EXPECTED_COLUMNS,
            "Role": ["Identifier" if c in ID_COLS else "Date" if c in DATE_COLS
                     else "Numerical" if c in NUMERIC_COLS else "Categorical"
                     for c in config.EXPECTED_COLUMNS],
            "Type as read by pandas": [str(inferred[c].dtype) for c in config.EXPECTED_COLUMNS],
        }),
    }


# =============================================================================
# 2. AUDIT
# =============================================================================
def audit_data(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Measure every data-quality issue in the raw file.
    Returns: Issue | Column | Affected_Records | Percent_Affected | Treatment
    """
    n = len(raw)
    rows = []

    def add(issue, column, count, treatment):
        rows.append({"Issue": issue, "Column": column, "Affected_Records": int(count),
                     "Percent_Affected": round(100 * count / n, 2), "Treatment": treatment})

    # Missing values
    missing_treatment = {
        "Customer_Age": "Restore from the same customer's other rows (one profile per customer); median only as last resort",
        "Gender": "Restore from the same customer's other rows",
        "City": "Restore from the same customer's other rows",
        "Payment_Method": "Copy from other lines of the same order; otherwise label 'Unknown'",
        "Discount": "Back-calculate: 1 - Sales / (Quantity x Unit_Price)",
        "Sales": "Recompute exactly as Cost + Profit, then confirm against Qty x Price x (1 - Discount)",
    }
    for col, cnt in raw.isna().sum().items():
        if cnt:
            add("Missing value", col, cnt, missing_treatment.get(col, "Investigate"))

    # Duplicates
    full_dup = raw.duplicated()
    add("Exact duplicate row", "All columns", full_dup.sum(), "Remove (keep first occurrence)")
    pk_dup = raw["Order_Line_ID"].duplicated() & ~full_dup
    add("Duplicate Order_Line_ID with different content", "Order_Line_ID", pk_dup.sum(),
        "Investigate; keep both if content differs")
    lines_per_order = raw.drop_duplicates().groupby("Order_ID")["Order_Line_ID"].transform("count")
    add("Order_ID repeated across rows (multi-product orders)", "Order_ID", (lines_per_order > 1).sum(),
        "Keep - legitimate: one order can contain several products")
    profile_cols = ["Customer_Name", "Customer_Age", "Gender", "City"]
    varies = raw.groupby("Customer_ID")[profile_cols].nunique() > 1
    add("Customer profile differs across rows", "Customer_ID", varies.any(axis=1).sum(),
        "Harmonise to the customer's most frequent (modal) value")

    # Dates
    parsed, fmt = _parse_dates(raw["Order_Date"])
    add("Non-ISO date format (DD-MM-YYYY or DD/MM/YYYY)", "Order_Date",
        (fmt.notna() & (fmt != "%Y-%m-%d")).sum(), "Parse each format explicitly (day-first)")
    add("Unparseable date", "Order_Date", (parsed.isna() & raw["Order_Date"].notna()).sum(),
        "Remove row if no date can be recovered")

    # Types
    price_text = raw["Unit_Price"].notna() & pd.to_numeric(raw["Unit_Price"], errors="coerce").isna()
    add("Numeric value stored as text (e.g. '₹1,299')", "Unit_Price", price_text.sum(),
        "Strip ₹ symbol and commas, convert to float")

    num = pd.DataFrame({c: _to_number(raw[c]) for c in NUMERIC_COLS})
    add("Negative or zero quantity", "Quantity", (num["Quantity"] <= 0).sum(),
        "Recover true quantity from Sales / (Unit_Price x (1 - Discount)) when it is a whole number")
    add("Negative or zero unit price", "Unit_Price", (num["Unit_Price"] <= 0).sum(), "Recover from Sales")
    add("Discount > 1 (stored as percentage)", "Discount", (num["Discount"] > 1).sum(),
        "Divide by 100 when value is between 1 and 100")
    add("Discount < 0", "Discount", (num["Discount"] < 0).sum(), "Set to missing and back-calculate")
    add("Negative sales", "Sales", (num["Sales"] < 0).sum(), "Investigate")
    add("Invalid order status", "Order_Status",
        (raw["Order_Status"].notna() & ~raw["Order_Status"].isin(config.VALID_ORDER_STATUS)).sum(),
        "Map to Delivered / Cancelled / Returned")
    add("Negative cost", "Cost", (num["Cost"] < 0).sum(), "Investigate")
    exp_sales = num["Quantity"] * num["Unit_Price"] * (1 - num["Discount"])
    add("Sales != Qty x Price x (1 - Discount)", "Sales", ((num["Sales"] - exp_sales).abs() > 1).sum(),
        "Identify the wrong component (quantity, discount or price) and correct it; flag the row")
    add("Profit != Sales - Cost", "Profit",
        ((num["Profit"] - (num["Sales"] - num["Cost"])).abs() > 1).sum(), "Recompute Profit")
    lo, hi = config.VALID_AGE_RANGE
    add(f"Impossible age (outside {lo}-{hi})", "Customer_Age",
        ((num["Customer_Age"] < lo) | (num["Customer_Age"] > hi)).sum(),
        "Treat as missing, then restore from the customer's other rows")
    non_integer_age = num["Customer_Age"].notna() & (num["Customer_Age"] % 1 != 0)
    add("Non-integer age", "Customer_Age", non_integer_age.sum(), "Investigate")

    # Categorical domains
    domains = {"Category": config.VALID_CATEGORIES, "Region": config.VALID_REGIONS,
               "Gender": config.VALID_GENDERS, "Payment_Method": config.VALID_PAYMENT_METHODS,
               "Order_Status": config.VALID_ORDER_STATUS, "Customer_Type": config.VALID_CUSTOMER_TYPES}
    for col, allowed in domains.items():
        bad = raw[col].notna() & ~raw[col].isin(allowed)
        if col == "Order_Status":
            continue  # reported separately above
        add("Non-standard categorical value", col, bad.sum(),
            "Trim, fix case, map spelling variants to the standard value")
    old_city = raw["City"].isin(CITY_ALIASES)
    add("Former / informal city name", "City", old_city.sum(), "Map to current official name")
    old_state = raw["State"].str.strip().str.title().isin(STATE_ALIASES) | raw["State"].isin(STATE_ALIASES)
    add("Former / informal state name", "State", old_state.sum(), "Map to official state name")
    name_fmt = raw["Customer_Name"].notna() & (raw["Customer_Name"] != raw["Customer_Name"].str.strip().str.title())
    add("Name casing / spacing inconsistent", "Customer_Name", name_fmt.sum(), "Trim and title-case")

    # Geography: a city must map to one state, a state to one region
    geo = raw.dropna(subset=["City", "State", "Region"])
    city_state_mode = geo.groupby("City")["State"].agg(_mode)
    state_region_mode = geo.groupby("State")["Region"].agg(_mode)
    bad_cs = geo["State"] != geo["City"].map(city_state_mode)
    bad_sr = geo["Region"] != geo["State"].map(state_region_mode)
    add("Inconsistent City-State pair", "City/State", bad_cs.sum(),
        "Resolved by standardising state names; re-checked after cleaning")
    add("Inconsistent State-Region pair", "State/Region", bad_sr.sum(),
        "Resolved by standardising region labels; re-checked after cleaning")

    out = pd.DataFrame(rows)
    # Zero-count rows are kept on purpose: they prove the check was run.
    out.loc[out["Affected_Records"] == 0, "Treatment"] = "No action needed (check passed)"
    return out.reset_index(drop=True)


# =============================================================================
# 3. DUPLICATES
# =============================================================================
def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Row-level duplicate  : every column identical (double ingestion) -> REMOVE.
    Order-level repeat   : same Order_ID on several rows = multi-product order -> KEEP.
    Customer repetition  : same Customer_ID on many orders = repeat buyer -> KEEP.
    Potential duplicate  : same order, product, qty, price but different line ID -> FLAG only.
    """
    before = len(df)
    exact = df.duplicated(keep="first")
    out = df.loc[~exact].copy().reset_index(drop=True)
    info = {"rows_before": before, "exact_duplicates_removed": int(exact.sum()), "rows_after": len(out)}
    # Order_Line_ID must now be unique; if not, the content differs and we keep both (flagged).
    info["remaining_duplicate_line_ids"] = int(out["Order_Line_ID"].duplicated().sum())
    return out, info


def flag_potential_duplicates(df: pd.DataFrame) -> pd.Series:
    """Same order, product, quantity and price on two lines: possible double scan (flag only)."""
    key = ["Order_ID", "Product_ID", "Quantity", "Unit_Price"]
    return df.duplicated(subset=key, keep=False)


# =============================================================================
# 4. TYPES
# =============================================================================
def standardize_types(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Dates -> datetime, numeric text -> float, IDs -> trimmed upper-case strings."""
    df = df.copy()
    df["DQ_Flags"] = ""
    parsed, fmt = _parse_dates(df["Order_Date"])
    _add_flag(df, fmt.notna() & (fmt != "%Y-%m-%d"), "date_format_fixed")
    unparseable = parsed.isna()
    df["Order_Date"] = parsed
    df = df.loc[~unparseable].copy()  # a sale without a date cannot be analysed in time

    price_is_text = df["Unit_Price"].notna() & pd.to_numeric(df["Unit_Price"], errors="coerce").isna()
    _add_flag(df, price_is_text, "price_text_converted")
    for c in NUMERIC_COLS:
        df[c] = _to_number(df[c])
    for c in ID_COLS:
        df[c] = df[c].astype("string").str.strip().str.upper()
    info = {"rows_dropped_unparseable_date": int(unparseable.sum()),
            "dates_reformatted": int((fmt.notna() & (fmt != "%Y-%m-%d")).sum()),
            "prices_converted_from_text": int(price_is_text.sum())}
    return df, info


# =============================================================================
# 5. CATEGORIES
# =============================================================================
def standardize_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One spelling per value. Returns the data and a before/after unique-value table."""
    df = df.copy()
    before = {c: sorted(df[c].dropna().unique().tolist()) for c in CATEGORICAL_COLS}

    def squash(s: pd.Series) -> pd.Series:
        return s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

    original = df.copy()  # keep raw spelling so whitespace-only fixes are flagged too
    for c in CATEGORICAL_COLS:
        df[c] = squash(df[c])

    df["Customer_Name"] = df["Customer_Name"].str.title()
    # Category: compare on a normalised key ("home and kitchen" == "Home & Kitchen")
    key = lambda s: s.str.lower().str.replace(" and ", " & ", regex=False)  # noqa: E731
    cat_lookup = {c.lower(): c for c in config.VALID_CATEGORIES}
    df["Category"] = key(df["Category"]).map(cat_lookup).fillna(df["Category"])
    df["Region"] = df["Region"].str.title()
    df["Gender"] = df["Gender"].str.lower().map(GENDER_MAP).fillna(df["Gender"])
    pay_key = df["Payment_Method"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    df["Payment_Method"] = pay_key.map(PAYMENT_MAP).fillna(df["Payment_Method"])
    df["City"] = df["City"].replace(CITY_ALIASES)
    state_title = df["State"].str.title()
    df["State"] = np.where(state_title.isin(STATE_ALIASES), state_title.map(STATE_ALIASES), df["State"])
    df["State"] = df["State"].astype("string")
    df["Order_Status"] = df["Order_Status"].str.title()
    df["Customer_Type"] = df["Customer_Type"].str.title()

    for c in CATEGORICAL_COLS:
        changed = original[c].notna() & (original[c] != df[c])
        _add_flag(df, changed, f"{c.lower()}_standardised")

    after = {c: sorted(df[c].dropna().unique().tolist()) for c in CATEGORICAL_COLS}
    comparison = pd.DataFrame({
        "Column": CATEGORICAL_COLS,
        "Unique_Before": [len(before[c]) for c in CATEGORICAL_COLS],
        "Unique_After": [len(after[c]) for c in CATEGORICAL_COLS],
        "Values_After (up to 12)": [", ".join(map(str, after[c][:12])) + (" ..." if len(after[c]) > 12 else "")
                                    for c in CATEGORICAL_COLS],
    })
    return df, comparison


# =============================================================================
# 6. NUMERIC VALIDATION
# =============================================================================
def validate_numeric_fields(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Apply business ranges. Values that are clearly errors become NaN (to be
    recovered in handle_missing_values) and are flagged. Legitimate extremes
    (e.g. bulk orders) are NOT touched here.
    """
    df = df.copy()
    info = {}
    lo, hi = config.VALID_AGE_RANGE
    bad_age = (df["Customer_Age"] < lo) | (df["Customer_Age"] > hi)
    _add_flag(df, bad_age, "age_invalid_restored")
    df.loc[bad_age, "Customer_Age"] = np.nan
    info["ages_out_of_range_set_missing"] = int(bad_age.sum())

    pct = (df["Discount"] > 1) & (df["Discount"] <= 100)
    _add_flag(df, pct, "discount_rescaled_from_percent")
    df.loc[pct, "Discount"] = df.loc[pct, "Discount"] / 100
    info["discounts_rescaled_from_percent"] = int(pct.sum())

    bad_disc = (df["Discount"] < 0) | (df["Discount"] > 1)
    _add_flag(df, bad_disc, "discount_invalid_recomputed")
    df.loc[bad_disc, "Discount"] = np.nan
    info["discounts_invalid_set_missing"] = int(bad_disc.sum())

    bad_qty = df["Quantity"] <= 0
    _add_flag(df, bad_qty, "quantity_invalid_recovered")
    df.loc[bad_qty, "Quantity"] = np.nan
    info["quantities_not_positive_set_missing"] = int(bad_qty.sum())

    bad_price = df["Unit_Price"] <= 0
    _add_flag(df, bad_price, "price_invalid_recovered")
    df.loc[bad_price, "Unit_Price"] = np.nan
    info["prices_not_positive_set_missing"] = int(bad_price.sum())
    return df, info


# =============================================================================
# 7. MISSING VALUES
# =============================================================================
def handle_missing_values(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Recovery order: (1) business rules that give the exact value,
    (2) the entity's own other records, (3) a neutral label or median as a
    last resort. Nothing is filled with zero.
    Returns the data and a per-column treatment log.
    """
    df = df.copy()
    log = []

    def record(col, before, method):
        after = int(df[col].isna().sum())
        log.append({"Column": col, "Missing_Before": before, "Missing_After": after,
                    "Recovered": before - after, "Method": method})

    # -- Customer profile: one person has one name/age/gender/city -------------
    for col in ["Customer_Name", "Customer_Age", "Gender", "City"]:
        before = int(df[col].isna().sum())
        modal = df.groupby("Customer_ID")[col].agg(_mode)
        filled = df[col].isna() & df["Customer_ID"].map(modal).notna()
        _add_flag(df, filled, f"{col.lower()}_restored_from_customer")
        # harmonise: every row gets the customer's modal value
        df[col] = df["Customer_ID"].map(modal).where(df["Customer_ID"].map(modal).notna(), df[col])
        record(col, before, "Customer's modal value from their other transactions")
    # Last resort for age: overall median (flagged)
    if df["Customer_Age"].isna().any():
        before = int(df["Customer_Age"].isna().sum())
        miss = df["Customer_Age"].isna()
        _add_flag(df, miss, "age_median_imputed")
        df.loc[miss, "Customer_Age"] = df["Customer_Age"].median()
        record("Customer_Age", before, "Median age (no other record for the customer)")
    # Gender / City cannot be guessed for a customer with no other record -> honest label
    for col in ["Gender", "City"]:
        if df[col].isna().any():
            before = int(df[col].isna().sum())
            miss = df[col].isna()
            _add_flag(df, miss, f"{col.lower()}_unknown")
            df.loc[miss, col] = "Unknown"
            record(col, before, "Labelled 'Unknown' (customer has no other record; State/Region kept)"
                   if col == "City" else "Labelled 'Unknown' (customer has no other record)")
    df["Customer_Age"] = df["Customer_Age"].round().astype("Int64")

    # -- Geography follows the city -------------------------------------------
    for col, parent in [("State", "City"), ("Region", "State")]:
        before = int(df[col].isna().sum())
        lookup = df.dropna(subset=[col]).groupby(parent)[col].agg(_mode)
        mismatch = df[col].notna() & df[parent].map(lookup).notna() & (df[col] != df[parent].map(lookup))
        _add_flag(df, mismatch, f"{col.lower()}_realigned_to_{parent.lower()}")
        df[col] = df[parent].map(lookup).fillna(df[col])
        record(col, before, f"Derived from {parent} (reference hierarchy)")

    # -- Payment method is an order-level attribute ------------------------------
    before = int(df["Payment_Method"].isna().sum())
    order_pay = df.groupby("Order_ID")["Payment_Method"].agg(_mode)
    from_order = df["Payment_Method"].isna() & df["Order_ID"].map(order_pay).notna()
    _add_flag(df, from_order, "payment_copied_from_order")
    df.loc[from_order, "Payment_Method"] = df.loc[from_order, "Order_ID"].map(order_pay)
    unknown = df["Payment_Method"].isna()
    _add_flag(df, unknown, "payment_unknown")
    df.loc[unknown, "Payment_Method"] = "Unknown"
    record("Payment_Method", before, "Copied from same order's other lines; else 'Unknown'")

    # -- Transaction amounts: exact identities first ----------------------------
    before = int(df["Sales"].isna().sum())
    miss = df["Sales"].isna() & df["Cost"].notna() & df["Profit"].notna()
    _add_flag(df, miss, "sales_recomputed")
    df.loc[miss, "Sales"] = (df.loc[miss, "Cost"] + df.loc[miss, "Profit"]).round(2)
    record("Sales", before, "Sales = Cost + Profit (exact accounting identity)")

    before = int(df["Quantity"].isna().sum())
    implied_q = df["Sales"] / (df["Unit_Price"] * (1 - df["Discount"]))
    ok = df["Quantity"].isna() & implied_q.notna() & ((implied_q - implied_q.round()).abs() < 0.02) & (implied_q.round() >= 1)
    df.loc[ok, "Quantity"] = implied_q[ok].round()
    record("Quantity", before, "Quantity = Sales / (Unit_Price x (1 - Discount)), accepted only if a whole number")

    before = int(df["Discount"].isna().sum())
    implied_d = 1 - df["Sales"] / (df["Quantity"] * df["Unit_Price"])
    ok = df["Discount"].isna() & implied_d.between(-0.005, 1)
    _add_flag(df, ok & ~df["DQ_Flags"].str.contains("discount_invalid"), "discount_back_calculated")
    df.loc[ok, "Discount"] = implied_d[ok].clip(lower=0).round(2)
    record("Discount", before, "Discount = 1 - Sales / (Quantity x Unit_Price)")

    before = int(df["Unit_Price"].isna().sum())
    implied_p = df["Sales"] / (df["Quantity"] * (1 - df["Discount"]))
    ok = df["Unit_Price"].isna() & implied_p.notna() & (implied_p > 0)
    df.loc[ok, "Unit_Price"] = implied_p[ok].round(0)
    record("Unit_Price", before, "Unit_Price = Sales / (Quantity x (1 - Discount))")

    # Rows still missing a transaction amount cannot be used -> removed (logged)
    essential = ["Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit"]
    unusable = df[essential].isna().any(axis=1)
    df = df.loc[~unusable].copy()
    df["Quantity"] = df["Quantity"].astype(int)
    log.append({"Column": "Transaction amounts", "Missing_Before": int(unusable.sum()), "Missing_After": 0,
                "Recovered": 0, "Method": f"Rows removed: {int(unusable.sum())} (amount could not be recovered)"})
    return df, pd.DataFrame(log)


# =============================================================================
# 8. BUSINESS RULES
# =============================================================================
def business_rule_check(df: pd.DataFrame) -> pd.DataFrame:
    """Return the gap for both formulas and pass/fail flags (no changes made)."""
    exp_sales = df["Quantity"] * df["Unit_Price"] * (1 - df["Discount"])
    out = pd.DataFrame(index=df.index)
    out["Revenue_Gap"] = (df["Sales"] - exp_sales).round(2)
    out["Profit_Gap"] = (df["Profit"] - (df["Sales"] - df["Cost"])).round(2)
    out["Revenue_Check_Pass"] = out["Revenue_Gap"].abs() <= config.CONSISTENCY_TOLERANCE_INR
    out["Profit_Check_Pass"] = out["Profit_Gap"].abs() <= config.CONSISTENCY_TOLERANCE_INR
    return out


def validate_business_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    1. Report rows breaking Sales = Qty x Price x (1 - Discount) or Profit = Sales - Cost.
    2. Diagnose which component is wrong. Sales is trusted when it agrees with
       Cost + Profit (an independent identity). If Qty x Price x (1-D) is ~10x
       or ~0.1x Sales, the unit price has a decimal-shift typo -> recompute price.
    3. Re-check and keep pass/fail flags on every row.
    """
    df = df.copy()
    chk = business_rule_check(df)
    info = {"revenue_failures_before": int((~chk["Revenue_Check_Pass"]).sum()),
            "profit_failures_before": int((~chk["Profit_Check_Pass"]).sum())}

    sales_trusted = chk["Profit_Check_Pass"]
    ratio = (df["Quantity"] * df["Unit_Price"] * (1 - df["Discount"])) / df["Sales"]
    price_shift = (~chk["Revenue_Check_Pass"]) & sales_trusted & (
        ratio.between(9.5, 10.5) | ratio.between(0.095, 0.105))
    _add_flag(df, price_shift, "price_decimal_shift_corrected")
    df.loc[price_shift, "Unit_Price"] = (
        df.loc[price_shift, "Sales"] / (df.loc[price_shift, "Quantity"] * (1 - df.loc[price_shift, "Discount"]))
    ).round(0)
    info["prices_corrected_decimal_shift"] = int(price_shift.sum())

    # Profit identity: Profit is recomputed only if it disagrees (none expected)
    bad_profit = ~chk["Profit_Check_Pass"]
    _add_flag(df, bad_profit, "profit_recomputed")
    df.loc[bad_profit, "Profit"] = (df.loc[bad_profit, "Sales"] - df.loc[bad_profit, "Cost"]).round(2)

    chk = business_rule_check(df)
    df["Revenue_Check_Pass"] = chk["Revenue_Check_Pass"]
    df["Profit_Check_Pass"] = chk["Profit_Check_Pass"]
    info["revenue_failures_after"] = int((~chk["Revenue_Check_Pass"]).sum())
    info["profit_failures_after"] = int((~chk["Profit_Check_Pass"]).sum())
    return df, info


# =============================================================================
# 9. OUTLIERS
# =============================================================================
def detect_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Flag (never delete) extreme values with three lenses:
      * IQR rule   : below Q1 - 1.5 IQR or above Q3 + 1.5 IQR
      * z-score    : |z| > 3 (sensitive to skew, reported for comparison)
      * business   : Quantity >= 10 (bulk), Profit < 0 (loss-making line)
    """
    df = df.copy()
    rows = []
    for col in ["Sales", "Profit", "Quantity", "Unit_Price"]:
        s = df[col].astype(float)
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_flag = (s < lo) | (s > hi)
        z = (s - s.mean()) / s.std()
        df[f"Outlier_IQR_{col}"] = iqr_flag
        rows.append({"Variable": col, "Q1": round(q1, 2), "Q3": round(q3, 2), "IQR": round(iqr, 2),
                     "Lower_Fence": round(lo, 2), "Upper_Fence": round(hi, 2),
                     "IQR_Outliers": int(iqr_flag.sum()), "IQR_Outlier_%": round(100 * iqr_flag.mean(), 2),
                     "Z>3_Outliers": int((z.abs() > 3).sum()), "Min": round(s.min(), 2),
                     "Max": round(s.max(), 2), "Skewness": round(s.skew(), 2),
                     "Note": OUTLIER_NOTES[col]})
    df["Is_Bulk_Order_Line"] = df["Quantity"] >= BULK_QTY_THRESHOLD
    df["Is_Loss_Making"] = df["Profit"] < 0
    summary = pd.DataFrame(rows)
    return df, summary


def explain_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Classify the flagged extremes into legitimate business cases vs. errors."""
    s_out = df["Outlier_IQR_Sales"]
    return pd.DataFrame([
        {"Group": "High-value lines (Sales above IQR fence)", "Rows": int(s_out.sum()),
         "Share_of_Gross_Sales_%": round(100 * df.loc[s_out, "Sales"].sum() / df["Sales"].sum(), 1),
         "Top_Categories": ", ".join(df.loc[s_out, "Category"].value_counts().head(3).index),
         "Interpretation": "Premium products (phones, laptops, TVs) - legitimate; they carry a large share of revenue"},
        {"Group": f"Bulk lines (Quantity >= {BULK_QTY_THRESHOLD})", "Rows": int(df["Is_Bulk_Order_Line"].sum()),
         "Share_of_Gross_Sales_%": round(100 * df.loc[df["Is_Bulk_Order_Line"], "Sales"].sum() / df["Sales"].sum(), 1),
         "Top_Categories": ", ".join(df.loc[df["Is_Bulk_Order_Line"], "Category"].value_counts().head(3).index),
         "Interpretation": "Formulas hold exactly, so not errors - likely gifting / institutional purchases; keep and flag"},
        {"Group": "Loss-making lines (Profit < 0)", "Rows": int(df["Is_Loss_Making"].sum()),
         "Share_of_Gross_Sales_%": round(100 * df.loc[df["Is_Loss_Making"], "Sales"].sum() / df["Sales"].sum(), 1),
         "Top_Categories": ", ".join(df.loc[df["Is_Loss_Making"], "Category"].value_counts().head(3).index),
         "Interpretation": "Deep discounts on thin-margin items - a business issue to study in EDA, not a data error"},
    ])


# =============================================================================
# 10. FEATURES
# =============================================================================
def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Transaction-level analytical features (no RFM scores)."""
    df = df.copy()
    d = df["Order_Date"]
    df["Order_Year"] = d.dt.year
    df["Order_Month"] = d.dt.month_name()
    df["Month_Number"] = d.dt.month
    df["Order_Quarter"] = "Q" + d.dt.quarter.astype(str)
    df["Year_Month"] = d.dt.strftime("%Y-%m")
    df["Order_Week"] = d.dt.isocalendar().week.astype(int)
    df["Order_Day"] = d.dt.day
    df["Day_of_Week"] = d.dt.day_name()
    df["Is_Weekend"] = d.dt.weekday >= 5

    df["Gross_Amount"] = (df["Quantity"] * df["Unit_Price"]).round(2)          # before discount
    df["Discount_Amount"] = (df["Gross_Amount"] - df["Sales"]).round(2)
    df["Is_Delivered"] = df["Order_Status"].eq("Delivered")
    # Documented revenue rule: only Delivered lines count as realised revenue/profit
    df["Revenue"] = np.where(df["Is_Delivered"], df["Sales"], 0.0)
    df["Net_Profit"] = np.where(df["Is_Delivered"], df["Profit"], 0.0)
    df["Profit_Margin"] = (df["Profit"] / df["Sales"]).round(4)                # line margin (all statuses)
    df["Discount_Band"] = pd.cut(df["Discount"], bins=[-0.001, 0, 0.10, 0.20, 0.30, 1.0],
                                 labels=["0%", "1-10%", "11-20%", "21-30%", "31-40%"]).astype(str)
    df["Age_Band"] = pd.cut(df["Customer_Age"].astype(float), bins=[17, 24, 34, 49, 120],
                            labels=["18-24", "25-34", "35-49", "50+"]).astype(str)
    df["Order_Line_Count"] = df.groupby("Order_ID")["Order_Line_ID"].transform("count")
    return df


def build_customer_features(df: pd.DataFrame, snapshot: str = config.END_DATE) -> pd.DataFrame:
    """
    Customer-level descriptive features over the FULL period (Delivered lines
    for money, all lines for activity). Not RFM scores. For ML in Step 8 these
    must be recomputed on the observation window only (see leakage table).
    """
    snap = pd.Timestamp(snapshot)
    deliv = df[df["Is_Delivered"]]
    all_orders = df.groupby("Customer_ID").agg(
        Customer_Name=("Customer_Name", "first"), Customer_Age=("Customer_Age", "first"),
        Gender=("Gender", "first"), City=("City", "first"), State=("State", "first"),
        Region=("Region", "first"), First_Purchase_Date=("Order_Date", "min"),
        Last_Purchase_Date=("Order_Date", "max"), Total_Orders_All_Status=("Order_ID", "nunique"),
        Total_Lines=("Order_Line_ID", "count"),
        Returned_Lines=("Order_Status", lambda s: (s == "Returned").sum()),
        Cancelled_Lines=("Order_Status", lambda s: (s == "Cancelled").sum()),
    )
    money = deliv.groupby("Customer_ID").agg(
        Total_Customer_Orders=("Order_ID", "nunique"), Total_Customer_Revenue=("Sales", "sum"),
        Total_Customer_Profit=("Profit", "sum"), Total_Units=("Quantity", "sum"),
        Avg_Discount=("Discount", "mean"),
        Categories_Bought=("Category", "nunique"),
    )
    cust = all_orders.join(money, how="left")
    fill0 = ["Total_Customer_Orders", "Total_Customer_Revenue", "Total_Customer_Profit", "Total_Units"]
    cust[fill0] = cust[fill0].fillna(0)  # a customer with no delivered line genuinely earned 0
    cust["Average_Order_Value"] = (cust["Total_Customer_Revenue"] / cust["Total_Customer_Orders"]
                                   .replace(0, np.nan)).round(2)
    tenure_days = (snap - cust["First_Purchase_Date"]).dt.days + 1
    cust["Tenure_Days"] = tenure_days
    # Purchase frequency = delivered orders per 30 days of observed tenure
    cust["Customer_Purchase_Frequency"] = (cust["Total_Customer_Orders"] / (tenure_days / 30)).round(3)
    cust["Days_Since_Last_Purchase"] = (snap - cust["Last_Purchase_Date"]).dt.days
    cust["Return_Rate"] = (cust["Returned_Lines"] / cust["Total_Lines"]).round(3)
    cust["Total_Customer_Revenue"] = cust["Total_Customer_Revenue"].round(2)
    cust["Total_Customer_Profit"] = cust["Total_Customer_Profit"].round(2)
    cust["Avg_Discount"] = cust["Avg_Discount"].round(3)
    return cust.reset_index()


def customer_validation(cust: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Headline customer statistics and a list of unusual customer records."""
    rev = cust["Total_Customer_Revenue"]
    q1, q3 = rev.quantile([0.25, 0.75])
    fence = q3 + 1.5 * (q3 - q1)
    stats = pd.DataFrame([
        ("Unique customers", len(cust)),
        ("Customers with >= 1 delivered order", int((cust["Total_Customer_Orders"] > 0).sum())),
        ("Median delivered orders per customer", float(cust["Total_Customer_Orders"].median())),
        ("Mean delivered orders per customer", round(cust["Total_Customer_Orders"].mean(), 2)),
        ("Max delivered orders per customer", int(cust["Total_Customer_Orders"].max())),
        ("Median revenue per customer (INR)", round(rev.median(), 2)),
        ("Mean revenue per customer (INR)", round(rev.mean(), 2)),
        ("Median customer AOV (INR)", round(cust["Average_Order_Value"].median(), 2)),
        ("Median purchase frequency (orders / 30 days)", round(cust["Customer_Purchase_Frequency"].median(), 3)),
        ("Single-order customers", int((cust["Total_Orders_All_Status"] == 1).sum())),
    ], columns=["Metric", "Value"])
    stats["Value"] = [f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}" if v > 1 else f"{v:.3f}"
                      for v in stats["Value"]]
    unusual = pd.concat([
        cust[rev > fence].assign(Reason=f"Revenue above IQR fence (INR {fence:,.0f})"),
        cust[cust["Total_Customer_Orders"] == 0].assign(Reason="No delivered order (all cancelled/returned)"),
        cust[cust["Return_Rate"] >= 0.5].assign(Reason="Return rate >= 50%"),
    ])[["Customer_ID", "Customer_Name", "Total_Customer_Orders", "Total_Customer_Revenue",
        "Return_Rate", "Reason"]]
    return stats, unusual.reset_index(drop=True)


# =============================================================================
# 11. LEAKAGE
# =============================================================================
def feature_usage_table() -> pd.DataFrame:
    """Preliminary guide to which columns may be used as predictors later."""
    rows = [
        ("Order_Line_ID", "Identifier", "No", "Unique key; carries no behaviour"),
        ("Order_ID", "Identifier", "No (aggregate only)", "Used to count orders, never as a raw input"),
        ("Customer_ID", "Identifier", "No (grouping key)", "Groups rows per customer; memorising IDs = leakage"),
        ("Product_ID / Product_Name", "Identifier", "Via aggregates", "Use category mix, not raw IDs"),
        ("Customer_Name", "Identifier (PII)", "No", "Personal identifier with no predictive meaning"),
        ("Order_Date", "Time index", "To build windows", "Defines observation vs. prediction windows"),
        ("Customer_Age, Gender, Region, State, City", "Customer attribute", "Yes", "Known before the prediction period"),
        ("Category, Sub_Category", "Transaction attribute", "Yes (observation window)", "As share of past spend"),
        ("Quantity, Unit_Price, Discount", "Transaction attribute", "Yes (observation window)", "Aggregated from past orders only"),
        ("Sales / Revenue", "TARGET-related", "Target only in prediction window",
         "Future-window revenue is the target; Sales = Qty x Price x (1-D) makes order-level prediction trivial (leakage)"),
        ("Cost, Profit, Profit_Margin", "Target-related", "No (for revenue model)", "Computed from Sales - reveals the target"),
        ("Order_Status", "Post-purchase outcome", "Past windows only", "Known only after delivery; future status unknown at prediction time"),
        ("Payment_Method", "Transaction attribute", "Yes (observation window)", "e.g. share of COD orders"),
        ("Customer_Type", "Derived from history", "With care", "Encodes whether a prior order exists; recompute inside the window"),
        ("Total_Customer_Revenue, Total_Customer_Orders, AOV, Purchase_Frequency, Days_Since_Last_Purchase",
         "Full-period customer aggregates", "No (as saved)", "Computed over ALL 36 months incl. the future window - must be recomputed on the observation window"),
        ("DQ_Flags, *_Check_Pass, Outlier_* flags", "Data-quality metadata", "No", "Describe the data process, not the customer"),
    ]
    return pd.DataFrame(rows, columns=["Column(s)", "Role", "Use as ML predictor?", "Reason"])


# =============================================================================
# 12. SUMMARY + SAVE
# =============================================================================
def dataset_profile(df: pd.DataFrame, cleaned: bool = False) -> dict:
    """Metrics measured identically before and after cleaning."""
    base = df[config.EXPECTED_COLUMNS]
    dates = base["Order_Date"]
    if not pd.api.types.is_datetime64_any_dtype(dates):
        dates, _ = _parse_dates(dates)
    viol = rule_violations(base, cleaned)
    numeric_ok = sum(pd.api.types.is_numeric_dtype(base[c]) for c in NUMERIC_COLS)
    return {
        "Rows": len(base),
        "Columns": df.shape[1],
        "Missing values (cells, original 23 columns)": int(base.isna().sum().sum()),
        "Duplicate rows (exact)": int(base.duplicated().sum()),
        "Records breaking >= 1 validation rule": int(viol.any(axis=1).sum()),
        "Numeric columns stored as numbers": f"{numeric_ok} of {len(NUMERIC_COLS)}",
        "Order_Date stored as datetime": "Yes" if pd.api.types.is_datetime64_any_dtype(base["Order_Date"]) else "No (text)",
        "Unique customers": int(base["Customer_ID"].nunique()),
        "Unique products": int(base["Product_ID"].nunique()),
        "Unique orders": int(base["Order_ID"].nunique()),
        "Distinct Category labels": int(base["Category"].nunique()),
        "Distinct City labels": int(base["City"].nunique()),
        "Date range": f"{dates.min().date()} to {dates.max().date()}",
    }


def before_after_table(before: dict, after: dict) -> pd.DataFrame:
    return pd.DataFrame({"Metric": list(before), "Before Cleaning": list(before.values()),
                         "After Cleaning": [after[k] for k in before]})


def plot_quality_charts(raw: pd.DataFrame, clean: pd.DataFrame, audit: pd.DataFrame,
                        clean_outliers: pd.DataFrame, out_dir: Path = config.DQ_FIGURES_DIR) -> list[Path]:
    """Four charts for the cleaning report (not business EDA)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c = config.CHART_COLORS
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": c["grid"],
                         "axes.labelcolor": c["muted"], "xtick.color": c["muted"],
                         "ytick.color": c["muted"], "axes.titleweight": "bold",
                         "axes.titlecolor": c["text"], "figure.facecolor": "white",
                         "axes.spines.top": False, "axes.spines.right": False})
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    raw_missing = raw[config.EXPECTED_COLUMNS].isna().sum()
    raw_missing = raw_missing[raw_missing > 0].sort_values()
    x_max = raw_missing.max() * 1.25

    def missing_chart(data: pd.DataFrame, title: str, fname: str):
        # Same columns and same x-scale in both charts, so they compare directly
        miss = data[raw_missing.index].isna().sum()
        fig, ax = plt.subplots(figsize=(8, 4.2))
        bars = ax.barh(miss.index, miss.values, color=c["primary"], height=0.6)
        for b, v in zip(bars, miss.values):
            ax.text(b.get_width() + x_max * 0.01, b.get_y() + b.get_height() / 2,
                    f"{v:,} ({100 * v / len(data):.1f}%)", va="center", fontsize=9, color=c["text"])
        ax.set_xlabel("Missing cells")
        ax.set_title(title, loc="left")
        ax.grid(axis="x", color=c["grid"], linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlim(0, x_max)
        if miss.max() == 0:
            unk = {col: int((data[col] == "Unknown").sum()) for col in ["Payment_Method", "Gender", "City"]}
            unk_txt = ", ".join(f"{col} {n}" for col, n in unk.items() if n)
            ax.text(0.5, 0.5, "All missing values resolved" +
                    (f"\nLabelled 'Unknown' (not recoverable): {unk_txt}" if unk_txt else ""),
                    transform=ax.transAxes, ha="center", va="center", fontsize=10.5, color=c["text"])
        fig.tight_layout()
        p = out_dir / fname
        fig.savefig(p, dpi=150)
        plt.close(fig)
        saved.append(p)

    missing_chart(raw, f"Missing values before cleaning ({len(raw):,} rows)", "01_missing_values_before.png")
    missing_chart(clean, f"Missing values after cleaning ({len(clean):,} rows)", "02_missing_values_after.png")

    # Outlier distribution: log-scale boxplots (values span 3 orders of magnitude)
    fig, axes = plt.subplots(1, 4, figsize=(12, 4))
    for ax, col in zip(axes, ["Sales", "Profit", "Quantity", "Unit_Price"]):
        vals = clean[col].astype(float)
        ax.boxplot(vals, vert=True, widths=0.5, patch_artist=True,
                   boxprops=dict(facecolor="#cde2fb", edgecolor=c["primary"]),
                   medianprops=dict(color=c["text"], linewidth=1.5),
                   whiskerprops=dict(color=c["muted"]), capprops=dict(color=c["muted"]),
                   flierprops=dict(marker="o", markersize=3, markerfacecolor=c["secondary"],
                                   markeredgecolor="none", alpha=0.5))
        if col != "Profit":
            ax.set_yscale("log")
        n_out = int(clean[f"Outlier_IQR_{col}"].sum())
        ax.set_title(f"{col}\n{n_out:,} IQR outliers ({100 * n_out / len(clean):.1f}%)", fontsize=10)
        ax.set_xticks([])
        ax.grid(axis="y", color=c["grid"], linewidth=0.8)
    axes[0].set_ylabel("Value (INR or units; log scale except Profit)")
    fig.suptitle("Outlier distribution after cleaning (flagged, not removed)", x=0.01, ha="left",
                 fontweight="bold", color=c["text"])
    fig.tight_layout()
    p = out_dir / "03_outlier_distribution.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # Issue summary: top issues by affected records (excluding informational rows)
    info_only = audit["Issue"].str.startswith("Order_ID repeated")
    top = audit.loc[~info_only].sort_values("Affected_Records").tail(15)
    labels = top["Issue"].str.slice(0, 48) + "  [" + top["Column"] + "]"
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, top["Affected_Records"], color=c["primary"], height=0.6)
    for b, v, pct in zip(bars, top["Affected_Records"], top["Percent_Affected"]):
        ax.text(b.get_width() + top["Affected_Records"].max() * 0.01, b.get_y() + b.get_height() / 2,
                f"{v:,} ({pct:.2f}%)", va="center", fontsize=8.5, color=c["text"])
    ax.set_xlabel("Affected records in raw file")
    ax.set_title("Data-quality issues found in the raw file (top 15)", loc="left")
    ax.grid(axis="x", color=c["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=8.5)
    fig.tight_layout()
    p = out_dir / "04_data_quality_issue_summary.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)
    return saved


FINAL_COLUMN_ORDER = config.EXPECTED_COLUMNS + [
    "Order_Year", "Order_Quarter", "Month_Number", "Order_Month", "Year_Month", "Order_Week",
    "Order_Day", "Day_of_Week", "Is_Weekend", "Gross_Amount", "Discount_Amount", "Is_Delivered",
    "Revenue", "Net_Profit", "Profit_Margin", "Discount_Band", "Age_Band", "Order_Line_Count",
    "Revenue_Check_Pass", "Profit_Check_Pass", "Outlier_IQR_Sales", "Outlier_IQR_Profit",
    "Outlier_IQR_Quantity", "Outlier_IQR_Unit_Price", "Is_Bulk_Order_Line", "Is_Loss_Making",
    "Potential_Duplicate_Flag", "DQ_Flags",
]


def save_clean_data(clean: pd.DataFrame, customers: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> list[Path]:
    """Write the cleaned data, customer features and all report tables."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = clean[FINAL_COLUMN_ORDER].copy()
    out["Order_Date"] = out["Order_Date"].dt.strftime("%Y-%m-%d")
    out.to_csv(config.CLEAN_DATA_FILE, index=False, encoding="utf-8-sig")
    cust = customers.copy()
    for c in ["First_Purchase_Date", "Last_Purchase_Date"]:
        cust[c] = cust[c].dt.strftime("%Y-%m-%d")
    cust.to_csv(config.CUSTOMER_FEATURES_FILE, index=False, encoding="utf-8-sig")
    paths = [config.CLEAN_DATA_FILE, config.CUSTOMER_FEATURES_FILE]
    for path, table in tables.items():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(path, index=False, encoding="utf-8-sig")
        paths.append(Path(path))
    return paths


# =============================================================================
# PIPELINE
# =============================================================================
def run_pipeline(verbose: bool = True, make_charts: bool = True) -> dict:
    """Run every step in order and return all intermediate results."""
    say = print if verbose else (lambda *a, **k: None)
    R: dict = {}
    raw = load_data()
    R["raw"] = raw
    R["raw_profile"] = describe_raw(raw)
    R["before"] = dataset_profile(raw)
    R["audit"] = audit_data(raw)
    R["invalid_before_by_rule"] = rule_violations(raw).sum().rename("Rows_Before")

    df, R["dup_info"] = remove_duplicates(raw)
    df, R["type_info"] = standardize_types(df)
    df, R["category_comparison"] = standardize_categories(df)
    df, R["numeric_info"] = validate_numeric_fields(df)
    df, R["missing_log"] = handle_missing_values(df)
    df, R["business_info"] = validate_business_rules(df)
    df["Potential_Duplicate_Flag"] = flag_potential_duplicates(df)
    df, R["outlier_summary"] = detect_outliers(df)
    R["outlier_explanation"] = explain_outliers(df)
    df = create_features(df)
    df = df.sort_values("Order_Line_ID").reset_index(drop=True)
    R["clean"] = df
    R["customers"] = build_customer_features(df)
    R["customer_stats"], R["unusual_customers"] = customer_validation(R["customers"])
    R["feature_usage"] = feature_usage_table()
    R["after"] = dataset_profile(df, cleaned=True)
    R["invalid_after_by_rule"] = rule_violations(df[config.EXPECTED_COLUMNS], cleaned=True) \
        .sum().rename("Rows_After")
    R["before_after"] = before_after_table(R["before"], R["after"])
    R["rule_before_after"] = pd.concat([R["invalid_before_by_rule"], R["invalid_after_by_rule"]], axis=1) \
        .rename_axis("Validation_Rule").reset_index()
    flags = df["DQ_Flags"].str.split(";").explode()
    R["correction_counts"] = flags[flags != ""].value_counts().rename_axis("Correction").reset_index(name="Rows")

    audit_with_result = R["audit"].copy()
    tables = {
        config.DATA_QUALITY_REPORT: audit_with_result,
        config.CLEANING_SUMMARY: R["before_after"].astype(str),
        config.TABLES_DIR / "cleaning_rule_checks_before_after.csv": R["rule_before_after"],
        config.TABLES_DIR / "cleaning_corrections_applied.csv": R["correction_counts"],
        config.TABLES_DIR / "cleaning_missing_value_log.csv": R["missing_log"],
        config.TABLES_DIR / "cleaning_category_standardisation.csv": R["category_comparison"],
        config.TABLES_DIR / "outlier_summary.csv": R["outlier_summary"],
        config.TABLES_DIR / "outlier_interpretation.csv": R["outlier_explanation"],
        config.TABLES_DIR / "customer_validation_stats.csv": R["customer_stats"].astype(str),
        config.TABLES_DIR / "unusual_customers.csv": R["unusual_customers"],
        config.TABLES_DIR / "feature_usage_leakage_check.csv": R["feature_usage"],
    }
    R["saved"] = save_clean_data(df, R["customers"], tables)
    if make_charts:
        R["charts"] = plot_quality_charts(raw, df, R["audit"], R["outlier_summary"])

    # ---------------------------------------------------------------- console
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_colwidth", 70)
    p = R["raw_profile"]
    say(f"*** {config.DATASET_LABEL} ***\n")
    say("=== 1. RAW DATA ===")
    say(f"Shape: {p['shape'][0]:,} rows x {p['shape'][1]} columns\n")
    say("First 10 rows:\n", p["head"].iloc[:, :12].to_string(), "\n")
    say("Last 10 rows:\n", p["tail"].iloc[:, :12].to_string(), "\n")
    say("Column roles and types as read:\n", p["roles"].to_string(index=False), "\n")
    say("Numeric statistics (as read):\n", p["numeric_stats"].to_string(), "\n")
    say("=== 2. DATA-QUALITY AUDIT ===")
    say(R["audit"].to_string(index=False), "\n")
    say("=== 3. DUPLICATES ===", R["dup_info"], "\n")
    say("=== 4. TYPES ===", R["type_info"], "\n")
    say("=== 5. CATEGORIES (unique values before -> after) ===")
    say(R["category_comparison"][["Column", "Unique_Before", "Unique_After"]].to_string(index=False), "\n")
    say("=== 6. NUMERIC VALIDATION ===", R["numeric_info"], "\n")
    say("=== 7. MISSING VALUES ===")
    say(R["missing_log"].to_string(index=False), "\n")
    say("=== 8. BUSINESS RULES ===", R["business_info"], "\n")
    say("=== 9. OUTLIERS (flagged, not removed) ===")
    say(R["outlier_summary"].to_string(index=False))
    say(R["outlier_explanation"].to_string(index=False), "\n")
    say("=== 10. CUSTOMER VALIDATION ===")
    say(R["customer_stats"].to_string(index=False))
    say(f"Unusual customer records flagged: {len(R['unusual_customers'])}\n")
    say("=== 13. BEFORE vs AFTER ===")
    say(R["before_after"].to_string(index=False), "\n")
    say("Validation rules (rows breaking each rule):")
    say(R["rule_before_after"].to_string(index=False), "\n")
    say("Saved files:")
    for path in R["saved"] + R.get("charts", []):
        say("  ", Path(path).relative_to(config.PROJECT_ROOT))
    return R


if __name__ == "__main__":
    run_pipeline()
