# Power BI Executive Dashboard - Documentation

**Project:** Customer Revenue Intelligence - An Interactive Data Science Platform for Customer
Segmentation, Revenue Prediction and Business Growth
**Step:** 11 of the project pipeline
**Dataset:** SYNTHETIC. Generated for this internship project; it does not describe real customers
or a real company.

> **What was built here, and what has to be built in Power BI Desktop.**
> Power BI Desktop runs only on Windows and cannot be installed or automated in this project's
> Linux environment. Everything that feeds the report - the star-schema extracts, the Power Query
> scripts, the DAX measure library, the theme, the recommendation content and the validated target
> values - was produced and checked here. The report file itself (`.pbix`) is assembled manually
> following `powerbi/POWERBI_BUILD_GUIDE.md`. No screenshot of a Power BI page is included, because
> none was taken; `outputs/figures/powerbi/mockups/` holds labelled design mockups instead.

---

## 1. Dashboard objective

Give a business reader the answer to six questions in one report, without asking them to open a
notebook:

1. How much revenue and profit does the business make, and how is that changing?
2. Which customers produce it, and which of them are drifting away?
3. How do the rule-based segments and the machine-learning clusters describe the customer base?
4. Which products and categories earn money rather than simply turn it over?
5. Which regions perform, and why?
6. What do the two forward-looking models say, and how accurate have they actually been?

The eighth page turns those answers into recommendations, each one carrying the analysis it rests
on.

**Scope limit.** The dashboard presents the analysis of Steps 3-10. It does not recompute
segmentation, customer value, predictions or forecasts; those were produced, validated and frozen
in their own steps, and Power BI reads their outputs.

---

## 2. Data sources

Everything comes from the validated Step 10 SQLite database
`data/customer_revenue_intelligence.db` and the saved model metadata. Power BI never reads the raw
CSV files.

| Layer | Source | Produced in |
|---|---|---|
| Transactions | `locations`, `customers`, `products`, `orders`, `order_items` | Step 3 (cleaning), loaded in Step 10 |
| RFM segments | `customer_rfm`, `rfm_segment_definitions` | Step 5 |
| K-Means clusters | `customer_segments`, `ml_clusters` | Step 6 |
| Customer value | `customer_value` | Step 7 |
| Revenue prediction | `outputs/tables/revenue_predictions.csv`, `revenue_quarterly_totals.csv`, `models/revenue_model_metadata.json` | Step 8 |
| Revenue forecast | `revenue_forecasts` table, `models/forecasting_metadata.json` | Step 9 |
| Recommendation evidence | `outputs/tables/` and `outputs/tables/sql/` | Steps 4-10 |

The extracts are produced by `sql/powerbi_views.sql` (eight `pbi_*` views) and
`src/powerbi_prep.py`, which writes `powerbi/data/*.csv`. Re-running the module regenerates every
file deterministically.

**Revenue rule.** Only Delivered order lines count as revenue. The rule is applied in one place in
SQL (`vw_delivered_sales`) and in one place in DAX (`FactSales[Is_Delivered] = 1` inside every
currency measure). Returned and Cancelled lines stay in the fact table so the realisation analysis
is possible, and are excluded from every revenue figure.

**Privacy.** `DimCustomer` deliberately has no name column. Analytical outputs identify a customer
by `Customer_ID` only. The dataset is synthetic, but the same rule is applied as if it were not.

---

## 3. Data model

A star schema: two transaction facts, two model facts and six dimensions, plus three supporting
tables that hold model metadata and recommendation content.

| Table | Role | Rows | Columns | Grain |
|---|---|---|---|---|
| DimDate | Dimension | 1277 | 23 | One row per calendar day, 2023-01-01 to 2026-06-30 |
| DimGeography | Dimension | 35 | 5 | One row per customer city |
| DimProduct | Dimension | 61 | 4 | One row per product |
| DimRFMSegment | Dimension | 12 | 6 | One row per Step 5 RFM segment (+ 'No delivered order') |
| DimCluster | Dimension | 5 | 4 | One row per Step 6 K-Means cluster (+ 'No delivered order') |
| DimCustomer | Dimension | 2000 | 36 | One row per registered customer (no names; Customer_ID only) |
| FactSales | Fact | 18670 | 19 | One row per order line, all statuses, with Is_Delivered |
| FactForecast | Fact | 54 | 13 | One row per month x forecast record type (Step 9) |
| FactRevenuePrediction | Fact | 2913 | 17 | One row per customer x target quarter, test split (Step 8) |
| PredictionQuarterly | Fact (aggregated) | 8 | 9 | One row per target quarter: actual vs predicted totals (Step 8) |
| ModelMetrics | Supporting | 25 | 8 | One row per model x split x metric (Steps 8 and 9) |
| ModelInfo | Supporting | 15 | 4 | One row per model attribute (design of Steps 8 and 9) |
| Recommendations | Supporting | 18 | 9 | One row per business recommendation, with its analytical basis |

Design notes:

- **FactSales keeps every order line**, with `Is_Delivered` as a flag, rather than filtering
  Delivered rows at load time. One fact table then answers both "what did we earn" and "what did we
  lose to returns", and the two can never disagree.
- **Customer state is folded into DimCustomer**, not left in separate tables. RFM scores, cluster
  assignment and customer-value fields are one-per-customer snapshots at the 2026-01-01 reference
  date, so they belong on the customer dimension. `DimRFMSegment` and `DimCluster` snowflake off it
  to carry segment descriptions and ordering.
- **DimGeography is joined to the fact**, not only to the customer, so a region slicer filters sales
  directly. In this dataset each customer has exactly one home location, so the two routes agree.
- **Customers with no delivered order** (16 of 2,000) get the member "No delivered order" in
  `DimRFMSegment` and `DimCluster` rather than a blank, so a segment slicer never shows an empty row.
- **No duplicated measures columns.** Nothing is pre-aggregated: every number on every page is a
  DAX measure over these tables.

### Date table

`DimDate` has one row per day from 2023-01-01 to 2026-06-30 - the 36 historical months plus the
6-month forecast horizon, so forecast rows have real dates to join to. Columns: `Date`, `Year`,
`Quarter`, `Quarter_Number`, `Year_Quarter`, `Month_Number`, `Month_Name`, `Month_Short`,
`Year_Month`, `Year_Month_Sort`, `Month_Start_Date`, `Week_Number` (ISO), `ISO_Week_Year`, `Day`,
`Day_Of_Week_Number`, `Day_Name`, `Is_Weekend`, `Financial_Year`, `Financial_Year_Start`,
`Financial_Quarter`, `Financial_Month_Number`, `Period_Type`.

The financial-year columns follow the Indian April-March convention as a standard calendar
attribute; the dataset does not state a company fiscal year, so they are offered rather than used as
the default.

Two manual steps in Power BI Desktop: sort `Month_Name` by `Month_Number` (and `Year_Month` by
`Year_Month_Sort`, `Year_Quarter` by `Year_Quarter_Sort`), and mark the table as the official date
table on `DimDate[Date]`.

---

## 4. Relationships

| From Table | From Column | To Table | To Column | Cardinality | Cross Filter Direction | Active | Notes |
|---|---|---|---|---|---|---|---|
| DimDate | Date | FactSales | Order_Date | One-to-many | Single | Yes | Date table marked in Power BI; drives every time intelligence measure |
| DimCustomer | Customer_ID | FactSales | Customer_ID | One-to-many | Single | Yes |  |
| DimProduct | Product_ID | FactSales | Product_ID | One-to-many | Single | Yes |  |
| DimGeography | Location_ID | FactSales | Location_ID | One-to-many | Single | Yes | Customer home location; one location per customer in this dataset |
| DimRFMSegment | RFM_Segment | DimCustomer | RFM_Segment | One-to-many | Single | Yes | Snowflake on the customer dimension: segment attributes filter customers, which filter sales |
| DimCluster | Cluster_ID | DimCustomer | Cluster_ID | One-to-many | Single | Yes | Snowflake on the customer dimension |
| DimDate | Date | FactForecast | Month_Date | One-to-many | Single | Yes | Forecast rows join on the first day of the month |
| DimDate | Date | FactRevenuePrediction | Target_Quarter_Start | One-to-many | Single | No | INACTIVE by design: the prediction grain is a quarter, so a date filter would silently drop rows. Activate with USERELATIONSHIP only if a quarter-level date filter is wanted. |
| DimCustomer | Customer_ID | FactRevenuePrediction | Customer_ID | One-to-many | Single | Yes | Lets the prediction page respond to the customer and segment slicers |

The only inactive relationship is `DimDate -> FactRevenuePrediction`. The prediction grain is a
quarter, not a day, so leaving that relationship active would let a date slicer silently drop
prediction rows and make the model look wrong. The Prediction & Forecast page therefore filters
predictions by `Target_Period` from the prediction table itself.

---

## 5. DAX measures

`powerbi/dax/measures.dax` holds 84 measures in 10
display folders, each with its format string and a one-line statement of what it is for.
`powerbi/dax/measure_catalog.csv` is the same list as a table.

| Display folder | Measures | What it covers |
|---|---|---|
| 01 Revenue | 14 | Total revenue, booked value and realisation, prior-year and prior-month comparisons, growth %, YTD, average monthly revenue, the ₹ lakh axis measure and the crore/lakh card label |
| 02 Profitability | 7 | Profit, margin %, profit per order, prior-year profit, margin change in percentage points |
| 03 Orders | 6 | Orders, order lines, quantity, AOV, quantity per order, value-weighted average discount |
| 04 Customers | 9 | Registered, purchasing, active, inactive, new, repeat (snapshot and in-period), repeat %, orders per customer |
| 05 Customer value | 13 | Average customer revenue, contribution % against customer / segment / cluster / category / region, historical CLV, estimated 12-month future profit, illustrative 3-year value, at-risk and high-value counts |
| 06 Segmentation | 7 | Segment customer counts and shares, average R / F / M, average RFM score, revenue per customer in a segment |
| 07 Products & regions | 4 | Return / cancel rate, products sold, revenue rank, margin versus own category in percentage points |
| 08 Prediction | 8 | Predicted and matching actual revenue, naive baseline, MAE, RMSE, R², bias %, and the metric value read from ModelMetrics |
| 09 Forecast | 11 | Historical monthly revenue, backtest forecast, future forecast, 80% and 95% interval bounds, interval width, horizon, forecast total |
| 10 Labels & context | 5 | Date-range label, selected model names read from ModelInfo, synthetic-data disclaimer, "filters applied" warning |

Three conventions worth stating:

1. **One revenue definition.** `Total Revenue` is the only place the Delivered filter is written;
   every other currency measure builds on it or repeats the same single filter.
2. **Snapshot measures are marked as snapshots.** `Active Customers`, `Avg Recency (days)`,
   `Repeat Customers`, the CLV measures and the RFM averages read `DimCustomer`, which is a
   2026-01-01 snapshot. They do not move with the Date slicer, and the measure descriptions say so.
   `Repeat Customers (in period)` is the version that does respond to dates.
3. **Indian number formatting.** Cards use `Revenue Label` / `Profit Label` / `Forecast Label`,
   which switch between `₹0.00 Cr` and `₹0.00 L`; chart axes use `Revenue (₹ lakh)` so axis labels
   stay short. Percentages are shown to one decimal, ratios (R², Spearman) to three.

---

## 6. Dashboard pages

### HOME

**Purpose.** Entry page: what the report answers, headline KPIs, page directory.

**Visuals.**

  - Four KPI cards (revenue, profit, margin, customers)
  - Page directory with navigation buttons
  - Synthetic-data statement

**Design mockup.** `outputs/figures/powerbi/mockups/00_home_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 1 Executive Overview

**Purpose.** The whole business on one screen: how much, how profitable, where it comes from.

**Visuals.**

  - KPI cards: Total Revenue, Total Profit, Profit Margin %, Total Orders, Total Customers, AOV
  - Line: monthly revenue and profit (one axis, both in rupees)
  - Ranked bars: revenue by region
  - Ranked bars: revenue by category with margin labels
  - Paired bars: revenue share vs customer share by RFM segment
  - Column: revenue by year with growth % labels
  - Line: cumulative revenue by customer (Pareto)

**Design mockup.** `outputs/figures/powerbi/mockups/01_executive_overview_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 2 Revenue Intelligence

**Purpose.** Where revenue and margin come from over time, and what moves them.

**Visuals.**

  - Line: revenue and profit by month with the cost gap shaded
  - Line: profit margin % by month (its own chart - a ratio never shares an axis with rupees)
  - Columns: year-over-year revenue and profit growth %
  - Ranked bars: top 10 sub-categories with margin labels
  - Columns: margin by discount band
  - Lines: discount band vs margin within each category
  - Grouped bars: revenue by region and year
  - Text panel: revenue drivers, each naming its query

**Design mockup.** `outputs/figures/powerbi/mockups/02_revenue_intelligence_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 3 Customer Intelligence

**Purpose.** Who the customers are, what they are worth, and how recently they bought.

**Visuals.**

  - KPI cards: customers, active customers, average customer revenue, AOV, repeat customers, at-risk high-value customers
  - Histogram: lifetime revenue per customer
  - Paired bars: orders-per-customer bands
  - Columns: recency distribution
  - Table: top 10 customers (Customer_ID, revenue, profit, frequency, recency, segment, illustrative 3-year value)
  - Line: revenue concentration (Pareto) with the 10 / 20 / 50% points marked

**Design mockup.** `outputs/figures/powerbi/mockups/03_customer_intelligence_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 4 Customer Segmentation

**Purpose.** RFM rules and K-Means clusters, compared without ranking one above the other.

**Visuals.**

  - Text panel: what each method is for
  - Paired bars: RFM segments - customer share vs revenue share
  - Paired bars: K-Means clusters - customer share vs revenue share
  - Grouped columns: average recency, frequency and monetary by segment
  - Matrix: segment, customers, revenue, profit, average revenue, average frequency, average recency, revenue %
  - Ranked bars: revenue per customer by cluster

**Design mockup.** `outputs/figures/powerbi/mockups/04_customer_segmentation_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 5 Product Analytics

**Purpose.** Which products earn, which only turn over, and which lose value to returns.

**Visuals.**

  - Bars: revenue with profit inside, by category, margin labelled
  - Ranked bars: top 10 products by revenue with their margin
  - Ranked bars: bottom 10 products by margin versus their own category (defined metric)
  - Scatter: revenue (X) vs profit (Y), bubble size = units, colour = category, notable products labelled
  - Bars: booked value lost by category
  - Bars: units sold by category
  - Table: products flagged for investigation by the Step 10 rules

**Design mockup.** `outputs/figures/powerbi/mockups/05_product_analytics_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 6 Regional Analytics

**Purpose.** Regional performance, and the category mix that explains it.

**Visuals.**

  - Text panel: why ranked bars and a matrix are used instead of a map
  - Bars: revenue with profit inside, by region, margin labelled
  - Grouped columns: customers and orders by region
  - Grouped columns: AOV and revenue per customer by region
  - Matrix / heat table: profit margin % by region and category, every cell numbered
  - Table: largest region x category combinations

**Design mockup.** `outputs/figures/powerbi/mockups/06_regional_analytics_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 7 Prediction & Forecast

**Purpose.** The two forward-looking models, kept strictly apart.

**Visuals.**

  - Legend panel defining Historical, Predicted and Forecast
  - Line: monthly actual, backtest forecast and future forecast with the 95% interval shaded
  - KPI cards: 6-month forecast total, forecast test MAPE, prediction MAE, prediction R²
  - Columns: actual vs predicted customer revenue by quarter, test quarters shaded
  - Bars: prediction error by segment at the cutoff
  - Table: model performance, read from ModelMetrics

**Design mockup.** `outputs/figures/powerbi/mockups/07_prediction_forecast_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

### 8 Business Recommendations

**Purpose.** 18 recommendations grouped into Customer, Product, Regional, Revenue and Forecasting & Planning, each with its evidence and source.

**Visuals.**

  - 18 recommendation cards, colour-coded by area
  - Each card: recommendation, evidence with figures, supporting metric, and the saved query, table or model metadata it came from
  - Table visual behind the cards with the full Evidence and Suggested_Action columns

**Design mockup.** `outputs/figures/powerbi/mockups/08_business_recommendations_mockup.png` (a specification drawn from the real data, not a Power BI screenshot).

---

## 7. Visualizations

Every visual on every page answers a stated question; none is decorative. The chart type follows
from the job the data has to do:

| Job | Chart used | Why |
|---|---|---|
| A value over time | Line | Months are ordered and continuous |
| One customer's months | Column | Separate purchases, not a continuous series |
| Compare categories | Ranked horizontal bars | Long labels, and rank is the point |
| Two comparable shares | Paired bars | The gap between share of customers and share of revenue is the message |
| A ratio over time | Its own line chart | A ratio never shares an axis with rupees |
| Two measures per item | Revenue bar with profit drawn inside | Shows the margin gap without a second axis |
| Relationship between two measures | Scatter with bubble size | Revenue, profit and volume at once |
| A matrix of one measure | Heat table with numbers in every cell | Colour is a reading aid; the number is the information |
| A single headline number | KPI card | Immediate recall, no decoding |

Rules applied throughout: **no dual axes anywhere**; a legend whenever two or more series appear;
selective direct labels rather than a number on every point; recessive gridlines; text in text
colours, never in a series colour; consistent series colours across pages (Historical, Predicted and
Forecast keep the same three hues on every page they appear).

---

## 8. Filters and slicers

Seven slicers, synced across pages with Power BI's **View > Sync slicers** panel:

| Slicer | Field | Type | Synced to | Notes |
|---|---|---|---|---|
| Date | `DimDate[Date]` | Between (range) | Pages 1-7 | Page 7 extends to 2026-06-30 to include the forecast horizon |
| Year | `DimDate[Year]` | Tile | Pages 1-6 | Quick alternative to the range slicer |
| Month | `DimDate[Month_Name]` | Dropdown | Pages 1-6 | Sorted by `Month_Number` |
| Region | `DimGeography[Region]` | Dropdown | All pages | |
| Category | `DimProduct[Category]` | Dropdown | All pages | |
| Sub-category | `DimProduct[Sub_Category]` | Dropdown | Pages 2, 5 | Hierarchically filtered by Category |
| Customer segment | `DimRFMSegment[RFM_Segment]` | Dropdown | Pages 1, 3, 4, 7 | Sorted by `Segment_Order` |
| Cluster | `DimCluster[Cluster_Label]` | Dropdown | Pages 3, 4 | Sorted by `Cluster_Order` |

Each page carries the `Date Range Label` and `Filters Applied` measures in its header, so a filtered
number is never mistaken for the full-period number.

---

## 9. Drill-through functionality

| Page | Type | Field | Reached from | Shows |
|---|---|---|---|---|
| Customer Detail | Drill-through | `DimCustomer[Customer_ID]` | Top-customer table (p3), segment matrix (p4), prediction table (p7) | Profile (no name), RFM and cluster, lifetime revenue and profit, estimated 12-month profit, illustrative 3-year value, revenue by month, category mix, recent orders |
| Product Detail | Drill-through | `DimProduct[Product_ID]` | Top / bottom product bars and the scatter (p5) | Revenue, profit, margin, units, average discount, return rate, monthly trend, region mix |
| Customer tooltip | Tooltip page (320 x 240) | `DimCustomer[Customer_ID]` | Any customer visual | Revenue, orders, recency, frequency, monetary, segment |
| Product tooltip | Tooltip page (320 x 240) | `DimProduct[Product_ID]` | Any product visual | Revenue, profit, quantity, margin |

Both drill-through pages keep the "Keep all filters" toggle on, so arriving from a filtered page
carries that context, and both have a back button.

---

## 10. Forecast integration

The two forward-looking models are different in unit, method and purpose, and the report never
merges them.

| | Revenue prediction (Step 8) | Revenue forecast (Step 9) |
|---|---|---|
| Question | How much will *this customer* spend next quarter? | How much will *the company* earn next month? |
| Unit | Customer x quarter | Company x month |
| Model | Linear regression | Theta: Theta (seasonality auto-tested) |
| Selection rule | simplest model within 2% of the best validation RMSE (fixed in advance) | lowest mean backtest MAPE; must beat naive and seasonal naive on test MAE; within 5% -> simpler family |
| Evaluated on | Validation targets 2025-01-01..2025-06-30, test targets 2025-07-01..2025-12-31 | Validation 2025-01..2025-06, test 2025-07..2025-12 |
| Headline accuracy | Test MAE ₹5,658, RMSE ₹11,232, R² 0.056, bias +1.12% | Test MAE ₹213,179, MAPE 7.77%, sMAPE 8.24%, WAPE 8.50% |
| Shown as | PREDICTED (orange) | FORECAST (green), with 80% and 95% intervals |
| Horizon | One quarter ahead | 6 months: 2026-01 to 2026-06 |

The forecast total for the horizon is **₹1.58 Cr**, and the page shows the prediction
interval alongside it rather than the point forecast alone. MAPE is reported for the forecast and
deliberately not for the prediction: many customer-quarters have an actual of zero, which makes a
percentage error undefined.

The `ModelMetrics` table is generated from the saved model metadata, and the model performance
visual reads it. No metric is typed onto a page, so a metric on the dashboard cannot drift from the
metric in the model file.

---

## 11. Design principles

1. **The headline KPIs are visible immediately.** Six cards across the top of the Executive
   Overview, before any chart.
2. **Nothing is crowded.** Six to eight visuals per page, on a consistent grid, with the
   navigation rail in the same place on every page.
3. **Every visual answers a business question**, and its title states the question's answer rather
   than naming the data ("Revenue contribution by RFM segment", not "Customer chart").
4. **Consistent number formatting.** Indian units on cards (₹6.01 Cr, ₹62.55 L), ₹ lakh on chart
   axes, one decimal on percentages, three on ratios. Each measure carries exactly one format
   string, so the same quantity looks the same everywhere.
5. **A dark data-intelligence theme**, defined once in `powerbi/theme/crm_dark_theme.json`: page
   `#0B111C`, panels `#141C2B` with a `#25324A` border and rounded
   corners, a soft two-glow gradient background PNG, and eight categorical hues that were validated
   against the panel surface for lightness, chroma, colour-vision separation and contrast.
   `powerbi/theme/palette_reference.md` lists every value.

### Accessibility and readability

- Body text `#E6EDF7` and headings `#FFFFFF` on `#141C2B`: contrast
  well above the 4.5:1 requirement. Muted text `#8E9BB3` is used only for labels and
  captions, never for a number the reader has to act on.
- Minimum font sizes: 10 pt axis labels, 11 pt body, 13 pt visual titles, 30 pt card values.
- **Colour is never the only cue.** Every segment bar is labelled, every heat-table cell shows its
  number, the recency chart labels its bands, and status colours always appear with a word.
- Status colours (good / warning / serious / critical) are reserved and never reused as a data
  series.
- Tooltips add context rather than repeating the visual.

---

## 12. Validation

Three independent checks, all of which run in this environment.

**(a) Measure definitions against SQL.** 120 measure-context combinations were recomputed
in pandas; 48 of them - the four required measures plus profit margin and AOV, across all
eight filter contexts - were also recomputed independently in SQL. **48 of 48
match** to within one paisa. File: `powerbi/validation/measure_validation_targets.csv`, which also
carries an empty `Power_BI_Value` column to fill in after the cards are built, and
`powerbi/dax/validation_query.dax`, which produces the same numbers from the finished report.

Headline targets on unfiltered data:

| Measure | Value |
|---|---|
| Total Revenue | ₹60,056,569.15 (6.01 Cr) |
| Total Profit | ₹14,022,551.58 (1.40 Cr) |
| Profit Margin % | 23.35% |
| Total Orders | 12,212 |
| Total Customers | 1,984 |
| Average Order Value | ₹4,917.83 |

**(b) Cross-step consistency.** 32 checks confirm the star-schema extracts still agree with
Steps 4-9 (revenue, profit, cost, orders, customers, units; Champions and cluster revenue; CLV
totals; monthly actuals; forecast totals; prediction totals and MAE) and that the model is sound
(no orphan keys, unique dimension keys, no customer-name column). **All 32 pass.** File:
`powerbi/validation/cross_step_consistency.csv`.

**(c) Customer-state targets.** `powerbi/validation/customer_state_validation_targets.csv` holds the
snapshot counts (registered, purchasing, active, inactive, repeat, at-risk) and the RFM and CLV
averages, for checking the customer pages.

**Legitimate differences that are not errors, and must not be "fixed" by forcing a match:**

- `Total Customers` (1,984) counts customers with a delivered order; `Registered Customers` (2,000)
  counts rows in `DimCustomer`. The 16-customer gap is real.
- `Active Customers` and every RFM / CLV measure are snapshots at 2026-01-01. Filtering the Date
  slicer to 2024 does not change them, by design. Filtering changes `Total Revenue` in the same
  visual, so the two are never presented as the same kind of quantity.
- `New Customers` for 2023 counts first *observed* delivered purchases. 767 customers were already
  customers before the data window (`Acquisition_Status = 'Existing before 2023'`), so 2023's figure
  is "first seen", not "newly acquired".
- `Prediction R²` recomputed inside a slicer is the R² of that subset, which is a different quantity
  from the Step 8 test R². The page shows the Step 8 figure from `ModelMetrics` next to it.
- Figures rounded in Step 10's SQL output can differ from the DAX value in the second decimal;
  the DAX value is the unrounded one.

### Checklist

| Checklist Item | Status | Evidence |
|---|---|---|
| Power BI data model created | Done (files) | 13 tables exported to powerbi/data/ from the pbi_* SQL views; catalogue in powerbi/table_catalog.csv. Loading them into Power BI Desktop is a manual step. |
| Relationships validated | Done (files) + Validated (Python) | 9 relationships specified in powerbi/relationships.csv with cardinality, cross-filter direction and active flag. Key uniqueness and orphan keys checked in powerbi/validation/cross_step_consistency.csv. |
| Date table created | Done (files) | DimDate: 1,277 daily rows, 2023-01-01 to 2026-06-30, with Year, Quarter, Month Number, Month Name, Year-Month, ISO week, Day, financial-year attributes and Period_Type. Marking it as the official date table and sorting Month Name by Month Number are manual steps in Power BI Desktop. |
| DAX measures created | Done (files) | 84 measures in powerbi/dax/measures.dax, grouped into 10 display folders, each with its format string and purpose. Pasting them into the model is manual. |
| Core KPI values reconciled with SQL/Python | Validated (Python/SQL) | 15 measures x 8 filter contexts recomputed in pandas; the four required measures plus margin and AOV independently recomputed in SQL - 48 of 48 comparisons match. Targets for the Power BI cards: powerbi/validation/measure_validation_targets.csv. |
| Executive Overview created | Specified + mockup | Layout, visuals and measures specified; design mockup 01. Building the page in Power BI Desktop is manual. |
| Revenue Intelligence created | Specified + mockup | Layout, visuals and measures specified; design mockup 02. Building the page is manual. |
| Customer Intelligence created | Specified + mockup | Layout, visuals and measures specified; design mockup 03. Building the page is manual. |
| Customer Segmentation created | Specified + mockup | Layout, visuals and measures specified; design mockup 04. Building the page is manual. |
| Product Analytics created | Specified + mockup | Layout, visuals and measures specified; design mockup 05. Building the page is manual. |
| Regional Analytics created | Specified + mockup | Layout, visuals and measures specified; design mockup 06. Building the page is manual. |
| Prediction & Forecast created | Specified + mockup | Layout, visuals and measures specified; design mockup 07. Building the page is manual. |
| Business Recommendations created | Done (content) + mockup | 18 recommendations computed from the Step 4-10 outputs into powerbi/data/Recommendations.csv; design mockup 08. Placing them on the page is manual. |
| Slicers configured | Specified | Seven synced slicers specified (Date, Year, Month, Region, Category, Sub-category, Segment/Cluster) with their sync groups; see section 8 of the documentation. Configuring them is manual. |
| Drill-through configured where appropriate | Specified + mockup | Customer Detail and Product Detail drill-through pages specified with their drill-through fields; Customer Detail mockup 09. Configuring them is manual. |
| Tooltips configured where appropriate | Specified | Customer and Product tooltip pages specified (320 x 240, fields listed in section 9). Configuring them is manual. |
| Navigation created | Specified + mockup | HOME plus the 8 pages, with a left navigation rail and page-navigation buttons; shown on every mockup. Adding the buttons is manual. |
| Dashboard design standardized | Done (files) | Theme JSON (powerbi/theme/crm_dark_theme.json), page background PNG and palette reference; one format string per measure. Applying the theme is one manual step. |
| Documentation created | Done | outputs/reports/powerbi_dashboard_documentation.md, 14 sections. |
| User guide created | Done | outputs/reports/powerbi_user_guide.md. |
| No fabricated results | Verified | Every figure in the extracts, recommendations, mockups and documentation is read from a Step 4-10 output file; cross-step consistency is checked in powerbi/validation/cross_step_consistency.csv (32 of 32 pass). No Power BI screenshot is claimed - outputs/figures/powerbi/ holds labelled design mockups and a README that says so. |

---

## 13. Limitations

1. **The report file itself is not built here.** Power BI Desktop is Windows-only, so the `.pbix`
   must be assembled manually from `powerbi/POWERBI_BUILD_GUIDE.md`. Until that is done, the pages
   exist as specifications and labelled mockups, not as a dashboard.
2. **No screenshots.** `outputs/figures/powerbi/` contains design mockups rendered with matplotlib
   from the real extracts, each watermarked "DESIGN MOCKUP - not a Power BI screenshot", plus a
   README explaining what has to be captured manually and under which file names.
3. **The data is synthetic.** Patterns in it were generated, so no finding here describes a real
   market. The analysis method is what transfers, not the numbers.
4. **Import mode, not DirectQuery.** The extracts are CSV snapshots; the dashboard does not update
   until they are regenerated and refreshed.
5. **Customer state is a single snapshot.** Segments, recency and customer value are as at
   2026-01-01. The report cannot show how a customer's segment changed over time, because that
   history was never computed.
6. **The customer-level prediction is weak** (test R² 0.056). It is
   presented for ranking customers and for aggregate planning, and the page says so rather than
   implying per-customer precision.
7. **The forecast is company-level and univariate.** It has no regional or category breakdown, no
   promotional or external drivers, and is fitted on 36 months, which is a short series for any
   seasonal claim. Step 9 found no significant seasonality at that length.
8. **Geography is limited.** Home city and a five-region business grouping, with no coordinates; the
   Regional page therefore uses ranked bars and a matrix rather than a filled map.
9. **Associations, not causes.** The discount / margin, payment-method / cancellation and
   region / margin comparisons are observational. The dashboard states them as associations.
10. **Nothing on the dashboard is monitored.** There is no alerting, no scheduled refresh and no
    row-level security configured.

---

## 14. User guide

A separate document for business readers: `outputs/reports/powerbi_user_guide.md`. It covers
opening the report, the slicers, page navigation, drill-through, how to read each KPI, how to read
the forecast and its interval, resetting filters and refreshing the data.

---

## Files produced by Step 11

| Path | What it is |
|---|---|
| `sql/powerbi_views.sql` | The eight `pbi_*` star-schema views |
| `src/powerbi_prep.py` | Builds and validates everything in this list |
| `src/powerbi_dax.py` | The DAX measure library as data |
| `powerbi/data/*.csv` | 13 star-schema extracts |
| `powerbi/powerquery/*.m` | One Power Query script per table + the `DataFolder` parameter |
| `powerbi/dax/measures.dax` | 84 measures with folders, formats and purposes |
| `powerbi/dax/validation_query.dax` | DAX to reproduce the validation numbers from the report |
| `powerbi/theme/crm_dark_theme.json` | The theme |
| `powerbi/theme/page_background.png` | Page background |
| `powerbi/theme/palette_reference.md` | Every colour and its rule |
| `powerbi/relationships.csv`, `table_catalog.csv` | Model specification |
| `powerbi/validation/*.csv` | Measure targets, customer-state targets, cross-step checks |
| `powerbi/POWERBI_BUILD_GUIDE.md` | The manual build steps, in order |
| `outputs/figures/powerbi/mockups/*.png` | 10 labelled design mockups |
| `outputs/figures/powerbi/README.md` | What still has to be captured manually |
| `outputs/reports/powerbi_dashboard_documentation.md` | This document |
| `outputs/reports/powerbi_user_guide.md` | The user guide |
| `outputs/tables/powerbi_*.csv` | Catalogue, relationships, measures, validation, checklist |

*18 recommendations, 84 DAX measures, 13 tables,
32 consistency checks - all generated from the project's own outputs.*
