"""
config.py — Central configuration for the Customer Revenue Intelligence project.

Every script imports paths and constants from here, so nothing is hard-coded
in more than one place. Change the seed or date range here, and the whole
pipeline follows.
"""
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DATA_FILE = RAW_DIR / "customer_sales_raw.csv"
INJECTION_LOG_FILE = RAW_DIR / "data_quality_injection_log.json"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
RAW_VALIDATION_REPORT = REPORTS_DIR / "raw_data_validation_report.md"

SQL_DIR = PROJECT_ROOT / "sql"

# Step 3 outputs
CLEAN_DATA_FILE = PROCESSED_DIR / "customer_sales_cleaned.csv"
CUSTOMER_FEATURES_FILE = PROCESSED_DIR / "customer_level_features.csv"
DATABASE_FILE = DATA_DIR / "customer_revenue_intelligence.db"   # Step 10 (was processed/revenue_intelligence.db)
DATA_QUALITY_REPORT = OUTPUTS_DIR / "data_quality_report.csv"
CLEANING_SUMMARY = OUTPUTS_DIR / "cleaning_summary.csv"
TABLES_DIR = OUTPUTS_DIR / "tables"
FIGURES_DIR = OUTPUTS_DIR / "figures"
DQ_FIGURES_DIR = FIGURES_DIR / "data_quality"

# Chart palette (validated categorical order, light mode)
CHART_COLORS = {
    "primary": "#2a78d6", "secondary": "#eb6834", "tertiary": "#1baf7a",
    "text": "#0b0b0b", "muted": "#52514e", "grid": "#e4e3df", "surface": "#fcfcfb",
}

# ----------------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------------
RANDOM_SEED = 42

# ----------------------------------------------------------------------------
# Dataset scope (SYNTHETIC DATA)
# ----------------------------------------------------------------------------
DATASET_LABEL = "SYNTHETIC DATA - generated for academic demonstration only"
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"          # also the analysis "snapshot" date for Recency
N_CUSTOMERS = 2000
CURRENCY = "INR"

# ----------------------------------------------------------------------------
# Business rules shared by generation, validation and later cleaning
# ----------------------------------------------------------------------------
MAX_DISCOUNT = 0.40              # company policy cap on discount
VALID_AGE_RANGE = (18, 100)      # plausible customer age
CONSISTENCY_TOLERANCE_INR = 1.0  # allowed rounding gap in Sales / Profit checks

EXPECTED_COLUMNS = [
    "Order_Line_ID", "Order_ID", "Order_Date",
    "Customer_ID", "Customer_Name", "Customer_Age", "Gender",
    "City", "State", "Region",
    "Product_ID", "Product_Name", "Category", "Sub_Category",
    "Quantity", "Unit_Price", "Discount", "Sales", "Cost", "Profit",
    "Payment_Method", "Order_Status", "Customer_Type",
]

VALID_CATEGORIES = ["Electronics", "Fashion", "Home & Kitchen",
                    "Beauty", "Sports", "Books"]
VALID_REGIONS = ["North", "South", "East", "West", "Central"]
VALID_GENDERS = ["Male", "Female", "Other"]
VALID_PAYMENT_METHODS = ["UPI", "Card", "COD", "Net Banking", "Wallet"]
VALID_ORDER_STATUS = ["Delivered", "Cancelled", "Returned"]
VALID_CUSTOMER_TYPES = ["New", "Returning"]
