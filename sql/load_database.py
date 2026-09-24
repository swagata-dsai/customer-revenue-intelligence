#!/usr/bin/env python3
"""
load_database.py
================
Reproducible SQL workflow entry point (Step 10).

    1. create the SQLite database          data/customer_revenue_intelligence.db
    2. create tables                        sql/schema.sql (PK, FK, CHECK constraints, views)
    3. load the cleaned transactions        data/processed/customer_sales_cleaned.csv
    4. load RFM / ML segments / CLV / forecasts from Steps 5-9
    5. validate row counts, totals, keys, nulls, relationships and cross-step consistency
    6. save the database and the validation table (outputs/tables/sql_validation_checks.csv)

Usage (from the project root):
    python sql/load_database.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.database import build_database, table_catalog, validate_database  # noqa: E402


def main() -> int:
    res = build_database()
    checks = validate_database(source=res["source"])
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    checks.to_csv(config.TABLES_DIR / "sql_validation_checks.csv", index=False, encoding="utf-8-sig")
    table_catalog().to_csv(config.TABLES_DIR / "sql_table_catalog.csv", index=False, encoding="utf-8-sig")
    print(f"*** {config.DATASET_LABEL} ***")
    print(f"Database created: {res['db_path'].relative_to(config.PROJECT_ROOT)}")
    print(table_catalog()[["Table", "Layer", "Rows", "Primary_Key", "Foreign_Keys"]].to_string(index=False))
    print(f"\nValidation: {int(checks['Pass'].sum())}/{len(checks)} checks passed")
    if not checks["Pass"].all():
        print(checks[~checks["Pass"]].to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
