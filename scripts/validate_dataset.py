#!/usr/bin/env python3
"""
validate_dataset.py
===================
Audits the RAW synthetic dataset BEFORE cleaning. It does not change the data;
it measures how far the raw file is from the business rules, so Step 3
(cleaning) has a documented starting point.

Checks
------
 1. Row / column counts and expected columns
 2. Unique customers, products, orders and order lines
 3. Date range and unparseable / non-standard dates
 4. Missing values per column
 5. Duplicate rows and duplicate primary keys
 6. Non-numeric values in numeric columns
 7. Negative values
 8. Invalid discounts (outside 0-1 or above the 40% policy cap)
 9. Revenue consistency:  Sales  = Quantity x Unit_Price x (1 - Discount)
10. Profit consistency:   Profit = Sales - Cost
11. Categorical domain checks (values outside the allowed list)
12. Referential consistency: City -> State -> Region, one profile per customer
13. Out-of-range ages

Each check is PASS (rule fully met), WARN (issues found - expected in raw data)
or FAIL (the file is unusable, e.g. columns missing).

Run from the project root:
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --file path/to/other.csv
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

NUMERIC_COLS = ["Customer_Age", "Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit"]


@dataclass
class CheckResult:
    name: str
    status: str          # PASS / WARN / FAIL
    summary: str
    details: list[str] = field(default_factory=list)


class RawDataValidator:
    """Runs every check and collects results for the console and the report."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.results: list[CheckResult] = []
        # Numeric view: text such as '₹1,299' becomes NaN here, so it can be counted.
        self.num = df.reindex(columns=NUMERIC_COLS).apply(pd.to_numeric, errors="coerce")

    def add(self, name, ok, summary, details=None, fail=False):
        status = "PASS" if ok else ("FAIL" if fail else "WARN")
        self.results.append(CheckResult(name, status, summary, details or []))

    # ------------------------------------------------------------------ checks
    def check_structure(self):
        df = self.df
        missing = [c for c in config.EXPECTED_COLUMNS if c not in df.columns]
        extra = [c for c in df.columns if c not in config.EXPECTED_COLUMNS]
        details = [f"Missing columns: {missing}"] if missing else []
        details += [f"Unexpected columns: {extra}"] if extra else []
        self.add("1. Rows and columns", not missing and not extra,
                 f"{len(df):,} rows x {df.shape[1]} columns "
                 f"(expected {len(config.EXPECTED_COLUMNS)} columns)", details, fail=bool(missing))
        return not missing

    def check_cardinality(self):
        df = self.df
        self.add("2. Unique entities", True,
                 f"customers={df['Customer_ID'].nunique():,} | products={df['Product_ID'].nunique():,} | "
                 f"orders={df['Order_ID'].nunique():,} | order lines={df['Order_Line_ID'].nunique():,}")

    def check_dates(self):
        s = self.df["Order_Date"].astype("string")
        iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
        dmy_dash = pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
        dmy_slash = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
        parsed = iso.fillna(dmy_dash).fillna(dmy_slash)
        n_non_iso = int(iso.isna().sum() - s.isna().sum())
        n_unparsed = int(parsed.isna().sum() - s.isna().sum())
        details = [f"Non-ISO (DD-MM-YYYY): {int(dmy_dash.notna().sum())}",
                   f"Non-ISO (DD/MM/YYYY): {int(dmy_slash.notna().sum())}",
                   f"Unparseable in any known format: {n_unparsed}"]
        self.add("3. Date range and format", n_non_iso == 0,
                 f"{parsed.min().date()} to {parsed.max().date()} "
                 f"({parsed.dt.to_period('M').nunique()} months); {n_non_iso} non-ISO dates", details)

    def check_missing(self):
        miss = self.df.isna().sum()
        miss = miss[miss > 0]
        details = [f"{c}: {n} ({n / len(self.df):.2%})" for c, n in miss.items()]
        self.add("4. Missing values", miss.empty,
                 f"{int(miss.sum())} missing cells in {len(miss)} columns", details)

    def check_duplicates(self):
        full = int(self.df.duplicated().sum())
        pk = int(self.df["Order_Line_ID"].duplicated().sum())
        self.add("5. Duplicates", full == 0 and pk == 0,
                 f"{full} fully duplicated rows; {pk} repeated Order_Line_ID values")

    def check_numeric_types(self):
        details = []
        for c in NUMERIC_COLS:
            bad = int((self.df[c].notna() & self.num[c].isna()).sum())
            if bad:
                examples = self.df.loc[self.df[c].notna() & self.num[c].isna(), c].head(3).tolist()
                details.append(f"{c}: {bad} non-numeric values, e.g. {examples}")
        self.add("6. Numeric columns contain numbers", not details,
                 f"{len(details)} numeric column(s) contain text", details)

    def check_negatives(self):
        details = []
        for c in ["Quantity", "Unit_Price", "Sales", "Cost"]:
            n = int((self.num[c] < 0).sum())
            if n:
                details.append(f"{c}: {n} negative values")
        n_zero_qty = int((self.num["Quantity"] == 0).sum())
        if n_zero_qty:
            details.append(f"Quantity: {n_zero_qty} zero values")
        loss_rows = int((self.num["Profit"] < 0).sum())
        self.add("7. Negative values", not details,
                 f"{len(details)} rule violation(s). Note: {loss_rows} rows have negative Profit "
                 "- this is a legitimate business outcome (loss-making sale), not an error.", details)

    def check_discounts(self):
        d = self.num["Discount"]
        outside = int(((d < 0) | (d > 1)).sum())
        above_cap = int(((d > config.MAX_DISCOUNT) & (d <= 1)).sum())
        details = [f"Outside 0-1: {outside} (e.g. {d[(d > 1)].head(3).tolist()})",
                   f"Between {config.MAX_DISCOUNT:.0%} cap and 100%: {above_cap}"]
        self.add("8. Invalid discounts", outside == 0 and above_cap == 0,
                 f"{outside + above_cap} invalid discount values", details)

    def check_revenue(self):
        n = self.num
        expected = n["Quantity"] * n["Unit_Price"] * (1 - n["Discount"])
        testable = expected.notna() & n["Sales"].notna()
        gap = (n["Sales"] - expected).abs()
        bad = testable & (gap > config.CONSISTENCY_TOLERANCE_INR)
        self.add("9. Revenue consistency", int(bad.sum()) == 0,
                 f"{int(bad.sum())} of {int(testable.sum()):,} testable rows break "
                 f"Sales = Qty x Price x (1 - Discount) by more than INR {config.CONSISTENCY_TOLERANCE_INR:.0f}",
                 [f"Not testable (a component missing or non-numeric): {int((~testable).sum())} rows"])

    def check_profit(self):
        n = self.num
        testable = n[["Sales", "Cost", "Profit"]].notna().all(axis=1)
        bad = testable & ((n["Profit"] - (n["Sales"] - n["Cost"])).abs() > config.CONSISTENCY_TOLERANCE_INR)
        self.add("10. Profit consistency", int(bad.sum()) == 0,
                 f"{int(bad.sum())} of {int(testable.sum()):,} testable rows break Profit = Sales - Cost",
                 [f"Not testable: {int((~testable).sum())} rows"])

    def check_domains(self):
        domains = {"Category": config.VALID_CATEGORIES, "Region": config.VALID_REGIONS,
                   "Gender": config.VALID_GENDERS, "Payment_Method": config.VALID_PAYMENT_METHODS,
                   "Order_Status": config.VALID_ORDER_STATUS, "Customer_Type": config.VALID_CUSTOMER_TYPES}
        details = []
        for col, allowed in domains.items():
            vals = self.df[col].dropna()
            bad = vals[~vals.isin(allowed)]
            if len(bad):
                details.append(f"{col}: {len(bad)} non-standard values -> "
                               f"{sorted(map(repr, bad.unique()))[:8]}")
        self.add("11. Categorical values", not details,
                 f"{len(details)} column(s) contain values outside the allowed list", details)

    def check_referential(self):
        df = self.df
        city_states = df.dropna(subset=["City"]).groupby("City")["State"].nunique()
        state_regions = df.groupby("State")["Region"].nunique()
        profile = df.groupby("Customer_ID")[["Customer_Name", "Customer_Age", "Gender", "City"]].nunique()
        inconsistent_customers = int((profile > 1).any(axis=1).sum())
        details = [f"Cities mapped to >1 state: {int((city_states > 1).sum())}",
                   f"States mapped to >1 region spelling: {int((state_regions > 1).sum())}",
                   f"Distinct City spellings: {df['City'].nunique()} | State spellings: {df['State'].nunique()}",
                   f"Customers whose name/age/gender/city differs across rows: {inconsistent_customers}"]
        ok = (city_states <= 1).all() and (state_regions <= 1).all() and inconsistent_customers == 0
        self.add("12. Referential consistency", bool(ok),
                 "Geography hierarchy and one-profile-per-customer rule", details)

    def check_age(self):
        age = self.num["Customer_Age"]
        lo, hi = config.VALID_AGE_RANGE
        bad = age[(age < lo) | (age > hi)]
        self.add("13. Age range", bad.empty,
                 f"{len(bad)} ages outside {lo}-{hi}",
                 [f"Values found: {sorted(bad.unique().tolist())}"] if len(bad) else [])

    # -------------------------------------------------------------------- run
    def run(self) -> list[CheckResult]:
        if not self.check_structure():
            return self.results  # nothing else is meaningful without the columns
        for check in (self.check_cardinality, self.check_dates, self.check_missing,
                      self.check_duplicates, self.check_numeric_types, self.check_negatives,
                      self.check_discounts, self.check_revenue, self.check_profit,
                      self.check_domains, self.check_referential, self.check_age):
            try:
                check()
            except Exception as exc:  # one broken check must not hide the others
                self.add(check.__name__, False, f"Check could not run: {exc}", fail=True)
        return self.results


def to_markdown(results: list[CheckResult], path: Path, source: Path) -> str:
    lines = ["# Raw Data Validation Report", "",
             f"*{config.DATASET_LABEL}*", "",
             f"Source file: `{source.name}`  ",
             f"Generated by `scripts/validate_dataset.py` (seed {config.RANDOM_SEED})", "",
             "| # | Check | Status | Result |", "|---|---|---|---|"]
    for r in results:
        num, _, title = r.name.partition(". ")
        lines.append(f"| {num} | {title} | **{r.status}** | {r.summary} |")
    lines += ["", "## Details", ""]
    for r in results:
        if r.details:
            lines.append(f"**{r.name}**")
            lines += [f"- {d}" for d in r.details]
            lines.append("")
    counts = pd.Series([r.status for r in results]).value_counts()
    lines += ["## Summary", "",
              f"PASS: {counts.get('PASS', 0)} | WARN: {counts.get('WARN', 0)} | FAIL: {counts.get('FAIL', 0)}", "",
              "WARN results are expected at this stage: the raw file deliberately contains the "
              "issues listed in `data/raw/data_quality_injection_log.json`. They are fixed in Step 3."]
    text = "\n".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the raw sales dataset.")
    parser.add_argument("--file", type=Path, default=config.RAW_DATA_FILE)
    args = parser.parse_args()
    if not args.file.exists():
        sys.exit(f"File not found: {args.file}. Run scripts/generate_dataset.py first.")

    df = pd.read_csv(args.file, encoding="utf-8-sig", dtype={"Order_Date": "string"})
    results = RawDataValidator(df).run()

    print(f"*** {config.DATASET_LABEL} ***\n")
    for r in results:
        print(f"[{r.status:4}] {r.name}: {r.summary}")
        for d in r.details:
            print(f"         - {d}")
    to_markdown(results, config.RAW_VALIDATION_REPORT, args.file)
    print(f"\nReport saved: {config.RAW_VALIDATION_REPORT.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
