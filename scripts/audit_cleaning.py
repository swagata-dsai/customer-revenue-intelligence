#!/usr/bin/env python3
"""
audit_cleaning.py
=================
Independent accuracy check of Step 3 - possible only because the data are
SYNTHETIC: the generator can rebuild the error-free data (before errors were
injected), so we can measure how many cleaned values match the truth.

The cleaning pipeline itself never sees this ground truth.

Run from the project root (after src/data_cleaning.py):
    python scripts/audit_cleaning.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import config  # noqa: E402
import generate_dataset as gen  # noqa: E402

TOLERANCE = {"Unit_Price": 1.0, "Discount": 0.005, "Sales": 0.01, "Cost": 0.01,
             "Profit": 0.01, "Quantity": 0, "Customer_Age": 0}


def main() -> None:
    g = gen.SyntheticSalesGenerator(seed=config.RANDOM_SEED)
    truth = g.build_transactions(g.build_customers()).set_index("Order_Line_ID")
    clean = pd.read_csv(config.CLEAN_DATA_FILE, encoding="utf-8-sig").set_index("Order_Line_ID")

    rows = [{"Check": "Order lines in truth", "Result": len(truth)},
            {"Check": "Order lines after cleaning", "Result": len(clean)},
            {"Check": "Lines missing from cleaned data", "Result": len(truth.index.difference(clean.index))},
            {"Check": "Unexpected extra lines", "Result": len(clean.index.difference(truth.index))}]
    clean = clean.loc[truth.index.intersection(clean.index)]
    truth = truth.loc[clean.index]
    detail = []
    for col in config.EXPECTED_COLUMNS[1:]:
        if col in TOLERANCE:
            ok = (pd.to_numeric(clean[col], errors="coerce") - truth[col].astype(float)).abs() <= TOLERANCE[col]
        else:
            ok = clean[col].astype(str) == truth[col].astype(str)
        mism = clean.loc[~ok, col].astype(str) + " (true: " + truth.loc[~ok, col].astype(str) + ")"
        detail.append({"Column": col, "Matching_Values": int(ok.sum()), "Mismatches": int((~ok).sum()),
                       "Accuracy_%": round(100 * ok.mean(), 3),
                       "Mismatch_Examples": "; ".join(mism.head(3))})
    detail = pd.DataFrame(detail)
    out = config.TABLES_DIR / "cleaning_accuracy_vs_ground_truth.csv"
    detail.to_csv(out, index=False, encoding="utf-8-sig")
    total = detail["Matching_Values"].sum() / (detail["Matching_Values"] + detail["Mismatches"]).sum()
    rows.append({"Check": "Cell-level accuracy (22 columns)", "Result": f"{100 * total:.3f}%"})
    print(pd.DataFrame(rows).to_string(index=False), "\n")
    print(detail.to_string(index=False))
    print(f"\nSaved: {out.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
