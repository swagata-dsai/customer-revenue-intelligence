# Step 3: Data Cleaning, Validation & Feature Engineering

**Project:** Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth

> **SYNTHETIC DATA.** The input is the Step 2 dataset (seed 42). Every number in this document was produced by `src/data_cleaning.py`, `src/database.py` and `scripts/audit_cleaning.py`. Re-running them reproduces the same numbers.

This document is written so its sections can go straight into **Chapter 3 (Design Flow / Process)** and **Chapter 4 (Results Analysis and Validation)** of the internship report.

---

## 1. Data Quality Assessment

The raw extract (`data/raw/customer_sales_raw.csv`, **18,819 rows × 23 columns**) was audited before any change was made. All columns were read as text, so that no automatic type conversion could hide a problem.

**Main issues found** (all counts measured; full table in `outputs/data_quality_report.csv`):

| Issue | Column | Affected records | % of rows | Treatment |
|---|---|---|---|---|
| Non-ISO date format | Order_Date | 566 | 3.01% | Each format parsed explicitly (day-first) |
| Customer profile differs across rows | Customer_ID | 319 customers | 1.70% | Harmonised to the customer's modal value |
| Missing value | Customer_Age | 285 | 1.51% | Restored from the customer's other rows |
| Non-standard category label | Category | 280 | 1.49% | Trimmed, case fixed, mapped to 6 standard values |
| Missing value | Payment_Method | 189 | 1.00% | Copied from the same order; otherwise `Unknown` |
| Non-standard label | Gender | 189 | 1.00% | Mapped to Male / Female / Other |
| Missing value | Gender | 188 | 1.00% | Restored from the customer's other rows |
| Non-standard label | Payment_Method | 187 | 0.99% | Mapped to the 5 standard methods |
| Non-standard label | Region | 151 | 0.80% | Trimmed, case fixed |
| Exact duplicate row | All columns | 149 | 0.79% | **Removed** |
| Missing value | City | 149 | 0.79% | Restored from the customer's other rows |
| Former / informal city name | City | 94 | 0.50% | Mapped to official name (e.g. Bombay → Mumbai) |
| Missing value | Discount | 93 | 0.49% | Back-calculated from the revenue formula |
| Price stored as text (`₹1,299`) | Unit_Price | 93 | 0.49% | Symbol and commas stripped, converted to number |
| Inconsistent name casing / spacing | Customer_Name | 93 | 0.49% | Trimmed and title-cased |
| Former / informal state name | State | 75 | 0.40% | Mapped to official name (e.g. Orissa → Odisha) |
| Missing value | Sales | 56 | 0.30% | Recomputed as Cost + Profit |
| Sales ≠ Qty × Price × (1 − Discount) | Sales | 56 | 0.30% | Faulty component identified and corrected |
| Discount stored as a percentage (> 1) | Discount | 38 | 0.20% | Divided by 100 |
| Impossible age (0, 5, 150, 999) | Customer_Age | 19 | 0.10% | Treated as missing, then restored |
| Negative quantity | Quantity | 9 | 0.05% | True quantity recovered from Sales |

**Checks that found no problems:**

- unparseable dates
- negative or zero unit prices
- negative sales or cost
- Profit ≠ Sales − Cost
- invalid order statuses
- Customer_Type labels
- duplicate line IDs with different content

**Order_ID repetition is not an error.** 9,633 rows (51%) share an `Order_ID` with another row, because one order can contain several products.

**Overall:** 2,359 of 18,819 raw rows (12.5%) broke at least one validation rule.

---

## 2. Cleaning Techniques

The pipeline is modular: one function per step in `src/data_cleaning.py`. It follows three principles:

1. **Business rules before statistics.** A value is recovered from an exact identity or from the same entity's own records before any average is used. Nothing is filled with zero.
2. **Nothing changes silently.** Every correction appends a code to the row's `DQ_Flags` column. In total, 2,569 rows carry at least one correction code.
3. **Delete only genuine duplicates.** The only rows removed were the 149 exact duplicates.

| Step | Technique | Result (actual) |
|---|---|---|
| Duplicates | Exact duplicates removed. Repeated Order_IDs (multi-product orders) and repeated Customer_IDs (repeat buyers) kept. Same order + product + quantity + price on two lines flagged only. | 18,819 → **18,670 rows**; 2 lines flagged as potential duplicates |
| Types | Explicit multi-format date parsing; `₹` and commas stripped from numbers; IDs trimmed | 560 dates reformatted; 93 prices converted |
| Categories | Trim, case-fix, variant mapping, official place names | Category 24 → 6 labels; Region 20 → 5; Gender 11 → 3 (+1 `Unknown`); Payment 15 → 5 (+ `Unknown`); City 41 → 34 (+1 `Unknown`); State 26 → 21 |
| Numeric validation | Age 18–100; discount 0–0.40; quantity and price > 0 | 19 ages, 37 percent-style discounts and 9 quantities corrected |
| Missing values | Customer mode (profile fields), order mode (payment), accounting identities (Sales = Cost + Profit), formula rearrangement (discount, quantity) | All 960 missing cells resolved |
| Unrecoverable values | Honest label instead of a guess | Payment_Method `Unknown` for 89 rows; Gender and City `Unknown` for 1 customer; median age imputed for 1 customer |
| Business rules | Report first, then diagnose the faulty component | 9 unit prices with a ×10 decimal-shift typo corrected |

**Differences between duplicates:**

- **Row-level duplicate:** an identical record loaded twice. It inflates revenue, so it is removed.
- **Order-level repetition:** one checkout containing several products. It is legitimate and kept.
- **Customer-level repetition:** one person buying many times. This is the behaviour that RFM and CLV measure, so it is kept.

---

## 3. Validation Techniques

| Technique | What it checks | Result after cleaning |
|---|---|---|
| **Domain validation** | Every categorical value is in its allowed list | 0 violations |
| **Range validation** | Age 18–100, discount 0–0.40, quantity and price > 0 | 0 violations |
| **Formula validation** | \|Sales − Qty × Price × (1 − D)\| ≤ ₹1 and \|Profit − (Sales − Cost)\| ≤ ₹1 | 0 failures (`Revenue_Check_Pass`, `Profit_Check_Pass` on every row) |
| **Referential validation** | City → one State → one Region; one profile per customer; one customer, date and payment method per order | 0 conflicts |
| **Database constraints** | The data were loaded into SQLite through `sql/schema.sql`, whose CHECK and FOREIGN KEY constraints reject any rule-breaking row | Loaded without error: 35 locations, 2,000 customers, 61 products, 13,251 orders, 18,670 order items; 0 FK violations. The view reconciles to the CSV (18,670 rows; ₹66,312,002.35 total Sales across all statuses). |
| **Ground-truth accuracy audit** | Possible only because the data are synthetic: cleaned values are compared with the generator's error-free data, which the cleaning code never sees | **99.959% cell-level accuracy** across 22 columns (see below) |

**Accuracy audit detail** (`outputs/tables/cleaning_accuracy_vs_ground_truth.csv`):

- 18 of 22 columns match the error-free values exactly (100%).
- **Quantity, Sales, Cost, Profit (19 mismatches each).** These are the 19 bulk-order lines. They are internally consistent, so the cleaning correctly **kept them as genuine extremes**. The generator had inflated them on purpose as realistic outliers, which is why they differ from its error-free values.
- **Payment_Method (89 mismatches).** These rows are labelled `Unknown`, because no information to recover them existed in the data.
- **Customer_Age, Gender, City (1 each).** This is one customer whose only row had these fields blank.

---

## 4. Outlier Treatment

Outliers were **flagged, never removed**. Three lenses were used:

| Variable | IQR outliers | z > 3 | Interpretation |
|---|---|---|---|
| Sales | 1,960 (10.5%) | 368 | Right-skewed (skewness 8.07). Lines above the IQR fence are premium products and make up **52.7% of gross sales**, so removing them would erase half the business. |
| Profit | 1,400 (7.5%) | 239 | Both tails. 271 loss-making lines, mostly Electronics, are a **business issue** (discounting on thin margins), not a data error. |
| Quantity | 4,578 (24.5%) | 19 | The IQR rule breaks down here (Q1 = Q3 = 1, so every multi-unit line counts as "outside"). The business threshold (≥ 10 units) is used instead: 19 bulk lines, all formula-consistent, so they are kept as likely gifting or institutional orders. |
| Unit_Price | 1,936 (10.4%) | 349 | Follows the price list (₹291 – ₹98,119). The extremes are laptops and TVs. |

Flag columns saved for later analysis:

- `Outlier_IQR_Sales`, `Outlier_IQR_Profit`, `Outlier_IQR_Quantity`, `Outlier_IQR_Unit_Price`
- `Is_Bulk_Order_Line`
- `Is_Loss_Making`

**Why extreme customers and transactions matter:** in a Pareto-type business, the top few customers and premium orders often generate a large share of revenue. They are the people a retention strategy most needs to protect, so they should be studied, not deleted.

---

## 5. Customer-Level Validation

Figures come from `data/processed/customer_level_features.csv`. Revenue counts Delivered lines only.

| Metric | Value |
|---|---|
| Unique customers | 2,000 |
| Customers with ≥ 1 delivered order | 1,984 |
| Delivered orders per customer: median / mean / max | 4 / 6.11 / 29 |
| Revenue per customer: median / mean | ₹13,335.95 / ₹30,028.28 |
| Median customer AOV | ₹3,093.35 |
| Median purchase frequency | 0.232 orders per 30 days |
| Single-order customers | 173 |

**Unusual customer records flagged** (`outputs/tables/unusual_customers.csv`):

- 184 with revenue above the IQR fence
- 41 with a return rate of 50% or more
- 16 with no delivered order at all

The mean being more than twice the median already points to revenue concentration, which Step 4 will quantify.

---

## 6. Feature Engineering

**Transaction level:** 28 columns are added to the 23 source columns, for **51 columns** in total.

- **Date features:** `Order_Year`, `Order_Quarter`, `Month_Number`, `Order_Month`, `Year_Month`, `Order_Week` (ISO), `Order_Day`, `Day_of_Week`, `Is_Weekend`
- **Money features:**
  - `Gross_Amount` = Qty × Price
  - `Discount_Amount`
  - `Revenue` and `Net_Profit`: Delivered lines only; 0 for Cancelled and Returned lines
  - `Profit_Margin` = Profit ÷ Sales
- **Bands:** `Discount_Band` (0%, 1–10%, 11–20%, 21–30%, 31–40%) and `Age_Band` (18–24, 25–34, 35–49, 50+)
- **Structure:** `Order_Line_Count`
- **Quality metadata:** check flags, outlier flags and `DQ_Flags`

**Customer level** (`customer_level_features.csv`):

- `Total_Customer_Revenue`, `Total_Customer_Orders`, `Average_Order_Value`
- `Customer_Purchase_Frequency`: delivered orders per 30 days of tenure
- First and last purchase dates, `Tenure_Days`, `Days_Since_Last_Purchase`
- `Return_Rate`, `Avg_Discount`, `Categories_Bought`

**RFM scores are deliberately not created here.** They come in Step 5.

**Order-status rule, applied from Step 4 onward:**

- Realised revenue and profit count **Delivered lines only**: 16,860 lines.
- Cancelled lines (709) and Returned lines (1,101) are kept in the data for return and cancellation analysis.

---

## 7. Data-Leakage Check (preliminary)

The full table is in `outputs/tables/feature_usage_leakage_check.csv`. The key rules:

- **Identifiers are never predictors:** Order_Line_ID, Order_ID, Customer_ID, Customer_Name.
- **Target-related columns are excluded from revenue models:**
  - Sales, Revenue, Cost, Profit, Profit_Margin.
  - Predicting order-level Sales from Quantity, Unit_Price and Discount would be trivial, because Sales is calculated from them.
- **Information available only after the prediction period** must not be used:
  - future Order_Status;
  - any full-period customer aggregate. The saved `customer_level_features.csv` spans all 36 months, so for Step 8 every aggregate must be **recomputed on the observation window only**.
- **Safe predictors,** computed within the observation window:
  - demographics (age, gender, region);
  - past spend, order count, discount usage, category mix, payment mix and return rate.

---

## 8. Data Quality Improvements (before vs after)

| Metric | Before cleaning | After cleaning |
|---|---|---|
| Rows | 18,819 | 18,670 |
| Columns | 23 | 51 (23 source + 28 engineered) |
| Missing values (23 source columns) | 960 cells | 0 |
| Exact duplicate rows | 149 | 0 |
| Records breaking ≥ 1 validation rule | 2,359 | 0 |
| Numeric columns stored as numbers | 0 of 7 (read as text) | 7 of 7 |
| Order_Date stored as a date | No (3 text formats) | Yes |
| Unique customers / products / orders | 2,000 / 61 / 13,251 | 2,000 / 61 / 13,251 (none lost) |
| Distinct Category labels | 24 | 6 |
| Distinct City labels | 41 | 35 (34 cities + `Unknown`) |
| Date range | 2023-01-01 to 2025-12-31 | 2023-01-01 to 2025-12-31 |

---

## 9. Limitations

1. **The `Unknown` labels are honest but incomplete.**
   - 89 order lines have `Payment_Method = Unknown` and will show as a separate category in payment analysis.
   - One customer's gender and city are `Unknown`, and their age is the median.
2. **Modal harmonisation assumes one profile per customer.** Customer attributes such as age and city are treated as fixed over the whole 3-year period. A real customer could move city or age by up to 3 years during that time.
3. **Returned lines keep their original Sales and Cost.** Return logistics costs are not modelled, so profit on returns is simplified by excluding those lines from realised figures.
4. **The alias lists (old city and state names) are finite.** A new variant in a future extract would fail the domain check and need to be added.
5. **The accuracy audit is possible only because the data are synthetic.** On real data, the validation checks in Section 3 would be the only evidence of data quality.
6. **Bulk orders are kept.** They slightly inflate quantity statistics, so later analyses can filter on `Is_Bulk_Order_Line` if needed.
